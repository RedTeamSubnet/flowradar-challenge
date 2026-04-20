from fastapi.testclient import TestClient

from src.flr_challenge.challenge.api.main import app

client = TestClient(app)


def test_ping() -> None:
    _response = client.get("/ping")
    assert _response.status_code == 200
    return


def test_health() -> None:
    _response = client.get("/health")
    assert _response.status_code == 200
    return
