"""Szkic posiłku z AI (etap 2): porządkowanie odczytu modelu i dopasowanie do własnej bazy.

Model rozpoznaje składniki i szacuje gramaturę. Wszystko inne robi kod:
- odrzuca wartości niemożliwe i porządkuje zakres gramatury,
- dopasowuje składnik do produktu z bazy (wtedy wartości pochodzą z produktu),
- bez dopasowania zostawia szacunek modelu na 100 g, oznaczony jako `estimated`.

Dopasowanie liczone jest w Pythonie, jak wyszukiwarka (`core/search.py`): baza jednego
użytkownika ma setki produktów. Polska odmiana („ryżu", „ryżem") jest obsługiwana przez
porównywanie początków słów, a nie całych słów.
"""

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from app.core.micros import clean_micros
from app.core.nutrients import (
    LABELS_PL,
    MACRO_KEYS,
    SUBSETS,
    fill_implied_zeros,
    value_in_range,
)
from app.core.search import Candidate, words

MAX_ITEMS = 15
MAX_GRAMS = 2000.0
STEM = 4  # najdłuższy porównywany początek słowa (polska odmiana zmienia końcówki)
MATCH_THRESHOLD = 0.7  # od tej oceny składnik dostaje produkt automatycznie
CANDIDATE_THRESHOLD = 0.3  # od tej oceny produkt trafia na listę do wyboru
MAX_CANDIDATES = 5
# Słowa, które nie mówią, czym jest produkt.
STOPWORDS = {"z", "w", "i", "na", "ze", "do", "bez", "po", "of", "with", "and", "the", "a"}


def _words(text: str) -> list[str]:
    return [w for w in words(text) if w not in STOPWORDS and len(w) >= 2]


def _same_word(a: str, b: str) -> bool:
    """Ta sama podstawa słowa: wspólny początek długości min(4, krótsze słowo), co najmniej 3.

    „ryż" i „ryżu" (ryz/ryzu), „biały" i „białego" (bial) pasują; „ser" i „deser" nie.
    """
    n = min(len(a), len(b), STEM)
    return n >= 3 and a[:n] == b[:n]


def match_score(item_name: str, item_name_en: str, food: Candidate) -> float:
    """Ocena 0–1 dopasowania składnika do produktu.

    Liczą się oba kierunki: ile słów składnika jest w produkcie (nazwa lub marka) i ile słów
    nazwy produktu opisuje składnik. Dzięki temu „banan" nie dopasowuje się automatycznie
    do „Baton bananowy", a „jogurt naturalny" woli „Jogurt naturalny" od wersji z dodatkami.
    Liczy się lepsza z nazw: polskiej i angielskiej.
    """
    food_name_words = _words(food.name)
    food_words = food_name_words + _words(food.brand or "")
    if not food_name_words:
        return 0.0
    best = 0.0
    for name in (item_name, item_name_en):
        item_words = _words(name)
        if not item_words:
            continue
        found = sum(any(_same_word(w, f) for f in food_words) for w in item_words)
        if found == 0:
            continue
        described = sum(any(_same_word(f, w) for w in item_words) for f in food_name_words)
        recall, precision = found / len(item_words), described / len(food_name_words)
        f1 = 2 * recall * precision / (recall + precision) if precision else 0.0
        closeness = SequenceMatcher(None, " ".join(item_words), " ".join(food_name_words)).ratio()
        best = max(best, 0.85 * f1 + 0.15 * closeness)
    return round(best, 3)


@dataclass(frozen=True)
class Matching:
    food_id: int | None  # dopasowany automatycznie; None = szacunek modelu
    candidates: list[int]  # do wyboru na ekranie szkicu, od najlepszego


