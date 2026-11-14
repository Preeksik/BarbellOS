from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.core.health_ingest import IngestError, parse_ingest
from tests.conftest import INGEST_TOKEN

AUTH = {"Authorization": f"Bearer {INGEST_TOKEN}"}
WEIGHT = {
    "type": "weight",
    "unit": "kg",
    "source": "OKOK",
    "starts": ["2026-11-10T07:02:00+01:00", "2026-11-11T07:05:00+01:00"],
    "values": [75.4, 75.1],
}


# ---------- parser ----------


def test_parses_lists():
    samples = parse_ingest("weight", WEIGHT["starts"], WEIGHT["values"], unit="kg")
    assert [s.value for s in samples] == [75.4, 75.1]
    assert samples[0].starts_at == datetime(2026, 11, 10, 7, 2, tzinfo=timezone(timedelta(hours=1)))


def test_parses_multiline_text_with_decimal_comma_and_unit():
    samples = parse_ingest(
        "weight",
        starts="2026-11-10T07:02:00+01:00\n2026-11-11T07:05:00+01:00\n",
        values="75,4 kg\n75,1 kg",
    )
    assert [s.value for s in samples] == [75.4, 75.1]


def test_dates_without_timezone_are_treated_as_warsaw_time():
    (sample,) = parse_ingest("steps", ["2026-07-01T12:00:00"], [1000])
    assert sample.starts_at.astimezone(UTC) == datetime(2026, 7, 1, 10, 0, tzinfo=UTC)


def test_text_values_become_labels():
    (sample,) = parse_ingest(
        "sleep", ["2026-11-10T23:30:00+01:00"], ["REM"], ends=["2026-11-11T00:10:00+01:00"]
    )
    assert (sample.value, sample.label) == (None, "REM")
    assert sample.ends_at is not None


def test_duplicate_start_in_one_request_keeps_the_last_value():
    samples = parse_ingest("weight", ["2026-11-10T07:00:00+01:00"] * 2, [75.0, 75.5])
    assert [s.value for s in samples] == [75.5]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"type": "blood_type", "starts": [], "values": []},
        {"type": "weight", "starts": ["2026-11-10T07:00:00+01:00"], "values": []},
        {"type": "weight", "starts": ["wczoraj rano"], "values": [75]},
    ],
)
def test_rejects_bad_input(kwargs):
    with pytest.raises(IngestError):
        parse_ingest(**kwargs)


# ---------- endpoint ----------


def test_ingest_requires_token(client):
    assert client.post("/api/health/ingest", json=WEIGHT).status_code == 401
    wrong = {"Authorization": "Bearer zly-token"}
    assert client.post("/api/health/ingest", json=WEIGHT, headers=wrong).status_code == 401


def test_ingest_is_idempotent(client):
    first = client.post("/api/health/ingest", json=WEIGHT, headers=AUTH)
    assert first.json() == {"received": 2, "inserted": 2, "updated": 0}

    again = client.post("/api/health/ingest", json=WEIGHT, headers=AUTH)
    assert again.json() == {"received": 2, "inserted": 0, "updated": 0}

    corrected = {**WEIGHT, "values": [75.4, 74.9]}
    third = client.post("/api/health/ingest", json=corrected, headers=AUTH)
    assert third.json() == {"received": 2, "inserted": 0, "updated": 1}


def test_ingest_reports_readable_error(client):
    bad = {**WEIGHT, "values": [75.4]}
    response = client.post("/api/health/ingest", json=bad, headers=AUTH)
    assert response.status_code == 422
    assert "różni się" in response.json()["detail"]


def test_summary_needs_login_and_shows_latest_sample(client):
    client.post("/api/health/ingest", json=WEIGHT, headers=AUTH)
    assert client.get("/api/health/summary").status_code == 401

    from tests.conftest import PASSWORD

    client.post("/api/auth/login", json={"password": PASSWORD})
    (row,) = client.get("/api/health/summary").json()
    assert (row["type"], row["count"], row["last_value"], row["source"]) == (
        "weight", 2, 75.1, "OKOK",
    )  # fmt: skip


def test_healthz_is_public_and_light(client):
    assert client.get("/api/healthz").json()["status"] == "ok"
