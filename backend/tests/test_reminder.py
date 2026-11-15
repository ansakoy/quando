from datetime import date

from backend import reminder

TODAY = date(2026, 4, 19)
TODAY_ISO = TODAY.isoformat()
TG_USERNAME = "quando_bot"

PREFIX = "🔔 🔔 🔔 @quando_bot"
PRESCRIPTION_BLOCK = "📋 Пора получать новое назначение! Старое истекает 03.05.2026."
MEDICINE_BLOCK = (
    "💊 <b>Препарат А</b>: пора получать новую порцию! Заканчивается 02.06.2026."
)


def make_medicine(name, depletion_date=None, next_pick_up_date=None):
    return {
        "name": name,
        "depletion_date": depletion_date,
        "next_pick_up_date": next_pick_up_date,
        "pick_ups": [],
    }


def make_record(record_id, end_date=None, next_date=None, medicines=None):
    return {
        "id": record_id,
        "start_date": "2026-03-02",
        "end_date": end_date,
        "next_date": next_date,
        "medicines": medicines if medicines is not None else [],
    }


def build(records, tg_username=TG_USERNAME, today=TODAY):
    return reminder.build(records, today, tg_username)


PRESCRIPTION_MATCH = make_record(1, end_date="2026-05-03", next_date=TODAY_ISO)
MEDICINE_MATCH = make_record(
    2,
    end_date="2026-06-02",
    next_date="2026-05-19",
    medicines=[make_medicine("Препарат А", "2026-06-02", TODAY_ISO)],
)


class TestNoReminders:
    def test_empty_records(self):
        assert build([]) is None

    def test_no_matching_dates(self):
        records = [
            make_record(1, end_date="2026-05-03", next_date="2026-04-18"),
            make_record(
                2, medicines=[make_medicine("X", "2026-06-02", "2026-04-20")]
            ),
        ]
        assert build(records) is None

    def test_overdue_dates_ignored(self):
        records = [
            make_record(1, end_date="2026-03-01", next_date="2026-02-15"),
            make_record(
                2, medicines=[make_medicine("X", "2026-03-01", "2026-02-22")]
            ),
        ]
        assert build(records) is None

    def test_future_dates_ignored(self):
        records = [
            make_record(1, end_date="2027-01-01", next_date="2026-12-18"),
            make_record(
                2, medicines=[make_medicine("X", "2027-01-01", "2026-12-25")]
            ),
        ]
        assert build(records) is None

    def test_null_dates_ignored(self):
        records = [
            make_record(1),
            make_record(2, medicines=[make_medicine("X")]),
        ]
        assert build(records) is None

    def test_missing_keys_ignored(self):
        assert build([{"id": 1, "medicines": [{}]}]) is None


class TestPrescriptionBlock:
    def test_prefix_and_block(self):
        assert build([PRESCRIPTION_MATCH]) == f"{PREFIX}\n\n{PRESCRIPTION_BLOCK}"

    def test_end_date_formatted_dd_mm_yyyy(self):
        text = build([PRESCRIPTION_MATCH])
        assert "03.05.2026" in text
        assert "2026-05-03" not in text

    def test_missing_end_date_renders_dash(self):
        text = build([make_record(1, next_date=TODAY_ISO)])
        assert text == f"{PREFIX}\n\n📋 Пора получать новое назначение! Старое истекает —."


