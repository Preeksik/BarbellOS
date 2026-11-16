"""Dostawca Claude (Anthropic API). Wyłączony, dopóki nie ma klucza. Implementacja: etap 2."""

from pydantic import BaseModel

from app.ai.provider import AiResult, ProviderUnavailable, Tier


class ClaudeProvider:
    name = "claude"

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
            raise ProviderUnavailable("brak klucza ANTHROPIC_API_KEY lub modelu dla poziomu")
        # Nie NotImplementedError: klucz dodany przed etapem 2 nie może wywracać żądania,
        # router ma po prostu zgłosić, że zapasowy dostawca nie odpowiedział.
        raise ProviderUnavailable("wywołania Claude powstają w etapie 2")
