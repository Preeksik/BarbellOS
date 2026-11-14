"""Wybór dostawcy i poziomu modelu dla zadania, z przejściem na zapasowego przy limicie."""

from enum import StrEnum

from pydantic import BaseModel

from app.ai.provider import AiProvider, AiResult, ProviderUnavailable, RateLimited, Tier


class Task(StrEnum):
    LABEL_TO_FOOD = "label_to_food"
    TEXT_TO_ITEMS = "text_to_items"
    MEAL_PHOTO = "meal_photo"
    DAY_SUMMARY = "day_summary"
    WEEK_REVIEW = "week_review"


# Kolejność prób: (dostawca, poziom). Dostawca bez klucza jest pomijany, więc dopóki
# nie ma klucza Claude, wszystko idzie na Gemini.
ROUTES: dict[Task, tuple[tuple[str, Tier], ...]] = {
    Task.LABEL_TO_FOOD: (("gemini", Tier.CHEAP), ("claude", Tier.CHEAP)),
    Task.TEXT_TO_ITEMS: (("gemini", Tier.CHEAP), ("claude", Tier.CHEAP)),
    Task.MEAL_PHOTO: (("gemini", Tier.MID), ("claude", Tier.MID)),
    Task.DAY_SUMMARY: (("claude", Tier.MID), ("gemini", Tier.MID)),
    Task.WEEK_REVIEW: (("claude", Tier.STRONG), ("gemini", Tier.MID)),
}


class AllProvidersFailed(Exception):
    pass


class AiRouter:
    def __init__(self, providers: dict[str, AiProvider]) -> None:
        self.providers = providers

    def run(
        self,
        task: Task,
        prompt: str,
        schema: type[BaseModel],
        images: list[bytes] | None = None,
    ) -> AiResult:
        errors: list[str] = []
        for name, tier in ROUTES[task]:
            provider = self.providers.get(name)
            if provider is None or not provider.supports(tier):
                errors.append(f"{name}: niedostępny")
                continue
            try:
                return provider.generate(tier, prompt, schema, images)
            except RateLimited:
                errors.append(f"{name}: limit")
            except ProviderUnavailable as exc:
                errors.append(f"{name}: {exc}")
        raise AllProvidersFailed(f"{task}: " + "; ".join(errors))
