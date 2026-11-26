"""API treningu (etap 4): import planu i starego dziennika, widoki, zapis wpisów."""

from tests.training_plan import make_plan

TODAY = "2026-11-02"

# Dziennik w formacie starego pliku HTML (klucz sesji → wpisy po indeksie ćwiczenia).
OLD_LOGS = {
    "t01-D1": {
        "e": {"0": {"kg": 160, "rpe": 8, "done": True}, "2": {"kg": 22.5, "reps": 15}},
        "gym": "Siłownia A",
        "bw": 78.4,
        "note": "Dobry dzień.",
        "at": "2026-10-26T18:30:00.000Z",
    },
    "t01-D2": {
        "e": {"0": {"kg": 25, "reps": 12, "rpe": 8, "done": True}},
        "gym": "Siłownia A",
        "at": "2026-10-28T19:00:00.000Z",
    },
    "t09-D1": {"e": {"0": {"kg": 100}}},  # sesji nie ma w planie
    "zle": {"e": {}},
}


def put_plan(client, **extra):
    return client.put("/api/training/plan", json={"plan": make_plan(), **extra})


def test_season_without_plan(logged_in):
    response = logged_in.get("/api/training/season", params={"today": TODAY})
    assert response.status_code == 200
    assert response.json()["plan_name"] is None
    assert logged_in.get("/api/training/week/0").status_code == 404


def test_import_plan_logs_and_settings(logged_in):
    response = put_plan(
        logged_in,
        logs=OLD_LOGS,
        settings={"tm": {"2": {"S": 170, "X": 1}}, "meet": "2026-11-29", "collars": True},
    )
    assert response.status_code == 200
    body = response.json()
    assert (body["weeks"], body["sessions"], body["imported_sessions"]) == (3, 6, 2)
    assert body["skipped"] == ["t09-D1", "zle"]

    week = logged_in.get("/api/training/week/0").json()
    d1 = week["sessions"][0]
    assert (d1["gym"], d1["bodyweight"], d1["log_note"]) == ("Siłownia A", 78.4, "Dobry dzień.")
    assert d1["status"] == "part"
    single, sets, acc = d1["exercises"]
    assert single["entry"] == {"kg": 160, "reps": None, "rpe": 8, "done": True, "ok": None}
    assert single["load"] == 145 and single["e1rm"] == 172.5  # 160 / 0,922 → 2,5 kg
    assert sets["load"] == 125
    assert sets["plates"] == [25, 25]  # z zaciskami ze starych ustawień
    assert sets["cue"] == "Każde powtórzenie na pełną głębokość."  # wskazówka pozycji
    assert acc["cue"] == "Łokcie wysoko."  # ogólna wskazówka ćwiczenia
    assert week["gyms"] == ["Siłownia A"]

    # TM fazy 2 wpisany ręcznie w starym pliku; nieznany bój pominięty.
    assert logged_in.get("/api/training/week/1").json()["tm"] == {"S": 170, "B": 122.5, "D": 205}


def test_import_twice_replaces_imported_sessions(logged_in):
    put_plan(logged_in, logs=OLD_LOGS)
    changed = {"t01-D1": {"e": {"1": {"kg": 120, "reps": 4, "rpe": 7}}}}
    assert put_plan(logged_in, logs=changed).json()["imported_sessions"] == 1
    week = logged_in.get("/api/training/week/0").json()
    entries = [e["entry"]["kg"] for e in week["sessions"][0]["exercises"]]
    assert entries == [None, 120, None]  # sesja z pliku zastąpiona w całości
    assert week["sessions"][1]["exercises"][0]["entry"]["kg"] == 25  # inne zostają


def test_import_rejects_broken_plan(logged_in):
    response = logged_in.put("/api/training/plan", json={"plan": {"weeks": []}})
    assert response.status_code == 422
    assert "start_date" in response.json()["detail"]


def test_season_view(logged_in):
    put_plan(logged_in, logs=OLD_LOGS)
    season = logged_in.get("/api/training/season", params={"today": TODAY}).json()
    assert season["plan_name"] == "Plan testowy"
    assert season["headline"] == "Tydzień 2 z 3 · Intensyfikacja I"
    assert season["countdowns"] == [
        {"days": 8, "label": "dni do testu 10.11"},
        {"days": 27, "label": "dni do zawodów (ok. 29.11)"},
    ]
    # Ostatnia zapisana sesja to t01-D2, więc pokazana jest następna w kolejności.
    assert season["position"] == {"week": 1, "day": 0, "rest": False}
    first = season["weeks"][0]
    assert (first["n"], first["plate"], first["done"], first["total"]) == (1, 10, 1, 2)
    assert season["weeks"][2]["label"] == "AMP"


