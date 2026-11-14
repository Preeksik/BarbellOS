"""Klient Open Food Facts: pobranie produktu po kodzie kreskowym i mapowanie pól.

Zapytania idą z backendu (nie z przeglądarki), bo OFF prosi o nagłówek User-Agent
identyfikujący aplikację, a wynik zapisujemy we własnej bazie.

[DO WERYFIKACJI w próbie C] Mapowanie mikroskładników zakłada, że OFF podaje pola
`*_100g` w gramach. Próba C porównuje kilka produktów z etykietą.
"""

from dataclasses import dataclass, field

import httpx

FIELDS = (
    "code,product_name,product_name_pl,brands,quantity,serving_quantity,nutriments,categories_tags"
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


def _num(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


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
    )


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
