"""Wyszukiwanie produktów we własnej bazie (etap 1, krok 5).

Baza jednego użytkownika ma setki, nie miliony produktów, więc dopasowanie jest liczone
w Pythonie. Działa tak samo na Postgresie i na SQLite i nie wymaga rozszerzeń.
Gdy baza urośnie (tabela `generic_foods` w etapie 6), wstępny filtr przejdzie na pg_trgm.
"""

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass

# Litery, których NFKD nie rozkłada na literę bazową i znak diakrytyczny.
_EXTRA_FOLD = str.maketrans({"ł": "l", "Ł": "l", "ß": "ss", "ø": "o", "æ": "ae"})
_WORD = re.compile(r"[0-9a-z]+")
MIN_QUERY = 2  # krótsze zapytanie pasowałoby do wszystkiego


def fold(text: str) -> str:
    """Małe litery bez polskich znaków: „Śmietanka ŁACIATA" -> „smietanka laciata"."""
    decomposed = unicodedata.normalize("NFKD", text.translate(_EXTRA_FOLD))
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch)).lower()


def words(text: str) -> list[str]:
    return _WORD.findall(fold(text))


@dataclass(frozen=True)
class Candidate:
    id: int
    name: str
    brand: str | None
    favorite: bool = False
    uses: int = 0  # ile razy produkt trafił do dziennika


def match_score(query: str, candidate: Candidate) -> float | None:
    """Ocena dopasowania albo None, gdy produkt nie pasuje.

    Każde słowo zapytania musi być początkiem któregoś słowa nazwy albo marki,
    więc „ser wiej" znajduje „Serek wiejski", a „ser" nie znajduje „deser".
    """
    query_words = words(query)
    if not query_words or len("".join(query_words)) < MIN_QUERY:
        return None
    name_words = words(candidate.name)
    brand_words = words(candidate.brand or "")
    score = 0.0
    for q in query_words:
        if any(w.startswith(q) for w in name_words):
            score += 2.0 if q in name_words else 1.5  # całe słowo wyżej niż początek
        elif any(w.startswith(q) for w in brand_words):
            score += 1.0
        else:
            return None
    if name_words and name_words[0].startswith(query_words[0]):
        score += 1.0  # nazwa zaczyna się od zapytania
    # Produkty znane z dziennika i ulubione wyżej: to je najczęściej wybierasz.
    score += min(candidate.uses, 20) * 0.05 + (0.5 if candidate.favorite else 0.0)
    return score


def rank(query: str, candidates: Iterable[Candidate], limit: int = 30) -> list[int]:
    """Identyfikatory pasujących produktów od najlepszego dopasowania."""
    scored = [
        (score, c.name.casefold(), c.id)
        for c in candidates
        if (score := match_score(query, c)) is not None
    ]
    scored.sort(key=lambda item: (-item[0], item[1], item[2]))
    return [food_id for _, _, food_id in scored[:limit]]
