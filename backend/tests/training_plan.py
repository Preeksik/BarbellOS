"""Mały, sztuczny plan do testów treningu (prawdziwy plan jest poza repo, AGENTS.md, zasada 4).

Trzy szablony tygodni: faza 1 (ciężary ze stałego `fixed_kg` i z TM), faza 2 i tydzień
startowy liczony od daty zawodów. Kształt jak `seed/plan_amp_2027.json`.
"""

import copy


def make_plan() -> dict:
    return copy.deepcopy(PLAN)


PLAN = {
    "meta": {
        "name": "Plan testowy",
        "start_date": "2026-10-26",
        "test_date": "2026-11-10",
        "default_meet_date": "2026-11-29",
        "spring_block_start": "2026-10-26",
        "meet_name": "Zawody testowe",
        "meet_date_range": ["2026-11-15", "2026-12-20"],
        "weight_class_kg": 74,
    },
    "attempts": {
        "context_weeks": {"test": ["t01"], "meet": ["t02"]},
        "fallback_phase": {"test": 1, "meet": 2},
        "default_bodyweight": {"test": 75, "meet": 74, "goals": 74},
    },
    # Cztery zwykłe tygodnie przy domyślnej dacie: wtedy plan nie zmienia długości.
    "meet_date_adjustment": {"prefer_weeks": ["t02", "t01"], "spring_weeks": 4, "relative_days": 3},
    "goals": [
        {
            "label": "Zeszły rok",
            "S": 150,
            "B": 105,
            "D": 190,
            "bodyweight_kg": 73.6,
            "baseline": True,
        },
        {"label": "Realnie", "S": 187.5, "B": 135, "D": 227.5},
    ],
    "notes": {
        "rules": [
            {
                "title": "Jak czytać trening",
                "blocks": [{"type": "list", "items": [{"text": "RPE."}]}],
            },
            {"title": "Zepsuta sekcja", "blocks": [{"type": "obrazek"}]},
        ],
        "maxes": {"goals_title": "Cele", "goals_intro": [{"type": "p", "text": "Wstęp."}]},
        "start": {"meet_intro": [{"type": "p", "text": "Wpisz datę."}]},
        "season": [
            {"title": "Jesień", "text": "Do testu.", "last_week": 2},
            {"title": "Wiosna", "text": "Start."},
        ],
    },
    "training_max": {
        "phase_1": {"S": 160, "B": 120, "D": 200},
        "default_increment_by_phase": {"2": {"S": 5, "B": 2.5, "D": 5}},
    },
    "phases": {"1": "Akumulacja", "2": "Intensyfikacja"},
    "blocks": {
        "acc": {"name": "Akumulacja I", "focus": "Objętość i technika."},
        "int": {"name": "Intensyfikacja I", "focus": "Ciężej i mniej powtórzeń."},
        "meet": {"name": "Start", "focus": "Tydzień startowy."},
    },
    "holidays": {"2026-11-11": "Święto Niepodległości"},
    "exercises": {
        "Przysiad": {"lift": "S", "tiers": ["main"], "cue": "Pełna głębokość."},
        "Face pull": {"lift": None, "tiers": ["acc"], "cue": "Łokcie wysoko."},
    },
    "weeks": [
        {
            "id": "t01",
            "phase": 1,
            "block": "acc",
            "intensity_plate_kg": 10,
            "days": [
                {
                    "code": "D1",
                    "title": "Przysiad",
                    "minutes": 90,
                    "day_offset": 0,
                    "exercises": [
                        {
                            "name": "Przysiad",
                            "lift": "S",
                            "kind": "single",
                            "tier": "main",
                            "sets": 1,
                            "reps": 1,
                            "percent_tm": 89.2,
                            "rpe": "7",
                            "fixed_kg": 145,
                        },
                        {
                            "name": "Przysiad",
                            "lift": "S",
                            "kind": "sets",
                            "tier": "main",
                            "sets": 4,
                            "reps": 4,
                            "percent_tm": 78.0,
                            "rpe": "7",
                            "note": "Każde powtórzenie na pełną głębokość.",
                        },
                        {
                            "name": "Face pull",
                            "lift": None,
                            "kind": "acc",
                            "tier": "acc",
                            "sets": 3,
                            "reps": "15",
                            "weight_hint": "20",
                        },
                    ],
                },
                {
                    "code": "D2",
                    "title": "Ława",
                    "minutes": 70,
                    "day_offset": 2,
                    "exercises": [
                        {"name": "Face pull", "lift": None, "kind": "acc", "tier": "acc"},
                    ],
                },
            ],
        },
        {
            "id": "t02",
            "phase": 2,
            "block": "int",
            "intensity_plate_kg": 20,
            "note": "Nowy blok: ciężkie single.",
            "days": [
                {
                    "code": "D1",
                    "title": "Single",
                    "minutes": 80,
                    "day_offset": 1,
                    "exercises": [
                        {
                            "name": "Przysiad",
                            "lift": "S",
                            "kind": "single",
                            "tier": "main",
                            "sets": 1,
                            "reps": 1,
                            "percent_tm": 92.2,
                            "rpe": "8",
                        },
                        {"name": "Face pull", "lift": None, "kind": "acc", "tier": "acc"},
                    ],
                },
                {
                    "code": "D2",
                    "title": "Wolny przysiad",
                    "minutes": 60,
                    "day_offset": 2,
                    "exercises": [
                        {"name": "Face pull", "lift": None, "kind": "acc", "tier": "acc"},
                    ],
                },
            ],
        },
        {
            "id": "t03",
            "phase": 2,
            "block": "meet",
            "intensity_plate_kg": 25,
            "label": "AMP",
            "days": [
                {
                    "code": "OPT",
                    "title": "Otwarcia",
                    "minutes": 45,
                    "days_before_meet": 3,
                    "exercises": [
                        {"name": "Face pull", "lift": None, "kind": "acc", "tier": "acc"},
                    ],
                },
                {
                    "code": "AMP",
                    "title": "Zawody",
                    "minutes": 240,
                    "days_before_meet": 0,
                    "exercises": [
                        {
                            "name": "Przysiad",
                            "lift": "S",
                            "kind": "att",
                            "tier": "main",
                            "attempt": a,
                        }
                        for a in (1, 2, 3)
                    ],
                },
            ],
        },
    ],
}
