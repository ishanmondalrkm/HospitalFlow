"""Synthetic operational data.

Runs the hospital model forward through 14 days of demand (rush hours, weekend
shifts and the scripted incidents in `config.INCIDENTS`) and returns one row per
department per 15-minute interval.  Seeded, so the demo is identical every time.

There is no patient-level data anywhere: rows are counts, queues and utilisation.
"""
from __future__ import annotations

import random
from datetime import datetime, time, timedelta

from backend import config as cfg
from backend.services import hospital_model as model


def incident_windows(reference_now: datetime) -> list[tuple[datetime, datetime, cfg.Incident]]:
    midnight = datetime.combine(reference_now.date(), time(0, 0))
    windows = []
    for incident in cfg.INCIDENTS:
        start = midnight - timedelta(days=incident.days_ago) + timedelta(hours=incident.start_hour)
        windows.append((start, start + timedelta(hours=incident.hours), incident))
    return windows


def _round(row: dict) -> dict:
    return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in row.items()}


def generate(
    seed: int = cfg.SEED,
    reference_now: datetime = cfg.REFERENCE_NOW,
    history_days: int = cfg.HISTORY_DAYS,
    warmup_days: int = cfg.WARMUP_DAYS,
) -> list[dict]:
    """Return operational rows; `timestamp` is the *end* of each 15-minute interval.

    The last timestamp equals `reference_now`.
    """
    rng = random.Random(seed)
    step_min = cfg.INTERVAL_MIN
    per_day = 24 * 60 // step_min
    total = (history_days + warmup_days) * per_day
    first_end = reference_now - timedelta(minutes=step_min * (total - 1))
    windows = incident_windows(reference_now)

    state = model.initial_state()
    rows: list[dict] = []
    for i in range(total):
        t_end = first_end + timedelta(minutes=step_min * i)
        t_start = t_end - timedelta(minutes=step_min)
        active = [inc for start, end, inc in windows if start <= t_start < end]
        state, out = model.step(state, model.demand_inputs(t_start, active), rng)
        if i < warmup_days * per_day:
            continue
        stamp = t_end.isoformat(timespec="minutes")
        for dept in cfg.DEPARTMENTS:
            rows.append(_round({"department_id": dept.id, "timestamp": stamp, **out[dept.id]}))
    return rows
