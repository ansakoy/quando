from dataclasses import dataclass
from datetime import date, timedelta
from html import escape
import logging
from math import floor
import os
import tempfile

import yaml

import constants as c
from settings import CONDITIONS_PATH


logger = logging.getLogger(__name__)



def load_conditions():
    """Получаем условия для расчетов из файла"""
    try:
        with open(CONDITIONS_PATH, encoding="utf-8") as handler:
            return yaml.safe_load(handler) or {}
    except FileNotFoundError:
        logger.error("Не удалось найти файл с условиями: %s", CONDITIONS_PATH)
        return {c.DATA: []}


@dataclass
class Drug:
    name: str
    tablets: int
    per_day: float = 1

    @property
    def supply_days(self) -> int:
        return int(self.tablets // self.per_day)


def calc(pickup: date, drugs, warn_days: int = 14):
    """Рассчитываем дату следующего назначения относительно даты получения и количества таблеток"""
    ends = {d.name: pickup + timedelta(days=d.supply_days) for d in drugs}
    earliest_name = min(ends, key=ends.get)
    remind = ends[earliest_name] - timedelta(days=warn_days)
    return ends, earliest_name, remind


def remaining_pills(drug: dict, pickup: date, today: date) -> tuple[float, int]:
    """Возвращает (остаток таблеток, дней хватит) на утро дня `today`,
    до приёма сегодняшней дозы."""
    elapsed = max(0, (today - pickup).days)  # если получение в будущем, остаток полный
    left = max(0, drug[c.NUM_PILLS] - drug[c.PER_DAY] * elapsed)
    return left, floor(left / drug[c.PER_DAY])


def build_report():
    """Формируем отчет о дате следующего назначения"""
    conditions = load_conditions()
    pickup_date = conditions.get(c.PICKUP_DATE)
    drugs = [Drug(entry[c.NAME], entry[c.NUM_PILLS], entry[c.PER_DAY]) for entry in conditions.get(c.DATA, [])]
    ends, earliest_name, remind = calc(pickup=pickup_date, drugs=drugs)
    text = "<b>Расчет даты следующей выписки лекарств</b>\n\n"
    text += f"Дата получения: {pickup_date:%d.%m.%Y}\n"
    for drug in drugs:
        text += (
            f"- {escape(drug.name)}: {drug.tablets} таблеток, "
            f"по {drug.per_day} в день (всего дней: {drug.supply_days}) "
            f"-> закончится {ends[drug.name]:%d.%m.%Y}\n"
        )
    text += (
        f"\nРаньше всех заканчивается <b>{escape(earliest_name)}</b> "
        f"({ends[earliest_name]:%d.%m.%Y})\n\n"
    )
    text += f"Желательно получить новое назначение в районе <b>{remind:%d.%m.%Y}</b>"
    return text


def build_today_report(today: date | None = None) -> str:
    today = today or date.today()
    conditions = load_conditions()
    pickup = conditions[c.PICKUP_DATE]

    text = f"<b>Остаток таблеток на {today:%d.%m.%Y}</b>\n\n"
    for drug in conditions[c.DATA]:
        left, days = remaining_pills(drug, pickup, today)
        end = today + timedelta(days=days)
        text += (
            f"- {escape(drug[c.NAME])}: <b>{left:g}</b> таблеток "
            f"(хватит на {days} дн., до {end:%d.%m.%Y})\n"
        )
    return text


def build_input_report(drugs):
    conditions = load_conditions()
    conditions[c.DATA] = drugs
    atomic_save(conditions)

    text = "<b>Список препаратов сохранён</b>\n\n"
    for d in drugs:
        days = floor(d[c.NUM_PILLS] / d[c.PER_DAY])
        text += (
            f"- {escape(d[c.NAME])}: {d[c.NUM_PILLS]} таблеток, "
            f"по {d[c.NUM_PILLS]} в день (всего дней: {days})\n"
        )
    text += "\nОсталось указать дату получения (команда /date <дата>)"
    return text


def atomic_save(conditions: dict) -> None:
    """Атомарная запись yaml"""
    dir_ = os.path.dirname(os.path.abspath(CONDITIONS_PATH))
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=dir_, delete=False, suffix=".tmp"
    ) as tmp:
        yaml.safe_dump(conditions, tmp, allow_unicode=True, sort_keys=False)
    os.replace(tmp.name, CONDITIONS_PATH)



def set_pickup_date(new_date: date) -> None:
    """Меняем только pickup_date, остальное содержимое файла не трогаем"""
    conditions = load_conditions()
    conditions["pickup_date"] = new_date
    atomic_save(conditions)



if __name__ == "__main__":
    print(build_report())