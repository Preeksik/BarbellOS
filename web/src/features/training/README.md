# Trening (etap 4)

Ekran przeniesiony z `Plan_AMP_2027.html` (żywa wersja z artefaktu): oś sezonu, tydzień, dni, sesja z wpisami i podejściami (`TrainingPage.tsx`). Wszystkie liczby (daty, ciężary, talerze, e1RM, statusy, „ostatnio”, sugestie TM) liczy serwer: `backend/app/core/season.py` i `backend/app/core/training.py`. Formatowanie tekstu i zebranie wpisu z pól: `src/lib/training.ts`.

Zapisy idą przez kolejkę offline (`trainingEntry`, `trainingSession` w `src/lib/offline.ts`, jedna kolejka `training`) do idempotentnych `PUT` z kluczem sesji i indeksem ćwiczenia.

Dalej (część 2): zakładki sezonu, maksów i startu, arkusz podejść, data zawodów.
