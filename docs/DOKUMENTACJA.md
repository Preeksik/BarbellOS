# BarbellOS — dokumentacja techniczna v0.5

Stan: 15.11.2026.

Zmiany w v0.5 (wyniki etapu 0, początek etapu 1): dane z Open Food Facts są szkicem, a prawdą jest etykieta (4.4); produkt ma status weryfikacji, jednostkę g/ml i datę danych w źródle (8); etap 1 podzielony na kroki (`docs/etap-1.md`); FatSecret odrzucony jako źródło (4.1).

Zmiany w v0.4 (szkielet etapu 0): nazwa projektu, jedna usługa serwująca API i frontend (3.4), wykrywanie braku połączenia po wyniku żądania i 30-dniowy czas życia kolejki (3.6), próba D (10), rzeczywista struktura repozytorium (9).

Zmiany w v0.3 (po recenzji): zimny start serwera a Skróty (3.4, 6.2), trwała kolejka zapisów offline (3.6), kontrakt AI bez identyfikatorów z bazy (7), makroskładniki jako kolumny i zamrożona historia spożycia (8), nowe zasady Coacha przy robieniu wagi (7).

Oznaczenia:

- **[ZAŁOŻENIE]** — przyjęta wartość domyślna, do zmiany na Twoje życzenie.
- **[DO WERYFIKACJI]** — trzeba sprawdzić na Twoim telefonie albo w panelu dostawcy. Najważniejsze z nich sprawdza etap 0.

---

## 0. Ustalenia

| Temat | Stan |
|---|---|
| Telefon | iPhone 16, iOS 27 |
| Mac | brak (tak rozumiem Twoją odpowiedź) → natywny Swift odpada, bo Xcode działa tylko na macOS |
| Konto Apple Developer (99 USD/rok) | nie kupujemy na start |
| Kto pisze kod | agenci (Claude Code, Antigravity); Ty przeglądasz — Python dobrze, TypeScript trochę |
| Edytor i system | VS Code na Windows 11 (Docker Desktop z WSL2 do lokalnej bazy) |
| Repozytorium | publiczne na GitHubie (zasady w 3.5) |
| Hosting | darmowy plan na start |
| Klucze AI | na start tylko darmowy klucz Gemini z Google AI Studio; płatny klucz Claude dochodzi później |
| Waga | aplikacja OKOK International |
| Opaska | Amazfit Helio Strap przez aplikację Zepp (od Świąt) |
| Plan treningowy | istnieje jako działająca aplikacja w jednym pliku HTML (patrz rozdział 5) |

## 1. Cel i zakres

Jedna aplikacja na iPhone'a dla jednego użytkownika, która łączy:

1. **Dietę** — dziennik posiłków: skan kodu kreskowego, wyszukiwarka, własne produkty, szacowanie ze zdjęcia; każdy produkt z kcal, B/T/W, tłuszczami nasyconymi, cukrami, błonnikiem, solą oraz witaminami i minerałami.
2. **Trening** — plan AMP 2027, logowanie serii, progres względem celu 600 kg.
3. **Regenerację** — sen, HRV, tętno spoczynkowe, masa ciała z Apple Health.

Nad tym **AI Coach**: podsumowanie dnia i tygodnia łączące wszystkie trzy moduły.

Poza zakresem v1: wielu użytkowników, Android, App Store, monetyzacja.

## 2. Zasady projektowe

1. **Serwer jest źródłem prawdy, telefon jest oknem.** Dane żyją w Postgresie. Telefon trzyma kopię podręczną i kolejkę zapisów na czas bez zasięgu. (Zmiana względem v0.1 — powód w 3.3.)
2. **Liczby liczy kod, LLM interpretuje.** Sumy kalorii, e1RM, trend wagi, wskaźnik regeneracji to funkcje w Pythonie z testami. Model dostaje gotowe liczby i je komentuje.
3. **Każda wartość ma źródło.** Przy składniku odżywczym zapisujemy pochodzenie: `label`, `reference`, `estimated`, `user`.
4. **AI proponuje, Ty zatwierdzasz.** Wynik ze zdjęcia to edytowalny szkic. Plan treningowy nie zmienia się sam.
5. **Dostawcy i modele w konfiguracji**, nie w kodzie.
6. **Logika w Pythonie, nie w przeglądarce.** Wszystko, co da się policzyć na serwerze, liczy serwer — bo ten kod umiesz przeczytać i sprawdzić. Frontend wyświetla i zbiera dane.

## 3. Architektura

```
┌────────────── iPhone ──────────────┐        ┌──────────── Serwer (HTTPS) ────────────┐
│ PWA (ikona na ekranie głównym)     │        │ FastAPI (Python)                       │
│  React + TypeScript + Vite         │  JSON  │  api/      endpointy                   │
│  Dieta│Trening│Regeneracja│Coach   │◄──────►│  core/     obliczenia + testy          │
│  aparat: skan kodów, zdjęcia       │        │  ai/       router Gemini / Claude      │
│  kopia podręczna + kolejka zapisów │        │  off/      klient Open Food Facts      │
└────────────────────────────────────┘        │  Postgres  jedyne źródło prawdy        │
┌────────────── iPhone ──────────────┐  POST  │                                        │
│ Skróty (automatyzacja)             │───────►│  /api/health/ingest                    │
│  czyta Apple Health                │        └───────┬───────────────┬────────────────┘
│  ← Zepp (opaska), OKOK (waga)      │                │               │
└────────────────────────────────────┘        Open Food Facts   Gemini API / Claude API
```

### 3.1 Stack

| Warstwa | Wybór | Dlaczego |
|---|---|---|
| Frontend | React + TypeScript + Vite, `vite-plugin-pwa` | Najlepiej wspierany przez agentów; działa i testuje się w zwykłej przeglądarce |
| Dane w UI | TanStack Query + trwały zapis w IndexedDB | Kopia podręczna i kolejka zapisów offline; trwałość wymaga jawnej konfiguracji (3.6) |
| Skaner kodów | biblioteka WebAssembly, np. `zxing-wasm` | Safari nie ma wbudowanego API do kodów kreskowych |
| Backend | FastAPI + SQLAlchemy + Alembic + Pydantic | Python, który znasz; schematy Pydantic są jednocześnie kontraktem API |
| Baza | PostgreSQL | Jedna baza na wszystko |
| Testy | pytest (backend), Vitest (frontend) | Agenci uruchamiają je bez telefonu |
| Dane zdrowotne | automatyzacja w aplikacji Skróty → `POST` na backend | Jedyna droga do Apple Health bez aplikacji natywnej |
| Klucze API | zmienne środowiskowe na serwerze | Nie trafiają do przeglądarki |

