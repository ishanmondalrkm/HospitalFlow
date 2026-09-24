from fastapi.testclient import TestClient

from backend.main import app


def test_bottlenecks_contract():
    with TestClient(app) as client:
        response = client.get('/api/bottlenecks')
    assert response.status_code == 200
    payload = response.json()
    assert payload['leading_department_id'] in {item['id'] for item in payload['departments']}
    assert len(payload['departments']) == 8
    assert payload['departments'][0]['contributors']
    assert payload['propagation']
    assert payload['chain']
