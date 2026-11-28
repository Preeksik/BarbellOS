# Ilustracje i filmy techniki

Przycisk „Technika” przy ćwiczeniu pokazuje krótki film ruchu w anatomicznym stylu (szare mięśnie, pracujące na niebiesko). Stan: 28.11.2026.

## Jak powstaje film

1. **Ty, czat Gemini:** obrazek ćwiczenia z naszą postacią (prompty niżej).
   - **Dwa panele** obok siebie (lewy: start ruchu, prawy: koniec), gdy technika musi być dokładna: boje, warianty, większość pomocniczych.
   - **Jeden obrazek** (sam start ruchu) przy prostych pomocniczych. Ruch dorysuje model wideo według opisu.
2. **Agent:** tnie obrazek na klatki wyrównane po sprzęcie (`scripts/technique_frames.py`), sprawdza technikę i wpina klatki do aplikacji. Od tej chwili ćwiczenie ma przełączane klatki.
3. **Ty, Google Colab:** notatnik z modelem wideo Wan (`scripts/colab/`) robi z klatek płynny film. Klikasz „Uruchom wszystko” raz na całą partię.
4. **Agent:** wpina filmy. Pauzy i tempo wariantów steruje aplikacja (np. postój na dole z odliczaniem), więc warianty korzystają z jednego filmu.

Film trafia dokładnie w obie pozycje z obrazka, dlatego **poprawna technika na obrazku to poprawna technika w filmie**.

## Status

| Plik | Ćwiczenie | Obrazek | Partia | Te same klatki dostają | Stan |
|---|---|---|---|---|---|
| `przysiad.png` | Przysiad | dwa panele | — | z pauzą 2 s, tempo 3-1-0 | **gotowe, z filmem**; do przegenerowania głębiej (na końcu) |
| `lawa.png` | Wyciskanie leżąc z pauzą | dwa panele | 1 | T&G, z pauzą 3 s | do zrobienia |
| `martwy.png` | Martwy ciąg | dwa panele | 1 | | do zrobienia |
| `rdl.png` | Rumuński martwy ciąg | dwa panele | 1 | | do zrobienia |
| `facepull.png` | Face pull | jeden obrazek | 1 | | do zrobienia |
| `triceps.png` | Prostowanie ramion na wyciągu jednorącz | jeden obrazek | 1 | | do zrobienia |
| `biceps.png` | Uginanie ramion z hantlami | jeden obrazek | 1 | | do zrobienia |
| `piny.png` | Przysiad z pinów | dwa panele | 2 | | do zrobienia |
| `larsen.png` | Larsen press | dwa panele | 2 | | do zrobienia |
| `waski.png` | Wyciskanie wąskim chwytem | dwa panele | 2 | | do zrobienia |
| `spoto.png` | Spoto press | dwa panele | 2 | | do zrobienia |
| `wioslowanie.png` | Wiosłowanie hantlem w podporze | dwa panele | 2 | | do zrobienia |
| `podciaganie.png` | Podciąganie nachwytem z obciążeniem | dwa panele | 2 | | do zrobienia |
| `suwnica.png` | Suwnica (leg press 45°) | dwa panele | 3 | | do zrobienia |
| `uginanie-nog.png` | Uginanie nóg leżąc | dwa panele | 3 | | do zrobienia |
| `hiperekstensje.png` | Hiperekstensje | dwa panele | 3 | | do zrobienia |
| `odwrotne-rozpietki.png` | Odwrotne rozpiętki | dwa panele | 3 | | do zrobienia |
| `skos-hantle.png` | Wyciskanie hantli na skosie | dwa panele | 3 | | do zrobienia |
| `rollout.png` | Rollout | dwa panele | 3 | | do zrobienia |
| `unoszenie-nog.png` | Unoszenie nóg w zwisie | dwa panele | 3 | | do zrobienia |
| `bieznia.png` | Marsz pod górę na bieżni | dwa panele | 3 | | do zrobienia |
| `mobilnosc.png` | Mobilność bioder i piersiowego | dwa panele (dwa ćwiczenia) | 3 | | do zrobienia, bez filmu |

Partia 1 sprawdza oba rodzaje obrazków. Jeśli „jeden obrazek” da dobry film, przestawimy tak też proste ćwiczenia z partii 3.

## Gemini: ustawienia i kolejność

