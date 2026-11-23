"""Suplementacja (23.11.2026): lista suplementów i odhaczanie, co wzięte danego dnia.

Suplement to pozycja z listy, a nie produkt w dzienniku: nie ma kalorii, a liczy się to,
czy wzięty był codziennie. Tu jest tylko logika dni; zapis jest w `api/supplements.py`.
"""

from collections.abc import Hashable, Iterable
from datetime import date, timedelta

HISTORY_DAYS = 7  # kropki „ostatni tydzień" przy suplemencie
MAX_NAME = 80
MAX_DOSE = 40


def streak(taken: Iterable[date], day: date) -> int:
    """Ile dni z rzędu suplement był wzięty, licząc do `day`.

    Gdy w `day` jeszcze nie wzięty, seria liczy się od dnia wcześniej: rano przed
    odhaczeniem nie pokazujemy zera, tylko serię do wczoraj.
    """
    days = set(taken)
    current = day if day in days else day - timedelta(days=1)
    count = 0
    while current in days:
        count += 1
        current -= timedelta(days=1)
    return count


def last_days(taken: Iterable[date], day: date, n: int = HISTORY_DAYS) -> list[bool]:
    """Czy wzięty w każdym z `n` dni kończących się na `day` (od najstarszego)."""
    days = set(taken)
    return [day - timedelta(days=offset) in days for offset in range(n - 1, -1, -1)]


def as_yesterday[T: Hashable](
    today: Iterable[T], yesterday: Iterable[T], active: Iterable[T]
) -> list[T]:
    """Stan dnia po „To co wczoraj": dzisiejsze plus wczorajsze, tylko z bieżącej listy.

    Niczego nie odznacza: jeśli dziś wzięte jest coś, czego wczoraj nie było, zostaje.
    Kolejność według listy suplementów.
    """
    chosen = set(today) | set(yesterday)
    return [supplement_id for supplement_id in active if supplement_id in chosen]


def supplement_errors(name: str, dose: str | None) -> list[str]:
    errors = []
    if not name.strip():
        errors.append("Nazwa suplementu nie może być pusta.")
    elif len(name.strip()) > MAX_NAME:
        errors.append(f"Nazwa suplementu może mieć najwyżej {MAX_NAME} znaków.")
    if dose is not None and len(dose.strip()) > MAX_DOSE:
        errors.append(f"Dawka może mieć najwyżej {MAX_DOSE} znaków.")
    return errors
