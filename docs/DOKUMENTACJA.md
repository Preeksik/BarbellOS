# BarbellOS — dokumentacja techniczna v0.9

Stan: 17.11.2026.

Zmiany w v0.9: profil użytkownika i plan kalorii oraz makroskładników z celem redukcja, utrzymanie albo masa (4.10); tabela `user_profile` (8); zakładka „Start” zastąpiona przez „Profil” (diagnostyka etapu 0 schowana pod profilem); praca bezpośrednio na `main` (11).

Zmiany w v0.8 (etap 1, kroki 4–6): cele dzienne wersjonowane datą (4.7); wyszukiwarka, ostatnie, ulubione i produkt bez kodu (4.8); zapisane posiłki (4.9); nowe kolumny i tabele (8); zakres kolejki offline (3.6).

Zmiany w v0.7 (etap 1, krok 3): zdjęcie etykiety wypełnia formularz produktu, a kod spoza Open Food Facts można dodać jako własny produkt (4.6); Gemini przez Interactions API i sprawdzone nazwy modeli (7); zakres kolejki offline (3.6); przycisk „Nowa wersja" po wdrożeniu (3.3).

Zmiany w v0.6 (etap 1, krok 2): dziennik dnia (4.5); wpis ma ilość i jednostkę g/ml zamiast samych gramów (8); kolejność zapisów dziennika, podgląd bez sieci i wygasła sesja w kolejce (3.6); znaczniki czasu nadaje aplikacja, a nie baza (8).

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
- **Aktualizacja po wdrożeniu.** Service worker podaje aplikację z pamięci telefonu, więc po wdrożeniu telefon nadal pokazuje starą wersję, a nowa pobiera się w tle. Gdy jest gotowa, pod nagłówkiem pojawia się przycisk „Nowa wersja aplikacji": stuknięcie przełącza kod i wczytuje aplikację ponownie. Przełączenie nie dzieje się samo, żeby nie skasować formularza w trakcie wpisywania. Aplikacja sprawdza nową wersję przy starcie i przy każdym powrocie z tła (iOS wznawia ją bez ponownego wczytania). Datę zbudowania widać na zakładce „Start". Kod: `web/src/lib/appUpdate.ts`.

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
7. Utrwalany stan ma czas życia 30 dni. Domyślne 24 godziny skasowałyby kolejkę po dniu bez otwierania aplikacji. Czas trzymania nieużywanych danych w pamięci (`gcTime`) to 20 dni i nie może przekroczyć ok. 24,8 dnia: przeglądarka liczy opóźnienia na 32 bitach, większa wartość przepełnia licznik i dane znikają natychmiast.
8. Wznowienie kolejki po starcie nie może blokować interfejsu: offline trwa ono do powrotu sieci.
9. Zapisy dziennika mają wspólny `scope`, więc idą do serwera pojedynczo, w kolejności wykonania (dodanie przed zmianą, zmiana przed usunięciem).
10. Zmiana jest widoczna od razu jako podgląd policzony na telefonie (`web/src/lib/diary.ts`). To jedyny wyjątek od zasady, że liczy serwer: po wysłaniu ostatniego zapisu z kolejki dzień jest pobierany z serwera i podgląd znika.
11. Odpowiedź 401 nie usuwa zapisu z kolejki. Aplikacja pokazuje logowanie, a zapis ponawia się po zalogowaniu.

Zakres kolejki: logowanie serii, wpisy posiłków z produktów, które telefon już zna (także dodanie zapisanego posiłku), poprawka i zapis własnego produktu (z kodem i bez), ulubione, cele dzienne oraz zapisanie i usunięcie posiłku. Wyszukiwanie wymaga sieci; listy „Ostatnie”, „Ulubione” i „Posiłki” są w pamięci telefonu. Skan nowego kodu i funkcje AI (odczyt etykiety) wymagają sieci: odczyt jest zwykłym żądaniem, nie zapisem w kolejce, więc bez połączenia od razu pokazuje błąd, a formularz da się wypełnić ręcznie.

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
- Zdjęcie etykiety wypełnia ten sam formularz, a użytkownik zatwierdza (4.6).

Źródła są wymienne (osobny adapter na źródło), więc przy skanie można docelowo pokazać kilku kandydatów obok siebie. **FatSecret Platform API odrzucony:** darmowe warianty obejmują tylko dane z USA, a warunki pozwalają przechowywać wyłącznie identyfikatory produktów, co wyklucza własną bazę i zamrożoną historię.