class TestMedicineBlock:
    def test_prefix_and_block(self):
        text = build([MEDICINE_MATCH])
        assert text == f"{PREFIX}\n\n{MEDICINE_BLOCK}"
        assert "📋" not in text

    def test_name_is_escaped(self):
        record = make_record(
            1,
            medicines=[make_medicine("A & B <b>c</b>", "2026-06-02", TODAY_ISO)],
        )
        text = build([record])
        assert "<b>A &amp; B &lt;b&gt;c&lt;/b&gt;</b>" in text
        assert "A & B <b>c</b>" not in text

    def test_depletion_date_formatted(self):
        text = build([MEDICINE_MATCH])
        assert "02.06.2026" in text
        assert "2026-06-02" not in text

    def test_missing_depletion_date_renders_dash(self):
        record = make_record(1, medicines=[make_medicine("X", None, TODAY_ISO)])
        assert build([record]).endswith("Заканчивается —.")

    def test_medicine_without_pick_up_date_ignored(self):
        record = make_record(
            1,
            medicines=[
                make_medicine("Без даты", "2026-06-02"),
                make_medicine("С датой", "2026-07-01", TODAY_ISO),
            ],
        )
        text = build([record])
        assert "Без даты" not in text
        assert "<b>С датой</b>" in text


class TestBlockOrder:
    def test_prescription_block_before_medicine_block(self):
        text = build([PRESCRIPTION_MATCH, MEDICINE_MATCH])
        assert text == f"{PREFIX}\n\n{PRESCRIPTION_BLOCK}\n\n{MEDICINE_BLOCK}"

    def test_record_blocks_follow_storage_order(self):
        first = make_record(
            1, medicines=[make_medicine("Первое", "2026-05-01", TODAY_ISO)]
        )
        second = make_record(2, end_date="2026-05-03", next_date=TODAY_ISO)
        third = make_record(
            3, medicines=[make_medicine("Третье", "2026-05-02", TODAY_ISO)]
        )
        text = build([first, second, third])
        assert text.split("\n\n")[1:] == [
            "💊 <b>Первое</b>: пора получать новую порцию! Заканчивается 01.05.2026.",
            "📋 Пора получать новое назначение! Старое истекает 03.05.2026.",
            "💊 <b>Третье</b>: пора получать новую порцию! Заканчивается 02.05.2026.",
        ]

    def test_prescription_block_precedes_own_medicines(self):
        record = make_record(
            1,
            end_date="2026-05-03",
            next_date=TODAY_ISO,
            medicines=[make_medicine("Препарат А", "2026-06-02", TODAY_ISO)],
        )
        text = build([record])
        assert text == f"{PREFIX}\n\n{PRESCRIPTION_BLOCK}\n\n{MEDICINE_BLOCK}"

    def test_several_medicines_of_one_record(self):
        record = make_record(
            1,
            medicines=[
                make_medicine("Первое", "2026-05-01", TODAY_ISO),
                make_medicine("Не сегодня", "2026-06-01", "2026-05-25"),
                make_medicine("Второе", "2026-07-01", TODAY_ISO),
            ],
        )
        blocks = build([record]).split("\n\n")[1:]
        assert [block.split("<b>")[1].split("</b>")[0] for block in blocks] == [
            "Первое",
            "Второе",
        ]


class TestFormatting:
    def test_prefix_contains_tg_username(self):
        text = build([PRESCRIPTION_MATCH], tg_username="dr_house")
        assert text.startswith("🔔 🔔 🔔 @dr_house\n\n")

    def test_empty_tg_username_keeps_at_sign(self):
        text = build([PRESCRIPTION_MATCH], tg_username="")
        assert text.startswith("🔔 🔔 🔔 @\n\n")

    def test_blocks_separated_by_double_newline(self):
        text = build([PRESCRIPTION_MATCH, MEDICINE_MATCH])
        assert text.count("\n\n") == 2
        assert "\n\n\n" not in text

    def test_no_trailing_newline(self):
        text = build([PRESCRIPTION_MATCH, MEDICINE_MATCH])
        assert not text.endswith("\n")
        assert text.endswith(".")

    def test_single_block_has_one_separator(self):
        text = build([PRESCRIPTION_MATCH])
        assert text.count("\n\n") == 1

    def test_other_dates_do_not_shift_result(self):
        record = make_record(1, end_date="2026-05-03", next_date="2026-05-19")
        assert build([record], today=date(2026, 5, 19)) == (
            f"{PREFIX}\n\n{PRESCRIPTION_BLOCK}"
        )
        assert build([record], today=date(2026, 5, 20)) is None
