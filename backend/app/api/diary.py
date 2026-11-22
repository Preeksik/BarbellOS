"""Dziennik dnia: wpisy posiłków i sumy."""

import datetime as dt
import logging
import uuid
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, sessionmaker

from app.ai.router import AiRouter
from app.api.deps import get_ai_router, get_fdc_client, require_user
from app.api.diet import Per100 as MacroValues
from app.config import Settings, get_settings
from app.core.diary import (
    MEAL_SLOTS,
    RECENT_MEALS_LIMIT,
    day_totals,
    freeze_portion,
    month_days,
    recent_meals,
    scale_portion,
)
from app.core.micros import clean_micros
from app.core.nutrients import MACRO_KEYS, macro_errors
from app.core.week import MIN_MICROS, average, micro_gaps, micro_week
from app.core.week import day_totals as day_totals_range
from app.db import repo
from app.db.models import AiRun, Food, MealEntry
from app.db.session import get_db, get_session_factory
from app.fdc.client import FdcClient
from app.services import micros_fill

router = APIRouter(prefix="/api/diary", tags=["diary"], dependencies=[Depends(require_user)])
log = logging.getLogger(__name__)

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
    food_id: int | None = None  # None dla składnika z AI (produkt zakłada serwer) i kopii
    estimate: EstimateIn | None = None
    # Kopia wpisu z innego dnia lub posiłku (22.11.2026): wartości przenoszone z tego wpisu.
    copy_of: uuid.UUID | None = None
    amount: float = Field(gt=0, le=5000)  # gramy albo mililitry, zależnie od produktu
    # meal: dodany z zapisanego posiłku (krok 6); photo/text: ze szkicu AI (etap 2);
    # copy: skopiowany z poprzedniego posiłku
    source: Literal["scan", "search", "photo", "text", "manual", "meal", "copy"] = "scan"
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
def put_entry(
    entry_id: uuid.UUID,
    body: EntryIn,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    fdc: FdcClient = Depends(get_fdc_client),
    ai: AiRouter = Depends(get_ai_router),
    sessions: sessionmaker = Depends(get_session_factory),
) -> EntryOut:
    """Dodaje wpis albo zmienia jego ilość, posiłek lub dzień.

    Idempotentne: identyfikator nadaje telefon, więc powtórka z kolejki offline niczego
    nie dubluje. Wartości odżywcze są zamrażane przy dodaniu. Przy zmianie ilości są
    skalowane, a nie pobierane ponownie z produktu.
    """
    entry = db.get(MealEntry, entry_id)
    food_id = body.food_id
    if entry is not None and (body.food_id is None or entry.food_id == body.food_id):
        # Zmiana ilości lub posiłku: zamrożone wartości są skalowane (także szacunek modelu).
        # Telefon może nie znać produktu, który serwer założył dla szacunku (food_id None).
        values, micros = scale_portion(_values(entry), entry.micros, body.amount / entry.amount)
        food_name, unit, macro_source = entry.food_name, entry.unit, entry.macro_source
        food_id = entry.food_id
    elif body.food_id is None and body.copy_of is not None:
        # Kopia wpisu: te same zamrożone wartości (przeskalowane do ilości), ten sam produkt.
        original = db.get(MealEntry, body.copy_of)
        if original is None:
            raise HTTPException(404, "Kopiowany wpis już nie istnieje.")
        values, micros = scale_portion(
            _values(original), original.micros, body.amount / original.amount
        )
        food_name, unit, macro_source = original.food_name, original.unit, original.macro_source
        food_id = original.food_id
    elif body.food_id is None:
        # Szacunek modelu: wartości oznaczone jako `estimated`. Od 22.11.2026 serwer zakłada
        # z niego produkt, żeby dało się go zapisać w posiłku, wyszukać i dodać ponownie.
        estimate = _estimate(body)
        micros_per_100 = {
            nutrient_id: (amount, "estimated")
            for nutrient_id, amount in clean_micros(estimate.micros_per_100).items()
        }
        per_100 = estimate.per_100.model_dump()
        values, micros = freeze_portion(per_100, micros_per_100, body.amount)
        food_name, unit, macro_source = estimate.name.strip(), "g", "estimated"
        food_id = repo.food_from_estimate(db, food_name, per_100, micros_per_100).id
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
        food_id=food_id,
        food_name=food_name,
        amount=body.amount,
        unit=unit,
        micros=micros,
        macro_source=macro_source,
        source=body.source,
        ai_run_id=entry.ai_run_id if entry is not None else _known_run(db, body.ai_run_id),
        **values,
    )
    if settings.micros_autofill and entry.food_id is not None and not entry.micros:
        # Witaminy z tabeli USDA w tle: odpowiedź nie czeka na USDA ani na model.
        background.add_task(_autofill_in_background, sessions, entry.food_id, fdc, ai)
    return _entry_out(entry)


