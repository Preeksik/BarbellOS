"""Zgodność core/training.py z oryginalnym kodem planu.

Plik fixtures/training_reference.json zawiera wyniki policzone kodem JavaScript
z Plan_AMP_2027.html: zaokrąglenia, e1RM, podejścia, maksy treningowe i ciężary
wszystkich 601 pozycji planu.
"""

import json
from pathlib import Path

import pytest

from app.core import training as t

REF = json.loads((Path(__file__).parent / "fixtures" / "training_reference.json").read_text())


def test_rts_table_matches_original():
    assert list(t.RTS_PERCENT) == REF["rts"]


def test_rounding_matches_javascript():
    for x, rounded, floored in REF["rounding"]:
        assert t.round_to_step(x) == rounded, x
        assert t.floor_to_step(x) == floored, x


def test_js_round_rounds_half_up_not_to_even():
    assert t.js_round(44.5) == 45
    assert round(44.5) == 44  # dlatego nie używamy wbudowanego round


def test_e1rm():
    for kg, reps, rpe, expected in REF["e1rm"]:
        assert t.e1rm(kg, reps, rpe) == (pytest.approx(expected) if expected else None)


def test_attempts():
    for max_kg, lift, a1, a2, a3_low, a3_high in REF["attempts"]:
        assert t.attempts_for(max_kg, lift) == {
            "first": a1,
            "second": a2,
            "third": (a3_low, a3_high),
        }


def test_third_from_second():
    for kg, rpe, lift, expected_kg, inc in REF["third"]:
        assert t.third_from_second(kg, rpe, lift) == {"kg": expected_kg, "inc": inc}
    assert t.third_from_second(0, 8, "S") is None


def test_gl_coefficient():
    for bodyweight, expected in REF["gl"]:
        assert t.gl_coefficient(bodyweight) == pytest.approx(expected)


def test_training_max_defaults_and_overrides():
    for phase, lift, expected in REF["tm_default"]:
        assert t.tm_for(phase, lift, REF["def_tm1"], REF["inc"]) == expected
    overrides = REF["tm_override"]["overrides"]
    for phase, lift, expected in REF["tm_override"]["values"]:
        assert t.tm_for(phase, lift, REF["def_tm1"], REF["inc"], overrides) == expected


def test_every_load_in_the_plan():
    checked = 0
    for week, day, index, phase, lift, kind, percent, expected in REF["loads"]:
        exercise = {"lift": lift, "kind": kind, "percent_tm": percent}
        tm = t.tm_for(phase, lift, REF["def_tm1"], REF["inc"]) if lift else 0.0
        assert t.load_for(exercise, tm) == expected, (week, day, index)
        checked += expected is not None
    assert len(REF["loads"]) == 601
    assert checked == 330
