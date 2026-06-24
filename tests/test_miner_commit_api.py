from fastapi.testclient import TestClient

from examples.miner_commit.src.app import app

client = TestClient(app)


def test_health() -> None:
    _response = client.get("/health")
    assert _response.status_code == 200
    return


def test_solve_returns_commit_files() -> None:
    response = client.post("/solve", json={"random_val": "test-value"})
    assert response.status_code == 200
    commit_files = response.json()["commit_files"]
    assert {item["file_name"] for item in commit_files} == {
        "train.py",
        "submissions.py",
    }
    assert all(item["content"] for item in commit_files)
