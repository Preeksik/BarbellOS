"""Dieta: produkt po kodzie kreskowym, poprawianie wartości i weryfikacja z etykietą."""

from datetime import datetime
from typing import Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.api.deps import OffFetcher, get_off_fetcher, require_user
from app.core.barcode import is_valid_ean
from app.core.nutrients import MACRO_KEYS, macro_errors, macro_warnings
from app.db import repo
from app.db.models import Food
from app.db.session import get_db

router = APIRouter(prefix="/api/foods", tags=["diet"], dependencies=[Depends(require_user)])


class MicroOut(BaseModel):
    nutrient_id: str
    amount_per_100g: float
    source: str


class Per100(BaseModel):
    """Osiem wartości z etykiety na 100 g lub 100 ml. Puste pole to brak danych, nie zero."""

    kcal: float | None = None
    protein_g: float | None = None
    fat_g: float | None = None
    sat_fat_g: float | None = None
    carbs_g: float | None = None
    sugars_g: float | None = None
    fiber_g: float | None = None
    salt_g: float | None = None


class FoodOut(BaseModel):
    id: int
    barcode: str | None
    name: str
    brand: str | None
    serving_g: float | None
    unit: Literal["g", "ml"]
    origin: str
    macro_source: str
    source_updated_at: datetime | None
    verified_at: datetime | None
    per_100: Per100
    micros: list[MicroOut]
    warnings: list[str]
    cached: bool


class FoodUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    brand: str | None = Field(default=None, max_length=255)
    serving_g: float | None = Field(default=None, gt=0, le=5000)
    unit: Literal["g", "ml"] = "g"
    per_100: Per100

    @field_validator("name", "brand")
    @classmethod
    def _strip(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


def _food_out(db: Session, food: Food, cached: bool) -> FoodOut:
    macros = {key: getattr(food, key) for key in MACRO_KEYS}
    return FoodOut(
        id=food.id,
        barcode=food.barcode,
        name=food.name,
        brand=food.brand,
        serving_g=food.serving_g,
        unit=food.unit or "g",
        origin=food.origin,
        macro_source=food.macro_source,
        source_updated_at=food.source_updated_at,
        verified_at=food.verified_at,
        per_100=Per100(**macros),
        micros=[
            MicroOut(nutrient_id=m.nutrient_id, amount_per_100g=m.amount_per_100g, source=m.source)
            for m in repo.food_micros(db, food.id)
        ],
        warnings=macro_warnings(macros),
        cached=cached,
    )


def _get_food(db: Session, food_id: int) -> Food:
    food = db.get(Food, food_id)
    if food is None:
        raise HTTPException(404, "Nie ma takiego produktu.")
    return food


@router.get("/barcode/{barcode}", response_model=FoodOut)
def by_barcode(
    barcode: str,
    db: Session = Depends(get_db),
    fetch: OffFetcher = Depends(get_off_fetcher),
) -> FoodOut:
    if not is_valid_ean(barcode):
        raise HTTPException(422, "Nieprawidłowy kod kreskowy.")
    if food := repo.find_food_by_barcode(db, barcode):
        return _food_out(db, food, cached=True)
    try:
        draft = fetch(barcode)
    except httpx.HTTPError as exc:
        raise HTTPException(502, "Open Food Facts nie odpowiada. Spróbuj ponownie.") from exc
    if draft is None:
        raise HTTPException(404, "Produktu nie ma w Open Food Facts.")
    draft.barcode = barcode
    return _food_out(db, repo.save_food_draft(db, draft), cached=False)


@router.put("/{food_id}", response_model=FoodOut)
def update_food(food_id: int, body: FoodUpdate, db: Session = Depends(get_db)) -> FoodOut:
    """Poprawka wartości według etykiety. Idempotentne: ten sam zapis można wysłać ponownie."""
    food = _get_food(db, food_id)
    if body.name is None:
        raise HTTPException(422, "Nazwa nie może być pusta.")
    macros = body.per_100.model_dump()
    if errors := macro_errors(macros, body.unit):
        raise HTTPException(422, " ".join(errors))
    repo.update_food(db, food, body.name, body.brand, body.serving_g, body.unit, macros)
    return _food_out(db, food, cached=True)


@router.post("/{food_id}/verify", response_model=FoodOut)
def verify_food(food_id: int, db: Session = Depends(get_db)) -> FoodOut:
    """Wartości zgadzają się z etykietą: produkt zostaje oznaczony jako zweryfikowany."""
    food = _get_food(db, food_id)
    return _food_out(db, repo.mark_food_verified(db, food), cached=True)
