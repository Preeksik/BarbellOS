"""Przeliczenia wartości odżywczych: porcja, suma dnia, pokrycie mikroskładników."""

from collections.abc import Iterable, Mapping

MACRO_KEYS = (
    "kcal", "protein_g", "fat_g", "sat_fat_g", "carbs_g", "sugars_g", "fiber_g", "salt_g",
)  # fmt: skip


def portion_values(per_100g: Mapping[str, float | None], grams: float) -> dict[str, float | None]:
    """Wartości dla porcji. Brak danych (None) zostaje brakiem, nie zerem."""
    return {k: (None if v is None else v * grams / 100) for k, v in per_100g.items()}


def sum_values(entries: Iterable[Mapping[str, float | None]], keys=MACRO_KEYS) -> dict[str, float]:
    """Suma wpisów. Brakujące wartości są pomijane (liczone jak zero)."""
    totals = dict.fromkeys(keys, 0.0)
    for entry in entries:
        for k in keys:
            totals[k] += entry.get(k) or 0.0
    return totals


def micro_coverage(entries: Iterable[Mapping], rda: Mapping[str, float | None]) -> dict[str, dict]:
    """Pokrycie normy dla każdego mikroskładnika wraz z miarą kompletności danych.

    Wpis ma postać {"kcal": float | None, "micros": {id: {"amount": float, ...}} | None}.
    `kcal_share` mówi, jaka część kalorii z dnia pochodzi z wpisów, które miały dane
    o danym składniku. Bez tego „78% normy" byłoby nie do odróżnienia od braku danych.
    """
    entries = list(entries)
    total_kcal = sum(e.get("kcal") or 0.0 for e in entries)
    out: dict[str, dict] = {}
    for nutrient_id, norm in rda.items():
        amount = kcal_with_data = 0.0
        for e in entries:
            micro = (e.get("micros") or {}).get(nutrient_id)
            if micro is None:
                continue
            amount += micro.get("amount") or 0.0
            kcal_with_data += e.get("kcal") or 0.0
        out[nutrient_id] = {
            "amount": amount,
            "percent_rda": (amount / norm * 100) if norm else None,
            "kcal_share": (kcal_with_data / total_kcal) if total_kcal else 0.0,
        }
    return out
