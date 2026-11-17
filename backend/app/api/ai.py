"""AI w diecie (etap 2): szkic posiłku ze zdjęcia lub opisu oraz licznik kosztów.

Szkic niczego nie zapisuje. Użytkownik poprawia składniki i ilości, a telefon zapisuje
zwykłe wpisy dziennika (`PUT /api/diary/entries/{id}`): z produktem, gdy składnik jest
w bazie, albo z szacunkiem modelu (`estimated`), gdy go nie ma (dokumentacja 7).
"""

import datetime as dt
import logging
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.ai.meal_prompts import MEAL_PHOTO_PROMPT, MEAL_TEXT_PROMPT, with_description
from app.ai.provider import AiResult
from app.ai.router import AiRouter, AllProvidersFailed, FailureKind, Task
from app.ai.schemas import MealEstimate
from app.api.deps import get_ai_router, require_user
from app.api.diet import FoodOut, Per100, _food_out, _label_image
from app.config import Settings, get_settings
from app.core.ai_cost import usage_summary
from app.core.label import image_mime
from app.core.meal_draft import clean_items, match_item, portion
from app.core.nutrients import MACRO_KEYS
from app.db import repo
from app.db.session import get_db

router = APIRouter(prefix="/api/ai", tags=["ai"], dependencies=[Depends(require_user)])
log = logging.getLogger(__name__)

AI_FAILURES: dict[FailureKind, tuple[int, str]] = {
    FailureKind.NOT_CONFIGURED: (
        503,
        "Funkcje AI są wyłączone: na serwerze nie ma klucza GEMINI_API_KEY.",
    ),
    FailureKind.RATE_LIMITED: (
        429,
        "Darmowy limit modelu jest wyczerpany. Spróbuj później albo dodaj produkty ręcznie.",
    ),
    FailureKind.INVALID: (
        502,
        "Model nie rozpoznał posiłku. Spróbuj ponownie albo opisz posiłek słowami.",
    ),
    FailureKind.ERROR: (502, "Model AI nie odpowiada. Spróbuj ponownie za chwilę."),
}


class DraftItemOut(BaseModel):
    name: str
    category: str
    grams: float
    grams_low: float
    grams_high: float
    confidence: Literal["low", "medium", "high"]
    # Dopasowany produkt z bazy; None = wpis z szacunkiem modelu.
    match: FoodOut | None
    # Inne produkty z bazy do wyboru (bez `match`), od najlepszego.
    candidates: list[FoodOut]
    estimate_per_100: Per100  # szacunek modelu: kcal, B, T, W; reszta pusta
    # Wartości porcji dla `grams` z dopasowania albo z szacunku (podgląd).
    values: Per100


class MealDraftOut(BaseModel):
    ai_run_id: int
    source: Literal["photo", "text"]
    items: list[DraftItemOut]
    notes: str | None
    warnings: list[str]


class TextIn(BaseModel):
    text: str = Field(min_length=3, max_length=1000)


def _run(db: Session, ai: AiRouter, task: Task, prompt: str, images: list[bytes] | None):
    try:
        result = ai.run(task, prompt, MealEstimate, images=images)
    except AllProvidersFailed as exc:
        log.warning("Szkic posiłku nieudany: %s", exc)
        for failure in exc.called:
            repo.log_ai_run(db, task, failure.provider, "", failure.kind)
        status, message = AI_FAILURES[exc.kind]
        raise HTTPException(status, message) from exc
    run = repo.log_ai_run(
        db, task, result.provider, result.model, "ok", result.input_tokens, result.output_tokens
    )
    return result, run.id


