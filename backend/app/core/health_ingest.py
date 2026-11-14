"""Parsowanie danych zdrowotnych wysyłanych przez automatyzację Skrótów.

Skróty najłatwiej zwracają listę próbek jako tekst, po jednej wartości w linii, a przy
polskich ustawieniach z przecinkiem dziesiętnym. Parser przyjmuje więc zarówno listy
JSON, jak i tekst wieloliniowy, i toleruje jednostkę doklejoną do liczby („74,3 kg").
"""

import re
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

ALLOWED_TYPES = frozenset(
    {
        "weight", "body_fat", "steps", "active_energy", "sleep",
        "hrv", "resting_hr", "heart_rate", "spo2",
    }
)  # fmt: skip
MAX_SAMPLES = 5000
_NUMBER = re.compile(r"[-+]?\d+(?:[.,]\d+)?")


class IngestError(ValueError):
    pass


@dataclass(frozen=True)
class Sample:
    type: str
    source: str
    starts_at: datetime
    ends_at: datetime | None
    value: float | None
    label: str | None
    unit: str | None


def _as_list(raw: list | str | None) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        return [line.strip() for line in raw.splitlines() if line.strip()]
    return [str(item).strip() for item in raw]


def _parse_datetime(text: str, default_tz: ZoneInfo) -> datetime:
    try:
        dt = datetime.fromisoformat(text)
    except ValueError as exc:
        raise IngestError(f"Nieprawidłowa data (oczekiwany format ISO 8601): {text!r}") from exc
    return dt if dt.tzinfo else dt.replace(tzinfo=default_tz)


def _parse_value(text: str) -> tuple[float | None, str | None]:
    """Zwraca (liczba, None) albo (None, etykieta), np. dla faz snu."""
    match = _NUMBER.search(text.replace(" ", " "))
    if match and (match.start() == 0 or not text[: match.start()].strip()):
        return float(match.group().replace(",", ".")), None
    return None, text or None


def parse_ingest(
    type: str,
    starts: list | str,
    values: list | str,
    ends: list | str | None = None,
    unit: str | None = None,
    source: str = "shortcuts",
    default_timezone: str = "Europe/Warsaw",
) -> list[Sample]:
    if type not in ALLOWED_TYPES:
        raise IngestError(f"Nieznany typ {type!r}. Dozwolone: {', '.join(sorted(ALLOWED_TYPES))}")
    start_items, value_items, end_items = _as_list(starts), _as_list(values), _as_list(ends)
    if len(start_items) != len(value_items):
        raise IngestError(
            f"Liczba dat ({len(start_items)}) różni się od liczby wartości ({len(value_items)})."
        )
    if end_items and len(end_items) != len(start_items):
        raise IngestError("Liczba dat końcowych różni się od liczby dat początkowych.")
    if len(start_items) > MAX_SAMPLES:
        raise IngestError(f"Za dużo próbek w jednym żądaniu (limit {MAX_SAMPLES}).")

    tz = ZoneInfo(default_timezone)
    by_start: dict[datetime, Sample] = {}
    for i, (start_text, value_text) in enumerate(zip(start_items, value_items, strict=True)):
        value, label = _parse_value(value_text)
        starts_at = _parse_datetime(start_text, tz)
        by_start[starts_at] = Sample(
            type=type,
            source=source,
            starts_at=starts_at,
            ends_at=_parse_datetime(end_items[i], tz) if end_items else None,
            value=value,
            label=label,
            unit=unit,
        )
    # Ta sama data początkowa dwa razy w jednym żądaniu: wygrywa ostatnia.
    return list(by_start.values())
