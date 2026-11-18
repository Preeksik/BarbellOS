"""Automatyczne uzupełnianie witamin i minerałów z tabel USDA (etap 6).

Decyzja właściciela z 18.11.2026: produkt dopasowuje się do tabeli sam, bez zatwierdzania.
Ręcznie zostają tylko produkty bez pewnego dopasowania, a każde dopasowanie można zmienić
w karcie produktu. Dopasowany produkt od razu uzupełnia brakujące mikroskładniki swoich
wpisów (kalorie i makro wpisów pozostają zamrożone).

To nie jest `core/`: moduł woła sieć (USDA, model AI) i bazę. Decyzje liczbowe (ocena
dopasowania, wiarygodność kalorii, łączenie źródeł) są w `core/micros.py`.
"""

import logging
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy.orm import Session

from app.ai.prompts import FOOD_QUERY_PROMPT
from app.ai.router import AiRouter, AllProvidersFailed, Task
from app.ai.schemas import FoodQuery
from app.core.micros import (
    MIN_MICROS,
    auto_match,
    clean_micros,
    fill_missing_micros,
    merge_micros,
    table_source,
)
from app.db import repo
from app.db.models import Food
from app.fdc.client import FdcClient, FdcError, FdcFood

log = logging.getLogger(__name__)


class QueryUnavailable(Exception):
    """Nie udało się przetłumaczyć nazwy produktu (model AI nie odpowiedział)."""


class Outcome(StrEnum):
    FILLED = "filled"  # dopasowany do tabeli i uzupełniony
    ALREADY = "already"  # produkt miał dane; uzupełniono tylko wpisy
    NO_MATCH = "no_match"  # brak pewnego dopasowania: zostaje do ręcznego wyboru
    ERROR = "error"  # sieć albo limit: spróbujemy następnym razem


def query_for(db: Session, food: Food, ai: AiRouter) -> str:
    """Zapytanie po angielsku: zapamiętana nazwa angielska albo tłumaczenie przez AI."""
    if food.name_en:
        return food.name_en
    task = Task.FOOD_QUERY
    try:
        result = ai.run(task, FOOD_QUERY_PROMPT.format(name=food.name), FoodQuery)
    except AllProvidersFailed as exc:
        for failure in exc.called:
            repo.log_ai_run(db, task, failure.provider, "", failure.kind)
        raise QueryUnavailable from exc
    repo.log_ai_run(
        db, task, result.provider, result.model, "ok", result.input_tokens, result.output_tokens
    )
    query = " ".join(result.data.query_en.split())[:120]
    if query:
        food.name_en = query  # następnym razem bez wywołania modelu
        db.commit()
    return query or food.name


def kept_micros(db: Session, food: Food) -> dict[str, tuple[float, str]]:
    """Mikroskładniki z etykiety lub wpisane ręcznie: tabela ich nie zastępuje."""
    return {
        m.nutrient_id: (m.amount_per_100g, m.source)
        for m in repo.food_micros(db, food.id)
        if m.source in ("label", "user")
    }


def apply_record(db: Session, food: Food, record: FdcFood) -> None:
    """Mikroskładniki produktu z rekordu USDA (etykieta ma pierwszeństwo)."""
    micros = merge_micros(
        kept_micros(db, food), clean_micros(record.micros), table_source(bool(food.barcode))
    )
    repo.set_food_micros(db, food, micros, record.fdc_id, record.description[:255])
    food.fdc_checked_at = datetime.now(UTC)
    db.commit()


def backfill_entries(db: Session, food: Food) -> int:
    """Uzupełnia brakujące mikroskładniki wpisów produktu. Zwraca liczbę zmienionych wpisów."""
    per_100 = {m.nutrient_id: (m.amount_per_100g, m.source) for m in repo.food_micros(db, food.id)}
    updated = 0
    for entry in repo.entries_of_food(db, food.id):
        filled = fill_missing_micros(entry.micros, per_100, entry.amount)
        if filled is not None:
            entry.micros = filled
            updated += 1
    db.commit()
    return updated


def auto_fill(db: Session, food: Food, fdc: FdcClient, ai: AiRouter) -> Outcome:
    """Dopasowuje produkt do tabeli USDA bez pytania i uzupełnia jego wpisy."""
    if len(repo.food_micros(db, food.id)) >= MIN_MICROS:
        backfill_entries(db, food)
        return Outcome.ALREADY
    if food.fdc_checked_at is not None:
        return Outcome.NO_MATCH  # już sprawdzany bez wyniku albo dopasowanie usunięte ręcznie
    try:
        query = query_for(db, food, ai)
        candidates = fdc.search(query)
    except (QueryUnavailable, FdcError) as exc:
        log.info("Uzupełnianie witamin dla %s odłożone: %s", food.id, exc)
        return Outcome.ERROR
    chosen = auto_match(query, food.kcal, [(c.fdc_id, c.description, c.kcal) for c in candidates])
    if chosen is None:
        food.fdc_checked_at = datetime.now(UTC)
        db.commit()
        return Outcome.NO_MATCH
    record = next(c for c in candidates if c.fdc_id == chosen)
    apply_record(db, food, record)
    backfill_entries(db, food)
    return Outcome.FILLED
