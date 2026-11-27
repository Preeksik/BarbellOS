# Ilustracje techniki: prompty do czatu Gemini

Ilustracje do przycisku „Technika” przy ćwiczeniach generujesz sam w zwykłym czacie [gemini.google.com](https://gemini.google.com) (Google AI Pro). Każde ćwiczenie to **jeden obrazek z dwoma panelami obok siebie**: lewy to start ruchu, prawy to koniec. Agent tnie go na 2 wyrównane klatki (`scripts/technique_frames.py`), a aplikacja przełącza je w pętli, z odliczaniem pauzy w wariantach.

Stan: 27.11.2026. Gotowe: przysiad (z niego też przysiad z pauzą 2 s i tempo 3-1-0). Zostało 21 obrazków.

## Ustawienia czatu

- Model **Neon**, effort **średni**. Hydrogen gorzej trzyma się opisu, a Carbon jest tylko w planie Ultra.
- Przed wysłaniem włącz **Utwórz obraz** (pole wpisywania → ikona obrazka). Bez tego Gemini odpowiada „Jako model językowy nie jestem do tego przeznaczony”.
- **Format obrazu:** kwadrat. **Format:** domyślny, bez stylu i bez GIF-a.

## Jak generować

1. **Każde ćwiczenie w nowej rozmowie.** W jednej rozmowie Gemini przenosi kadr z poprzedniego ćwiczenia.
2. Załącz spinaczem `exports\technika\00-postac.png` (postać wzorcowa).
3. Wklej prompt ćwiczenia (cały blok) i wyślij.
4. Sprawdź obrazek (lista niżej). Gdy coś nie gra, wyślij **jedną** poprawkę zaczynającą się od `popraw:`. Gdy poprawka nic nie zmienia (Gemini trzyma się poprzedniego kadru), wygeneruj od nowa w nowej rozmowie.
5. Pobierz i zapisz pod nazwą z nagłówka, np. `lawa.png`, w `C:\Users\adria\Desktop\BarbellOS\exports\technika\`.

**Sprawdź przed zapisem:**

- **Kamera** jak w opisie (najczęstszy błąd: Gemini obraca postać przodem).
- **Oba panele mają ten sam sprzęt, skalę i miejsce na podłodze.** Zmienia się tylko ciało.
- **Technika:**
  - przysiad i warianty: biodro poniżej kolana;
  - ława: pośladki na ławce, stopy na podłodze;
  - martwy: plecy proste;
  - dłonie widoczne na gryfie albo hantlu.
- **Niebieskie tylko mięśnie z opisu.** Gemini lubi dokładać brzuch i łydki.
- **Bez napisów i liczb,** także na talerzach.

Drobiazgi (zacisk na talerzu, odcień niebieskiego) można przepuścić, bo każda poprawka ryzykuje zmianę kąta.

## Prompty

Każdy blok jest samodzielny: kopiujesz cały blok do nowej rozmowy z załączoną postacią.

### `lawa.png`: wyciskanie leżąc z pauzą (zawodnicze)

Z tych klatek korzystają też ława T&G (dół tylko na mgnienie) i ława z pauzą 3 s (odliczanie na klatce).

```
Create a NEW image with TWO PANELS SIDE BY SIDE (left half and right half), using the attached man as the reference character: same face, hair, anatomical écorché muscle style with grey muscles, black shorts, black shoes, pure white background, soft studio light. Both panels: exactly the same scene, camera angle, distance and scale; only his pose differs. No text, no numbers, no logos anywhere (also none on plates).

Scene: competition bench press on a flat light grey bench under a light grey rack, barbell with two identical matte black plates (no clips, no markings). Camera: from the side, at bench height, slightly from above and from the side of his feet, so we see the bar path, his arched upper back, buttocks on the bench and both feet flat on the floor. Both hands clearly visible gripping the bar slightly wider than shoulder width.

LEFT panel: TOP position, arms straight, bar locked out directly above the shoulders.
RIGHT panel: bar paused motionless ON the lower chest (touching the sternum), forearms vertical, elbows about 45 degrees from the torso, buttocks still on the bench, feet flat.

Blue (#2F6FD6) ONLY on pectorals, front shoulders and triceps; everything else grey.
```

### `martwy.png`: martwy ciąg

```
Create a NEW image with TWO PANELS SIDE BY SIDE (left half and right half), using the attached man as the reference character: same face, hair, anatomical écorché muscle style with grey muscles, black shorts, black shoes, pure white background, soft studio light. Both panels: exactly the same scene, camera angle, distance and scale; only his pose differs. No text, no numbers, no logos anywhere (also none on plates).

Scene: conventional deadlift, no rack, barbell with two identical matte black plates (no clips, no markings). Camera: true SIDE PROFILE from his left at hip height (we see his face from the side and the full line of his back). Both hands clearly visible gripping the bar just outside the legs.

LEFT panel: START: bar on the floor over the middle of the foot, shins touching the bar, straight arms, hips higher than the knees, shoulders slightly in front of the bar, back FLAT and neutral.
RIGHT panel: LOCKOUT: standing fully upright, hips and knees fully extended, shoulders back, bar hanging in straight arms at the top of the thighs, no leaning back.

Blue (#2F6FD6) ONLY on glutes, hamstrings, lower back erectors and upper trapezius; everything else grey.
```

### `piny.png`: przysiad z pinów

```
Create a NEW image with TWO PANELS SIDE BY SIDE (left half and right half), using the attached man as the reference character: same face, hair, anatomical écorché muscle style with grey muscles, black shorts, black shoes, pure white background, soft studio light. Both panels: exactly the same scene, camera angle, distance and scale; only his pose differs. No text, no numbers, no logos anywhere (also none on plates).

Scene: back squat from safety pins inside a light grey power rack. The rack's two horizontal safety pins are clearly visible, set LOW, at the height the bar reaches in a deep squat. Barbell with two identical matte black plates (no clips, no markings) on his upper back behind the neck. Camera: true SIDE PROFILE from his left at hip height. His hand is clearly visible gripping the bar, elbow pointing down and back.

LEFT panel: TOP, standing fully upright with the bar on his back.
RIGHT panel: BOTTOM: the bar resting completely still ON the safety pins; thighs slope DOWNWARD from the knee to the hip, hip crease clearly LOWER than the top of the knee, back flat, body tight.

Blue (#2F6FD6) ONLY on quadriceps, glutes and lower back erectors; everything else grey.
```

### `larsen.png`: Larsen press

```
Create a NEW image with TWO PANELS SIDE BY SIDE (left half and right half), using the attached man as the reference character: same face, hair, anatomical écorché muscle style with grey muscles, black shorts, black shoes, pure white background, soft studio light. Both panels: exactly the same scene, camera angle, distance and scale; only his arms differ. No text, no numbers, no logos anywhere (also none on plates).

Scene: Larsen press on a flat light grey bench under a light grey rack, barbell with two identical matte black plates (no clips, no markings). His legs are STRAIGHT and LIFTED OFF THE FLOOR, extended forward in the air at about bench height, feet touching nothing, buttocks on the bench. Camera: from the side at bench height, slightly from above, so the straight raised legs are clearly visible. Both hands clearly visible on the bar.

LEFT panel: arms straight, bar locked out above the shoulders.
RIGHT panel: bar paused motionless on the lower chest, forearms vertical; legs still straight in the air.

Blue (#2F6FD6) ONLY on pectorals, front shoulders, triceps and abdominals; everything else grey.
```

### `waski.png`: wyciskanie wąskim chwytem

```
Create a NEW image with TWO PANELS SIDE BY SIDE (left half and right half), using the attached man as the reference character: same face, hair, anatomical écorché muscle style with grey muscles, black shorts, black shoes, pure white background, soft studio light. Both panels: exactly the same scene, camera angle, distance and scale; only his arms differ. No text, no numbers, no logos anywhere (also none on plates).

Scene: close-grip bench press on a flat light grey bench under a light grey rack, barbell with two identical matte black plates (no clips, no markings), feet flat on the floor. Camera: three-quarter view from slightly above and from the side of his head, so the NARROW grip is clearly visible: hands at shoulder width, clearly narrower than a normal bench press grip.

LEFT panel: arms straight, bar locked out above the shoulders.
RIGHT panel: bar paused motionless on the lower chest, elbows tucked close to the torso, forearms vertical.

Blue (#2F6FD6) ONLY on triceps, pectorals and front shoulders; everything else grey.
```

### `spoto.png`: spoto press

```
Create a NEW image with TWO PANELS SIDE BY SIDE (left half and right half), using the attached man as the reference character: same face, hair, anatomical écorché muscle style with grey muscles, black shorts, black shoes, pure white background, soft studio light. Both panels: exactly the same scene, camera angle, distance and scale; only his arms differ. No text, no numbers, no logos anywhere (also none on plates).

Scene: Spoto press on a flat light grey bench under a light grey rack, barbell with two identical matte black plates (no clips, no markings), buttocks on the bench, feet flat. Camera: from the side at bench height, slightly from above, so the space between the bar and the chest is clearly visible. Both hands clearly visible on the bar.

LEFT panel: arms straight, bar locked out above the shoulders.
RIGHT panel: the bar held motionless about 2 cm ABOVE the chest, clearly NOT touching it: a small visible gap of white background between the bar and the chest. Forearms vertical, body tight.

Blue (#2F6FD6) ONLY on pectorals, front shoulders and triceps; everything else grey.
```

### `rdl.png`: rumuński martwy ciąg

```
Create a NEW image with TWO PANELS SIDE BY SIDE (left half and right half), using the attached man as the reference character: same face, hair, anatomical écorché muscle style with grey muscles, black shorts, black shoes, pure white background, soft studio light. Both panels: exactly the same scene, camera angle, distance and scale; only his pose differs. No text, no numbers, no logos anywhere (also none on plates).

Scene: Romanian deadlift, no rack, barbell with two identical matte black plates (no clips, no markings). Camera: true SIDE PROFILE from his left at hip height. Both hands clearly visible on the bar.

LEFT panel: standing upright, bar in straight arms at the top of the thighs, knees slightly unlocked.
RIGHT panel: hips pushed far BACK, knees slightly bent (same as in the left panel), back FLAT, bar slid along the legs to mid-shin, plates NOT touching the floor.

Blue (#2F6FD6) ONLY on hamstrings, glutes and lower back erectors; everything else grey.
```

### `suwnica.png`: suwnica (leg press 45°)

```
Create a NEW image with TWO PANELS SIDE BY SIDE (left half and right half), using the attached man as the reference character: same face, hair, anatomical écorché muscle style with grey muscles, black shorts, black shoes, pure white background, soft studio light. Both panels: exactly the same scene, camera angle, distance and scale; only his legs differ. No text, no numbers, no logos anywhere (also none on the machine or plates).

Scene: 45-degree leg press machine (light grey frame, matte black plates). He sits with his back flat on the backrest, feet shoulder-width on the platform. Camera: true SIDE view from his left.

LEFT panel: legs almost straight, knees NOT locked.
RIGHT panel: knees deeply bent towards the chest, lower back still flat on the backrest, heels on the platform.

Blue (#2F6FD6) ONLY on quadriceps and glutes; everything else grey.
```

### `uginanie-nog.png`: uginanie nóg leżąc

```
Create a NEW image with TWO PANELS SIDE BY SIDE (left half and right half), using the attached man as the reference character: same face, hair, anatomical écorché muscle style with grey muscles, black shorts, black shoes, pure white background, soft studio light. Both panels: exactly the same scene, camera angle, distance and scale; only his legs differ. No text, no numbers, no logos anywhere.

Scene: lying leg curl machine (light grey). He lies face down, hips pressed into the pad, hands on the handles, the roller pad behind the lower calves just above the heels. Camera: true SIDE view from his left.

LEFT panel: legs straight.
RIGHT panel: knees bent 90 degrees or more, heels pulled towards the glutes, hips still on the pad.

Blue (#2F6FD6) ONLY on hamstrings and calves; everything else grey.
```

### `hiperekstensje.png`: hiperekstensje

```
Create a NEW image with TWO PANELS SIDE BY SIDE (left half and right half), using the attached man as the reference character: same face, hair, anatomical écorché muscle style with grey muscles, black shorts, black shoes, pure white background, soft studio light. Both panels: exactly the same scene, camera angle, distance and scale; only his torso differs. No text, no numbers, no logos anywhere (also none on the plate).

Scene: 45-degree back extension bench (Roman chair, light grey). Hips on the pad, ankles under the foot rollers, a matte black weight plate held against his chest with both arms. Camera: true SIDE view from his left.

LEFT panel: torso bent down at the hips, back neutral.
RIGHT panel: torso raised until the body is one straight line from heels to head, no overextension of the lower back.

Blue (#2F6FD6) ONLY on glutes, hamstrings and lower back erectors; everything else grey.
```

### `wioslowanie.png`: wiosłowanie hantlem w podporze

```
Create a NEW image with TWO PANELS SIDE BY SIDE (left half and right half), using the attached man as the reference character: same face, hair, anatomical écorché muscle style with grey muscles, black shorts, black shoes, pure white background, soft studio light. Both panels: exactly the same scene, camera angle, distance and scale; only his arms differ. No text, no numbers, no logos anywhere.

Scene: chest-supported dumbbell row. He lies chest down on a light grey incline bench set to about 30 degrees, feet on the floor, a matte black dumbbell in each hand. Camera: three-quarter side view from his left, slightly from above, so the back and the elbows are visible.

LEFT panel: arms hanging straight down.
RIGHT panel: dumbbells pulled up to the hips, elbows driven back past the torso, shoulder blades squeezed, chest still on the bench.

Blue (#2F6FD6) ONLY on lats, rhomboids, trapezius, rear shoulders and biceps; everything else grey.
```

### `podciaganie.png`: podciąganie nachwytem z obciążeniem

```
Create a NEW image with TWO PANELS SIDE BY SIDE (left half and right half), using the attached man as the reference character: same face, hair, anatomical écorché muscle style with grey muscles, black shorts, black shoes, pure white background, soft studio light. Both panels: exactly the same scene, camera angle, distance and scale; only his body position differs. No text, no numbers, no logos anywhere.

Scene: weighted pull-up on a light grey pull-up bar, overhand grip slightly wider than the shoulders, a matte black dumbbell held between his feet, legs slightly bent. Camera: three-quarter view from BEHIND and to the left, so his back is clearly visible.

LEFT panel: dead hang, arms fully straight.
RIGHT panel: chin above the bar, elbows pulled down to the sides, dumbbell still between the feet.

Blue (#2F6FD6) ONLY on lats, biceps and middle back; everything else grey.
```

### `facepull.png`: face pull

```
Create a NEW image with TWO PANELS SIDE BY SIDE (left half and right half), using the attached man as the reference character: same face, hair, anatomical écorché muscle style with grey muscles, black shorts, black shoes, pure white background, soft studio light. Both panels: exactly the same scene, camera angle, distance and scale; only his arms differ. No text, no numbers, no logos anywhere.

Scene: face pull on a light grey cable tower, pulley at face height, a rope attachment held with both hands, standing facing the tower. Camera: true SIDE view from his left.

LEFT panel: arms straight in front, rope at arm's length.
RIGHT panel: rope pulled to the face, hands beside the ears, elbows high and wide, upper arms rotated outward.

Blue (#2F6FD6) ONLY on rear shoulders, rhomboids and middle trapezius; everything else grey.
```

### `odwrotne-rozpietki.png`: odwrotne rozpiętki

```
Create a NEW image with TWO PANELS SIDE BY SIDE (left half and right half), using the attached man as the reference character: same face, hair, anatomical écorché muscle style with grey muscles, black shorts, black shoes, pure white background, soft studio light. Both panels: exactly the same scene, camera angle, distance and scale; only his arms differ. No text, no numbers, no logos anywhere.

Scene: bent-over reverse dumbbell fly. He stands bent forward at the hips, back flat, torso almost parallel to the floor, knees slightly bent, a light matte black dumbbell in each hand. Camera: three-quarter view from the front-left, slightly from above, so both arms and the upper back are visible.

LEFT panel: dumbbells hanging below the chest, palms facing each other, elbows slightly bent.
RIGHT panel: dumbbells raised out to the sides to shoulder height in a wide arc, shoulder blades squeezed, torso still bent forward.

Blue (#2F6FD6) ONLY on rear shoulders, rhomboids and middle trapezius; everything else grey.
```

### `skos-hantle.png`: wyciskanie hantli na skosie

```
Create a NEW image with TWO PANELS SIDE BY SIDE (left half and right half), using the attached man as the reference character: same face, hair, anatomical écorché muscle style with grey muscles, black shorts, black shoes, pure white background, soft studio light. Both panels: exactly the same scene, camera angle, distance and scale; only his arms differ. No text, no numbers, no logos anywhere.

Scene: incline dumbbell press on a light grey bench set to about 30 degrees, feet flat on the floor, a matte black dumbbell in each hand. Camera: three-quarter view from the side of his feet, slightly from above.

LEFT panel: dumbbells beside the upper chest, elbows about 45 degrees from the torso.
RIGHT panel: dumbbells pressed up over the upper chest, arms straight, dumbbells close but not touching.

Blue (#2F6FD6) ONLY on upper chest, front shoulders and triceps; everything else grey.
```

### `triceps.png`: prostowanie ramion na wyciągu jednorącz

```
Create a NEW image with TWO PANELS SIDE BY SIDE (left half and right half), using the attached man as the reference character: same face, hair, anatomical écorché muscle style with grey muscles, black shorts, black shoes, pure white background, soft studio light. Both panels: exactly the same scene, camera angle, distance and scale; only his working arm differs. No text, no numbers, no logos anywhere.

Scene: single-arm cable triceps pushdown on a light grey cable tower with a high pulley, a single handle in his LEFT hand, upper arm tight against his side, other hand relaxed. He stands facing the tower. Camera: true SIDE view from his left, so the working arm is closest to the camera.

LEFT panel: elbow bent about 90 degrees, forearm about parallel to the floor.
RIGHT panel: elbow fully straight, handle pushed down next to the thigh, upper arm still against the side.

Blue (#2F6FD6) ONLY on the triceps of the working (left) arm; everything else grey.
```

### `biceps.png`: uginanie ramion z hantlami

```
Create a NEW image with TWO PANELS SIDE BY SIDE (left half and right half), using the attached man as the reference character: same face, hair, anatomical écorché muscle style with grey muscles, black shorts, black shoes, pure white background, soft studio light. Both panels: exactly the same scene, camera angle, distance and scale; only his arms differ. No text, no numbers, no logos anywhere.

Scene: standing dumbbell biceps curl, a matte black dumbbell in each hand, palms facing forward, elbows close to the sides. Camera: three-quarter view from the front-left.

LEFT panel: arms straight at the sides.
RIGHT panel: both dumbbells curled up to shoulder height, elbows still at the sides, no swinging.

Blue (#2F6FD6) ONLY on biceps and forearm flexors; everything else grey.
```

### `rollout.png`: rollout

```
Create a NEW image with TWO PANELS SIDE BY SIDE (left half and right half), using the attached man as the reference character: same face, hair, anatomical écorché muscle style with grey muscles, black shorts, black shoes, pure white background, soft studio light. Both panels: exactly the same scene, camera angle, distance and scale; only his body position differs. No text, no numbers, no logos anywhere.

Scene: ab wheel rollout from the knees on the floor, both hands on the ab wheel handles. Camera: true SIDE view from his left at floor level.

LEFT panel: kneeling, the wheel under the shoulders, arms straight, back flat.
RIGHT panel: rolled forward until the body is almost straight and low over the floor, arms extended in front, hips NOT sagging, one straight line from knees to shoulders.

Blue (#2F6FD6) ONLY on abdominals and obliques; everything else grey.
```

### `unoszenie-nog.png`: unoszenie nóg w zwisie

```
Create a NEW image with TWO PANELS SIDE BY SIDE (left half and right half), using the attached man as the reference character: same face, hair, anatomical écorché muscle style with grey muscles, black shorts, black shoes, pure white background, soft studio light. Both panels: exactly the same scene, camera angle, distance and scale; only his legs differ. No text, no numbers, no logos anywhere.

Scene: hanging leg raise from a light grey pull-up bar, overhand grip, arms straight, body not swinging. Camera: true SIDE view from his left.

LEFT panel: legs hanging straight down.
RIGHT panel: knees raised up towards the chest, pelvis tilted up.

Blue (#2F6FD6) ONLY on abdominals and hip flexors; everything else grey.
```

### `bieznia.png`: marsz pod górę na bieżni

```
Create a NEW image with TWO PANELS SIDE BY SIDE (left half and right half), using the attached man as the reference character: same face, hair, anatomical écorché muscle style with grey muscles, black shorts, black shoes, pure white background, soft studio light. Both panels: exactly the same scene, camera angle, distance and scale; only his stride differs. No text, no numbers, no logos anywhere (also no display text on the treadmill).

Scene: walking on a light grey treadmill set to a clearly visible incline (about 10 percent), upright posture, NOT holding the handrails, natural arm swing. Camera: true SIDE view from his left.

LEFT panel: left leg forward.
RIGHT panel: right leg forward, arms swinging the other way.

Blue (#2F6FD6) ONLY on glutes, hamstrings, quadriceps and calves; everything else grey.
```

### `mobilnosc.png`: mobilność bioder i odcinka piersiowego

Tu panele to dwa różne ćwiczenia, a nie start i koniec ruchu. Aplikacja pokaże je po kolei.

```
Create a NEW image with TWO PANELS SIDE BY SIDE (left half and right half), using the attached man as the reference character: same face, hair, anatomical écorché muscle style with grey muscles, black shorts, black shoes, pure white background, soft studio light. Same scale in both panels. No text, no numbers, no logos anywhere.

LEFT panel: 90/90 hip stretch: sitting on the floor, front leg bent 90 degrees in front, back leg bent 90 degrees to the side behind, torso upright leaning slightly over the front shin, hands lightly on the floor. Three-quarter front view. Blue (#2F6FD6) on glutes and hip rotators.
RIGHT panel: thoracic "open book": lying on his left side on the floor, knees bent 90 degrees and stacked, the top (right) arm rotated open to the other side, chest turning towards the ceiling, eyes following the hand, knees together on the floor. Three-quarter view from above. Blue (#2F6FD6) on upper back and chest.

Everything not listed stays grey.
```

## Gdy skończysz

Napisz agentowi, które pliki są w `exports/technika/`. Możesz wrzucać partiami. Agent:

1. Potnie każdy obrazek na 2 klatki wyrównane po sprzęcie i zmniejszy je do WebP (ok. 15–20 kB na klatkę).
2. Obejrzy klatki i wskaże te do poprawy.
3. Wepnie je w aplikację w miejsce ludzika, z odliczaniem pauz w wariantach.
