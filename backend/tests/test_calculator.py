import math

import pytest

from backend import calculator


def test_supply_days_integer_per_day():
    assert calculator.supply_days(90, 1) == 90
    assert calculator.supply_days(60, 2) == 30


def test_supply_days_float_trap():
    # math.ceil(1.1 / 0.1) == 12 with raw floats; Fraction(str(...)) keeps it 10.
    assert math.ceil(1.1 / 0.1) == 12
    assert calculator.supply_days(3, 0.3) == 10


def test_supply_days_minimum_is_one():
    assert calculator.supply_days(1, 0.1) == 10
    assert calculator.supply_days(1, 5) == 1


def test_compute_medicine_without_per_day_nulls_everything():
    medicine = {
        "name": "X",
        "pick_ups": [
            {"date": "2026-03-05", "num_pills": 10},
        ],
    }
    calculator.compute_medicine(medicine)
    assert medicine["depletion_date"] is None
    assert medicine["next_pick_up_date"] is None
    assert medicine["pick_ups"][0]["next_date"] is None


def test_compute_medicine_empty_pick_ups_nulls_dates():
    medicine = {"name": "X", "per_day": 1, "pick_ups": []}
    calculator.compute_medicine(medicine)
    assert medicine["depletion_date"] is None
    assert medicine["next_pick_up_date"] is None


def test_compute_medicine_cumulative_next_dates():
    medicine = {
        "name": "Б",
        "num_pills": 120,
        "per_day": 2,
        "pick_ups": [
            {"date": "2026-03-05", "num_pills": 60},
            {"date": "2026-04-03", "num_pills": 60},
        ],
    }
    calculator.compute_medicine(medicine)
    assert medicine["pick_ups"][0]["next_date"] == "2026-03-27"
    assert medicine["pick_ups"][1]["next_date"] == "2026-04-26"
    assert medicine["depletion_date"] == "2026-05-03"
    assert medicine["next_pick_up_date"] == "2026-04-26"
    assert medicine["next_pick_up_date"] == medicine["pick_ups"][-1]["next_date"]


def test_recalculate_example_record_1():
    record = {
        "id": 1,
        "start_date": "2026-03-02",
        "medicines": [
            {
                "name": "Препарат А",
                "num_pills": 90,
                "per_day": 1,
                "pick_ups": [{"date": "2026-03-05", "num_pills": 90}],
            },
            {
                "name": "Препарат Б",
                "num_pills": 120,
                "per_day": 2,
                "pick_ups": [
                    {"date": "2026-03-05", "num_pills": 60},
                    {"date": "2026-04-03", "num_pills": 60},
                ],
            },
        ],
    }
    calculator.recalculate(record)
    a, b = record["medicines"]
    assert a["depletion_date"] == "2026-06-02"
    assert a["next_pick_up_date"] == "2026-05-26"
    assert a["pick_ups"][0]["next_date"] == "2026-05-26"
    assert b["depletion_date"] == "2026-05-03"
    assert b["next_pick_up_date"] == "2026-04-26"
    assert record["end_date"] == "2026-05-03"
    assert record["next_date"] == "2026-04-19"


def test_recalculate_example_record_2_with_empty_pick_ups():
    record = {
        "id": 2,
        "start_date": "2026-09-28",
        "medicines": [
            {
                "name": "Препарат А",
                "num_pills": 90,
                "per_day": 1,
                "pick_ups": [{"date": "2026-10-01", "num_pills": 90}],
            },
            {
                "name": "Препарат В",
                "num_pills": 120,
                "per_day": 2,
                "pick_ups": [
                    {"date": "2026-10-01", "num_pills": 60},
                    {"date": "2026-10-30", "num_pills": 60},
                ],
            },
            {"name": "Препарат Г", "num_pills": 30, "per_day": 1, "pick_ups": []},
        ],
    }
    calculator.recalculate(record)
    a, b, g = record["medicines"]
    assert a["depletion_date"] == "2026-12-29"
    assert a["next_pick_up_date"] == "2026-12-22"
    assert b["depletion_date"] == "2026-11-29"
    assert g["depletion_date"] is None
    assert g["next_pick_up_date"] is None
    assert record["end_date"] == "2026-11-29"
    assert record["next_date"] == "2026-11-15"


def test_recalculate_sorts_pick_ups_ascending():
    record = {
        "start_date": "2026-01-01",
        "medicines": [
            {
                "name": "X",
                "per_day": 1,
                "pick_ups": [
                    {"date": "2026-02-01", "num_pills": 10},
                    {"date": "2026-01-01", "num_pills": 10},
                ],
            }
        ],
    }
    calculator.recalculate(record)
    dates = [p["date"] for p in record["medicines"][0]["pick_ups"]]
    assert dates == ["2026-01-01", "2026-02-01"]


def test_recalculate_no_medicines_gives_null_dates():
    record = {"id": 1, "start_date": "2026-03-02", "medicines": []}
    calculator.recalculate(record)
    assert record["end_date"] is None
    assert record["next_date"] is None


def test_recalculate_is_idempotent():
    record = {
        "start_date": "2026-03-02",
        "medicines": [
            {
                "name": "А",
                "num_pills": 90,
                "per_day": 1,
                "pick_ups": [{"date": "2026-03-05", "num_pills": 90}],
            }
        ],
    }
    first = calculator.recalculate(record)
    snapshot = repr(first)
    second = calculator.recalculate(first)
    assert repr(second) == snapshot


def test_recalculate_anchors_to_first_pick_up_not_start_date():
    record = {
        "start_date": "2026-03-02",
        "medicines": [
            {
                "name": "А",
                "per_day": 1,
                "pick_ups": [{"date": "2026-03-05", "num_pills": 90}],
            }
        ],
    }
    calculator.recalculate(record)
    assert record["medicines"][0]["depletion_date"] == "2026-06-02"
