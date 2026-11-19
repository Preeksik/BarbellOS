"""Produkty podstawowe (warzywa, owoce, mięso, kasze) w wyszukiwarce, z tabel USDA (19.11.2026).

Duża baza produktów zna głównie produkty paczkowane z kodem: „papryka" daje chipsy
i przyprawy, a nie warzywo. Tabele USDA mają produkty podstawowe z kaloriami, makro
i witaminami, ale po angielsku. Przebieg:

1. tani model tłumaczy zapytanie na styl USDA („papryka czerwona" -> „Peppers, sweet, red"),
2. USDA zwraca rekordy, kod wybiera najlepsze (`core.micros.generic_candidates`),
3. tani model nadaje im polskie nazwy (kolejność jak na wejściu, bez identyfikatorów).

Wynik jest pamiętany dla zapytania, więc powtórka nie kosztuje wywołań. Gdy nazwy się nie
uda, zostają opisy USDA: lepsze to niż brak wyniku.
"""

import logging
from collections import OrderedDict
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.ai.prompts import FOOD_QUERY_PROMPT, GENERIC_NAMES_PROMPT
from app.ai.router import AiRouter, AllProvidersFailed, Task
from app.ai.schemas import FoodQuery, GenericNames
from app.core.micros import generic_candidates
from app.core.search import words
from app.db import repo
from app.fdc.client import FdcClient, FdcFood

log = logging.getLogger(__name__)

PAGE_SIZE = 25  # kandydaci z USDA; kod wybiera z nich kilka najlepszych
CACHE_SIZE = 200


class TranslationUnavailable(Exception):
    """Żaden model nie przetłumaczył zapytania."""


@dataclass(frozen=True)
class GenericHit:
    record: FdcFood
    name: str  # po polsku


_cache: OrderedDict[str, list[GenericHit]] = OrderedDict()


def clear_cache() -> None:
    _cache.clear()


def _key(query: str) -> str:
    return " ".join(words(query))


def _run(db: Session, ai: AiRouter, task: Task, prompt: str, schema):
    try:
        result = ai.run(task, prompt, schema)
    except AllProvidersFailed as exc:
        for failure in exc.called:
            repo.log_ai_run(db, task, failure.provider, "", failure.kind)
        raise
    repo.log_ai_run(
        db, task, result.provider, result.model, "ok", result.input_tokens, result.output_tokens
    )
    return result.data


def _polish_names(db: Session, ai: AiRouter, query: str, records: list[FdcFood]) -> list[str]:
    fallback = [r.description for r in records]
    try:
        data = _run(
            db,
            ai,
            Task.GENERIC_NAMES,
            GENERIC_NAMES_PROMPT.format(
                query=query, descriptions="\n".join(r.description for r in records)
            ),
            GenericNames,
        )
    except AllProvidersFailed:
        return fallback
    names = [" ".join(n.split())[:120] for n in data.names_pl]
    if len(names) != len(records) or not all(names):
        log.warning("Model zwrócił %d nazw dla %d rekordów", len(names), len(records))
        return fallback
    return names


def search(db: Session, query: str, fdc: FdcClient, ai: AiRouter) -> list[GenericHit]:
    """Produkty podstawowe dla zapytania po polsku. Błędy USDA (`FdcError`) idą wyżej."""
    key = _key(query)
    if key in _cache:
        _cache.move_to_end(key)
        return _cache[key]
    try:
        translated = _run(db, ai, Task.FOOD_QUERY, FOOD_QUERY_PROMPT.format(name=query), FoodQuery)
    except AllProvidersFailed as exc:
        raise TranslationUnavailable from exc
    query_en = " ".join(translated.query_en.split())[:120] or query
    found = fdc.search(query_en, page_size=PAGE_SIZE)
    by_id = {record.fdc_id: record for record in found}
    chosen = [
        by_id[fdc_id]
        for fdc_id in generic_candidates(
            query_en, [(r.fdc_id, r.description, r.kcal) for r in found]
        )
    ]
    names = _polish_names(db, ai, query, chosen) if chosen else []
    hits: list[GenericHit] = []
    seen: set[str] = set()
    for record, name in zip(chosen, names, strict=True):
        # Dwa zbiory USDA mają często ten sam produkt („Peppers, sweet, red, raw" i „Peppers,
        # bell, red, raw"): pod tą samą polską nazwą zostaje pierwszy, lepiej dopasowany.
        if (folded := _key(name)) in seen:
            continue
        seen.add(folded)
        hits.append(GenericHit(record=record, name=name))
    _cache[key] = hits
    if len(_cache) > CACHE_SIZE:
        _cache.popitem(last=False)
    return hits
