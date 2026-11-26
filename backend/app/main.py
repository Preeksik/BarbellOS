"""Aplikacja FastAPI. W produkcji ten sam proces serwuje API i zbudowany frontend (PWA)."""

import mimetypes
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from starlette.middleware.sessions import SessionMiddleware

from app import __version__
from app.api import (
    ai,
    auth,
    diary,
    diet,
    health,
    meals,
    probe,
    profile,
    supplements,
    targets,
    training,
    training_plan,
)
from app.config import Settings, get_settings

mimetypes.add_type("application/manifest+json", ".webmanifest")
mimetypes.add_type("application/wasm", ".wasm")

SESSION_MAX_AGE_S = 60 * 60 * 24 * 90


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    settings.validate_for_environment()

    app = FastAPI(
        title="BarbellOS",
        version=__version__,
        docs_url=None if settings.is_prod else "/api/docs",
        redoc_url=None,
        openapi_url=None if settings.is_prod else "/api/openapi.json",
    )
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key,
        session_cookie="barbellos_session",
        https_only=settings.is_prod,
        same_site="lax",
        max_age=SESSION_MAX_AGE_S,
    )
    for module in (
        health,
        auth,
        diet,
        diary,
        targets,
        meals,
        supplements,
        training,
        training_plan,
        profile,
        ai,
        probe,
    ):
        app.include_router(module.router)

    static = Path(settings.static_dir).resolve() if settings.static_dir else None
    if static and static.is_dir():
        _mount_frontend(app, static)
    return app


def _mount_frontend(app: FastAPI, static: Path) -> None:
    """Pliki z web/dist; nieznane ścieżki dostają index.html (aplikacja jednostronicowa)."""

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str) -> FileResponse:
        if path.startswith("api/"):
            raise HTTPException(404)
        candidate = (static / path).resolve()
        if path and candidate.is_file() and candidate.is_relative_to(static):
            # Service worker i manifest nie mogą być długo trzymane w pamięci podręcznej.
            no_cache = candidate.name in ("sw.js", "manifest.webmanifest", "registerSW.js")
            headers = {"Cache-Control": "no-cache"} if no_cache else None
            return FileResponse(candidate, headers=headers)
        return FileResponse(static / "index.html", headers={"Cache-Control": "no-cache"})


app = create_app()
