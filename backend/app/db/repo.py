"""Operacje na bazie używane przez endpointy. Bez logiki obliczeniowej (ta jest w core/)."""

import uuid
from collections.abc import Iterable
from datetime import UTC, date, datetime

from sqlalchemy import func, insert, select
from sqlalchemy.orm import Session

from app.core.health_ingest import Sample
from app.core.nutrients import MACRO_KEYS, fill_implied_zeros
from app.db.models import AiRun, Food, FoodNutrient, HealthSample, MealEntry, Nutrient
from app.off.client import FoodDraft


def _utc_naive(dt: datetime) -> datetime:
    """Klucz porównania niezależny od bazy (SQLite zwraca daty bez strefy)."""
    return dt.astimezone(UTC).replace(tzinfo=None) if dt.tzinfo else dt


def upsert_health_samples(db: Session, samples: Iterable[Sample]) -> tuple[int, int]:
    """Wstawia nowe próbki i aktualizuje istniejące. Zwraca (wstawione, zaktualizowane)."""
    samples = list(samples)
    if not samples:
        return 0, 0
    kind, source = samples[0].type, samples[0].source
    starts = [s.starts_at for s in samples]
    existing = {
        _utc_naive(row.starts_at): row
        for row in db.scalars(
            select(HealthSample).where(
                HealthSample.type == kind,
                HealthSample.source == source,
                HealthSample.starts_at >= min(starts),
                HealthSample.starts_at <= max(starts),
            )
        )
    }
    new_rows: list[dict] = []
    updated = 0
    for s in samples:
        row = existing.get(_utc_naive(s.starts_at))
        if row is None:
            new_rows.append(
                {
                    "type": s.type,
                    "starts_at": s.starts_at,
                    "source": s.source,
                    "ends_at": s.ends_at,
                    "value": s.value,
                    "label": s.label,
                    "unit": s.unit,
                }
            )
            continue
        if (row.value, row.label, row.unit) != (s.value, s.label, s.unit):
            updated += 1
        row.ends_at, row.value, row.label, row.unit = s.ends_at, s.value, s.label, s.unit
    if new_rows:
        db.execute(insert(HealthSample), new_rows)
    db.commit()
    return len(new_rows), updated


def health_summary(db: Session) -> list[dict]:
    rows = db.execute(
        select(
            HealthSample.type,
            func.count(),
            func.max(HealthSample.starts_at),
            func.max(HealthSample.received_at),
        ).group_by(HealthSample.type)
    ).all()
    out = []
    for kind, count, last_start, last_received in rows:
        last = db.scalars(
            select(HealthSample)
            .where(HealthSample.type == kind, HealthSample.starts_at == last_start)
            .limit(1)
        ).first()
        out.append(
            {
                "type": kind,
                "count": count,
                "last_starts_at": last_start,
                "last_value": last.value if last else None,
                "last_label": last.label if last else None,
                "unit": last.unit if last else None,
                "source": last.source if last else None,
                "last_received_at": last_received,
            }
        )
    return sorted(out, key=lambda r: r["type"])


def find_food_by_barcode(db: Session, barcode: str) -> Food | None:
    return db.scalars(select(Food).where(Food.barcode == barcode)).first()


def food_micros(db: Session, food_id: int) -> list[FoodNutrient]:
    return list(db.scalars(select(FoodNutrient).where(FoodNutrient.food_id == food_id)))


def save_food_draft(db: Session, draft: FoodDraft) -> Food:
    food = Food(
        kind="packaged",
        barcode=draft.barcode,
        name=draft.name,
        brand=draft.brand,
        category=draft.category,
        serving_g=draft.serving_g,
        unit=draft.unit,
        origin="off",
        macro_source="label",
        source_updated_at=draft.source_updated_at,
        fetched_at=datetime.now(UTC),
        raw=draft.raw,
        **fill_implied_zeros(draft.macros),
    )
    db.add(food)
    db.flush()
    known = set(db.scalars(select(Nutrient.id)))
    for nutrient_id, amount in draft.micros.items():
        # Mikroskładnik spoza słownika pomijamy: słownik wgrywa się z seed/nutrients.json.
        if nutrient_id in known:
            db.add(
                FoodNutrient(
                    food_id=food.id, nutrient_id=nutrient_id, amount_per_100g=amount, source="label"
                )
            )
    db.commit()
    return food


def update_food(
    db: Session,
    food: Food,
    name: str,
    brand: str | None,
    serving_g: float | None,
    unit: str,
    macros: dict[str, float | None],
) -> Food:
    """Zapisuje wartości wpisane przez użytkownika. Produkt staje się zweryfikowany.

    Oryginalna odpowiedź źródła zostaje w `food.raw`, więc poprawkę da się porównać.
    Wpisy w dzienniku nie zmieniają się wstecz: przechowują własne, zamrożone wartości.
    """
    food.name, food.brand, food.serving_g, food.unit = name, brand, serving_g, unit
    for key in MACRO_KEYS:
        setattr(food, key, macros.get(key))
    food.macro_source = "user"
    food.verified_at = datetime.now(UTC)
    db.commit()
    return food


def create_user_food(
    db: Session,
    barcode: str,
    name: str,
    brand: str | None,
    serving_g: float | None,
    unit: str,
    macros: dict[str, float | None],
    origin: str,
) -> Food:
    """Produkt, którego nie było w żadnym źródle: wartości wpisał albo zatwierdził użytkownik.

    `origin` mówi, skąd wziął się szkic: `user` (wpisany ręcznie) albo `ai_label`
    (odczytany ze zdjęcia etykiety). W obu przypadkach wartości zatwierdził człowiek,
    więc `macro_source` to `user`, a produkt jest od razu zweryfikowany.
    """
    food = Food(
        kind="packaged",
        barcode=barcode,
        name=name,
        brand=brand,
        serving_g=serving_g,
        unit=unit,
        origin=origin,
        macro_source="user",
        verified_at=datetime.now(UTC),
        **{key: macros.get(key) for key in MACRO_KEYS},
    )
    db.add(food)
    db.commit()
    return food


def mark_food_verified(db: Session, food: Food) -> Food:
    """Użytkownik potwierdził, że wartości zgadzają się z etykietą."""
    food.verified_at = datetime.now(UTC)
    db.commit()
    return food


# ---------- AI ----------


def log_ai_run(
    db: Session,
    task: str,
    provider: str,
    model: str,
    status: str,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
) -> AiRun:
    """Zapisuje wywołanie modelu. Koszt zostaje pusty do czasu licznika kosztów (etap 2)."""
    run = AiRun(
        task=task,
        provider=provider,
        model=model,
        status=status,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )
    db.add(run)
    db.commit()
    return run


# ---------- dziennik ----------


def save_meal_entry(
    db: Session, entry: MealEntry | None, entry_id: uuid.UUID, **fields
) -> MealEntry:
    """Tworzy wpis albo nadpisuje pola istniejącego."""
    if entry is None:
        entry = MealEntry(id=entry_id, **fields)
        db.add(entry)
    else:
        for name, value in fields.items():
            setattr(entry, name, value)
    db.commit()
    db.refresh(entry)
    return entry


def delete_meal_entry(db: Session, entry_id: uuid.UUID) -> None:
    entry = db.get(MealEntry, entry_id)
    if entry is not None:
        db.delete(entry)
        db.commit()


def meal_entries_for_day(db: Session, day: date) -> list[MealEntry]:
    return list(
        db.scalars(select(MealEntry).where(MealEntry.date == day).order_by(MealEntry.created_at))
    )
