# 0001: PWA + FastAPI + Skróty zamiast aplikacji natywnej

Data: 2026-11-12. Stan: przyjęte, do potwierdzenia wynikami etapu 0.

## Kontekst

- Aplikacja dla jednego użytkownika na iPhone'a. Wymaga aparatu (kody kreskowe, zdjęcia) i danych z Apple Health.
- Praca na Windows 11 w VS Code; kod piszą agenci, właściciel przegląda Pythona.
- Brak płatnego konta Apple Developer. W domu jest Mac, ale nie jest to komputer do codziennej pracy.

## Decyzja

Frontend jako PWA (React + TypeScript + Vite) instalowana na ekranie początkowym. Backend FastAPI + Postgres, w którym jest cała logika. Dane z Apple Health dosyła automatyzacja w aplikacji Skróty. Jeden proces serwuje API i zbudowany frontend.

## Dlaczego

- Agent może sam uruchomić i przetestować aplikację webową w przeglądarce. Buildu iOS nie uruchomi.
- Logika w Pythonie jest kodem, który właściciel potrafi sprawdzić.
- Wdrożenie zmiany to `git push`, bez certyfikatów i ponownej instalacji.
- Koszt stały 0 zł na start.

## Koszty tej decyzji

- Apple Health tylko przez Skróty: działa wyłącznie przy odblokowanym telefonie, wymaga jednorazowej ręcznej konfiguracji.
- Kody kreskowe wymagają biblioteki WebAssembly, bo Safari nie ma Barcode Detection API.
- Brak pracy w tle i brak gwarancji trwałości pamięci na telefonie, stąd serwer jako źródło prawdy i trwała kolejka zapisów.
- Darmowy hosting usypia usługę; potrzebne podtrzymanie.

## Kiedy wracamy do tej decyzji

Gdy próba A, B lub D z `docs/etap-0.md` zawiedzie. Wtedy backend zostaje bez zmian, a frontend dostaje natywną powłokę z HealthKit budowaną na Macu (darmowe konto Apple: ponowna instalacja co 7 dni; płatne: 99 USD rocznie).

## Odrzucone

- **Swift + SwiftUI:** wymaga Maca do codziennej pracy i kodu, którego właściciel nie zna.
- **Expo (React Native) z EAS Build:** wymaga płatnego konta Apple, a agent nie przetestuje buildu.
