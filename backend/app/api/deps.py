"""Wspólne zależności endpointów."""

from collections.abc import Callable
from functools import lru_cache

from fastapi import Depends, HTTPException, Request

from app.ai.claude import ClaudeProvider
from app.ai.gemini import GeminiProvider
from app.ai.provider import Tier
from app.ai.router import AiRouter
from app.config import Settings, get_settings
from app.fdc.client import FdcClient
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


@lru_cache
def _fdc_client(api_key: str, base_url: str) -> FdcClient:
    # Jeden klient na proces: jego pamięć wyników oszczędza limit zapytań USDA.
    return FdcClient(api_key, base_url)


def get_fdc_client(settings: Settings = Depends(get_settings)) -> FdcClient:
    """Pusty FDC_API_KEY w .env oznacza klucz demonstracyjny (ok. 10 zapytań na godzinę)."""
    return _fdc_client(settings.fdc_api_key or "DEMO_KEY", settings.fdc_base_url)


def get_off_searcher(settings: Settings = Depends(get_settings)) -> OffSearcher:
    # 50 zamiast 20: wyniki bez kalorii i nietrafione odpadają (`core.search.order_hits`),
    # a liczba zapytań do bazy (limit na minutę) się nie zmienia.
    return lambda query: search_products(
        query,
        settings.off_search_url,
        settings.off_user_agent,
        page_size=50,
        country=settings.off_search_country or None,
    )


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
