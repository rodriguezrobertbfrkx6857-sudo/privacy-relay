import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_DB", str(tmp_path / "test.sqlite3"))


@pytest.fixture
def client():
    from app.main import app

    with TestClient(app) as client:
        yield client