def test_week_view_banner_and_last(logged_in):
    put_plan(logged_in, logs=OLD_LOGS)
    week = logged_in.get("/api/training/week/1").json()
    assert week["focus"] == "Nowy blok: ciężkie single."
    # Pierwszy tydzień fazy 2: z singla 160 na RPE 8 wychodzi TM 172,5 (obecny 165).
    assert week["banner"] == {
        "phase_name": "Intensyfikacja",
        "suggestions": [{"lift": "S", "kg": 172.5}],
    }
    face_pull = week["sessions"][0]["exercises"][1]
    assert face_pull["last"] == {
        "kg": 25,
        "reps": 12,
        "rpe": 8,
        "date": "2026-10-28",
        "gym": "Siłownia A",
    }
    assert logged_in.get("/api/training/week/2").json()["banner"] is None
    assert logged_in.get("/api/training/week/7").status_code == 404


def test_put_entry_is_idempotent_and_empty_deletes(logged_in):
    put_plan(logged_in)
    url = "/api/training/sessions/t02-D1/entries/0"
    body = {"kg": 175, "rpe": 8.5, "done": True}
    assert logged_in.put(url, json=body).status_code == 204
    assert logged_in.put(url, json=body).status_code == 204
    session = logged_in.get("/api/training/week/1").json()["sessions"][0]
    assert session["exercises"][0]["entry"]["kg"] == 175
    assert session["exercises"][0]["e1rm"] == 187.5  # 175 / 0,939
    assert session["status"] == "part"

    assert logged_in.put(url, json={}).status_code == 204
    session = logged_in.get("/api/training/week/1").json()["sessions"][0]
    assert session["exercises"][0]["entry"]["kg"] is None
    assert session["status"] == "none"

    assert logged_in.put("/api/training/sessions/t02-D1/entries/9", json={}).status_code == 404
    assert logged_in.put("/api/training/sessions/t09-D1/entries/0", json={}).status_code == 404
    assert logged_in.put(url, json={"rpe": 11}).status_code == 422


def test_put_session_fields(logged_in):
    put_plan(logged_in)
    url = "/api/training/sessions/t02-D1"
    body = {"gym": "  Siłownia B ", "bodyweight": 79.1, "note": " Lekko. "}
    assert logged_in.put(url, json=body).status_code == 204
    session = logged_in.get("/api/training/week/1").json()["sessions"][0]
    assert (session["gym"], session["bodyweight"], session["log_note"]) == (
        "Siłownia B",
        79.1,
        "Lekko.",
    )
    assert logged_in.put(url, json={"bodyweight": 5}).status_code == 422


def test_attempts_and_holiday(logged_in):
    put_plan(logged_in, settings={"meet": "2026-11-29"})
    url = "/api/training/sessions/t03-AMP/entries/0"
    assert logged_in.put(url, json={"kg": 170, "ok": "y"}).status_code == 204
    meet_week = logged_in.get("/api/training/week/2").json()
    amp = meet_week["sessions"][1]
    assert amp["days_before_meet"] == 0 and amp["date"] == "2026-11-29"
    assert amp["exercises"][0]["entry"]["ok"] == "y"
    assert amp["exercises"][0]["load"] is None  # podejścia wybiera arkusz, nie % TM


def test_training_requires_login(client):
    assert client.get("/api/training/season", params={"today": TODAY}).status_code == 401


def test_equipment_changes_plates(logged_in):
    assert logged_in.get("/api/training/equipment").json() == {
        "plates_25": True,
        "collars": False,
        "has_plan": False,
        "plan_name": None,
    }
    assert logged_in.put("/api/training/equipment", json={"plates_25": False}).status_code == 404
    put_plan(logged_in)
    sets = logged_in.get("/api/training/week/0").json()["sessions"][0]["exercises"][1]
    assert sets["load"] == 125 and sets["plates"] == [25, 25, 2.5]

    body = {"plates_25": False, "collars": True}
    assert logged_in.put("/api/training/equipment", json=body).status_code == 204
    assert logged_in.get("/api/training/equipment").json() == {
        **body,
        "has_plan": True,
        "plan_name": "Plan testowy",
    }
    sets = logged_in.get("/api/training/week/0").json()["sessions"][0]["exercises"][1]
    assert sets["plates"] == [20, 20, 10]  # (125 − 20 − 5) / 2 = 50 kg na stronę
    # Ponowny import planu nie zmienia sprzętu.
    put_plan(logged_in)
    assert logged_in.get("/api/training/equipment").json()["plates_25"] is False


# ---------------------------------------------------------------- część 2


