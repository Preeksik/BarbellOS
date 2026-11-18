"""Klient USDA FoodData Central: wyszukiwanie produktów i mikroskładniki na 100 g.

Dane USDA są w domenie publicznej (CC0). Używamy zbiorów „Foundation" i „SR Legacy":
wartości z analiz laboratoryjnych dla konkretnego produktu (np. „Bananas, raw"), a nie
z etykiet. Dokumentacja: https://fdc.nal.usda.gov/api-guide

Limit: klucz demonstracyjny `DEMO_KEY` pozwala na ok. 10 zapytań na godzinę z adresu,
własny darmowy klucz (https://fdc.nal.usda.gov/api-key-signup) na 1000. Jedno zapytanie
wyszukiwania zwraca od razu komplet składników kandydatów, więc wynik trzymamy w pamięci
i zapis dopasowania nie wymaga kolejnego zapytania.
"""

import time
from dataclasses import dataclass, field

import httpx

DATA_TYPES = "Foundation,SR Legacy"

# Numer składnika w FDC -> identyfikator z seed/nutrients.json. Numery są stabilne,
# nazwy bywają różne między zbiorami. Jednostki w FDC odpowiadają naszym (mg, µg).
NUTRIENT_NUMBERS: dict[str, str] = {
    "320": "vit_a",  # Vitamin A, RAE (µg)
    "328": "vit_d",  # Vitamin D (D2 + D3) (µg)
    "323": "vit_e",  # Vitamin E (alpha-tocopherol) (mg)
    "430": "vit_k",  # Vitamin K (phylloquinone) (µg)
    "401": "vit_c",  # Vitamin C, total ascorbic acid (mg)
    "404": "vit_b1",  # Thiamin (mg)
    "405": "vit_b2",  # Riboflavin (mg)
    "406": "vit_b3",  # Niacin (mg)
    "415": "vit_b6",  # Vitamin B-6 (mg)
    "435": "folate",  # Folate, DFE (µg)
    "418": "vit_b12",  # Vitamin B-12 (µg)
    "301": "calcium",  # Calcium, Ca (mg)
    "303": "iron",  # Iron, Fe (mg)
    "304": "magnesium",  # Magnesium, Mg (mg)
    "309": "zinc",  # Zinc, Zn (mg)
    "306": "potassium",  # Potassium, K (mg)
    "307": "sodium",  # Sodium, Na (mg)
    "305": "phosphorus",  # Phosphorus, P (mg)
    "317": "selenium",  # Selenium, Se (µg)
    "314": "iodine",  # Iodine, I (µg)
}
# Jednostka, w której FDC musi podać składnik, żeby wartość pasowała do naszej.
EXPECTED_UNITS = {"UG": {"vit_a", "vit_d", "vit_k", "folate", "vit_b12", "selenium", "iodine"}}
KCAL_NUMBERS = ("208", "957", "958")  # Energy; Atwater General; Atwater Specific (Foundation)


class FdcError(Exception):
    """USDA nie odpowiada albo odrzuca zapytanie."""


class FdcRateLimited(FdcError):
    """Wyczerpany limit zapytań (HTTP 429): klucz demonstracyjny ma ok. 10 na godzinę."""


@dataclass(frozen=True)
class FdcFood:
    fdc_id: int
    description: str
    data_type: str
    kcal: float | None
    micros: dict[str, float] = field(default_factory=dict)  # na 100 g, nasze jednostki


def _unit_ok(nutrient_id: str, unit: str) -> bool:
    expected = "UG" if nutrient_id in EXPECTED_UNITS["UG"] else "MG"
    return unit.upper() == expected


def parse_food(raw: dict) -> FdcFood | None:
    """Rekord z wyszukiwania FDC -> produkt z mikroskładnikami. None bez identyfikatora."""
    fdc_id = raw.get("fdcId")
    if not isinstance(fdc_id, int):
        return None
    micros: dict[str, float] = {}
    kcal_by_number: dict[str, float] = {}
    for nutrient in raw.get("foodNutrients") or []:
        number = str(nutrient.get("nutrientNumber") or "")
        value = nutrient.get("value")
        if not isinstance(value, int | float) or isinstance(value, bool) or value < 0:
            continue
        if number in KCAL_NUMBERS and str(nutrient.get("unitName", "")).upper() == "KCAL":
            kcal_by_number[number] = float(value)
        nutrient_id = NUTRIENT_NUMBERS.get(number)
        if nutrient_id and _unit_ok(nutrient_id, str(nutrient.get("unitName") or "")):
            micros[nutrient_id] = float(value)
    kcal = next((kcal_by_number[n] for n in KCAL_NUMBERS if n in kcal_by_number), None)
    return FdcFood(
        fdc_id=fdc_id,
        description=str(raw.get("description") or "").strip(),
        data_type=str(raw.get("dataType") or ""),
        kcal=kcal,
        micros=micros,
    )


class FdcClient:
    """Wyszukiwanie w FDC z pamięcią wyników (zapis dopasowania bez drugiego zapytania)."""

    CACHE_SECONDS = 3600

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.nal.usda.gov/fdc",
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.api_key, self.base_url, self.transport = api_key, base_url.rstrip("/"), transport
        self._cache: dict[int, tuple[float, FdcFood]] = {}

    def _get(self, path: str, params: dict) -> dict | list:
        try:
            with httpx.Client(transport=self.transport, timeout=20.0) as client:
                response = client.get(
                    f"{self.base_url}{path}", params={**params, "api_key": self.api_key}
                )
        except httpx.HTTPError as exc:
            raise FdcError(f"brak odpowiedzi ({type(exc).__name__})") from exc
        if response.status_code == 429:
            raise FdcRateLimited("limit zapytań USDA")
        if response.status_code >= 400:
            raise FdcError(f"HTTP {response.status_code}")
        try:
            return response.json()
        except ValueError as exc:
            raise FdcError("odpowiedź nie jest JSON-em") from exc

    def search(self, query: str, page_size: int = 10) -> list[FdcFood]:
        payload = self._get(
            "/v1/foods/search",
            {"query": query, "dataType": DATA_TYPES, "pageSize": page_size},
        )
        foods = [
            food
            for raw in (payload.get("foods") or [] if isinstance(payload, dict) else [])
            if (food := parse_food(raw)) is not None
        ]
        now = time.monotonic()
        for food in foods:
            self._cache[food.fdc_id] = (now, food)
        return foods

    def food(self, fdc_id: int) -> FdcFood:
        """Produkt z pamięci wyszukiwania albo (po godzinie) pobrany ponownie."""
        cached = self._cache.get(fdc_id)
        if cached and time.monotonic() - cached[0] < self.CACHE_SECONDS:
            return cached[1]
        payload = self._get(f"/v1/food/{fdc_id}", {"format": "abridged"})
        food = parse_food(payload) if isinstance(payload, dict) else None
        if food is None:
            raise FdcError("USDA nie zwróciło produktu")
        self._cache[fdc_id] = (time.monotonic(), food)
        return food
