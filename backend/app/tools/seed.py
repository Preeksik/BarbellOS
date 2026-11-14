"""Wgrywa dane startowe z katalogu seed/.  Użycie:  python -m app.tools.seed

Bezpieczne do wielokrotnego uruchamiania: słownik mikroskładników jest aktualizowany,
a plan treningowy wgrywany tylko wtedy, gdy plik istnieje i planu jeszcze nie ma.
"""

import json
import os
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Nutrient, Plan, PlanSettings
from app.db.session import get_engine

DEFAULT_SEED_DIR = Path(__file__).resolve().parents[3] / "seed"


def seed_nutrients(db: Session, seed_dir: Path) -> int:
    rows = json.loads((seed_dir / "nutrients.json").read_text(encoding="utf-8"))["nutrients"]
    for row in rows:
        db.merge(Nutrient(**row))
    return len(rows)


def seed_plan(db: Session, seed_dir: Path) -> str:
    path = seed_dir / "plan_amp_2027.json"
    if not path.exists():
        return "pominięty (brak pliku; plan można wgrać później)"
    data = json.loads(path.read_text(encoding="utf-8"))
    name = data["meta"]["name"]
    if db.scalars(select(Plan).where(Plan.name == name)).first():
        return "już jest w bazie"
    plan = Plan(name=name, data=data)
    db.add(plan)
    db.flush()
    db.add(PlanSettings(plan_id=plan.id, tm={}, adj={}))
    return f"wgrany ({len(data['weeks'])} tygodni)"


def main() -> None:
    seed_dir = Path(os.environ.get("SEED_DIR", DEFAULT_SEED_DIR))
    with Session(get_engine()) as db:
        count = seed_nutrients(db, seed_dir)
        plan_status = seed_plan(db, seed_dir)
        db.commit()
    print(f"Mikroskładniki: {count}. Plan treningowy: {plan_status}.")


if __name__ == "__main__":
    main()
