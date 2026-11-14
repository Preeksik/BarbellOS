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
    kcal: float = Field(ge=0)
    protein_g: float = Field(ge=0)
    fat_g: float = Field(ge=0)
    carbs_g: float = Field(ge=0)


class MealItem(BaseModel):
    name_pl: str
    name_en: str
    category: FoodCategory
    grams: float = Field(gt=0)
    grams_range: tuple[float, float]
    per_100g_estimate: Per100gEstimate
    confidence: Confidence


class MealEstimate(BaseModel):
    """Zdjęcie lub opis posiłku -> składniki z gramaturą. Kalorie liczy backend."""

    items: list[MealItem]
    notes: str | None = None


class LabelExtract(BaseModel):
    """Zdjęcie etykiety -> wartości na 100 g. Pole puste, gdy etykieta go nie podaje."""

    name: str | None = None
    brand: str | None = None
    serving_g: float | None = None
    kcal: float | None = None
    protein_g: float | None = None
    fat_g: float | None = None
    sat_fat_g: float | None = None
    carbs_g: float | None = None
    sugars_g: float | None = None
    fiber_g: float | None = None
    salt_g: float | None = None
