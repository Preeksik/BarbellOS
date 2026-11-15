# Etap 0: cztery próby ryzyka

Cel: sprawdzić na prawdziwym iPhonie cztery rzeczy, od których zależy cały stack, zanim powstanie reszta aplikacji. Jeśli próba A, B lub D zawiedzie, wracamy do decyzji o stacku (plan C: natywna powłoka budowana na Macu).

Kod do wszystkich prób jest w repo. Każda próba kończy się wpisaniem wyniku w tabeli na dole.

## Przygotowanie

1. Uruchom projekt lokalnie (główny `README.md`) i upewnij się, że testy przechodzą.
2. Wystaw aplikację pod HTTPS. Kamera i instalacja PWA nie działają po zwykłym HTTP z adresu w sieci domowej. Dwie drogi:
   - **Wdrożenie** na Render + baza w Neon (`render.yaml`, dokumentacja 3.4). To i tak trzeba zrobić, a próba B wymaga prawdziwego usypiania serwera.
   - **Tunel** do komputera na szybkie testy: zbuduj frontend (`npm run build` w `web/`), uruchom backend ze zmienną `STATIC_DIR=../web/dist`, a potem `cloudflared tunnel --url http://localhost:8000`.
3. Ustaw `ENVIRONMENT=prod`, `SECRET_KEY`, `INGEST_TOKEN` i `APP_PASSWORD_HASH`. Aplikacja wystawiona do internetu nie może działać bez logowania.
4. Na iPhonie otwórz adres w Safari → Udostępnij → „Do ekranu początkowego". Dalsze próby wykonuj w zainstalowanej wersji.

## Próba A: skan kodu kreskowego

Zakładka **Skan** → „Włącz kamerę" → skieruj na kod produktu.

Sprawdź:

- czy pojawia się pytanie o kamerę i czy po zgodzie widać podgląd,
- ile trwa odczyt kodu przy normalnym świetle i przy słabym,
- czy po przejściu na inną zakładkę i powrocie iOS pyta o kamerę ponownie,
- czy po zamknięciu i otwarciu aplikacji pyta ponownie,
- czy „Zrób zdjęcie kodu" działa jako zapas.

Zaliczone, gdy: 10 różnych produktów skanuje się bez frustracji.

## Próba B: Apple Health przez Skróty

Zbuduj skrót według `shortcuts/README.md` (masa ciała i kroki).

Sprawdź:

- wysyłkę na rozbudzony serwer: zakładka **Zdrowie** pokazuje próbki,
- wysyłkę na **uśpiony** serwer (odczekaj ponad 15 minut bez ruchu, wyłącz na ten czas podtrzymanie): po ilu sekundach skrót zgłasza błąd,
- to samo po włączeniu podtrzymania co 14 minut (cron-job.org → `GET /api/healthz`),
- automatyzację po zamknięciu aplikacji wagi lub Zepp,
- czy waga OKOK zapisuje masę ciała do Apple Health.

Zaliczone, gdy: przez 3 dni z rzędu masa ciała pojawia się na serwerze bez ręcznego działania poza zwykłym ważeniem.

## Próba C: pokrycie Open Food Facts

Skopiuj `scripts/kody.example.txt` jako `scripts/kody.txt`, wpisz 30 kodów z własnej kuchni i uruchom w katalogu `backend`:

```
python ../scripts/off_coverage.py ../scripts/kody.txt
```

Dodatkowo porównaj 3 produkty z etykietą, w tym jeden z podanymi witaminami lub minerałami. To sprawdza przeliczanie jednostek w `backend/app/off/client.py`.

Wynik decyduje o kolejności prac: przy pokryciu poniżej ok. 70% funkcja „zdjęcie etykiety → produkt" wchodzi do etapu 1 zamiast do etapu 2.

## Próba D: zapis offline

Zakładka **Start**, sekcja „Próba D".

1. Włącz tryb samolotowy.
2. Stuknij „Zapisz próbkę". Ma się pojawić „czeka na wysłanie" i plakietka „niewysłane: 1".
3. Zamknij aplikację z przełącznika aplikacji (przesunięcie w górę).
4. Wyłącz tryb samolotowy i otwórz aplikację.
5. Próbka ma się pojawić na liście „Na serwerze".

Powtórz z wariantami: zablokowanie telefonu na kilka minut zamiast zamknięcia; Wi-Fi włączone, ale bez internetu; kilka próbek naraz.

W przeglądarce Chrome na komputerze ten scenariusz przechodzi (sprawdzone automatycznie). Próba dotyczy zachowania iOS.

Zaliczone, gdy: żadna próbka nie ginie w żadnym wariancie.

## Wyniki

| Próba | Data | Wynik | Uwagi |
|---|---|---|---|
| A: skan | 15.11.2026 | zaliczona | iPhone 16, Safari i aplikacja z ikony. Odczyt szybki (Fitatu nieco szybsze). Brak ponownego pytania o kamerę przy zmianie zakładki; pytanie wraca po ponownym otwarciu karty Safari. |
| B: Skróty | | czeka | Wymaga stałego adresu (wdrożenie na serwer). |
| C: OFF | 15.11.2026 | częściowo | Kilkanaście zeskanowanych produktów znalezionych, ale wartości często nieaktualne lub niepełne. Decyzja: baza jest szkicem, etykieta prawdą (dokumentacja 4.4); edycja produktu i zdjęcie etykiety weszły do etapu 1. Próba na 30 kodach nie była robiona. |
| D: offline | 15.11.2026 | zaliczona | Próbka zapisana w trybie samolotowym dotarła po zamknięciu i ponownym otwarciu aplikacji. |

Wniosek: zostajemy przy PWA + FastAPI. Testy szły przez tymczasowy tunel Cloudflare.
