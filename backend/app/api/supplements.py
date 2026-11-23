"""Suplementacja (23.11.2026): lista suplementów i odhaczanie w Diecie.

Każdy zapis jest idempotentny, bo może czekać w kolejce offline (AGENTS.md, zasada 5):
suplement ma UUID z telefonu, a stan dnia zapisuje się w całości (lista wziętych).
"""

import datetime as dt
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.deps import require_user
from app.core.supplements import HISTORY_DAYS, as_yesterday, last_days, streak, supplement_errors
from app.db.models import Supplement, SupplementIntake, utcnow
from app.db.session import get_db

router = APIRouter(
    prefix="/api/supplements", tags=["supplements"], dependencies=[Depends(require_user)]
)

STREAK_LOOKBACK_DAYS = 366  # seria dłuższa niż rok i tak wyświetla się jako „365+"


class SupplementIn(BaseModel):
    name: str = Field(max_length=200)
    dose: str | None = Field(default=None, max_length=200)


class SupplementDayItem(BaseModel):
    id: uuid.UUID
    name: str
    dose: str | None
    taken: bool
    streak: int  # dni z rzędu do tego dnia (bez dziś, jeśli jeszcze nie wzięty)
    last7: list[bool]  # ostatnie 7 dni, od najstarszego


class SupplementDayOut(BaseModel):
    date: dt.date
    supplements: list[SupplementDayItem]
    taken_ids: list[uuid.UUID]
    yesterday_ids: list[uuid.UUID]  # wzięte dzień wcześniej: podgląd „To co wczoraj"


class DayIn(BaseModel):
    taken_ids: list[uuid.UUID]


def _active(db: Session) -> list[Supplement]:
    return list(
        db.scalars(
            select(Supplement)
            .where(Supplement.archived_at.is_(None))
            .order_by(Supplement.created_at, Supplement.name)
        )
    )


def _taken_on(db: Session, day: dt.date) -> set[uuid.UUID]:
    return set(
        db.scalars(select(SupplementIntake.supplement_id).where(SupplementIntake.date == day))
    )


def _set_day(db: Session, day: dt.date, wanted: list[uuid.UUID]) -> None:
    known = {s.id for s in db.scalars(select(Supplement).where(Supplement.id.in_(wanted)))}
    if missing := [str(i) for i in wanted if i not in known]:
        raise HTTPException(404, f"Nie ma suplementów: {', '.join(missing)}.")
    current = _taken_on(db, day)
    db.execute(
        delete(SupplementIntake).where(
            SupplementIntake.date == day, SupplementIntake.supplement_id.not_in(wanted)
        )
    )
    db.add_all(
        SupplementIntake(date=day, supplement_id=i)
        for i in dict.fromkeys(wanted)
        if i not in current
    )
    db.commit()


@router.get("/day/{day}", response_model=SupplementDayOut)
def get_day(day: dt.date, db: Session = Depends(get_db)) -> SupplementDayOut:
    """Lista suplementów z tym, co wzięte w `day`, serią dni i ostatnim tygodniem."""
    supplements = _active(db)
    rows = db.execute(
        select(SupplementIntake.supplement_id, SupplementIntake.date).where(
            SupplementIntake.date <= day,
            SupplementIntake.date > day - dt.timedelta(days=STREAK_LOOKBACK_DAYS),
        )
    ).all()
    taken_by: dict[uuid.UUID, set[dt.date]] = {}
    for supplement_id, taken_day in rows:
        taken_by.setdefault(supplement_id, set()).add(taken_day)
    active_ids = [s.id for s in supplements]
    yesterday = day - dt.timedelta(days=1)
    return SupplementDayOut(
        date=day,
        supplements=[
            SupplementDayItem(
                id=s.id,
                name=s.name,
                dose=s.dose,
                taken=day in taken_by.get(s.id, set()),
                streak=streak(taken_by.get(s.id, set()), day),
                last7=last_days(taken_by.get(s.id, set()), day, HISTORY_DAYS),
            )
            for s in supplements
        ],
        taken_ids=[i for i in active_ids if day in taken_by.get(i, set())],
        yesterday_ids=[i for i in active_ids if yesterday in taken_by.get(i, set())],
    )


@router.put("/day/{day}", status_code=204)
def put_day(day: dt.date, body: DayIn, db: Session = Depends(get_db)) -> Response:
    """Stan dnia w całości: wzięte są dokładnie te suplementy. Powtórka niczego nie zmienia."""
    _set_day(db, day, body.taken_ids)
    return Response(status_code=204)


@router.post("/day/{day}/as-yesterday", status_code=204)
def like_yesterday(day: dt.date, db: Session = Depends(get_db)) -> Response:
    """„To co wczoraj": odhacza to, co wzięte dzień wcześniej, niczego nie odznaczając.

    Idempotentne (suma zbiorów), więc może czekać w kolejce offline.
    """
    active = [s.id for s in _active(db)]
    wanted = as_yesterday(_taken_on(db, day), _taken_on(db, day - dt.timedelta(days=1)), active)
    _set_day(db, day, wanted)
    return Response(status_code=204)


@router.put("/{supplement_id}", status_code=204)
def put_supplement(
    supplement_id: uuid.UUID, body: SupplementIn, db: Session = Depends(get_db)
) -> Response:
    """Dodaje suplement albo zmienia nazwę i dawkę. Usunięty wraca na listę przy zapisie."""
    dose = (body.dose or "").strip() or None
    if errors := supplement_errors(body.name, dose):
        raise HTTPException(422, " ".join(errors))
    supplement = db.get(Supplement, supplement_id)
    if supplement is None:
        supplement = Supplement(id=supplement_id)
        db.add(supplement)
    supplement.name, supplement.dose, supplement.archived_at = body.name.strip(), dose, None
    db.commit()
    return Response(status_code=204)


@router.delete("/{supplement_id}", status_code=204)
def delete_supplement(supplement_id: uuid.UUID, db: Session = Depends(get_db)) -> Response:
    """Usuwa z listy; historia odhaczeń zostaje. Usunięcie nieistniejącego też się udaje."""
    supplement = db.get(Supplement, supplement_id)
    if supplement is not None and supplement.archived_at is None:
        supplement.archived_at = utcnow()
        db.commit()
    return Response(status_code=204)