- Model **Neon**, effort **średni**. Carbon jest tylko w planie Ultra, a Hydrogen gorzej trzyma się opisu.
- Przed wysłaniem włącz **Utwórz obraz** (ikona obrazka w polu wpisywania). Bez tego Gemini odpowiada „Jako model językowy nie jestem do tego przeznaczony”.
- **Format obrazu:** kwadrat. **Format:** domyślny, bez stylu i bez GIF-a.

Dla każdego ćwiczenia:

1. **Nowa rozmowa.** W starej Gemini przenosi kadr z poprzedniego ćwiczenia.
2. Załącz spinaczem `exports\technika\00-postac.png` (postać wzorcowa).
3. Wklej **cały blok** promptu i wyślij.
4. Sprawdź obrazek (lista niżej).
   - Gdy kompozycja jest dobra, a zepsuty jest szczegół (np. ręce): **wygeneruj ponownie w tej samej rozmowie** albo wyślij poprawkę `popraw:`.
   - Gdy zła jest kamera albo ustawienie sprzętu: **nowa rozmowa**, bo poprawki trzymają się starego kadru.
5. Pobierz i zapisz pod nazwą z tabeli w `C:\Users\adria\Desktop\BarbellOS\exports\technika\`. Pliki z Gemini przychodzą jako `Gemini_Generated_Image_….png`, więc zmień im nazwy.

**Sprawdź przed zapisem:**

- **Kamera jak w opisie.** Najczęstszy błąd: Gemini obraca postać przodem. Ławy idą w czystym profilu, bo z ukosa Gemini rysuje sztangę nad klatką zamiast na niej.
- **Ten sam sprzęt w obu panelach**, w tym samym miejscu i skali. Zmienia się tylko ciało. Przesunięta ławka czy stojak skacze w filmie.
- **Technika:**
  - przysiad i warianty: biodro poniżej kolana;
  - ława: sztanga dotyka klatki, łopatki na ławce, pośladki na ławce, stopy na podłodze;
  - martwy i RDL: plecy proste.
- **Ręce:** osobne ramię, łokieć i przedramię, dłonie widoczne na gryfie albo hantlu. Niebieska „kula” przy barku oznacza, że trzeba wygenerować ponownie.
- **Niebieskie tylko mięśnie z opisu.** Gemini lubi dokładać brzuch i łydki.
- **Bez napisów i liczb**, także na talerzach.

Drobiazgi (zacisk na talerzu, odcień niebieskiego) przepuszczaj, bo każda poprawka ryzykuje zmianę kadru.

**Poprawki** (wysyłasz w tej samej rozmowie):

```
popraw: keep everything identical, fix only the arms: anatomically correct arms with a clearly separate upper arm, elbow and forearm, normal-size shoulder muscle, both hands visibly gripping the bar.
```

```
popraw: keep both panels, the same man, equipment and scale. Turn the camera to a true SIDE PROFILE (we look at his left side, his face is seen from the side).
```

```
popraw: keep everything identical. Blue ONLY on <mięśnie po angielsku>; everything else grey, including abs, obliques and calves.
```

## Prompty: partia 1

### `lawa.png`: wyciskanie leżąc z pauzą (dwa panele)

```
IMPORTANT: the RIGHT panel must be an exact copy of the LEFT panel: same equipment, same position and rotation of every object, same camera; ONLY the moving body parts change. If you overlay the two panels, the equipment and the floor must match perfectly. No divider line between the panels.

Create a NEW image with TWO PANELS SIDE BY SIDE (left half and right half), using the attached man as the reference character: same face, hair, anatomical écorché muscle style with grey muscles, black shorts, black shoes, pure white background, soft studio light. Both panels: exactly the same scene, camera angle, distance and scale; only his arms differ. No text, no numbers, no logos anywhere (also none on plates).

Scene: competition bench press on a flat light grey bench under a light grey rack, barbell with two identical matte black plates (no clips, no markings). Camera: PURE SIDE PROFILE from his left at bench height. Shoulder blades squeezed together and pressed DOWN into the bench, shoulders pulled back and away from the ears (NOT shrugged up towards the bar), moderate upper-back arch, buttocks on the bench, both feet flat on the floor. Anatomically correct arms: clearly separate upper arm, elbow and forearm, normal-size shoulder muscle, hands visibly gripping the bar.

LEFT panel: TOP position, arms straight and VERTICAL, bar locked out directly above the SHOULDER JOINT (not above the face), shoulders still pressed into the bench.
RIGHT panel: the bar RESTS ON his chest: it physically TOUCHES the lower part of the sternum, NO gap between bar and chest; forearms vertical, elbows below the bar, buttocks still on the bench, feet flat.

