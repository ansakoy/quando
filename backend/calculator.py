import math
from datetime import date, timedelta
from fractions import Fraction

from constants import PICK_UP_DELTA_DAYS, PRESCRIPTION_DELTA_DAYS


def supply_days(pills: int, per_day: float) -> int:
    return max(1, math.ceil(pills / Fraction(str(per_day))))


def compute_medicine(medicine: dict) -> None:
    pick_ups = medicine.get("pick_ups") or []
    per_day = medicine.get("per_day")
    if per_day is None or not pick_ups:
        medicine["depletion_date"] = None
        medicine["next_pick_up_date"] = None
        for pick_up in pick_ups:
            pick_up["next_date"] = None
        return

    first = date.fromisoformat(min(pick_up["date"] for pick_up in pick_ups))
    cumulative = 0
    for pick_up in pick_ups:
        cumulative += pick_up["num_pills"]
        pick_up["next_date"] = (
            first
            + timedelta(days=supply_days(cumulative, per_day) - 1)
            - timedelta(days=PICK_UP_DELTA_DAYS)
        ).isoformat()

    depletion_date = first + timedelta(days=supply_days(cumulative, per_day) - 1)
    medicine["depletion_date"] = depletion_date.isoformat()
    medicine["next_pick_up_date"] = (
        depletion_date - timedelta(days=PICK_UP_DELTA_DAYS)
    ).isoformat()


def compute_prescription(record: dict) -> None:
    depletions = [
        medicine["depletion_date"]
        for medicine in record.get("medicines") or []
        if medicine.get("depletion_date") is not None
    ]
    end_date = min(depletions) if depletions else None
    record["end_date"] = end_date
    record["next_date"] = (
        date.fromisoformat(end_date) - timedelta(days=PRESCRIPTION_DELTA_DAYS)
    ).isoformat() if end_date else None


def recalculate(record: dict) -> dict:
    for medicine in record.get("medicines") or []:
        medicine["pick_ups"] = sorted(
            medicine.get("pick_ups") or [], key=lambda pick_up: pick_up["date"]
        )
        compute_medicine(medicine)
    compute_prescription(record)
    return record
