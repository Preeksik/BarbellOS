from datetime import date, timedelta

import pytest

from app.core.barcode import is_valid_ean
from app.core.energy import adaptive_tdee, weight_trend
from app.core.nutrients import (
    fill_implied_zeros,
    macro_errors,
    macro_warnings,
    micro_coverage,
    portion_values,
    sum_values,
)
from app.core.readiness import readiness

D0 = date(2026, 11, 1)


# ---------- kody kreskowe ----------


@pytest.mark.parametrize("code", ["5900000000015", "4006381333931", "96385074", "036000291452"])
def test_valid_barcodes(code):
    assert is_valid_ean(code)


@pytest.mark.parametrize("code", ["5900000000016", "123", "59000000000a5", "", "4006381333932"])
def test_invalid_barcodes(code):
    assert not is_valid_ean(code)


# ---------- wartości odżywcze ----------


def test_portion_keeps_missing_values_missing():
    assert portion_values({"kcal": 200, "fiber_g": None}, 150) == {"kcal": 300, "fiber_g": None}


def test_sum_treats_missing_as_zero():
    total = sum_values([{"kcal": 300, "protein_g": 20}, {"kcal": 150, "protein_g": None}])
    assert total["kcal"] == 450
    assert total["protein_g"] == 20
    assert total["salt_g"] == 0


def test_micro_coverage_reports_how_much_of_the_day_had_data():
    entries = [
        {"kcal": 600, "micros": {"magnesium": {"amount": 150}}},
        {"kcal": 400, "micros": None},
    ]
    result = micro_coverage(entries, {"magnesium": 375, "iodine": 150})
    assert result["magnesium"]["percent_rda"] == pytest.approx(40)
    assert result["magnesium"]["kcal_share"] == pytest.approx(0.6)
    assert result["iodine"] == {"amount": 0.0, "percent_rda": 0.0, "kcal_share": 0.0}


# ---------- trend wagi i zapotrzebowanie ----------


def test_weight_trend_is_mean_of_last_seven_days():
    weights = {D0 + timedelta(days=i): 80.0 + i for i in range(10)}
    trend = weight_trend(weights)
    assert trend[D0] == 80.0
    assert trend[D0 + timedelta(days=9)] == pytest.approx(86.0)  # średnia z 83..89


def test_tdee_at_stable_weight_equals_intake():
    days = [D0 + timedelta(days=i) for i in range(15)]
    trend = dict.fromkeys(days, 75.0)
    estimate = adaptive_tdee(dict.fromkeys(days, 3000.0), trend)
    assert estimate.tdee_kcal == pytest.approx(3000)
    assert estimate.days == 14


def test_tdee_when_losing_weight_is_above_intake():
    days = [D0 + timedelta(days=i) for i in range(15)]
    trend = {d: 76.0 - i / 14 for i, d in enumerate(days)}  # 1 kg w 14 dni
    estimate = adaptive_tdee(dict.fromkeys(days, 2500.0), trend)
    assert estimate.tdee_kcal == pytest.approx(2500 + 7700 / 14)


def test_tdee_needs_two_weeks_and_a_complete_log():
    days = [D0 + timedelta(days=i) for i in range(15)]
    trend = dict.fromkeys(days, 75.0)
    assert adaptive_tdee(dict.fromkeys(days[:10], 3000.0), dict.fromkeys(days[:10], 75.0)) is None
    assert adaptive_tdee(dict.fromkeys(days[:8], 3000.0), trend) is None  # dziurawy dziennik


# ---------- regeneracja ----------

SLEEP = [450.0] * 14
HRV = [60.0, 62.0] * 14
RHR = [50.0, 52.0] * 14


def test_readiness_collects_data_before_baseline_exists():
    assert readiness(420, 60, 50, SLEEP[:5], HRV[:5], RHR[:5]).state == "collecting"


def test_readiness_green_on_a_normal_day():
    result = readiness(455, 61, 51, SLEEP, HRV, RHR)
    assert (result.state, result.factors) == ("green", [])


def test_readiness_yellow_after_short_sleep():
    result = readiness(300, 61, 51, SLEEP, HRV, RHR)
    assert (result.state, result.factors) == ("yellow", ["sleep_short"])


def test_readiness_red_when_several_signals_agree():
    result = readiness(300, 50, 58, SLEEP, HRV, RHR)
    assert result.state == "red"
    assert result.factors == ["sleep_short", "hrv_low", "resting_hr_high"]


# ---------- spójność wartości z etykiety ----------

MIRINDA_OFF = {
    "kcal": 20.9, "protein_g": 0, "fat_g": 0, "sat_fat_g": None,
    "carbs_g": 5.2, "sugars_g": None, "fiber_g": None, "salt_g": 0,
}  # fmt: skip


def test_zero_fat_implies_zero_saturated_fat():
    filled = fill_implied_zeros(MIRINDA_OFF)
    assert filled["sat_fat_g"] == 0
    assert filled["sugars_g"] is None  # węglowodany 5,2 g: cukrów nie da się wywnioskować
    assert filled["fiber_g"] is None
    assert MIRINDA_OFF["sat_fat_g"] is None  # wejście nie jest modyfikowane


def test_zero_carbs_implies_zero_sugars_but_known_values_stay():
    filled = fill_implied_zeros({"carbs_g": 0, "sugars_g": None, "fat_g": 0, "sat_fat_g": 0.0})
    assert (filled["sugars_g"], filled["sat_fat_g"]) == (0, 0)
    assert fill_implied_zeros({"fat_g": None, "sat_fat_g": None})["sat_fat_g"] is None


def test_macro_errors_and_unit_dependent_limit():
    assert macro_errors({"fat_g": 5, "sat_fat_g": 5}) == []
    assert len(macro_errors({"fat_g": 5, "sat_fat_g": 6, "kcal": 950})) == 2
    assert macro_errors({"carbs_g": 115}, unit="g") != []
    assert macro_errors({"carbs_g": 115}, unit="ml") == []  # 100 ml miodu waży ok. 140 g


def test_macro_warnings_tolerate_rounding_and_missing_values():
    cream = {"kcal": 244, "protein_g": 2.7, "fat_g": 21, "carbs_g": 10, "fiber_g": 0}
    assert macro_warnings(cream) == []
    assert macro_warnings({**cream, "kcal": 81}) != []
    assert macro_warnings({"kcal": 81, "protein_g": None, "fat_g": 1, "carbs_g": 2}) == []
    assert macro_warnings({"kcal": 21, "protein_g": 0, "fat_g": 0, "carbs_g": 5.0}) == []
