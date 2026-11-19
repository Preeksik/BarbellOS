"""Wybór dostawcy i poziomu modelu dla zadania, z przejściem na zapasowego przy limicie."""

import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel

from app.ai.provider import (
    AiProvider,
    AiResult,
    InvalidResponse,
    Overloaded,
    ProviderUnavailable,
    RateLimited,
    Tier,
)


class Task(StrEnum):
    LABEL_TO_FOOD = "label_to_food"
    TEXT_TO_ITEMS = "text_to_items"
    MEAL_PHOTO = "meal_photo"
    DAY_SUMMARY = "day_summary"
    WEEK_REVIEW = "week_review"
    FOOD_QUERY = "food_query"  # nazwa produktu -> zapytanie do tabeli USDA
    GENERIC_NAMES = "generic_names"  # opisy rekordów USDA -> polskie nazwy w wyszukiwarce


# Kolejność prób: (dostawca, poziom). Dostawca bez klucza jest pomijany, więc dopóki
# nie ma klucza Claude, wszystko idzie na Gemini. Drugi model Gemini jest zapasem: każdy
# model ma osobny limit i osobne obciążenie (HTTP 503 „high demand" dotyczy jednego modelu).
ROUTES: dict[Task, tuple[tuple[str, Tier], ...]] = {
    Task.LABEL_TO_FOOD: (("gemini", Tier.CHEAP), ("gemini", Tier.MID), ("claude", Tier.CHEAP)),
    Task.TEXT_TO_ITEMS: (("gemini", Tier.CHEAP), ("gemini", Tier.MID), ("claude", Tier.CHEAP)),
    Task.MEAL_PHOTO: (("gemini", Tier.MID), ("gemini", Tier.CHEAP), ("claude", Tier.MID)),
    Task.DAY_SUMMARY: (("claude", Tier.MID), ("gemini", Tier.MID)),
    Task.WEEK_REVIEW: (("claude", Tier.STRONG), ("gemini", Tier.MID)),
    Task.FOOD_QUERY: (("gemini", Tier.CHEAP), ("gemini", Tier.MID), ("claude", Tier.CHEAP)),
    Task.GENERIC_NAMES: (("gemini", Tier.CHEAP), ("gemini", Tier.MID), ("claude", Tier.CHEAP)),
}

# Odpowiedź niezgodna ze schematem: jedno ponowienie, potem błąd (dokumentacja 7).
ATTEMPTS_ON_INVALID = 2
# Przeciążenie dostawcy (HTTP 503 „high demand") zwykle mija po chwili: jedno ponowienie.
OVERLOAD_RETRY_DELAY_S = 3.0


class FailureKind(StrEnum):
    NOT_CONFIGURED = "not_configured"  # brak klucza: żadnego wywołania nie było
    RATE_LIMITED = "rate_limited"
    INVALID = "invalid"
    ERROR = "error"


@dataclass(frozen=True)
class Failure:
    provider: str
    kind: FailureKind
    detail: str


class AllProvidersFailed(Exception):
    def __init__(self, task: Task, failures: list[Failure]) -> None:
        self.task, self.failures = task, failures
        super().__init__(f"{task}: " + "; ".join(f"{f.provider}: {f.detail}" for f in failures))

    @property
    def kind(self) -> FailureKind:
        """Najważniejsza przyczyna: to ją widzi użytkownik."""
        kinds = {f.kind for f in self.failures}
        for kind in (FailureKind.RATE_LIMITED, FailureKind.INVALID, FailureKind.ERROR):
            if kind in kinds:
                return kind
        return FailureKind.NOT_CONFIGURED

    @property
    def called(self) -> list[Failure]:
        """Nieudane próby, w których model został naprawdę wywołany."""
        return [f for f in self.failures if f.kind != FailureKind.NOT_CONFIGURED]


class AiRouter:
    def __init__(
        self,
        providers: dict[str, AiProvider],
        sleep: Callable[[float], None] = time.sleep,  # w testach bez czekania
    ) -> None:
        self.providers, self.sleep = providers, sleep

    def run(
        self,
        task: Task,
        prompt: str,
        schema: type[BaseModel],
        images: list[bytes] | None = None,
    ) -> AiResult:
        failures: list[Failure] = []
        for name, tier in ROUTES[task]:
            provider = self.providers.get(name)
            if provider is None or not provider.supports(tier):
                failures.append(Failure(name, FailureKind.NOT_CONFIGURED, "niedostępny"))
                continue
            try:
                return self._call(provider, tier, prompt, schema, images)
            except RateLimited:
                failures.append(Failure(name, FailureKind.RATE_LIMITED, "limit"))
            except InvalidResponse as exc:
                failures.append(Failure(name, FailureKind.INVALID, f"zła odpowiedź ({exc})"))
            except ProviderUnavailable as exc:
                failures.append(Failure(name, FailureKind.ERROR, str(exc)))
        raise AllProvidersFailed(task, failures)

    def _call(
        self,
        provider: AiProvider,
        tier: Tier,
        prompt: str,
        schema: type[BaseModel],
        images: list[bytes] | None,
    ) -> AiResult:
        try:
            return self._call_with_schema_retry(provider, tier, prompt, schema, images)
        except Overloaded:
            self.sleep(OVERLOAD_RETRY_DELAY_S)
            return self._call_with_schema_retry(provider, tier, prompt, schema, images)

    @staticmethod
    def _call_with_schema_retry(
        provider: AiProvider,
        tier: Tier,
        prompt: str,
        schema: type[BaseModel],
        images: list[bytes] | None,
    ) -> AiResult:
        for _ in range(ATTEMPTS_ON_INVALID - 1):
            try:
                return provider.generate(tier, prompt, schema, images)
            except InvalidResponse:
                continue
        return provider.generate(tier, prompt, schema, images)
