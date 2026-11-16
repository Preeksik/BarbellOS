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


# ---------- spójność wartości z etykiety ----------

# (składnik podrzędny, składnik nadrzędny): podrzędny nigdy nie przekracza nadrzędnego.
SUBSETS = (("sat_fat_g", "fat_g"), ("sugars_g", "carbs_g"))
LABELS_PL = {
    "kcal": "energia",
    "protein_g": "białko",
    "fat_g": "tłuszcz",
    "sat_fat_g": "kwasy nasycone",
    "carbs_g": "węglowodany",
    "sugars_g": "cukry",
    "fiber_g": "błonnik",
    "salt_g": "sól",
}
MAX_KCAL_PER_100 = 900.0  # czysty tłuszcz
KCAL_TOLERANCE = 0.20  # odchylenie kalorii od wyliczonych z makro, od którego ostrzegamy
KCAL_TOLERANCE_MIN = 15.0


def fill_implied_zeros(macros: Mapping[str, float | None]) -> dict[str, float | None]:
    """Uzupełnia zera, które wynikają z etykiety: tłuszcz 0 g oznacza nasycone 0 g itd.

    To nie jest szacunek. Składnik podrzędny nie może być większy od nadrzędnego,
    więc przy zerze wartość jest pewna.
    """
    out = dict(macros)
    for child, parent in SUBSETS:
        if out.get(child) is None and out.get(parent) == 0:
            out[child] = 0.0
    return out


def value_in_range(key: str, value: float, unit: str = "g") -> bool:
    """Czy wartość na 100 g lub 100 ml jest w ogóle możliwa.

    Górna granica 100 g na 100 g dotyczy tylko produktów w gramach: 100 ml gęstego
    płynu (miód, syrop) waży więcej niż 100 g.
    """
    limit = MAX_KCAL_PER_100 if key == "kcal" else (100.0 if unit == "g" else 200.0)
    return 0 <= value <= limit


def macro_errors(macros: Mapping[str, float | None], unit: str = "g") -> list[str]:
    """Błędy, z którymi produktu nie zapisujemy (wartości niemożliwe)."""
    errors = []
    for key in MACRO_KEYS:
        value = macros.get(key)
        if value is None:
            continue
        if not value_in_range(key, value, unit):
            errors.append(f"{LABELS_PL[key].capitalize()}: wartość {value:g} jest poza zakresem.")
    for child, parent in SUBSETS:
        c, p = macros.get(child), macros.get(parent)
        if c is not None and p is not None and c > p:
            errors.append(
                f"{LABELS_PL[child].capitalize()} ({c:g} g) nie mogą przekraczać "
                f"wartości „{LABELS_PL[parent]}” ({p:g} g)."
            )
    return errors


def macro_warnings(macros: Mapping[str, float | None]) -> list[str]:
    """Ostrzeżenia, które nie blokują zapisu: najczęściej literówka przy przepisywaniu."""
    kcal = macros.get("kcal")
    protein, carbs, fat = macros.get("protein_g"), macros.get("carbs_g"), macros.get("fat_g")
    if None in (kcal, protein, carbs, fat):
        return []
    expected = 4 * protein + 4 * carbs + 9 * fat + 2 * (macros.get("fiber_g") or 0)
    if abs(kcal - expected) > max(KCAL_TOLERANCE_MIN, KCAL_TOLERANCE * expected):
        return [
            f"Energia {kcal:g} kcal nie pasuje do makroskładników "
            f"(wychodzi ok. {expected:.0f} kcal). Sprawdź, czy w którejś wartości nie ma pomyłki."
        ]
    return []