def test_maxes_and_manual_tm(logged_in):
    put_plan(logged_in, logs=OLD_LOGS)
    maxes = logged_in.get("/api/training/maxes").json()
    assert [g["label"] for g in maxes["goals"]] == [
        "Zeszły rok",
        "Realnie",
    ]  # bez „Teraz”: tylko przysiad
    assert maxes["goals_intro"][0]["text"] == "Wstęp."
    phase2 = maxes["phases"][1]
    assert (phase2["phase"], phase2["first_week"], phase2["last_week"]) == (2, 2, 3)
    squat = phase2["lifts"][0]
    assert (squat["value"], squat["default"], squat["manual"], squat["suggestion"]) == (
        165,
        165,
        False,
        172.5,
    )
    assert maxes["points"][0]["e1rm_rounded"] == 172.5

    assert logged_in.put("/api/training/tm/2", json={"S": 172.5}).status_code == 204
    assert logged_in.get("/api/training/week/1").json()["tm"]["S"] == 172.5
    squat = logged_in.get("/api/training/maxes").json()["phases"][1]["lifts"][0]
    assert (squat["value"], squat["manual"], squat["suggestion"]) == (172.5, True, None)
    # Puste pola wracają do wartości z planu.
    assert logged_in.put("/api/training/tm/2", json={}).status_code == 204
    assert logged_in.get("/api/training/week/1").json()["tm"]["S"] == 165
    assert logged_in.put("/api/training/tm/9", json={}).status_code == 404


def test_calculator(logged_in):
    response = logged_in.get("/api/training/calculator", params={"kg": 150, "reps": 1, "rpe": 8})
    assert response.json() == {"e1rm": 162.5, "tm": 162.5}
    bad = logged_in.get("/api/training/calculator", params={"kg": 150, "reps": 8, "rpe": 8})
    assert bad.status_code == 422 and bad.json()["detail"] == "Powtórzenia 1–6, RPE 6–10."


def test_start_and_meet_date(logged_in):
    put_plan(logged_in, logs=OLD_LOGS)
    start = logged_in.get("/api/training/start").json()
    assert start["test"]["date"] == "2026-11-10" and start["test"]["week_index"] is None
    squat = start["test"]["attempts"]["rows"][0]
    # Test: single z t01 (160 na RPE 8 → e1RM 173,5).
    assert (squat["max"], squat["from_singles"], squat["first"], squat["second"]) == (
        172.5,
        True,
        157.5,
        167.5,
    )
    meet = start["meet"]
    assert (meet["name"], meet["date"], meet["week_index"]) == ("Zawody testowe", "2026-11-29", 2)
    assert meet["attempts"]["rows"][1]["from_singles"] is False  # ława z TM fazy 2
    assert meet["intro"][0]["text"] == "Wpisz datę."
    assert start["meet_default"] is True
    assert start["adjustment"] == "Plan ułożony bez zmian długości."
    assert start["results"][0]["label"] == "Zeszły rok" and start["results"][0]["baseline"]
    assert start["results"][-1]["empty"] is True

    body = {"date": "2026-12-06", "today": "2026-10-20"}
    assert logged_in.put("/api/training/meet", json=body).status_code == 204
    start = logged_in.get("/api/training/start").json()
    assert start["meet_default"] is False and start["meet"]["date"] == "2026-12-06"
    assert "dodatkowy tydzień 3 (powtórka tygodnia 2" in start["adjustment"]
    season = logged_in.get("/api/training/season", params={"today": TODAY}).json()
    assert [w["key"] for w in season["weeks"]] == ["t01", "t02", "t02b", "t03"]

    outside = logged_in.put(
        "/api/training/meet", json={"date": "2027-03-01", "today": "2026-10-20"}
    )
    assert outside.status_code == 422
    late = logged_in.put("/api/training/meet", json={"date": "2026-12-13", "today": "2026-12-01"})
    assert late.status_code == 422


def test_rules_season_groups_and_sheet(logged_in):
    put_plan(logged_in)
    rules = logged_in.get("/api/training/rules").json()["sections"]
    assert [s["title"] for s in rules] == ["Jak czytać trening"]  # zepsuta sekcja pominięta
    season = logged_in.get("/api/training/season", params={"today": TODAY}).json()
    assert season["groups"][0] == {"title": "Jesień", "text": "Do testu.", "last_week": 2}
    url = "/api/training/sessions/t03-AMP/entries/1"
    assert logged_in.put(url, json={"kg": 175, "ok": "y", "rpe": 8}).status_code == 204
    sheet = logged_in.get("/api/training/week/2").json()["sessions"][1]["sheet"]
    assert sheet["context"] == "meet" and sheet["bodyweight"] == 74
    assert sheet["lifts"][0]["hint"] == {"kind": "next", "kg": 182.5, "rpe": 8}
    assert sheet["best"]["S"] == 175 and sheet["total"] is None
    assert logged_in.get("/api/training/week/0").json()["sessions"][0]["sheet"] is None
