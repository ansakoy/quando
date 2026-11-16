import pytest
from fastapi.testclient import TestClient

import settings
from backend.main import app


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_PATH", tmp_path)
    monkeypatch.setattr(settings, "PRESCRIPTIONS_PATH", tmp_path / "prescriptions.jsonl")
    monkeypatch.setattr(settings, "DELETED_PATH", tmp_path / "deleted.jsonl")
    return tmp_path


@pytest.fixture
def client(data_dir):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def prescriptions_path(data_dir):
    return data_dir / "prescriptions.jsonl"


@pytest.fixture
def deleted_path(data_dir):
    return data_dir / "deleted.jsonl"
