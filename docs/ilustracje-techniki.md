# Ilustracje techniki: polecenia do czatu Gemini

Ilustracje do przycisku „Technika” przy ćwiczeniach generujesz sam w czacie [gemini.google.com](https://gemini.google.com) (subskrypcja Google AI Pro, model obrazkowy Nano Banana Pro). Agent potem je przycina, zmniejsza i wpina w aplikację. Plan ćwiczeń: stan z 27.11.2026, 26 ćwiczeń.

## Jak to działa w aplikacji

Każde ćwiczenie ma 2 klatki: pozycję startową i końcową. Aplikacja przełącza je płynnie jak w dawnych aplikacjach treningowych, z czasem zależnym od wariantu. Warianty, które różnią się tylko czasem, dostają te same klatki co bój podstawowy, a aplikacja pokazuje na dolnej klatce odliczanie i podpis:

| Ćwiczenie | Klatki | Co dokłada aplikacja |
|---|---|---|
| Przysiad z pauzą 2 s | z przysiadu | odliczanie „2 s” w dolnej pozycji |
| Przysiad tempo 3-1-0 | z przysiadu | 3 s w dół, „1 s” na dole, szybko w górę |
| Wyciskanie leżąc T&G | z ławy | „dotyk i od razu w górę”, bez pauzy |
| Wyciskanie z pauzą 3 s | z ławy | odliczanie „3 s” na klatce |

Pozostałe warianty (piny, Larsen, wąski chwyt, spoto, RDL) wyglądają inaczej, więc mają własne klatki.

## Wymagania techniczne

1. **Jedna rozmowa na wszystko.** Zacznij od postaci wzorcowej, potem klatki po kolei. Gdy rozmowa zacznie się sypać albo trafisz na limit, zacznij nową i dołącz `00-postac.png` jako załącznik (polecenie „ciąg dalszy” na końcu pliku).
2. **Kwadrat 1:1**, co najmniej 1024 × 1024 px. Pobieraj w pełnej rozdzielczości (przycisk pobierania, nie zrzut ekranu).
3. **Białe tło**, cała postać i cały sprzęt w kadrze, z marginesem. Nic nie może być ucięte przy krawędzi.
4. **Obie klatki ćwiczenia z tej samej kamery:** ten sam kąt, odległość i miejsce sprzętu. Zmienia się tylko pozycja ciała. Dlatego druga klatka zawsze odnosi się do poprzedniego obrazka.
5. **Bez napisów, liczb i logo**, także na talerzach. Znaczek Gemini w rogu nie przeszkadza, agent go przytnie.
6. **Nazwy plików dokładnie jak w liście** (małe litery, myślniki), wszystkie do folderu `exports/technika/`. Ten folder nie trafia do repo.
7. **Sprawdź każdą klatkę, zanim pójdziesz dalej**, i wygeneruj ją ponownie (polecenie „poprawka” na końcu pliku), gdy:
   - postać albo styl wyraźnie różnią się od wzorca;
   - anatomia się nie zgadza (dodatkowe palce, ręka przez sztangę, dziwne stawy);
   - technika jest błędna (płytki przysiad, pośladki nad ławką, okrągłe plecy w martwym);
   - pojawił się tekst albo liczba.

Razem 44 obrazki: postać wzorcowa i 43 klatki.

## Krok 0: postać wzorcowa

Plik: `00-postac.png`

```
Create a reference image for a series of exercise technique illustrations for a strength training app.

Style: semi-realistic 3D anatomical illustration, like a medical anatomy model. A fit adult man with realistic, clearly defined muscles rendered in light neutral grey (visible muscle shapes and fibres, no skin texture, no tattoos), short dark hair, calm neutral face. He wears plain black athletic shorts and plain black flat training shoes. Pure white background, soft even studio lighting, a soft shadow under the feet. Working muscles will later be highlighted in one saturated blue (#2F6FD6); in this image no muscles are highlighted.

Pose: standing upright, relaxed athletic stance, full body visible, three-quarter front view.

Rules for this whole series: square 1:1 image, the whole figure and all equipment fully in frame with margin, no text, no letters, no numbers, no logos, no labels anywhere (also none on weight plates). Equipment style for later images: matte black weight plates without markings, steel barbell, light grey squat rack and bench.
```

Gdy postać Ci pasuje, w tej samej rozmowie wyślij:

```
This is the reference character and style. Keep exactly this man, this rendering style, the white background and the lighting in every next image. Confirm, and wait for the next instruction.
```

## Krok 1: boje zawodnicze i warianty

Każde ćwiczenie to dwa polecenia: najpierw pozycja startowa, potem końcowa.

### 1. Przysiad

`przysiad-1-gora.png`

```
Using exactly the same man, style, lighting and white background as the reference: competition back squat, TOP position. He stands fully upright inside a light grey squat rack with a loaded barbell resting on his upper back (on the traps, below the neck), hands gripping the bar just outside the shoulders, elbows pointing down and back, feet shoulder-width, toes slightly out, chest up, neutral head. Black plates on both sides of the bar. Camera: three-quarter side view from the front-left at hip height, so the knee and hip angles are clearly visible. Highlight in blue: quadriceps, glutes, adductors, lower back erectors. Square 1:1, everything in frame, no text.
```

`przysiad-2-dol.png`

```
Same scene, same camera angle, same rack and barbell as the previous image. Change only the pose: BOTTOM of the competition squat. Hips clearly below parallel: the hip crease is lower than the top of the knee. Knees forward in line with the toes, heels flat on the floor, the bar stays directly over the middle of the foot, back flat and tight, chest up. Same blue highlights. Square 1:1, no text.
```

### 2. Wyciskanie leżąc z pauzą (zawodnicze)

`lawa-1-gora.png`

```
Using exactly the same man, style, lighting and white background as the reference: competition bench press, TOP position. He lies on a flat light grey bench under a rack, arms straight with the loaded barbell locked out above the shoulders, hands slightly wider than shoulder width, shoulder blades pulled together, a moderate arch in the upper back, buttocks on the bench, both feet flat on the floor. Camera: three-quarter view from slightly above, from the side of his feet, so the bar path, the arch and the feet are visible. Highlight in blue: chest (pectorals), front shoulders, triceps. Square 1:1, everything in frame, no text.
```

`lawa-2-klatka.png`

```
Same scene, same camera angle as the previous image. Change only the pose: the bar is lowered and resting motionless on the lower part of his chest (paused, as in competition). Forearms vertical, elbows under the bar about 45 degrees from the torso, buttocks still on the bench, feet flat on the floor. Same blue highlights. Square 1:1, no text.
```

### 3. Martwy ciąg

`martwy-1-start.png`

```
Using exactly the same man, style, lighting and white background as the reference: conventional deadlift, START position. The loaded barbell rests on the floor over the middle of his feet, shins touching the bar, hands gripping the bar just outside the legs with straight arms, hips higher than the knees, shoulders slightly in front of the bar, back flat and neutral, eyes looking slightly ahead on the floor. No rack. Camera: pure side view from his left at hip height. Highlight in blue: glutes, hamstrings, lower back erectors, quadriceps, upper back (traps). Square 1:1, everything in frame, no text.
```

`martwy-2-wyprost.png`

```
Same scene, same camera angle as the previous image. Change only the pose: LOCKOUT of the deadlift. He stands fully upright with hips and knees fully extended, shoulders back, the barbell hanging in straight arms at the top of the thighs, no leaning back. Same blue highlights. Square 1:1, no text.
```

### 4. Przysiad z pinów

`piny-1-gora.png`

```
Using exactly the same man, style, lighting and white background as the reference, and the same camera angle as the squat images: back squat from safety pins, TOP position. He stands upright inside the light grey squat rack with the loaded barbell on his upper back. The rack's two horizontal safety pins are set clearly visible at low height, at the level of the bar in a below-parallel squat. Highlight in blue: quadriceps, glutes, adductors, lower back erectors. Square 1:1, no text.
```

`piny-2-dol.png`

```
Same scene, same camera angle as the previous image. Change only the pose: the bottom of the squat with the barbell resting completely still on the safety pins, hips below parallel, back flat, body tight, ready to stand up from a dead stop. Same blue highlights. Square 1:1, no text.
```

### 5. Larsen press

`larsen-1-gora.png`

```
Using exactly the same man, style, lighting and white background as the reference, and the same camera angle as the bench press images: Larsen press, TOP position. Bench press on a flat bench with arms straight and the bar locked out over the shoulders, but his legs are straight and lifted off the floor, extended forward in the air at about the height of the bench, feet not touching anything. Buttocks on the bench. Highlight in blue: chest, front shoulders, triceps, abdominals. Square 1:1, no text.
```

`larsen-2-klatka.png`

```
Same scene, same camera angle as the previous image. Change only the arms: the bar is paused motionless on the lower chest, forearms vertical. Legs stay straight in the air off the floor. Same blue highlights. Square 1:1, no text.
```

### 6. Wyciskanie wąskim chwytem

`waski-1-gora.png`

```
Using exactly the same man, style, lighting and white background as the reference: close-grip bench press, TOP position. Flat bench, bar locked out over the shoulders, hands at shoulder width (clearly narrower than a normal bench grip), elbows close to the body, feet flat on the floor. Camera: three-quarter view from slightly above and from the side of his head, so the narrow grip on the bar is clearly visible. Highlight in blue: triceps, chest, front shoulders. Square 1:1, no text.
```

`waski-2-klatka.png`

```
Same scene, same camera angle as the previous image. Change only the arms: the bar is paused motionless on the lower chest, elbows tucked close to the torso, forearms vertical. Same blue highlights. Square 1:1, no text.
```

### 7. Spoto press (tylko klatka dolna; górną aplikacja bierze z ławy)

`spoto-2-nad-klatka.png`

```
Use the bench press top-position image as the base: same man, same bench, same camera angle. New pose: Spoto press. The bar is held motionless about 2 cm ABOVE his chest, clearly NOT touching it, with a small visible gap between the bar and the chest. Forearms vertical, body tight, buttocks on the bench, feet flat. Same blue highlights (chest, front shoulders, triceps). Square 1:1, no text.
```

### 8. Rumuński martwy ciąg (RDL)

`rdl-1-gora.png`

```
Using exactly the same man, style, lighting and white background as the reference, and the same camera angle as the deadlift images (pure side view from his left): Romanian deadlift, TOP position. He stands upright holding the loaded barbell in straight arms at the top of the thighs, knees slightly unlocked. Highlight in blue: hamstrings, glutes, lower back erectors. Square 1:1, no text.
```

`rdl-2-dol.png`

```
Same scene, same camera angle as the previous image. Change only the pose: bottom of the Romanian deadlift. Hips pushed far back, knees slightly bent and in the same position as before, back flat and neutral, the bar slides down along the legs to just below the knees (mid-shin), plates NOT touching the floor, strong stretch in the hamstrings. Same blue highlights. Square 1:1, no text.
```

## Krok 2: ćwiczenia pomocnicze

### 9. Suwnica (leg press 45°)

`suwnica-1-gora.png`

```
Using exactly the same man, style, lighting and white background as the reference: 45-degree leg press machine (light grey machine, black plates), TOP position. He sits with his back flat on the pad, feet shoulder-width on the platform, legs almost straight (knees not locked). Camera: side view from his left. Highlight in blue: quadriceps, glutes. Square 1:1, no text.
```

`suwnica-2-dol.png`

```
Same scene, same camera angle as the previous image. Change only the pose: bottom of the leg press, knees deeply bent towards the chest, lower back still flat on the pad, heels on the platform. Same blue highlights. Square 1:1, no text.
```

### 10. Uginanie nóg leżąc

`uginanie-nog-1-start.png`

```
Using exactly the same man, style, lighting and white background as the reference: lying leg curl machine (light grey). He lies face down, the roller pad behind his lower calves just above the heels, legs straight, hips pressed into the pad, hands on the handles. Camera: side view. Highlight in blue: hamstrings, calves. Square 1:1, no text.
```

`uginanie-nog-2-skurcz.png`

```
Same scene, same camera angle as the previous image. Change only the legs: knees bent to about 90 degrees or more, heels pulled towards the glutes, hips still pressed into the pad. Same blue highlights. Square 1:1, no text.
```

### 11. Hiperekstensje

`hiperekstensje-1-dol.png`

```
Using exactly the same man, style, lighting and white background as the reference: 45-degree back extension bench (Roman chair). Hips on the pad, ankles hooked under the foot rollers, a black weight plate held against his chest, torso bent down at the hips with a neutral back. Camera: side view. Highlight in blue: glutes, hamstrings, lower back erectors. Square 1:1, no text.
```

`hiperekstensje-2-gora.png`

```
Same scene, same camera angle as the previous image. Change only the pose: torso raised until the body forms one straight line from heels to head, no overextension of the lower back, the plate still against the chest. Same blue highlights. Square 1:1, no text.
```

### 12. Wiosłowanie hantlem w podporze

`wioslowanie-1-dol.png`

```
Using exactly the same man, style, lighting and white background as the reference: chest-supported dumbbell row. He lies chest down on an incline bench set to about 30 degrees, feet on the floor, holding one black dumbbell in each hand with arms hanging straight down. Camera: three-quarter side view. Highlight in blue: lats, middle and upper back (rhomboids, traps), rear shoulders, biceps. Square 1:1, no text.
```

`wioslowanie-2-gora.png`

```
Same scene, same camera angle as the previous image. Change only the arms: dumbbells pulled up towards the hips, elbows driven back past the torso, shoulder blades squeezed together, chest still on the bench. Same blue highlights. Square 1:1, no text.
```

### 13. Podciąganie nachwytem z obciążeniem

`podciaganie-1-zwis.png`

```
Using exactly the same man, style, lighting and white background as the reference: weighted pull-up. He hangs from a pull-up bar with an overhand grip slightly wider than the shoulders, arms fully straight, a black dumbbell held between his feet for extra weight, legs slightly bent. Camera: three-quarter view from behind-left so the back is visible. Highlight in blue: lats, biceps, middle back. Square 1:1, no text.
```

`podciaganie-2-gora.png`

```
Same scene, same camera angle as the previous image. Change only the pose: chin above the bar, chest close to the bar, elbows pulled down to the sides, the dumbbell still held between the feet. Same blue highlights. Square 1:1, no text.
```

### 14. Face pull

`facepull-1-start.png`

```
Using exactly the same man, style, lighting and white background as the reference: face pull on a cable machine. He stands facing a light grey cable tower, the pulley set at face height, holding a rope attachment with both hands, arms straight in front of him. Camera: side view from his left. Highlight in blue: rear shoulders, upper back (rhomboids, middle traps), rotator cuff. Square 1:1, no text.
```

`facepull-2-koniec.png`

```
Same scene, same camera angle as the previous image. Change only the arms: the rope pulled towards his face, hands next to the ears, elbows high and wide, upper arms rotated outward. Same blue highlights. Square 1:1, no text.
```

### 15. Odwrotne rozpiętki

`odwrotne-rozpietki-1-dol.png`

```
Using exactly the same man, style, lighting and white background as the reference: bent-over reverse dumbbell fly. He stands bent forward at the hips with a flat back, torso almost parallel to the floor, knees slightly bent, light black dumbbells hanging below the chest, palms facing each other, elbows slightly bent. Camera: three-quarter front view. Highlight in blue: rear shoulders, rhomboids, middle traps. Square 1:1, no text.
```

`odwrotne-rozpietki-2-gora.png`

```
Same scene, same camera angle as the previous image. Change only the arms: dumbbells raised out to the sides up to shoulder height in a wide arc, shoulder blades squeezed, torso still bent forward. Same blue highlights. Square 1:1, no text.
```

### 16. Wyciskanie hantli na skosie

`skos-hantle-1-dol.png`

```
Using exactly the same man, style, lighting and white background as the reference: incline dumbbell press on a bench set to about 30 degrees. Bottom position: black dumbbells beside the upper chest, elbows below the bench line at about 45 degrees from the torso, feet flat on the floor. Camera: three-quarter view from the side of his feet. Highlight in blue: upper chest, front shoulders, triceps. Square 1:1, no text.
```

`skos-hantle-2-gora.png`

```
Same scene, same camera angle as the previous image. Change only the arms: dumbbells pressed up over the upper chest with arms straight, dumbbells close together but not touching. Same blue highlights. Square 1:1, no text.
```

### 17. Prostowanie ramion na wyciągu jednorącz (triceps)

`triceps-1-start.png`

```
Using exactly the same man, style, lighting and white background as the reference: single-arm cable triceps pushdown. He stands facing a light grey cable tower with a high pulley, holding a single handle in his LEFT hand, upper arm tight against his side, elbow bent about 90 degrees, forearm roughly parallel to the floor. Other hand relaxed. Camera: side view from his left. Highlight in blue: triceps of the working arm. Square 1:1, no text.
```

`triceps-2-wyprost.png`

```
Same scene, same camera angle as the previous image. Change only the working arm: elbow fully straight, handle pushed down next to the thigh, upper arm still tight against the side. Same blue highlights. Square 1:1, no text.
```

### 18. Uginanie ramion z hantlami (biceps)

`biceps-1-dol.png`

```
Using exactly the same man, style, lighting and white background as the reference: standing dumbbell biceps curl. He stands upright with a black dumbbell in each hand, arms straight at the sides, palms facing forward. Camera: three-quarter front view. Highlight in blue: biceps, forearm flexors. Square 1:1, no text.
```

`biceps-2-gora.png`

```
Same scene, same camera angle as the previous image. Change only the arms: both dumbbells curled up to shoulder height, elbows still close to the sides, no swinging of the torso. Same blue highlights. Square 1:1, no text.
```

### 19. Rollout

`rollout-1-start.png`

```
Using exactly the same man, style, lighting and white background as the reference: ab wheel rollout from the knees. He kneels on the floor holding an ab wheel under his shoulders, arms straight, back flat, abs tight. Camera: side view from his left. Highlight in blue: abdominals (rectus abdominis, obliques). Square 1:1, no text.
```

`rollout-2-wyciagniety.png`

```
Same scene, same camera angle as the previous image. Change only the pose: rolled out forward until the body is almost straight and low over the floor, arms extended overhead in front, hips NOT sagging, body in one straight line from knees to shoulders. Same blue highlights. Square 1:1, no text.
```

### 20. Unoszenie nóg w zwisie

`unoszenie-nog-1-zwis.png`

```
Using exactly the same man, style, lighting and white background as the reference: hanging leg raise. He hangs from a pull-up bar with straight arms and an overhand grip, legs straight down, body still, not swinging. Camera: side view from his left. Highlight in blue: abdominals, hip flexors. Square 1:1, no text.
```

`unoszenie-nog-2-gora.png`

```
Same scene, same camera angle as the previous image. Change only the legs: knees raised up towards the chest with the pelvis tilted up, body not swinging. Same blue highlights. Square 1:1, no text.
```

### 21. Marsz pod górę na bieżni

`bieznia-1-krok.png`

```
Using exactly the same man, style, lighting and white background as the reference: incline treadmill walk. He walks on a light grey treadmill set to a clearly visible incline (about 10 percent), upright posture, NOT holding the handrails, natural arm swing, left leg forward. He wears the same black shoes. Camera: side view from his left. Highlight in blue: glutes, hamstrings, calves, quadriceps. Square 1:1, no text.
```

`bieznia-2-krok.png`

```
Same scene, same camera angle as the previous image. Change only the stride: the opposite step, right leg forward, arms swinging the other way. Same blue highlights. Square 1:1, no text.
```

### 22. Mobilność bioder i odcinka piersiowego

Dwa osobne ćwiczenia zamiast ruchu; aplikacja pokaże je obok siebie.

`mobilnosc-1-biodra.png`

```
Using exactly the same man, style, lighting and white background as the reference: 90/90 hip mobility stretch. He sits on the floor with the front leg bent 90 degrees in front of him and the back leg bent 90 degrees to the side behind him, torso upright and leaning slightly forward over the front shin, hands lightly on the floor. Camera: three-quarter front view. Highlight in blue: glutes, hip rotators. Square 1:1, no text.
```

`mobilnosc-2-piersiowy.png`

```
Using exactly the same man, style, lighting and white background as the reference: thoracic spine "open book" rotation. He lies on his left side on the floor, knees bent 90 degrees and stacked, arms straight in front; the top (right) arm rotates open to the other side, chest turning towards the ceiling, eyes following the hand, knees staying together on the floor. Camera: three-quarter view from above. Highlight in blue: upper back, chest. Square 1:1, no text.
```

## Polecenia pomocnicze

**Poprawka** (gdy klatka wyszła źle):

```
Regenerate the previous image. Keep the same man, style, camera angle and equipment. Fix: <opisz po angielsku, np. "the hips must be clearly below the knees", "the buttocks must stay on the bench", "remove all text and numbers", "the bar must not touch the chest">.
```

**Ciąg dalszy w nowej rozmowie** (dołącz `00-postac.png`):

```
The attached image is the reference character and style for a series of exercise technique illustrations: same man, same semi-realistic 3D anatomical style with grey muscles, black shorts and black shoes, white background, soft studio light, working muscles highlighted in saturated blue (#2F6FD6), square 1:1, no text, no numbers, no logos. Keep all of this exactly in every image I ask for next. Confirm and wait.
```

## Gdy skończysz

Napisz agentowi, że pliki są w `exports/technika/`. Agent:

1. Sprawdzi, czy są wszystkie 44 pliki z dobrymi nazwami.
2. Przytnie znaczek Gemini i zmniejszy klatki do formatu WebP (ok. 50–80 kB na klatkę).
3. Obejrzy klatki i wskaże te do poprawy.
4. Wepnie je w aplikację w miejsce obecnego ludzika, z odliczaniem pauz w wariantach.