### 3.2 Dlaczego nie aplikacja natywna

| | PWA + FastAPI + Skróty (wybrane) | Expo + EAS + konto Apple |
|---|---|---|
| Mac | niepotrzebny | niepotrzebny, ale debugowanie bez niego jest uciążliwe |
| Koszt stały | hosting: 0 zł do ok. 30 zł/mies. | 99 USD/rok + hosting, jeśli chcesz kopię danych |
| Wdrożenie zmiany | `git push`, odświeżasz aplikację | budowanie w chmurze i ponowna instalacja przy zmianach natywnych |
| Testowanie przez agentów | w przeglądarce, od razu | agent nie uruchomi buildu iOS |
| Apple Health | przez Skróty: działa, ale tylko przy odblokowanym telefonie | natywnie, także w tle |
| Aparat | działa, z drobnymi dziwactwami iOS | natywny |

Decyduje pętla zwrotna: skoro kod piszą agenci, to wersja, którą agent sam uruchomi i przetestuje w przeglądarce, powstanie wielokrotnie szybciej. Droga odwrotu istnieje — backend zostaje bez zmian, a frontend można kiedyś opakować w aplikację natywną, jeśli most przez Skróty okaże się za słaby.

### 3.3 Ograniczenia PWA na iOS (sprawdzone)

- **Instalacja:** tylko ręcznie — Safari → Udostępnij → „Do ekranu początkowego". W UE działa normalnie (Apple wycofał się z planu wyłączenia PWA w UE w 2024 r.).
- **Aparat:** dostęp do kamery (`getUserMedia`) działa w zainstalowanej PWA. Znany kłopot: iOS potrafi ponownie pytać o zgodę na kamerę przy zmianie adresu wewnątrz aplikacji. Skaner trzymamy więc na jednym ekranie bez zmiany trasy. Zdjęcia posiłków robimy prostszą drogą: `<input type="file" accept="image/*" capture="environment">`.
- **Kody kreskowe:** Safari nie obsługuje Barcode Detection API, stąd biblioteka WebAssembly.
- **HTTPS jest wymagany** do kamery i instalacji. Test na telefonie wymaga więc wdrożenia albo tunelu (np. Cloudflare Tunnel) — sam adres w sieci domowej nie wystarczy.
- **Pamięć:** zainstalowana PWA nie podlega 7-dniowemu czyszczeniu danych, które dotyczy stron w Safari, ale iOS nie daje gwarancji trwałości. Dlatego telefon nie jest jedynym miejscem przechowywania.
- **Brak pracy w tle.** Aplikacja nie zsynchronizuje niczego, gdy jest zamknięta. Dane zdrowotne dosyła automatyzacja Skrótów, nie PWA.

### 3.4 Hosting

„0 zł" jest możliwe, ale ma cenę w wygodzie. Stan na 2026 **[DO WERYFIKACJI — darmowe plany często się zmieniają]**:

| Opcja | Koszt | Uwaga |
|---|---|---|
| Render (darmowy plan) + darmowy Postgres w Neon | 0 zł | Usługa zasypia po 15 min bez ruchu; wybudzenie trwa około minuty. Baza w Neon, bo darmowy Postgres na Renderze wygasa po 30 dniach |
| Google Cloud Run + Neon | 0 zł w ramach limitu | Wymaga konta rozliczeniowego z kartą; szybsze wybudzanie |
| Mały VPS | ok. 20–30 zł/mies. | Zawsze włączony, Postgres na tej samej maszynie, pełna kontrola |

**Ustalone:** zaczynamy od darmowego planu. Jeśli usypianie będzie irytować przy logowaniu posiłków kilka razy dziennie, przenosimy na VPS — to zmiana konfiguracji, nie kodu (całość w Dockerze).

**Zimny start a Skróty.** Uśpiony serwer budzi się około minuty, a akcja „Pobierz zawartość URL" w Skrótach ma nieudokumentowany limit czasu — relacje mówią o 25–60 s **[DO WERYFIKACJI w próbie B]**. Poranna wysyłka danych zdrowotnych trafiałaby więc regularnie w śpiący serwer. W Skrótach nieudane żądanie zwykle przerywa cały skrót, więc nie da się tego obejść ponowieniem po stronie telefonu. Zabezpieczenia:

1. **Podtrzymanie.** Zewnętrzny harmonogram (np. cron-job.org) co 14 minut woła `GET /api/healthz` w godzinach 6:00–23:00. Endpoint nie dotyka bazy i musi być prawdziwą trasą aplikacji. Jedna usługa mieści się w darmowym limicie 750 godzin miesięcznie; druga na tym samym koncie już nie.
2. **Idempotentny import ostatnich 7 dni** (6.2): nieudana wysyłka niczego nie gubi, bo kolejna udana uzupełnia braki.
3. **Baza:** Neon na darmowym planie usypia po 5 minutach, ale budzi się w czasie od kilkuset milisekund do kilku sekund — nie wymaga podtrzymania.
4. **Jeśli to nie wystarczy:** Cloud Run (zimny start liczony w sekundach, wymaga karty) albo płatna instancja Render bez usypiania (7 USD/mies.).

Podtrzymanie rozwiązuje przy okazji minutowe czekanie przy otwieraniu aplikacji w ciągu dnia.

**Jedna usługa.** Ten sam proces FastAPI serwuje API i zbudowany frontend (jeden obraz Dockera, katalog `web/dist`). Dzięki temu jest jedna darmowa usługa do podtrzymywania, frontend i API mają ten sam adres, a ciasteczko sesji nie wymaga konfiguracji CORS.

### 3.5 Logowanie i bezpieczeństwo

