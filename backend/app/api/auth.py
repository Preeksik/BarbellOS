"""Logowanie jednego użytkownika: hasło -> ciasteczko sesji (HttpOnly, w prod także Secure)."""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.config import Settings, get_settings
from app.security import LoginLimiter, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])
limiter = LoginLimiter()


class LoginIn(BaseModel):
    password: str


class SessionOut(BaseModel):
    authenticated: bool
    auth_required: bool


@router.get("/me", response_model=SessionOut)
def me(request: Request, settings: Settings = Depends(get_settings)) -> SessionOut:
    required = not settings.auth_disabled
    return SessionOut(
        authenticated=not required or bool(request.session.get("user")), auth_required=required
    )


@router.post("/login", response_model=SessionOut)
def login(
    body: LoginIn, request: Request, settings: Settings = Depends(get_settings)
) -> SessionOut:
    client = request.client.host if request.client else "unknown"
    if limiter.blocked(client):
        raise HTTPException(429, "Za dużo prób. Spróbuj za kilkanaście minut.")
    if not verify_password(body.password, settings.app_password_hash):
        limiter.record_failure(client)
        raise HTTPException(401, "Nieprawidłowe hasło.")
    limiter.reset(client)
    request.session["user"] = True
    return SessionOut(authenticated=True, auth_required=True)


@router.post("/logout", status_code=204)
def logout(request: Request) -> None:
    request.session.clear()
