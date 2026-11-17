"""Zapisane posiłki (etap 1, krok 6): zestawy produktów z ilościami.

Zestaw nie przechowuje wartości odżywczych. Wpis dziennika liczy je z produktu w chwili
dodania i zamraża (dokumentacja 8), więc zestaw i pojedynczy produkt zachowują się
tak samo. Podsumowanie zestawu pokazuje wartości według produktów na dziś.
"""

from collections.abc import Iterable, Mapping

from app.core.nutrients import MACRO_KEYS, portion_values, sum_values

MAX_ITEMS = 30
MAX_AMOUNT = 5000.0  # ta sama granica co we wpisie dziennika
MAX_NAME = 120


def meal_errors(name: str, items: list[tuple[int, float]]) -> list[str]:
    """Błędy, z którymi zestawu nie zapisujemy. `items` to pary (produkt, ilość)."""
    errors = []
    if not name.strip():
        errors.append("Nazwa posiłku nie może być pusta.")
    elif len(name.strip()) > MAX_NAME:
        errors.append(f"Nazwa posiłku może mieć najwyżej {MAX_NAME} znaków.")
    if not items:
        errors.append("Posiłek musi mieć co najmniej jeden produkt.")
    elif len(items) > MAX_ITEMS:
        errors.append(f"Posiłek może mieć najwyżej {MAX_ITEMS} produktów.")
    if any(not 0 < amount <= MAX_AMOUNT for _, amount in items):
        errors.append(f"Ilość produktu musi być większa od zera, najwyżej {MAX_AMOUNT:g}.")
    return errors


def meal_totals(items: Iterable[tuple[Mapping[str, float | None], float]]) -> dict[str, float]:
    """Suma zestawu: pary (wartości na 100 g lub ml, ilość). Brak danych liczy się jak zero."""
    return sum_values(
        portion_values({key: per_100.get(key) for key in MACRO_KEYS}, amount)
        for per_100, amount in items
    )
