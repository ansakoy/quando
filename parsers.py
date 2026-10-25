from datetime import date
import logging
import re


logger = logging.getLogger(__name__)


MONTHS = {
    "янв": 1, "фев": 2, "мар": 3, "апр": 4, "мая": 5, "май": 5, "июн": 6,
    "июл": 7, "авг": 8, "сен": 9, "окт": 10, "ноя": 11, "дек": 12,
}

NUMERIC_RE = re.compile(r"^(\d{1,2})\.(\d{1,2})(?:\.(\d{4}|\d{2}))?$")
TEXT_RE = re.compile(r"^(\d{1,2})\s+([а-яё]+)\.?(?:\s+(\d{4}))?(?:\s*г\.?)?$")


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


if __name__ == "__main__":
    print(parse_date("31 янв"))