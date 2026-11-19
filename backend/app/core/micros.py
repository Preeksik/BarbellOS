"""Mikroskładniki (etap 6): źródło wartości, kontrola szacunku AI, dopasowanie do tabeli USDA.

Trzy poziomy pewności (dokumentacja 4.2):
- `label`: z etykiety (Open Food Facts, rzadko dla witamin),
- `reference`: z tabeli USDA dla tego samego produktu podstawowego (banan, szpinak),
- `estimated`: przybliżenie: produkt paczkowany dziedziczy wartości z najbliższego
  produktu podstawowego albo składnik potrawy ma szacunek modelu AI.
"""

import math
from collections.abc import Iterable, Mapping

from app.core.search import words

# Górne granice na 100 g. [ZAŁOŻENIE] Z zapasem ponad najbogatsze znane źródła (wątroba,
# tran, drożdże, sól), żeby odrzucić tylko pomyłki w rzędzie wielkości (mg zamiast µg).
MICRO_LIMITS: dict[str, float] = {
    "vit_a": 30_000,
    "vit_d": 300,
    "vit_e": 200,
    "vit_k": 2_000,
    "vit_c": 3_000,
    "vit_b1": 30,
    "vit_b2": 30,
    "vit_b3": 150,
    "vit_b6": 30,
    "folate": 5_000,
    "vit_b12": 200,
    "calcium": 5_000,
    "iron": 100,
    "magnesium": 1_500,
    "zinc": 200,
    "potassium": 15_000,
    "sodium": 40_000,
    "phosphorus": 5_000,
    "selenium": 2_000,
    "iodine": 5_000,
}

# Produkt, który ma wartości z etykiety, ma też pierwszeństwo przed tabelą.
SOURCE_RANK = {"label": 3, "user": 3, "reference": 2, "estimated": 1}


def table_source(has_barcode: bool) -> str:
    """Źródło wartości z tabeli USDA dla produktu.

    Produkt podstawowy bez kodu (banan, ryż) ma wartości z tabeli dla tego samego
    produktu: `reference`. Produkt paczkowany (serek z kodem) dziedziczy wartości
    z najbliższego produktu podstawowego: to przybliżenie, więc `estimated`.
    """
    return "estimated" if has_barcode else "reference"


def clean_micros(raw: Mapping | None) -> dict[str, float]:
    """Mikroskładniki z szacunku lub tabeli po kontroli: znane, liczbowe, w rozsądnym zakresie.

    Wartość nieznana albo niemożliwa jest pomijana (brak danych), nigdy zamieniana na zero.
    """
    out: dict[str, float] = {}
    for nutrient_id, limit in MICRO_LIMITS.items():
        value = (raw or {}).get(nutrient_id)
        if isinstance(value, bool) or not isinstance(value, int | float):
            continue
        if not math.isfinite(value) or not 0 <= value <= limit:
            continue
        out[nutrient_id] = round(float(value), 3)
    return out


def merge_micros(
    existing: Mapping[str, tuple[float, str]], new: Mapping[str, float], source: str
) -> dict[str, tuple[float, str]]:
    """Łączy mikroskładniki produktu: nowe źródło nie nadpisuje pewniejszego (etykiety)."""
    out = dict(existing)
    for nutrient_id, amount in new.items():
        current = out.get(nutrient_id)
        if current is None or SOURCE_RANK.get(current[1], 0) <= SOURCE_RANK.get(source, 0):
            out[nutrient_id] = (amount, source)
    return out


# ---------- dopasowanie do tabeli USDA ----------


def _base(word: str) -> str:
    """Słowo angielskie bez liczby mnogiej: „oats" -> „oat", „tomatoes" -> „tomato"."""
    if len(word) > 4 and word.endswith("es"):
        return word[:-2]
    if len(word) > 3 and word.endswith("s"):
        return word[:-1]
    return word


def fdc_score(query: str, description: str) -> float:
    """Ocena 0–1 dopasowania zapytania po angielsku do opisu rekordu USDA.

    Opisy USDA mają postać „Rzeczownik, cechy, …" („Oats, whole grain, rolled"), więc
    najważniejsza jest zgodność pierwszego słowa. Słowa porównujemy w całości (z liczbą
    mnogą), a nie po początkach: „rolled" to nie „rolls".
    """
    query_words = [_base(w) for w in words(query)]
    food_words = [_base(w) for w in words(description)]
    if not query_words or not food_words:
        return 0.0
    head = 1.0 if query_words[0] == food_words[0] else 0.0
    recall = sum(w in food_words for w in query_words) / len(query_words)
    precision = sum(w in query_words for w in food_words) / len(food_words)
    return round(0.5 * head + 0.35 * recall + 0.15 * precision, 3)


