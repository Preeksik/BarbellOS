"""Wspólne zależności endpointów."""

from collections.abc import Callable

from fastapi import Depends, HTTPException, Request

from app.ai.claude import ClaudeProvider
from app.ai.gemini import GeminiProvider
from app.ai.provider import Tier
from app.ai.router import AiRouter
from app.config import Settings, get_settings
from app.off.client import FoodDraft, fetch_product, search_products
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


OffSearcher = Callable[[str], dict]


def get_off_searcher(settings: Settings = Depends(get_settings)) -> OffSearcher:
    return lambda query: search_products(query, settings.off_search_url, settings.off_user_agent)


def get_ai_router(settings: Settings = Depends(get_settings)) -> AiRouter:
    """Dostawcy modeli z konfiguracji. Dostawca bez klucza jest przez router pomijany."""
    return AiRouter(
        {
            "gemini": GeminiProvider(
                settings.gemini_api_key,
                {Tier.CHEAP: settings.gemini_model_cheap, Tier.MID: settings.gemini_model_mid},
                settings.gemini_base_url,
            ),
            "claude": ClaudeProvider(
                settings.anthropic_api_key,
                {
                    Tier.CHEAP: settings.claude_model_cheap,
                    Tier.MID: settings.claude_model_mid,
                    Tier.STRONG: settings.claude_model_strong,
                },
            ),
        }
    )