def _autofill_in_background(
    sessions: sessionmaker, food_id: int, fdc: FdcClient, ai: AiRouter
) -> None:
    """Uzupełnianie po odpowiedzi. Błąd nie może zepsuć dziennika: tylko trafia do logu."""
    try:
        with sessions() as db:
            food = db.get(Food, food_id)
            if food is not None:
                micros_fill.auto_fill(db, food, fdc, ai)
    except Exception:  # noqa: BLE001 - zadanie w tle: zapis wpisu już się udał
        log.exception("Uzupełnianie witamin w tle nieudane (produkt %s)", food_id)


@router.delete("/entries/{entry_id}", status_code=204)
def delete_entry(entry_id: uuid.UUID, db: Session = Depends(get_db)) -> Response:
    """Idempotentne: usunięcie wpisu, którego już nie ma, też kończy się powodzeniem."""
    repo.delete_meal_entry(db, entry_id)
    return Response(status_code=204)


# ---------- poprzednie posiłki (22.11.2026) ----------

RECENT_DAYS = 14


class RecentMealOut(BaseModel):
    date: dt.date
    meal_slot: MealSlot
    kcal: float
    entries: list[EntryOut]


@router.get("/recent-meals/{day}", response_model=list[RecentMealOut])
def get_recent_meals(day: dt.date, db: Session = Depends(get_db)) -> list[RecentMealOut]:
    """Posiłki z ostatnich dwóch tygodni do `day` włącznie, do skopiowania jednym stuknięciem."""
    entries = repo.meal_entries_between(db, day - dt.timedelta(days=RECENT_DAYS - 1), day)
    rows = [{"date": e.date, "meal_slot": e.meal_slot, **_values(e)} for e in entries]
    meals = []
    # Jeden więcej: telefon pomija posiłek, do którego właśnie dodaje.
    for date, slot, indices in recent_meals(rows, limit=RECENT_MEALS_LIMIT + 1):
        group = [entries[i] for i in indices]
        meals.append(
            RecentMealOut(
                date=date,
                meal_slot=slot,
                kcal=day_totals(rows[i] for i in indices)["totals"]["kcal"],
                entries=[_entry_out(e) for e in group],
            )
        )
    return meals


class MonthDayOut(BaseModel):
    date: dt.date
    entries: int
    kcal: float


@router.get("/month/{month}", response_model=list[MonthDayOut])
def get_month(month: str, db: Session = Depends(get_db)) -> list[MonthDayOut]:
    """Dni miesiąca („RRRR-MM") z wpisami: kropki w kalendarzu kopiowania posiłku."""
    try:
        days = month_days(month)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    entries = repo.meal_entries_between(db, days[0], days[-1])
    totals = day_totals_range(days, ({"date": e.date, **_values(e)} for e in entries))
    return [
        MonthDayOut(date=d.date, entries=d.entries, kcal=d.totals["kcal"])
        for d in totals
        if d.entries > 0
    ]


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


