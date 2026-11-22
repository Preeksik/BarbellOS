"""Dziennik dnia: zamrażanie wartości porcji i sumy.

Wpis przechowuje wartości policzone w chwili dodania. Późniejsza poprawka produktu
nie zmienia historii (dokumentacja, rozdział 8).
"""

from collections.abc import Iterable, Mapping

from app.core.nutrients import MACRO_KEYS, portion_values, sum_values

# Kolejność wyświetlania. Identyfikatory trafiają do bazy, więc ich nie zmieniamy.
MEAL_SLOTS = ("breakfast", "second_breakfast", "lunch", "snack", "dinner")

Micros = dict[str, dict]  # {"magnesium": {"amount": 48.0, "source": "label"}}


def freeze_portion(
    per_100: Mapping[str, float | None],
    micros_per_100: Mapping[str, tuple[float, str]],
    amount: float,
) -> tuple[dict[str, float | None], Micros]:
    """Wartości dla `amount` gramów lub mililitrów produktu. Brak danych zostaje brakiem."""
    values = portion_values({key: per_100.get(key) for key in MACRO_KEYS}, amount)
    micros = {
        nutrient_id: {"amount": per100 * amount / 100, "source": source}
        for nutrient_id, (per100, source) in micros_per_100.items()
    }
    return values, micros


def scale_portion(
    values: Mapping[str, float | None], micros: Micros | None, ratio: float
) -> tuple[dict[str, float | None], Micros]:
    """Zmiana ilości we wpisie: zamrożone wartości są skalowane, nie liczone od nowa.

    Dzięki temu wpis nadal odpowiada produktowi z chwili dodania, nawet jeśli produkt
    został później poprawiony.
    """
    scaled = {key: (None if value is None else value * ratio) for key, value in values.items()}
    scaled_micros = {
        nutrient_id: {**micro, "amount": micro["amount"] * ratio}
        for nutrient_id, micro in (micros or {}).items()
    }
    return scaled, scaled_micros


def day_totals(entries: Iterable[Mapping]) -> dict:
    """Suma dnia i sumy posiłków. Wpis ma klucze `meal_slot` oraz osiem wartości."""
    entries = list(entries)
    by_slot = {
        slot: sum_values(e for e in entries if e["meal_slot"] == slot)
        for slot in MEAL_SLOTS
        if any(e["meal_slot"] == slot for e in entries)
    }
    return {"totals": sum_values(entries), "by_slot": by_slot}


def per_100_of_entry(
    values: Mapping[str, float | None], micros: Micros | None, amount: float
) -> tuple[dict[str, float | None], dict[str, tuple[float, str]]]:
    """Wartości na 100 g odtworzone z zamrożonego wpisu (22.11.2026).

    Służy do zamiany dawnego wpisu z AI bez produktu w produkt, który można zapisać
    w posiłku i dodać ponownie. Brak danych zostaje brakiem, źródło składnika zostaje.
    """
    per_100, micros_100 = scale_portion(values, micros, 100 / amount)
    return per_100, {nid: (m["amount"], m["source"]) for nid, m in micros_100.items()}


RECENT_MEALS_LIMIT = 10


def recent_meals(
    entries: Iterable[Mapping], limit: int = RECENT_MEALS_LIMIT
) -> list[tuple[object, str, list[int]]]:
    """Poprzednie posiłki do skopiowania (22.11.2026): (dzień, posiłek, indeksy wpisów).

    Wpis ma klucze `date` i `meal_slot`. Najnowszy dzień pierwszy, w dniu w kolejności
    posiłków; wpisy w posiłku w kolejności wejścia (dodania).
    """
    groups: dict[tuple[object, str], list[int]] = {}
    for index, entry in enumerate(entries):
        groups.setdefault((entry["date"], entry["meal_slot"]), []).append(index)
    order = {slot: i for i, slot in enumerate(MEAL_SLOTS)}
    keys = sorted(groups, key=lambda key: (-key[0].toordinal(), order.get(key[1], len(order))))
    return [(day, slot, groups[(day, slot)]) for day, slot in keys[:limit]]
