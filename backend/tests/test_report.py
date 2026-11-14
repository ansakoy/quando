from backend import report

SITE = "https://example.test"

NO_DATA_TEXT = (
    "❗️❗️❗️ Нет необходимых данных для расчета сроков. "
    f"Внести данные можно здесь: {SITE}."
)


def make_medicine(
    name,
    num_pills=None,
    per_day=None,
    depletion_date=None,
    next_pick_up_date=None,
):
    medicine = {"name": name}
    if num_pills is not None:
        medicine["num_pills"] = num_pills
    if per_day is not None:
        medicine["per_day"] = per_day
    medicine["depletion_date"] = depletion_date
    medicine["next_pick_up_date"] = next_pick_up_date
    medicine["pick_ups"] = []
    return medicine


def make_record(record_id, start_date, next_date=None, medicines=None):
    return {
        "id": record_id,
        "start_date": start_date,
        "end_date": None,
        "next_date": next_date,
        "medicines": medicines if medicines is not None else [],
    }


FULL_RECORD = make_record(
    1,
    "2026-11-10",
    next_date="2026-12-06",
    medicines=[
        make_medicine(
            "Лекарство 1",
            num_pills=200,
            per_day=2,
            depletion_date="2027-01-04",
            next_pick_up_date="2026-12-27",
        ),
        make_medicine(
            "Лекарство 2",
            num_pills=130,
            per_day=1,
            depletion_date="2026-12-20",
            next_pick_up_date="2026-12-13",
        ),
    ],
)

EXPECTED_BODY = (
    "<b>Назначение от 10.11.2026</b>:\n"
    "\n"
    "Желательно получить новое в районе <b>06.12.2026</b>.\n"
    "\n"
    "Из лекарств первым заканчивается <b>Лекарство 2</b>, "
    "нужно получить еще в районе <b>13.12.2026</b>.\n"
    "\n"
    "<b>Подробности назначения</b>:\n"
    "\n"
    "- Лекарство 1: 200 таблеток, по 2 в день -> закончится 04.01.2027\n"
    "- Лекарство 2: 130 таблеток, по 1 в день -> закончится 20.12.2026"
)


class TestCaseC:
    def test_empty_records(self):
        assert report.build([], SITE) == NO_DATA_TEXT

    def test_no_next_date_anywhere(self):
        records = [
            make_record(1, "2026-01-01"),
            make_record(2, "2026-02-02", medicines=[make_medicine("X", 10, 1)]),
        ]
        assert report.build(records, SITE) == NO_DATA_TEXT


class TestCaseA:
    def test_latest_with_next_date_body_only(self):
        text = report.build([FULL_RECORD], SITE)
        assert text == EXPECTED_BODY
        assert "❗" not in text
        assert SITE not in text

    def test_dates_formatted_dd_mm_yyyy(self):
        text = report.build([FULL_RECORD], SITE)
        assert "10.11.2026" in text
        assert "06.12.2026" in text
        assert "2026-11-10" not in text

    def test_newline_structure(self):
        text = report.build([FULL_RECORD], SITE)
        assert not text.endswith("\n")
        assert text.count("\n\n") == 4
        details = text.split("\n\n")[-1]
        assert details.split("\n") == [
            "- Лекарство 1: 200 таблеток, по 2 в день -> закончится 04.01.2027",
            "- Лекарство 2: 130 таблеток, по 1 в день -> закончится 20.12.2026",
        ]

    def test_equal_start_dates_higher_id_is_latest(self):
        target = make_record(1, "2026-11-14", next_date="2026-12-06")
        latest = make_record(2, "2026-11-14", next_date="2026-12-10")
        text = report.build([target, latest], SITE)
        assert "❗" not in text
        assert "<b>Назначение от 14.11.2026</b>:" in text
        assert "<b>10.12.2026</b>" in text


