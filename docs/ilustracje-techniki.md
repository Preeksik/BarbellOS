# Ilustracje techniki: prompt do czatu Gemini

Ilustracje do przycisku „Technika” przy ćwiczeniach generujesz sam w zwykłym czacie [gemini.google.com](https://gemini.google.com) (subskrypcja Google AI Pro). Agent potem je przycina, zmniejsza i wpina w aplikację. Plan ćwiczeń: stan z 27.11.2026, 26 ćwiczeń, razem 44 obrazki.

## Model

Wybierz **Neon**, czyli najnowszy model dostępny w planie Pro. Carbon wymaga planu Ultra.

Wybór modelu ma niewielkie znaczenie dla wyglądu, bo obrazki rysuje osobne narzędzie obrazkowe (Nano Banana), takie samo w Neonie i Argonie. Model czatu odpowiada za trzymanie się listy, kolejności i zasad, a w tym nowszy Neon jest lepszy. Jeśli Neon zamiast obrazka odpowie tekstem, włącz w polu wpisywania narzędzie **„Utwórz obraz”** i wyślij ponownie.

## Jak to działa

1. Nowa rozmowa, model Neon. Wklejasz **cały prompt** z sekcji niżej i wysyłasz. Gemini generuje obrazek nr 1 (postać wzorcową) i podaje jego nazwę.
2. Pobierasz obrazek (najedź → pobierz), zmieniasz nazwę na podaną i przenosisz do `C:\Users\adria\Desktop\BarbellOS\exports\technika\`.
3. Piszesz **`Generate image #2 now.`** (potem `#3`, `#4`…). Samo „dalej” nie wystarcza: Gemini odpowiada wtedy „Jako model językowy nie jestem do tego przeznaczony”, bo nie uruchamia narzędzia obrazkowego. Gdy mimo to odmawia, włącz w polu wpisywania **Narzędzia → „Utwórz obraz”** i wyślij ponownie, a w ostateczności wklej opis tej jednej klatki z listy z dopiskiem `Generate this image:`.
4. Klatka wyszła źle? Piszesz **`popraw: <co poprawić>`**. Gemini generuje ją jeszcze raz, a dopiero potem idziesz do następnego numeru.
5. Limit albo rozmowa się sypie: nowa rozmowa, dołączasz `00-postac.png` (spinacz), wklejasz cały prompt jeszcze raz i dopisujesz na końcu `Zacznij od obrazka nr <numer>`.

Zmienianie nazw plików jest wygodne, ale nieobowiązkowe. Wystarczy, że pobierasz po kolei: agent dopasuje pliki po kolejności i po tym, co na nich widać.

**Kiedy poprawiać:**

- postać albo styl wyraźnie inne niż na obrazku nr 1;
- błąd anatomii (dodatkowe palce, ręka przez sztangę, dziwne stawy);
- błąd techniki (płytki przysiad, pośladki nad ławką, okrągłe plecy w martwym);
- tekst, liczby albo logo na obrazku;
- coś ucięte przy krawędzi.

Znaczek Gemini w rogu nie przeszkadza, agent go przytnie.

**Jak to wygląda w aplikacji:** każde ćwiczenie ma 2 klatki (start i koniec ruchu), które płynnie się przełączają. Przysiad z pauzą, przysiad tempo, ława T&G i ława z pauzą 3 s wyglądają tak samo jak bój podstawowy, więc korzystają z jego klatek, a aplikacja pokazuje na dolnej klatce odliczanie („2 s”, „3 s”, „1 s”) i podpis. Spoto, piny, Larsen, wąski chwyt i RDL wyglądają inaczej, więc mają własne klatki.

## Cały prompt (skopiuj od „You are…” do końca bloku)

```
You are helping me create a consistent series of exercise technique illustrations for my strength training app. We will make exactly 44 images, ONE image per message, in the order of the list below.

HOW WE WORK
- Now generate image #1 only. After that, every time I write "Generate image #<n> now", generate exactly that image from the list. Never generate more than one image per message and never skip an image.
- Before each image, write one short line: "#<number> <file name>". Nothing else.
- If I write "popraw: <instructions>", regenerate the last image with that fix, keeping everything else identical. Then wait for my next message.
- If I write "Zacznij od obrazka nr <n>", the attached image is image #1 (the reference character); continue the list from image #n.

STYLE (identical in every image)
- Semi-realistic 3D anatomical illustration, like a medical anatomy model. The SAME fit adult man in every image: realistic, clearly defined muscles rendered in light neutral grey (visible muscle shapes and fibres, no skin texture, no tattoos), short dark hair, calm neutral face, plain black athletic shorts, plain black flat training shoes.
- Pure white background, soft even studio lighting, soft shadow on the floor.
- Working muscles of each exercise highlighted in one saturated blue (#2F6FD6); all other muscles stay grey.
- Equipment: matte black weight plates and dumbbells WITHOUT any markings, steel barbell, light grey rack, benches and machines.
- Square 1:1 image, at least 1024 x 1024 px. The whole body and all equipment fully in frame with a margin; nothing cut off at the edges.
- NO text, letters, numbers, logos or labels anywhere in the image (also none on plates, dumbbells or machines).
- Correct, safe competition-standard technique and correct anatomy (five fingers, natural joints, hands really holding the bar).
- Each exercise has two images (start and end of the movement). The second image MUST use exactly the same camera angle, distance, equipment and position in the frame as the first one; only the body position changes.

THE LIST
#1 00-postac — Reference character. Standing upright, relaxed athletic stance, full body, three-quarter front view. No equipment, no blue highlights.

SQUAT (camera for all squat images: three-quarter side view from the front-left at hip height, knee and hip angles clearly visible). Blue: quadriceps, glutes, adductors, lower back erectors.
#2 przysiad-1-gora — Competition back squat, TOP: standing fully upright inside a squat rack, loaded barbell on the upper back (traps, below the neck), hands just outside the shoulders, elbows down and back, feet shoulder-width, toes slightly out, chest up.
#3 przysiad-2-dol — Same scene, BOTTOM: hip crease clearly LOWER than the top of the knee (below parallel), knees forward in line with the toes, heels flat, bar directly over mid-foot, back flat and tight, chest up.

BENCH PRESS (camera: three-quarter view from slightly above, from the side of his feet; bar path, arch and feet visible). Blue: pectorals, front shoulders, triceps.
#4 lawa-1-gora — Competition bench press, TOP: lying on a flat bench under a rack, arms straight, loaded bar locked out above the shoulders, grip slightly wider than shoulders, shoulder blades pulled together, moderate upper-back arch, buttocks ON the bench, both feet flat on the floor.
#5 lawa-2-klatka — Same scene: bar paused motionless ON the lower chest, forearms vertical, elbows about 45 degrees from the torso, buttocks on the bench, feet flat.

DEADLIFT (camera: pure side view from his left at hip height, no rack). Blue: glutes, hamstrings, lower back erectors, quadriceps, upper traps.
#6 martwy-1-start — Conventional deadlift, START: loaded bar on the floor over mid-foot, shins touching the bar, straight arms gripping just outside the legs, hips higher than knees, shoulders slightly in front of the bar, back flat and neutral.
#7 martwy-2-wyprost — Same scene, LOCKOUT: fully upright, hips and knees fully extended, shoulders back, bar hanging in straight arms at the top of the thighs, no leaning back.

SQUAT FROM PINS (same camera as the squat images). Blue: quadriceps, glutes, adductors, lower back erectors.
#8 piny-1-gora — Standing upright in the rack with the bar on the upper back; the rack's two horizontal safety pins clearly visible, set low at the bar height of a below-parallel squat.
#9 piny-2-dol — Same scene: bottom of the squat with the bar resting completely still ON the safety pins, hips below parallel, back flat, body tight.

LARSEN PRESS (same camera as the bench press images). Blue: pectorals, front shoulders, triceps, abdominals.
#10 larsen-1-gora — Bench press TOP with arms locked out, but both legs straight and lifted OFF the floor, extended forward in the air at about bench height, buttocks on the bench.
#11 larsen-2-klatka — Same scene: bar paused motionless on the lower chest, forearms vertical, legs still straight in the air.

CLOSE-GRIP BENCH PRESS (camera: three-quarter view from slightly above and from the side of his head, so the narrow grip is clearly visible). Blue: triceps, pectorals, front shoulders.
#12 waski-1-gora — Flat bench, bar locked out, hands at shoulder width (clearly narrower than a normal bench grip), elbows close to the body, feet flat.
#13 waski-2-klatka — Same scene: bar paused motionless on the lower chest, elbows tucked close to the torso.

SPOTO PRESS (same scene and camera as image #4). Blue: pectorals, front shoulders, triceps.
#14 spoto-2-nad-klatka — The bar held motionless about 2 cm ABOVE the chest, clearly NOT touching it, a small visible gap between bar and chest, forearms vertical, buttocks on the bench, feet flat.

ROMANIAN DEADLIFT (same camera as the deadlift images). Blue: hamstrings, glutes, lower back erectors.
#15 rdl-1-gora — Standing upright holding the loaded bar in straight arms at the top of the thighs, knees slightly unlocked.
#16 rdl-2-dol — Same scene: hips pushed far back, knees slightly bent in the same position as before, back flat, bar slid along the legs to mid-shin, plates NOT touching the floor, strong hamstring stretch.

LEG PRESS 45 DEGREES (camera: side view from his left). Blue: quadriceps, glutes.
#17 suwnica-1-gora — Seated in a 45-degree leg press machine, back flat on the pad, feet shoulder-width on the platform, legs almost straight (knees not locked).
#18 suwnica-2-dol — Same scene: knees deeply bent towards the chest, lower back still flat on the pad, heels on the platform.

LYING LEG CURL (camera: side view). Blue: hamstrings, calves.
#19 uginanie-nog-1-start — Lying face down on a leg curl machine, roller pad just above the heels, legs straight, hips pressed into the pad, hands on the handles.
#20 uginanie-nog-2-skurcz — Same scene: knees bent 90 degrees or more, heels pulled towards the glutes, hips still on the pad.

BACK EXTENSION (camera: side view). Blue: glutes, hamstrings, lower back erectors.
#21 hiperekstensje-1-dol — 45-degree Roman chair, hips on the pad, ankles under the rollers, a plate held against the chest, torso bent down at the hips with a neutral back.
#22 hiperekstensje-2-gora — Same scene: torso raised until the body is one straight line from heels to head, no overextension, plate still against the chest.

CHEST-SUPPORTED DUMBBELL ROW (camera: three-quarter side view). Blue: lats, rhomboids, traps, rear shoulders, biceps.
#23 wioslowanie-1-dol — Chest down on a 30-degree incline bench, feet on the floor, a dumbbell in each hand, arms hanging straight down.
#24 wioslowanie-2-gora — Same scene: dumbbells pulled up to the hips, elbows driven back past the torso, shoulder blades squeezed, chest on the bench.

WEIGHTED PULL-UP (camera: three-quarter view from behind-left, back visible). Blue: lats, biceps, middle back.
#25 podciaganie-1-zwis — Hanging from a pull-up bar, overhand grip slightly wider than shoulders, arms fully straight, a dumbbell held between the feet, legs slightly bent.
#26 podciaganie-2-gora — Same scene: chin above the bar, chest close to the bar, elbows pulled down to the sides, dumbbell still between the feet.

FACE PULL (camera: side view from his left). Blue: rear shoulders, rhomboids, middle traps, rotator cuff.
#27 facepull-1-start — Standing facing a cable tower, pulley at face height, rope attachment in both hands, arms straight in front.
#28 facepull-2-koniec — Same scene: rope pulled to the face, hands next to the ears, elbows high and wide, upper arms rotated outward.

BENT-OVER REVERSE DUMBBELL FLY (camera: three-quarter front view). Blue: rear shoulders, rhomboids, middle traps.
#29 odwrotne-rozpietki-1-dol — Bent forward at the hips, flat back, torso almost parallel to the floor, knees slightly bent, light dumbbells hanging below the chest, palms facing each other, elbows slightly bent.
#30 odwrotne-rozpietki-2-gora — Same scene: dumbbells raised out to the sides to shoulder height in a wide arc, shoulder blades squeezed.

INCLINE DUMBBELL PRESS (camera: three-quarter view from the side of his feet). Blue: upper chest, front shoulders, triceps.
#31 skos-hantle-1-dol — Bench at 30 degrees, dumbbells beside the upper chest, elbows about 45 degrees from the torso, feet flat.
#32 skos-hantle-2-gora — Same scene: dumbbells pressed up over the upper chest, arms straight, dumbbells close but not touching.

SINGLE-ARM CABLE TRICEPS PUSHDOWN (camera: side view from his left). Blue: triceps of the working arm.
#33 triceps-1-start — Standing facing a cable tower with a high pulley, single handle in the LEFT hand, upper arm tight against the side, elbow bent about 90 degrees, forearm about parallel to the floor, other hand relaxed.
#34 triceps-2-wyprost — Same scene: working elbow fully straight, handle pushed down next to the thigh, upper arm still against the side.

DUMBBELL BICEPS CURL (camera: three-quarter front view). Blue: biceps, forearm flexors.
#35 biceps-1-dol — Standing upright, a dumbbell in each hand, arms straight at the sides, palms facing forward.
#36 biceps-2-gora — Same scene: both dumbbells curled to shoulder height, elbows close to the sides, no swinging.

AB WHEEL ROLLOUT (camera: side view from his left). Blue: abdominals, obliques.
#37 rollout-1-start — Kneeling on the floor holding an ab wheel under the shoulders, arms straight, back flat, abs tight.
#38 rollout-2-wyciagniety — Same scene: rolled forward until the body is almost straight and low over the floor, arms extended in front, hips NOT sagging, one straight line from knees to shoulders.

HANGING LEG RAISE (camera: side view from his left). Blue: abdominals, hip flexors.
#39 unoszenie-nog-1-zwis — Hanging from a pull-up bar, straight arms, overhand grip, legs straight down, not swinging.
#40 unoszenie-nog-2-gora — Same scene: knees raised up towards the chest, pelvis tilted up, not swinging.

INCLINE TREADMILL WALK (camera: side view from his left). Blue: glutes, hamstrings, calves, quadriceps.
#41 bieznia-1-krok — Walking on a treadmill set to a clearly visible incline (about 10 percent), upright, NOT holding the handrails, natural arm swing, left leg forward.
#42 bieznia-2-krok — Same scene: the opposite step, right leg forward, arms swinging the other way.

MOBILITY (two separate stretches, each its own camera).
#43 mobilnosc-1-biodra — 90/90 hip stretch: sitting on the floor, front leg bent 90 degrees in front, back leg bent 90 degrees to the side behind, torso upright leaning slightly over the front shin, hands lightly on the floor. Three-quarter front view. Blue: glutes, hip rotators.
#44 mobilnosc-2-piersiowy — Thoracic "open book": lying on the left side, knees bent 90 degrees and stacked, the top (right) arm rotated open to the other side, chest turning towards the ceiling, eyes following the hand, knees together on the floor. Three-quarter view from above. Blue: upper back, chest.

Start now with image #1 only.
```

## Gdy skończysz

Napisz agentowi, że pliki są w `exports/technika/`. Agent:

1. Sprawdzi, czy jest 44 plików (z nazwami albo w kolejności pobierania).
2. Przytnie znaczek Gemini i zmniejszy klatki do formatu WebP (ok. 50–80 kB na klatkę).
3. Obejrzy klatki i wskaże te do poprawy (numer i co poprawić).
4. Wepnie je w aplikację w miejsce obecnego ludzika, z odliczaniem pauz w wariantach.
