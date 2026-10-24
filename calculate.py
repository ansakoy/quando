from dataclasses import dataclass
from datetime import date, timedelta
import logging

import yaml

from settings import CONDITIONS_PATH


logger = logging.getLogger(__name__)



def read_conditions():
    try:
        with open(CONDITIONS_PATH, encoding="utf-8") as handler:
            return yaml.safe_load(handler)
    except Exception as e:
        logger.error("Не удалось найти файл с условиями: %s", CONDITIONS_PATH)
        return []


CONDITIONS = read_conditions()

PICKUP_DATE = CONDITIONS.get("pickup_date")


@dataclass
class Drug:
    name: str
    tablets: int
    per_day: float = 1

    @property
    def supply_days(self) -> int:
        return int(self.tablets // self.per_day)


DRUGS = [Drug(entry["name"], entry["num_pills"], entry["per_day"]) for entry in CONDITIONS.get("data", [])]


def calc(pickup: date = PICKUP_DATE, drugs=DRUGS, warn_days: int = 14):
    ends = {d.name: pickup + timedelta(days=d.supply_days) for d in drugs}
    earliest_name = min(ends, key=ends.get)
    remind = ends[earliest_name] - timedelta(days=warn_days)
    return ends, earliest_name, remind


def say_world():
    return "world"


def build_report():
    ends, earliest_name, remind = calc()
    text = "**Расчет даты следующей выписки лекарств**\n\n"
    text += f"Дата получения: {PICKUP_DATE:%d.%m.%Y}\n"
    for drug in DRUGS:
        text += f"- {drug.name}: {drug.tablets} таблеток, по {drug.per_day} в день (всего дней: {drug.supply_days}) -> закончится {ends[drug.name]:%d.%m.%Y}\n"
    text += f"Раньше всех заканчивается {earliest_name} ({ends[drug.name]:%d.%m.%Y})\n\n"
    text += f"Желательно получить новое назначение в районе {remind:%d.%m.%Y}"
    return text


if __name__ == "__main__":
    print(build_report())