class GapOut(BaseModel):
    food_id: int
    name: str
    brand: str | None
    kcal: float
    share: float  # udział w kaloriach tygodnia
    entries: int
    # Produkt ma już mikroskładniki (np. dopasowany do tabeli): wystarczy uzupełnić wpisy.
    has_micros: bool
    checked: bool  # automat już szukał produktu w tabeli (bez pewnego wyniku: wybór ręczny)


class GapsOut(BaseModel):
    foods: list[GapOut]
    share_without_food: float  # wpisy bez produktu (szacunki AI sprzed 18.11.2026)


@router.get("/week/{end}/gaps", response_model=GapsOut)
def get_week_gaps(end: dt.date, db: Session = Depends(get_db)) -> GapsOut:
    """Produkty z tygodnia bez danych o witaminach: lista do uzupełnienia z tabeli USDA."""
    start = end - dt.timedelta(days=WEEK_DAYS - 1)
    entries = repo.meal_entries_between(db, start, end)
    gaps, orphan = micro_gaps(
        {"food_id": e.food_id, "kcal": e.kcal, "micros": e.micros} for e in entries
    )
    foods = {f.id: f for f in repo.foods_by_ids(db, [g.food_id for g in gaps])}
    return GapsOut(
        foods=[
            GapOut(
                food_id=g.food_id,
                name=foods[g.food_id].name,
                brand=foods[g.food_id].brand,
                kcal=g.kcal,
                share=g.share,
                entries=g.entries,
                has_micros=len(repo.food_micros(db, g.food_id)) >= MIN_MICROS,
                checked=foods[g.food_id].fdc_checked_at is not None,
            )
            for g in gaps
            if g.food_id in foods
        ],
        share_without_food=orphan,
    )


class AutofillOut(BaseModel):
    filled: list[str]  # dopasowane teraz do tabeli
    completed: list[str]  # produkty z danymi: uzupełniono tylko wpisy
    no_match: list[str]  # bez pewnego dopasowania: wybór ręczny w karcie produktu
    postponed: list[str]  # sieć albo limit: kolejna próba przy następnym otwarciu


@router.post("/week/{end}/autofill", response_model=AutofillOut)
def autofill_week(
    end: dt.date,
    db: Session = Depends(get_db),
    fdc: FdcClient = Depends(get_fdc_client),
    ai: AiRouter = Depends(get_ai_router),
) -> AutofillOut:
    """Uzupełnia witaminy produktów z tygodnia bez danych (decyzja właściciela z 18.11.2026).

    Idempotentne: produkt sprawdzony bez wyniku nie jest wyszukiwany ponownie.
    """
    start = end - dt.timedelta(days=WEEK_DAYS - 1)
    entries = repo.meal_entries_between(db, start, end)
    gaps, _ = micro_gaps(
        {"food_id": e.food_id, "kcal": e.kcal, "micros": e.micros} for e in entries
    )
    out = AutofillOut(filled=[], completed=[], no_match=[], postponed=[])
    buckets = {
        micros_fill.Outcome.FILLED: out.filled,
        micros_fill.Outcome.ALREADY: out.completed,
        micros_fill.Outcome.NO_MATCH: out.no_match,
        micros_fill.Outcome.ERROR: out.postponed,
    }
    for gap in gaps:
        food = db.get(Food, gap.food_id)
        if food is None:
            continue
        name = food.name
        try:
            outcome = micros_fill.auto_fill(db, food, fdc, ai)
        except Exception:  # noqa: BLE001 - np. równoległe uzupełnianie w tle tego samego produktu
            log.exception("Uzupełnianie witamin nieudane (produkt %s)", gap.food_id)
            db.rollback()
            outcome = micros_fill.Outcome.ERROR  # spróbujemy przy następnym otwarciu
        buckets[outcome].append(name)
    return out


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
