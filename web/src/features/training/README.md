# Trening (etap 4)

Tu trafią ekrany przeniesione z `Plan_AMP_2027.html`: sesja dnia, logowanie serii, arkusz podejść, ekran celu. Obliczenia są już w `backend/app/core/training.py` i zgadzają się z oryginałem (test `backend/tests/test_training.py`).

Zapis serii musi korzystać z kolejki offline: `mutationKey` i funkcja w `src/lib/offline.ts`, endpoint `PUT` z kluczem (plan, sesja, indeks ćwiczenia).
