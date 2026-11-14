"""Obliczenia treningowe przeniesione 1:1 z pliku Plan_AMP_2027.html.

Zgodność z oryginałem sprawdza tests/test_training.py na wartościach wyliczonych
oryginalnym kodem JavaScript (tests/fixtures/training_reference.json).

Uwaga o zaokrągleniach: JavaScript `Math.round` zaokrągla połówki w górę, a pythonowe
`round` do parzystej. Dlatego używamy własnego `js_round`.
"""

import math
from collections.abc import Mapping

STEP_KG = 2.5

# Procent maksa dla pary (powtórzenia, RPE); indeks = (10 - RPE) * 2 + (powtórzenia - 1) * 2.
RTS_PERCENT = (
    100, 97.8, 95.5, 93.9, 92.2, 90.7, 89.2, 87.8, 86.3, 85.0,
    83.7, 82.4, 81.1, 79.9, 78.6, 77.4, 76.2, 75.1, 73.9,
)  # fmt: skip

ATTEMPT_COEF = {"B": (0.92, 0.97, 1.0, 1.02)}
ATTEMPT_COEF_DEFAULT = (0.91, 0.96, 1.0, 1.025)


def js_round(x: float) -> int:
    return math.floor(x + 0.5)


def round_to_step(kg: float, step: float = STEP_KG) -> float:
    """Najbliższa wielokrotność kroku (oryginalne `r25`)."""
    return js_round(kg / step) * step


def floor_to_step(kg: float, step: float = STEP_KG) -> float:
    """W dół do wielokrotności kroku (oryginalne `f25`)."""
    return math.floor(kg / step + 1e-9) * step


def rts_percent(reps: int, rpe: float) -> float | None:
    i = js_round((10 - rpe) * 2 + (reps - 1) * 2)
    return RTS_PERCENT[i] if 0 <= i < len(RTS_PERCENT) else None


def e1rm(kg: float, reps: int, rpe: float) -> float | None:
    """Szacowany maks z serii. Poza tabelą RPE zwraca None."""
    pct = rts_percent(reps, rpe)
    return kg / (pct / 100) if pct else None


def tm_for(
    phase: int,
    lift: str,
    phase_1: Mapping[str, float],
    increments: Mapping[str, Mapping[str, float]],
    overrides: Mapping[str, Mapping[str, float]] | None = None,
) -> float:
    """Maks treningowy fazy: wartość wpisana ręcznie albo TM poprzedniej fazy + przyrost.

    `phase_1`, `increments` pochodzą z planu (`training_max`), `overrides` z ustawień
    użytkownika (`plan_settings.tm`). Klucze faz są tekstem, bo tak zapisuje je JSON.
    """
    manual = (overrides or {}).get(str(phase), {}).get(lift)
    if isinstance(manual, int | float) and manual > 0:
        return float(manual)
    if phase <= 1:
        return float(phase_1[lift])
    previous = tm_for(phase - 1, lift, phase_1, increments, overrides)
    return previous + increments[str(phase)][lift]


def load_for(exercise: Mapping, tm: float) -> float | None:
    """Ciężar serii z procentu TM. Akcesoria i podejścia nie mają wyliczanego ciężaru."""
    percent = exercise.get("percent_tm")
    if not exercise.get("lift") or exercise.get("kind") in ("acc", "att") or percent is None:
        return None
    return round_to_step(tm * percent / 100)


def attempts_for(max_kg: float, lift: str) -> dict:
    """Trzy podejścia: pierwsze w dół do 2,5 kg, trzecie jako przedział."""
    k = ATTEMPT_COEF.get(lift, ATTEMPT_COEF_DEFAULT)
    return {
        "first": floor_to_step(max_kg * k[0]),
        "second": round_to_step(max_kg * k[1]),
        "third": (round_to_step(max_kg * k[2]), round_to_step(max_kg * k[3])),
    }


def third_from_second(kg: float, rpe: float, lift: str) -> dict | None:
    """Podpowiedź trzeciego podejścia na podstawie RPE drugiego."""
    if not kg or not rpe:
        return None
    big = lift != "B"
    if rpe <= 7.5:
        inc = 10 if big else 5
    elif rpe <= 8:
        inc = 7.5 if big else 5
    elif rpe <= 8.5:
        inc = 5 if big else 2.5
    elif rpe <= 9:
        inc = 2.5
    else:
        inc = 0
    return {"kg": kg + inc, "inc": inc}


def gl_coefficient(bodyweight_kg: float) -> float:
    """Współczynnik punktów GL użyty w oryginalnym planie."""
    return 100 / (1199.72839 - 1025.18162 * math.exp(-0.00921 * bodyweight_kg))


def gl_points(total_kg: float, bodyweight_kg: float) -> float:
    return total_kg * gl_coefficient(bodyweight_kg)
