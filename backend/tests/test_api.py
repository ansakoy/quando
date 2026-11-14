import json
import re
from datetime import date

import settings

FULL_PAYLOAD = {
    "start_date": "2026-03-02",
    "medicines": [
        {
            "name": "Препарат А",
            "num_pills": 90,
            "per_day": 1,
            "pick_ups": [{"date": "2026-03-05", "num_pills": 90}],
        },
        {
            "name": "Препарат Б",
            "num_pills": 120,
            "per_day": 2,
            "pick_ups": [
                {"date": "2026-04-03", "num_pills": 60},
                {"date": "2026-03-05", "num_pills": 60},
            ],
        },
    ],
}


def read_lines(path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


class TestGetList:
    def test_empty_list(self, client):
        response = client.get("/api/prescriptions/")
        assert response.status_code == 200
        assert response.json() == []

    def test_ordered_by_id_descending(self, client):
        client.post("/api/prescriptions/", json={})
        client.post("/api/prescriptions/", json={})
        client.post("/api/prescriptions/", json={})
        response = client.get("/api/prescriptions/")
        assert [item["id"] for item in response.json()] == [3, 2, 1]

    def test_corrupt_line_returns_500(self, client, prescriptions_path):
        prescriptions_path.parent.mkdir(parents=True, exist_ok=True)
        prescriptions_path.write_text("{not json}\n", encoding="utf-8")
        response = client.get("/api/prescriptions/")
        assert response.status_code == 500
        assert "detail" in response.json()

    def test_duplicate_ids_last_occurrence_wins(self, client, prescriptions_path):
        prescriptions_path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            {"id": 1, "start_date": "2026-01-01", "end_date": None, "next_date": None, "medicines": []},
            {"id": 1, "start_date": "2026-02-02", "end_date": None, "next_date": None, "medicines": []},
        ]
        prescriptions_path.write_text(
            "".join(json.dumps(line, ensure_ascii=False) + "\n" for line in lines),
            encoding="utf-8",
        )
        response = client.get("/api/prescriptions/")
        assert response.status_code == 200
        assert response.json() == [lines[1]]


class TestPost:
    def test_minimal_record_defaults_to_today(self, client):
        response = client.post("/api/prescriptions/", json={})
        assert response.status_code == 201
        assert response.json() == {
            "id": 1,
            "start_date": date.today().isoformat(),
            "end_date": None,
            "next_date": None,
            "medicines": [],
        }

    def test_completely_empty_body(self, client):
        response = client.post("/api/prescriptions/", content=b"")
        assert response.status_code == 400

    def test_computed_fields_match_example(self, client):
        response = client.post("/api/prescriptions/", json=FULL_PAYLOAD)
        assert response.status_code == 201
        body = response.json()
        assert body["end_date"] == "2026-05-03"
        assert body["next_date"] == "2026-04-19"
        first, second = body["medicines"]
        assert first["depletion_date"] == "2026-06-02"
        assert first["next_pick_up_date"] == "2026-05-26"
        assert second["pick_ups"] == [
            {"date": "2026-03-05", "next_date": "2026-03-27", "num_pills": 60},
            {"date": "2026-04-03", "next_date": "2026-04-26", "num_pills": 60},
        ]

    def test_readonly_fields_in_body_are_ignored(self, client):
        payload = {
            "id": 999,
            "start_date": "2026-03-02",
            "end_date": "1999-01-01",
            "next_date": "1999-01-01",
            "medicines": [
                {
                    "name": "X",
                    "depletion_date": "1999-01-01",
                    "next_pick_up_date": "1999-01-01",
                    "pick_ups": [{"date": "2026-03-05", "next_date": "1999-01-01", "num_pills": 10}],
                }
            ],
        }
        response = client.post("/api/prescriptions/", json=payload)
        assert response.status_code == 201
        body = response.json()
        assert body["id"] == 1
        assert body["end_date"] is None
        assert body["medicines"][0]["depletion_date"] is None
        assert body["medicines"][0]["pick_ups"][0]["next_date"] is None

    def test_sequential_ids(self, client):
        first = client.post("/api/prescriptions/", json={}).json()
        second = client.post("/api/prescriptions/", json={}).json()
        assert (first["id"], second["id"]) == (1, 2)

    def test_validation_errors_return_400(self, client):
        cases = [
            {"start_date": "02.03.2026"},
            {"start_date": "not-a-date"},
            {"medicines": [{"num_pills": 1}]},
            {"medicines": [{"name": ""}]},
            {"medicines": [{"name": "   "}]},
            {"medicines": [{"name": "X", "num_pills": 0}]},
            {"medicines": [{"name": "X", "per_day": 0}]},
            {"medicines": [{"name": "X", "per_day": -1}]},
            {"medicines": [{"name": "X", "pick_ups": [{"date": "2026-03-05"}]}]},
            {"medicines": [{"name": "X", "pick_ups": [{"num_pills": 5}]}]},
            {"medicines": [{"name": "X", "pick_ups": [{"date": "2026-03-05", "num_pills": 0}]}]},
        ]
        for payload in cases:
            response = client.post("/api/prescriptions/", json=payload)
            assert response.status_code == 400, payload
            assert "detail" in response.json()

    def test_stored_line_format(self, client, prescriptions_path):
        client.post(
            "/api/prescriptions/",
            json={
                "start_date": "2026-03-02",
                "medicines": [{"name": "Препарат А", "per_day": 2}],
            },
        )
        raw = prescriptions_path.read_text(encoding="utf-8")
        assert raw.endswith("\n")
        assert raw.count("\n") == 1
        assert "Препарат А" in raw


