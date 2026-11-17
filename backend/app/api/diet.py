"""Dieta: produkt po kodzie kreskowym, poprawianie wartości, zdjęcie etykiety, własny produkt."""

import logging
import time
import uuid
from datetime import datetime
from typing import Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.ai.prompts import LABEL_PROMPT
from app.ai.router import AiRouter, AllProvidersFailed, FailureKind, Task
from app.ai.schemas import LabelExtract
from app.api.deps import (
    OffFetcher,
    OffSearcher,
    get_ai_router,
    get_off_fetcher,
    get_off_searcher,
    require_user,
)
from app.core.barcode import is_valid_ean
from app.core.label import image_mime, label_draft
from app.core.nutrients import MACRO_KEYS, macro_errors, macro_warnings
from app.core.search import rank
from app.db import repo
from app.db.models import Food
from app.db.session import get_db
from app.off.client import parse_search, search_limiter

router = APIRouter(prefix="/api/foods", tags=["diet"], dependencies=[Depends(require_user)])
log = logging.getLogger(__name__)

# Telefon zmniejsza zdjęcie przed wysłaniem; limit chroni serwer przed resztą.
MAX_LABEL_IMAGE_BYTES = 8 * 1024 * 1024

# Co widzi użytkownik, gdy żaden model nie odpowiedział: (status HTTP, komunikat).
AI_FAILURES: dict[FailureKind, tuple[int, str]] = {
    FailureKind.NOT_CONFIGURED: (
        503,
        "Odczyt etykiety jest wyłączony: na serwerze nie ma klucza GEMINI_API_KEY.",
    ),
    FailureKind.RATE_LIMITED: (
        429,
        "Darmowy limit modelu jest wyczerpany. Spróbuj później albo wpisz wartości ręcznie.",
    ),
    FailureKind.INVALID: (
        502,
        "Model nie odczytał etykiety. Zrób wyraźniejsze zdjęcie albo wpisz wartości ręcznie.",
    ),
    FailureKind.ERROR: (
        502,
        "Model AI nie odpowiada. Spróbuj ponownie albo wpisz wartości ręcznie.",
    ),
}


class MicroOut(BaseModel):
    nutrient_id: str
    amount_per_100g: float
    source: str


class Per100(BaseModel):
    """Osiem wartości z etykiety na 100 g lub 100 ml. Puste pole to brak danych, nie zero."""

    kcal: float | None = None
    protein_g: float | None = None
    fat_g: float | None = None
    sat_fat_g: float | None = None
    carbs_g: float | None = None
    sugars_g: float | None = None
    fiber_g: float | None = None
    salt_g: float | None = None


class FoodOut(BaseModel):
    id: int
    barcode: str | None
    name: str
    brand: str | None
    serving_g: float | None
    unit: Literal["g", "ml"]
    origin: str
    macro_source: str
    source_updated_at: datetime | None
    verified_at: datetime | None
    per_100: Per100
    micros: list[MicroOut]
    warnings: list[str]
    cached: bool
    favorite: bool


class FoodUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    brand: str | None = Field(default=None, max_length=255)
    serving_g: float | None = Field(default=None, gt=0, le=5000)
    unit: Literal["g", "ml"] = "g"
    per_100: Per100

    @field_validator("name", "brand")
    @classmethod
    def _strip(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class FoodCreate(FoodUpdate):
    """Własny produkt dla kodu, którego nie ma w źródłach."""

    # Skąd wziął się szkic: wpisany ręcznie albo odczytany ze zdjęcia etykiety.
    origin: Literal["user", "ai_label"] = "user"


class LabelDraftOut(BaseModel):
    """Szkic z etykiety do formularza produktu. Niczego nie zapisuje."""

    name: str | None
    brand: str | None
    serving_g: float | None
    unit: Literal["g", "ml"] | None
    per_100: Per100
    warnings: list[str]


def _food_out(db: Session, food: Food, cached: bool) -> FoodOut:
    macros = {key: getattr(food, key) for key in MACRO_KEYS}
    return FoodOut(
        id=food.id,
        barcode=food.barcode,
        name=food.name,
        brand=food.brand,
        serving_g=food.serving_g,
        unit=food.unit or "g",
        origin=food.origin,
        macro_source=food.macro_source,
        source_updated_at=food.source_updated_at,
        verified_at=food.verified_at,
        per_100=Per100(**macros),
        micros=[
            MicroOut(nutrient_id=m.nutrient_id, amount_per_100g=m.amount_per_100g, source=m.source)
            for m in repo.food_micros(db, food.id)
        ],
        warnings=macro_warnings(macros),
        cached=cached,
        favorite=food.favorite_at is not None,
    )


def _get_food(db: Session, food_id: int) -> Food:
    food = db.get(Food, food_id)
    if food is None:
        raise HTTPException(404, "Nie ma takiego produktu.")
    return food


@router.get("/barcode/{barcode}", response_model=FoodOut)
def by_barcode(
    barcode: str,
    db: Session = Depends(get_db),
    fetch: OffFetcher = Depends(get_off_fetcher),
) -> FoodOut:
    if not is_valid_ean(barcode):
        raise HTTPException(422, "Nieprawidłowy kod kreskowy.")
    if food := repo.find_food_by_barcode(db, barcode):
        return _food_out(db, food, cached=True)
    try:
        draft = fetch(barcode)
    except httpx.HTTPError as exc:
        raise HTTPException(502, "Open Food Facts nie odpowiada. Spróbuj ponownie.") from exc
    if draft is None:
        raise HTTPException(404, "Produktu nie ma w Open Food Facts.")
    draft.barcode = barcode
    return _food_out(db, repo.save_food_draft(db, draft), cached=False)


def _checked_macros(body: FoodUpdate) -> dict[str, float | None]:
    """Wartości z formularza po kontroli. Niemożliwe wartości kończą żądanie błędem 422."""
    if body.name is None:
        raise HTTPException(422, "Nazwa nie może być pusta.")
    macros = body.per_100.model_dump()
    if errors := macro_errors(macros, body.unit):
        raise HTTPException(422, " ".join(errors))
    return macros


@router.put("/barcode/{barcode}", response_model=FoodOut)
def put_by_barcode(barcode: str, body: FoodCreate, db: Session = Depends(get_db)) -> FoodOut:
    """Własny produkt dla zeskanowanego kodu, np. przepisany ze zdjęcia etykiety.

    Idempotentne: kluczem jest kod kreskowy, więc powtórzona wysyłka nie tworzy
    duplikatu, tylko zapisuje te same wartości jeszcze raz.
    """
    if not is_valid_ean(barcode):
        raise HTTPException(422, "Nieprawidłowy kod kreskowy.")
    macros = _checked_macros(body)
    food = repo.find_food_by_barcode(db, barcode)
    if food is None:
        food = repo.create_user_food(
            db, barcode, body.name, body.brand, body.serving_g, body.unit, macros, body.origin
        )
    else:
        repo.update_food(db, food, body.name, body.brand, body.serving_g, body.unit, macros)
    return _food_out(db, food, cached=True)


async def _label_image(request: Request) -> bytes:
    """Treść żądania jako zdjęcie. Czytana porcjami, żeby limit zadziałał przed końcem wysyłki."""
    too_big = HTTPException(413, "Zdjęcie jest za duże (limit 8 MB).")
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > MAX_LABEL_IMAGE_BYTES:
        raise too_big
    data = bytearray()
    async for chunk in request.stream():
        data += chunk
        if len(data) > MAX_LABEL_IMAGE_BYTES:
            raise too_big
    return bytes(data)


@router.post("/label", response_model=LabelDraftOut)
def read_label(
    image: bytes = Depends(_label_image),
    db: Session = Depends(get_db),
    ai: AiRouter = Depends(get_ai_router),
) -> LabelDraftOut:
    """Zdjęcie etykiety -> szkic wartości do formularza. Zapis robi dopiero użytkownik.

    Model przepisuje tabelę, a zakresy i spójność sprawdza kod (`core/label.py`).
    """
    if image_mime(image) is None:
        raise HTTPException(415, "To nie jest zdjęcie (JPEG, PNG, WebP albo HEIC).")
    task = Task.LABEL_TO_FOOD
    try:
        result = ai.run(task, LABEL_PROMPT, LabelExtract, images=[image])
    except AllProvidersFailed as exc:
        log.warning("Odczyt etykiety nieudany: %s", exc)
        for failure in exc.called:
            repo.log_ai_run(db, task, failure.provider, "", failure.kind)
        status, message = AI_FAILURES[exc.kind]
        raise HTTPException(status, message) from exc
    repo.log_ai_run(
        db, task, result.provider, result.model, "ok", result.input_tokens, result.output_tokens
    )

    draft = label_draft(result.data.model_dump())
    if draft.found == 0:
        raise HTTPException(
            422,
            "Nie widzę na zdjęciu tabeli wartości odżywczych na 100 g lub 100 ml. "
            "Zrób zdjęcie samej tabeli albo wpisz wartości ręcznie.",
        )
    return LabelDraftOut(
        name=draft.name,
        brand=draft.brand,
        serving_g=draft.serving_g,
        unit=draft.unit,
        per_100=Per100(**draft.macros),
        warnings=draft.warnings,
    )


@router.put("/custom/{client_id}", response_model=FoodOut)
def put_custom(client_id: uuid.UUID, body: FoodCreate, db: Session = Depends(get_db)) -> FoodOut:
    """Własny produkt bez kodu kreskowego (np. obiad domowy, produkt z wagi w sklepie).

    Identyfikator nadaje telefon, więc zapis może czekać w kolejce offline,
    a powtórzona wysyłka poprawia ten sam produkt zamiast tworzyć drugi.
    """
    macros = _checked_macros(body)
    food = repo.find_food_by_client_id(db, client_id)
    if food is None:
        food = repo.create_user_food(
            db,
            None,
            body.name,
            body.brand,
            body.serving_g,
            body.unit,
            macros,
            body.origin,
            client_id=client_id,
        )
    else:
        repo.update_food(db, food, body.name, body.brand, body.serving_g, body.unit, macros)
    return _food_out(db, food, cached=True)


# ---------- wyszukiwanie, ostatnie, ulubione ----------


class SearchOut(BaseModel):
    foods: list[FoodOut]


class OffHitOut(BaseModel):
    barcode: str
    name: str
    brand: str | None
    kcal: float | None  # na 100 g lub 100 ml
    unit: Literal["g", "ml"]


class RecentOut(BaseModel):
    food: FoodOut
    last_amount: float
    last_slot: str


class FavoriteIn(BaseModel):
    favorite: bool


@router.get("/search", response_model=SearchOut)
def search(q: str = Query(max_length=100), db: Session = Depends(get_db)) -> SearchOut:
    """Wyszukiwanie we własnej bazie. Szybkie, więc może działać przy każdym znaku."""
    ids = rank(q, repo.search_candidates(db), limit=30)
    return SearchOut(
        foods=[_food_out(db, food, cached=True) for food in repo.foods_by_ids(db, ids)]
    )


@router.get("/search/off", response_model=list[OffHitOut])
def search_off(
    q: str = Query(min_length=2, max_length=100),
    searcher: OffSearcher = Depends(get_off_searcher),
) -> list[OffHitOut]:
    """Wyszukiwanie w Open Food Facts. Produkt zapisuje się dopiero po wybraniu (po kodzie)."""
    if not search_limiter.allow(time.monotonic()):
        raise HTTPException(
            429, "Open Food Facts pozwala na kilka wyszukiwań na minutę. Spróbuj za chwilę."
        )
    try:
        payload = searcher(q.strip())
    except httpx.HTTPError as exc:
        raise HTTPException(502, "Open Food Facts nie odpowiada. Spróbuj ponownie.") from exc
    return [OffHitOut(**vars(hit)) for hit in parse_search(payload, is_valid_ean)]


@router.get("/recent", response_model=list[RecentOut])
def recent(db: Session = Depends(get_db)) -> list[RecentOut]:
    """Ostatnio jedzone produkty z ostatnią ilością: najszybsza droga do powtórki."""
    return [
        RecentOut(
            food=_food_out(db, food, cached=True),
            last_amount=entry.amount,
            last_slot=entry.meal_slot,
        )
        for food, entry in repo.recent_foods(db)
    ]


@router.get("/favorites", response_model=list[FoodOut])
def favorites(db: Session = Depends(get_db)) -> list[FoodOut]:
    return [_food_out(db, food, cached=True) for food in repo.favorite_foods(db)]


@router.put("/{food_id}/favorite", response_model=FoodOut)
def put_favorite(food_id: int, body: FavoriteIn, db: Session = Depends(get_db)) -> FoodOut:
    """Dodaje do ulubionych albo usuwa z nich. Idempotentne (stan, nie przełącznik)."""
    return _food_out(db, repo.set_favorite(db, _get_food(db, food_id), body.favorite), True)


@router.get("/{food_id}", response_model=FoodOut)
def get_food(food_id: int, db: Session = Depends(get_db)) -> FoodOut:
    return _food_out(db, _get_food(db, food_id), cached=True)


@router.put("/{food_id}", response_model=FoodOut)
def update_food(food_id: int, body: FoodUpdate, db: Session = Depends(get_db)) -> FoodOut:
    """Poprawka wartości według etykiety. Idempotentne: ten sam zapis można wysłać ponownie."""
    food = _get_food(db, food_id)
    macros = _checked_macros(body)
    repo.update_food(db, food, body.name, body.brand, body.serving_g, body.unit, macros)
    return _food_out(db, food, cached=True)


@router.post("/{food_id}/verify", response_model=FoodOut)
def verify_food(food_id: int, db: Session = Depends(get_db)) -> FoodOut:
    """Wartości zgadzają się z etykietą: produkt zostaje oznaczony jako zweryfikowany."""
    food = _get_food(db, food_id)
    return _food_out(db, repo.mark_food_verified(db, food), cached=True)
