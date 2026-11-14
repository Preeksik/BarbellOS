# Skrót „BarbellOS Sync": dane z Apple Health na serwer

Aplikacja webowa nie ma dostępu do Apple Health. Dane wynosi skrót w systemowej aplikacji Skróty i wysyła je na `POST /api/health/ingest`.

**Stan:** opis poniżej powstał bez dostępu do iPhone'a. Nazwy akcji i pól mogą się nieznacznie różnić w Twojej wersji iOS. Dopasowanie go do rzeczywistości jest treścią próby B (`docs/etap-0.md`); poprawki wpisz do tego pliku.

## Zanim zbudujesz skrót: sprawdź serwer

W PowerShell (podstaw adres i token z `.env`):

```powershell
$body = @{
  type = "weight"; unit = "kg"; source = "test"
  starts = "2026-11-14T07:05:00+01:00"; values = "75,1"
} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "https://ADRES/api/health/ingest" `
  -Headers @{ Authorization = "Bearer TWOJ_INGEST_TOKEN" } `
  -ContentType "application/json" -Body $body
```

Oczekiwana odpowiedź: `received 1, inserted 1, updated 0`. Ta sama komenda wysłana drugi raz zwraca `inserted 0`, bo import jest idempotentny.

## Format danych

Serwer przyjmuje wartości jako listy JSON albo jako tekst z jedną wartością w linii. Skróty najłatwiej tworzą to drugie, więc z niego korzystamy.

| Pole | Znaczenie |
|---|---|
| `type` | `weight`, `steps`, `hrv`, `resting_hr`, `sleep`, `active_energy`, `body_fat`, `heart_rate`, `spo2` |
| `starts` | Daty początku próbek w ISO 8601, po jednej w linii |
| `values` | Wartości, po jednej w linii, w tej samej kolejności. Przecinek dziesiętny jest akceptowany |
| `ends` | Opcjonalnie daty końca (potrzebne dla snu) |
| `unit` | Jednostka, np. `kg` |
| `source` | Skąd pochodzą dane, np. `OKOK`, `Zepp` |

Daty bez strefy są traktowane jako czas warszawski.

## Budowa skrótu (wersja dla próby B: masa ciała i kroki)

Nazwa skrótu musi brzmieć dokładnie **BarbellOS Sync**, bo przycisk w aplikacji uruchamia go po nazwie.

Dla każdego typu danych powtarzasz ten sam blok czterech akcji:

1. **Znajdź próbki zdrowia** (Find Health Samples)
   - Typ: Masa ciała
   - Filtr: Data początkowa → jest w ciągu ostatnich → 7 dni
   - Sortuj wg: Data początkowa
2. **Tekst**: wstaw zmienną „Próbki zdrowia", stuknij ją i wybierz właściwość **Wartość**. Powstaje tekst z jedną wartością w linii.
3. **Tekst**: wstaw tę samą zmienną i wybierz właściwość **Data początkowa**, format daty **ISO 8601**, z włączonym czasem.
4. **Pobierz zawartość URL** (Get Contents of URL)
   - URL: `https://ADRES/api/health/ingest`
   - Metoda: POST
   - Nagłówki: `Authorization` = `Bearer TWOJ_INGEST_TOKEN`
   - Treść żądania: JSON z polami tekstowymi:
     - `type` = `weight`
     - `unit` = `kg`
     - `source` = `OKOK`
     - `values` = tekst z kroku 2
     - `starts` = tekst z kroku 3

Drugi blok: Typ = Kroki, `type` = `steps`, `unit` = `count`, `source` = `iPhone`.

Na końcu warto dodać akcję **Pokaż powiadomienie** z wynikiem ostatniego żądania, żeby od razu widzieć `inserted`.

Token jest wpisany w skrócie jawnym tekstem. Ma prawo wyłącznie do dopisywania próbek zdrowotnych, niczego nie odczyta. Nie udostępniaj skrótu nikomu.

## Automatyzacja

Skróty → Automatyzacja → Nowa → **Aplikacja** → wybierz **Zepp** → **Jest zamknięta** → Uruchom natychmiast → skrót „BarbellOS Sync".

Dlaczego nie stała godzina: dane zdrowotne są zaszyfrowane, gdy telefon jest zablokowany, więc automatyzacja uruchomiona o 8:00 na zablokowanym telefonie kończy się błędem. Zamknięcie aplikacji Zepp oznacza, że telefon jest odblokowany, a opaska właśnie się zsynchronizowała. Do czasu, gdy opaska dotrze, tak samo można podpiąć aplikację wagi.

Zapasowo skrót uruchamia przycisk „Uruchom skrót" na ekranie Zdrowie.

## Co sprawdzić i zapisać w próbie B

- Czy tekst z kroku 2 ma rzeczywiście jedną wartość w linii i czy data z kroku 3 ma strefę (np. `+01:00`).
- Jak nazywa się źródło próbek masy ciała w Apple Health (czy OKOK w ogóle tam zapisuje).
- Po ilu sekundach skrót się poddaje, gdy serwer śpi (dokumentacja 3.4).
- Czy automatyzacja po zamknięciu Zepp działa bez pytania o potwierdzenie.
- Czy przycisk „Uruchom skrót" działa z aplikacji zainstalowanej na ekranie początkowym.

## Kolejne typy (etap 3)

| Dane | Typ w Zdrowiu | `type` | Uwagi |
|---|---|---|---|
| HRV | Zmienność tętna | `hrv` | Zepp zapisuje średnią z nocy |
| Tętno spoczynkowe | Tętno spoczynkowe | `resting_hr` | |
| Sen | Analiza snu | `sleep` | `values` to nazwa fazy, potrzebne też `ends` (Data końcowa) |
| Energia aktywna | Energia aktywna | `active_energy` | tylko informacyjnie |
| Tkanka tłuszczowa | Procent tkanki tłuszczowej | `body_fat` | o ile waga ją zapisuje |
