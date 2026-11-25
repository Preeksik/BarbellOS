# Dane startowe

Wgrywa je `python -m app.tools.seed` (w katalogu `backend/`). Polecenie można uruchamiać wielokrotnie.

| Plik | Zawartość | W repo |
|---|---|---|
| `nutrients.json` | Słownik 20 mikroskładników z jednostkami i wartościami odniesienia | tak |
| `plan_amp_2027.json` | Plan treningowy: 29 tygodni, 139 sesji, 601 pozycji, maksy treningowe, cele | **nie** (wpisany w `.gitignore`) |
| `generic_foods.json` | Produkty podstawowe z mikroskładnikami z USDA FoodData Central | powstanie w etapie 6 |

## nutrients.json

Kolumna `rda` to referencyjne wartości spożycia dla dorosłych z rozporządzenia UE 1169/2011 (załącznik XIII), czyli te same, do których odnoszą się procenty na etykietach. Nie są indywidualnym zapotrzebowaniem sportowca. Sód nie ma takiej wartości: 2400 mg odpowiada 6 g soli i jest górną granicą, a nie celem.

Identyfikatory muszą zgadzać się z mapowaniem pól Open Food Facts w `backend/app/off/client.py`. Pilnuje tego test.

## plan_amp_2027.json

Plik zawiera osobiste maksy i cele, dlatego domyślnie nie trafia do publicznego repo. Bez niego aplikacja działa, a polecenie `seed` plan pomija. Żeby go opublikować, usuń odpowiednią linię z `.gitignore`.

Opis pól jest w samym pliku, w sekcji `field_guide`.

Od 25.11.2026 plik odpowiada żywej wersji planu z artefaktu (zmiany do 22.11.2026). Nowe pole ćwiczenia `fixed_kg` to stały ciężar z planu, który ma pierwszeństwo przed procentem TM (tygodnie sprzed zmiany maksów). Na serwer plan trafia przez „Wczytaj plan z pliku” w zakładce Trening, bo plik nie jest w repo.
