# Etap 1: dziennik diety

Cel: przez tydzień logować jedzenie tutaj zamiast w Fitatu. Każdy krok kończy się czymś, czego da się używać.

| Krok | Zakres | Stan |
|---|---|---|
| 1 | **Edycja produktu.** Status weryfikacji, „Zgadza się z etykietą", formularz „Popraw", jednostka g/ml, data danych w źródle, reguły spójności | gotowe 15.11.2026 |
| 2 | **Dziennik dnia.** „Dodaj do dnia" z gramaturą i posiłkiem, widok dnia z sumami, zmiana ilości, usuwanie, zapis przez kolejkę offline | gotowe 16.11.2026 |
| 3 | **Zdjęcie etykiety.** AI wypełnia formularz z kroku 1, użytkownik zatwierdza (pierwsze użycie klucza Gemini). Kod, którego nie ma w Open Food Facts, można dodać jako własny produkt | kod gotowy 16.11.2026; przed Tobą test z prawdziwym kluczem i na telefonie |
| 4 | **Cele dzienne** i pasek postępu. Cele wersjonowane datą: zmiana nie przepisuje historii | kod gotowy 17.11.2026 |
| 5 | **Wyszukiwarka** (własna baza przy pisaniu, Open Food Facts na przycisk), ostatnie i ulubione, własny produkt bez kodu | kod gotowy 17.11.2026 |
| 6 | **Posiłki:** zestawy dodawane jednym stuknięciem | kod gotowy 17.11.2026 |

Przed codziennym używaniem kroku 2 trzeba wdrożyć aplikację na serwer: lokalna baza SQLite nie przenosi się sama.

## Krok 1: co sprawdzić na telefonie

1. Zeskanuj produkt, którego jeszcze nie było. Karta pokazuje „Niezweryfikowany" i miesiąc danych z Open Food Facts.
2. Napój ma nagłówek „Wartości na 100 ml".
3. „Zgadza się z etykietą" zmienia status na „Zweryfikowany … zgodny z etykietą".
4. „Popraw": klawiatura numeryczna z przecinkiem, zmiana jednej wartości, zapis. Status: „Zweryfikowany … Twoje wartości".
5. Wpisz nasycone większe od tłuszczu: formularz nie pozwala zapisać.
6. Tryb samolotowy → „Popraw" → zapis: formularz się zamyka, karta pokazuje nowe wartości, u góry „niewysłane: 1". Po wyłączeniu trybu samolotowego plakietka znika.
7. Zeskanuj poprawiony produkt ponownie: wartości zostały.

Produkty zeskanowane przed tym krokiem nie mają daty danych i wszystkie są „na 100 g". Popraw jednostkę przyciskiem „Popraw".

## Krok 2: co sprawdzić na telefonie

