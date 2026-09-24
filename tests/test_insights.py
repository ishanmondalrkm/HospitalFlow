from fastapi.testclient import TestClient

from backend.main import app
from backend.services import data_service, insights


def test_build_insights_returns_modelled_options():
    data_service.ensure_seeded()
    result = insights.build_insights(data_service.get_frame(), 60)
    assert result["horizon_minutes"] == 60
    assert len(result["options"]) == 4
    assert all("pressure_points" in option for option in result["options"])


def test_insights_endpoint():
    with TestClient(app) as client:
        response = client.get("/api/insights?horizon=60")
    assert response.status_code == 200
    payload = response.json()
    assert payload["leading_department_name"]
    assert len(payload["options"]) == 4
