"""Wspólny interfejs dostawców modeli."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel


class Tier(StrEnum):
    CHEAP = "cheap"
    MID = "mid"
    STRONG = "strong"


class RateLimited(Exception):
    """Dostawca odpowiedział limitem (HTTP 429). Router próbuje wtedy kolejnego."""


class ProviderUnavailable(Exception):
    """Brak klucza, nieobsługiwany poziom albo błąd po stronie dostawcy (sieć, HTTP 5xx)."""


class InvalidResponse(Exception):
    """Odpowiedź nie pasuje do schematu. Router ponawia wywołanie jeden raz."""


@dataclass(frozen=True)
class AiResult:
    data: BaseModel
    provider: str
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None


class AiProvider(Protocol):
    name: str

    def supports(self, tier: Tier) -> bool: ...

    def generate(
        self,
        tier: Tier,
        prompt: str,
        schema: type[BaseModel],
        images: list[bytes] | None = None,
    ) -> AiResult:
        """Zwraca odpowiedź zgodną ze schematem albo rzuca jeden z wyjątków powyżej."""
        ...
