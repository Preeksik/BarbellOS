"""Klient Open Food Facts: pobranie produktu po kodzie kreskowym i mapowanie pól.

Zapytania idą z backendu (nie z przeglądarki), bo OFF prosi o nagłówek User-Agent
identyfikujący aplikację, a wynik zapisujemy we własnej bazie.

[DO WERYFIKACJI w próbie C] Mapowanie mikroskładników zakłada, że OFF podaje pola
`*_100g` w gramach. Próba C porównuje kilka produktów z etykietą.
"""

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime

import httpx

FIELDS = (
    "code,product_name,product_name_pl,brands,quantity,product_quantity_unit,serving_quantity,"
    "nutriments,categories_tags,last_modified_t"
)

# nasza kolumna -> pole OFF (na 100 g)
MACRO_FIELDS = {
    "kcal": "energy-kcal_100g",
    "protein_g": "proteins_100g",
    "fat_g": "fat_100g",
    "sat_fat_g": "saturated-fat_100g",
    "carbs_g": "carbohydrates_100g",
    "sugars_g": "sugars_100g",
    "fiber_g": "fiber_100g",
    "salt_g": "salt_100g",
}

# identyfikator z seed/nutrients.json -> (pole OFF, mnożnik z gramów na naszą jednostkę)
MG, UG = 1_000.0, 1_000_000.0
MICRO_FIELDS = {
    "vit_a": ("vitamin-a_100g", UG),
    "vit_d": ("vitamin-d_100g", UG),
    "vit_e": ("vitamin-e_100g", MG),
    "vit_k": ("vitamin-k_100g", UG),
    "vit_c": ("vitamin-c_100g", MG),
    "vit_b1": ("vitamin-b1_100g", MG),
    "vit_b2": ("vitamin-b2_100g", MG),
    "vit_b3": ("vitamin-pp_100g", MG),
    "vit_b6": ("vitamin-b6_100g", MG),
    "folate": ("vitamin-b9_100g", UG),
    "vit_b12": ("vitamin-b12_100g", UG),
    "calcium": ("calcium_100g", MG),
    "iron": ("iron_100g", MG),
    "magnesium": ("magnesium_100g", MG),
    "zinc": ("zinc_100g", MG),
    "potassium": ("potassium_100g", MG),
    "sodium": ("sodium_100g", MG),
    "phosphorus": ("phosphorus_100g", MG),
    "selenium": ("selenium_100g", UG),
    "iodine": ("iodine_100g", UG),
}

KJ_PER_KCAL = 4.184
SALT_PER_SODIUM = 2.5


@dataclass
class FoodDraft:
    barcode: str
    name: str
    brand: str | None
    category: str | None
    serving_g: float | None
    macros: dict[str, float | None]
    micros: dict[str, float] = field(default_factory=dict)
    raw: dict | None = None
    unit: str = "g"  # g | ml
    source_updated_at: datetime | None = None


