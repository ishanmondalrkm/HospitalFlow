from datetime import datetime

import pandas as pd

from backend.services import alerts


def test_alert_candidates_include_high_pressure(monkeypatch):
    captured = []

    monkeypatch.setattr(alerts, "ensure_indexes", lambda: None)
    monkeypatch.setattr(alerts, "_recent_duplicate", lambda fingerprint, timestamp: False)

    class Result:
        inserted_id = "test-alert-id"

    class Collection:
        def insert_one(self, document):
            captured.append(document)
            return Result()

    monkeypatch.setattr(alerts, "_collection", lambda: Collection())

    frame = pd.DataFrame([
        {
            "department_id": "emergency",
            "timestamp": datetime(2026, 9, 21, 10, 0),
            "pressure": 0.80,
            "avg_wait_min": 30,
            "queue_length": 5,
            "utilization": 0.80,
        }
    ])

    created = alerts.evaluate(frame)
    assert created
    assert any(item["alert_type"] == "critical_pressure" for item in captured)
