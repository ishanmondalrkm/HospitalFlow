"""Operational alert engine for HospitalFlow Phase 8D.

Alerts are derived from aggregate operational snapshots.  No patient-level
information is stored.  The engine uses the same pressure/operational metrics
already produced by HospitalFlow and persists alert events in MongoDB.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from pymongo import ASCENDING, DESCENDING

from backend import config as cfg
from backend.db import mongo

COLLECTION = "alerts"
ALERT_COOLDOWN_MINUTES = 30


def _collection():
    return mongo.database()[COLLECTION]


def ensure_indexes() -> None:
    collection = _collection()
    collection.create_index([("timestamp", DESCENDING)], name="alert_time_idx")
    collection.create_index([("department_id", ASCENDING), ("timestamp", DESCENDING)], name="department_alert_time_idx")
    collection.create_index([("status", ASCENDING), ("timestamp", DESCENDING)], name="status_alert_time_idx")
    collection.create_index([("fingerprint", ASCENDING)], name="fingerprint_idx")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _fingerprint(department_id: str, alert_type: str) -> str:
    return f"{department_id}:{alert_type}"


def _recent_duplicate(fingerprint: str, timestamp: datetime) -> bool:
    cutoff = timestamp - timedelta(minutes=ALERT_COOLDOWN_MINUTES)
    return _collection().find_one(
        {"fingerprint": fingerprint, "timestamp": {"$gte": cutoff}},
        {"_id": 1},
        sort=[("timestamp", DESCENDING)],
    ) is not None


def _add_candidate(candidates: list[dict[str, Any]], department_id: str, timestamp: datetime,
                   alert_type: str, severity: str, message: str, value: float, threshold: float) -> None:
    candidates.append({
        "department_id": department_id,
        "timestamp": timestamp,
        "alert_type": alert_type,
        "severity": severity,
        "message": message,
        "value": round(float(value), 3),
        "threshold": round(float(threshold), 3),
    })


def evaluate(frame) -> list[dict[str, Any]]:
    """Evaluate the latest enriched operational rows and persist new alerts."""
    ensure_indexes()
    if frame is None or len(frame) == 0:
        return []

    latest_timestamp = frame["timestamp"].max()
    latest = frame[frame["timestamp"] == latest_timestamp]
    candidates: list[dict[str, Any]] = []

    for _, row in latest.iterrows():
        department_id = str(row["department_id"])
        name = cfg.DEPARTMENT_BY_ID[department_id].name
        pressure = float(row["pressure"])
        wait = float(row["avg_wait_min"])
        queue = float(row["queue_length"])
        utilization = float(row["utilization"])

        if pressure >= cfg.LEVEL_THRESHOLDS["CRITICAL"]:
            _add_candidate(candidates, department_id, latest_timestamp, "critical_pressure", "CRITICAL",
                           f"{name} pressure is critical ({pressure:.0%}).", pressure, cfg.LEVEL_THRESHOLDS["CRITICAL"])
        elif pressure >= cfg.LEVEL_THRESHOLDS["HIGH"]:
            _add_candidate(candidates, department_id, latest_timestamp, "high_pressure", "HIGH",
                           f"{name} pressure is high ({pressure:.0%}).", pressure, cfg.LEVEL_THRESHOLDS["HIGH"])

        department = cfg.DEPARTMENT_BY_ID[department_id]
        if wait >= department.critical_wait:
            _add_candidate(candidates, department_id, latest_timestamp, "critical_wait", "CRITICAL",
                           f"{name} average wait has reached {wait:.0f} minutes.", wait, department.critical_wait)
        elif wait >= department.critical_wait * 0.75:
            _add_candidate(candidates, department_id, latest_timestamp, "high_wait", "HIGH",
                           f"{name} average wait is {wait:.0f} minutes.", wait, department.critical_wait * 0.75)

        if department.kind == "station":
            if utilization >= 0.95:
                _add_candidate(candidates, department_id, latest_timestamp, "high_utilization", "HIGH",
                               f"{name} utilization is {utilization:.0%}.", utilization, 0.95)
        elif department_id == "beds":
            availability = max(0.0, 1.0 - utilization)
            if availability <= 0.05:
                _add_candidate(candidates, department_id, latest_timestamp, "low_bed_availability", "CRITICAL",
                               f"Bed availability is only {availability:.0%}.", availability, 0.05)
            elif availability <= 0.10:
                _add_candidate(candidates, department_id, latest_timestamp, "low_bed_availability", "HIGH",
                               f"Bed availability is only {availability:.0%}.", availability, 0.10)

        if queue >= max(10.0, department.critical_wait / 5.0):
            threshold = max(10.0, department.critical_wait / 5.0)
            _add_candidate(candidates, department_id, latest_timestamp, "high_queue", "HIGH",
                           f"{name} queue has reached {queue:.0f}.", queue, threshold)

    created: list[dict[str, Any]] = []
    collection = _collection()
    for candidate in candidates:
        fingerprint = _fingerprint(candidate["department_id"], candidate["alert_type"])
        if _recent_duplicate(fingerprint, candidate["timestamp"]):
            continue
        document = {
            **candidate,
            "fingerprint": fingerprint,
            "status": "OPEN",
            "created_at": _now_utc(),
            "acknowledged_at": None,
            "acknowledged_by": None,
        }
        result = collection.insert_one(document)
        document["alert_id"] = str(result.inserted_id)
        document.pop("_id", None)
        created.append(document)
    return created


def list_alerts(*, status: str | None = None, department_id: str | None = None,
                severity: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    ensure_indexes()
    query: dict[str, Any] = {}
    if status:
        query["status"] = status.upper()
    if department_id:
        query["department_id"] = department_id
    if severity:
        query["severity"] = severity.upper()
    docs = list(_collection().find(query, {"_id": 1}).sort("timestamp", DESCENDING).limit(limit))
    result = []
    for doc in docs:
        full = _collection().find_one({"_id": doc["_id"]})
        if full:
            full["alert_id"] = str(full.pop("_id"))
            result.append(full)
    return result


def acknowledge(alert_id: str, acknowledged_by: str = "operator") -> bool:
    from bson import ObjectId

    ensure_indexes()
    try:
        object_id = ObjectId(alert_id)
    except Exception:
        return False
    result = _collection().update_one(
        {"_id": object_id, "status": "OPEN"},
        {"$set": {"status": "ACKNOWLEDGED", "acknowledged_at": _now_utc(), "acknowledged_by": acknowledged_by}},
    )
    return result.modified_count == 1
