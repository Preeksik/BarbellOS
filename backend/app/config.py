"""Konfiguracja z zmiennych środowiskowych (plik .env w katalogu głównym repo).

Żadna wartość tajna nie ma sensownej wartości domyślnej: w trybie `prod` aplikacja
nie wystartuje bez SECRET_KEY, APP_PASSWORD_HASH i INGEST_TOKEN.
"""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_SECRET = "dev-only-change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    environment: str = "dev"  # dev | prod
    database_url: str = "sqlite:///./barbellos.db"
    secret_key: str = DEV_SECRET
    app_password_hash: str = ""
    ingest_token: str = ""
    default_timezone: str = "Europe/Warsaw"
    static_dir: str = ""

    off_user_agent: str = "BarbellOS/0.1 (prywatny projekt; kontakt w repozytorium)"
    off_base_url: str = "https://world.openfoodfacts.org"
    # Wyszukiwanie po nazwie (search-a-licious). Stare API nie ma wyszukiwania pełnotekstowego.
    off_search_url: str = "https://search.openfoodfacts.org"

    # USDA FoodData Central: witaminy i minerały produktów podstawowych (etap 6).
    # DEMO_KEY działa bez rejestracji, ale tylko ok. 10 zapytań na godzinę.
    fdc_api_key: str = "DEMO_KEY"
    fdc_base_url: str = "https://api.nal.usda.gov/fdc"
    # Produkt dodany do dziennika dopasowuje się do tabeli USDA w tle (decyzja z 18.11.2026).
    micros_autofill: bool = True

    # AI: na start działa tylko Gemini. Claude włącza się po dodaniu klucza.
    gemini_api_key: str = ""
    anthropic_api_key: str = ""
    # Modele z darmowego poziomu AI Studio (sprawdzone w dokumentacji 16.11.2026).
    gemini_model_cheap: str = "gemini-3.5-flash-lite"
    gemini_model_mid: str = "gemini-3.8-flash"
    gemini_base_url: str = "https://generativelanguage.googleapis.com"
    claude_model_cheap: str = "claude-haiku-5-5"
    claude_model_mid: str = "claude-sonnet-5-5"
    claude_model_strong: str = "claude-opus-5-5"

    @field_validator("app_password_hash", "secret_key", "ingest_token", mode="before")
    @classmethod
    def _clean_secret(cls, value):
        """Wartość wklejona w panelu hostingu bywa z apostrofami, nazwą zmiennej albo Enterem.

        Lokalny `.env` zdejmuje cudzysłowy sam, panel Render nie: `'scrypt$...'` z apostrofami
        nie pasowało do hasła i logowanie na serwerze nie działało (18.11.2026).
        """
        if not isinstance(value, str):
            return value
        cleaned = value.strip()
        for prefix in ("APP_PASSWORD_HASH=", "SECRET_KEY=", "INGEST_TOKEN="):
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix) :].strip()
        if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in "'\"":
            cleaned = cleaned[1:-1].strip()
        return cleaned

    @property
    def password_hash_looks_valid(self) -> bool:
        """Czy hash ma postać z `app.tools.hash_password` (bez ujawniania samej wartości)."""
        parts = self.app_password_hash.split("$")
        return len(parts) == 6 and parts[0] == "scrypt"

    @property
    def is_prod(self) -> bool:
        return self.environment == "prod"

    @property
    def auth_disabled(self) -> bool:
        """Logowanie jest wyłączone tylko lokalnie i tylko gdy nie ustawiono hasła."""
        return not self.is_prod and not self.app_password_hash

    @property
    def sqlalchemy_url(self) -> str:
        """Hosting podaje `postgres://` lub `postgresql://`; wymuszamy sterownik psycopg 3."""
        url = self.database_url
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                return "postgresql+psycopg://" + url[len(prefix) :]
        return url

    def validate_for_environment(self) -> None:
        if not self.is_prod:
            return
        missing = []
        if not self.secret_key or self.secret_key == DEV_SECRET:
            missing.append("SECRET_KEY")
        if not self.app_password_hash:
            missing.append("APP_PASSWORD_HASH")
        if not self.ingest_token:
            missing.append("INGEST_TOKEN")
        if missing:
            raise RuntimeError("Brak wymaganych zmiennych w trybie prod: " + ", ".join(missing))
        if not self.password_hash_looks_valid:
            raise RuntimeError(
                "APP_PASSWORD_HASH ma złą postać: powinna zaczynać się od scrypt$ "
                "i mieć 5 znaków $. Wygeneruj ją: python -m app.tools.hash_password"
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()