Blue (#2F6FD6) ONLY on pectorals, front shoulders and triceps; everything else grey.
```

### `martwy.png`: martwy ciąg (dwa panele)

```
IMPORTANT: the RIGHT panel must be an exact copy of the LEFT panel: same equipment, same position and rotation of every object, same camera; ONLY the moving body parts change. If you overlay the two panels, the equipment and the floor must match perfectly. No divider line between the panels.

Create a NEW image with TWO PANELS SIDE BY SIDE (left half and right half), using the attached man as the reference character: same face, hair, anatomical écorché muscle style with grey muscles, black shorts, black shoes, pure white background, soft studio light. Both panels: exactly the same scene, camera angle, distance and scale; only his pose differs. No text, no numbers, no logos anywhere (also none on plates).

Scene: conventional deadlift, no rack, barbell with two identical matte black plates (no clips, no markings). Camera: true SIDE PROFILE from his left at hip height (we see his face from the side and the full line of his back). Both hands clearly visible gripping the bar just outside the legs.

LEFT panel: START: bar on the floor over the middle of the foot, shins touching the bar, straight arms, hips higher than the knees, shoulders slightly in front of the bar, back FLAT and neutral.
RIGHT panel: LOCKOUT: standing fully upright, hips and knees fully extended, shoulders back, bar hanging in straight arms at the top of the thighs, no leaning back.

Blue (#2F6FD6) ONLY on glutes, hamstrings, lower back erectors and upper trapezius; everything else grey.
```

### `rdl.png`: rumuński martwy ciąg (dwa panele)

```
IMPORTANT: the RIGHT panel must be an exact copy of the LEFT panel: same equipment, same position and rotation of every object, same camera; ONLY the moving body parts change. If you overlay the two panels, the equipment and the floor must match perfectly. No divider line between the panels.

Create a NEW image with TWO PANELS SIDE BY SIDE (left half and right half), using the attached man as the reference character: same face, hair, anatomical écorché muscle style with grey muscles, black shorts, black shoes, pure white background, soft studio light. Both panels: exactly the same scene, camera angle, distance and scale; only his pose differs. No text, no numbers, no logos anywhere (also none on plates).

Scene: Romanian deadlift, no rack, barbell with two identical matte black plates (no clips, no markings). Camera: true SIDE PROFILE from his left at hip height. Both hands clearly visible on the bar.

LEFT panel: standing upright, bar in straight arms at the top of the thighs, knees slightly unlocked.
RIGHT panel: hips pushed far BACK, knees slightly bent (same as in the left panel), back FLAT, bar slid along the legs to mid-shin, plates NOT touching the floor.

Blue (#2F6FD6) ONLY on hamstrings, glutes and lower back erectors; everything else grey.
```

### `facepull.png`: face pull (jeden obrazek)

```
Create a NEW single image (ONE scene, not panels), using the attached man as the reference character: same face, hair, anatomical écorché muscle style with grey muscles, black shorts, black shoes, pure white background, soft studio light. No text, no numbers, no logos anywhere. Whole body and all equipment in frame with margin, square image.

Scene: face pull on a light grey cable tower, pulley at face height, a rope attachment held with both hands, standing facing the tower. Camera: true SIDE view from his left.

Pose: START of the movement: arms straight in front, rope at arm's length, body upright.

Blue (#2F6FD6) ONLY on rear shoulders, rhomboids and middle trapezius; everything else grey.
```

### `triceps.png`: prostowanie ramion na wyciągu jednorącz (jeden obrazek)

```
Create a NEW single image (ONE scene, not panels), using the attached man as the reference character: same face, hair, anatomical écorché muscle style with grey muscles, black shorts, black shoes, pure white background, soft studio light. No text, no numbers, no logos anywhere. Whole body and all equipment in frame with margin, square image.

Scene: single-arm cable triceps pushdown on a light grey cable tower with a high pulley, a single handle in his LEFT hand, upper arm tight against his side, other hand relaxed. He stands facing the tower. Camera: true SIDE view from his left, so the working arm is closest to the camera.

Pose: START of the movement: elbow bent about 90 degrees, forearm about parallel to the floor.

Blue (#2F6FD6) ONLY on the triceps of the working (left) arm; everything else grey.
```

### `biceps.png`: uginanie ramion z hantlami (jeden obrazek)

```
Create a NEW single image (ONE scene, not panels), using the attached man as the reference character: same face, hair, anatomical écorché muscle style with grey muscles, black shorts, black shoes, pure white background, soft studio light. No text, no numbers, no logos anywhere. Whole body and all equipment in frame with margin, square image.

Scene: standing dumbbell biceps curl, a matte black dumbbell in each hand, palms facing forward, elbows close to the sides. Camera: three-quarter view from the front-left.

Pose: START of the movement: arms straight at the sides.

Blue (#2F6FD6) ONLY on biceps and forearm flexors; everything else grey.
```

## Prompty: partia 2

### `piny.png`: przysiad z pinów (dwa panele)

```
IMPORTANT: the RIGHT panel must be an exact copy of the LEFT panel: same equipment, same position and rotation of every object, same camera; ONLY the moving body parts change. If you overlay the two panels, the equipment and the floor must match perfectly. No divider line between the panels.

Create a NEW image with TWO PANELS SIDE BY SIDE (left half and right half), using the attached man as the reference character: same face, hair, anatomical écorché muscle style with grey muscles, black shorts, black shoes, pure white background, soft studio light. Both panels: exactly the same scene, camera angle, distance and scale; only his pose differs. No text, no numbers, no logos anywhere (also none on plates).

Scene: back squat from safety pins inside a light grey power rack. The rack's two horizontal safety pins are clearly visible, set LOW, at the height the bar reaches in a deep squat. Barbell with two identical matte black plates (no clips, no markings) on his upper back behind the neck. Camera: true SIDE PROFILE from his left at hip height. His hand is clearly visible gripping the bar, elbow pointing down and back.

LEFT panel: TOP, standing fully upright with the bar on his back.
RIGHT panel: BOTTOM: the bar resting completely still ON the safety pins; thighs slope DOWNWARD from the knee to the hip, hip crease clearly LOWER than the top of the knee, back flat, body tight.

Blue (#2F6FD6) ONLY on quadriceps, glutes and lower back erectors; everything else grey.
```

### `larsen.png`: Larsen press (dwa panele)

```
IMPORTANT: the RIGHT panel must be an exact copy of the LEFT panel: same equipment, same position and rotation of every object, same camera; ONLY the moving body parts change. If you overlay the two panels, the equipment and the floor must match perfectly. No divider line between the panels.

Create a NEW image with TWO PANELS SIDE BY SIDE (left half and right half), using the attached man as the reference character: same face, hair, anatomical écorché muscle style with grey muscles, black shorts, black shoes, pure white background, soft studio light. Both panels: exactly the same scene, camera angle, distance and scale; only his arms differ. No text, no numbers, no logos anywhere (also none on plates).

Scene: Larsen press on a flat light grey bench under a light grey rack, barbell with two identical matte black plates (no clips, no markings). His legs are STRAIGHT and LIFTED OFF THE FLOOR, extended forward in the air at about bench height, feet touching nothing, buttocks on the bench. Camera: PURE SIDE PROFILE from his left at bench height, so the straight raised legs are clearly visible. Shoulder blades squeezed together and pressed DOWN into the bench, shoulders pulled back (NOT shrugged up towards the bar), moderate upper-back arch. Anatomically correct arms: clearly separate upper arm, elbow and forearm, normal-size shoulder muscle, hands visibly gripping the bar.

LEFT panel: arms straight and vertical, bar locked out directly above the shoulder joint.
RIGHT panel: the bar RESTS ON the lower chest, touching it, NO gap; forearms vertical; legs still straight in the air.

Blue (#2F6FD6) ONLY on pectorals, front shoulders, triceps and abdominals; everything else grey.
```

### `waski.png`: wyciskanie wąskim chwytem (dwa panele)

```
IMPORTANT: the RIGHT panel must be an exact copy of the LEFT panel: same equipment, same position and rotation of every object, same camera; ONLY the moving body parts change. If you overlay the two panels, the equipment and the floor must match perfectly. No divider line between the panels.

Create a NEW image with TWO PANELS SIDE BY SIDE (left half and right half), using the attached man as the reference character: same face, hair, anatomical écorché muscle style with grey muscles, black shorts, black shoes, pure white background, soft studio light. Both panels: exactly the same scene, camera angle, distance and scale; only his arms differ. No text, no numbers, no logos anywhere (also none on plates).

Scene: close-grip bench press on a flat light grey bench under a light grey rack, barbell with two identical matte black plates (no clips, no markings), feet flat on the floor, buttocks on the bench, shoulder blades pressed into the bench. Camera: three-quarter view from slightly above and from the side of his head, so the NARROW grip is clearly visible: hands at shoulder width, clearly narrower than a normal bench press grip. Anatomically correct arms with hands visibly gripping the bar.

LEFT panel: arms straight, bar locked out above the shoulders.
RIGHT panel: the bar RESTS ON the lower chest, touching it, NO gap; elbows tucked close to the torso, forearms vertical.

Blue (#2F6FD6) ONLY on triceps, pectorals and front shoulders; everything else grey.
```

### `spoto.png`: spoto press (dwa panele)

```
IMPORTANT: the RIGHT panel must be an exact copy of the LEFT panel: same equipment, same position and rotation of every object, same camera; ONLY the moving body parts change. If you overlay the two panels, the equipment and the floor must match perfectly. No divider line between the panels.

Create a NEW image with TWO PANELS SIDE BY SIDE (left half and right half), using the attached man as the reference character: same face, hair, anatomical écorché muscle style with grey muscles, black shorts, black shoes, pure white background, soft studio light. Both panels: exactly the same scene, camera angle, distance and scale; only his arms differ. No text, no numbers, no logos anywhere (also none on plates).

Scene: Spoto press on a flat light grey bench under a light grey rack, barbell with two identical matte black plates (no clips, no markings), buttocks on the bench, feet flat. Camera: PURE SIDE PROFILE from his left at bench height, so the space between the bar and the chest is clearly visible. Shoulder blades squeezed together and pressed DOWN into the bench, shoulders pulled back (NOT shrugged up towards the bar). Anatomically correct arms: clearly separate upper arm, elbow and forearm, normal-size shoulder muscle, hands visibly gripping the bar.

LEFT panel: arms straight and vertical, bar locked out directly above the shoulder joint.
RIGHT panel: the bar held motionless about 2 cm ABOVE the chest, clearly NOT touching it: a small visible gap of white background between the bar and the chest. Forearms vertical, body tight.

Blue (#2F6FD6) ONLY on pectorals, front shoulders and triceps; everything else grey.
```

### `wioslowanie.png`: wiosłowanie hantlem w podporze (dwa panele)

```
IMPORTANT: the RIGHT panel must be an exact copy of the LEFT panel: same equipment, same position and rotation of every object, same camera; ONLY the moving body parts change. If you overlay the two panels, the equipment and the floor must match perfectly. No divider line between the panels.

Create a NEW image with TWO PANELS SIDE BY SIDE (left half and right half), using the attached man as the reference character: same face, hair, anatomical écorché muscle style with grey muscles, black shorts, black shoes, pure white background, soft studio light. Both panels: exactly the same scene, camera angle, distance and scale; only his arms differ. No text, no numbers, no logos anywhere.

Scene: chest-supported dumbbell row. He lies chest down on a light grey incline bench set to about 30 degrees, feet on the floor, a matte black dumbbell in each hand. Camera: three-quarter side view from his left, slightly from above, so the back and the elbows are visible.

LEFT panel: arms hanging straight down.
RIGHT panel: dumbbells pulled up to the hips, elbows driven back past the torso, shoulder blades squeezed, chest still on the bench.

Blue (#2F6FD6) ONLY on lats, rhomboids, trapezius, rear shoulders and biceps; everything else grey.
```

### `podciaganie.png`: podciąganie nachwytem z obciążeniem (dwa panele)

```
IMPORTANT: the RIGHT panel must be an exact copy of the LEFT panel: same equipment, same position and rotation of every object, same camera; ONLY the moving body parts change. If you overlay the two panels, the equipment and the floor must match perfectly. No divider line between the panels.

Create a NEW image with TWO PANELS SIDE BY SIDE (left half and right half), using the attached man as the reference character: same face, hair, anatomical écorché muscle style with grey muscles, black shorts, black shoes, pure white background, soft studio light. Both panels: exactly the same scene, camera angle, distance and scale; only his body position differs. No text, no numbers, no logos anywhere.

Scene: weighted pull-up on a light grey pull-up bar, overhand grip slightly wider than the shoulders, a matte black dumbbell held between his feet, legs slightly bent. Camera: three-quarter view from BEHIND and to the left, so his back is clearly visible.

LEFT panel: dead hang, arms fully straight.
RIGHT panel: chin above the bar, elbows pulled down to the sides, dumbbell still between the feet.

Blue (#2F6FD6) ONLY on lats, biceps and middle back; everything else grey.
```

## Prompty: partia 3

### `suwnica.png`: suwnica, leg press 45° (dwa panele)

```
IMPORTANT: the RIGHT panel must be an exact copy of the LEFT panel: same equipment, same position and rotation of every object, same camera; ONLY the moving body parts change. If you overlay the two panels, the equipment and the floor must match perfectly. No divider line between the panels.

Create a NEW image with TWO PANELS SIDE BY SIDE (left half and right half), using the attached man as the reference character: same face, hair, anatomical écorché muscle style with grey muscles, black shorts, black shoes, pure white background, soft studio light. Both panels: exactly the same scene, camera angle, distance and scale; only his legs differ. No text, no numbers, no logos anywhere (also none on the machine or plates).

Scene: 45-degree leg press machine (light grey frame, matte black plates). He sits with his back flat on the backrest, feet shoulder-width on the platform. Camera: true SIDE view from his left.

LEFT panel: legs almost straight, knees NOT locked.
RIGHT panel: knees deeply bent towards the chest, lower back still flat on the backrest, heels on the platform.

Blue (#2F6FD6) ONLY on quadriceps and glutes; everything else grey.
```

### `uginanie-nog.png`: uginanie nóg leżąc (dwa panele)

```
IMPORTANT: the RIGHT panel must be an exact copy of the LEFT panel: same equipment, same position and rotation of every object, same camera; ONLY the moving body parts change. If you overlay the two panels, the equipment and the floor must match perfectly. No divider line between the panels.

Create a NEW image with TWO PANELS SIDE BY SIDE (left half and right half), using the attached man as the reference character: same face, hair, anatomical écorché muscle style with grey muscles, black shorts, black shoes, pure white background, soft studio light. Both panels: exactly the same scene, camera angle, distance and scale; only his legs differ. No text, no numbers, no logos anywhere.

Scene: lying leg curl machine (light grey). He lies face down, hips pressed into the pad, hands on the handles, the roller pad behind the lower calves just above the heels. Camera: true SIDE view from his left.

LEFT panel: legs straight.
RIGHT panel: knees bent 90 degrees or more, heels pulled towards the glutes, hips still on the pad.

Blue (#2F6FD6) ONLY on hamstrings and calves; everything else grey.
```

### `hiperekstensje.png`: hiperekstensje (dwa panele)

```
IMPORTANT: the RIGHT panel must be an exact copy of the LEFT panel: same equipment, same position and rotation of every object, same camera; ONLY the moving body parts change. If you overlay the two panels, the equipment and the floor must match perfectly. No divider line between the panels.

Create a NEW image with TWO PANELS SIDE BY SIDE (left half and right half), using the attached man as the reference character: same face, hair, anatomical écorché muscle style with grey muscles, black shorts, black shoes, pure white background, soft studio light. Both panels: exactly the same scene, camera angle, distance and scale; only his torso differs. No text, no numbers, no logos anywhere (also none on the plate).

Scene: 45-degree back extension bench (Roman chair, light grey). Hips on the pad, ankles under the foot rollers, a matte black weight plate held against his chest with both arms. Camera: true SIDE view from his left.

LEFT panel: torso bent down at the hips, back neutral.
RIGHT panel: torso raised until the body is one straight line from heels to head, no overextension of the lower back.

Blue (#2F6FD6) ONLY on glutes, hamstrings and lower back erectors; everything else grey.
```

### `odwrotne-rozpietki.png`: odwrotne rozpiętki (dwa panele)

```
IMPORTANT: the RIGHT panel must be an exact copy of the LEFT panel: same equipment, same position and rotation of every object, same camera; ONLY the moving body parts change. If you overlay the two panels, the equipment and the floor must match perfectly. No divider line between the panels.

Create a NEW image with TWO PANELS SIDE BY SIDE (left half and right half), using the attached man as the reference character: same face, hair, anatomical écorché muscle style with grey muscles, black shorts, black shoes, pure white background, soft studio light. Both panels: exactly the same scene, camera angle, distance and scale; only his arms differ. No text, no numbers, no logos anywhere.

Scene: bent-over reverse dumbbell fly. He stands bent forward at the hips, back flat, torso almost parallel to the floor, knees slightly bent, a light matte black dumbbell in each hand. Camera: three-quarter view from the front-left, slightly from above, so both arms and the upper back are visible.

LEFT panel: dumbbells hanging below the chest, palms facing each other, elbows slightly bent.
RIGHT panel: dumbbells raised out to the sides to shoulder height in a wide arc, shoulder blades squeezed, torso still bent forward.

Blue (#2F6FD6) ONLY on rear shoulders, rhomboids and middle trapezius; everything else grey.
```

### `skos-hantle.png`: wyciskanie hantli na skosie (dwa panele)

```
IMPORTANT: the RIGHT panel must be an exact copy of the LEFT panel: same equipment, same position and rotation of every object, same camera; ONLY the moving body parts change. If you overlay the two panels, the equipment and the floor must match perfectly. No divider line between the panels.

Create a NEW image with TWO PANELS SIDE BY SIDE (left half and right half), using the attached man as the reference character: same face, hair, anatomical écorché muscle style with grey muscles, black shorts, black shoes, pure white background, soft studio light. Both panels: exactly the same scene, camera angle, distance and scale; only his arms differ. No text, no numbers, no logos anywhere.

Scene: incline dumbbell press on a light grey bench set to about 30 degrees, feet flat on the floor, a matte black dumbbell in each hand. Camera: three-quarter view from the side of his feet, slightly from above.

LEFT panel: dumbbells beside the upper chest, elbows about 45 degrees from the torso.
RIGHT panel: dumbbells pressed up over the upper chest, arms straight, dumbbells close but not touching.

Blue (#2F6FD6) ONLY on upper chest, front shoulders and triceps; everything else grey.
```

### `rollout.png`: rollout (dwa panele)

```
IMPORTANT: the RIGHT panel must be an exact copy of the LEFT panel: same equipment, same position and rotation of every object, same camera; ONLY the moving body parts change. If you overlay the two panels, the equipment and the floor must match perfectly. No divider line between the panels.

Create a NEW image with TWO PANELS SIDE BY SIDE (left half and right half), using the attached man as the reference character: same face, hair, anatomical écorché muscle style with grey muscles, black shorts, black shoes, pure white background, soft studio light. Both panels: exactly the same scene, camera angle, distance and scale; only his body position differs. No text, no numbers, no logos anywhere.

Scene: ab wheel rollout from the knees on the floor, both hands on the ab wheel handles. Camera: true SIDE view from his left at floor level.

LEFT panel: kneeling, the wheel under the shoulders, arms straight, back flat.
RIGHT panel: rolled forward until the body is almost straight and low over the floor, arms extended in front, hips NOT sagging, one straight line from knees to shoulders.

Blue (#2F6FD6) ONLY on abdominals and obliques; everything else grey.
```

### `unoszenie-nog.png`: unoszenie nóg w zwisie (dwa panele)

```
IMPORTANT: the RIGHT panel must be an exact copy of the LEFT panel: same equipment, same position and rotation of every object, same camera; ONLY the moving body parts change. If you overlay the two panels, the equipment and the floor must match perfectly. No divider line between the panels.

Create a NEW image with TWO PANELS SIDE BY SIDE (left half and right half), using the attached man as the reference character: same face, hair, anatomical écorché muscle style with grey muscles, black shorts, black shoes, pure white background, soft studio light. Both panels: exactly the same scene, camera angle, distance and scale; only his legs differ. No text, no numbers, no logos anywhere.

Scene: hanging leg raise from a light grey pull-up bar, overhand grip, arms straight, body not swinging. Camera: true SIDE view from his left.

LEFT panel: legs hanging straight down.
RIGHT panel: knees raised up towards the chest, pelvis tilted up.

Blue (#2F6FD6) ONLY on abdominals and hip flexors; everything else grey.
```

### `bieznia.png`: marsz pod górę na bieżni (dwa panele)

```
IMPORTANT: the RIGHT panel must be an exact copy of the LEFT panel: same equipment, same position and rotation of every object, same camera; ONLY the moving body parts change. If you overlay the two panels, the equipment and the floor must match perfectly. No divider line between the panels.

Create a NEW image with TWO PANELS SIDE BY SIDE (left half and right half), using the attached man as the reference character: same face, hair, anatomical écorché muscle style with grey muscles, black shorts, black shoes, pure white background, soft studio light. Both panels: exactly the same scene, camera angle, distance and scale; only his stride differs. No text, no numbers, no logos anywhere (also no display text on the treadmill).

Scene: walking on a light grey treadmill set to a clearly visible incline (about 10 percent), upright posture, NOT holding the handrails, natural arm swing. Camera: true SIDE view from his left.

LEFT panel: left leg forward.
RIGHT panel: right leg forward, arms swinging the other way.

Blue (#2F6FD6) ONLY on glutes, hamstrings, quadriceps and calves; everything else grey.
```

### `mobilnosc.png`: mobilność bioder i odcinka piersiowego (dwa ćwiczenia, bez filmu)

Panele to dwa różne ćwiczenia, a nie start i koniec ruchu. Aplikacja pokaże je obok siebie albo po kolei.

```
Create a NEW image with TWO PANELS SIDE BY SIDE (left half and right half), using the attached man as the reference character: same face, hair, anatomical écorché muscle style with grey muscles, black shorts, black shoes, pure white background, soft studio light. Same scale in both panels. No divider line. No text, no numbers, no logos anywhere.

LEFT panel: 90/90 hip stretch: sitting on the floor, front leg bent 90 degrees in front, back leg bent 90 degrees to the side behind, torso upright leaning slightly over the front shin, hands lightly on the floor. Three-quarter front view. Blue (#2F6FD6) on glutes and hip rotators.
RIGHT panel: thoracic "open book": lying on his left side on the floor, knees bent 90 degrees and stacked, the top (right) arm rotated open to the other side, chest turning towards the ceiling, eyes following the hand, knees together on the floor. Three-quarter view from above. Blue (#2F6FD6) on upper back and chest.

Everything not listed stays grey.
```

## Na koniec: przysiad jeszcze raz

Obecny przysiad ma głębokość „na styk” i dziwnie ułożone ręce. Gdy reszta będzie gotowa, wygeneruj go ponownie i zapisz jako `przysiad.png`. Film przeliczy się w następnej partii.

```
IMPORTANT: the RIGHT panel must be an exact copy of the LEFT panel: same equipment, same position and rotation of every object, same camera; ONLY the moving body parts change. If you overlay the two panels, the equipment and the floor must match perfectly. No divider line between the panels.

Create a NEW image with TWO PANELS SIDE BY SIDE (left half and right half), using the attached man as the reference character: same face, hair, anatomical écorché muscle style with grey muscles, black shorts, black shoes, pure white background, soft studio light. Both panels: exactly the same scene, camera angle, distance and scale; only his pose differs. No text, no numbers, no logos anywhere (also none on plates).

Scene: competition back squat in a light grey squat rack WITHOUT safety arms (only the two uprights and the bar hooks). Barbell with two identical matte black plates (no clips, no markings) resting on his upper back BEHIND the neck. Camera: true SIDE PROFILE from his left at hip height (we see his face from the side and the full line of his back). His left hand is clearly visible gripping the bar just outside the shoulder, the elbow points DOWN and BACK under the bar; the arm does not wrap around the chest.

LEFT panel: TOP position, standing fully upright.
RIGHT panel: BOTTOM of a DEEP competition squat: the thighs slope DOWNWARD from the knee to the hip, the hip crease is clearly LOWER than the top of the knee, buttocks well below knee height. Knees forward over the toes, heels flat, the bar directly above the middle of the foot, back flat, chest up, torso leaning forward naturally.

Blue (#2F6FD6) ONLY on quadriceps, glutes and lower back erectors; everything else grey, including abs and obliques.
```

## Gdy partia jest gotowa

Napisz agentowi, które pliki są w `exports\technika\`. Agent:

1. Potnie obrazki na klatki wyrównane po sprzęcie (WebP, ok. 15–20 kB na klatkę), obejrzy je i wskaże do poprawy (numer panelu i co poprawić).
2. Wepnie klatki w aplikację, więc ćwiczenie od razu ma przełączane klatki.
3. Przygotuje notatnik Colab na całą partię. Ty: otwierasz link, wybierasz kartę **L4** albo **A100** (nie T4), włączasz dużą pamięć RAM i klikasz **Uruchom wszystko**. Na L4 to ok. 30 min na ćwiczenie plus kilka minut ładowania modelu, czyli 2–3 jednostki obliczeniowe na godzinę. Na końcu pobierasz paczkę filmów i wrzucasz ją do `exports\technika\`. Potem **Odłącz i usuń środowisko**, żeby nie zjadało jednostek.
4. Wepnie filmy i ustawi pauzy oraz tempo wariantów.
