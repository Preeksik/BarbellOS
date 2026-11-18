# Wdrożenie na serwer (Render + Neon)

**Stan: wdrożone 18.11.2026** pod adresem https://barbellos.onrender.com (dane z PC przeniesione, budzik ustawiony).

Po tym przewodniku aplikacja działa pod adresem `https://barbellos-….onrender.com`, na iPhonie
jako ikona na ekranie głównym, a dane są w bazie w internecie, a nie na Twoim PC.

| Usługa | Do czego | Koszt |
|---|---|---|
| **Neon** | baza danych (Postgres) | 0 zł (1 GB, usypia się po 5 min, budzi w ułamku sekundy) |
| **Render** | aplikacja (jeden serwer: API + strona) | 0 zł (usypia się po 15 min bez ruchu, budzi ok. minuty) |
| **cron-job.org** | „budzik”, żeby Render nie zasypiał w dzień | 0 zł |

Czas: ok. 30 minut. Wszystkie trzy usługi pozwalają zalogować się kontem GitHub.

Repo jest gotowe: `Dockerfile` buduje jeden obraz, `render.yaml` opisuje usługę, a serwer przy każdym starcie sam robi migracje bazy i wgrywa słownik witamin. Nowa wersja wchodzi na serwer sama po każdym `git push`, ale tylko gdy przejdą testy w GitHub Actions (także na Postgresie).

---

## Krok 1. Baza w Neon

1. Wejdź na https://neon.com i załóż konto („Sign up” → GitHub).
2. Utwórz projekt:
   - **Project name:** `barbellos`
   - **Postgres version:** najnowsza (17)
   - **Region:** **AWS Europe Central 1 (Frankfurt)**: ten sam region co serwer, krótsze opóźnienia.
   - **Services:** zostaw włączony tylko „Postgres database”. Podpowiedzi „Set up Neon with your coding agent” nie używaj: wpisałaby adres bazy z serwera do lokalnego `.env`.
3. Na stronie projektu kliknij **Connect**.
4. **Wyłącz „Connection pooling”** (przełącznik w oknie Connect). Aplikacja ma jeden serwer i sama trzyma połączenia, a pośrednik Neon bywa kłopotliwy z biblioteką `psycopg`.
5. Skopiuj **connection string**. Wygląda tak:
   `postgresql://neondb_owner:HASŁO@ep-cos-123456.eu-central-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require`
6. Zapisz go na chwilę w notatniku. **To hasło do Twojej bazy: nie wklejaj go nigdzie poza panelem Render i nie commituj.**

## Krok 2. Hasło do aplikacji

Aplikacja w internecie wymaga logowania. Hasło zamieniasz na „hash” (zapis, z którego nie da się odczytać hasła):

```powershell
cd C:\Users\adria\Desktop\BarbellOS\backend
.\.venv\Scripts\python -m app.tools.hash_password
```

Wpisz hasło (min. 10 znaków) dwa razy. Program wypisze linię `APP_PASSWORD_HASH='scrypt$...'`. Skopiuj **tylko to, co jest między apostrofami** (zaczyna się od `scrypt$`). W panelu Render apostrofów nie wpisujesz.

## Krok 3. Serwer w Render

1. Wejdź na https://render.com i załóż konto („Get Started” → GitHub). Zgódź się na dostęp do repozytorium `BarbellOS`.
2. W panelu: **New +** → **Blueprint**.
3. Wybierz repozytorium **Preeksik/BarbellOS**. Render znajdzie plik `render.yaml` i pokaże usługę `barbellos`.
4. Wypełnij pola (te z `sync: false`):

   | Pole | Co wpisać |
   |---|---|
   | `DATABASE_URL` | connection string z Neon (krok 1) |
   | `APP_PASSWORD_HASH` | hash z kroku 2, bez apostrofów |
   | `OFF_USER_AGENT` | `BarbellOS/0.1 (https://github.com/Preeksik/BarbellOS)` |
   | `GEMINI_API_KEY` | ten sam klucz co w Twoim `.env` |
   | `FDC_API_KEY` | ten sam klucz co w Twoim `.env` |

   `SECRET_KEY` i `INGEST_TOKEN` Render wygeneruje sam.
5. **Apply** (albo „Deploy Blueprint”). Budowa trwa ok. 5–10 minut (frontend + backend w jednym obrazie).
6. W usłudze `barbellos` → **Logs**. Na końcu powinno być:
   - `Running upgrade ... -> 0009` (migracje bazy),
   - `Mikroskładniki: 20.`
   - `Uvicorn running on http://0.0.0.0:...`
7. Adres aplikacji jest u góry strony usługi, np. `https://barbellos-abcd.onrender.com`. Otwórz go w przeglądarce na PC i zaloguj się hasłem z kroku 2.

