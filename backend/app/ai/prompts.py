"""Polecenia dla modeli.

Zasada: model przepisuje i opisuje, nie liczy. Żadne polecenie nie prosi o przeliczanie
porcji, sumowanie ani szacowanie brakujących wartości (AGENTS.md, wymóg 1).
"""

LABEL_PROMPT = """\
Na zdjęciu jest etykieta produktu spożywczego z tabelą wartości odżywczych.
Przepisz tę tabelę do pól odpowiedzi.

Zasady:
- Przepisuj wyłącznie liczby widoczne na zdjęciu. Niczego nie przeliczaj, nie zaokrąglaj
  i nie szacuj.
- Bierz wartości z kolumny „na 100 g" albo „na 100 ml" i wpisz w polu basis, której użyto.
  Jeśli tabela ma tylko kolumnę na porcję, ustaw basis na "other" i zostaw wszystkie
  wartości odżywcze jako null.
- Energia: przepisz liczbę w kcal. Nie przepisuj wartości w kJ.
- Zapis „<0,5" przepisz jako 0.5. Przecinek dziesiętny zamień na kropkę.
- Jeśli wartości nie ma na etykiecie albo jest nieczytelna, wpisz null. Nie zgaduj.
- Nazwę i markę przepisz tylko wtedy, gdy widać je na zdjęciu.
- Jeśli na zdjęciu nie ma tabeli wartości odżywczych, ustaw basis na "other",
  a pozostałe pola na null.
"""


FOOD_QUERY_PROMPT = """\
Przetłumacz nazwę produktu spożywczego na krótkie zapytanie po angielsku do bazy USDA
FoodData Central, w jej stylu: rzeczownik, potem przecinki i cechy, np. „Oats, rolled",
„Chicken, breast, roasted", „Yogurt, plain, whole milk", „Bananas, raw".
Bez marki, bez gramatury, bez słów reklamowych. Produkt paczkowany opisz jako produkt
podstawowy, który go najlepiej przypomina (serek wiejski -> „Cheese, cottage").
Produkt: «{name}»
"""
