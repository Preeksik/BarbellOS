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
    assert first["per_100"]["sat_fat_g"] == 3.5
    assert first["per_100"]["fiber_g"] is None
    assert first["verified_at"] is None
    assert first["unit"] == "g"
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


# ---------- poprawianie i weryfikacja produktu ----------

EAN = "5900000000015"
LABEL = {
    "kcal": 97, "protein_g": 11, "fat_g": 5, "sat_fat_g": 3.5,
    "carbs_g": 2, "sugars_g": 2, "fiber_g": 0, "salt_g": 0.7,
}  # fmt: skip


def _update(client, food_id, **changes):
    body = {"name": "Serek wiejski", "brand": "Testowa", "unit": "g", "per_100": {**LABEL}}
    body["per_100"].update(changes.pop("per_100", {}))
    body.update(changes)
    return client.put(f"/api/foods/{food_id}", json=body)


def test_edit_requires_login(client):
    assert client.put("/api/foods/1", json={"name": "x", "per_100": {}}).status_code == 401
    assert client.post("/api/foods/1/verify").status_code == 401


def test_small_correction_is_saved_and_marks_product_verified(logged_in, off_calls):
    food = logged_in.get(f"/api/foods/barcode/{EAN}").json()
    response = _update(logged_in, food["id"], per_100={"kcal": 94})
    assert response.status_code == 200
    saved = response.json()
    assert saved["per_100"]["kcal"] == 94
    assert saved["per_100"]["fiber_g"] == 0
    assert saved["macro_source"] == "user"
    assert saved["origin"] == "off"  # pochodzenie rekordu się nie zmienia
    assert saved["verified_at"] is not None

    again = logged_in.get(f"/api/foods/barcode/{EAN}").json()
    assert again["per_100"]["kcal"] == 94
    assert again["cached"] is True
    assert off_calls == [EAN]  # poprawiony produkt nie jest nadpisywany danymi z OFF


def test_edit_is_idempotent(logged_in):
    food = logged_in.get(f"/api/foods/barcode/{EAN}").json()
    first = _update(logged_in, food["id"], per_100={"kcal": 94}).json()
    second = _update(logged_in, food["id"], per_100={"kcal": 94}).json()
    assert first["per_100"] == second["per_100"]


def test_empty_field_means_no_data_not_zero(logged_in):
    food = logged_in.get(f"/api/foods/barcode/{EAN}").json()
    saved = _update(logged_in, food["id"], per_100={"fiber_g": None}).json()
    assert saved["per_100"]["fiber_g"] is None


def test_unit_and_name_can_be_changed(logged_in):
    food = logged_in.get(f"/api/foods/barcode/{EAN}").json()
    saved = _update(logged_in, food["id"], name="  Napój  ", unit="ml", brand="").json()
    assert (saved["name"], saved["unit"], saved["brand"]) == ("Napój", "ml", None)


@pytest.mark.parametrize(
    ("changes", "fragment"),
    [
        ({"per_100": {"sat_fat_g": 9}}, "Kwasy nasycone (9 g) nie mogą przekraczać"),
        ({"per_100": {"sugars_g": 30}}, "Cukry (30 g) nie mogą przekraczać"),
        ({"per_100": {"protein_g": 140}}, "Białko: wartość 140 jest poza zakresem"),
        ({"per_100": {"kcal": -5}}, None),
        ({"name": "   "}, "Nazwa nie może być pusta"),
        ({"unit": "szt"}, None),
    ],
)
def test_impossible_values_are_rejected(logged_in, changes, fragment):
    food = logged_in.get(f"/api/foods/barcode/{EAN}").json()
    response = _update(logged_in, food["id"], **changes)
    assert response.status_code == 422
    if fragment:
        assert fragment in response.json()["detail"]
    assert logged_in.get(f"/api/foods/barcode/{EAN}").json()["verified_at"] is None


def test_typo_in_calories_gives_warning_but_saves(logged_in):
    food = logged_in.get(f"/api/foods/barcode/{EAN}").json()
    assert food["warnings"] == []
    saved = _update(logged_in, food["id"], per_100={"kcal": 79.0 * 10}).json()
    assert saved["per_100"]["kcal"] == 790
    assert "nie pasuje do makroskładników (wychodzi ok. 97 kcal)" in saved["warnings"][0]


def test_verify_keeps_values_and_source(logged_in):
    food = logged_in.get(f"/api/foods/barcode/{EAN}").json()
    verified = logged_in.post(f"/api/foods/{food['id']}/verify").json()
    assert verified["verified_at"] is not None
    assert verified["macro_source"] == "label"
    assert verified["per_100"] == food["per_100"]


def test_unknown_food_id(logged_in):
    assert _update(logged_in, 999).status_code == 404
    assert logged_in.post("/api/foods/999/verify").status_code == 404


@pytest.mark.parametrize(
    "pasted",
    [
        "'{h}'",  # z apostrofami, jak w .env
        '"{h}"',
        "APP_PASSWORD_HASH='{h}'",  # cała linia z .env
        "{h}" + chr(10),  # Enter na końcu (pole w panelu Render jest wielowierszowe)
        "  {h}  ",
    ],
)
def test_password_hash_pasted_in_hosting_panel_still_works(pasted):
    """Logowanie na serwerze nie działało, bo hash w panelu Render miał apostrofy (18.11.2026)."""
    stored = hash_password("haslo-do-serwera")
    settings = Settings(_env_file=None, app_password_hash=pasted.format(h=stored))
    assert settings.app_password_hash == stored
    assert verify_password("haslo-do-serwera", settings.app_password_hash)


def test_prod_refuses_to_start_with_malformed_hash():
    with pytest.raises(RuntimeError, match="APP_PASSWORD_HASH ma złą postać"):
        create_app(
            Settings(
                _env_file=None,
                environment="prod",
                secret_key="sekret",
                app_password_hash="scrypt$ucięty",
                ingest_token="token",
            )
        )
