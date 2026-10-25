from datetime import date
import logging
import re


logger = logging.getLogger(__name__)


MONTHS = {
# кириллица
    "янв": 1, "фев": 2, "мар": 3, "апр": 4, "мая": 5, "май": 5, "июн": 6,
    "июл": 7, "авг": 8, "сен": 9, "окт": 10, "ноя": 11, "дек": 12,
    # латиница
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

NUMERIC_RE = re.compile(r"^(\d{1,2})\.(\d{1,2})(?:\.(\d{4}|\d{2}))?$")
TEXT_RE = re.compile(r"^(\d{1,2})\s+([а-яёa-z]+)\.?(?:\s+(\d{4}))?(?:\s*г\.?)?$")


def parse_date(text: str, today: date | None = None) -> date:
    """Разбирает '1 окт', '01.10', '1 октября 2026', '1.10.2026' и т.п.
    Если год не указан, берётся текущий. Бросает ValueError при ошибке.
    Параметр today для работы не нужен, но будет полезен, если когда-нибудь сюда добавятся тесты
    """
    today = today or date.today()
    s = text.strip().lower()

    if m := NUMERIC_RE.match(s):
        day, month, year = int(m[1]), int(m[2]), m[3]
    elif m := TEXT_RE.match(s):
        day, year = int(m[1]), m[3]
        month = MONTHS.get(m[2][:3])
        if month is None:
            msg = f"Не удалось распознать месяц: {m[2]}"
            logger.error(msg)
            raise ValueError(msg)
    else:
        msg = "Не удалось распознать дату"
        logger.error(msg)
        raise ValueError(msg)

    if year is None:
        year = today.year
    else:
        year = int(year)
        if year < 100:
            year += 2000

    try:
        return date(year, month, day)  # ValueError, если даты не существует (31.02)
    except ValueError:
        msg = f"Даты {day}.{month}.{year} не существует"
        logger.error(msg)
        raise ValueError(msg)


def parse_drugs(text: str) -> tuple[list[dict], list[str]]:
    """Разбираем строки 'название, всего_таблеток, сколько_раз_в_день'.
    Возвращает (список препаратов, список ошибок)."""
    drugs, errors, seen = [], [], set()

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    for i, line in enumerate(lines, 1):
        parts = [p.strip() for p in line.split(",")]
        if len(parts) != 3:
            errors.append(
                f"Строка {i}: нужно 3 поля через запятую, найдено {len(parts)} "
                f"(дробное число нужно писать через точку: 0.5)"
            )
            continue

        name, pills_raw, per_day_raw = parts
        if not name:
            errors.append(f"Строка {i}: пустое название")
            continue
        if name.lower() in seen:
            errors.append(f"Строка {i}: «{name}» уже есть выше")
            continue

        try:
            num_pills = int(pills_raw)
            if num_pills <= 0:
                raise ValueError
        except ValueError:
            errors.append(f"Строка {i} ({name}): число таблеток должно быть целым и больше 0, а не «{pills_raw}»")
            continue

        try:
            per_day = float(per_day_raw)
            if per_day <= 0:
                raise ValueError
        except ValueError:
            errors.append(f"Строка {i} ({name}): приём в день должен быть числом больше 0, а не «{per_day_raw}»")
            continue
        if per_day.is_integer():
            per_day = int(per_day)

        seen.add(name.lower())
        drugs.append({"name": name, "num_pills": num_pills, "per_day": per_day})

    if not lines:
        errors.append("Не найдено ни одной строки с данными")
    return drugs, errors


if __name__ == "__main__":
    print(parse_date("31 янв"))