def rank_fdc(query: str, candidates: Iterable[tuple[int, str]]) -> list[tuple[int, float]]:
    """Kandydaci z tabeli USDA (id, opis) od najlepiej pasującego do zapytania.

    Wyszukiwarka USDA potrafi postawić na pierwszym miejscu coś obok („oats rolled" ->
    „Rolls, dinner, oat bran"). Przy równej ocenie zostaje kolejność USDA. Ostateczny
    wybór i tak zatwierdza użytkownik.
    """
    scored = [(fdc_id, fdc_score(query, description)) for fdc_id, description in candidates]
    order = {fdc_id: i for i, (fdc_id, _) in enumerate(scored)}
    return sorted(scored, key=lambda s: (-s[1], order[s[0]]))


def fill_missing_micros(
    entry_micros: Mapping[str, dict] | None,
    food_micros: Mapping[str, tuple[float, str]],
    amount: float,
) -> dict[str, dict] | None:
    """Uzupełnia brakujące mikroskładniki wpisu z obecnych danych produktu.

    Jawna akcja użytkownika („uzupełnij witaminy we wcześniejszych wpisach"), a nie efekt
    uboczny edycji. Istniejące wartości wpisu zostają nietknięte, zamrożone kalorie
    i makro też. Zwraca None, gdy nie ma czego dodać.
    """
    current = dict(entry_micros or {})
    added = {
        nutrient_id: {"amount": per_100 * amount / 100, "source": source}
        for nutrient_id, (per_100, source) in food_micros.items()
        if nutrient_id not in current
    }
    return {**current, **added} if added else None


# Wpis albo produkt z mniej niż tyloma mikroskładnikami traktujemy jako „bez danych
# o witaminach": etykiety podają zwykle tylko sód, a to nie mówi nic o witaminach.
MIN_MICROS = 5
# Od tej oceny dopasowanie jest przyjmowane bez pytania. 0,35 (19.11.2026, wcześniej 0,5):
# wszystkie słowa zapytania w innej kolejności niż w tabeli („Iceberg lettuce" przy
# „Lettuce, iceberg…") dają ok. 0,4 i mają przejść; samo wspólne słowo („Apple juice"
# przy „Pineapple juice") daje ok. 0,25 i nie przechodzi. Witaminy to szacunek, a pytanie
# o każdy produkt było uciążliwe (decyzja właściciela).
AUTO_MATCH_SCORE = 0.35
# Kalorie rekordu USDA mogą się różnić od produktu (napój light, inny tłuszcz), ale nie
# kilkukrotnie: wtedy to inny produkt (np. olej owsiany zamiast płatków).
MAX_KCAL_RATIO = 2.5


def kcal_plausible(food_kcal: float | None, record_kcal: float | None) -> bool:
    if not food_kcal or not record_kcal:
        return True  # brak danych do porównania: decyduje ocena nazwy
    ratio = record_kcal / food_kcal
    return 1 / MAX_KCAL_RATIO <= ratio <= MAX_KCAL_RATIO


GENERIC_LIMIT = 6  # tyle produktów podstawowych pokazuje wyszukiwarka


def generic_candidates(
    query: str,
    candidates: Iterable[tuple[int, str, float | None]],
    limit: int = GENERIC_LIMIT,
) -> list[int]:
    """Rekordy USDA do wyszukiwarki produktów (19.11.2026): najlepsze według nazwy.

    Bez kalorii rekord jest bezużyteczny w dzienniku, więc odpada. Próg ten sam co przy
    automatycznym dopasowaniu witamin: jedno wspólne słowo to za mało.
    """
    candidates = list(candidates)
    kcal_of = {fdc_id: kcal for fdc_id, _, kcal in candidates}
    ranked = rank_fdc(query, [(fdc_id, description) for fdc_id, description, _ in candidates])
    chosen = [
        fdc_id
        for fdc_id, score in ranked
        if score >= AUTO_MATCH_SCORE and kcal_of[fdc_id] is not None
    ]
    return chosen[:limit]


def auto_match(
    query: str, food_kcal: float | None, candidates: Iterable[tuple[int, str, float | None]]
) -> int | None:
    """Rekord USDA przyjmowany automatycznie albo None (wtedy wybór zostaje ręczny).

    Najlepszy według nazwy, pod warunkiem pewnej oceny i wiarygodnych kalorii.
    """
    candidates = list(candidates)
    kcal_of = {fdc_id: kcal for fdc_id, _, kcal in candidates}
    for fdc_id, score in rank_fdc(query, [(fdc_id, d) for fdc_id, d, _ in candidates]):
        if score < AUTO_MATCH_SCORE:
            return None
        if kcal_plausible(food_kcal, kcal_of[fdc_id]):
            return fdc_id
    return None
