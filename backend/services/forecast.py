"""Deterministic short-horizon forecasts built from the hospital queue model."""
from __future__ import annotations

from datetime import timedelta

import pandas as pd

from backend import config as cfg
from backend.services import data_generator, hospital_model as model, metrics


def _clip(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _latest_state(df: pd.DataFrame) -> tuple[model.State, pd.Timestamp]:
    latest_time = df["timestamp"].max()
    latest = df[df["timestamp"] == latest_time].set_index("department_id")
    queues = {sid: float(latest.loc[sid, "queue_length"]) for sid in cfg.STATION_IDS}
    queues["beds"] = float(latest.loc["beds", "queue_length"])
    lab = cfg.DEPARTMENT_BY_ID["laboratory"]
    lab_delay = (float(latest.loc["laboratory", "avg_wait_min"]) - lab.base_wait) / (lab.critical_wait - lab.base_wait)
    occupied = float(latest.loc["beds", "beds_occupied"])
    return model.State(queues=queues, occupied_beds=occupied, lab_delay=_clip(lab_delay)), latest_time


def _typical_arrivals(df: pd.DataFrame) -> dict[tuple[str, bool, int], float]:
    work = df.copy()
    work["is_weekend"] = work["timestamp"].dt.dayofweek >= 5
    work["slot"] = work["timestamp"].dt.hour * 4 + work["timestamp"].dt.minute // 15
    grouped = work.groupby(["department_id", "is_weekend", "slot"])["arrivals"].median()
    return {key: float(value) for key, value in grouped.items()}


def _score_forecast_point(dept_id, row, recent, typical, timestamp):
    dept = cfg.DEPARTMENT_BY_ID[dept_id]
    is_beds = dept.kind == "beds"
    c_queue = _clip((row["avg_wait_min"] - dept.base_wait) / (dept.critical_wait - dept.base_wait))
    recent_loads = [float(item["load"]) for item in recent[-3:]] + [float(row["load"])]
    load_1h = sum(recent_loads) / len(recent_loads)
    floor = cfg.BED_LOAD_FLOOR if is_beds else cfg.STATION_LOAD_FLOOR
    ceil = cfg.BED_LOAD_CEIL if is_beds else 1.0
    c_util = _clip((load_1h - floor) / (ceil - floor))

    arrivals_window = [float(item["arrivals"]) for item in recent[-7:]] + [float(row["arrivals"])]
    weekend = timestamp.weekday() >= 5
    slot = timestamp.hour * 4 + timestamp.minute // 15
    typical_value = typical.get((dept_id, weekend, slot), float(row["arrivals"]))
    typical_window = typical_value * len(arrivals_window)
    surge_ratio = (sum(arrivals_window) - typical_window) / max(typical_window, cfg.SURGE_MIN_VOLUME)
    c_surge = _clip((surge_ratio - cfg.SURGE_DEADZONE) / (cfg.SURGE_SATURATION - cfg.SURGE_DEADZONE))

    if is_beds:
        occupied = max(float(row.get("beds_occupied") or 0.0), 1.0)
        pending = float(row.get("pending_discharges") or 0.0)
        c_resource = _clip((pending / occupied) * cfg.BLOCKED_BEDS_GAIN)
    else:
        planned = float(row["staff_planned"])
        shortfall = ((planned - float(row["staff_on_duty"])) / planned) if planned > 0 else 0.0
        c_resource = _clip(shortfall * cfg.STAFF_SHORTFALL_GAIN)

    score = (
        cfg.PRESSURE_WEIGHTS["queue"] * c_queue
        + cfg.PRESSURE_WEIGHTS["utilization"] * c_util
        + cfg.PRESSURE_WEIGHTS["arrival_surge"] * c_surge
        + cfg.PRESSURE_WEIGHTS["resource_constraint"] * c_resource
    )
    score = round(_clip(score), 3)
    return score, metrics.level_for_score(score)


def build_forecast(df: pd.DataFrame, horizon_minutes: int = 120) -> dict:
    """Project the connected queue network forward without random arrivals."""
    horizon_minutes = int(horizon_minutes)
    if horizon_minutes not in (30, 60, 120):
        raise ValueError("horizon_minutes must be 30, 60, or 120")

    state, latest_time = _latest_state(df)
    typical = _typical_arrivals(df)
    incidents = data_generator.incident_windows(latest_time.to_pydatetime())

    recent_by_dept = {}
    for dept_id in cfg.DEPARTMENT_IDS:
        rows = df[df["department_id"] == dept_id].tail(cfg.SURGE_WINDOW_INTERVALS - 1)
        recent_by_dept[dept_id] = [
            {"arrivals": float(r.arrivals), "load": float(r.beds_occupied / r.beds_total) if dept_id == "beds" else float(r.utilization)}
            for r in rows.itertuples()
        ]

    latest_rows = df[df["timestamp"] == latest_time].set_index("department_id")
    baseline = {
        dept_id: {
            "pressure_score": round(float(latest_rows.loc[dept_id, "pressure"]), 3),
            "level": str(latest_rows.loc[dept_id, "level"]),
            "queue_length": round(float(latest_rows.loc[dept_id, "queue_length"]), 2),
            "avg_wait_min": round(float(latest_rows.loc[dept_id, "avg_wait_min"]), 1),
        }
        for dept_id in cfg.DEPARTMENT_IDS
    }

    points = horizon_minutes // cfg.INTERVAL_MIN
    timestamps = []
    forecasts = {
        dept.id: {"id": dept.id, "name": dept.name, "kind": dept.kind, "pressure_score": [], "level": [], "queue_length": [], "avg_wait_min": [], "utilization": []}
        for dept in cfg.DEPARTMENTS
    }
    overall_scores, overall_levels = [], []

    for step_number in range(1, points + 1):
        forecast_end = latest_time + timedelta(minutes=cfg.INTERVAL_MIN * step_number)
        t_start = forecast_end - timedelta(minutes=cfg.INTERVAL_MIN)
        active = [inc for start, end, inc in incidents if start <= t_start < end]
        state, out = model.step(state, model.demand_inputs(t_start.to_pydatetime(), active), rng=None)
        timestamps.append(forecast_end.isoformat(timespec="minutes"))

        scores = []
        for dept in cfg.DEPARTMENTS:
            raw = out[dept.id]
            row = dict(raw)
            row["load"] = float(raw["beds_occupied"] / raw["beds_total"]) if dept.kind == "beds" else float(raw["utilization"])
            row["pending_discharges"] = float(out["discharge"]["queue_length"]) if dept.kind == "beds" else 0.0
            score, level = _score_forecast_point(dept.id, row, recent_by_dept[dept.id], typical, forecast_end.to_pydatetime())
            recent_by_dept[dept.id].append({"arrivals": float(raw["arrivals"]), "load": row["load"]})
            recent_by_dept[dept.id] = recent_by_dept[dept.id][-cfg.SURGE_WINDOW_INTERVALS:]

            payload = forecasts[dept.id]
            payload["pressure_score"].append(score)
            payload["level"].append(level)
            payload["queue_length"].append(round(float(raw["queue_length"]), 2))
            payload["avg_wait_min"].append(round(float(raw["avg_wait_min"]), 1))
            payload["utilization"].append(round(float(raw["utilization"]), 3))
            scores.append(score)

        overall = round(0.5 * (sum(scores) / len(scores)) + 0.5 * max(scores), 3)
        overall_scores.append(overall)
        overall_levels.append(metrics.level_for_score(overall))

    changes = {dept_id: values["pressure_score"][-1] - values["pressure_score"][0] for dept_id, values in forecasts.items()}
    leading_id = max(changes, key=lambda dept_id: changes[dept_id])
    leading = forecasts[leading_id]

    return {
        "as_of": latest_time.to_pydatetime(),
        "horizon_minutes": horizon_minutes,
        "interval_minutes": cfg.INTERVAL_MIN,
        "timestamps": timestamps,
        "baseline": baseline,
        "overall": {"pressure_score": overall_scores, "level": overall_levels},
        "departments": forecasts,
        "headline": f'{leading["name"]} is projected to change by {changes[leading_id] * 100:+.1f} pressure points over {horizon_minutes} minutes.',
        "leading_department_id": leading_id,
    }