class TestGetOne:
    def test_found(self, client):
        created = client.post("/api/prescriptions/", json=FULL_PAYLOAD).json()
        response = client.get(f"/api/prescriptions/{created['id']}/")
        assert response.status_code == 200
        assert response.json() == created

    def test_unknown_id_returns_404(self, client):
        response = client.get("/api/prescriptions/42/")
        assert response.status_code == 404
        assert "detail" in response.json()

    def test_non_integer_id_returns_400(self, client):
        response = client.get("/api/prescriptions/abc/")
        assert response.status_code == 400


class TestPut:
    def test_full_replace(self, client):
        created = client.post("/api/prescriptions/", json=FULL_PAYLOAD).json()
        response = client.put(
            f"/api/prescriptions/{created['id']}/",
            json={"start_date": "2026-09-28", "medicines": [{"name": "Метформин"}]},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["id"] == created["id"]
        assert body["start_date"] == "2026-09-28"
        assert body["end_date"] is None
        assert body["medicines"] == [
            {
                "name": "Метформин",
                "depletion_date": None,
                "next_pick_up_date": None,
                "pick_ups": [],
            }
        ]

    def test_id_is_never_mutated(self, client, prescriptions_path):
        created = client.post("/api/prescriptions/", json=FULL_PAYLOAD).json()
        response = client.put(
            f"/api/prescriptions/{created['id']}/",
            json={"id": 777, "start_date": "2026-03-02", "medicines": []},
        )
        assert response.status_code == 200
        assert response.json()["id"] == created["id"]
        assert read_lines(prescriptions_path)[0]["id"] == created["id"]

    def test_recalculates_derived_fields(self, client):
        created = client.post("/api/prescriptions/", json={}).json()
        response = client.put(
            f"/api/prescriptions/{created['id']}/",
            json=FULL_PAYLOAD,
        )
        body = response.json()
        assert body["end_date"] == "2026-05-03"
        assert body["next_date"] == "2026-04-19"

    def test_unknown_id_returns_404(self, client):
        response = client.put("/api/prescriptions/42/", json={"start_date": "2026-01-01", "medicines": []})
        assert response.status_code == 404

    def test_missing_required_fields_returns_400(self, client):
        created = client.post("/api/prescriptions/", json={}).json()
        for payload in [{}, {"start_date": "2026-01-01"}, {"medicines": []}]:
            response = client.put(f"/api/prescriptions/{created['id']}/", json=payload)
            assert response.status_code == 400, payload

    def test_persisted_as_single_line(self, client, prescriptions_path):
        created = client.post("/api/prescriptions/", json=FULL_PAYLOAD).json()
        client.put(
            f"/api/prescriptions/{created['id']}/",
            json={"start_date": "2026-09-28", "medicines": []},
        )
        lines = read_lines(prescriptions_path)
        assert len(lines) == 1
        assert lines[0]["start_date"] == "2026-09-28"


class TestDelete:
    def test_delete_archives_with_deleted_at(self, client, prescriptions_path, deleted_path):
        created = client.post("/api/prescriptions/", json=FULL_PAYLOAD).json()
        response = client.delete(f"/api/prescriptions/{created['id']}/")
        assert response.status_code == 204
        assert response.content == b""
        assert read_lines(prescriptions_path) == []
        archived = read_lines(deleted_path)
        assert len(archived) == 1
        assert archived[0]["id"] == created["id"]
        assert archived[0]["start_date"] == "2026-03-02"
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", archived[0]["deleted_at"])

    def test_deleted_file_appends_and_is_never_truncated(self, client, deleted_path):
        first = client.post("/api/prescriptions/", json={}).json()
        second = client.post("/api/prescriptions/", json={}).json()
        client.delete(f"/api/prescriptions/{first['id']}/")
        client.delete(f"/api/prescriptions/{second['id']}/")
        archived = read_lines(deleted_path)
        assert [record["id"] for record in archived] == [1, 2]

    def test_second_delete_returns_404(self, client):
        created = client.post("/api/prescriptions/", json={}).json()
        assert client.delete(f"/api/prescriptions/{created['id']}/").status_code == 204
        assert client.delete(f"/api/prescriptions/{created['id']}/").status_code == 404

    def test_get_after_delete_returns_404(self, client):
        created = client.post("/api/prescriptions/", json={}).json()
        client.delete(f"/api/prescriptions/{created['id']}/")
        assert client.get(f"/api/prescriptions/{created['id']}/").status_code == 404

    def test_ids_are_never_reused(self, client):
        first = client.post("/api/prescriptions/", json={}).json()
        second = client.post("/api/prescriptions/", json={}).json()
        client.delete(f"/api/prescriptions/{second['id']}/")
        third = client.post("/api/prescriptions/", json={}).json()
        assert (first["id"], second["id"], third["id"]) == (1, 2, 3)


class TestRoundTrip:
    def test_created_record_survives_reread(self, client, prescriptions_path):
        created = client.post("/api/prescriptions/", json=FULL_PAYLOAD).json()
        fetched = client.get(f"/api/prescriptions/{created['id']}/").json()
        assert fetched == created
        listed = client.get("/api/prescriptions/").json()
        assert listed == [created]

    def test_pick_ups_persisted_sorted(self, client, prescriptions_path):
        client.post("/api/prescriptions/", json=FULL_PAYLOAD)
        stored = read_lines(prescriptions_path)[0]
        dates = [pick_up["date"] for pick_up in stored["medicines"][1]["pick_ups"]]
        assert dates == sorted(dates)


QUANDO_FULL_BODY = (
    "<b>Назначение от 02.03.2026</b>:\n"
    "\n"
    "Желательно получить новое в районе <b>19.04.2026</b>.\n"
    "\n"
    "Из лекарств первым заканчивается <b>Препарат Б</b>, "
    "нужно получить еще в районе <b>26.04.2026</b>.\n"
    "\n"
    "<b>Подробности назначения</b>:\n"
    "\n"
    "- Препарат А: 90 таблеток, по 1 в день -> закончится 02.06.2026\n"
    "- Препарат Б: 120 таблеток, по 2 в день -> закончится 03.05.2026"
)


class TestQuando:
    def test_content_type_is_text_plain_utf8(self, client):
        client.post("/api/prescriptions/", json=FULL_PAYLOAD)
        response = client.get("/api/quando/")
        assert response.status_code == 200
        content_type = response.headers["content-type"]
        assert content_type.startswith("text/plain")
        assert "charset=utf-8" in content_type

    def test_body_matches_expected_for_full_payload(self, client):
        client.post("/api/prescriptions/", json=FULL_PAYLOAD)
        response = client.get("/api/quando/")
        assert response.text == QUANDO_FULL_BODY
        assert not response.text.endswith("\n")

    def test_empty_store_returns_no_data_message_200(self, client):
        response = client.get("/api/quando/")
        assert response.status_code == 200
        assert response.text.startswith("❗️❗️❗️ Нет необходимых данных для расчета сроков.")

    def test_warning_when_latest_has_no_next_date(self, client):
        client.post("/api/prescriptions/", json=FULL_PAYLOAD)
        client.post("/api/prescriptions/", json={"start_date": "2026-11-14"})
        response = client.get("/api/quando/")
        assert response.status_code == 200
        assert response.text.startswith(
            "❗️❗️❗️ Последним добавлено назначение от <b>14.11.2026</b>, "
            "но у него недостаточно данных для расчета сроков."
        )
        assert f"\n\n{QUANDO_FULL_BODY}" in response.text

    def test_cyrillic_is_not_mojibake(self, client):
        client.post("/api/prescriptions/", json=FULL_PAYLOAD)
        response = client.get("/api/quando/")
        decoded = response.content.decode("utf-8")
        assert decoded == response.text
        assert "Препарат А" in decoded
        assert "Назначение" in decoded

    def test_site_url_taken_from_settings(self, client, monkeypatch):
        monkeypatch.setattr(settings, "SITE_URL", "https://quando.test")
        response = client.get("/api/quando/")
        assert response.status_code == 200
        assert "https://quando.test" in response.text


class TestBackup:
    def test_route_order_backup_not_swallowed_by_id_route(self, client):
        client.post("/api/prescriptions/", json=FULL_PAYLOAD)
        response = client.get("/api/prescriptions/backup/")
        assert response.status_code == 200

    def test_backup_matches_file_byte_for_byte(self, client, prescriptions_path):
        client.post("/api/prescriptions/", json=FULL_PAYLOAD)
        response = client.get("/api/prescriptions/backup/")
        assert response.status_code == 200
        assert response.content == prescriptions_path.read_bytes()
        assert response.headers["content-type"].startswith("application/x-ndjson")
        assert re.fullmatch(
            r'attachment; filename="prescriptions_\d{8}\.jsonl"',
            response.headers["content-disposition"],
        )

    def test_filename_date_is_today(self, client):
        client.post("/api/prescriptions/", json=FULL_PAYLOAD)
        response = client.get("/api/prescriptions/backup/")
        expected = f'attachment; filename="prescriptions_{date.today():%Y%m%d}.jsonl"'
        assert response.headers["content-disposition"] == expected

    def test_missing_files_return_404_with_detail(self, client):
        response = client.get("/api/prescriptions/backup/")
        assert response.status_code == 404
        assert response.json() == {"detail": "backup file not found: prescriptions"}
        response = client.get("/api/prescriptions/backup-deleted/")
        assert response.status_code == 404
        assert response.json() == {"detail": "backup file not found: deleted"}

    def test_backup_deleted_lifecycle(self, client, deleted_path):
        created = client.post("/api/prescriptions/", json=FULL_PAYLOAD).json()
        assert client.get("/api/prescriptions/backup-deleted/").status_code == 404
        client.delete(f"/api/prescriptions/{created['id']}/")
        response = client.get("/api/prescriptions/backup-deleted/")
        assert response.status_code == 200
        assert response.content == deleted_path.read_bytes()
        assert "deleted_at" in response.text
        assert re.fullmatch(
            r'attachment; filename="deleted_\d{8}\.jsonl"',
            response.headers["content-disposition"],
        )

    def test_corrupt_line_still_served_200(self, client, prescriptions_path):
        prescriptions_path.parent.mkdir(parents=True, exist_ok=True)
        prescriptions_path.write_bytes(b"{not json}\n")
        response = client.get("/api/prescriptions/backup/")
        assert response.status_code == 200
        assert response.content == b"{not json}\n"

    def test_deleted_backup_is_never_truncated(self, client):
        first = client.post("/api/prescriptions/", json={}).json()
        second = client.post("/api/prescriptions/", json={}).json()
        client.delete(f"/api/prescriptions/{first['id']}/")
        client.delete(f"/api/prescriptions/{second['id']}/")
        response = client.get("/api/prescriptions/backup-deleted/")
        assert response.status_code == 200
        lines = [
            json.loads(line)
            for line in response.content.decode("utf-8").splitlines()
            if line.strip()
        ]
        assert [record["id"] for record in lines] == [1, 2]
