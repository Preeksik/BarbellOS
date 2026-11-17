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
    carbs_g: float = Field(description="węglowodany, g na 100 g")


class MealItem(BaseModel):
    name_pl: str = Field(description="Nazwa składnika po polsku, np. „ryż biały gotowany”.")
    name_en: str = Field(description="Ta sama nazwa po angielsku.")
    category: FoodCategory
    grams: float = Field(description="Najbardziej prawdopodobna ilość w gramach.")
    grams_low: float = Field(description="Dolna granica ilości w gramach.")
    grams_high: float = Field(description="Górna granica ilości w gramach.")
    per_100g_estimate: Per100gEstimate
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
