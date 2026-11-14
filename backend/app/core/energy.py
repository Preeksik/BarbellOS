"""Trend masy ciała i adaptacyjne zapotrzebowanie energetyczne (dokumentacja 6.4)."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, timedelta

KCAL_PER_KG = 7700.0


def weight_trend(weights: Mapping[date, float], window: int = 7) -> dict[date, float]:
    """Średnia z pomiarów z ostatnich `window` dni kalendarzowych.

    Trend jest liczony tylko dla dni z pomiarem; dni bez pomiaru nie są uzupełniane.
    """
    trend: dict[date, float] = {}
    for day in sorted(weights):
        recent = [w for d, w in weights.items() if timedelta(0) <= day - d < timedelta(days=window)]
        trend[day] = sum(recent) / len(recent)
    return trend


@dataclass(frozen=True)
class TdeeEstimate:
    tdee_kcal: float
    mean_intake_kcal: float
    trend_change_kg: float
    days: int
    logged_days: int


def adaptive_tdee(
    intake_kcal: Mapping[date, float],
    trend: Mapping[date, float],
    min_days: int = 14,
    max_days: int = 21,
    min_logged_share: float = 0.8,
) -> TdeeEstimate | None:
    """Zapotrzebowanie = średnie spożycie − (zmiana trendu wagi × 7700 kcal/kg ÷ liczba dni).

    Zwraca None, gdy okno jest krótsze niż `min_days` albo zalogowano mniej niż
    `min_logged_share` dni: z dziurawego dziennika wychodzi zaniżone zapotrzebowanie.
    """
    if len(trend) < 2:
        return None
    end = max(trend)
    start = min((d for d in trend if end - d <= timedelta(days=max_days)), default=end)
    days = (end - start).days
    if days < min_days:
        return None
    logged = [kcal for d, kcal in intake_kcal.items() if start < d <= end and kcal > 0]
    if len(logged) < min_logged_share * days:
        return None
    mean_intake = sum(logged) / len(logged)
    change = trend[end] - trend[start]
    return TdeeEstimate(
        tdee_kcal=mean_intake - change * KCAL_PER_KG / days,
        mean_intake_kcal=mean_intake,
        trend_change_kg=change,
        days=days,
        logged_days=len(logged),
    )