### 4.5 Dziennik dnia

Dzień składa się z pięciu posiłków: śniadanie, II śniadanie, obiad, podwieczorek, kolacja. Wpis to produkt, ilość (g albo ml) i posiłek.

- `PUT /api/diary/entries/{id}` dodaje wpis albo go zmienia. Identyfikator UUID nadaje telefon, więc powtórzona wysyłka nie tworzy duplikatu.
- Przy dodaniu wartości porcji są liczone z produktu i zamrażane. Przy zmianie ilości zamrożone wartości są **skalowane**, a nie liczone od nowa: wpis nadal odpowiada produktowi z chwili dodania.
- `DELETE /api/diary/entries/{id}` usuwa wpis; usunięcie nieistniejącego wpisu też kończy się powodzeniem.
- `GET /api/diary/{data}` zwraca wpisy, sumę dnia i sumy posiłków. Brak danych we wpisie liczy się w sumie jak zero.
- Dzień to data według zegara telefonu, nie UTC: wpis dodany po północy trafia do nowego dnia.
- Logika: `backend/app/core/diary.py`.

### 4.6 Zdjęcie etykiety i własny produkt

Formularz produktu (ten sam co „Popraw") ma przycisk „Zdjęcie etykiety". Zdjęcie niczego nie zapisuje: wypełnia pola, a zapis następuje dopiero po „Zapisz".

- Telefon zmniejsza zdjęcie do JPEG-a o dłuższym boku 2000 px i wysyła je w treści żądania `POST /api/foods/label`. Serwer rozpoznaje format po zawartości pliku (JPEG, PNG, WebP, HEIC) i odrzuca pliki powyżej 8 MB.
- Model **przepisuje** tabelę: wartości z kolumny „na 100 g" albo „na 100 ml", energia w kcal, brak wartości jako `null`. Polecenie zabrania przeliczania i szacowania (`backend/app/ai/prompts.py`). Gdy etykieta ma tylko kolumnę na porcję, wartości zostają puste.
- Resztę robi kod (`backend/app/core/label.py`): wartość niemożliwa (np. kJ przepisane jako kcal) nie trafia do formularza i jest wymieniona w uwagach; tłuszcz 0 g daje nasycone 0 g; sprzeczność (cukry większe od węglowodanów) i energia niepasująca do makroskładników są pokazane jako uwagi, bo kod nie wie, która liczba jest błędna.
- Odpowiedź to szkic: nazwa, marka, porcja, jednostka, osiem wartości i uwagi. Gdy nie odczytano żadnej wartości, serwer odpowiada błędem 422 z prośbą o lepsze zdjęcie.
- W formularzu pola wpisane ze zdjęcia są podświetlone. Pole, którego model nie odczytał, zostaje bez zmian. Nazwa i marka są wpisywane tylko w puste pola.
- Błędy są widoczne i rozróżnione: brak klucza (503), wyczerpany limit (429), odpowiedź niezgodna ze schematem po jednym ponowieniu albo błąd dostawcy (502). W każdym przypadku formularz można wypełnić ręcznie.
- Każde wywołanie modelu trafia do `ai_run` (zadanie, dostawca, model, tokeny, status). Koszt policzy licznik z etapu 2.

**Własny produkt.** Gdy zeskanowanego kodu nie ma ani w naszej bazie, ani w Open Food Facts, karta proponuje „Dodaj produkt": ten sam formularz, pusty.

- `PUT /api/foods/barcode/{kod}` tworzy produkt. Kluczem jest kod kreskowy, więc powtórzona wysyłka nie tworzy duplikatu; dla kodu, który już istnieje, działa jak poprawka.
- `origin` to `ai_label`, gdy formularz wypełniło zdjęcie, albo `user`, gdy wartości wpisano ręcznie. W obu przypadkach `macro_source = 'user'` i produkt jest od razu zweryfikowany, bo wartości zatwierdził człowiek.
- Kolejny skan tego kodu odpowiada z własnej bazy i nie pyta Open Food Facts.
- Zapis jest zarejestrowany w kolejce offline, ale bez podglądu: produkt dostaje identyfikator dopiero na serwerze, więc do dnia można go dodać po wysłaniu.
- Produkt bez kodu kreskowego: 4.8.

### 4.7 Cele dzienne

Cele dotyczą ośmiu wartości z etykiety. Każda ma stały rodzaj celu (`backend/app/core/targets.py`):

| Rodzaj | Składniki | Znaczenie na pasku |
|---|---|---|
| cel | kalorie, tłuszcz, węglowodany | „zostało X", po przekroczeniu „+X ponad cel" |
| co najmniej | białko, błonnik | po osiągnięciu „cel osiągnięty", przekroczenie nie jest problemem |
| najwyżej | nasycone, cukry, sól | „zostało X do limitu", po przekroczeniu „+X ponad limit" |

- **Cele są wersjonowane datą.** Zapis obowiązuje od oglądanego dnia do następnej zmiany. Dni wcześniejsze zachowują cele, które wtedy obowiązywały, więc zmiana celu nie przepisuje historii.
- `PUT /api/targets/{od_dnia}` zapisuje komplet ośmiu wartości (puste = bez celu). Zapis z tą samą datą zastępuje poprzedni (idempotentny). Usunięty cel nie wraca z wcześniejszej wersji, bo zapisywany jest wiersz „bez celu".
- `GET /api/targets/{dzień}` zwraca cele obowiązujące w danym dniu: wersję z najpóźniejszą datą nie późniejszą niż ten dzień.
- Cel musi być większy od zera; górne granice chronią przed literówką (np. 10 000 kcal).
- Pasek pokazuje sumę dnia (także podgląd z kolejki offline) względem celu. Wartości bez celu są pokazane drobno pod paskami.
- **[ZAŁOŻENIE]** Kalorie przekroczone choćby o 1 kcal są oznaczone jako „ponad cel". Tolerancję dodamy, jeśli będzie przeszkadzać.

### 4.8 Wyszukiwarka, ostatnie, ulubione, produkt bez kodu

Zakładka „Dodaj" zastępuje „Skan": wyszukiwarka, przyciski „Skanuj kod" i „Produkt bez kodu", a pod spodem listy „Posiłki", „Ulubione" i „Ostatnie".

- **Własna baza** jest przeszukiwana przy pisaniu (`GET /api/foods/search?q=`). Każde słowo zapytania musi być początkiem słowa w nazwie albo marce, bez polskich znaków i wielkości liter („ser wiej" znajduje „Serek wiejski"). Wyżej są całe słowa, nazwa zaczynająca się od zapytania, produkty często dodawane do dziennika i ulubione. Logika: `backend/app/core/search.py`. Dopasowanie jest liczone w Pythonie, bo baza jednego użytkownika ma setki produktów; indeksy pg_trgm przydadzą się w etapie 6.
- **Open Food Facts** jest przeszukiwane na przycisk (`GET /api/foods/search/off?q=`), przez search-a-licious (`https://search.openfoodfacts.org/search`): stare API v2 nie ma wyszukiwania po nazwie. OFF pozwala na 10 wyszukiwań na minutę z jednego adresu i za przekroczenie blokuje adres, dlatego serwer przepuszcza najwyżej 8 na minutę i nie wyszukuje przy każdym znaku. Wynik z OFF nie zapisuje się w bazie: po wybraniu produkt jest pobierany po kodzie kreskowym, jak przy skanie.
- **Ostatnie** (`GET /api/foods/recent`): 20 ostatnio jedzonych produktów, każdy raz, z ilością z ostatniego wpisu, która jest podpowiedzią przy dodawaniu.
- **Ulubione:** gwiazdka na karcie produktu (`PUT /api/foods/{id}/favorite` ze stanem, nie przełącznikiem, więc powtórka jest bezpieczna).
- **Produkt bez kodu** (danie domowe, produkt na wagę): ten sam formularz co „Popraw", także ze zdjęciem etykiety. `PUT /api/foods/custom/{uuid}` z identyfikatorem nadanym na telefonie, więc zapis może czekać w kolejce offline bez ryzyka duplikatu.

### 4.9 Zapisane posiłki

Zestaw produktów z ilościami, np. „Śniadanie standard", dodawany do dnia jednym stuknięciem.

- **Zapis:** w dzienniku przy posiłku (śniadanie, obiad…) przycisk „Zapisz jako posiłek" zapisuje jego produkty z ilościami. Wpis bez produktu (w przyszłości ze zdjęcia posiłku) jest pomijany.
- **Dodanie:** w zakładce „Dodaj" wybierasz posiłek dnia (podpowiadany według godziny) i stukasz zestaw. Powstają zwykłe wpisy dziennika, po jednym na produkt, ze źródłem `meal`. Działa bez sieci tak samo jak pojedynczy produkt. „Cofnij" usuwa właśnie dodane wpisy.
- **Zestaw przechowuje produkty i ilości, nie wartości.** Wartości liczy i zamraża wpis dziennika w chwili dodania (rozdział 8), więc poprawka produktu działa od tej pory w przód, a dodane wcześniej wpisy się nie zmieniają. Kalorie zestawu na liście są liczone według produktów na dziś.
- `GET /api/meals`, `PUT /api/meals/{uuid}` (nazwa i skład; powtórka zastępuje skład), `DELETE /api/meals/{uuid}` (wpisy w dzienniku zostają). Logika: `backend/app/core/meals.py`.
- Edycja składu zestawu (zmiana ilości, usunięcie produktu) nie jest jeszcze dostępna: zestaw zapisuje się od nowa z dziennika.

### 4.10 Profil i plan żywieniowy

Zakładka „Profil": płeć, data urodzenia, wzrost, masa ciała, tryb życia, średnia kroków, treningi siłowe i cardio, cel (schudnąć, utrzymać, przytyć), tempo i opcjonalnie białko na kg. Z tego serwer liczy plan (`backend/app/core/profile.py`); to szacunek z ogólnych wzorów, punkt startowy.

| Liczba | Jak liczona | Źródło |
|---|---|---|
| Przemiana spoczynkowa (BMR) | 10 × kg + 6,25 × cm − 5 × wiek, +5 (mężczyzna) albo −161 (kobieta) | Mifflin-St Jeor, 1990 |
| Zapotrzebowanie (TDEE) | suma składników z tabeli niżej, podzielona przez 0,9 (trawienie ≈ 10% całości) | metoda czynnikowa |
| Deficyt / nadwyżka | tempo (kg/tydz.) × 7700 kcal ÷ 7 | 1 kg tkanki ≈ 7700 kcal |
| Białko (co najmniej) | domyślnie 2,2 g/kg na redukcji, 1,8 g/kg w pozostałych celach; do zmiany 1,2–3,1 | ISSN 2017 |
| Tłuszcz | 25% kalorii (20%, gdy białko zajmuje dużo kalorii) | National Academies, 20–35% |
| Węglowodany | reszta kalorii | — |
| Błonnik (co najmniej) | 14 g na 1000 kcal, nie mniej niż 25 g | Dietary Guidelines; WHO |
| Nasycone (najwyżej) | 10% kalorii | WHO |
| Sól (najwyżej) | 5 g | WHO |
| Cukry | bez limitu: zalecenie WHO dotyczy cukrów dodanych, a etykieta podaje wszystkie cukry | — |

**Zapotrzebowanie ze składników.** Jeden współczynnik „aktywności" mieszał pracę, chodzenie i treningi, a student dojeżdżający autem z 5000 kroków i czterema treningami nie pasował do żadnej kategorii. Każdy składnik jest więc liczony osobno i pokazany w tabeli „Na co idą kalorie":

| Składnik | Jak liczony |
|---|---|
| Przemiana spoczynkowa | Mifflin-St Jeor |
| Tryb życia (bez chodzenia i treningów) | siedzący +15% BMR (nauka, biuro, dojazd autem), mieszany +25%, praca na stojąco +40%, ciężka praca fizyczna +70% **[ZAŁOŻENIE]** |
| Kroki | średnia kroków × długość kroku (0,415 × wzrost u mężczyzn, 0,413 u kobiet) × 0,5 kcal na kg na km ponad spoczynek (równanie ACSM: 0,1 ml O₂ na kg na metr) |
| Trening siłowy | treningi w tygodniu × minuty × (5 MET − 1) × kg ÷ 7 dni; 5 MET to przysiad i martwy ciąg w Compendium of Physical Activities 2024 (trójbój „intensywnie": 6 MET), niżej ze względu na przerwy między seriami |
| Cardio | minuty w tygodniu × (7 MET − 1) × kg ÷ 7 dni |
| Trawienie | 10% całości |

Przykład: 80 kg, 180 cm, 28 lat, tryb siedzący, 5000 kroków (≈ 3,7 km ≈ 150 kcal), 4 treningi po 75 min (≈ 230 kcal dziennie) daje 2707 kcal, czyli 1,51 × BMR. Procenty trybu życia są dobrane tak, żeby całość mieściła się w zakresach PAL FAO/WHO/UNU 2004 (siedzący 1,40–1,69, aktywny 1,70–1,99, bardzo aktywny 2,00–2,40); test `test_whole_expenditure_stays_in_who_pal_ranges` tego pilnuje. Średnią kroków wpisuje się ręcznie (Zdrowie → Kroki → widok roczny); w etapie 3 przyjdzie z Apple Zdrowie, a trening z sesji w module treningowym.

Bezpieczniki w kodzie:

- Tempo redukcji: 0,25 / 0,5 / 0,75 / 1 kg na tydzień, ale najwyżej 1% masy ciała na tydzień. Szybsze wybrane tempo jest obniżane z wyjaśnieniem.
- Cel kaloryczny redukcji nie schodzi poniżej przemiany spoczynkowej. Gdy wybrane tempo by tego wymagało, plan zatrzymuje się na BMR i podaje wynikające z tego tempo.
- Tempo masy: 0,1 / 0,25 / 0,5 kg na tydzień.

Plan ma przy każdej liczbie opis, skąd się wzięła („Skąd te liczby"). **Plan nie zmienia celów sam:** przycisk „Ustaw jako cele dzienne od dziś" zapisuje je przez `PUT /api/targets/{dziś}` (4.7), więc wcześniejsze dni zachowują stare cele.

- `GET /api/profile` zwraca profil i plan (`null`, gdy profilu nie wypełniono). `PUT /api/profile` zapisuje cały profil (idempotentne) i zwraca nowy plan. Wiek liczony jest od dzisiejszej daty w strefie `DEFAULT_TIMEZONE`.
- Zapis profilu działa bez sieci (kolejka offline). Plan liczy serwer, więc do czasu wysłania ekran pokazuje informację, że plan przeliczy się po powrocie sieci.
- Masę ciała wpisuje się ręcznie. W etapie 3 będzie brana z trendu wagi z Apple Health, a zapotrzebowanie korygowane adaptacyjnie (6.4). Wtedy też AI skomentuje plan na podstawie gotowych liczb; liczby nadal liczy kod (zasada 2).

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

**Gemini: stan na 16.11.2026** (dokumentacja na aistudio.google.com/docs). Wywołania idą przez Interactions API: `POST /v1beta/interactions`, klucz w nagłówku `x-goog-api-key`, schemat JSON w `response_format`, zdjęcie jako część `input` zakodowana w base64. Starsze `generateContent` nadal działa, ale nowe projekty mają używać Interactions. Wysyłamy `store: false`, żeby zdjęcia i rozmowy nie były przechowywane po stronie Google. Domyślne modele: `gemini-3.5-flash-lite` (tani) i `gemini-3.8-flash` (średni); oba są na darmowym poziomie, podobnie jak `gemini-4-hydrogen`. Zmienia się je w `.env` (`GEMINI_MODEL_CHEAP`, `GEMINI_MODEL_MID`). Schemat Pydantic jest przed wysłaniem upraszczany do podzbioru JSON Schema z dokumentacji (`backend/app/ai/json_schema.py`). Wywołania Claude'a powstaną w etapie 2: do tego czasu dostawca zgłasza się jako niedostępny, także gdy klucz jest ustawiony.

Stan na listopad 2026 **[DO WERYFIKACJI w panelach]**: darmowy poziom Gemini obejmuje modele Flash i Flash-Lite, flagowe Gemini 4 Argon i Carbon są płatne, a rzeczywiste limity widać tylko w AI Studio. Claude (USD za milion tokenów, wejście / wyjście): Haiku 5.5 — 0,10 / 0,50; Sonnet 5.5 — 2 / 10; Opus 5.5 — 4 / 20.

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
     generic_parent_id NULL, fetched_at, raw JSONB,   -- raw: oryginalna odpowiedź źródła
     favorite_at NULL,            -- kiedy dodany do ulubionych
     client_id UUID UNIQUE NULL)  -- produkt bez kodu: identyfikator z telefonu (idempotentny zapis)
food_alias(food_id, alias)        -- synonimy do wyszukiwania; indeks GIN pg_trgm na name i alias
food_nutrient(food_id, nutrient_id, amount_per_100g,   -- mikroskładniki
              source,             -- 'label' | 'reference' | 'estimated'
              PRIMARY KEY(food_id, nutrient_id))

meal_entry(id UUID PK,            -- nadawany na telefonie (idempotentny zapis offline)
           date, meal_slot,       -- 'breakfast' | 'second_breakfast' | 'lunch' | 'snack' | 'dinner'
           food_id NULL, food_name,
           amount, unit,          -- ilość w gramach albo mililitrach, jak w produkcie
           -- wartości dla tej porcji, zamrożone w chwili zapisu
           kcal, protein_g, fat_g, sat_fat_g, carbs_g, sugars_g, fiber_g, salt_g,
           micros JSONB,          -- { "magnesium": { "amount": 48, "source": "estimated" } }
           source,                -- 'scan' | 'search' | 'photo' | 'text' | 'manual' | 'meal'
           ai_run_id NULL, created_at)
daily_target(date_from, nutrient_id, min, max)  -- wersja celów od date_from; min i max puste = bez celu
user_profile(id PK = 1, sex, birth_date, height_cm, weight_kg,              -- 4.10
             lifestyle, steps_per_day, strength_sessions_week, strength_minutes,
             cardio_minutes_week, goal, pace_kg_week, protein_g_per_kg NULL, updated_at)
meal_template(id UUID PK, name, created_at, updated_at)   -- zapisany posiłek (4.9)
meal_template_item(meal_id, position, food_id, amount,   -- skład: produkty i ilości, bez wartości
                   PRIMARY KEY(meal_id, position))

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
    api/          auth.py, health.py, diet.py, diary.py, targets.py, meals.py, profile.py, probe.py, deps.py
    core/         training.py, nutrients.py, diary.py, label.py, targets.py, search.py, meals.py, profile.py,
                  energy.py, readiness.py,
                  health_ingest.py, barcode.py                        ← czysta logika z testami
    ai/           provider.py, router.py, schemas.py, json_schema.py, prompts.py,
                  gemini.py, claude.py
    off/          client.py
    db/           models.py, repo.py, session.py, migrations/
    tools/        seed.py, hash_password.py
    config.py, security.py, main.py
  tests/          w tym fixtures/training_reference.json (wartości z oryginalnego planu)
web/
  src/
    features/     diet/ diary/ health/ profile/ home/ (diagnostyka), training/ coach/ (kolejne etapy)
    lib/          api.ts, offline.ts, connectivity.ts, scanner.ts, ean.ts, diary.ts, label.ts,
                  number.ts, targets.ts, meals.ts, appUpdate.ts
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
| **1. Dieta** | Skan → OFF → baza, zdjęcie etykiety (jedyna funkcja AI w tym etapie, przeniesiona z etapu 2 po próbie C), wyszukiwarka, własne produkty, posiłki, cele, widok dnia. Kroki: `docs/etap-1.md` | Przez tydzień logujesz tu zamiast w Fitatu |
| **2. AI w diecie** | Zdjęcie posiłku, opis tekstowy, dostawca Claude, licznik kosztów | Posiłek na mieście w mniej niż 30 sekund |
| **3. Regeneracja** | Pełny skrót, import, trend wagi, wskaźnik regeneracji, adaptacyjne TDEE | Rano widzisz stan regeneracji (start, gdy opaska dotrze) |
| **4. Trening** | Przeniesienie planu i dziennika, migracja wpisów | Trenujesz z nowej aplikacji, stary plik idzie do archiwum |
| **5. Coach** | Podsumowanie dnia i tygodnia | Podsumowanie mówi coś, czego sam byś nie zauważył |
| **6. Mikroskładniki** | Tabela `generic_foods`, dziedziczenie, widok pokrycia | Pokrycie witamin i minerałów z oznaczeniem pewności |

Trening jest dopiero czwarty, bo działający tracker już masz. Największą lukę wypełniają dieta i regeneracja.

## 11. Praca z Claude Code i Antigravity

- Claude Code pisze funkcje; Antigravity robi przegląd, uruchamia aplikację w przeglądarce i testuje. Agenci nie pracują równocześnie: jeden pisze, drugi czeka.
- Antigravity czyta `AGENTS.md`, Claude Code czyta `CLAUDE.md`. Treść zasad trzymamy w `AGENTS.md`, a `CLAUDE.md` ją importuje.
- Jedno zadanie = jeden commit na `main` z testami, bez gałęzi i pull requestów (decyzja właściciela z 17.11.2026). Agent dostaje konkretny rozdział tej dokumentacji jako specyfikację.
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
