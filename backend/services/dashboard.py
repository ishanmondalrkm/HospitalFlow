"""Builds the API payloads from the enriched metrics frame.

All values are converted to plain Python types (float / int / str / datetime) and
rounded, so they serialise to JSON without surprises (no NumPy scalars, no NaN).
"""
from __future__ import annotations

from datetime import datetime

import pandas as pd

from backend import config as cfg
from backend.services import metrics

STEPS_PER_HOUR = 60 // cfg.INTERVAL_MIN
HISTORY_HOURS = 24 * 7
SPARKLINE_HOURS = 24


# ------------------------------------------------------------------------ helpers
def _hourly(series: pd.Series, hours: int) -> pd.Series:
    """One value per hour, counting back from the latest sample (oldest first)."""
    return series.iloc[::-1].iloc[::STEPS_PER_HOUR].iloc[:hours].iloc[::-1]


def _floats(values, digits: int) -> list[float]:
    return [round(float(v), digits) for v in values]


def _datetimes(index) -> list[datetime]:
    return [ts.to_pydatetime() for ts in index]


def _department_status(dept: cfg.Department, row: pd.Series, hour_ago: pd.Series) -> dict:
    return {
        "id": dept.id,
        "name": dept.name,
        "kind": dept.kind,
        "arrivals_last_hour": round(float(row["arrivals_1h"]), 1),
        "queue_length": int(round(float(row["queue_length"]))),
        "avg_wait_min": round(float(row["avg_wait_min"]), 1),
        "utilization": round(float(row["load_1h"]), 3),
        "staff_on_duty": int(row["staff_on_duty"]),
        "staff_planned": int(row["staff_planned"]),
        "pressure_score": round(float(row["pressure"]), 3),
        "level": str(row["level"]),
        "pressure_delta_1h": round(float(row["pressure"] - hour_ago["pressure"]), 3),
        "breakdown": {
            "queue": round(float(row["c_queue"]), 3),
            "utilization": round(float(row["c_util"]), 3),
            "arrival_surge": round(float(row["c_surge"]), 3),
            "resource_constraint": round(float(row["c_resource"]), 3),
        },
    }


def _snapshot(df: pd.DataFrame) -> tuple[pd.Timestamp, pd.DataFrame, pd.DataFrame]:
    """The latest interval and the one an hour earlier, indexed by department."""
    now = df["timestamp"].max()
    hour_ago = now - pd.Timedelta(minutes=cfg.INTERVAL_MIN * STEPS_PER_HOUR)
    latest = df[df["timestamp"] == now].set_index("department_id")
    earlier = df[df["timestamp"] == hour_ago].set_index("department_id")
    return now, latest, earlier


def _headline(level: str, busiest: dict, high_or_critical: int) -> str:
    if high_or_critical:
        plural = "s" if high_or_critical != 1 else ""
        return f"{high_or_critical} department{plural} at high pressure or above, led by {busiest['name']}."
    if busiest["level"] == "LOW":
        return f"All departments are within normal limits. {busiest['name']} is the busiest."
    return f"{busiest['name']} has the highest pressure ({busiest['level'].lower()})."


