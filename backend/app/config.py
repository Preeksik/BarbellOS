"""Konfiguracja z zmiennych środowiskowych (plik .env w katalogu głównym repo).

Żadna wartość tajna nie ma sensownej wartości domyślnej: w trybie `prod` aplikacja
nie wystartuje bez SECRET_KEY, APP_PASSWORD_HASH i INGEST_TOKEN.
"""

from functools import lru_cache

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