## Krok 4. Przeniesienie Twoich danych z PC (opcjonalnie)

Twoje produkty, wpisy, cele i profil są w lokalnym pliku `backend\barbellos.db`. Narzędzie przenosi je do pustej bazy w Neon. **Zrób to przed dodaniem czegokolwiek na serwerze**: narzędzie odmówi, jeśli w Neon są już Twoje dane, żeby nie zdublować historii. Serwer musi raz wystartować (krok 3), bo to on tworzy tabele.

```powershell
cd C:\Users\adria\Desktop\BarbellOS\backend
.\.venv\Scripts\python -m alembic upgrade head
.\.venv\Scripts\python -m app.tools.copy_db --from "sqlite:///./barbellos.db" --to "TU_WKLEJ_CONNECTION_STRING_Z_NEON"
```

Pierwsze uruchomienie tylko pokazuje, co przeniesie (tabela, liczba wierszy, decyzja). Jeśli wygląda dobrze, powtórz to samo polecenie z `--wykonaj` na końcu. Słownik witamin jest pomijany, bo serwer wgrał go sam. Odśwież stronę aplikacji: Twoje dane są na serwerze.

Twój lokalny `.env` zostaje bez zmian (lokalna baza do testów). Adresu Neon nie wpisuj do `.env`.

## Krok 5. iPhone

1. Otwórz adres aplikacji w **Safari** (nie w Chrome).
2. **Udostępnij** (kwadrat ze strzałką) → **Do ekranu początkowego** → Dodaj.
3. Otwórz aplikację z ikony i zaloguj się. Od teraz używasz jej jak zwykłej aplikacji; skaner i zdjęcia działają, bo adres jest pod HTTPS.

## Krok 6. Budzik, żeby serwer nie zasypiał

Darmowy Render usypia po 15 minutach bez ruchu, a obudzenie trwa ok. minuty. Żeby w dzień aplikacja odpowiadała od razu:

1. https://cron-job.org → załóż konto (strona jest po polsku).
2. **Utwórz zadanie cron**:
   - **Tytuł:** `BarbellOS budzik`
   - **Adres URL:** `https://barbellos.onrender.com/api/healthz` (adres bez logowania i bez dotykania bazy, zrobiony do sprawdzania, czy serwer żyje)
   - **Harmonogram:** najprościej gotowe **„Co 10 minut”**. Serwer nie zaśnie wtedy nigdy, a cały miesiąc pracy (744 godziny) mieści się w darmowym limicie Render (750). Z nocną przerwą: „Zdefiniowany przez użytkownika”, minuty `0, 14, 28, 42, 56`, godziny 6–23, strefa Europe/Warsaw.
3. Zapisz. W **Historii** zadania powinny pojawiać się odpowiedzi `200 OK`.

## Kolejne wersje

Ja (albo Ty) robię `git push` na `main` → GitHub Actions uruchamia testy → gdy przejdą, Render buduje i wdraża nową wersję (ok. 5–10 min) → na telefonie pojawia się pasek „Nowa wersja aplikacji · stuknij, żeby odświeżyć”. Gdy testy nie przejdą, serwer zostaje na poprzedniej wersji.

## Gdy coś nie działa

| Objaw | Przyczyna i co zrobić |
|---|---|
| Logi: `Brak wymaganych zmiennych w trybie prod: …` | Brakuje zmiennej w Render → Environment. Uzupełnij i kliknij „Save, rebuild and deploy”. |
| Logi: błąd połączenia z bazą, `password authentication failed` | Zły `DATABASE_URL`. Skopiuj ponownie z Neon (Connect, bez poolingu). |
| Logowanie nie działa | Aplikacja sama zdejmuje apostrofy, `APP_PASSWORD_HASH=` i spacje. Jeśli nadal nie działa, wartość jest od innego hasła albo ucięta: wygeneruj nową (`python -m app.tools.hash_password`) i wklej w Environment. |
| Wdrożenie „Failed”, w logach `APP_PASSWORD_HASH ma złą postać` | W polu nie ma pełnego hasha (od `scrypt$`, dokładnie 5 znaków `$`). Wklej ponownie i „Save, rebuild and deploy”. Poprzednia wersja działa w tym czasie dalej. |
| Strona długo się ładuje | Serwer się budzi (do minuty). Ustaw budzik z kroku 6. |
| `copy_db`: „Różne wersje migracji” | Uruchom lokalnie `alembic upgrade head` (krok 4) albo poczekaj, aż serwer skończy start. |
| `copy_db`: „Baza docelowa ma już dane…” | Na serwerze dodano już dane. Napisz do mnie, ustalimy, co zrobić. |
