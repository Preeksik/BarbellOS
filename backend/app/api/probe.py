"""Próba D etapu 0: czy zapis zrobiony offline przetrwa zamknięcie aplikacji na iPhonie."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_user
from app.db.models import OfflineProbe
from app.db.session import get_db

router = APIRouter(prefix="/api/probe", tags=["etap-0"], dependencies=[Depends(require_user)])


class ProbeIn(BaseModel):
    client_created_at: datetime
    note: str | None = None


class ProbeOut(BaseModel):
    id: uuid.UUID
    client_created_at: datetime
    received_at: datetime
    note: str | None


@router.put("/{probe_id}", response_model=ProbeOut)
def put_probe(probe_id: uuid.UUID, body: ProbeIn, db: Session = Depends(get_db)) -> OfflineProbe:
    """Idempotentne: identyfikator nadaje telefon, powtórka niczego nie dubluje."""
    probe = db.get(OfflineProbe, probe_id)
    if probe is None:
        probe = OfflineProbe(id=probe_id, client_created_at=body.client_created_at, note=body.note)
        db.add(probe)
        db.commit()
        db.refresh(probe)
    return probe


@router.get("", response_model=list[ProbeOut])
def list_probes(db: Session = Depends(get_db)) -> list[OfflineProbe]:
    return list(
        db.scalars(select(OfflineProbe).order_by(OfflineProbe.received_at.desc()).limit(20))
    )