- Aplikacja jest w publicznym internecie i trzyma dane zdrowotne, więc wymaga logowania: jedno konto, hasło, ciasteczko sesji ustawiane przez serwer (`HttpOnly`, `Secure`).
- Endpoint dla Skrótów ma osobny, długi token w nagłówku `Authorization`, z prawem wyłącznie do zapisu próbek zdrowotnych.
- Kopia zapasowa bazy: codzienny zrzut (`pg_dump`) poza serwer. Eksport wszystkich danych do JSON z poziomu aplikacji.

**Repozytorium jest publiczne**, więc obowiązują cztery reguły:

1. Żadnych sekretów w repo. Klucze API, hasło, token Skrótów i adres bazy są w pliku `.env` (wpisanym do `.gitignore`) oraz w panelu hostingu. W repo leży tylko `.env.example` z pustymi wartościami.
2. Żadnych danych osobistych w repo: zrzutów bazy, eksportów dziennika, zdjęć posiłków, danych zdrowotnych.
3. `seed/plan_amp_2027.json` zawiera Twoje maksy treningowe i cele. To jedyny osobisty plik, który świadomie publikujemy — jeśli wolisz, trzymamy go poza repo i wgrywamy przez ekran importu.
4. Commity podpisujesz adresem `noreply` z GitHuba, żeby prywatny e-mail nie trafił do publicznej historii.

### 3.6 Zapisy offline (wymóg twardy, trafia do `AGENTS.md`)

TanStack Query domyślnie trzyma wstrzymane zapisy tylko w pamięci. Jeśli iOS ubije aplikację w tle (zablokowany telefon, przejście do innej aplikacji), niewysłana seria znika. Dlatego:

1. Klient jest opakowany w `PersistQueryClientProvider` z persisterem zapisującym do **IndexedDB** (własny persister na `idb-keyval` według dokumentacji TanStack albo `@tanstack/query-async-storage-persister`). Persister `query-sync-storage-persister` jest do `localStorage` i tu się nie nadaje.
2. Każdy zapis, który może trafić do kolejki, ma `mutationKey`, a jego `mutationFn` jest zarejestrowana globalnie przez `queryClient.setMutationDefaults`. Bez tego po restarcie aplikacji nie ma funkcji, którą dałoby się wznowić.
3. Po odtworzeniu stanu wywoływane jest `queryClient.resumePausedMutations()`.
4. Zapisy są idempotentne: `PUT` z kluczem naturalnym (seria: plan + sesja + indeks ćwiczenia) albo z identyfikatorem UUID nadanym na telefonie (wpis posiłku). Powtórzona wysyłka nie tworzy duplikatu.
5. Interfejs pokazuje licznik niewysłanych zapisów.

6. O braku połączenia decyduje wynik prawdziwego żądania, a nie przeglądarka. Telefon w sieci Wi-Fi bez internetu (częste na siłowni) zgłasza się jako „online", więc nieudane żądanie samo przełącza aplikację w tryb offline, a lekki `GET /api/healthz` jest odpytywany, aż serwer znów odpowie (`web/src/lib/connectivity.ts`).
7. Utrwalany stan ma czas życia 30 dni. Domyślne 24 godziny skasowałyby kolejkę po dniu bez otwierania aplikacji.
8. Wznowienie kolejki po starcie nie może blokować interfejsu: offline trwa ono do powrotu sieci.

Zakres kolejki: logowanie serii oraz wpisy posiłków z produktów, które telefon już zna. Skan nowego kodu i funkcje AI wymagają sieci.

Test akceptacyjny na prawdziwym iPhonie: tryb samolotowy → zapis serii → zamknięcie aplikacji z przełącznika aplikacji → otwarcie z siecią → seria jest w bazie.

## 4. Moduł 1 — Dieta

### 4.1 Źródła danych

| Źródło | Co daje | Licencja | Rola |
|---|---|---|---|
| **Open Food Facts (OFF)** | Produkty paczkowane po kodzie kreskowym; wartości z etykiet | ODbL | Skan kodu, wyszukiwarka |
| **USDA FoodData Central (FDC)** | Produkty podstawowe z pełnym profilem mikroskładników | CC0 | Witaminy i minerały |
| **Własne produkty** | To, czego nie ma w OFF | — | Ręcznie lub ze zdjęcia etykiety |

Nie kopiujemy bazy Fitatu. Funkcje można odtworzyć, danych nie.

OFF odpytuje **backend**, nie przeglądarka: ustawia wymagany nagłówek `User-Agent`, zapisuje wynik w Postgresie i przy kolejnym skanie odpowiada z własnej bazy.

```
GET https://world.openfoodfacts.org/api/v2/product/{EAN}
    ?fields=code,product_name,brands,quantity,serving_size,nutriments,categories_tags
```

Czytane pola `nutriments` (na 100 g): `energy-kcal_100g`, `proteins_100g`, `fat_100g`, `saturated-fat_100g`, `carbohydrates_100g`, `sugars_100g`, `fiber_100g`, `salt_100g`, `sodium_100g` oraz — jeśli są — `vitamin-*_100g`, `calcium_100g`, `iron_100g`, `magnesium_100g` itd. Każde pole jest opcjonalne.

### 4.2 Mikroskładniki — trzy poziomy pewności

**Poziom A — z etykiety.** Kcal, białko, tłuszcz, **kwasy nasycone**, węglowodany, cukry, **sól**: obowiązkowe na etykietach w UE (rozporządzenie 1169/2011). Błonnik dobrowolny, ale częsty.

**Poziom B — z tabel składu.** Witaminy i minerały dla produktów podstawowych (mięso, jaja, ryż, kasze, warzywa, owoce, nabiał) z FDC. Jednorazowo budujemy tabelę `generic_foods`: 300–500 pozycji z polskimi nazwami zmapowanych na rekordy FDC. Mapowanie robi model, Ty je przeglądasz.

**Poziom C — szacunek.** Witaminy i minerały dla produktów paczkowanych rzadko są na etykiecie, więc produkt dziedziczy profil z najbliższego produktu podstawowego (po kategorii OFF) z oznaczeniem `estimated`.

