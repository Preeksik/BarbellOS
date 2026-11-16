# BarbellOS: zasady dla agentów

Ten plik czytają wszyscy agenci kodujący (Claude Code przez `CLAUDE.md`, Antigravity bezpośrednio). Pełna specyfikacja jest w `docs/DOKUMENTACJA.md`; tutaj są reguły, których nie wolno pominąć.

## Czym jest projekt

Aplikacja jednego użytkownika łącząca dietę, trening siłowy i regenerację. Frontend to PWA (React + TypeScript + Vite) instalowana na iPhonie, backend to FastAPI + Postgres. Dane z Apple Health dosyła automatyzacja Skrótów. Właściciel czyta swobodnie Pythona, TypeScript słabiej.

## Wymogi twarde

1. **Liczby liczy kod, model językowy tylko interpretuje.** Kalorie, e1RM, trendy, wskaźnik regeneracji to funkcje w `backend/app/core/` z testami. Żaden prompt nie prosi modelu o arytmetykę ani o dawki.
2. **Logika w Pythonie.** Wszystko, co da się policzyć na serwerze, liczy serwer. Frontend wyświetla i zbiera dane. Jedyny wyjątek to podgląd zmiany, która czeka w kolejce offline (`web/src/lib/diary.ts`): po wysłaniu zapisu ekran pokazuje wynik z serwera.
3. **`backend/app/core/` jest czyste:** bez importów FastAPI, SQLAlchemy i sieci. Każda funkcja ma test.
4. **Sekrety i dane osobiste nigdy nie trafiają do repo** (repo jest publiczne). Klucze, hasła i tokeny są w `.env`. Nie commituj zrzutów bazy, eksportów, zdjęć posiłków ani danych zdrowotnych. Nowa zmienna środowiskowa oznacza aktualizację `.env.example`.
5. **Kolejka zapisów offline musi być trwała** (dokumentacja 3.6). Każdy zapis, który może powstać bez sieci:
   - ma `mutationKey` i funkcję zarejestrowaną przez `setMutationDefaults` w `web/src/lib/offline.ts`,
   - trafia do idempotentnego endpointu (`PUT` z kluczem naturalnym albo UUID nadanym na telefonie),
   - nie definiuje `mutationFn` lokalnie w komponencie.
6. **Historia spożycia jest zamrożona.** `meal_entry` zapisuje wartości z chwili dodania. Edycja produktu nie zmienia wpisów wstecz.
7. **Każda wartość odżywcza ma źródło** (`label`, `reference`, `estimated`, `user`). Brak danych to `NULL`, nigdy zero.
8. **Model AI nie zwraca identyfikatorów z bazy.** Dopasowanie do `food` robi backend (dokumentacja 7).
9. **Robienie wagi:** Coach nie generuje protokołów ani dawek wody i sodu. Wartości pochodzą z szablonu `meet_week` wypełnionego przez użytkownika, granice są w kodzie (dokumentacja 7).
10. **Daty w bazie są w UTC i zawsze ze strefą** (typ `UtcDateTime`). Data bez strefy jest błędem. Znaczniki czasu nadaje aplikacja (`default=utcnow` w modelu), nie baza: `now()` nie istnieje w SQLite.
11. **Zakładki frontendu są stanem, nie adresami URL.** Zmiana adresu w zainstalowanej PWA potrafi na iOS ponownie wywołać pytanie o kamerę.
12. **Nie dodawaj do commitów ani PR linijek Co-Authored-By ani "Generated with Claude Code".**

## Praca nad zmianą

- Jedno zadanie = jedna gałąź = jeden PR z testami. Specyfikacją jest wskazany rozdział dokumentacji.
- Najpierw kontrakt (model Pydantic, tabela, migracja), potem implementacja.
- Zmiana kształtu odpowiedzi API, którą frontend trzyma w pamięci podręcznej = podbicie `CACHE_VERSION` w `web/src/lib/offline.ts`. Inaczej telefon wczyta starą kopię w starym kształcie.
- `gcTime` w TanStack Query nie może przekroczyć ok. 24 dni (przepełnienie licznika przeglądarki). Używaj `GC_TIME_MS` z `web/src/lib/offline.ts`.
- Zmiana schematu bazy = migracja Alembic: `alembic revision --autogenerate -m "opis"`, potem przegląd wygenerowanego pliku. Typ `UtcDateTime` w migracji zapisuj jako `sa.DateTime(timezone=True)`.
- Zmiana zachowania opisanego w dokumentacji = aktualizacja `docs/DOKUMENTACJA.md` w tym samym PR.
- Nazwy modeli AI i ceny zmieniają się często. Przed pisaniem wywołań API sprawdź aktualną dokumentację dostawcy zamiast polegać na pamięci.
- Komunikaty dla użytkownika i komentarze są po polsku; nazwy w kodzie po angielsku.

## Polecenia

Backend (katalog `backend/`, aktywne środowisko wirtualne):

```
pip install -e ".[dev]"
pytest -q
ruff check . && ruff format --check .
alembic upgrade head
python -m app.tools.seed
uvicorn app.main:app --reload
```

Frontend (katalog `web/`):

```
npm install
npm run dev          # http://localhost:5173, zapytania /api idą na localhost:8000
npm run typecheck
npm test
npm run build
```

## Definicja ukończenia

- `pytest`, `ruff check`, `ruff format --check`, `npm run typecheck`, `npm test` i `npm run build` przechodzą.
- Nowa logika ma testy; poprawka błędu ma test, który bez niej nie przechodzi.
- Zmiany dotyczące kamery, kolejki offline, instalacji PWA i Skrótów są sprawdzone na prawdziwym iPhonie. Agent nie może tego zrobić sam, więc w opisie PR wypisuje kroki do ręcznego sprawdzenia.
