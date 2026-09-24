"""MongoDB connection lifecycle for HospitalFlow.

Phase 8A introduces MongoDB without changing the existing model/data pipeline.
The connection is intentionally optional during this foundation phase so the
existing demo still starts when MongoDB is not running. Later phases will use
the same client for operational snapshots, alerts and history.
"""
from __future__ import annotations

import logging
from typing import Optional

from pymongo import MongoClient
from pymongo.errors import PyMongoError

from backend import config as cfg

logger = logging.getLogger("hospitalflow.mongo")

_client: Optional[MongoClient] = None


def connect() -> bool:
    """Connect to MongoDB and ping it. Returns False instead of breaking the demo."""
    global _client
    if _client is not None:
        return True

    try:
        client = MongoClient(
            cfg.MONGODB_URI,
            serverSelectionTimeoutMS=cfg.MONGODB_SERVER_SELECTION_TIMEOUT_MS,
            connectTimeoutMS=cfg.MONGODB_CONNECT_TIMEOUT_MS,
        )
        client.admin.command("ping")
        _client = client
        logger.info("MongoDB connected: %s/%s", cfg.MONGODB_URI, cfg.MONGODB_DATABASE)
        return True
    except PyMongoError as exc:
        logger.warning("MongoDB is unavailable: %s", exc)
        try:
            client.close()
        except Exception:
            pass
        return False


def disconnect() -> None:
    """Close the shared MongoDB client."""
    global _client
    if _client is not None:
        _client.close()
        _client = None


def is_available() -> bool:
    """Return whether MongoDB is currently reachable."""
    if _client is None and not connect():
        return False
    try:
        _client.admin.command("ping")
        return True
    except PyMongoError:
        return False


def database():
    """Return the configured database, raising a clear error if unavailable."""
    if _client is None and not connect():
        raise RuntimeError(
            "MongoDB is unavailable. Start MongoDB Server and check HOSPITALFLOW_MONGODB_URI."
        )
    return _client[cfg.MONGODB_DATABASE]
