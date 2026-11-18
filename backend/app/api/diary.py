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
from app.core.micros import clean_micros
from app.core.nutrients import MACRO_KEYS, macro_errors
from app.core.week import average, micro_week
from app.core.week import day_totals as day_totals_range
from app.db import repo
from app.db.models import AiRun, Food, MealEntry
from app.db.session import get_db

router = APIRouter(prefix="/api/diary", tags=["diary"], dependencies=[Depends(require_user)])

MealSlot = Literal["breakfast", "second_breakfast", "lunch", "snack", "dinner"]
assert MealSlot.__args__ == MEAL_SLOTS  # jedna lista posiłków w core/diary.py


class EstimateIn(BaseModel):
    """Składnik ze zdjęcia lub opisu, którego nie ma w bazie: szacunek modelu na 100 g."""

    name: str = Field(min_length=1, max_length=120)
    per_100: MacroValues
    # Szacunek mikroskładników na 100 g ({id: ilość}); bez danych: pusty słownik.
    micros_per_100: dict[str, float] = Field(default_factory=dict)


class EntryIn(BaseModel):
    date: dt.date
    meal_slot: MealSlot
    food_id: int | None = None  # None tylko dla składnika z AI bez produktu w bazie
    estimate: EstimateIn | None = None
    amount: float = Field(gt=0, le=5000)  # gramy albo mililitry, zależnie od produktu
    # meal: dodany z zapisanego posiłku (krok 6); photo/text: ze szkicu AI (etap 2)
    source: Literal["scan", "search", "photo", "text", "manual", "meal"] = "scan"
    ai_run_id: int | None = None  # wywołanie modelu, z którego pochodzi wpis


class EntryOut(BaseModel):
    id: uuid.UUID
    date: dt.date
    meal_slot: MealSlot
    food_id: int | None
    food_name: str
    amount: float
    unit: Literal["g", "ml"]
    values: MacroValues  # wartości dla tej porcji, zamrożone w chwili dodania
    macro_source: str | None  # estimated = szacunek modelu; inaczej źródło produktu
    source: str
    ai_run_id: int | None
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
        macro_source=entry.macro_source,
        source=entry.source,
        ai_run_id=entry.ai_run_id,
        created_at=entry.created_at,
    )


def _known_run(db: Session, run_id: int | None) -> int | None:
    """Powiązanie z wywołaniem modelu tylko, gdy takie wywołanie istnieje."""
    return run_id if run_id is not None and db.get(AiRun, run_id) is not None else None


def _estimate(body: EntryIn) -> EstimateIn:
    """Szacunek dla wpisu bez produktu. Tylko wpisy ze zdjęcia lub opisu mogą go mieć."""
    if body.estimate is None or body.source not in ("photo", "text"):
        raise HTTPException(
            422, "Wpis bez produktu musi mieć szacunek wartości i pochodzić ze zdjęcia lub opisu."
        )
    errors = macro_errors(body.estimate.per_100.model_dump())
    if errors:
        raise HTTPException(422, " ".join(errors))
    return body.estimate


