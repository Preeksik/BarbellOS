"""Próba C: ile produktów z własnej kuchni jest w Open Food Facts i z jakimi danymi.

Użycie (w katalogu backend, z aktywnym środowiskiem wirtualnym):

    python ../scripts/off_coverage.py ../scripts/kody.txt

Plik z kodami: jeden kod EAN w linii, po kodzie opcjonalnie własna nazwa produktu.
Linie zaczynające się od # są pomijane. Wzór: scripts/kody.example.txt
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.config import get_settings  # noqa: E402
from app.core.barcode import is_valid_ean  # noqa: E402
from app.off.client import fetch_product  # noqa: E402

LABEL_FIELDS = ("kcal", "protein_g", "fat_g", "sat_fat_g", "carbs_g", "sugars_g", "salt_g")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    settings = get_settings()
    rows = []
    for line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        code, _, own_name = line.partition(" ")
        if not is_valid_ean(code):
            rows.append((code, own_name, "BŁĘDNY KOD", "", 0))
            continue
        try:
            draft = fetch_product(code, settings.off_base_url, settings.off_user_agent)
        except Exception as exc:  # sieć bywa kapryśna: pokazujemy błąd i idziemy dalej
            rows.append((code, own_name, f"BŁĄD: {exc}", "", 0))
            continue
        if draft is None:
            rows.append((code, own_name, "BRAK W OFF", "", 0))
        else:
            missing = [f for f in LABEL_FIELDS if draft.macros[f] is None]
            status = "komplet" if not missing else "brakuje: " + ", ".join(missing)
            rows.append((code, own_name or draft.name, status, draft.name, len(draft.micros)))
        time.sleep(1)  # OFF prosi o umiar w liczbie zapytań

    print(f"{'kod':<15}{'produkt':<34}{'dane z etykiety':<34}mikro")
    for code, name, status, _, micros in rows:
        print(f"{code:<15}{name[:32]:<34}{status[:32]:<34}{micros or ''}")

    total = len(rows)
    found = [r for r in rows if r[3]]
    complete = [r for r in found if r[2] == "komplet"]
    with_micros = [r for r in found if r[4]]
    print(
        f"\nRazem: {total}. W OFF: {len(found)}. Z kompletem 7 wartości z etykiety: "
        f"{len(complete)}. Z jakimkolwiek mikroskładnikiem: {len(with_micros)}."
    )


if __name__ == "__main__":
    main()
