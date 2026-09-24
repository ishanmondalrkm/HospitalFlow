"""MongoDB-backed operational history for HospitalFlow.

Phase 8B stores the model's existing operational history in MongoDB.  This is
still operational data only: no patient identifiers or clinical records are
stored.  The SQLite dataset remains the deterministic source used by the
current model; MongoDB becomes the persistent history/read layer that later
live ingestion and alert phases can append to.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import PyMongoError

from backend.db import mongo
from backend import config as cfg

COLLECTION = "operational_snapshots"


def _collection():
    return mongo.database()[COLLECTION]


def ensure_indexes() -> None:
    """Create the indexes needed for department/time history queries."""
    collection = _collection()
    collection.create_index([("timestamp", ASCENDING)], name="timestamp_idx")
    collection.create_index(
        [("department_id", ASCENDING), ("timestamp", ASCENDING)],
        name="department_time_idx",
    )
    collection.create_index(
        [("source", ASCENDING), ("timestamp", DESCENDING)],
        name="source_time_idx",
    )
    collection.create_index(
        [("source", ASCENDING), ("department_id", ASCENDING), ("timestamp", ASCENDING)],
        name="snapshot_identity_idx",
        unique=True,
    )


def _document(row: pd.Series, source: str = "synthetic") -> dict[str, Any]:
    timestamp = pd.Timestamp(row["timestamp"]).to_pydatetime()
    return {
        "source": source,
        "department_id": str(row["department_id"]),
        "department_name": cfg.DEPARTMENT_BY_ID[str(row["department_id"])].name,
        "timestamp": timestamp,
        "arrivals": float(row["arrivals"]),
        "served": float(row["served"]),
        "queue_length": float(row["queue_length"]),
        "staff_planned": int(row["staff_planned"]),
        "staff_on_duty": int(row["staff_on_duty"]),
        "capacity": float(row["capacity"]),
        "utilization": float(row["utilization"]),
        "avg_wait_min": float(row["avg_wait_min"]),
        "beds_total": int(row["beds_total"]) if pd.notna(row["beds_total"]) else None,
        "beds_occupied": float(row["beds_occupied"]) if pd.notna(row["beds_occupied"]) else None,
        # Derived values are stored so historical reads do not have to rerun the
        # complete model just to display the operational pressure state.
        "pressure": float(row["pressure"]),
        "level": str(row["level"]),
        "pressure_components": {
            "queue": float(row["c_queue"]),
            "utilization": float(row["c_util"]),
            "arrival_surge": float(row["c_surge"]),
            "resource_constraint": float(row["c_resource"]),
        },
    }


def seed_from_frame(frame: pd.DataFrame) -> int:
    """Populate MongoDB once from the deterministic model history.

    A unique logical key (source, department, timestamp) prevents duplicate
    snapshots when the application restarts.
    """
    collection = _collection()
    ensure_indexes()
    if collection.count_documents({"source": "synthetic"}, limit=1) > 0:
        return 0

    docs = [_document(row, source="synthetic") for _, row in frame.iterrows()]
    if not docs:
        return 0

    # Insert in batches so the initial 14-day history remains lightweight and
    # reliable on local MongoDB installations.
    inserted = 0
    for start in range(0, len(docs), 1000):
        batch = docs[start : start + 1000]
        result = collection.insert_many(batch, ordered=False)
        inserted += len(result.inserted_ids)
    return inserted


def save_snapshot(frame: pd.DataFrame, source: str = "synthetic") -> int:
    """Persist the latest interval for each department under the given source.

    The logical identity is (source, department, timestamp), so synthetic
    history and live/external history can coexist safely.
    """
    collection = _collection()
    ensure_indexes()
    latest_timestamp = frame["timestamp"].max()
    latest = frame[frame["timestamp"] == latest_timestamp]
    inserted = 0
    for _, row in latest.iterrows():
        doc = _document(row, source=source)
        exists = collection.find_one(
            {
                "source": doc["source"],
                "department_id": doc["department_id"],
                "timestamp": doc["timestamp"],
            },
            {"_id": 1},
        )
        if exists is None:
            collection.insert_one(doc)
            inserted += 1
    return inserted


def save_snapshots(frame: pd.DataFrame, source: str) -> int:
    """Persist all department/timestamp rows in an external ingestion batch."""
    collection = _collection()
    ensure_indexes()
    inserted = 0
    for _, row in frame.iterrows():
        doc = _document(row, source=source)
        exists = collection.find_one(
            {
                "source": doc["source"],
                "department_id": doc["department_id"],
                "timestamp": doc["timestamp"],
            },
            {"_id": 1},
        )
        if exists is None:
            collection.insert_one(doc)
            inserted += 1
    return inserted


def initialize(frame: pd.DataFrame) -> dict[str, int]:
    """Initialize MongoDB history for application startup."""
    seeded = seed_from_frame(frame)
    appended = save_snapshot(frame) if seeded == 0 else 0
    return {"seeded": seeded, "appended": appended}


def count() -> int:
    return _collection().count_documents({})


def get_history(
    *, department_id: str | None = None, source: str | None = None, hours: int = 24, limit: int = 5000
) -> list[dict[str, Any]]:
    """Return recent operational snapshots, oldest first."""
    query: dict[str, Any] = {}
    if department_id:
        query["department_id"] = department_id
    if source:
        query["source"] = source

    latest = _collection().find_one(query, sort=[("timestamp", DESCENDING)])
    if latest is None:
        return []

    cutoff = latest["timestamp"].timestamp() - (hours * 3600)
    query["timestamp"] = {"$gte": datetime.fromtimestamp(cutoff, tz=latest["timestamp"].tzinfo)}

    docs = list(
        _collection()
        .find(query, {"_id": 0})
        .sort([("timestamp", ASCENDING), ("department_id", ASCENDING)])
        .limit(limit)
    )
    return docs
