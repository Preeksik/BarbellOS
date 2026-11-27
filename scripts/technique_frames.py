"""Tnie ilustrację z dwoma panelami (góra i dół ruchu) na dwie wyrównane klatki WebP.

Ilustracje generuje właściciel w czacie Gemini (docs/ilustracje-techniki.md): jeden obrazek,
dwa panele obok siebie, ta sama kamera. Skrypt:
1. znajduje pionową przerwę między panelami (najdłuższy pas prawie białych kolumn w środku),
2. wyrównuje prawy panel do lewego po dolnym pasie obrazu (podłoga i stojak), żeby sprzęt
   nie skakał między klatkami,
3. przycina obie klatki do wspólnego prostokąta z treścią, dodaje biały margines,
4. zapisuje WebP o wysokości `--height` do web/public/technique/.

Użycie (Pillow w osobnym środowisku, nie jest zależnością aplikacji):
    python scripts/technique_frames.py exports/technika/przysiad.png przysiad
"""

import argparse
import pathlib

from PIL import Image, ImageChops

WHITE_LEVEL = 238  # jaśniejsze piksele traktujemy jak tło
OUT_DIR = pathlib.Path(__file__).resolve().parents[1] / "web" / "public" / "technique"


def column_ink(img: Image.Image) -> list[int]:
    """Ile „nie-białych" pikseli ma każda kolumna."""
    gray = img.convert("L").point(lambda v: 255 if v < WHITE_LEVEL else 0)
    w, h = gray.size
    data = gray.load()
    return [sum(1 for y in range(0, h, 2) if data[x, y]) for x in range(w)]


def find_gap(img: Image.Image) -> tuple[int, int]:
    """Najdłuższy pas pustych kolumn w środkowej połowie obrazu: (początek, koniec)."""
    w = img.width
    ink = column_ink(img)
    best, start = (w // 2, w // 2), None
    for x in range(w // 4, 3 * w // 4):
        empty = ink[x] <= 2
        if empty and start is None:
            start = x
        if (not empty or x == 3 * w // 4 - 1) and start is not None:
            if x - start > best[1] - best[0]:
                best = (start, x)
            start = None
    return best


def best_offset(left: Image.Image, right: Image.Image, band: tuple[int, int]) -> int:
    """Przesunięcie w poziomie, przy którym dolne pasy obu paneli najlepiej się pokrywają."""
    y0, y1 = band
    a = left.convert("L").crop((0, y0, left.width, y1))
    b = right.convert("L").crop((0, y0, right.width, y1))
    best, best_diff = 0, None
    for dx in range(-200, 201, 2):
        shifted = ImageChops.offset(b, dx, 0)
        diff = ImageChops.difference(a, shifted).point(lambda v: v // 8)
        score = sum(i * n for i, n in enumerate(diff.histogram()))
        if best_diff is None or score < best_diff:
            best, best_diff = dx, score
    return best


def content_box(img: Image.Image) -> tuple[int, int, int, int]:
    mask = img.convert("L").point(lambda v: 255 if v < WHITE_LEVEL else 0)
    return mask.getbbox() or (0, 0, img.width, img.height)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("source", type=pathlib.Path)
    parser.add_argument("name", help="nazwa ćwiczenia w plikach, np. przysiad")
    parser.add_argument("--height", type=int, default=900)
    parser.add_argument("--quality", type=int, default=78)
    args = parser.parse_args()

    img = Image.open(args.source).convert("RGB")
    gap = find_gap(img)
    mid = (gap[0] + gap[1]) // 2
    width = min(mid, img.width - mid)
    left = img.crop((mid - width, 0, mid, img.height))
    right = img.crop((mid, 0, mid + width, img.height))
    floor = (int(img.height * 0.70), int(img.height * 0.95))
    dx = best_offset(left, right, floor)
    right = ImageChops.offset(right, dx, 0)
    if dx > 0:
        right.paste((255, 255, 255), (0, 0, dx, right.height))
    elif dx < 0:
        right.paste((255, 255, 255), (right.width + dx, 0, right.width, right.height))

    boxes = [content_box(left), content_box(right)]
    box = (
        min(b[0] for b in boxes),
        min(b[1] for b in boxes),
        max(b[2] for b in boxes),
        max(b[3] for b in boxes),
    )
    margin = int((box[3] - box[1]) * 0.04)
    box = (
        max(0, box[0] - margin),
        max(0, box[1] - margin),
        min(width, box[2] + margin),
        min(img.height, box[3] + margin),
    )
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for i, panel in enumerate((left, right), start=1):
        frame = panel.crop(box)
        scale = args.height / frame.height
        frame = frame.resize((round(frame.width * scale), args.height), Image.LANCZOS)
        out = OUT_DIR / f"{args.name}-{i}.webp"
        frame.save(out, "WEBP", quality=args.quality, method=6)
        print(f"{out.name}: {frame.width}×{frame.height}, {out.stat().st_size // 1024} kB")
    print(f"przerwa {gap}, przesunięcie prawego panelu {dx} px, kadr {box}")


if __name__ == "__main__":
    main()
