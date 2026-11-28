"""Rysuje szare manekiny w pozach ćwiczeń: szkic pozy dla modelu obrazów (Qwen-Image-Edit).

Gemini nie trzyma się techniki (sztanga przed stopami, talerze w powietrzu), więc pozę
i położenie sprzętu dyktuje kod, a model tylko maluje postać w tym ułożeniu
(docs/ilustracje-techniki.md, droga B). Geometria to ta sama mechanika co w ludziku
(web/src/features/training/technique/skeleton.ts): stałe długości kości, sztanga nad
środkiem stopy, stawy pośrednie z kinematyki odwrotnej dwóch kości.

Obie klatki ćwiczenia mają to samo płótno i tę samą skalę, a stopy stoją w tym samym
miejscu, więc wyrównanie klatek wychodzi z konstrukcji.

Użycie (Pillow w osobnym środowisku, nie jest zależnością aplikacji):
    python scripts/technique_pose.py martwy rdl
Wynik: scripts/colab/szkice/<nazwa>-1.png i <nazwa>-2.png (start i koniec ruchu).
"""

import argparse
import math
import pathlib
from dataclasses import dataclass

from PIL import Image, ImageDraw

OUT_DIR = pathlib.Path(__file__).resolve().parent / "colab" / "szkice"

# Długości w centymetrach, jak w skeleton.ts.
SHIN, THIGH, TORSO = 42.0, 44.0, 52.0
NECK, HEAD = 9.0, 10.0
UPPER_ARM, FOREARM = 31.0, 33.0
ANKLE_HEIGHT, TOE, HEEL = 8.0, 18.0, 6.0
PLATE_RADIUS = 22.5  # talerz zawodniczy ma 45 cm średnicy
MIDFOOT_X = 100.0
LOCKOUT_BAR_Y = ANKLE_HEIGHT + SHIN + THIGH + TORSO - UPPER_ARM - FOREARM

# Płótno: kwadrat 1024 px, 1 cm = 4,6 px, podłoga 80 px nad dolną krawędzią.
SIZE = 1024
SCALE = 4.6
FLOOR_Y = SIZE - 80
SUPERSAMPLE = 2


@dataclass(frozen=True)
class Vec:
    x: float
    y: float

    def __add__(self, o: "Vec") -> "Vec":
        return Vec(self.x + o.x, self.y + o.y)

    def __sub__(self, o: "Vec") -> "Vec":
        return Vec(self.x - o.x, self.y - o.y)

    def __mul__(self, k: float) -> "Vec":
        return Vec(self.x * k, self.y * k)

    def length(self) -> float:
        return math.hypot(self.x, self.y)


@dataclass(frozen=True)
class Pose:
    ankle: Vec
    knee: Vec
    hip: Vec
    shoulder: Vec
    head: Vec
    elbow: Vec
    hand: Vec
    bar: Vec


def two_bone(a: Vec, target: Vec, l1: float, l2: float, bend: int) -> Vec:
    """Staw pośredni dwóch kości; bend = 1 zgina w lewo od kierunku a → cel."""
    d = min(max((target - a).length(), abs(l1 - l2) + 1e-6), l1 + l2 - 1e-6)
    base = math.atan2(target.y - a.y, target.x - a.x)
    inner = math.acos((l1 * l1 + d * d - l2 * l2) / (2 * l1 * d))
    angle = base + bend * inner
    return a + Vec(math.cos(angle) * l1, math.sin(angle) * l1)


def head_from(hip: Vec, shoulder: Vec, forward: float) -> Vec:
    along = (shoulder - hip) * (1 / TORSO)
    ahead = Vec(along.y, -along.x)
    return shoulder + along * (NECK + HEAD) + ahead * (forward * HEAD)


def hinge_pose(bar_y: float, shin_deg: float) -> Pose:
    """Martwy ciąg i RDL: sztanga w prostych rękach nad środkiem stopy (jak hingePose)."""
    ankle = Vec(MIDFOOT_X - 6, ANKLE_HEIGHT)
    bar = Vec(MIDFOOT_X + 1, bar_y)
    rad = math.radians(shin_deg)
    knee = ankle + Vec(math.sin(rad), math.cos(rad)) * SHIN
    shoulder_target = Vec(bar.x + 3, bar.y + UPPER_ARM + FOREARM)
    hip = two_bone(knee, shoulder_target, THIGH, TORSO, 1)
    along = (shoulder_target - hip) * (1 / (shoulder_target - hip).length())
    shoulder = hip + along * TORSO
    elbow = two_bone(shoulder, bar, UPPER_ARM, FOREARM, -1)
    return Pose(ankle, knee, hip, shoulder, head_from(hip, shoulder, 0.6), elbow, bar, bar)


# Start i koniec ruchu, jak w moves.ts
# (martwy: piszczel 17° → 1°, RDL: od wyprostu do połowy piszczeli).
POSES: dict[str, tuple[Pose, Pose]] = {
    "martwy": (hinge_pose(PLATE_RADIUS, 17), hinge_pose(LOCKOUT_BAR_Y, 1)),
    "rdl": (hinge_pose(LOCKOUT_BAR_Y, 2), hinge_pose(36, 9)),
}

SKIN = (178, 178, 178)
SKIN_FAR = (140, 140, 140)
OUTLINE = (95, 95, 95)
SHORTS = (45, 45, 45)
SHOE = (30, 30, 30)
PLATE = (25, 25, 25)
PLATE_FAR = (70, 70, 70)
STEEL = (150, 150, 150)
# Lekki skos kamery: bliższy talerz trochę bliżej widza (niżej i do przodu), dalszy za ciałem.
NEAR_SHIFT = Vec(3, -2)
FAR_SHIFT = Vec(-5, 2)


