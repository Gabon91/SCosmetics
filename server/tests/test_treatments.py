from fastapi.testclient import TestClient

from app.main import app


def test_treatment_catalog_returns_seed_data() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/treatments")

    assert response.status_code == 200
    treatments = response.json()
    assert len(treatments) == 3
    assert treatments[0]["name"] == "טיפול זוהר לפנים"
    assert response.headers["X-Cache"] in {"HIT", "MISS"}

