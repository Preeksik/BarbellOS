"""Cele dzienne (etap 1, krok 4): odczyt celów dla dnia i zmiana od wskazanej daty."""

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_user
from app.api.diet import Per100 as Goals
from app.core.targets import GOAL_KINDS, active_version, goal_errors, goals_to_rows, rows_to_goals
from app.db import repo
from app.db.session import get_db

router = APIRouter(prefix="/api/targets", tags=["targets"], dependencies=[Depends(require_user)])


class TargetsOut(BaseModel):
    date: dt.date  # dzień, o który pytano
    date_from: dt.date | None  # od kiedy obowiązują te cele; None = celów jeszcze nie ustawiono
    goals: Goals  # puste pole = bez celu
    kinds: dict[str, str]  # target | min | max: jak czytać cel


class TargetsIn(BaseModel):
    goals: Goals


def _targets_for(db: Session, day: dt.date) -> TargetsOut:
    version = active_version(repo.target_versions(db), day)
    goals = rows_to_goals(repo.target_rows(db, version)) if version else dict.fromkeys(GOAL_KINDS)
    return TargetsOut(date=day, date_from=version, goals=Goals(**goals), kinds=GOAL_KINDS)


@router.get("/{day}", response_model=TargetsOut)
def get_targets(day: dt.date, db: Session = Depends(get_db)) -> TargetsOut:
    """Cele obowiązujące w danym dniu (wersja z najpóźniejszą datą nie późniejszą niż dzień)."""
    return _targets_for(db, day)


@router.put("/{date_from}", response_model=TargetsOut)
def put_targets(date_from: dt.date, body: TargetsIn, db: Session = Depends(get_db)) -> TargetsOut:
    """Nowe cele od `date_from`. Dni wcześniejsze zachowują poprzednie cele.

    Idempotentne: zapis z tą samą datą zastępuje cele z tej daty.
    """
    goals = body.goals.model_dump()
    if errors := goal_errors(goals):
        raise HTTPException(422, " ".join(errors))
    repo.replace_targets(db, date_from, goals_to_rows(goals))
    return _targets_for(db, date_from)
