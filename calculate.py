from dataclasses import dataclass
from datetime import date, timedelta
from html import escape
import logging
import os
import tempfile

import yaml

from settings import CONDITIONS_PATH


logger = logging.getLogger(__name__)



def read_conditions():
    try:
        with open(CONDITIONS_PATH, encoding="utf-8") as handler:
            return yaml.safe_load(handler) or {}
    except FileNotFoundError:
        logger.error("Не удалось найти файл с условиями: %s", CONDITIONS_PATH)
        return {"data": []}


@dataclass
class Drug:
    name: str
    tablets: int
    per_day: float = 1

    @property
    def supply_days(self) -> int:
        return int(self.tablets // self.per_day)


def calc(pickup: date, drugs, warn_days: int = 14):
    ends = {d.name: pickup + timedelta(days=d.supply_days) for d in drugs}
    earliest_name = min(ends, key=ends.get)
    remind = ends[earliest_name] - timedelta(days=warn_days)
    return ends, earliest_name, remind


def build_report():
    conditions = read_conditions()
    pickup_date = conditions.get("pickup_date")
    drugs = [Drug(entry["name"], entry["num_pills"], entry["per_day"]) for entry in conditions.get("data", [])]
    ends, earliest_name, remind = calc(pickup=pickup_date)
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


def set_pickup_date(new_date: date) -> None:
    """Меняем только pickup_date, остальное содержимое файла не трогаем"""
    try:
        with open(CONDITIONS_PATH, encoding="utf-8") as handler:
            conditions = yaml.safe_load(handler) or {}
    except FileNotFoundError:
        conditions = {"data": []}

    conditions["pickup_date"] = new_date

    # атомарная запись: пишем во временный файл и подменяем
    dir_ = os.path.dirname(os.path.abspath(CONDITIONS_PATH))
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=dir_, delete=False, suffix=".tmp"
    ) as tmp:
        yaml.safe_dump(conditions, tmp, allow_unicode=True, sort_keys=False)
    os.replace(tmp.name, CONDITIONS_PATH)


if __name__ == "__main__":
    print(build_report())