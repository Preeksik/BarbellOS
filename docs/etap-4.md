# Etap 4: trening

Specyfikacja: `docs/DOKUMENTACJA.md`, rozdział 5 (5.3, 5.4).

| Część | Stan |
|---|---|
| Kalendarz sezonu, statusy, „ostatnio”, sugestie TM, wybór sesji (`core/season.py`) | kod gotowy 25.11.2026; zgodny z oryginałem na prawdziwym dzienniku (zero różnic) |
| Zakładka „Trening”: oś sezonu, tydzień, dni, sesja, wpisy przez kolejkę offline | kod gotowy 25.11.2026 |
| Import planu i dziennika ze starego pliku | kod gotowy 25.11.2026 |
| Zakładki sezonu, maksów, startu i zasady; arkusz podejść; data zawodów | część 2 |

## Przeniesienie planu i dziennika

Plan i dziennik są osobiste, więc nie ma ich w repo. Plik do importu leży lokalnie w `exports/trening-import.json` (plan z artefaktu z 22.11.2026, ustawienia i 23 sesje dziennika, od t01-D1 do t06-D1).

1. Do czasu przejścia trenujesz ze starego pliku jak dotąd. W dniu przejścia poproś agenta o świeży plik importu, żeby objął ostatnie treningi.
2. Na komputerze otwórz aplikację w przeglądarce i zaloguj się → „Trening” → „Wybierz plik” → `exports/trening-import.json`.
3. Komunikat: „Wgrano »Plan AMP 2027«: 29 tygodni, 139 sesji, z dziennika 23.” bez pominiętych sesji.
4. Import można powtórzyć: sesje z pliku zastępują te same sesje w aplikacji, pozostałe zostają. Nie importuj starego pliku po tym, jak zaczniesz wpisywać w aplikacji te same sesje, bo zastąpi wpisy.

## Co sprawdzić na iPhonie

1. „Nowa wersja aplikacji” → zakładka „Trening” (druga od lewej, ikona sztangi).
2. Na górze: numer tygodnia, blok i odliczanie do testu i do zawodów. Pod spodem rząd krążków: bieżący tydzień ma kreskę pod spodem, wybrany jest obrysowany. Stuknij krążek innego tygodnia: otwiera się ten tydzień.
3. Po otwarciu widać sesję po ostatniej zapisanej (teraz: tydzień 6, D2). „Wróć do najbliższego treningu” wraca do niej z innego tygodnia.
4. Ciężary jak w starym pliku: porównaj jedną sesję z tygodnia 4 (stałe ciężary) i jedną z tygodnia 6 (z TM 170 / 130 / 210). Talerze na stronę zgadzają się z ciężarem.
5. Wpisz kg, powtórzenia i RPE w serii, odczekaj sekundę: pod spodem pojawia się e1RM. „Odhacz” przy pustym polu kg wpisuje ciężar z planu. Kreska pod dniem robi się zielona do połowy, a po odhaczeniu wszystkiego cała.
6. Akcesoria pokazują „Ostatnio: … kg, data, siłownia”.
7. Siłownia: stuknij podpowiedź; masa ciała i notatka zapisują się po wyjściu z pola. Zamknij aplikację i otwórz ponownie: wszystko zostaje.
8. **Bez zasięgu:** włącz tryb samolotowy, wpisz serię i odhacz ją, zamknij aplikację przesunięciem w górę. Otwórz ponownie (nadal bez sieci): wpis jest, na górze „niewysłane”. Włącz sieć: znacznik znika, a po odświeżeniu widać e1RM.
9. Sąsiednie tygodnie działają bez sieci, jeśli były otwarte z siecią (aplikacja pobiera je od razu).
10. Tydzień 10 (test): sekcja „Podejścia” z ciężarem, RPE i przyciskami ✓ / ✕; drugie stuknięcie zdejmuje ocenę.
