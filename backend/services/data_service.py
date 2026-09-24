"""Data service: SQLite storage plus cached access to enriched metrics.

The synthetic history is stored in SQLite (`operational_metrics`), which is the
shape a real hospital feed would land in.  On startup the database is created if
it is missing, or rebuilt if it was produced by a different generator version or
model configuration (departments, staffing, routing, incidents, seed ...), so a stale
file can never silently feed the dashboard.

Run `python -m backend.services.data_service` to rebuild it by hand.
"""
from __future__ import annotations

import sqlite3
from functools import lru_cache
from pathlib import Path

import pandas as pd

from backend import config as cfg
from backend.services import data_generator, metrics

SCHEMA = """
DROP TABLE IF EXISTS operational_metrics;
DROP TABLE IF EXISTS departments;
DROP TABLE IF EXISTS meta;

CREATE TABLE meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE departments (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    kind          TEXT NOT NULL,          -- 'station' or 'beds'
    staff_night   INTEGER NOT NULL,
    staff_day     INTEGER NOT NULL,
    staff_evening INTEGER NOT NULL,
    rate          REAL NOT NULL,          -- patients per staff member per hour
    base_wait     REAL NOT NULL,          -- minutes
    critical_wait REAL NOT NULL           -- minutes
);

CREATE TABLE operational_metrics (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    department_id TEXT NOT NULL REFERENCES departments(id),
    timestamp     TEXT NOT NULL,          -- end of the 15-minute interval, ISO 8601
    arrivals      REAL NOT NULL,
    served        REAL NOT NULL,
    queue_length  REAL NOT NULL,
    staff_planned INTEGER NOT NULL,
    staff_on_duty INTEGER NOT NULL,
    capacity      REAL NOT NULL,          -- patients that could be processed this interval
    utilization   REAL NOT NULL,          -- 0..1 (occupancy for beds)
    avg_wait_min  REAL NOT NULL,
    beds_total    INTEGER,                -- beds row only
    beds_occupied REAL                    -- beds row only
);
CREATE INDEX idx_metrics_dept_time ON operational_metrics (department_id, timestamp);
"""

_METRIC_COLUMNS = (
    "department_id",
    "timestamp",
    "arrivals",
    "served",
    "queue_length",
    "staff_planned",
    "staff_on_duty",
    "capacity",
    "utilization",
    "avg_wait_min",
    "beds_total",
    "beds_occupied",
)


def _db_path(path: Path | str | None) -> Path:
    return Path(path) if path is not None else cfg.DB_PATH


def _expected_meta() -> dict[str, str]:
    return {
        "generator_version": cfg.GENERATOR_VERSION,
        "model_fingerprint": cfg.model_fingerprint(),
        "seed": str(cfg.SEED),
        "reference_now": cfg.REFERENCE_NOW.isoformat(timespec="minutes"),
        "history_days": str(cfg.HISTORY_DAYS),
    }


def seed_database(path: Path | str | None = None) -> int:
    """(Re)build the database from the generator. Returns the number of metric rows."""
    db_path = _db_path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    rows = data_generator.generate()

    conn = sqlite3.connect(db_path)
    try:
        with conn:
            conn.executescript(SCHEMA)
            conn.executemany(
                "INSERT INTO departments VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (d.id, d.name, d.kind, *d.staff, d.rate, d.base_wait, d.critical_wait)
                    for d in cfg.DEPARTMENTS
                ],
            )
            placeholders = ", ".join(f":{c}" for c in _METRIC_COLUMNS)
            conn.executemany(
                f"INSERT INTO operational_metrics ({', '.join(_METRIC_COLUMNS)}) VALUES ({placeholders})",
                rows,
            )
            conn.executemany("INSERT INTO meta VALUES (?, ?)", list(_expected_meta().items()))
    finally:
        conn.close()
    reset_cache()
    return len(rows)


def _read_meta(db_path: Path) -> dict[str, str]:
    conn = sqlite3.connect(db_path)
    try:
        return dict(conn.execute("SELECT key, value FROM meta").fetchall())
    except sqlite3.DatabaseError:
        return {}
    finally:
        conn.close()


def ensure_seeded(path: Path | str | None = None) -> bool:
    """Create or refresh the database when needed. Returns True if it was rebuilt."""
    db_path = _db_path(path)
    if db_path.exists() and _read_meta(db_path) == _expected_meta():
        return False
    seed_database(db_path)
    return True


def load_metrics(path: Path | str | None = None) -> pd.DataFrame:
    """Raw metric rows, oldest first."""
    conn = sqlite3.connect(_db_path(path))
    try:
        frame = pd.read_sql_query(
            f"SELECT {', '.join(_METRIC_COLUMNS)} FROM operational_metrics ORDER BY timestamp, id",
            conn,
        )
    finally:
        conn.close()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"])
    return frame


@lru_cache(maxsize=1)
def get_frame() -> pd.DataFrame:
    """Enriched metrics (pressure scores etc.). The data is static, so it is cached."""
    return metrics.enrich(load_metrics())


def reset_cache() -> None:
    get_frame.cache_clear()


if __name__ == "__main__":
    count = seed_database()
    print(f"Rebuilt {cfg.DB_PATH} with {count} rows (seed {cfg.SEED}, now = {cfg.REFERENCE_NOW}).")
