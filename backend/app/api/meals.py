"""Zapisane posiłki (etap 1, krok 6): zestawy produktów dodawane jednym stuknięciem.

Dodanie zestawu do dnia to zwykłe wpisy dziennika (`PUT /api/diary/entries/{id}`),
po jednym na produkt. Dzięki temu działa bez sieci tak samo jak pojedynczy produkt,
a wartości zamrażają się we wpisach.
"""

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import require_user
from app.api.diet import Per100
from app.core.meals import meal_errors, meal_totals
from app.core.nutrients import MACRO_KEYS
from app.db import repo
from app.db.models import Food
from app.db.session import get_db

router = APIRouter(prefix="/api/meals", tags=["meals"], dependencies=[Depends(require_user)])


class MealItemIn(BaseModel):
    food_id: int
    amount: float


class MealIn(BaseModel):
    name: str = Field(max_length=200)
    items: list[MealItemIn] = Field(default_factory=list)
    # Zamiast `items`: wpisy dziennika, z których serwer bierze produkty i ilości (22.11.2026).
    # Telefon nie zna numeru produktu, który serwer założył dla szacunku AI.
    entry_ids: list[uuid.UUID] | None = None


class MealItemOut(BaseModel):
    food_id: int
    food_name: str
    amount: float
    unit: Literal["g", "ml"]
    # Wartości produktu na 100 g lub ml: telefon liczy z nich podgląd wpisu bez sieci.
    per_100: Per100


class MealOut(BaseModel):
    id: uuid.UUID
    name: str
    items: list[MealItemOut]
    totals: dict[str, float]  # według produktów na dziś


def _per_100(food: Food) -> dict[str, float | None]:
    return {key: getattr(food, key) for key in MACRO_KEYS}


@router.get("", response_model=list[MealOut])
def list_meals(db: Session = Depends(get_db)) -> list[MealOut]:
    out = []
    for meal, items in repo.list_meals(db):
        out.append(
            MealOut(
                id=meal.id,
                name=meal.name,
                items=[
                    MealItemOut(
                        food_id=food.id,
                        food_name=food.name,
                        amount=item.amount,
                        unit=food.unit or "g",
                        per_100=Per100(**_per_100(food)),
                    )
                    for item, food in items
                ],
                totals=meal_totals((_per_100(food), item.amount) for item, food in items),
            )
        )
    return out


@router.put("/{meal_id}", status_code=204)
def put_meal(meal_id: uuid.UUID, body: MealIn, db: Session = Depends(get_db)) -> Response:
    """Tworzy zestaw albo zastępuje jego nazwę i skład. Identyfikator nadaje telefon."""
    if body.entry_ids is not None:
        entries = {e.id: e for e in repo.meal_entries_by_ids(db, body.entry_ids)}
        if missing_entries := [str(i) for i in body.entry_ids if i not in entries]:
            raise HTTPException(404, f"Nie ma wpisów: {', '.join(missing_entries)}.")
        # W kolejności wybranej na telefonie; wpis bez produktu (przed migracją 0011) odpada.
        items = [
            (entries[i].food_id, entries[i].amount)
            for i in body.entry_ids
            if entries[i].food_id is not None
        ]
    else:
        items = [(item.food_id, item.amount) for item in body.items]
    if errors := meal_errors(body.name, items):
        raise HTTPException(422, " ".join(errors))
    known = {food.id for food in repo.foods_by_ids(db, [food_id for food_id, _ in items])}
    if missing := sorted({food_id for food_id, _ in items} - known):
        raise HTTPException(404, f"Nie ma produktów: {', '.join(map(str, missing))}.")
    repo.save_meal(db, meal_id, body.name.strip(), items)
    return Response(status_code=204)


@router.delete("/{meal_id}", status_code=204)
def delete_meal(meal_id: uuid.UUID, db: Session = Depends(get_db)) -> Response:
    """Idempotentne. Wpisy dodane wcześniej z zestawu zostają w dzienniku."""
    repo.delete_meal(db, meal_id)
    return Response(status_code=204)
