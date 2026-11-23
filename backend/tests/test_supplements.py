"""Suplementacja (23.11.2026): lista, odhaczanie, „To co wczoraj", seria dni."""

import datetime as dt
import uuid

from app.core.supplements import as_yesterday, last_days, streak, supplement_errors

D = dt.date(2026, 11, 23)


def _days(*offsets):
    return {D - dt.timedelta(days=o) for o in offsets}


# ====================================================================== core


def test_streak_counts_back_from_today_or_yesterday():
    assert streak(_days(0, 1, 2), D) == 3
    # Rano przed odhaczeniem: seria do wczoraj, a nie zero.
    assert streak(_days(1, 2, 3), D) == 3
    assert streak(_days(0, 2, 3), D) == 1  # przerwa wczoraj
    assert streak(set(), D) == 0
    assert streak(_days(2, 3), D) == 0  # nie wzięty ani dziś, ani wczoraj


def test_last_days_oldest_first():
    assert last_days(_days(0, 2, 6), D) == [True, False, False, False, True, False, True]
    assert last_days(set(), D, n=3) == [False, False, False]


def test_as_yesterday_adds_without_unticking():
    active = ["d3", "magnez", "kreatyna", "omega"]
    assert as_yesterday(["omega"], ["d3", "kreatyna", "stary"], active) == [
        "d3",
        "kreatyna",
        "omega",
    ]
    assert as_yesterday([], [], active) == []


def test_supplement_errors():
    assert supplement_errors("Witamina D3", "2000 IU") == []
    assert supplement_errors("  ", None) == ["Nazwa suplementu nie może być pusta."]
    assert len(supplement_errors("x" * 81, "y" * 41)) == 2


# ====================================================================== API


def _add(client, name, dose=None):
    sid = str(uuid.uuid4())
    assert (
        client.put(f"/api/supplements/{sid}", json={"name": name, "dose": dose}).status_code == 204
    )
    return sid


def test_list_tick_and_like_yesterday(logged_in):
    d3 = _add(logged_in, "Witamina D3", "2000 IU")
    mg = _add(logged_in, "Magnez", " ")  # pusta dawka = brak
    kre = _add(logged_in, "Kreatyna", "5 g")

    assert (
        logged_in.put("/api/supplements/day/2026-11-22", json={"taken_ids": [d3, kre]}).status_code
        == 204
    )
    # Powtórka z kolejki niczego nie zmienia.
    logged_in.put("/api/supplements/day/2026-11-22", json={"taken_ids": [d3, kre]})
    logged_in.put("/api/supplements/day/2026-11-23", json={"taken_ids": [mg]})

    day = logged_in.get("/api/supplements/day/2026-11-23").json()
    assert [(s["name"], s["dose"], s["taken"]) for s in day["supplements"]] == [
        ("Witamina D3", "2000 IU", False),
        ("Magnez", None, True),
        ("Kreatyna", "5 g", False),
    ]
    assert day["yesterday_ids"] == [d3, kre]

    # „To co wczoraj": dodaje D3 i kreatynę, magnez zostaje odhaczony.
    assert logged_in.post("/api/supplements/day/2026-11-23/as-yesterday").status_code == 204
    logged_in.post("/api/supplements/day/2026-11-23/as-yesterday")  # powtórka
    day = logged_in.get("/api/supplements/day/2026-11-23").json()
    assert day["taken_ids"] == [d3, mg, kre]
    d3_row = day["supplements"][0]
    assert d3_row["streak"] == 2 and d3_row["last7"][-2:] == [True, True]

    # Odznaczenie: stan dnia zapisany w całości.
    logged_in.put("/api/supplements/day/2026-11-23", json={"taken_ids": [mg]})
    assert logged_in.get("/api/supplements/day/2026-11-23").json()["taken_ids"] == [mg]


def test_delete_keeps_history_and_readding_restores(logged_in):
    d3 = _add(logged_in, "Witamina D3")
    logged_in.put("/api/supplements/day/2026-11-22", json={"taken_ids": [d3]})
    assert logged_in.delete(f"/api/supplements/{d3}").status_code == 204
    assert logged_in.delete(f"/api/supplements/{d3}").status_code == 204  # idempotentne
    assert logged_in.get("/api/supplements/day/2026-11-23").json()["supplements"] == []

    logged_in.put(f"/api/supplements/{d3}", json={"name": "Witamina D3 + K2", "dose": "1 kaps."})
    back = logged_in.get("/api/supplements/day/2026-11-23").json()["supplements"]
    assert [(s["name"], s["streak"]) for s in back] == [("Witamina D3 + K2", 1)]  # historia została


def test_validation_and_unknown_supplement(logged_in):
    sid = str(uuid.uuid4())
    assert logged_in.put(f"/api/supplements/{sid}", json={"name": " "}).status_code == 422
    unknown = {"taken_ids": [str(uuid.uuid4())]}
    assert logged_in.put("/api/supplements/day/2026-11-23", json=unknown).status_code == 404
    assert logged_in.get("/api/supplements/day/2026-11-23").json()["supplements"] == []
