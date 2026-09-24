from datetime import timedelta

import pandas as pd

from backend import config as cfg
from backend.services import data_generator, data_service, metrics


def _frame() -> pd.DataFrame:
    data_service.ensure_seeded()
    return data_service.get_frame()


def test_generation_is_deterministic():
    a = data_generator.generate(seed=7, history_days=2, warmup_days=1)
    b = data_generator.generate(seed=7, history_days=2, warmup_days=1)
    c = data_generator.generate(seed=8, history_days=2, warmup_days=1)
    assert a == b
    assert a != c


def test_row_count_and_time_range():
    rows = data_generator.generate()
    per_day = 24 * 60 // cfg.INTERVAL_MIN
    assert len(rows) == cfg.HISTORY_DAYS * per_day * len(cfg.DEPARTMENTS)
    stamps = sorted({r["timestamp"] for r in rows})
    assert stamps[-1] == cfg.REFERENCE_NOW.isoformat(timespec="minutes")
    first = pd.Timestamp(stamps[0])
    assert pd.Timestamp(cfg.REFERENCE_NOW) - first == timedelta(
        minutes=cfg.INTERVAL_MIN * (cfg.HISTORY_DAYS * per_day - 1)
    )


def test_values_are_physically_sane():
    data_service.ensure_seeded()
    raw = data_service.load_metrics()
    assert (raw["queue_length"] >= 0).all()
    assert (raw["arrivals"] >= 0).all()
    assert raw["utilization"].between(0, 1).all()
    beds = raw[raw["department_id"] == "beds"]
    assert beds["beds_occupied"].between(0, cfg.TOTAL_BEDS).all()
    assert not raw.drop(columns=["beds_total", "beds_occupied"]).isna().any().any()


def test_database_round_trip_matches_generator(tmp_path):
    path = tmp_path / "roundtrip.db"
    assert data_service.ensure_seeded(path) is True  # created
    assert data_service.ensure_seeded(path) is False  # up to date, left alone
    assert len(data_service.load_metrics(path)) == len(data_generator.generate())


def test_stale_database_is_rebuilt(tmp_path):
    import sqlite3

    path = tmp_path / "stale.db"
    data_service.ensure_seeded(path)
    conn = sqlite3.connect(path)
    conn.execute("UPDATE meta SET value = 'changed' WHERE key = 'model_fingerprint'")
    conn.commit()
    conn.close()
    assert data_service.ensure_seeded(path) is True  # config drifted, so it rebuilds
    assert data_service.ensure_seeded(path) is False


def test_scripted_incidents_show_up_as_pressure():
    df = _frame()
    primary = {
        "Radiology scanner outage": "radiology",
        "Emergency evening shift short-staffed": "emergency",
        "Seasonal illness spike": "emergency",
        "Laboratory analyser downtime": "laboratory",
        "Discharge processing slowdown": "discharge",
        "Saturday evening emergency surge": "emergency",
    }
    for start, end, incident in data_generator.incident_windows(cfg.REFERENCE_NOW):
        window = df[
            (df["department_id"] == primary[incident.name])
            & (df["timestamp"] > start)
            & (df["timestamp"] <= end + pd.Timedelta(hours=3))
        ]
        assert window["pressure"].max() >= 0.45, incident.name


def test_reference_snapshot_is_busy_but_stable():
    """The demo starts stable, with Emergency the department to watch."""
    df = _frame()
    now = df["timestamp"].max()
    latest = df[df["timestamp"] == now].set_index("department_id")
    overall = metrics.overall_pressure(metrics.wide(df, "pressure")).iloc[-1]
    assert metrics.level_for_score(overall) == "LOW"
    assert (latest["level"].isin(["HIGH", "CRITICAL"])).sum() == 0
    assert latest["pressure"].idxmax() == "emergency"
    assert 30 <= latest.loc["emergency", "avg_wait_min"] <= 45
    occupancy = latest.loc["beds", "beds_occupied"] / cfg.TOTAL_BEDS
    assert 0.80 <= occupancy <= 0.90
