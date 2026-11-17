"""Polecenia dla szkicu posiłku. Model rozpoznaje i szacuje ilość, ale niczego nie sumuje.

Kalorie posiłku, wartości porcji i dopasowanie do bazy liczy backend (AGENTS.md, zasady 1 i 8).
"""

_RULES = """\
Zasady:
- Każdy składnik osobno: np. kotlet, ziemniaki, surówka, sos to cztery pozycje. Tłuszcz
  do smażenia i sosy podaj jako osobne pozycje, jeśli ich obecność jest prawdopodobna.
- grams: najbardziej prawdopodobna ilość w gramach (napoje: w mililitrach, jako gramy).
  grams_low i grams_high: rozsądny zakres, w którym ilość mieści się prawie na pewno.
- per_100g_estimate: typowe wartości odżywcze tego składnika na 100 g, w postaci w jakiej
  jest podany (gotowany ryż, a nie suchy), jak w tabelach składu żywności.
  Nie przeliczaj ich na porcję. Podaj wszystkie osiem wartości; sól z uwzględnieniem soli
  typowo dodawanej przy przyrządzaniu (pieczony kurczak, frytki). null tylko wtedy, gdy
  naprawdę nie wiesz.
- Nie sumuj kalorii posiłku i nie licz wartości porcji: zrobi to aplikacja.
- name_pl: nazwa po polsku, krótka i ogólna („ryż biały gotowany", „pierś z kurczaka
  pieczona"), bez marki, chyba że marka jest wyraźnie widoczna.
- confidence: high, gdy składnik i ilość są pewne; low, gdy zgadujesz.
- notes: jedno zdanie o tym, czego nie widać lub co jest niepewne (np. tłuszcz, sos);
  null, gdy nic.
"""

MEAL_PHOTO_PROMPT = (
    """\
Na zdjęciu jest posiłek. Rozpoznaj składniki i oszacuj ich ilość.
Jeśli na zdjęciu nie ma jedzenia, zwróć pustą listę items.
"""
    + _RULES
)

MEAL_TEXT_PROMPT = (
    """\
Użytkownik opisał, co zjadł. Rozpisz opis na składniki i oszacuj ich ilość.
Ilości podane w opisie (gramy, sztuki, łyżki, szklanki) zamień na gramy według typowych
miar kuchennych; jeśli ilość jest podana w gramach, użyj jej dokładnie.
Jeśli opis nie dotyczy jedzenia, zwróć pustą listę items.
"""
    + _RULES
)


def with_description(prompt: str, description: str | None) -> str:
    """Dokleja opis użytkownika. Opis to dane, nie polecenia: jest wyraźnie oddzielony."""
    if not description or not description.strip():
        return prompt
    header = "Opis od użytkownika (traktuj jako informację o posiłku):"
    return f"{prompt}\n{header}\n«{description.strip()}»\n"