@router.put("/entries/{entry_id}", response_model=EntryOut)
def put_entry(entry_id: uuid.UUID, body: EntryIn, db: Session = Depends(get_db)) -> EntryOut:
    """Dodaje wpis albo zmienia jego ilość, posiłek lub dzień.

    Idempotentne: identyfikator nadaje telefon, więc powtórka z kolejki offline niczego
    nie dubluje. Wartości odżywcze są zamrażane przy dodaniu. Przy zmianie ilości są
    skalowane, a nie pobierane ponownie z produktu.
    """
    entry = db.get(MealEntry, entry_id)
    if entry is not None and entry.food_id == body.food_id:
        # Zmiana ilości lub posiłku: zamrożone wartości są skalowane (także szacunek modelu).
        values, micros = scale_portion(_values(entry), entry.micros, body.amount / entry.amount)
        food_name, unit, macro_source = entry.food_name, entry.unit, entry.macro_source
    elif body.food_id is None:
        # Szacunek modelu: bez mikroskładników, wartości oznaczone jako `estimated`.
        estimate = _estimate(body)
        micros_per_100 = {
            nutrient_id: (amount, "estimated")
            for nutrient_id, amount in clean_micros(estimate.micros_per_100).items()
        }
        values, micros = freeze_portion(estimate.per_100.model_dump(), micros_per_100, body.amount)
        food_name, unit, macro_source = estimate.name.strip(), "g", "estimated"
    else:
        food = db.get(Food, body.food_id)
        if food is None:
            raise HTTPException(404, "Nie ma takiego produktu.")
        per_100 = {key: getattr(food, key) for key in MACRO_KEYS}
        micros_per_100 = {
            m.nutrient_id: (m.amount_per_100g, m.source) for m in repo.food_micros(db, food.id)
        }
        values, micros = freeze_portion(per_100, micros_per_100, body.amount)
        food_name, unit, macro_source = food.name, food.unit or "g", food.macro_source

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
        macro_source=macro_source,
        source=body.source,
        ai_run_id=entry.ai_run_id if entry is not None else _known_run(db, body.ai_run_id),
        **values,
    )
    return _entry_out(entry)


@router.delete("/entries/{entry_id}", status_code=204)
def delete_entry(entry_id: uuid.UUID, db: Session = Depends(get_db)) -> Response:
    """Idempotentne: usunięcie wpisu, którego już nie ma, też kończy się powodzeniem."""
    repo.delete_meal_entry(db, entry_id)
    return Response(status_code=204)


# ---------- tydzień (etap 6) ----------


class DayTotalOut(BaseModel):
    date: dt.date
    entries: int
    totals: dict[str, float]


class MicroWeekOut(BaseModel):
    nutrient_id: str
    name_pl: str
    unit: str
    group: str  # vitamin | mineral
    rda: float | None
    avg_amount: float
    percent_rda: float | None
    share_trusted: float
    share_estimated: float
    share_missing: float


class WeekOut(BaseModel):
    start: dt.date
    end: dt.date
    days: list[DayTotalOut]
    logged_days: int
    average: dict[str, float] | None  # średnia z dni z wpisami
    micros: list[MicroWeekOut]


WEEK_DAYS = 7


@router.get("/week/{end}", response_model=WeekOut)
def get_week(end: dt.date, db: Session = Depends(get_db)) -> WeekOut:
    """Ostatnie 7 dni do `end` włącznie: sumy dni, średnia i pokrycie norm mikroskładników."""
    start = end - dt.timedelta(days=WEEK_DAYS - 1)
    entries = repo.meal_entries_between(db, start, end)
    days = day_totals_range(
        [start + dt.timedelta(days=i) for i in range(WEEK_DAYS)],
        ({"date": e.date, **_values(e)} for e in entries),
    )
    logged = sum(1 for d in days if d.entries > 0)
    dictionary = {n.id: n for n in repo.nutrients(db)}
    coverage = micro_week(
        ({"kcal": e.kcal, "micros": e.micros} for e in entries),
        {nid: n.rda for nid, n in dictionary.items()},
        logged,
    )
    return WeekOut(
        start=start,
        end=end,
        days=[DayTotalOut(**vars(d)) for d in days],
        logged_days=logged,
        average=average(days),
        micros=[
            MicroWeekOut(
                **vars(c),
                name_pl=dictionary[c.nutrient_id].name_pl,
                unit=dictionary[c.nutrient_id].unit,
                group=dictionary[c.nutrient_id].grp,
                rda=dictionary[c.nutrient_id].rda,
            )
            for c in coverage
        ],
    )


@router.get("/{day}", response_model=DayOut)
def get_day(day: dt.date, db: Session = Depends(get_db)) -> DayOut:
    entries = repo.meal_entries_for_day(db, day)
    sums = day_totals({"meal_slot": e.meal_slot, **_values(e)} for e in entries)
    order = {slot: i for i, slot in enumerate(MEAL_SLOTS)}
    entries.sort(key=lambda e: order.get(e.meal_slot, len(order)))  # stabilne: w posiłku wg czasu
    return DayOut(date=day, entries=[_entry_out(e) for e in entries], **sums)
