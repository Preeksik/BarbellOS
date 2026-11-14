"""Wskaźnik regeneracji (dokumentacja 6.3). Deterministyczny, liczony z własnych średnich.

[ZAŁOŻENIE] Progi poniżej są wartościami startowymi do skalibrowania na prawdziwych
danych z opaski. Są stałymi w jednym miejscu, żeby ich zmiana nie wymagała szukania.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from statistics import mean, pstdev

MIN_BASELINE_DAYS = 14
SLEEP_RATIO_LOW = 0.85  # sen krótszy niż 85% własnej średniej z 14 dni
Z_LIMIT = 1.0  # odchylenie HRV w dół / tętna spoczynkowego w górę


@dataclass(frozen=True)
class Readiness:
    state: str  # collecting | green | yellow | red
    factors: list[str] = field(default_factory=list)


def _z(value: float, history: Sequence[float]) -> float | None:
    if len(history) < MIN_BASELINE_DAYS:
        return None
    sd = pstdev(history)
    return (value - mean(history)) / sd if sd > 0 else 0.0


def readiness(
    sleep_min: float | None,
    hrv_ms: float | None,
    resting_hr: float | None,
    sleep_history: Sequence[float],
    hrv_history: Sequence[float],
    resting_hr_history: Sequence[float],
) -> Readiness:
    """Historia to wartości z poprzednich dni (bez dzisiejszej): sen z 14 dni, reszta z 28."""
    factors: list[str] = []
    measured = 0

    if sleep_min is not None and len(sleep_history) >= MIN_BASELINE_DAYS:
        measured += 1
        if sleep_min < SLEEP_RATIO_LOW * mean(sleep_history):
            factors.append("sleep_short")

    z_hrv = _z(hrv_ms, hrv_history) if hrv_ms is not None else None
    if z_hrv is not None:
        measured += 1
        if z_hrv < -Z_LIMIT:
            factors.append("hrv_low")

    z_rhr = _z(resting_hr, resting_hr_history) if resting_hr is not None else None
    if z_rhr is not None:
        measured += 1
        if z_rhr > Z_LIMIT:
            factors.append("resting_hr_high")

    if measured == 0:
        return Readiness("collecting")
    state = ("green", "yellow", "red")[min(len(factors), 2)]
    return Readiness(state, factors)