# --------------------------------------------------------------------- dashboard
def build_dashboard(df: pd.DataFrame) -> dict:
    now, latest, earlier = _snapshot(df)
    ids = list(cfg.DEPARTMENT_IDS)

    departments = [
        _department_status(dept, latest.loc[dept.id], earlier.loc[dept.id]) for dept in cfg.DEPARTMENTS
    ]
    by_id = {d["id"]: d for d in departments}

    # Hospital-wide time series (one value per 15-minute interval).
    pressure = metrics.wide(df, "pressure")
    waits = metrics.wide(df, "avg_wait_min")
    queues = metrics.wide(df, "queue_length")
    arrivals_1h = metrics.wide(df, "arrivals_1h")
    load_1h = metrics.wide(df, "load_1h")
    staff = metrics.wide(df, "staff_on_duty")
    beds_occupied = metrics.wide(df, "beds_occupied")["beds"]
    beds_total = metrics.wide(df, "beds_total")["beds"]

    facing = list(cfg.PATIENT_FACING)
    stations = list(cfg.STATION_IDS)
    avg_wait = (waits[facing] * arrivals_1h[facing]).sum(axis=1) / arrivals_1h[facing].sum(axis=1).clip(lower=1e-9)
    in_system = queues[facing + ["beds"]].sum(axis=1) + beds_occupied
    bed_availability = (1 - beds_occupied / beds_total) * 100
    staff_utilization = (staff[stations] * load_1h[stations]).sum(axis=1) / staff[stations].sum(axis=1) * 100
    overall = metrics.overall_pressure(pressure)

    def kpi(key, label, series, unit, higher_is_worse, digits, level_from=None) -> dict:
        current = float(series.iloc[-1])
        hour_earlier = float(series.iloc[-1 - STEPS_PER_HOUR])
        return {
            "key": key,
            "label": label,
            "value": round(current, digits),
            "unit": unit,
            "delta_1h": round(current - hour_earlier, digits),
            "higher_is_worse": higher_is_worse,
            "level": by_id[level_from]["level"] if level_from else None,
            "sparkline": _floats(_hourly(series, SPARKLINE_HOURS), digits),
        }

    kpis = [
        kpi("avg_wait", "Average wait", avg_wait, "min", True, 1),
        kpi("emergency_wait", "Emergency wait", waits["emergency"], "min", True, 1, "emergency"),
        kpi("patients_in_system", "Patients in the system", in_system, "patients", True, 0),
        kpi("bed_availability", "Beds available", bed_availability, "%", False, 1, "beds"),
        kpi("staff_utilization", "Staff utilization", staff_utilization, "%", True, 1),
        kpi("lab_queue", "Laboratory queue", queues["laboratory"], "patients", True, 0, "laboratory"),
        kpi("radiology_queue", "Radiology queue", queues["radiology"], "patients", True, 0, "radiology"),
        kpi("discharge_pending", "Discharges pending", queues["discharge"], "patients", True, 0, "discharge"),
    ]

    overall_now = float(overall.iloc[-1])
    level = metrics.level_for_score(overall_now)
    busiest = max(departments, key=lambda d: d["pressure_score"])
    high_or_critical = sum(1 for d in departments if d["level"] in ("HIGH", "CRITICAL"))

    beds_row = latest.loc["beds"]
    occupied = int(round(float(beds_row["beds_occupied"])))
    total = int(beds_row["beds_total"])
    resources = {
        "beds": {
            "total": total,
            "occupied": occupied,
            "available": total - occupied,
            "availability_pct": round((total - occupied) / total * 100, 1),
            "boarding": by_id["beds"]["queue_length"],
            "pending_discharges": by_id["discharge"]["queue_length"],
        },
        "staff": [
            {
                "department_id": d["id"],
                "name": d["name"],
                "on_duty": d["staff_on_duty"],
                "planned": d["staff_planned"],
                "utilization": d["utilization"],
            }
            for d in departments
            if d["kind"] == "station"
        ],
    }

    overall_hourly = _hourly(overall, HISTORY_HOURS)
    history = {
        "timestamps": _datetimes(overall_hourly.index),
        "overall": _floats(overall_hourly, 3),
        "departments": {dept_id: _floats(_hourly(pressure[dept_id], HISTORY_HOURS), 3) for dept_id in ids},
    }

    return {
        "as_of": now.to_pydatetime(),
        "data_source": cfg.DATA_SOURCE,
        "hospital": {
            "name": cfg.HOSPITAL_NAME,
            "status": cfg.STATUS_LABELS[level],
            "level": level,
            "overall_score": round(overall_now, 3),
            "overall_delta_1h": round(overall_now - float(overall.iloc[-1 - STEPS_PER_HOUR]), 3),
            "headline": _headline(level, busiest, high_or_critical),
            "busiest_department": busiest["name"],
            "departments_high_or_critical": high_or_critical,
        },
        "kpis": kpis,
        "departments": departments,
        "resources": resources,
        "history": history,
        "scoring": {
            "weights": dict(cfg.PRESSURE_WEIGHTS),
            "thresholds": {name.lower(): value for name, value in cfg.LEVEL_THRESHOLDS.items()},
        },
    }


# ------------------------------------------------------------------- departments
def _department_info(dept: cfg.Department, status: dict) -> dict:
    night, day, evening = dept.staff
    return {
        "id": dept.id,
        "name": dept.name,
        "kind": dept.kind,
        "staffing": {"night": night, "day": day, "evening": evening},
        "rate_per_staff_hour": dept.rate,
        "base_wait_min": dept.base_wait,
        "critical_wait_min": dept.critical_wait,
        "status": status,
    }


def build_departments(df: pd.DataFrame) -> list[dict]:
    _, latest, earlier = _snapshot(df)
    return [
        _department_info(dept, _department_status(dept, latest.loc[dept.id], earlier.loc[dept.id]))
        for dept in cfg.DEPARTMENTS
    ]


def build_department_detail(df: pd.DataFrame, department_id: str, hours: int = 24) -> dict | None:
    dept = cfg.DEPARTMENT_BY_ID.get(department_id)
    if dept is None:
        return None
    _, latest, earlier = _snapshot(df)
    info = _department_info(dept, _department_status(dept, latest.loc[dept.id], earlier.loc[dept.id]))
    rows = df[df["department_id"] == department_id].tail(hours * STEPS_PER_HOUR)
    info["history"] = {
        "timestamps": _datetimes(rows["timestamp"]),
        "arrivals": _floats(rows["arrivals"], 2),
        "queue_length": _floats(rows["queue_length"], 2),
        "avg_wait_min": _floats(rows["avg_wait_min"], 1),
        "utilization": _floats(rows["load"], 3),
        "pressure_score": _floats(rows["pressure"], 3),
    }
    return info