W interfejsie: makro, sól i nasycone jako liczby; mikroskładniki jako pokrycie normy z informacją, jaka część kalorii z dnia miała dane (np. „magnez: 78% normy, na podstawie 85% kalorii"). To wystarcza do wykrycia stałego niedoboru, nie do liczenia miligramów.

Lista **[ZAŁOŻENIE]**: witaminy A, D, E, K, C, B1, B2, B3, B6, B12, foliany; wapń, żelazo, magnez, cynk, potas, sód, fosfor, selen, jod.

### 4.3 Przepływy

1. **Skan kodu** → baza własna → OFF → karta produktu ze statusem weryfikacji (4.4) → „dodaj produkt", gdy nigdzie go nie ma.
2. **Zdjęcie etykiety → produkt.** Model przepisuje tabelę wartości odżywczych do JSON-a, Ty zatwierdzasz. Zatyka dziury w OFF dla polskich produktów.
3. **Wyszukiwarka** — najpierw ostatnie, ulubione i podstawowe; potem OFF.
4. **Zdjęcie posiłku → szkic.** Zdjęcie + opcjonalny opis → lista składników z gramaturą i przedziałem niepewności → backend dopasowuje każdy składnik do własnej bazy (rozdział 7) → edytujesz, także dopasowanie → zapis ze źródłem `estimated`.
5. **Opis tekstowy** → ta sama ścieżka bez obrazu.
6. **Posiłki i przepisy** — zestawy do dodania jednym dotknięciem.

Model dobrze rozpoznaje, co jest na talerzu, gorzej — ile. Dla posiłków domowych źródłem prawdy zostaje waga kuchenna i kod kreskowy.

### 4.4 Baza daje szkic, etykieta jest prawdą

Wynik etapu 0: zeskanowane produkty są w Open Food Facts, ale wartości bywają nieaktualne albo niepełne (np. śmietanka: 18 g węglowodanów w bazie, 10 g na etykiecie). OFF wypełniają użytkownicy, a producenci zmieniają receptury. Dlatego:

- Każdy produkt z zewnętrznego źródła jest **niezweryfikowany**, dopóki nie porównasz go z etykietą. Karta produktu pokazuje status i miesiąc ostatniej zmiany danych w źródle.
- **„Zgadza się z etykietą"** oznacza produkt jako zweryfikowany bez zmiany wartości.
- **„Popraw"** otwiera formularz ośmiu wartości. Zapis ustawia `macro_source = 'user'` i weryfikuje produkt. Oryginał ze źródła zostaje w `raw`.
- Zweryfikowany produkt nie jest nadpisywany danymi ze źródła.
- Reguły pewne, liczone w kodzie: tłuszcz 0 g oznacza kwasy nasycone 0 g, węglowodany 0 g oznaczają cukry 0 g. Nasycone nie mogą przekraczać tłuszczu, cukry węglowodanów. Wartości niemożliwe są odrzucane.
- Ostrzeżenie (nie blokuje zapisu): energia odbiega o ponad 20% od wyliczonej z makroskładników. Najczęściej to literówka.
- Krok 3 etapu 1: zdjęcie etykiety wypełnia ten sam formularz, a użytkownik zatwierdza.

Źródła są wymienne (osobny adapter na źródło), więc przy skanie można docelowo pokazać kilku kandydatów obok siebie. **FatSecret Platform API odrzucony:** darmowe warianty obejmują tylko dane z USA, a warunki pozwalają przechowywać wyłącznie identyfikatory produktów, co wyklucza własną bazę i zamrożoną historię.

## 5. Moduł 2 — Trening

### 5.1 Punkt wyjścia: plan już jest aplikacją

Plik `Plan_AMP_2027.html` to nie dokument, tylko kompletny tracker w jednym pliku: dane planu, logika i dziennik. Zawiera:

- 29 szablonów tygodni, 139 sesji, 601 pozycji ćwiczeń, 26 różnych ćwiczeń;
- sześć faz z własnym maksem treningowym (TM); ciężar serii = TM × procent, zaokrąglony do 2,5 kg;
- e1RM liczony z tabeli RPE (nie wzorem Epleya), sugestie nowego TM z singli;
- arkusz podejść na test 29.12 i na zawody, z podpowiedzią trzeciego podejścia;
- dopasowanie długości planu do daty zawodów (powtórka lub usunięcie tygodnia);
- dziennik: kg, powtórzenia, RPE, odhaczenie; siłownia, masa ciała i notatka przy sesji;
- zapis w przeglądarce oraz w chmurze Claude'a, gdy plik działa jako artefakt.

**Wniosek:** modułu treningowego nie projektujemy od zera, tylko przenosimy istniejący. Do czasu przeniesienia nadal trenujesz z obecnym plikiem — nic nie tracisz.

### 5.2 Format danych

Dane planu są wyodrębnione do pliku `plan_amp_2027.json` (do katalogu `seed/` w repo). Struktura:

```
meta            daty: start 26.10.2026, test 29.12.2026, zawody (domyślnie 15.05.2027)
training_max    TM fazy 1 i domyślne przyrosty między fazami
rpe_table       tabela % maksa dla pary (powtórzenia, RPE)
attempts        współczynniki podejść i reguła trzeciego podejścia
blocks, phases  nazwy i opis bloków
exercises       26 ćwiczeń: bój, rodzaj, wskazówka techniczna
weeks[]         id, phase, block, note, days[]
  days[]        code (D1–D5, TEST, OPT, AMP), title, minutes,
                day_offset (dzień tygodnia) albo days_before_meet
    exercises[] name, lift (S/B/D), kind, tier, sets, reps, percent_tm, rpe, weight_hint, note
```

`kind`: `sets` (serie na % TM), `single` (jedynka do RPE), `acc` (akcesoria), `att` (podejście). Pełny opis pól jest w samym pliku, w sekcji `field_guide`.

Format dziennika w obecnej aplikacji (do migracji):

```
klucz sesji:  "<id tygodnia>-<kod dnia>", np. "t03-D2"; powtórzony tydzień ma sufiks "b"
wpis sesji:   { e: { "<indeks ćwiczenia>": { kg, reps, rpe, done, ok } }, gym, bw, note, at }
ustawienia:   { tm: { "<faza>": { S, B, D } }, meet, adj: { ins, rem }, collars, bw }
```

### 5.3 Co robimy

1. Logika (`tm_for`, `load_for`, `e1rm`, `attempts_for`, budowa kalendarza z szablonów) przepisana na Python w `core/training.py`, z testami porównującymi wyniki z obecnym plikiem.
2. Ekrany przeniesione do React z zachowaniem obecnego układu, który już znasz.
3. Jednorazowa migracja dotychczasowych wpisów z dziennika do Postgresa.
4. Nowe względem obecnego pliku: masa ciała z modułu 3 zamiast ręcznego wpisu, powiązanie sesji z tętnem z opaski, dane dla Coacha.

## 6. Moduł 3 — Regeneracja

### 6.1 Skąd dane

Aplikacja nie rozmawia z opaską ani z wagą. Aplikacje producentów zapisują do Apple Health, a stamtąd dane wynosi automatyzacja Skrótów.

- **Helio Strap → Zepp → Apple Health:** tętno, SpO2, sen; HRV od firmware 3.3.10.3. Według relacji użytkowników trafia tam uśredniona wartość HRV z nocy.
- **Wskaźniki autorskie Zepp (BioCharge, wynik snu) nie trafiają do Apple Health** — własny wskaźnik liczymy sami.
- **OKOK International → Apple Health:** aplikacja deklaruje synchronizację masy ciała po wyrażeniu zgody. Potwierdzona jest tylko masa; procent tkanki tłuszczowej może nie przechodzić **[DO WERYFIKACJI]**.

### 6.2 Most: Skróty → backend

Skrót składa się z powtarzanego wzorca: **Znajdź próbki zdrowia** (typ, ostatnie N dni) → pobierz daty i wartości → **Pobierz zawartość URL** (metoda POST, nagłówek z tokenem).

Typy do pobrania: sen, HRV, tętno spoczynkowe, masa ciała, kroki, energia aktywna.

**Najważniejsze ograniczenie:** dane zdrowotne są zaszyfrowane, gdy telefon jest zablokowany. Automatyzacja „codziennie o 8:00" zadziała tylko wtedy, gdy akurat masz telefon w ręku — w przeciwnym razie kończy się błędem. Dlatego wyzwalacz musi być związany z używaniem telefonu:

| Wyzwalacz | Ocena |
|---|---|
| **Zamknięcie aplikacji Zepp** | Najlepszy: telefon jest odblokowany, a Zepp właśnie zsynchronizował opaskę, więc dane z nocy są świeże |
| Przycisk „Synchronizuj" w PWA (otwiera skrót przez adres `shortcuts://run-shortcut?name=…`) | Zapas ręczny **[DO WERYFIKACJI z poziomu zainstalowanej PWA]** |
| Stała godzina | Odradzam — zawodzi przy zablokowanym telefonie |

Endpoint:

```
POST /api/health/ingest
Authorization: Bearer <token tylko do zapisu>

{ "type": "hrv", "unit": "ms", "source": "Zepp",
  "starts": ["2026-12-28T03:10:00+01:00", ...],
  "values": [58, ...] }
```

Format jest celowo płaski (równoległe listy), bo tak Skróty zwracają dane; budowanie zagnieżdżonego JSON-a w Skrótach jest żmudne. Zapis jest idempotentny: ta sama próbka (typ, czas, źródło) wysłana dwa razy nie tworzy duplikatu, więc skrót zawsze wysyła ostatnie 7 dni i nieudana wysyłka (np. na uśpiony serwer, patrz 3.4) niczego nie gubi. Dokładny kształt ustali próba z etapu 0.

**Plan B:** aplikacja Health Auto Export — automatyczny eksport na dowolne REST API jest w niej funkcją płatną (subskrypcja albo zakup jednorazowy). **Plan C:** natywna powłoka z HealthKit. W domu jest Mac (partnerki, model do sprawdzenia), więc plan C może kosztować 0 zł: budowanie w Xcode na darmowym koncie Apple, z ponowną instalacją co 7 dni. HealthKit na darmowym koncie według części relacji działa **[DO WERYFIKACJI]**.

### 6.3 Wskaźnik regeneracji

Deterministyczny, w `core/readiness.py`: długość snu względem średniej z 14 dni; HRV z nocy względem średniej z 28 dni (w odchyleniach standardowych); tętno spoczynkowe względem średniej z 28 dni. Wynik: trzy stany i lista czynników. Przez pierwsze 2–4 tygodnie: „zbieram dane".

### 6.4 Trend wagi i bilans energii

- Trend: średnia krocząca z 7 dni.
- Adaptacyjne zapotrzebowanie z okna 14–21 dni: `średnie spożycie − (zmiana trendu wagi × 7700 kcal/kg ÷ liczba dni)`. Spożycie liczone jest z wartości zamrożonych we wpisach (rozdział 8), więc późniejsza edycja produktu nie zmienia wyniku wstecz.
- „Spalone kalorie" z opaski przy treningu siłowym są mało dokładne — pokazujemy je informacyjnie, nie korygujemy nimi limitu.

## 7. Warstwa AI

Klucze i wywołania są na serwerze. Jeden interfejs `AiProvider`, dwie implementacje, router po typie zadania; przy błędzie limitu (429) przejście na dostawcę zapasowego.

| Zadanie | Poziom | Domyślnie | Zapasowo |
|---|---|---|---|
| Skan kodu, wyszukiwanie | bez AI | — | — |
| Zdjęcie etykiety → produkt | tani | Gemini Flash-Lite (darmowy) | Claude Haiku 5.5 |
| Opis tekstowy → składniki | tani | Gemini Flash-Lite (darmowy) | Claude Haiku 5.5 |
| Zdjęcie posiłku → szkic | średni | Gemini Flash (darmowy) | Claude Sonnet 5.5 |
| Podsumowanie dnia | średni | Claude Sonnet 5.5 | Gemini Flash |
| Przegląd tygodnia | mocny | Claude Opus 5.5 | — |

**Na start działa tylko kolumna Gemini:** wszystkie zadania, także podsumowania, idą na darmowy klucz z AI Studio. Router ma obsługę Claude'a od początku, ale jest ona wyłączona, dopóki w konfiguracji nie pojawi się klucz. Skutek uboczny: przy wyczerpaniu darmowego limitu funkcje AI czekają do następnego dnia, a reszta aplikacji działa normalnie.

Stan na listopad 2026 **[DO WERYFIKACJI w panelach]**: darmowy poziom Gemini obejmuje modele Flash i Flash-Lite, flagowy Gemini 4 Argon jest płatny, a rzeczywiste limity widać tylko w AI Studio. Claude (USD za milion tokenów, wejście / wyjście): Haiku 5.5 — 0,10 / 0,50; Sonnet 5.5 — 2 / 10; Opus 5.5 — 4 / 20.

**Koszt** (założenia: zdjęcie ≈ 2000 tokenów wejścia i 600 wyjścia; dzień ≈ 6000 / 1000; tydzień ≈ 30 000 / 3000): 4 zdjęcia dziennie na Sonnet ≈ 1,20 USD/mies., podsumowania dnia ≈ 0,66, przeglądy tygodnia na Opus ≈ 0,78. Razem ok. **2,60 USD miesięcznie** przy samych płatnych modelach.

**Kontrakty.** Każde wywołanie zwraca JSON zgodny ze schematem Pydantic; odpowiedź niezgodna = jedno ponowienie, potem widoczny błąd. Model **nie zwraca identyfikatorów z naszej bazy**, bo ich nie zna i by je zmyślał. Zwraca opis składnika:

```json
{ "items": [ { "name_pl": "ryż biały gotowany", "name_en": "white rice, cooked",
               "category": "grains", "grams": 200, "grams_range": [150, 260],
               "per_100g_estimate": { "kcal": 130, "protein_g": 2.7, "fat_g": 0.3, "carbs_g": 28 },
               "confidence": "medium" } ],
  "notes": "Nie widać, czy użyto tłuszczu do smażenia." }
```

`category` to zamknięta lista kilkunastu wartości wymuszona schematem. Dopasowanie do bazy robi backend:

1. Wyszukiwanie przybliżone po nazwie polskiej, angielskiej i aliasach (`pg_trgm` + `unaccent`), zawężone kategorią.
2. Wynik powyżej progu podobieństwa → składnik dostaje `food_id`, a kalorie i mikroskładniki liczone są z bazy.
3. Kilku bliskich kandydatów → opcjonalnie tani model wybiera spośród 5 podanych pozycji. Lista jest zamknięta, więc nie ma czego zmyślić.
4. Brak dopasowania → wpis bez `food_id`, z makro z `per_100g_estimate`, oznaczony `estimated`, bez mikroskładników.

Na ekranie szkicu widać, do czego składnik został dopasowany, i można to zmienić. Niedopasowane nazwy trafiają do listy, z której uzupełniamy `generic_foods` i aliasy.

**Prywatność i bezpieczniki.**

- Do API idą agregaty, nie surowe próbki. Przełącznik w ustawieniach wyłącza wysyłanie danych zdrowotnych do modeli.
- Coach nie stawia diagnoz; przy utrzymujących się odchyleniach sugeruje konsultację.

**Robienie wagi przed startem.** Aplikacja ma tu pomagać, a nie odmawiać. Liczby nie pochodzą jednak z modelu (zasada 2), tylko z konfiguracji i kodu.

- **Wczesne ostrzeganie — główna funkcja.** Od 8 tygodni przed startem ekran „Waga na start" pokazuje trend masy ciała względem limitu 74,0 kg i tempo potrzebne, żeby dojść do niego samą dietą. Różnicę ma być widać w marcu, a nie w tygodniu zawodów.
- **Tydzień startowy to szablon, nie generacja.** Protokół (dieta lekkostrawna i niskobłonnikowa, sód, płyny, jedzenie po ważeniu) jest plikiem `meet_week` z wartościami na każdy dzień. Wartości wpisujesz Ty, najlepiej z trenerem lub dietetykiem sportowym; punktem wyjścia jest przegląd zaleceń dla trójboju z ważeniem 2 h przed startem (Renner, Helms, Kwan, Csapo, JISSN 2025). Aplikacja szablon wyświetla, odhacza i zestawia z poranną wagą.
- **Rola Coacha:** komentuje przebieg na podstawie danych („jesteś 0,4 kg nad planem na dziś, sen w normie"). Nie wymyśla dawek i nie zmienia szablonu.
- **Granica w kodzie, nie w prompcie.** Jeśli na 7 dni przed startem trend jest powyżej limitu o więcej niż próg (konfigurowalny; **[ZAŁOŻENIE]** 2% masy ciała, do potwierdzenia z trenerem), aplikacja mówi wprost, że to więcej, niż obejmuje szablon, i pokazuje opcje: start w wyższej kategorii albo decyzja z trenerem.
- **Poza zakresem aplikacji:** odwadnianie termiczne (sauna, gorące kąpiele), środki moczopędne i przeczyszczające. Przy ważeniu 2 h przed startem nie ma czasu na odrobienie strat, więc kosztują one wynik, nie tylko zdrowie.

## 8. Model danych (Postgres, szkic)

```sql
nutrient(id TEXT PK, name_pl, unit, grp, rda)          -- tylko mikroskładniki

food(id PK, kind,                 -- 'packaged' | 'generic' | 'recipe'
     barcode UNIQUE NULL, name, name_en NULL, brand, category, serving_g,
     origin,                      -- 'off' | 'fdc' | 'user' | 'ai_label'
     unit,                        -- 'g' | 'ml': wartości na 100 g albo na 100 ml (napoje)
     -- osiem wartości z etykiety UE jako kolumny; NULL = brak danych
     kcal, protein_g, fat_g, sat_fat_g, carbs_g, sugars_g, fiber_g, salt_g,
     macro_source,                -- skąd są aktualne wartości: 'label' | 'reference' | 'estimated' | 'user'
     source_updated_at NULL,      -- kiedy dane zmieniono w źródle (np. w OFF)
     verified_at NULL,            -- kiedy użytkownik potwierdził zgodność z etykietą
     generic_parent_id NULL, fetched_at, raw JSONB)   -- raw: oryginalna odpowiedź źródła
food_alias(food_id, alias)        -- synonimy do wyszukiwania; indeks GIN pg_trgm na name i alias
food_nutrient(food_id, nutrient_id, amount_per_100g,   -- mikroskładniki
              source,             -- 'label' | 'reference' | 'estimated'
              PRIMARY KEY(food_id, nutrient_id))

meal_entry(id UUID PK,            -- nadawany na telefonie (idempotentny zapis offline)
           date, meal_slot, food_id NULL, food_name, grams,
           -- wartości dla tej porcji, zamrożone w chwili zapisu
           kcal, protein_g, fat_g, sat_fat_g, carbs_g, sugars_g, fiber_g, salt_g,
           micros JSONB,          -- { "magnesium": { "amount": 48, "source": "estimated" } }
           source,                -- 'scan' | 'search' | 'photo' | 'text' | 'manual'
           ai_run_id NULL, created_at)
daily_target(date_from, nutrient_id, min, max)

plan(id PK, name, data JSONB)                    -- zawartość plan_amp_2027.json
plan_settings(plan_id PK, tm JSONB, meet_date, adj JSONB, collars)
session_log(plan_id, session_key, gym, bodyweight, note, updated_at,
            PRIMARY KEY(plan_id, session_key))   -- np. 't03-D2'
set_log(plan_id, session_key, ex_index, kg, reps, rpe, done, ok,
        PRIMARY KEY(plan_id, session_key, ex_index))

health_sample(type, starts_at, ends_at NULL, value, unit, source, received_at,
              PRIMARY KEY(type, starts_at, source))   -- surowe z ingestu
health_daily(date PK, sleep_min, sleep_deep_min, sleep_rem_min, hrv_ms,
             resting_hr, weight_kg, steps, active_kcal, readiness, factors JSONB)

ai_run(id PK, task, provider, model, input_tokens, output_tokens, cost_usd, status, created_at)
coach_note(id PK, date, scope, text, ai_run_id)       -- 'day' | 'week'
```

**Historia spożycia jest zamrożona.** Wpis w `meal_entry` przechowuje wartości policzone w chwili zapisu. Poprawienie produktu albo zmiana przepisu działa od tej pory w przód i nie zmienia dziennika wstecz. Gdy produkt miał zwykły błąd w danych, dostępna jest jawna akcja „przelicz wpisy od daty" — świadoma decyzja, a nie efekt uboczny edycji. `food_id` może być pusty dla składników ze zdjęcia, których nie udało się dopasować.

**Dlaczego makro w kolumnach.** Lista produktów w wyszukiwarce i suma dnia to wtedy proste zapytania bez złączeń. Osobna tabela zostaje dla mikroskładników, których lista jest długa i zmienna.

## 9. Struktura repozytorium

```
backend/
  app/
    api/          auth.py, health.py, diet.py, probe.py, deps.py     (dojdą: training.py, coach.py)
    core/         training.py, nutrients.py, energy.py, readiness.py,
                  health_ingest.py, barcode.py                        ← czysta logika z testami
    ai/           provider.py, router.py, schemas.py, gemini.py, claude.py
    off/          client.py
    db/           models.py, repo.py, session.py, migrations/
    tools/        seed.py, hash_password.py
    config.py, security.py, main.py
  tests/          w tym fixtures/training_reference.json (wartości z oryginalnego planu)
web/
  src/
    features/     home/ diet/ health/ (ekrany etapu 0), training/ coach/ (kolejne etapy)
    lib/          api.ts, offline.ts, connectivity.ts, scanner.ts, ean.ts
  public/         ikony
seed/             nutrients.json, plan_amp_2027.json (poza repo, patrz 3.5)
shortcuts/        budowa skrótu krok po kroku
scripts/          off_coverage.py (próba C)
docs/             ta dokumentacja, etap-0.md, decisions/
Dockerfile, docker-compose.yml, render.yaml, .env.example
AGENTS.md         zasady wspólne dla agentów
CLAUDE.md         import @AGENTS.md + rzeczy specyficzne dla Claude Code
```

`backend/app/core/` nie importuje FastAPI ani bazy — same funkcje na danych. To kod, który przeglądasz w pierwszej kolejności.

## 10. Etapy

| Etap | Zakres | Gotowe, gdy |
|---|---|---|
| **0. Próby ryzyka** | Repo, „hello world" wdrożony pod HTTPS, PWA na ekranie głównym. Próba A: skan kodu kreskowego na Twoim iPhonie. Próba B: skrót czyta masę ciała i kroki z Apple Health i wysyła na backend — raz na rozbudzony serwer i raz celowo na uśpiony, z pomiarem, po ilu sekundach skrót się poddaje. Próba C: 30 produktów z Twojej kuchni — ile jest w OFF. Próba D: zapis zrobiony w trybie samolotowym przetrwa zamknięcie aplikacji. Instrukcje: `docs/etap-0.md`. | Wszystkie cztery próby mają wynik. Jeśli A, B lub D zawiedzie, wracamy do decyzji o stacku, zanim powstanie reszta. |
| **1. Dieta bez AI** | Skan → OFF → baza, wyszukiwarka, własne produkty, posiłki, cele, widok dnia | Przez tydzień logujesz tu zamiast w Fitatu |
| **2. AI w diecie** | Router, zdjęcie etykiety, zdjęcie posiłku, opis tekstowy, licznik kosztów | Posiłek na mieście w mniej niż 30 sekund |
| **3. Regeneracja** | Pełny skrót, import, trend wagi, wskaźnik regeneracji, adaptacyjne TDEE | Rano widzisz stan regeneracji (start, gdy opaska dotrze) |
| **4. Trening** | Przeniesienie planu i dziennika, migracja wpisów | Trenujesz z nowej aplikacji, stary plik idzie do archiwum |
| **5. Coach** | Podsumowanie dnia i tygodnia | Podsumowanie mówi coś, czego sam byś nie zauważył |
| **6. Mikroskładniki** | Tabela `generic_foods`, dziedziczenie, widok pokrycia | Pokrycie witamin i minerałów z oznaczeniem pewności |

Trening jest dopiero czwarty, bo działający tracker już masz. Największą lukę wypełniają dieta i regeneracja.

## 11. Praca z Claude Code i Antigravity

- Claude Code pisze funkcje; Antigravity robi przegląd, uruchamia aplikację w przeglądarce i testuje. Jeden agent pisze na jednej gałęzi naraz.
- Antigravity czyta `AGENTS.md`, Claude Code czyta `CLAUDE.md`. Treść zasad trzymamy w `AGENTS.md`, a `CLAUDE.md` ją importuje.
- Jedno zadanie = jedna gałąź = jeden PR z testami. Agent dostaje konkretny rozdział tej dokumentacji jako specyfikację.
- `AGENTS.md` zawiera wymogi twarde, których agent nie może pominąć: trwała kolejka offline (3.6), reguły publicznego repo (3.5), zamrożona historia spożycia (8), liczby z kodu zamiast z modelu (2).
- Najpierw kontrakt (model Pydantic, tabela), potem kod. Typy dla frontendu generujemy ze schematu OpenAPI, który FastAPI wystawia sam.

## 12. Ryzyka

| Ryzyko | Skutek | Ograniczenie |
|---|---|---|
| Most przez Skróty okaże się zawodny | Dziury w danych zdrowotnych | Próba B w etapie 0; idempotentny import ostatnich dni; plany B i C |
| Kłopoty z kamerą w PWA | Skan działa nierówno | Próba A w etapie 0; zapas: zdjęcie kodu zamiast podglądu na żywo |
| Usypianie darmowego hostingu | Aplikacja otwiera się minutę; skrót zdrowotny przekracza limit czasu | Podtrzymanie co 14 min, idempotentny import 7 dni; dalej Cloud Run albo płatna instancja (3.4) |
| Model zwraca składnik spoza bazy | Brak mikroskładników, gorsza dokładność | Dopasowanie po stronie backendu, zapas w postaci szacunku modelu, lista braków do uzupełnienia (7) |
| Edycja produktu zmienia historię | Rozjechany bilans energii | Wartości zamrożone we wpisach (8) |
| Braki polskich produktów w OFF | Skan często nie znajduje | Próba C; zdjęcie etykiety → produkt |
| Zakres: trzy aplikacje naraz | Nic nie jest skończone | Etapy z kryterium „używam codziennie" |
| Tarcie przy logowaniu | Porzucenie po dwóch tygodniach | Ostatnie, ulubione i posiłki jednym dotknięciem ważniejsze niż AI |
| Brak zasięgu na siłowni | Seria znika, gdy iOS ubije aplikację w tle | Kolejka zapisów utrwalana w IndexedDB, test na telefonie (3.6) |
| Fałszywa precyzja | Decyzje na podstawie szumu | Źródło przy każdej wartości; trendy zamiast pojedynczych pomiarów |
| Wyciek danych zdrowotnych | Dane w publicznym internecie | Logowanie, osobny token dla Skrótów, HTTPS, kopie zapasowe |

## 13. Otwarte pytania

1. Czy `seed/plan_amp_2027.json` ma trafić do publicznego repo? Do czasu decyzji plik jest w `.gitignore`.
2. Które mikroskładniki są priorytetem (lista z 4.2 czy krótsza)?
3. Licencja repozytorium (publiczne repo bez licencji oznacza „wszelkie prawa zastrzeżone").

## 14. Źródła

- [Open Food Facts — dokumentacja API](https://openfoodfacts.github.io/documentation/docs/Product-Opener/api/tutorial-off-api/)
- [USDA FoodData Central](https://fdc.nal.usda.gov/index.html)
- [iOS PWA Compatibility (firt.dev)](https://firt.dev/notes/pwa-ios/)
- [Skanowanie kodów na iOS: brak Barcode Detection API](https://dev.to/ilhannegis/barcode-scanning-on-ios-the-missing-web-api-and-a-webassembly-solution-2in2)
- [WebKit — ponowne pytania o kamerę w PWA (bug 215884)](https://bugs.webkit.org/show_bug.cgi?id=215884)
- [web.dev — pamięć przeglądarki, limit 7 dni i wyjątek dla zainstalowanych PWA](https://web.dev/articles/storage-for-the-web)
- [TechCrunch — Apple wycofuje się z blokowania PWA w UE](https://techcrunch.com/?p=2673309)
- [Automators — dane Health niedostępne przy zablokowanym iPhonie](https://talk.automators.fm/t/get-workouts-from-health-not-working-when-iphone-locked/13100)
- [Przykład: Skróty → Znajdź próbki zdrowia → POST](https://jngiam.bearblog.dev/syncing-apple-health-data-to-claude-code/)
- [OKOK International — App Store](https://apps.apple.com/app/id1028294311)
- [Health Auto Export — eksport REST API](https://www.github.com/Lybron/health-auto-export)
- [Helio Strap — HRV w Apple Health](https://gadgetsandwearables.com/2025/10/28/helio-strap-hrv-sync-apple-health/)
- [Zepp a Apple Health — relacje użytkowników](https://feedback.bevel.health/feature-requests/p/integrate-with-amazfit-helio-strap-zepp-app)
- [Render — dokumentacja darmowego planu](https://render.com/docs/free)
- [Render — podtrzymywanie usługi i pułapki](https://odown.com/blog/how-to-keep-a-render-free-service-from-sleeping/)
- [Skróty — limit czasu żądania (Apple Community)](https://discussions.apple.com/thread/254691588)
- [Neon — rozszerzenia Postgresa (pg_trgm)](https://neon.tech/docs/reference/pg-extensions)
- [Neon — usypianie i wybudzanie](https://neon.com/faqs/cloud-postgres-services-scale-zero-data)
- [Cloud Run — zimny start](https://docs.cloud.google.com/run/docs/tips?hl=nl)
- [TanStack Query — persistQueryClient i persister IndexedDB](https://tanstack.com/query/latest/docs/framework/react/plugins/persistQueryClient)
- [TanStack Query — przykład offline (setMutationDefaults)](https://tanstack.com/query/v4/docs/framework/react/examples/offline)
- [Renner i in. 2025 — krótkoterminowa manipulacja masą ciała w trójboju (JISSN)](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12667356/)
- [Porównanie darmowego hostingu backendów 2026](https://snapdeploy.dev/blog/free-backend-hosting-2026-apis-servers)
- [Gemini API — limity i poziomy](https://ai.google.dev/gemini-api/docs/rate-limits)
- [Claude API — cennik](https://platform.claude.com/docs/en/about-claude/pricing)
- [Antigravity — zasady i AGENTS.md](https://antigravity.google/docs/rules?tab=ide)
