"""Cele dzienne (etap 1, krok 4).

Cele są wersjonowane datą: zmiana obowiązuje od wskazanego dnia, a dni wcześniejsze
zachowują cele, które wtedy obowiązywały. Bez tego zmiana celu „przepisałaby"
historię i stary dzień wyglądałby na nieudany albo udany bez powodu.

Każdy składnik ma stały rodzaj celu:
- `target`: wartość, do której się dąży (kalorie, tłuszcz, węglowodany),
- `min`: co najmniej (białko, błonnik),
- `max`: najwyżej (nasycone, cukry, sól).
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date
from typing import Literal

from app.core.nutrients import LABELS_PL, MACRO_KEYS

GoalKind = Literal["target", "min", "max"]

GOAL_KINDS: dict[str, GoalKind] = {
    "kcal": "target",
    "protein_g": "min",
    "fat_g": "target",
    "sat_fat_g": "max",
    "carbs_g": "target",
    "sugars_g": "max",
    "fiber_g": "min",
    "salt_g": "max",
}
assert set(GOAL_KINDS) == set(MACRO_KEYS)

# Górne granice celu na dzień. Chronią przed literówką (np. 25000 zamiast 2500 kcal).
GOAL_LIMITS = {
    "kcal": 10_000.0,
    "protein_g": 1_000.0,
    "fat_g": 1_000.0,
    "sat_fat_g": 1_000.0,
    "carbs_g": 2_000.0,
    "sugars_g": 1_000.0,
    "fiber_g": 500.0,
    "salt_g": 100.0,
}

Goals = dict[str, float | None]


@dataclass(frozen=True)
class TargetRow:
    """Wiersz tabeli `daily_target`. Puste `low` i `high` oznaczają „bez celu"."""

    nutrient_id: str
    low: float | None
    high: float | None


def goal_errors(goals: Mapping[str, float | None]) -> list[str]:
    """Błędy, z którymi celów nie zapisujemy."""
    errors = [f"Nieznany składnik: {key}." for key in goals if key not in GOAL_KINDS]
    for key, value in goals.items():
        if key not in GOAL_KINDS or value is None:
            continue
        if not 0 < value <= GOAL_LIMITS[key]:
            errors.append(
                f"{LABELS_PL[key].capitalize()}: cel {value:g} jest poza zakresem "
                f"(od 0 do {GOAL_LIMITS[key]:g})."
            )
    return errors


def goals_to_rows(goals: Mapping[str, float | None]) -> list[TargetRow]:
    """Komplet wierszy dla wszystkich składników, także tych bez celu.

    Wiersz „bez celu" jest potrzebny: inaczej usunięty cel wróciłby z poprzedniej wersji.
    """
    rows = []
    for key, kind in GOAL_KINDS.items():
        value = goals.get(key)
        low = value if kind in ("target", "min") else None
        high = value if kind in ("target", "max") else None
        rows.append(TargetRow(key, low, high))
    return rows


def rows_to_goals(rows: Iterable[TargetRow]) -> Goals:
    """Odwrotność `goals_to_rows`. Składnik bez wiersza nie ma celu."""
    goals: Goals = dict.fromkeys(GOAL_KINDS)
    for row in rows:
        kind = GOAL_KINDS.get(row.nutrient_id)
        if kind is None:
            continue  # mikroskładniki: osobna funkcja w etapie 6
        goals[row.nutrient_id] = row.high if kind == "max" else row.low
    return goals


def active_version(versions: Iterable[date], day: date) -> date | None:
    """Data wersji celów obowiązującej w danym dniu: najpóźniejsza nie późniejsza niż dzień."""
    earlier = [version for version in versions if version <= day]
    return max(earlier) if earlier else None
