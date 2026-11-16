"""Dziennik dnia: wpisy posiłków i sumy."""

import datetime as dt
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import require_user
from app.api.diet import Per100 as MacroValues
from app.core.diary import MEAL_SLOTS, day_totals, freeze_portion, scale_portion
from app.core.nutrients import MACRO_KEYS
from app.db import repo
from app.db.models import Food, MealEntry
from app.db.session import get_db

router = APIRouter(prefix="/api/diary", tags=["diary"], dependencies=[Depends(require_user)])

MealSlot = Literal["breakfast", "second_breakfast", "lunch", "snack", "dinner"]
assert MealSlot.__args__ == MEAL_SLOTS  # jedna lista posiłków w core/diary.py


class EntryIn(BaseModel):
    date: dt.date
    meal_slot: MealSlot
    food_id: int
    amount: float = Field(gt=0, le=5000)  # gramy albo mililitry, zależnie od produktu
    source: Literal["scan", "search", "photo", "text", "manual"] = "scan"


class EntryOut(BaseModel):
    id: uuid.UUID
    date: dt.date
    meal_slot: MealSlot
    food_id: int | None
    food_name: str
    amount: float
    unit: Literal["g", "ml"]
    values: MacroValues  # wartości dla tej porcji, zamrożone w chwili dodania
    source: str
    created_at: dt.datetime


class DayOut(BaseModel):
    date: dt.date
    entries: list[EntryOut]
    totals: dict[str, float]
    by_slot: dict[str, dict[str, float]]


def _values(entry: MealEntry) -> dict[str, float | None]:
    return {key: getattr(entry, key) for key in MACRO_KEYS}


def _entry_out(entry: MealEntry) -> EntryOut:
    return EntryOut(
        id=entry.id,
        date=entry.date,
        meal_slot=entry.meal_slot,
        food_id=entry.food_id,
        food_name=entry.food_name,
        amount=entry.amount,
        unit=entry.unit or "g",
        values=MacroValues(**_values(entry)),
        source=entry.source,
        created_at=entry.created_at,
    )


@router.put("/entries/{entry_id}", response_model=EntryOut)
def put_entry(entry_id: uuid.UUID, body: EntryIn, db: Session = Depends(get_db)) -> EntryOut:
    """Dodaje wpis albo zmienia jego ilość, posiłek lub dzień.

    Idempotentne: identyfikator nadaje telefon, więc powtórka z kolejki offline niczego
    nie dubluje. Wartości odżywcze są zamrażane przy dodaniu. Przy zmianie ilości są
    skalowane, a nie pobierane ponownie z produktu.
    """
    entry = db.get(MealEntry, entry_id)
    if entry is not None and entry.food_id == body.food_id:
        values, micros = scale_portion(_values(entry), entry.micros, body.amount / entry.amount)
        food_name, unit = entry.food_name, entry.unit
    else:
        food = db.get(Food, body.food_id)
        if food is None:
            raise HTTPException(404, "Nie ma takiego produktu.")
        per_100 = {key: getattr(food, key) for key in MACRO_KEYS}
        micros_per_100 = {
            m.nutrient_id: (m.amount_per_100g, m.source) for m in repo.food_micros(db, food.id)
        }
        values, micros = freeze_portion(per_100, micros_per_100, body.amount)
        food_name, unit = food.name, food.unit or "g"

    entry = repo.save_meal_entry(
        db,
        entry,
        entry_id,
        date=body.date,
        meal_slot=body.meal_slot,
        food_id=body.food_id,
        food_name=food_name,
        amount=body.amount,
        unit=unit,
        micros=micros,
        source=body.source,
        **values,
    )
    return _entry_out(entry)


@router.delete("/entries/{entry_id}", status_code=204)
def delete_entry(entry_id: uuid.UUID, db: Session = Depends(get_db)) -> Response:
    """Idempotentne: usunięcie wpisu, którego już nie ma, też kończy się powodzeniem."""
    repo.delete_meal_entry(db, entry_id)
    return Response(status_code=204)


@router.get("/{day}", response_model=DayOut)
def get_day(day: dt.date, db: Session = Depends(get_db)) -> DayOut:
    entries = repo.meal_entries_for_day(db, day)
    sums = day_totals({"meal_slot": e.meal_slot, **_values(e)} for e in entries)
    order = {slot: i for i, slot in enumerate(MEAL_SLOTS)}
    entries.sort(key=lambda e: order.get(e.meal_slot, len(order)))  # stabilne: w posiłku wg czasu
    return DayOut(date=day, entries=[_entry_out(e) for e in entries], **sums)
