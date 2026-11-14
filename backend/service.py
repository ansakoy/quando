from datetime import date
from pathlib import PurePath

import settings
from backend import calculator, models, report, storage


class PrescriptionNotFound(Exception):
    pass


class BackupNotFound(Exception):
    pass


def build_quando_report() -> str:
    records = [models.serialize_record(record) for record in storage.read_prescriptions()]
    return report.build(records, settings.SITE_URL)


def get_backup(kind: str, today: date | None = None) -> tuple[str, bytes]:
    result = storage.read_backup(kind)
    if result is None:
        raise BackupNotFound(kind)
    name, content = result
    today = today or date.today()
    original = PurePath(name)
    return f"{original.stem}_{today:%Y%m%d}{original.suffix}", content


def _record_from_payload(start_date: date, medicines: list[models.MedicineIn]) -> dict:
    return {
        "start_date": start_date.isoformat(),
        "medicines": [medicine.model_dump(mode="json") for medicine in medicines],
    }


def list_prescriptions() -> list[dict]:
    records = storage.read_prescriptions()
    ordered = sorted(records, key=lambda record: record["id"], reverse=True)
    return [models.serialize_record(record) for record in ordered]


def get_prescription(prescription_id: int) -> dict:
    record = storage.get_record(prescription_id)
    if record is None:
        raise PrescriptionNotFound(prescription_id)
    return models.serialize_record(record)


def create_prescription(payload: models.PrescriptionCreate) -> dict:
    record = _record_from_payload(payload.start_date or date.today(), payload.medicines)
    calculator.recalculate(record)
    return models.serialize_record(storage.create_record(record))


def replace_prescription(
    prescription_id: int, payload: models.PrescriptionUpdate
) -> dict:
    record = _record_from_payload(payload.start_date, payload.medicines)
    calculator.recalculate(record)
    replaced = storage.replace_record(prescription_id, record)
    if replaced is None:
        raise PrescriptionNotFound(prescription_id)
    return models.serialize_record(replaced)


def delete_prescription(prescription_id: int) -> dict:
    archived = storage.delete_record(prescription_id)
    if archived is None:
        raise PrescriptionNotFound(prescription_id)
    return archived
