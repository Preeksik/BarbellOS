"""Dostawca Gemini (Google AI Studio). Implementacja wywołań: etap 2."""

from pydantic import BaseModel

from app.ai.provider import AiResult, ProviderUnavailable, Tier


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key: str, models: dict[Tier, str]) -> None:
        self.api_key, self.models = api_key, models

    def supports(self, tier: Tier) -> bool:
        return bool(self.api_key) and tier in self.models

    def generate(
        self,
        tier: Tier,
        prompt: str,
        schema: type[BaseModel],
        images: list[bytes] | None = None,
    ) -> AiResult:
        if not self.supports(tier):
            raise ProviderUnavailable("brak klucza GEMINI_API_KEY lub modelu dla poziomu")
        # Etap 2: wywołanie API z wymuszonym schematem JSON, mapowanie HTTP 429 na
        # RateLimited, zapis tokenów do ai_run. Przed implementacją sprawdzić aktualną
        # dokumentację SDK, bo nazwy modeli i parametry zmieniają się często.
        raise NotImplementedError("Wywołania Gemini powstają w etapie 2.")
