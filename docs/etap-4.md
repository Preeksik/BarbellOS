# Etap 4: trening

Specyfikacja: `docs/DOKUMENTACJA.md`, rozdział 5 (5.3–5.6).

| Część | Stan |
|---|---|
| Kalendarz sezonu, statusy, „ostatnio”, sugestie TM, wybór sesji (`core/season.py`) | kod gotowy 25.11.2026; zgodny z oryginałem na prawdziwym dzienniku (zero różnic) |
| Zakładka „Trening”: oś sezonu, tydzień, dni, sesja, wpisy przez kolejkę offline | kod gotowy 25.11.2026 |
| Import planu i dziennika ze starego pliku | kod gotowy 25.11.2026 |
| Sprzęt w Profilu: talerze 25 / 20 kg, zaciski | kod gotowy 25.11.2026 |
| Animacje techniki: boje ze sztangą i warianty | kod gotowy 25.11.2026 |
| Część 2: Sezon, Maksy, Start, Zasady; arkusz podejść; data zawodów; „Zastosuj” TM | kod gotowy 26.11.2026; zgodny z oryginałem (zero różnic) |

## Przeniesienie planu i dziennika

Plan i dziennik są osobiste, więc nie ma ich w repo. Plik do importu leży lokalnie w `exports/trening-import.json` (plan z artefaktu z 22.11.2026, ustawienia i 23 sesje dziennika, od t01-D1 do t06-D1).

1. Do czasu przejścia trenujesz ze starego pliku jak dotąd. W dniu przejścia poproś agenta o świeży plik importu, żeby objął ostatnie treningi.
2. Na komputerze otwórz aplikację w przeglądarce i zaloguj się → Profil → „Trening” → „Wybierz plik” → `exports/trening-import.json` (bez planu na serwerze to samo jest od razu w zakładce Trening).
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
10. Tydzień 10 (test): arkusz „Podejścia”: przy numerze ciężar z planu, pola kg i RPE, ✓ / ✕ (drugie stuknięcie zdejmuje ocenę). Po zaliczonym drugim z RPE pod bojem pojawia się ciężar trzeciego, po trzech zaliczonych bojach suma i punkty GL.
11. Profil → „Trening” → „20 kg”: wróć do Treningu, talerze przy ćwiczeniach liczą się z dwudziestek (np. 142,5 kg = 20+20+20+1,25 na stronę). Przełącz z powrotem na 25 kg. „2 × 2,5 kg” przy zaciskach zmniejsza talerze o 2,5 kg na stronę.
12. Przy przysiadzie, ławie, martwym i ich wariantach przycisk „Technika”: ludzik płynnie robi ruch, pod spodem nazwa fazy („pauza 2 s”, „siad na piny”). Stuknięcie w obrazek zatrzymuje. Sprawdź, czy animacja nie przycina przewijania i czy działa w trybie samolotowym.
13. Ustawienia → Dostępność → Ruch → „Ogranicz ruch”: animacja startuje zatrzymana w dolnej pozycji, „Odtwórz” ją uruchamia.
14. Podzakładki pod osią: Trening, Sezon, Maksy, Start, Zasady. Sezon: stuknięcie tygodnia otwiera go w Treningu.
15. Maksy: zmień TM jednego boju w bloku i wyjdź z pola: pojawia się „wpisane ręcznie”, a ciężary w tygodniach tego bloku się zmieniają. Wyczyść pole: wraca wartość z planu. Wykres: stuknij, pod nim wartości z tego dnia. Kalkulator: 150 kg × 1 na RPE 8 daje ok. 162,5 kg.
16. Start: tabele podejść i rozgrzewki dla testu i zawodów, „Otwórz arkusz testu” przenosi do tygodnia 10. Zmiana daty zawodów (np. 29.05) dopisuje „Dopasowanie do daty: dodatkowy tydzień …”, a oś sezonu ma więcej krążków. Wróć do 15.05: dopasowanie znika.
17. Zasady: cały tekst ze starego pliku (skala RPE jako tabela).
18. Bez sieci: zmiana TM czeka w kolejce i wysyła się po powrocie; zmiana daty zawodów i kalkulator mówią, że potrzebują połączenia.
