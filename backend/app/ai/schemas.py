"""Kontrakty odpowiedzi modeli (dokumentacja 7).

Model nigdy nie zwraca identyfikatorów z naszej bazy: opisuje składnik, a dopasowanie
do `food` robi backend (pg_trgm). Kategoria jest listą zamkniętą wymuszoną schematem.
"""

from enum import StrEnum

from pydantic import BaseModel, Field


class FoodCategory(StrEnum):
    MEAT = "meat"
    FISH = "fish"
    EGGS = "eggs"
    DAIRY = "dairy"
    GRAINS = "grains"
    BREAD = "bread"
    LEGUMES = "legumes"
    VEGETABLES = "vegetables"
    FRUIT = "fruit"
    NUTS_SEEDS = "nuts_seeds"
    FATS_OILS = "fats_oils"
    SWEETS = "sweets"
    DRINKS = "drinks"
    SAUCES = "sauces"
    MIXED_DISH = "mixed_dish"
    OTHER = "other"


class Confidence(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Per100gEstimate(BaseModel):
    """Typowe wartości na 100 g z wiedzy modelu (nie liczone). Zapas, gdy produktu nie ma w bazie.

    Bez ograniczeń w schemacie: zakresy sprawdza `core/meal_draft.py`, a słowa kluczowe
    w rodzaju `minimum` komplikują schemat wysyłany do dostawcy.
    """

    kcal: float = Field(description="kcal na 100 g")
    protein_g: float = Field(description="białko, g na 100 g")
    fat_g: float = Field(description="tłuszcz, g na 100 g")
    sat_fat_g: float | None = Field(description="w tym kwasy nasycone, g na 100 g")
    carbs_g: float = Field(description="węglowodany, g na 100 g")
    sugars_g: float | None = Field(description="w tym cukry, g na 100 g")
    fiber_g: float | None = Field(description="błonnik, g na 100 g")
    salt_g: float | None = Field(
        description="sól, g na 100 g, razem z solą zwykle dodawaną przy przyrządzaniu"
    )


class MicroEstimate(BaseModel):
    """Typowe mikroskładniki na 100 g (jak w tabelach składu). Zapas, gdy nie ma tabeli.

    null = model nie zna wartości. Zakresy sprawdza `core/micros.py`.
    """

    vit_a: float | None = Field(description="witamina A (RAE), µg na 100 g")
    vit_d: float | None = Field(description="witamina D, µg na 100 g")
    vit_e: float | None = Field(description="witamina E, mg na 100 g")
    vit_k: float | None = Field(description="witamina K, µg na 100 g")
    vit_c: float | None = Field(description="witamina C, mg na 100 g")
    vit_b1: float | None = Field(description="tiamina B1, mg na 100 g")
    vit_b2: float | None = Field(description="ryboflawina B2, mg na 100 g")
    vit_b3: float | None = Field(description="niacyna B3, mg na 100 g")
    vit_b6: float | None = Field(description="witamina B6, mg na 100 g")
    folate: float | None = Field(description="foliany (DFE), µg na 100 g")
    vit_b12: float | None = Field(description="witamina B12, µg na 100 g")
    calcium: float | None = Field(description="wapń, mg na 100 g")
    iron: float | None = Field(description="żelazo, mg na 100 g")
    magnesium: float | None = Field(description="magnez, mg na 100 g")
    zinc: float | None = Field(description="cynk, mg na 100 g")
    potassium: float | None = Field(description="potas, mg na 100 g")
    sodium: float | None = Field(description="sód, mg na 100 g")
    phosphorus: float | None = Field(description="fosfor, mg na 100 g")
    selenium: float | None = Field(description="selen, µg na 100 g")
    iodine: float | None = Field(description="jod, µg na 100 g")


class MealItem(BaseModel):
    name_pl: str = Field(description="Nazwa składnika po polsku, np. „ryż biały gotowany”.")
    name_en: str = Field(description="Ta sama nazwa po angielsku.")
    category: FoodCategory
    grams: float = Field(description="Najbardziej prawdopodobna ilość w gramach.")
    grams_low: float = Field(description="Dolna granica ilości w gramach.")
    grams_high: float = Field(description="Górna granica ilości w gramach.")
    per_100g_estimate: Per100gEstimate
    micros_per_100g: MicroEstimate
    confidence: Confidence = Field(description="Pewność rozpoznania składnika i ilości.")


class MealEstimate(BaseModel):
    """Zdjęcie lub opis posiłku -> składniki z gramaturą. Kalorie liczy backend."""

    items: list[MealItem]
    notes: str | None = Field(
        description="Krótka uwaga, czego nie widać lub co jest niepewne; null, gdy nic."
    )


class LabelBasis(StrEnum):
    PER_100G = "100g"
    PER_100ML = "100ml"
    OTHER = "other"


class LabelExtract(BaseModel):
    """Zdjęcie etykiety -> przepisana tabela wartości odżywczych.

    Pola są wymagane, ale mogą być puste: model ma jawnie napisać `null`, gdy etykieta
    czegoś nie podaje. Model niczego nie przelicza. Zakresy i spójność sprawdza
    `core/label.py`.
    """

    name: str | None = Field(description="Nazwa produktu z opakowania; null, gdy jej nie widać.")
    brand: str | None = Field(description="Marka albo producent; null, gdy jej nie widać.")
    basis: LabelBasis = Field(
        description=(
            "Której kolumny tabeli dotyczą przepisane wartości: '100g' (na 100 g), "
            "'100ml' (na 100 ml), 'other' gdy tabela nie ma żadnej z nich."
        )
    )
    serving_g: float | None = Field(
        description="Wielkość porcji w g albo ml, jeśli etykieta ją podaje; inaczej null."
    )
    kcal: float | None = Field(description="Wartość energetyczna w kcal (nie w kJ).")
    fat_g: float | None = Field(description="Tłuszcz, g.")
    sat_fat_g: float | None = Field(description="W tym kwasy tłuszczowe nasycone, g.")
    carbs_g: float | None = Field(description="Węglowodany, g.")
    sugars_g: float | None = Field(description="W tym cukry, g.")
    fiber_g: float | None = Field(description="Błonnik, g.")
    protein_g: float | None = Field(description="Białko, g.")
    salt_g: float | None = Field(description="Sól, g.")


class FoodQuery(BaseModel):
    """Nazwa produktu po angielsku w stylu bazy USDA, do wyszukania w tabeli."""

    query_en: str = Field(
        description="Zapytanie po angielsku w stylu USDA FoodData Central, np. 'Oats, rolled'."
    )
