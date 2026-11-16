from datetime import date
from html import escape

PREFIX = "🔔 🔔 🔔 @{tg_username}"
PRESCRIPTION_BLOCK = "📋 Пора получать новое назначение! Старое истекает {end_date}."
MEDICINE_BLOCK = (
    "💊 <b>{name}</b>: пора получать новую порцию! Заканчивается {depletion_date}."
)
DASH = "—"


def _fmt_date(iso: str | None) -> str:
    if iso is None:
        return DASH
    return date.fromisoformat(iso).strftime("%d.%m.%Y")


def _prescription_block(record: dict) -> str:
    return PRESCRIPTION_BLOCK.format(end_date=_fmt_date(record.get("end_date")))


def _medicine_block(medicine: dict) -> str:
    return MEDICINE_BLOCK.format(
        name=escape(medicine["name"]),
        depletion_date=_fmt_date(medicine.get("depletion_date")),
    )


def build(records: list[dict], today: date, tg_username: str) -> str | None:
    """Текст напоминания на дату `today` или None, если совпадений нет."""
    today_iso = today.isoformat()
    blocks: list[str] = []
    for record in records:
        if record.get("next_date") == today_iso:
            blocks.append(_prescription_block(record))
        for medicine in record.get("medicines", []):
            if medicine.get("next_pick_up_date") == today_iso:
                blocks.append(_medicine_block(medicine))
    if not blocks:
        return None
    prefix = PREFIX.format(tg_username=tg_username)
    return prefix + "\n\n" + "\n\n".join(blocks)
