"""Dieta. Etap 0: produkt po kodzie kreskowym (własna baza -> Open Food Facts)."""

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import OffFetcher, get_off_fetcher, require_user
from app.core.barcode import is_valid_ean
from app.core.nutrients import MACRO_KEYS
from app.db import repo
from app.db.models import Food
from app.db.session import get_db

router = APIRouter(prefix="/api/foods", tags=["diet"], dependencies=[Depends(require_user)])


class MicroOut(BaseModel):
    nutrient_id: str
    amount_per_100g: float
    source: str


class FoodOut(BaseModel):
    id: int
    barcode: str | None
    name: str
    brand: str | None
    serving_g: float | None
    origin: str
    macro_source: str
    per_100g: dict[str, float | None]
    micros: list[MicroOut]
    cached: bool


def _food_out(db: Session, food: Food, cached: bool) -> FoodOut:
    return FoodOut(
        id=food.id,
        barcode=food.barcode,
        name=food.name,
        brand=food.brand,
        serving_g=food.serving_g,
        origin=food.origin,
        macro_source=food.macro_source,
        per_100g={key: getattr(food, key) for key in MACRO_KEYS},
        micros=[
            MicroOut(nutrient_id=m.nutrient_id, amount_per_100g=m.amount_per_100g, source=m.source)
            for m in repo.food_micros(db, food.id)
        ],
        cached=cached,
    )


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
