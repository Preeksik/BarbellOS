# Etap 6: witaminy i minerały

Zrobione przed etapem 3 (Apple Zdrowie), na życzenie. Specyfikacja: `docs/DOKUMENTACJA.md`, rozdziały 4.2 i 4.11.

| Część | Stan |
|---|---|
| Dopasowanie produktu do tabeli USDA (AI tłumaczy, kod wybiera; od 18.11.2026 automatycznie, bez zatwierdzania) | kod gotowy 18.11.2026; sprawdzone z prawdziwym USDA na kopii Twojej bazy |
| Szacunek mikroskładników od AI dla składników posiłku spoza bazy | kod gotowy 18.11.2026; sprawdzone z prawdziwym Gemini |
| Uzupełnianie wcześniejszych wpisów (jawna akcja) | kod gotowy 18.11.2026 |
| Widok tygodnia: średnie, kalorie dzień po dniu, pokrycie norm ze źródłami | kod gotowy 18.11.2026 |

## Przygotowanie

1. Po pobraniu zmian: `alembic upgrade head` w katalogu `backend` (kolumny `food.fdc_id`, `food.fdc_description`, `food.fdc_checked_at`).
2. **Klucz USDA (zalecany):** https://fdc.nal.usda.gov/api-key-signup, potem w `.env` wpis `FDC_API_KEY=...`. Bez klucza działa klucz demonstracyjny, ale tylko ok. 10 zapytań na godzinę.

## Co sprawdzić

1. „Dodaj" → wyszukaj produkt, który często jesz (np. płatki) → otwórz → „Witaminy i minerały" → „Dopasuj do tabeli USDA".
2. W polu jest zapytanie po angielsku (np. „Oats, rolled"), a pod nim kandydaci z kaloriami. Podpowiedź jest zaznaczona; porównaj kalorie z produktem. Jeśli żaden nie pasuje, popraw zapytanie i „Szukaj".
3. „Użyj wybranego": karta pokazuje mikroskładniki ze źródłem „tabela USDA" (produkt bez kodu) albo „szacunek" (produkt paczkowany: wartości z podobnego produktu podstawowego). Wartości z etykiety zostają.
4. „Uzupełnij witaminy we wcześniejszych wpisach tego produktu": komunikat „Uzupełniono wpisy: N". Kalorie w dzienniku się nie zmieniają.
5. Dziennik → „Tydzień (7 dni)": średnio dziennie (z dni z wpisami), kalorie dzień po dniu, witaminy i minerały z procentem normy i opisem „dokładne … · przybliżone … · brak …".
5a. Karta „Dane o witaminach": przy otwarciu tygodnia pojawia się „Uzupełniam witaminy z tabel USDA…", potem „Uzupełniono: …". Po przełączeniu zakładki i powrocie dane zostają, a karta niczego już nie uzupełnia. Sprawdzone 18.11.2026 na kopii Twojej bazy: Gouda, filet z kurczaka i Coca-Cola dopasowane same, witaminy dla 70% kalorii tygodnia.
5b. Dodaj nowy produkt do dziennika i po chwili otwórz jego kartę: „Witaminy i minerały" mają dane z tabeli bez żadnego klikania.
6. Dodaj posiłek przez AI (opis albo zdjęcie): składniki spoza bazy mają szacunek witamin, a w tygodniu rośnie udział „szacunek".
7. Gdy większość kalorii tygodnia nie ma danych o składniku, pasek jest szary z dopiskiem „za mało danych". Dopasuj do tabeli produkty, które jesz najczęściej; to najszybciej podnosi udział danych z tabel.

## Na telefonie

8. Dopasowanie do tabeli wymaga sieci: w trybie samolotowym pokazuje błąd i niczego nie psuje.
9. Widok tygodnia bez sieci pokazuje ostatnio pobrany tydzień albo komunikat, że potrzebne jest połączenie.
