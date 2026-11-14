"""Stan serwera oraz import danych zdrowotnych ze Skrótów (dokumentacja 6.2)."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import __version__
from app.api.deps import require_ingest_token, require_user
from app.config import Settings, get_settings
from app.core.health_ingest import IngestError, parse_ingest
from app.db import repo
from app.db.session import get_db

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/healthz")
def healthz() -> dict:
    """Lekki endpoint dla podtrzymania (cron co 14 min). Celowo nie dotyka bazy."""
    return {"status": "ok", "version": __version__}


class IngestIn(BaseModel):
    """Listy równoległe albo tekst z jedną wartością w linii (tak zwracają dane Skróty)."""

    type: str
    starts: list[str] | str
    values: list[float | str] | str
    ends: list[str] | str | None = None
    unit: str | None = None
    source: str = "shortcuts"


class IngestOut(BaseModel):
    received: int
    inserted: int
    updated: int


@router.post(
    "/health/ingest", response_model=IngestOut, dependencies=[Depends(require_ingest_token)]
)
def ingest(
    body: IngestIn,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> IngestOut:
    """Idempotentne: ta sama próbka (typ, początek, źródło) wysłana ponownie nie dubluje się."""
    try:
        samples = parse_ingest(
            type=body.type,
            starts=body.starts,
            values=body.values,
            ends=body.ends,
            unit=body.unit,
            source=body.source,
            default_timezone=settings.default_timezone,
        )
    except IngestError as exc:
        raise HTTPException(422, str(exc)) from exc
    inserted, updated = repo.upsert_health_samples(db, samples)
    return IngestOut(received=len(samples), inserted=inserted, updated=updated)


class TypeSummary(BaseModel):
    type: str
    count: int
    last_starts_at: datetime | None
    last_value: float | None
    last_label: str | None
    unit: str | None
    source: str | None
    last_received_at: datetime | None


@router.get(
    "/health/summary", response_model=list[TypeSummary], dependencies=[Depends(require_user)]
)
def summary(db: Session = Depends(get_db)) -> list[dict]:
    """Co i kiedy ostatnio dotarło: ekran diagnostyczny próby B."""
    return repo.health_summary(db)
