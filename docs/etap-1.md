# Etap 1: dziennik diety

Cel: przez tydzień logować jedzenie tutaj zamiast w Fitatu. Każdy krok kończy się czymś, czego da się używać.

| Krok | Zakres | Stan |
|---|---|---|
| 1 | **Edycja produktu.** Status weryfikacji, „Zgadza się z etykietą", formularz „Popraw", jednostka g/ml, data danych w źródle, reguły spójności | gotowe 15.11.2026 |
| 2 | **Dziennik dnia.** „Dodaj do dnia" z gramaturą i posiłkiem, widok dnia z sumami, zapis przez kolejkę offline | |
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
