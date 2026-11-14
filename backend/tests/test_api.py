import uuid

import pytest

from app.config import Settings
from app.main import create_app
from app.security import LoginLimiter, hash_password, verify_password
from tests.conftest import PASSWORD

# ---------- logowanie ----------


def test_password_hash_roundtrip():
    stored = hash_password("haslo-do-testu")
    assert stored.startswith("scrypt$")
    assert verify_password("haslo-do-testu", stored)
    assert not verify_password("inne-haslo", stored)
    assert not verify_password("cokolwiek", "")
    assert not verify_password("cokolwiek", "to-nie-jest-hash")


def test_login_flow(client):
    assert client.get("/api/auth/me").json() == {"authenticated": False, "auth_required": True}
    assert client.post("/api/auth/login", json={"password": "zle"}).status_code == 401
    assert client.post("/api/auth/login", json={"password": PASSWORD}).status_code == 200
    assert client.get("/api/auth/me").json()["authenticated"] is True
    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/me").json()["authenticated"] is False


def test_login_limiter_blocks_after_five_failures():
    limiter = LoginLimiter(limit=5, window_s=900)
    for _ in range(5):
        assert not limiter.blocked("1.2.3.4", now=100.0)
        limiter.record_failure("1.2.3.4", now=100.0)
    assert limiter.blocked("1.2.3.4", now=200.0)
    assert not limiter.blocked("5.6.7.8", now=200.0)
    assert not limiter.blocked("1.2.3.4", now=100.0 + 901)


def test_prod_refuses_to_start_without_secrets():
    with pytest.raises(RuntimeError, match="SECRET_KEY, APP_PASSWORD_HASH, INGEST_TOKEN"):
        create_app(
            Settings(
                _env_file=None,
                environment="prod",
                secret_key="",
                app_password_hash="",
                ingest_token="",
            )
        )


def test_database_url_is_normalised_to_psycopg3():
    settings = Settings(_env_file=None, database_url="postgresql://u:p@host/db?sslmode=require")
    assert settings.sqlalchemy_url == "postgresql+psycopg://u:p@host/db?sslmode=require"
    assert Settings(_env_file=None, database_url="postgres://u@h/d").sqlalchemy_url.startswith(
        "postgresql+psycopg://"
    )


# ---------- produkty ----------


def test_barcode_lookup_requires_login(client):
    assert client.get("/api/foods/barcode/5900000000015").status_code == 401


def test_barcode_is_fetched_once_then_served_from_own_database(logged_in, off_calls):
    first = logged_in.get("/api/foods/barcode/5900000000015").json()
    assert first["cached"] is False
    assert first["name"] == "Serek wiejski"
    assert first["per_100g"]["sat_fat_g"] == 3.5
    assert first["per_100g"]["fiber_g"] is None
    # mikroskładnik spoza słownika jest pomijany
    assert first["micros"] == [
        {"nutrient_id": "calcium", "amount_per_100g": 80.0, "source": "label"}
    ]

    second = logged_in.get("/api/foods/barcode/5900000000015").json()
    assert second["cached"] is True
    assert second["id"] == first["id"]
    assert off_calls == ["5900000000015"]


def test_unknown_and_invalid_barcodes(logged_in, off_calls):
    assert logged_in.get("/api/foods/barcode/4006381333931").status_code == 404
    assert logged_in.get("/api/foods/barcode/5900000000016").status_code == 422
    assert off_calls == ["4006381333931"]  # błędny kod nie wychodzi do sieci


# ---------- próba D ----------


def test_offline_probe_is_idempotent(logged_in):
    probe_id = str(uuid.uuid4())
    body = {"client_created_at": "2026-11-14T18:00:00+01:00", "note": "siłownia"}
    first = logged_in.put(f"/api/probe/{probe_id}", json=body)
    second = logged_in.put(f"/api/probe/{probe_id}", json=body)
    assert first.status_code == second.status_code == 200
    assert first.json()["received_at"] == second.json()["received_at"]
    assert len(logged_in.get("/api/probe").json()) == 1
