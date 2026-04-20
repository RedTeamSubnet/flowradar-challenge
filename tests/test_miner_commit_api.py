from fastapi.testclient import TestClient

from examples.miner_commit.src.app import app

client = TestClient(app)


def test_health() -> None:
    _response = client.get("/health")
    assert _response.status_code == 200
    return