class TestCaseB:
    def test_warning_mentions_latest_body_uses_fallback(self):
        latest = make_record(2, "2026-11-14")
        text = report.build([FULL_RECORD, latest], SITE)
        assert text.startswith(
            "❗️❗️❗️ Последним добавлено назначение от <b>14.11.2026</b>, "
            "но у него недостаточно данных для расчета сроков. "
            f"Нужно добавить данные на странице {SITE}. "
            "Ниже данные по последнему назначению, для которого рассчитаны сроки.\n\n"
        )
        assert text.endswith(EXPECTED_BODY)

    def test_fallback_is_first_with_next_date_in_reverse_order(self):
        records = [
            make_record(1, "2026-01-01", next_date="2026-02-01"),
            make_record(2, "2026-06-01", next_date="2026-07-01"),
            make_record(3, "2026-09-01"),
        ]
        text = report.build(records, SITE)
        assert "<b>Назначение от 01.06.2026</b>:" in text
        assert "<b>01.07.2026</b>" in text


class TestEarliestMedicine:
    def test_min_depletion_date_wins(self):
        record = make_record(
            1,
            "2026-01-01",
            next_date="2026-02-01",
            medicines=[
                make_medicine("Позднее", 10, 1, "2026-06-01", "2026-05-25"),
                make_medicine("Раннее", 10, 1, "2026-03-01", "2026-02-22"),
            ],
        )
        text = report.build([record], SITE)
        assert "первым заканчивается <b>Раннее</b>" in text
        assert "<b>22.02.2026</b>" in text

    def test_tie_goes_to_first_in_record(self):
        record = make_record(
            1,
            "2026-01-01",
            next_date="2026-02-01",
            medicines=[
                make_medicine("Первое", 10, 1, "2026-03-01", "2026-02-22"),
                make_medicine("Второе", 10, 1, "2026-03-01", "2026-02-22"),
            ],
        )
        text = report.build([record], SITE)
        assert "первым заканчивается <b>Первое</b>" in text

    def test_medicines_without_depletion_date_are_ignored(self):
        record = make_record(
            1,
            "2026-01-01",
            next_date="2026-02-01",
            medicines=[
                make_medicine("Без даты"),
                make_medicine("С датой", 10, 1, "2026-03-01", "2026-02-22"),
            ],
        )
        text = report.build([record], SITE)
        assert "первым заканчивается <b>С датой</b>" in text


class TestFormatting:
    def test_missing_values_render_dash(self):
        record = make_record(
            1,
            "2026-11-10",
            next_date="2026-12-06",
            medicines=[make_medicine("Препарат Г", per_day=1)],
        )
        text = report.build([record], SITE)
        assert "- Препарат Г: — таблеток, по 1 в день -> закончится —" in text
        assert "Из лекарств первым заканчивается" not in text

    def test_missing_per_day_renders_dash(self):
        record = make_record(
            1,
            "2026-11-10",
            next_date="2026-12-06",
            medicines=[make_medicine("Препарат Д", num_pills=30)],
        )
        text = report.build([record], SITE)
        assert "- Препарат Д: 30 таблеток, по — в день -> закончится —" in text

    def test_names_are_escaped_everywhere(self):
        name = "A & B <b>c</b>"
        record = make_record(
            1,
            "2026-11-10",
            next_date="2026-12-06",
            medicines=[
                make_medicine(name, 10, 1, "2026-12-20", "2026-12-13"),
            ],
        )
        text = report.build([record], SITE)
        assert "<b>A &amp; B &lt;b&gt;c&lt;/b&gt;</b>" in text
        assert "- A &amp; B &lt;b&gt;c&lt;/b&gt;: 10 таблеток" in text
        assert name not in text

    def test_fractional_per_day_preserved(self):
        record = make_record(
            1,
            "2026-11-10",
            next_date="2026-12-06",
            medicines=[make_medicine("X", 30, 0.5, "2027-01-09", "2027-01-02")],
        )
        text = report.build([record], SITE)
        assert "по 0.5 в день" in text