def to_px(p: Vec) -> tuple[float, float]:
    """Świat (cm, y w górę, twarz w +x) → piksele; lustro: postać patrzy w lewo jak u Gemini."""
    s = SCALE * SUPERSAMPLE
    return (SIZE * SUPERSAMPLE / 2 - (p.x - MIDFOOT_X) * s, FLOOR_Y * SUPERSAMPLE - p.y * s)


def capsule(
    draw: ImageDraw.ImageDraw, a: Vec, b: Vec, width_cm: float, fill, outline=OUTLINE
) -> None:
    w = width_cm * SCALE * SUPERSAMPLE
    o = 2 * SUPERSAMPLE
    (ax, ay), (bx, by) = to_px(a), to_px(b)
    for color, extra in ((outline, o), (fill, 0)):
        r = w / 2 + extra
        draw.line((ax, ay, bx, by), fill=color, width=int(2 * r))
        for x, y in ((ax, ay), (bx, by)):
            draw.ellipse((x - r, y - r, x + r, y + r), fill=color)


def disc(draw: ImageDraw.ImageDraw, c: Vec, radius_cm: float, fill, outline=OUTLINE) -> None:
    x, y = to_px(c)
    r = radius_cm * SCALE * SUPERSAMPLE
    draw.ellipse((x - r, y - r, x + r, y + r), fill=fill, outline=outline, width=2 * SUPERSAMPLE)


def shoe(draw: ImageDraw.ImageDraw, ankle: Vec) -> None:
    pts = [
        Vec(ankle.x - HEEL - 2, 0),
        Vec(ankle.x + TOE + 2, 0),
        Vec(ankle.x + TOE + 2, 4),
        Vec(ankle.x + 8, 9),
        Vec(ankle.x - 1, ANKLE_HEIGHT + 4),
        Vec(ankle.x - HEEL - 2, ANKLE_HEIGHT + 2),
    ]
    draw.polygon([to_px(p) for p in pts], fill=SHOE, outline=OUTLINE)


def render(pose: Pose) -> Image.Image:
    img = Image.new("RGB", (SIZE * SUPERSAMPLE, SIZE * SUPERSAMPLE), "white")
    d = ImageDraw.Draw(img)

    # Za ciałem: dalszy talerz i gryf.
    far, near = pose.bar + FAR_SHIFT, pose.bar + NEAR_SHIFT
    disc(d, far, PLATE_RADIUS, PLATE_FAR)
    capsule(d, far, near, 2.8, STEEL)

    # Dalsza noga i ręka lekko w tle (stopy na szerokość bioder, widać je tylko trochę).
    back = Vec(-2.5, 0.8)
    capsule(d, pose.ankle + back, pose.knee + back, 11, SKIN_FAR)
    capsule(d, pose.knee + back, pose.hip + back, 15, SKIN_FAR)
    shoe(d, pose.ankle + Vec(-3, 0))

    # Bliższa strona: noga, szorty, tułów, głowa, ręka.
    capsule(d, pose.ankle, pose.knee, 11, SKIN)
    capsule(d, pose.knee, pose.hip, 16, SKIN)
    capsule(d, pose.hip + (pose.knee - pose.hip) * 0.45, pose.hip, 18, SHORTS)
    shoe(d, pose.ankle)
    capsule(d, pose.hip, pose.shoulder, 23, SKIN)
    capsule(d, pose.hip, pose.hip + (pose.shoulder - pose.hip) * 0.18, 23.5, SHORTS)
    capsule(d, pose.shoulder, pose.head, 10, SKIN)
    disc(d, pose.head, 11, SKIN)
    # Wyraźny profil twarzy (nos i oko), żeby model nie wziął wyprostu za widok z przodu
    # (próba 28.11.2026: talerz na środku sylwetki wyglądał jak postać przodem).
    along = (pose.head - pose.shoulder) * (1 / (pose.head - pose.shoulder).length())
    ahead = Vec(along.y, -along.x)
    nose = pose.head + ahead * 10.5
    tip = nose + ahead * 4.5 - along * 1.5
    d.polygon(
        [to_px(tip), to_px(nose + along * 3.5), to_px(nose - along * 3)],
        fill=SKIN,
        outline=OUTLINE,
    )
    disc(d, pose.head + ahead * 6 + along * 2.5, 1.3, OUTLINE)
    capsule(d, pose.shoulder, pose.elbow, 9.5, SKIN)
    capsule(d, pose.elbow, pose.hand, 8, SKIN)

    # Przed ciałem: bliższy talerz z tuleją (na starcie martwego zasłania piszczele i dłoń).
    disc(d, near, PLATE_RADIUS, PLATE)
    disc(d, near, 2.6, STEEL)

    return img.resize((SIZE, SIZE), Image.LANCZOS)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    names = ", ".join(sorted(POSES))
    parser.add_argument("names", nargs="*", default=sorted(POSES), help=f"ćwiczenia: {names}")
    args = parser.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name in args.names:
        for i, pose in enumerate(POSES[name], start=1):
            path = OUT_DIR / f"{name}-{i}.png"
            render(pose).save(path, optimize=True)
            print(path.relative_to(OUT_DIR.parents[1]), f"sztanga {pose.bar.y:.0f} cm nad podłogą")


if __name__ == "__main__":
    main()
