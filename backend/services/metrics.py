"""Derived operational metrics: pressure components, scores and levels.

Everything here is a pure function of the raw `operational_metrics` table, so the
same code scores history, the current state and (later) simulated states.

Pressure is built from four interpretable components, each scaled to 0..1:

    queue                how far the wait has moved from normal towards critical
    utilization          how close to full capacity (occupancy for beds)
    arrival_surge        arrivals vs the typical level for this time of day (2-hour window)
    resource_constraint  missing staff, or beds blocked by pending discharges

    pressure = sum(weight * component)      (weights in config.PRESSURE_WEIGHTS)

The score maps to LOW / MEDIUM / HIGH / CRITICAL using config.LEVEL_THRESHOLDS.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from backend import config as cfg

LEVELS = ("LOW", "MEDIUM", "HIGH", "CRITICAL")
ROLLING_INTERVALS = 4  # one hour of 15-minute intervals


def level_for_score(score: float) -> str:
    thresholds = cfg.LEVEL_THRESHOLDS
    if score >= thresholds["CRITICAL"]:
        return "CRITICAL"
    if score >= thresholds["HIGH"]:
        return "HIGH"
    if score >= thresholds["MEDIUM"]:
        return "MEDIUM"
    return "LOW"


def _clip01(values):
    return np.clip(values, 0.0, 1.0)


def _rolling(frame: pd.DataFrame, column: str, how: str, window: int = ROLLING_INTERVALS) -> pd.Series:
    grouped = frame.groupby("department_id", sort=False)[column]
    if how == "sum":
        return grouped.transform(lambda s: s.rolling(window, min_periods=1).sum())
    return grouped.transform(lambda s: s.rolling(window, min_periods=1).mean())


def enrich(raw: pd.DataFrame) -> pd.DataFrame:
    """Add rolling windows, pressure components, score and level to raw metric rows."""
    df = raw.sort_values(["department_id", "timestamp"]).reset_index(drop=True)
    is_beds = df["department_id"] == "beds"

    df["is_weekend"] = df["timestamp"].dt.dayofweek >= 5
    df["slot"] = df["timestamp"].dt.hour * 4 + df["timestamp"].dt.minute // 15

    # Occupancy stands in for utilisation on the beds row.
    occupancy = df["beds_occupied"] / df["beds_total"]
    df["load"] = np.where(is_beds, occupancy, df["utilization"])
    df["arrivals_1h"] = _rolling(df, "arrivals", "sum")
    df["load_1h"] = _rolling(df, "load", "mean")

    # "Typical" arrivals: median for the same department, day type and time of day.
    # (Computed over the whole history for simplicity; live data would use a trailing window.)
    df["typical"] = df.groupby(["department_id", "is_weekend", "slot"])["arrivals"].transform("median")
    df["typical_1h"] = _rolling(df, "typical", "sum")
    window = cfg.SURGE_WINDOW_INTERVALS
    arrivals_window = _rolling(df, "arrivals", "sum", window)
    typical_window = _rolling(df, "typical", "sum", window)
    df["surge_ratio"] = (arrivals_window - typical_window) / typical_window.clip(lower=cfg.SURGE_MIN_VOLUME)

    # Beds are "blocked" while their occupants wait for discharge processing.
    pending = df.loc[df["department_id"] == "discharge"].set_index("timestamp")["queue_length"]
    df["pending_discharges"] = df["timestamp"].map(pending).where(is_beds, 0.0).fillna(0.0)

    base_wait = df["department_id"].map({d.id: d.base_wait for d in cfg.DEPARTMENTS}).astype(float)
    critical_wait = df["department_id"].map({d.id: d.critical_wait for d in cfg.DEPARTMENTS}).astype(float)
    c_queue = _clip01((df["avg_wait_min"] - base_wait) / (critical_wait - base_wait))

    floor = np.where(is_beds, cfg.BED_LOAD_FLOOR, cfg.STATION_LOAD_FLOOR)
    ceil = np.where(is_beds, cfg.BED_LOAD_CEIL, 1.0)
    c_util = _clip01((df["load_1h"] - floor) / (ceil - floor))

    c_surge = _clip01(
        (df["surge_ratio"] - cfg.SURGE_DEADZONE) / (cfg.SURGE_SATURATION - cfg.SURGE_DEADZONE)
    )

    planned = df["staff_planned"].astype(float)
    shortfall = ((planned - df["staff_on_duty"]) / planned.where(planned > 0)).fillna(0.0)
    blocked = (df["pending_discharges"] / df["beds_occupied"].where(is_beds)).fillna(0.0)
    c_resource = _clip01(
        np.where(is_beds, blocked * cfg.BLOCKED_BEDS_GAIN, shortfall * cfg.STAFF_SHORTFALL_GAIN)
    )

    weights = cfg.PRESSURE_WEIGHTS
    score = (
        weights["queue"] * c_queue
        + weights["utilization"] * c_util
        + weights["arrival_surge"] * c_surge
        + weights["resource_constraint"] * c_resource
    )
    score = score.round(3)  # level and displayed score must agree
    thresholds = cfg.LEVEL_THRESHOLDS
    df["c_queue"] = c_queue
    df["c_util"] = c_util
    df["c_surge"] = c_surge
    df["c_resource"] = c_resource
    df["pressure"] = score
    df["level"] = np.select(
        [score >= thresholds["CRITICAL"], score >= thresholds["HIGH"], score >= thresholds["MEDIUM"]],
        ["CRITICAL", "HIGH", "MEDIUM"],
        default="LOW",
    )
    return df


def wide(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """One row per timestamp, one column per department (in flow order)."""
    return df.pivot(index="timestamp", columns="department_id", values=column)[list(cfg.DEPARTMENT_IDS)]


def overall_pressure(pressure: pd.DataFrame) -> pd.Series:
    """Hospital-wide score: half the average, half the worst department."""
    return 0.5 * pressure.mean(axis=1) + 0.5 * pressure.max(axis=1)
