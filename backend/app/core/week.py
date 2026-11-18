"""Podsumowanie tygodnia (etap 6): średnie dzienne i pokrycie norm mikroskładników.

Średnie liczone są z dni, w których coś zapisano. Dzień bez wpisów to najczęściej
dzień niezalogowany, a nie dzień głodówki, więc nie zaniża średniej.

Pokrycie normy mówi też, na ile można mu ufać: jaka część kalorii z tygodnia pochodzi
z wpisów z danymi z tabel lub etykiet, jaka z szacunku AI, a jaka nie ma danych o danym
składniku. „Magnez 78% normy" przy 30% kalorii z danymi to zupełnie inna informacja niż
przy 90%.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date

from app.core.nutrients import MACRO_KEYS, sum_values

TRUSTED = {"label", "reference", "user"}  # wartości z etykiety, tabeli albo wpisane ręcznie


@dataclass(frozen=True)
class DayTotal:
    date: date
    entries: int
    totals: dict[str, float]


@dataclass(frozen=True)
class MicroCoverage:
    nutrient_id: str
    avg_amount: float  # średnio na dzień zalogowany
    percent_rda: float | None
    share_trusted: float  # część kalorii z wpisów z danymi z tabeli lub etykiety
    share_estimated: float  # część kalorii z wpisów z szacunkiem
    share_missing: float  # część kalorii z wpisów bez tego składnika


def day_totals(days: Iterable[date], entries: Iterable[Mapping]) -> list[DayTotal]:
    """Suma każdego dnia z zakresu, także pustego. Wpis ma `date` i osiem wartości."""
    by_day: dict[date, list[Mapping]] = {}
    for entry in entries:
        by_day.setdefault(entry["date"], []).append(entry)
    return [
        DayTotal(day, len(by_day.get(day, [])), sum_values(by_day.get(day, []))) for day in days
    ]


def average(days: list[DayTotal]) -> dict[str, float] | None:
    """Średnia dzienna z dni z wpisami. None, gdy w tygodniu nic nie zapisano."""
    logged = [d for d in days if d.entries > 0]
    if not logged:
        return None
    return {key: sum(d.totals[key] for d in logged) / len(logged) for key in MACRO_KEYS}


def _share(part: float, whole: float) -> float:
    return part / whole if whole else 0.0


def micro_week(
    entries: Iterable[Mapping], rda: Mapping[str, float | None], logged_days: int
) -> list[MicroCoverage]:
    """Pokrycie normy w tygodniu z podziałem kalorii według źródła danych.

    Wpis ma `kcal` i `micros` ({id: {"amount": float, "source": str}} albo None).
    """
    entries = list(entries)
    total_kcal = sum(e.get("kcal") or 0.0 for e in entries)
    out = []
    for nutrient_id, norm in rda.items():
        amount = trusted = estimated = 0.0
        for e in entries:
            micro = (e.get("micros") or {}).get(nutrient_id)
            if micro is None:
                continue
            amount += micro.get("amount") or 0.0
            if micro.get("source") in TRUSTED:
                trusted += e.get("kcal") or 0.0
            else:
                estimated += e.get("kcal") or 0.0
        avg = amount / logged_days if logged_days else 0.0
        out.append(
            MicroCoverage(
                nutrient_id=nutrient_id,
                avg_amount=avg,
                percent_rda=(avg / norm * 100) if norm else None,
                share_trusted=_share(trusted, total_kcal),
                share_estimated=_share(estimated, total_kcal),
                share_missing=_share(total_kcal - trusted - estimated, total_kcal),
            )
        )
    return out


# Wpis z mniej niż tyloma mikroskładnikami traktujemy jako „bez danych o witaminach":
# etykiety podają zwykle tylko sód, a to nie mówi nic o witaminach.
MIN_MICROS = 5


@dataclass(frozen=True)
class Gap:
    food_id: int
    kcal: float  # kalorie tygodnia z wpisów tego produktu bez danych
    share: float  # ich udział w kaloriach tygodnia
    entries: int


def micro_gaps(entries: Iterable[Mapping], limit: int = 8) -> tuple[list[Gap], float]:
    """Produkty, których wpisy w tygodniu nie mają danych o witaminach, od największych kalorii.

    Drugi wynik to udział kalorii z wpisów bez produktu (szacunki AI sprzed etapu 6),
    których nie da się uzupełnić z tabeli. Wpis ma `food_id`, `kcal` i `micros`.
    """
    entries = list(entries)
    total = sum(e.get("kcal") or 0.0 for e in entries)
    by_food: dict[int, list[float]] = {}
    orphan = 0.0
    for e in entries:
        if len(e.get("micros") or {}) >= MIN_MICROS:
            continue
        if e.get("food_id") is None:
            orphan += e.get("kcal") or 0.0
        else:
            by_food.setdefault(e["food_id"], []).append(e.get("kcal") or 0.0)
    gaps = [
        Gap(food_id, sum(kcals), _share(sum(kcals), total), len(kcals))
        for food_id, kcals in by_food.items()
    ]
    gaps.sort(key=lambda g: (-g.kcal, g.food_id))
    return gaps[:limit], _share(orphan, total)
