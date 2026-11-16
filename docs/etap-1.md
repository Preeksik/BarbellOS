# Etap 1: dziennik diety

Cel: przez tydzień logować jedzenie tutaj zamiast w Fitatu. Każdy krok kończy się czymś, czego da się używać.

| Krok | Zakres | Stan |
|---|---|---|
| 1 | **Edycja produktu.** Status weryfikacji, „Zgadza się z etykietą", formularz „Popraw", jednostka g/ml, data danych w źródle, reguły spójności | gotowe 15.11.2026 |
| 2 | **Dziennik dnia.** „Dodaj do dnia" z gramaturą i posiłkiem, widok dnia z sumami, zmiana ilości, usuwanie, zapis przez kolejkę offline | gotowe 16.11.2026 |
| 3 | **Zdjęcie etykiety.** AI wypełnia formularz z kroku 1, użytkownik zatwierdza (pierwsze użycie klucza Gemini) | |
| 4 | **Cele dzienne** i pasek postępu | |
| 5 | **Wyszukiwarka**, ostatnie i ulubione, własny produkt bez kodu | |
| 6 | **Posiłki:** zestawy dodawane jednym stuknięciem | |

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
