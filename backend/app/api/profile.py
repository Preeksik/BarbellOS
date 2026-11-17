"""Profil użytkownika i wyliczony z niego plan: kalorie i cele makroskładników.

Plan to propozycja. Cele dzienne zmieniają się dopiero, gdy użytkownik je zatwierdzi
(frontend zapisuje `plan.goals` przez `PUT /api/targets/{od_dnia}`).
"""

import datetime as dt
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_user
from app.api.diet import Per100 as Goals
from app.config import Settings, get_settings
from app.core.profile import Activity, Goal, Profile, Sex, plan_for, profile_errors
from app.db.models import UserProfile, utcnow
from app.db.session import get_db

router = APIRouter(prefix="/api/profile", tags=["profile"], dependencies=[Depends(require_user)])

PROFILE_ID = 1


class ProfileBody(BaseModel):
    sex: Sex
    birth_date: dt.date
    height_cm: float
    weight_kg: float
    activity: Activity
    goal: Goal
    pace_kg_week: float
    protein_g_per_kg: float | None = None


class PlanOut(BaseModel):
    age: int
    bmr: float
    tdee: float
    kcal: float
    adjustment: float
    pace_kg_week: float
    protein_g_per_kg: float
    goals: Goals
    notes: list[str]
    warnings: list[str]


class ProfileOut(BaseModel):
    profile: ProfileBody | None  # None = profilu jeszcze nie wypełniono
    plan: PlanOut | None


def _today(settings: Settings) -> dt.date:
    """Dzisiejsza data w strefie użytkownika: od niej zależy wiek."""
    return dt.datetime.now(ZoneInfo(settings.default_timezone)).date()


def _out(row: UserProfile | None, today: dt.date) -> ProfileOut:
    if row is None:
        return ProfileOut(profile=None, plan=None)
    body = ProfileBody(
        sex=row.sex,
        birth_date=row.birth_date,
        height_cm=row.height_cm,
        weight_kg=row.weight_kg,
        activity=row.activity,
        goal=row.goal,
        pace_kg_week=row.pace_kg_week,
        protein_g_per_kg=row.protein_g_per_kg,
    )
    plan = plan_for(Profile(**body.model_dump()), today)
    return ProfileOut(
        profile=body,
        plan=PlanOut(**{**vars(plan), "goals": Goals(**plan.goals)}),
    )


@router.get("", response_model=ProfileOut)
def get_profile(
    db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
) -> ProfileOut:
    return _out(db.get(UserProfile, PROFILE_ID), _today(settings))


@router.put("", response_model=ProfileOut)
def put_profile(
    body: ProfileBody,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ProfileOut:
    """Zapisuje profil (idempotentne: cały profil jednym zapisem) i zwraca nowy plan."""
    today = _today(settings)
    if errors := profile_errors(Profile(**body.model_dump()), today):
        raise HTTPException(422, " ".join(errors))
    row = db.get(UserProfile, PROFILE_ID)
    if row is None:
        row = UserProfile(id=PROFILE_ID, **body.model_dump())
        db.add(row)
    else:
        for name, value in body.model_dump().items():
            setattr(row, name, value)
        row.updated_at = utcnow()
    db.commit()
    return _out(row, today)