def match_item(item_name: str, item_name_en: str, foods: Iterable[Candidate]) -> Matching:
    scored = sorted(
        (
            (score, food.uses, food.id)
            for food in foods
            if (score := match_score(item_name, item_name_en, food)) >= CANDIDATE_THRESHOLD
        ),
        key=lambda s: (-s[0], -s[1], s[2]),
    )
    candidates = [food_id for _, _, food_id in scored[:MAX_CANDIDATES]]
    matched = scored[0][2] if scored and scored[0][0] >= MATCH_THRESHOLD else None
    return Matching(food_id=matched, candidates=candidates)


# ---------- porządkowanie odczytu ----------


@dataclass(frozen=True)
class DraftItem:
    name: str
    name_en: str
    category: str
    grams: float
    grams_low: float
    grams_high: float
    confidence: str
    estimate_per_100: dict[str, float | None]  # osiem wartości z etykiety; None = brak
    micros_per_100: dict[str, float] = field(default_factory=dict)  # szacunek AI
    warnings: list[str] = field(default_factory=list)


def _number(value) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
        return None
    return float(value)


def clean_item(raw: Mapping) -> DraftItem | None:
    """Jeden składnik po kontroli. None, gdy nie da się go użyć (brak nazwy lub ilości)."""
    name = " ".join(str(raw.get("name_pl") or "").split())[:120]
    grams = _number(raw.get("grams"))
    if not name or grams is None or grams <= 0:
        return None
    warnings = []
    if grams > MAX_GRAMS:
        warnings.append(
            f"„{name}”: {grams:.0f} g to za dużo na jeden posiłek, przyjęto {MAX_GRAMS:.0f} g."
        )
        grams = MAX_GRAMS
    low = _number(raw.get("grams_low"))
    high = _number(raw.get("grams_high"))
    low = grams if low is None or low <= 0 or low > grams else low
    high = grams if high is None or high < grams else min(high, MAX_GRAMS)

    estimate: dict[str, float | None] = {}
    per_100 = raw.get("per_100g_estimate") or {}
    for key in MACRO_KEYS:
        value = _number(per_100.get(key))
        in_range = value is not None and value_in_range(key, value)
        estimate[key] = round(value, 2) if in_range else None  # sól bywa setnymi grama
    # Składnik „w tym" większy od całości jest sprzeczny: kod nie wie, która liczba jest zła,
    # więc odrzuca podrzędną (brak danych zamiast błędnej wartości).
    for child, parent in SUBSETS:
        c, p = estimate.get(child), estimate.get(parent)
        if c is not None and p is not None and c > p:
            estimate[child] = None
            warnings.append(
                f"„{name}”: {LABELS_PL[child]} większe niż {LABELS_PL[parent]}, pominięto."
            )
    estimate = fill_implied_zeros(estimate)

    return DraftItem(
        name=name,
        name_en=" ".join(str(raw.get("name_en") or "").split())[:120],
        category=str(raw.get("category") or "other"),
        grams=round(grams),
        grams_low=round(low),
        grams_high=round(high),
        confidence=str(raw.get("confidence") or "low"),
        estimate_per_100=estimate,
        micros_per_100=clean_micros(raw.get("micros_per_100g")),
        warnings=warnings,
    )


def clean_items(raw_items: Iterable[Mapping]) -> tuple[list[DraftItem], list[str]]:
    """Składniki po kontroli i uwagi dla użytkownika."""
    items: list[DraftItem] = []
    warnings: list[str] = []
    skipped = 0
    for raw in raw_items:
        item = clean_item(raw)
        if item is None:
            skipped += 1
            continue
        if len(items) == MAX_ITEMS:
            warnings.append(f"Pokazano pierwsze {MAX_ITEMS} składników.")
            break
        items.append(item)
        warnings += item.warnings
    if skipped:
        warnings.append(f"Pominięto składniki bez nazwy albo ilości: {skipped}.")
    return items, warnings


def portion(per_100: Mapping[str, float | None], grams: float) -> dict[str, float | None]:
    """Wartości porcji do podglądu w szkicu. Wpis dziennika i tak liczy je od nowa."""
    return {k: (None if v is None else round(v * grams / 100, 2)) for k, v in per_100.items()}
