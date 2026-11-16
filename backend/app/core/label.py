"""Zdjęcie etykiety: rozpoznanie formatu obrazu i uporządkowanie odczytu modelu.

Model tylko przepisuje tabelę wartości odżywczych. Wszystko, co wymaga liczenia albo
oceny (zakresy, spójność, zera wynikające z etykiety), dzieje się tutaj, w kodzie.
Wynik jest szkicem formularza: zapis następuje dopiero po zatwierdzeniu przez użytkownika.
"""

import math
from collections.abc import Mapping
from dataclasses import dataclass, field

from app.core.nutrients import (
    LABELS_PL,
    MACRO_KEYS,
    fill_implied_zeros,
    macro_errors,
    macro_warnings,
    value_in_range,
)

MAX_SERVING = 5000.0  # ta sama granica co w formularzu produktu
MAX_TEXT = 255

# Początek pliku -> typ MIME. Formaty przyjmowane przez modele z obsługą obrazu.
_HEIF_BRANDS = {
    b"heic": "image/heic",
    b"heix": "image/heic",
    b"hevc": "image/heic",
    b"hevx": "image/heic",
    b"mif1": "image/heif",
    b"msf1": "image/heif",
    b"heim": "image/heif",
    b"heis": "image/heif",
}

# Kolumna tabeli wybrana przez model -> jednostka produktu.
_BASIS_UNIT = {"100g": "g", "100ml": "ml"}


def image_mime(data: bytes) -> str | None:
    """Typ obrazu rozpoznany po zawartości, a nie po deklaracji przeglądarki."""
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data[4:8] == b"ftyp":
        return _HEIF_BRANDS.get(data[8:12])
    return None


@dataclass(frozen=True)
class LabelDraft:
    """Szkic do formularza produktu. `None` oznacza „nie odczytano", nigdy zero."""

    name: str | None
    brand: str | None
    serving_g: float | None
    unit: str | None  # "g" | "ml"; None, gdy nie wiadomo, czego dotyczy tabela
    macros: dict[str, float | None]
    warnings: list[str] = field(default_factory=list)

    @property
    def found(self) -> int:
        """Ile z ośmiu wartości udało się odczytać."""
        return sum(value is not None for value in self.macros.values())


def _text(value) -> str | None:
    cleaned = " ".join(str(value).split()) if value is not None else ""
    return cleaned[:MAX_TEXT] or None


def _number(value) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
        return None
    return float(value)


def label_draft(extract: Mapping) -> LabelDraft:
    """Zamienia odczyt modelu na szkic produktu.

    Wartość niemożliwa (ujemna, ponad 100 g w 100 g, ponad 900 kcal) nie trafia do
    formularza: pole zostaje puste, a użytkownik dostaje informację, co odrzucono.
    Sprzeczność między polami (np. cukry większe od węglowodanów) zostaje widoczna
    razem z ostrzeżeniem, bo kod nie wie, która z dwóch liczb jest błędna.
    """
    unit = _BASIS_UNIT.get(str(extract.get("basis") or ""))
    warnings: list[str] = []

    macros: dict[str, float | None] = {}
    for key in MACRO_KEYS:
        value = _number(extract.get(key))
        if value is not None and not value_in_range(key, value, unit or "g"):
            warnings.append(
                f"{LABELS_PL[key].capitalize()}: odczytana wartość {value:g} jest niemożliwa, "
                "pole zostało puste."
            )
            value = None
        macros[key] = None if value is None else round(value, 2)
    macros = fill_implied_zeros(macros)

    found = sum(value is not None for value in macros.values())
    if found and unit is None:
        warnings.append(
            "Nie widać, czy tabela podaje wartości na 100 g, czy na 100 ml. Sprawdź jednostkę."
        )
    warnings += macro_errors(macros, unit or "g")
    warnings += macro_warnings(macros)

    serving = _number(extract.get("serving_g"))
    if serving is not None and not 0 < serving <= MAX_SERVING:
        serving = None

    return LabelDraft(
        name=_text(extract.get("name")),
        brand=_text(extract.get("brand")),
        serving_g=serving,
        unit=unit,
        macros=macros,
        warnings=warnings,
    )
