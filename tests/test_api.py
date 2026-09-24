import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from backend.main import app  # noqa: E402


def test_health_dashboard_and_departments():
    with TestClient(app) as client:  # the context manager runs startup (database seeding)
        health = client.get("/api/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"

        dashboard = client.get("/api/dashboard")
        assert dashboard.status_code == 200
        body = dashboard.json()
        assert body["hospital"]["level"] in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
        assert len(body["departments"]) == 8
        assert len(body["kpis"]) == 8

        departments = client.get("/api/departments")
        assert departments.status_code == 200
        assert len(departments.json()) == 8

        emergency = client.get("/api/departments/emergency")
        assert emergency.status_code == 200
        assert len(emergency.json()["history"]["timestamps"]) == 96


def test_unknown_department_returns_a_helpful_404():
    with TestClient(app) as client:
        response = client.get("/api/departments/cardiology")
        assert response.status_code == 404
        assert "Use one of" in response.json()["detail"]
