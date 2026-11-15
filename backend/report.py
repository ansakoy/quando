from datetime import date
from html import escape

NO_DATA = "❗️❗️❗️ Нет необходимых данных для расчета сроков. Внести данные можно здесь: {site_url}."
WARNING = (
    "❗️❗️❗️ Последним добавлено назначение от <b>{start_date}</b>, но у него недостаточно "
    "данных для расчета сроков. Нужно добавить данные на странице {site_url}. "
    "Ниже данные по последнему назначению, для которого рассчитаны сроки.\n\n"
)
DASH = "—"


def _fmt_date(iso: str | None) -> str:
    if iso is None:
        return DASH
    return date.fromisoformat(iso).strftime("%d.%m.%Y")


def _fmt_value(value) -> str:
    if value is None:
        return DASH
    return str(value)


def _pick_record(records: list[dict]) -> tuple[dict, dict] | None:
    """(последнее назначение, целевое назначение с непустым next_date) или None."""
    if not records:
        return None
    ordered = sorted(
        records, key=lambda record: (record["start_date"], record["id"]), reverse=True
    )
    latest = ordered[0]
    target = next((record for record in ordered if record.get("next_date")), None)
    if target is None:
        return None
    return latest, target


def _earliest_medicine(record: dict) -> dict | None:
    candidates = [
        medicine
        for medicine in record.get("medicines", [])
        if medicine.get("depletion_date") is not None
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda medicine: medicine["depletion_date"])


def _body(record: dict) -> str:
    paragraphs = [
        f"<b>Назначение от {_fmt_date(record['start_date'])}</b>:",
        f"Желательно получить новое в районе <b>{_fmt_date(record.get('next_date'))}</b>.",
    ]
    earliest = _earliest_medicine(record)
    if earliest is not None:
        paragraphs.append(
            f"Из лекарств первым заканчивается <b>{escape(earliest['name'])}</b>, "
            f"нужно получить еще в районе "
            f"<b>{_fmt_date(earliest.get('next_pick_up_date'))}</b>."
        )
    paragraphs.append("<b>Подробности назначения</b>:")
    details = [
        f"- <b>{escape(medicine['name'])}</b>: {_fmt_value(medicine.get('num_pills'))} таблеток, "
        f"по {_fmt_value(medicine.get('per_day'))} в день -> "
        f"закончится {_fmt_date(medicine.get('depletion_date'))}"
        for medicine in record.get("medicines", [])
    ]
    if details:
        paragraphs.append("\n".join(details))
    return "\n\n".join(paragraphs)


def build(records: list[dict], site_url: str) -> str:
    picked = _pick_record(records)
    if picked is None:
        return NO_DATA.format(site_url=site_url)
    latest, target = picked
    if latest is target:
        return _body(target)
    return WARNING.format(
        start_date=_fmt_date(latest["start_date"]), site_url=site_url
    ) + _body(target)
