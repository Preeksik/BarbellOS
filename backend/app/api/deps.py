"""Wspólne zależności endpointów."""

from collections.abc import Callable

from fastapi import Depends, HTTPException, Request

from app.config import Settings, get_settings
from app.off.client import FoodDraft, fetch_product
from app.security import token_matches


def require_user(request: Request, settings: Settings = Depends(get_settings)) -> None:
    """Sesja z ciasteczka. Lokalnie bez ustawionego hasła logowanie jest pomijane."""
    if settings.auth_disabled:
        return
    if not request.session.get("user"):
        raise HTTPException(401, "Wymagane logowanie.")


def require_ingest_token(request: Request, settings: Settings = Depends(get_settings)) -> None:
    """Token tylko do zapisu próbek zdrowotnych: `Authorization: Bearer <token>`."""
    scheme, _, token = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not token_matches(token.strip(), settings.ingest_token):
        raise HTTPException(401, "Nieprawidłowy token.")


OffFetcher = Callable[[str], FoodDraft | None]


def get_off_fetcher(settings: Settings = Depends(get_settings)) -> OffFetcher:
    return lambda barcode: fetch_product(barcode, settings.off_base_url, settings.off_user_agent)
