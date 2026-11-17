# Etap 2: AI w diecie

Cel: posiłek na mieście w mniej niż 30 sekund. Specyfikacja: `docs/DOKUMENTACJA.md`, rozdział 7.

| Część | Zakres | Stan |
|---|---|---|
| Zdjęcie posiłku | Składniki z gramaturą i zakresem, dopasowanie do Twoich produktów, szacunek AI dla reszty, poprawki przed dodaniem | kod gotowy 17.11.2026 |
| Opis tekstowy | „2 jajka sadzone, kromka chleba” → te same wpisy | kod gotowy 17.11.2026; sprawdzony z prawdziwym Gemini |
| Licznik kosztów | Koszt każdego wywołania według cennika, podsumowanie miesiąca w „Profilu” | kod gotowy 17.11.2026 |
| Dostawca Claude | Zapas za Gemini i modele do podsumowań | czeka na klucz `ANTHROPIC_API_KEY` |

Po pobraniu zmian uruchom `alembic upgrade head` w katalogu `backend` (nowa kolumna `meal_entry.macro_source`).

## Co sprawdzić (najpierw na komputerze)

1. „Dodaj” → „Opisz posiłek (AI)” → np. „60 g płatków owsianych na mleku, banan, łyżka masła orzechowego” → „Rozpisz na składniki”. Po kilku sekundach lista składników; 60 g wzięte dokładnie z opisu.
2. Składnik, który masz w bazie (np. Twoje płatki), ma w polu „Produkt” Twój produkt. Reszta ma „Szacunek AI (… kcal/100 g)”.
3. Zmień gramaturę: kalorie składnika i „Razem” zmieniają się od razu. Zmień produkt na inny z listy albo na „Szacunek AI”.
4. Odznacz jeden składnik: znika z sumy i nie zostanie dodany.
5. „Dodaj do dnia” → „Pokaż dziennik”: wpisy z szacunkiem mają dopisek „≈ szacunek AI”. Zmiana ilości takiego wpisu działa jak przy zwykłym produkcie.
6. „Profil” → „AI w tym miesiącu”: liczba wywołań i koszt według cennika.
7. Gdy Google jest przeciążony, aplikacja sama próbuje drugiego modelu. Jeśli oba nie odpowiadają, widać komunikat „Model AI nie odpowiada. Spróbuj ponownie za chwilę.”

## Na telefonie

8. „Zdjęcie posiłku (AI)” otwiera aparat. Zdjęcie z góry, cały talerz. Po kilku sekundach szkic ze zdjęciem u góry.
9. Opis w polu nad przyciskiem (np. „smażone na oliwie”) pojawia się w szkicu jako składnik albo w uwadze AI.
10. Tryb samolotowy: rozpoznanie pokazuje błąd połączenia. Szkic rozpoznany przed włączeniem trybu samolotowego da się dodać: wpisy czekają w kolejce („niewysłane”) i wysyłają się po powrocie sieci.
11. Zmierz czas od otwarcia „Dodaj” do dodania posiłku. Cel etapu: poniżej 30 sekund.
