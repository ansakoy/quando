import json
import os
import tempfile
import threading
from datetime import datetime
from pathlib import Path

import settings
from constants import DELETED_AT


class StoreCorrupted(Exception):
    def __init__(self, path: Path, line_no: int):
        super().__init__(f"{path}: malformed NDJSON on line {line_no}")
        self.path = path
        self.line_no = line_no


_LOCK = threading.RLock()


def ensure_data_dir() -> None:
    settings.DATA_PATH.mkdir(parents=True, exist_ok=True)


def _read_ndjson(path: Path) -> list[dict]:
    if not path.exists():
        return []
    objects = []
    with path.open(encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            if not line.strip():
                continue
            try:
                objects.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise StoreCorrupted(path, line_no) from exc
    return objects


def _append_ndjson(path: Path, obj: dict) -> None:
    ensure_data_dir()
    if path.exists() and path.stat().st_size > 0:
        with path.open("rb") as fh:
            fh.seek(-1, os.SEEK_END)
            needs_leading_newline = fh.read(1) != b"\n"
    else:
        needs_leading_newline = False
    with path.open("a", encoding="utf-8") as fh:
        if needs_leading_newline:
            fh.write("\n")
        fh.write(json.dumps(obj, ensure_ascii=False) + "\n")
        fh.flush()


def _next_id() -> int:
    ids = []
    for path in (settings.PRESCRIPTIONS_PATH, settings.DELETED_PATH):
        for record in _read_ndjson(path):
            record_id = record.get("id")
            if isinstance(record_id, int):
                ids.append(record_id)
    return max(ids) + 1 if ids else 1


def read_prescriptions() -> list[dict]:
    with _LOCK:
        by_id: dict[int, dict] = {}
        for record in _read_ndjson(settings.PRESCRIPTIONS_PATH):
            by_id[record["id"]] = record
        return list(by_id.values())


def write_prescriptions(records: list[dict]) -> None:
    with _LOCK:
        ensure_data_dir()
        fd, tmp_name = tempfile.mkstemp(
            dir=settings.PRESCRIPTIONS_PATH.parent, suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                for record in records:
                    fh.write(json.dumps(record, ensure_ascii=False) + "\n")
            os.replace(tmp_name, settings.PRESCRIPTIONS_PATH)
        except BaseException:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise


def get_record(record_id: int) -> dict | None:
    with _LOCK:
        for record in read_prescriptions():
            if record["id"] == record_id:
                return record
        return None


def create_record(record: dict) -> dict:
    with _LOCK:
        records = read_prescriptions()
        new_record = {"id": _next_id(), **record}
        records.append(new_record)
        write_prescriptions(records)
        return new_record


def replace_record(record_id: int, record: dict) -> dict | None:
    with _LOCK:
        records = read_prescriptions()
        for index, existing in enumerate(records):
            if existing["id"] == record_id:
                records[index] = {"id": record_id, **record}
                write_prescriptions(records)
                return records[index]
        return None


def delete_record(record_id: int) -> dict | None:
    with _LOCK:
        records = read_prescriptions()
        target = next((r for r in records if r["id"] == record_id), None)
        if target is None:
            return None
        archived = {**target, DELETED_AT: datetime.now().isoformat(timespec="seconds")}
        _append_ndjson(settings.DELETED_PATH, archived)
        write_prescriptions([r for r in records if r["id"] != record_id])
        return archived
