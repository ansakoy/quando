from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator


class PickUpIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    date: date
    num_pills: int = Field(ge=1)


class MedicineIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    num_pills: int | None = Field(default=None, ge=1)
    per_day: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    pick_ups: list[PickUpIn] = []

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("name must be a non-empty string")
        return stripped


class PrescriptionCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    start_date: date | None = None
    medicines: list[MedicineIn] = []


class PrescriptionUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    start_date: date
    medicines: list[MedicineIn]


class PickUpOut(BaseModel):
    date: date
    next_date: date | None = None
    num_pills: int


class MedicineOut(BaseModel):
    name: str
    num_pills: int | None = None
    per_day: float | None = None
    depletion_date: date | None = None
    next_pick_up_date: date | None = None
    pick_ups: list[PickUpOut] = []

    @field_serializer("per_day")
    def _serialize_per_day(self, value: float | None) -> float | int | None:
        if value is None:
            return None
        return int(value) if float(value).is_integer() else value


class PrescriptionOut(BaseModel):
    id: int
    start_date: date
    end_date: date | None = None
    next_date: date | None = None
    medicines: list[MedicineOut] = []


def serialize_record(record: dict) -> dict:
    dumped = PrescriptionOut.model_validate(record).model_dump(mode="json")
    for medicine in dumped["medicines"]:
        for key in ("num_pills", "per_day"):
            if medicine[key] is None:
                del medicine[key]
    return dumped