def _num(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


_VOLUME = re.compile(r"\d\s*(ml|cl|dl|l)\b", re.IGNORECASE)


def _detect_unit(product: dict) -> str:
    """Napoje mają wartości na 100 ml. OFF nie mówi tego wprost, więc patrzymy na opakowanie.

    Użytkownik może jednostkę poprawić przy edycji produktu.
    """
    declared = str(product.get("product_quantity_unit") or "").lower()
    if declared in ("ml", "l", "cl", "dl"):
        return "ml"
    if declared in ("g", "kg", "mg"):
        return "g"
    return "ml" if _VOLUME.search(str(product.get("quantity") or "")) else "g"


def _timestamp(value) -> datetime | None:
    seconds = _num(value)
    return datetime.fromtimestamp(seconds, UTC) if seconds else None


def parse_product(payload: dict) -> FoodDraft | None:
    """Zamienia odpowiedź OFF na szkic produktu. Zwraca None, gdy produktu nie ma w bazie."""
    product = payload.get("product")
    if not product or payload.get("status") == 0:
        return None
    n = product.get("nutriments") or {}

    macros = {col: _num(n.get(off_field)) for col, off_field in MACRO_FIELDS.items()}
    if macros["kcal"] is None and (kj := _num(n.get("energy_100g"))) is not None:
        macros["kcal"] = kj / KJ_PER_KCAL
    if macros["salt_g"] is None and (sodium := _num(n.get("sodium_100g"))) is not None:
        macros["salt_g"] = sodium * SALT_PER_SODIUM

    micros = {
        nutrient_id: value * factor
        for nutrient_id, (off_field, factor) in MICRO_FIELDS.items()
        if (value := _num(n.get(off_field))) is not None
    }

    categories = product.get("categories_tags") or []
    brands = (product.get("brands") or "").split(",")[0].strip()
    name = (product.get("product_name_pl") or product.get("product_name") or "").strip()
    return FoodDraft(
        barcode=str(payload.get("code") or product.get("code") or ""),
        name=name or "(bez nazwy)",
        brand=brands or None,
        category=categories[-1] if categories else None,
        serving_g=_num(product.get("serving_quantity")),
        macros=macros,
        micros=micros,
        raw=product,
        unit=_detect_unit(product),
        source_updated_at=_timestamp(product.get("last_modified_t")),
    )


@dataclass(frozen=True)
class SearchHit:
    """Wynik wyszukiwania w OFF. Pełny produkt pobiera się potem po kodzie kreskowym."""

    barcode: str
    name: str
    brand: str | None
    kcal: float | None  # na 100 g lub 100 ml, tylko do podglądu na liście
    unit: str


SEARCH_FIELDS = "code,product_name,product_name_pl,brands,quantity,product_quantity_unit,nutriments"


def _first_text(value) -> str | None:
    """OFF podaje markę jako tekst albo listę; bierzemy pierwszą."""
    if isinstance(value, list):
        value = value[0] if value else None
    if not isinstance(value, str):
        return None
    return value.split(",")[0].strip() or None


def parse_search(payload: dict, is_valid_barcode) -> list[SearchHit]:
    """Zamienia odpowiedź search-a-licious na listę. Pomija wyniki bez nazwy i kodu."""
    hits = []
    for product in payload.get("hits") or []:
        code = str(product.get("code") or "")
        name = _first_text(product.get("product_name_pl")) or _first_text(
            product.get("product_name")
        )
        if not name or not is_valid_barcode(code):
            continue
        nutriments = product.get("nutriments") or {}
        kcal = _num(nutriments.get("energy-kcal_100g"))
        if kcal is None and (kj := _num(nutriments.get("energy_100g"))) is not None:
            kcal = kj / KJ_PER_KCAL
        hits.append(
            SearchHit(
                barcode=code,
                name=name,
                brand=_first_text(product.get("brands")),
                kcal=kcal,
                unit=_detect_unit(product),
            )
        )
    return hits


def search_products(
    query: str, base_url: str, user_agent: str, page_size: int = 20, timeout: float = 10.0
) -> dict:
    """Wyszukiwanie pełnotekstowe przez search-a-licious (https://search.openfoodfacts.org).

    Stare API v2 nie ma wyszukiwania po nazwie. Limit OFF: 10 wyszukiwań na minutę
    z jednego adresu, więc wywołuje się to na przycisk, nie przy każdym znaku.
    """
    response = httpx.get(
        f"{base_url}/search",
        params=[
            ("q", query),
            ("langs", "pl"),
            ("langs", "en"),
            ("page_size", str(page_size)),
            ("fields", SEARCH_FIELDS),
        ],
        headers={"User-Agent": user_agent},
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()


class RateLimiter:
    """Najwyżej `limit` zdarzeń w oknie `window_s` sekund (jeden proces serwera)."""

    def __init__(self, limit: int, window_s: float) -> None:
        self.limit, self.window_s = limit, window_s
        self.events: list[float] = []

    def allow(self, now: float) -> bool:
        self.events = [t for t in self.events if now - t < self.window_s]
        if len(self.events) >= self.limit:
            return False
        self.events.append(now)
        return True


# Zapas względem limitu OFF (10 na minutę): przekroczenie grozi blokadą adresu serwera.
search_limiter = RateLimiter(limit=8, window_s=60.0)


def fetch_product(
    barcode: str, base_url: str, user_agent: str, timeout: float = 10.0
) -> FoodDraft | None:
    """Pobiera produkt z OFF. 404 oznacza brak produktu; inne błędy sieci idą wyżej."""
    response = httpx.get(
        f"{base_url}/api/v2/product/{barcode}",
        params={"fields": FIELDS},
        headers={"User-Agent": user_agent},
        timeout=timeout,
    )
    if response.status_code == 404:
        return None
    response.raise_for_status()
    draft = parse_product(response.json())
    if draft and not draft.barcode:
        draft.barcode = barcode
    return draft
