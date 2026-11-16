"""Dostawca Gemini (Google AI Studio) przez Interactions API.

Stan dokumentacji na 16.11.2026 (https://aistudio.google.com/docs/interactions):
`POST /v1beta/interactions`, klucz w nagłówku `x-goog-api-key`, wymuszony schemat JSON
w `response_format`. Starsze `generateContent` nadal działa, ale nowe projekty mają
używać Interactions. Nazwy modeli i pól zmieniają się często: przed zmianą tego pliku
sprawdź aktualną dokumentację zamiast polegać na pamięci.
"""

import base64

import httpx
from pydantic import BaseModel, ValidationError

from app.ai.json_schema import provider_schema
from app.ai.provider import AiResult, InvalidResponse, ProviderUnavailable, RateLimited, Tier
from app.core.label import image_mime

DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com"
# Wersja kontraktu API z przykładów w dokumentacji. Od niej zależy kształt odpowiedzi.
API_REVISION = "2026-05-20"
TIMEOUT_S = 60.0


class GeminiProvider:
    name = "gemini"

    def __init__(
        self,
        api_key: str,
        models: dict[Tier, str],
        base_url: str = DEFAULT_BASE_URL,
        transport: httpx.BaseTransport | None = None,  # podmieniany w testach
    ) -> None:
        self.api_key, self.models = api_key, models
        self.base_url, self.transport = base_url.rstrip("/"), transport

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
        model = self.models[tier]
        payload = self._post(self._request_body(model, prompt, schema, images or []))

        if payload.get("status") == "failed":
            raise ProviderUnavailable("model zakończył wywołanie błędem")
        try:
            data = schema.model_validate_json(_output_text(payload))
        except ValidationError as exc:
            # Także odpowiedź ucięta limitem tokenów (status „incomplete") trafia tutaj.
            raise InvalidResponse(f"{exc.error_count()} błędów walidacji") from exc

        usage = payload.get("usage") or {}
        return AiResult(
            data=data,
            provider=self.name,
            model=model,
            input_tokens=usage.get("total_input_tokens"),
            output_tokens=_billed_output_tokens(usage),
        )

    def _request_body(
        self, model: str, prompt: str, schema: type[BaseModel], images: list[bytes]
    ) -> dict:
        parts: list[dict] = [{"type": "text", "text": prompt}]
        for image in images:
            mime = image_mime(image)
            if mime is None:
                raise ValueError("Nieobsługiwany format obrazu.")
            parts.append(
                {
                    "type": "image",
                    "data": base64.b64encode(image).decode("ascii"),
                    "mime_type": mime,
                }
            )
        return {
            "model": model,
            "input": parts,
            "response_format": {
                "type": "text",
                "mime_type": "application/json",
                "schema": provider_schema(schema),
            },
            # Bez przechowywania rozmowy po stronie Google: zdjęcia nie mają tam zostawać.
            "store": False,
        }

    def _post(self, body: dict) -> dict:
        try:
            with httpx.Client(transport=self.transport, timeout=TIMEOUT_S) as client:
                response = client.post(
                    f"{self.base_url}/v1beta/interactions",
                    json=body,
                    headers={"x-goog-api-key": self.api_key, "Api-Revision": API_REVISION},
                )
        except httpx.HTTPError as exc:
            raise ProviderUnavailable(f"brak odpowiedzi ({type(exc).__name__})") from exc
        if response.status_code == 429:
            raise RateLimited
        if response.status_code >= 400:
            raise ProviderUnavailable(f"HTTP {response.status_code}: {_error_message(response)}")
        try:
            return response.json()
        except ValueError as exc:
            raise ProviderUnavailable("odpowiedź nie jest JSON-em") from exc


def _output_text(payload: dict) -> str:
    """Tekst odpowiedzi: kroki `model_output`, w nich fragmenty typu `text`."""
    return "".join(
        part.get("text") or ""
        for step in payload.get("steps") or []
        if step.get("type") == "model_output"
        for part in step.get("content") or []
        if part.get("type") == "text"
    )


def _billed_output_tokens(usage: dict) -> int | None:
    """Tokeny „myślenia" są rozliczane jak wyjściowe, a API podaje je osobno."""
    output = usage.get("total_output_tokens")
    if output is None:
        return None
    return output + (usage.get("total_thought_tokens") or 0)


def _error_message(response: httpx.Response) -> str:
    try:
        return str(response.json()["error"]["message"])[:200]
    except (ValueError, KeyError, TypeError):
        return response.reason_phrase