def _draft(db: Session, result: AiResult, run_id: int, source: str) -> MealDraftOut:
    estimate: MealEstimate = result.data
    items, warnings = clean_items(item.model_dump() for item in estimate.items)
    if not items:
        raise HTTPException(
            422,
            "Nie rozpoznano jedzenia. Zrób zdjęcie z góry, w dobrym świetle, albo opisz posiłek.",
        )
    candidates = repo.search_candidates(db)
    out = []
    for item in items:
        matching = match_item(item.name, item.name_en, candidates)
        foods = {f.id: f for f in repo.foods_by_ids(db, matching.candidates)}
        match = foods.get(matching.food_id) if matching.food_id is not None else None
        per_100 = (
            {key: getattr(match, key) for key in MACRO_KEYS} if match else item.estimate_per_100
        )
        out.append(
            DraftItemOut(
                name=item.name,
                category=item.category,
                grams=item.grams,
                grams_low=item.grams_low,
                grams_high=item.grams_high,
                confidence=item.confidence
                if item.confidence in ("low", "medium", "high")
                else "low",
                match=_food_out(db, match, cached=True) if match else None,
                candidates=[
                    _food_out(db, foods[food_id], cached=True)
                    for food_id in matching.candidates
                    if food_id in foods and food_id != matching.food_id
                ],
                estimate_per_100=Per100(**item.estimate_per_100),
                values=Per100(**portion(per_100, item.grams)),
            )
        )
    return MealDraftOut(
        ai_run_id=run_id,
        source=source,
        items=out,
        notes=(estimate.notes or "").strip() or None,
        warnings=warnings,
    )


@router.post("/meal/photo", response_model=MealDraftOut)
def meal_from_photo(
    image: bytes = Depends(_label_image),
    description: str | None = Query(default=None, max_length=500),
    db: Session = Depends(get_db),
    ai: AiRouter = Depends(get_ai_router),
) -> MealDraftOut:
    """Zdjęcie posiłku (i opcjonalny opis) -> szkic składników z gramaturą."""
    if image_mime(image) is None:
        raise HTTPException(415, "To nie jest zdjęcie (JPEG, PNG, WebP albo HEIC).")
    prompt = with_description(MEAL_PHOTO_PROMPT, description)
    result, run_id = _run(db, ai, Task.MEAL_PHOTO, prompt, [image])
    return _draft(db, result, run_id, "photo")


@router.post("/meal/text", response_model=MealDraftOut)
def meal_from_text(
    body: TextIn, db: Session = Depends(get_db), ai: AiRouter = Depends(get_ai_router)
) -> MealDraftOut:
    """Opis słowami („2 jajka sadzone, 2 kromki chleba") -> szkic składników z gramaturą."""
    prompt = with_description(MEAL_TEXT_PROMPT, body.text)
    result, run_id = _run(db, ai, Task.TEXT_TO_ITEMS, prompt, None)
    return _draft(db, result, run_id, "text")


# ---------- licznik kosztów ----------


class TaskUsageOut(BaseModel):
    task: str
    runs: int
    failed: int
    input_tokens: int
    output_tokens: int
    cost_usd: float


class UsageOut(BaseModel):
    month: str  # RRRR-MM
    runs: int
    cost_usd: float  # według cennika płatnego poziomu
    unpriced_runs: int  # wywołania modelu spoza cennika
    by_task: list[TaskUsageOut]


@router.get("/usage", response_model=UsageOut)
def usage(
    month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> UsageOut:
    """Zużycie AI w miesiącu (domyślnie bieżącym, w strefie użytkownika)."""
    zone = ZoneInfo(settings.default_timezone)
    if month is None:
        month = dt.datetime.now(zone).strftime("%Y-%m")
    year, mon = map(int, month.split("-"))
    if not 1 <= mon <= 12:
        raise HTTPException(422, "Nieprawidłowy miesiąc.")
    start = dt.datetime(year, mon, 1, tzinfo=zone)
    end = dt.datetime(year + mon // 12, mon % 12 + 1, 1, tzinfo=zone)
    runs = repo.ai_runs_between(db, start, end)
    by_task, unpriced = usage_summary(
        {
            "task": r.task,
            "status": r.status,
            "input_tokens": r.input_tokens,
            "output_tokens": r.output_tokens,
            "cost_usd": r.cost_usd,
        }
        for r in runs
    )
    return UsageOut(
        month=month,
        runs=len(runs),
        cost_usd=round(sum(t.cost_usd for t in by_task), 6),
        unpriced_runs=unpriced,
        by_task=[TaskUsageOut(**vars(t)) for t in by_task],
    )