1. Aplikacja otwiera się na zakładce „Dziennik" z dzisiejszą datą.
2. Skan → karta produktu ma u góry „Dodaj do dnia": ilość, posiłek (podpowiadany według godziny), podgląd kalorii. Po dodaniu: „Dodano…" i przycisk „Pokaż dziennik".
3. Dziennik pokazuje sumę dnia i sumy posiłków. Napój ma ilość w ml.
4. Stuknij wpis: zmień ilość albo posiłek i zapisz. Sumy się zmieniają.
5. Stuknij wpis → „Usuń".
6. Popraw wartości produktu („Popraw") już po dodaniu go do dnia: wpis w dzienniku się **nie** zmienia (historia jest zamrożona).
7. Strzałki zmieniają dzień. Skan dodaje do dnia, który jest otwarty w dzienniku (nagłówek „Dodaj do dnia · Wczoraj").
8. Tryb samolotowy: zeskanuj produkt, który już był skanowany, dodaj go, zmień ilość innego wpisu. Wpisy mają dopisek „czeka na wysłanie", u góry „niewysłane: 2". Zamknij aplikację (wyrzuć z listy), otwórz ponownie bez sieci: wpisy nadal są. Wyłącz tryb samolotowy: dopiski i plakietka znikają.

Krok 2 naprawia też dwa błędy znalezione przy testach:

- **Baza SQLite zbudowana migracjami nie przyjmowała zapisów z datą nadawaną przez bazę** (`unknown function: now()`): próba D, dane ze Skrótów i wpisy dziennika. Znaczniki czasu nadaje teraz aplikacja. Test `tests/test_migrations.py` buduje bazę migracjami i zapisuje przez API.
- **Produkt zeskanowany wcześniej nie otwierał się bez sieci.** Czas trzymania danych w pamięci (30 dni) przepełniał licznik przeglądarki i dane znikały od razu po zamknięciu karty.

## Krok 3: przygotowanie

1. Utwórz darmowy klucz na <https://aistudio.google.com/apikey> i wpisz go do `.env` jako `GEMINI_API_KEY=...` (na serwerze: w panelu hostingu). Klucz nie trafia do repo.
2. Uruchom backend ponownie. Bez klucza przycisk „Zdjęcie etykiety" odpowiada komunikatem o braku klucza, a reszta aplikacji działa normalnie.
3. Domyślny model to `gemini-3.5-flash-lite` (darmowy poziom, stan na 16.11.2026). Gdy Google go wycofa, zmień `GEMINI_MODEL_CHEAP` w `.env`, bez zmiany kodu.

Wywołanie Gemini jest sprawdzone testami na udawanym serwerze (kształt żądania i odpowiedzi według dokumentacji z 16.11.2026). **Z prawdziwym kluczem nie było jeszcze uruchamiane**: pierwsze zdjęcie jest zarazem testem.

## Nowa wersja na telefonie

Pierwszy test kroku 3 pokazał starą aplikację: po wdrożeniu telefon podawał poprzednią wersję z pamięci i nic o tym nie mówiło. Od teraz:

1. Po wdrożeniu otwórz aplikację. Po kilku sekundach pod nagłówkiem pojawia się „Nowa wersja aplikacji · stuknij, żeby odświeżyć". Stuknij.
2. Zakładka „Start" → „Wersja aplikacji" pokazuje datę i godzinę zbudowania. Porównaj ją z godziną `npm run build`.
3. Przycisk można pominąć: nowa wersja wejdzie sama po zamknięciu aplikacji z listy i ponownym otwarciu.

**Jednorazowo**, żeby telefon dostał sam mechanizm: zamknij aplikację z listy aplikacji, otwórz, odczekaj ok. 10 sekund, zamknij z listy jeszcze raz i otwórz ponownie.

## Krok 3: co sprawdzić na telefonie

1. Zeskanuj produkt z Open Food Facts → „Popraw" → „Zdjęcie etykiety". Otwiera się aparat. Sfotografuj tabelę wartości odżywczych.
2. Po kilku sekundach pola mają wartości z etykiety i żółtą ramkę, u góry „Odczytano N z 8 wartości". Porównaj z opakowaniem.
3. Popraw ręcznie jedno pole: jego ramka wraca do zwykłej. „Zapisz" → karta pokazuje „Zweryfikowany … Twoje wartości".
4. Napój: po zdjęciu przełącznik ustawia się na „100 ml".
5. Zdjęcie czegoś bez tabeli (np. przód opakowania): komunikat „Nie widzę na zdjęciu tabeli…", pola bez zmian.
6. Zeskanuj kod, którego nie ma w Open Food Facts → „Dodaj produkt" → „Zdjęcie etykiety" → uzupełnij nazwę → „Zapisz". Karta pokazuje nowy produkt i „Dodaj do dnia". Dodaj go do dnia.
7. Zeskanuj ten sam kod ponownie: produkt otwiera się od razu z Twoimi wartościami.
8. Tryb samolotowy → „Zdjęcie etykiety": komunikat o braku połączenia, formularz zostaje otwarty i da się go wypełnić ręcznie.
9. Po powrocie z aparatu formularz nadal jest otwarty i ma wpisane wcześniej wartości. Jeśli aplikacja się przeładowała (iOS potrafi to zrobić przy małej ilości pamięci), zapisz to w wynikach: wtedy zdjęcie trzeba robić przed wpisywaniem.

## Kroki 4–6: zmiany na ekranie

- Zakładka **„Skan" nazywa się teraz „Dodaj"**: wyszukiwarka, przyciski „Skanuj kod" i „Produkt bez kodu", pod spodem „Posiłki", „Ulubione" i „Ostatnie".
- Dziennik ma pod sumą link **„Ustaw cele dzienne"**, a przy każdym posiłku **„Zapisz jako posiłek"**.
- Po aktualizacji telefon zaczyna z pustą pamięcią podręczną (zmienił się kształt danych produktu). **Przed aktualizacją poczekaj, aż zniknie plakietka „niewysłane"**, bo zapisy czekające w kolejce przepadną.
- Baza dostaje nowe kolumny i tabele: po pobraniu zmian uruchom `alembic upgrade head` w katalogu `backend`.

## Kroki 4–6: co sprawdzić (najpierw na komputerze, potem na telefonie)

Cele (krok 4):

1. Dziennik → „Ustaw cele dzienne" → wpisz kalorie, białko i sól → „Zapisz cele". Pod sumą pojawiają się trzy paski z napisami „zostało …".
2. Dodaj coś do dnia: paski się wypełniają. Białko po osiągnięciu celu robi się zielone; sól ponad limit czerwona.
3. Przejdź strzałką na wczoraj: cele obowiązują od dnia, w którym je zapisałeś, więc wczoraj ich nie ma.
4. „Zmień cele", wyczyść pole „Sól", zapisz: pasek soli znika, sól wraca do drobnych wartości.

Wyszukiwarka, ostatnie, ulubione (krok 5):

5. „Dodaj" → wpisz kilka liter produktu, który już masz (np. „nute"): wynik pojawia się przy pisaniu, bez polskich znaków też („smietan").
6. Wpisz coś, czego nie masz → „Szukaj … w Open Food Facts" → wybierz wynik: otwiera się karta produktu jak po skanie. Porównaj wartości z etykietą.
7. Gwiazdka ☆ na karcie: produkt trafia do „Ulubionych".
8. Wyczyść wyszukiwarkę: „Ostatnie" pokazują produkty z dziennika z ilością z ostatniego razu; po wybraniu ta ilość jest już wpisana.
9. „Produkt bez kodu" → np. „Leczo domowe", wartości na 100 g → „Zapisz" → „Dodaj do dnia". Potem wyszukaj „lecz": jest na liście.

Posiłki (krok 6):

10. Dziennik → przy śniadaniu „Zapisz jako posiłek" → nazwa → „Zapisz".
11. „Dodaj" → „Posiłki": wybierz porę („do: Kolacja") i stuknij zestaw. Pojawia się „Dodano … · Cofnij", a w dzienniku wszystkie produkty zestawu.
12. „Cofnij" usuwa właśnie dodane wpisy.
13. ✕ przy zestawie usuwa zapisany posiłek; wpisy w dzienniku zostają.

Tylko na telefonie (kolejka offline):

14. Tryb samolotowy → dodaj zapisany posiłek, zmień cele, dodaj gwiazdkę. Plakietka „niewysłane" rośnie, dziennik od razu pokazuje zmiany. Zamknij aplikację z listy, otwórz bez sieci: zmiany nadal są. Wyłącz tryb samolotowy: plakietka znika.
15. Bez sieci wyszukiwarka pokazuje błąd połączenia, ale „Ostatnie", „Ulubione" i „Posiłki" działają z pamięci telefonu.
16. „Skanuj kod" w zakładce „Dodaj": kamera nie pyta ponownie o zgodę przy przechodzeniu między listą a skanerem.

## Profil i plan (dodatek do etapu 1)

Zakładka **„Start" nazywa się teraz „Profil"**. Na górze profil i plan, na dole schowana „Diagnostyka" (dawny ekran „Start": serwer, instalacja, próba offline). Po pobraniu zmian uruchom `alembic upgrade head` w katalogu `backend`.

Co sprawdzić:

1. „Profil" → wypełnij dane, cel „Schudnąć", tempo 0,5 kg → „Zapisz i policz plan". Plan pokazuje kalorie, deficyt i osiem celów.
2. „Skąd te liczby": każda liczba ma opis i wzór.
3. Wybierz tempo 1 kg na tydzień przy masie poniżej 100 kg: pojawia się ostrzeżenie, że plan liczy wolniej (najwyżej 1% masy ciała na tydzień).
4. „Ustaw jako cele dzienne od dziś" → Dziennik: paski mają wartości z planu. Wczorajszy dzień zachowuje stare cele.
5. „Zmień profil" → zmień masę ciała → plan się przelicza, ale cele w dzienniku zostają, dopóki nie stukniesz „Ustaw jako cele…" ponownie.
6. Na telefonie: tryb samolotowy → zmień profil → „Profil czeka na wysłanie". Po powrocie sieci pojawia się nowy plan.
