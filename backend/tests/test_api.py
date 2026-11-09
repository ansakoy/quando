import json
import re
from datetime import date

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
