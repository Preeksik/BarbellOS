"""Suplementacja (23.11.2026): lista, odhaczanie, „To co wczoraj", seria dni."""

import datetime as dt
import uuid

import pytest

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


# ============================================================ składniki dawki (24.11.2026)


def test_to_native_units():
    from app.core.supplements import to_native

    assert to_native("vit_d", 2000, "IU", "µg") == 50  # 40 IU = 1 µg
    assert to_native("magnesium", 400, "mg", "mg") == 400
    assert to_native("vit_b12", 1, "mg", "µg") == 1000
    assert to_native("vit_b12", 500, "mcg", "µg") == 500
    assert to_native("zinc", 15000, "µg", "mg") == 15
    for bad in (("vit_a", 5000, "IU", "µg"), ("zinc", 0, "mg", "mg"), ("zinc", 5, "g", "mg")):
        with pytest.raises(ValueError):
            to_native(*bad)


def test_supplement_daily_divides_by_all_days():
    from app.core.supplements import supplement_daily

    doses = {"d3": {"vit_d": 50.0}, "mg": {"magnesium": 400.0}}
    taken = ["d3"] * 7 + ["mg"] * 3 + ["usuniety"]
    daily = supplement_daily(taken, doses, 7)
    assert daily == {"vit_d": 50.0, "magnesium": pytest.approx(400 * 3 / 7)}
    assert supplement_daily(taken, doses, 0) == {}


def _seed_nutrients(db_factory):
    from app.db.models import Nutrient

    with db_factory() as db:
        for nid, name, unit, grp, rda in (
            ("vit_d", "Witamina D", "µg", "vitamin", 5),
            ("magnesium", "Magnez", "mg", "mineral", 375),
        ):
            if db.get(Nutrient, nid) is None:
                db.add(Nutrient(id=nid, name_pl=name, unit=unit, grp=grp, rda=rda))
        db.commit()


def test_supplement_doses_count_in_week_coverage(logged_in, db_factory):
    _seed_nutrients(db_factory)
    d3 = str(uuid.uuid4())
    body = {"name": "Witamina D3", "dose": "2000 IU",
            "micros": [{"nutrient_id": "vit_d", "amount": 2000, "unit": "IU"}]}  # fmt: skip
    assert logged_in.put(f"/api/supplements/{d3}", json=body).status_code == 204
    day = logged_in.get("/api/supplements/day/2026-11-24").json()
    assert day["supplements"][0]["micros"] == [{"nutrient_id": "vit_d", "amount": 50.0}]

    for d in ("2026-11-18", "2026-11-20", "2026-11-22", "2026-11-23", "2026-11-24"):
        logged_in.put(f"/api/supplements/day/{d}", json={"taken_ids": [d3]})
    # Jedzenie zapisane tylko jednego dnia: suplement liczy się na wszystkie 7 dni.
    est = {"name": "kawa", "per_100": {"kcal": 39}}
    logged_in.put(
        f"/api/diary/entries/{uuid.uuid4()}",
        json={"date": "2026-11-24", "meal_slot": "lunch", "amount": 100, "estimate": est,
              "source": "text"},
    )  # fmt: skip
    week = logged_in.get("/api/diary/week/2026-11-24").json()
    vit_d = next(m for m in week["micros"] if m["nutrient_id"] == "vit_d")
    assert vit_d["supplement_amount"] == pytest.approx(50 * 5 / 7)
    assert vit_d["avg_amount"] == pytest.approx(50 * 5 / 7)  # kawa nie ma witaminy D
    assert vit_d["percent_rda"] == pytest.approx(50 * 5 / 7 / 5 * 100)


def test_supplement_dose_validation(logged_in, db_factory):
    _seed_nutrients(db_factory)
    sid = str(uuid.uuid4())

    def put(micro):
        return logged_in.put(f"/api/supplements/{sid}", json={"name": "X", "micros": [micro]})

    too_much = {"nutrient_id": "vit_d", "amount": 100000, "unit": "IU"}  # > 300 µg
    assert put(too_much).status_code == 422
    assert put({"nutrient_id": "nieznany", "amount": 1, "unit": "mg"}).status_code == 422
    assert put({"nutrient_id": "magnesium", "amount": 400, "unit": "IU"}).status_code == 422
    assert put({"nutrient_id": "magnesium", "amount": 400, "unit": "mg"}).status_code == 204
    # Zapis bez składników czyści skład.
    logged_in.put(f"/api/supplements/{sid}", json={"name": "X", "micros": []})
    assert logged_in.get("/api/supplements/day/2026-11-24").json()["supplements"][0]["micros"] == []
