"""Deterministic what-if simulation on the same connected hospital model."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

import pandas as pd

from backend import config as cfg
from backend.services import data_generator, forecast, hospital_model as model, metrics


@dataclass(frozen=True)
class Scenario:
    emergency_arrival_pct: float = 0.0
    walkin_arrival_pct: float = 0.0
    emergency_staff_delta: int = 0
    laboratory_staff_delta: int = 0
    discharge_staff_delta: int = 0
    laboratory_capacity_pct: float = 0.0
    discharge_capacity_pct: float = 0.0


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _score_point(dept_id: str, row: dict, recent: list[dict], typical: dict, timestamp) -> tuple[float, str]:
    return forecast._score_forecast_point(dept_id, row, recent, typical, timestamp)


def _recent_history(df: pd.DataFrame) -> dict[str, list[dict]]:
    result: dict[str, list[dict]] = {}
    for dept_id in cfg.DEPARTMENT_IDS:
        rows = df[df["department_id"] == dept_id].tail(cfg.SURGE_WINDOW_INTERVALS - 1)
        result[dept_id] = [
            {
                "arrivals": float(r.arrivals),
                "load": float(r.beds_occupied / r.beds_total) if dept_id == "beds" else float(r.utilization),
            }
            for r in rows.itertuples()
        ]
    return result


def _apply_scenario(inp: model.Inputs, scenario: Scenario) -> model.Inputs:
    """Apply the same intervention during every simulated interval."""
    inp.walkins *= max(0.0, 1.0 + scenario.walkin_arrival_pct)
    inp.emergency *= max(0.0, 1.0 + scenario.emergency_arrival_pct)

    staff_changes = {
        "emergency": scenario.emergency_staff_delta,
        "laboratory": scenario.laboratory_staff_delta,
        "discharge": scenario.discharge_staff_delta,
    }
    for dept_id, delta in staff_changes.items():
        if delta:
            new_staff = max(1, int(inp.staff[dept_id]) + int(delta))
            inp.staff[dept_id] = new_staff
            # Added staff represents additional planned coverage for the scenario,
            # so the resource-pressure component does not penalize the intervention.
            inp.staff_planned[dept_id] = max(int(inp.staff_planned[dept_id]), new_staff)

    inp.capacity["laboratory"] *= max(0.0, 1.0 + scenario.laboratory_capacity_pct)
    inp.capacity["discharge"] *= max(0.0, 1.0 + scenario.discharge_capacity_pct)
    return inp


def _run_path(
    df: pd.DataFrame,
    state: model.State,
    horizon_minutes: int,
    scenario: Scenario,
) -> dict:
    latest_time = df["timestamp"].max()
    typical = forecast._typical_arrivals(df)
    recent = _recent_history(df)
    incidents = data_generator.incident_windows(latest_time.to_pydatetime())

    forecasts = {
        dept.id: {
            "id": dept.id,
            "name": dept.name,
            "kind": dept.kind,
            "pressure_score": [],
            "level": [],
            "queue_length": [],
            "avg_wait_min": [],
            "utilization": [],
        }
        for dept in cfg.DEPARTMENTS
    }
    timestamps: list[str] = []
    overall_scores: list[float] = []
    overall_levels: list[str] = []

    for step_number in range(1, horizon_minutes // cfg.INTERVAL_MIN + 1):
        forecast_end = latest_time + timedelta(minutes=cfg.INTERVAL_MIN * step_number)
        t_start = forecast_end - timedelta(minutes=cfg.INTERVAL_MIN)
        active = [inc for start, end, inc in incidents if start <= t_start < end]
        inp = model.demand_inputs(t_start.to_pydatetime(), active)
        _apply_scenario(inp, scenario)
        state, out = model.step(state, inp, rng=None)
        timestamps.append(forecast_end.isoformat(timespec="minutes"))

        scores = []
        for dept in cfg.DEPARTMENTS:
            raw = out[dept.id]
            row = dict(raw)
            row["load"] = float(raw["beds_occupied"] / raw["beds_total"]) if dept.kind == "beds" else float(raw["utilization"])
            row["pending_discharges"] = float(out["discharge"]["queue_length"]) if dept.kind == "beds" else 0.0
            score, level = _score_point(
                dept.id,
                row,
                recent[dept.id],
                typical,
                forecast_end.to_pydatetime(),
            )
            recent[dept.id].append({"arrivals": float(raw["arrivals"]), "load": row["load"]})
            recent[dept.id] = recent[dept.id][-cfg.SURGE_WINDOW_INTERVALS:]

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

    return {
        "timestamps": timestamps,
        "overall": {"pressure_score": overall_scores, "level": overall_levels},
        "departments": forecasts,
    }


def _state_pair(df: pd.DataFrame) -> tuple[model.State, model.State]:
    baseline, _ = forecast._latest_state(df)
    # State is made of mutable dictionaries; build an independent copy for the second run.
    scenario = model.State(
        queues=dict(baseline.queues),
        occupied_beds=baseline.occupied_beds,
        lab_delay=baseline.lab_delay,
    )
    return baseline, scenario


def _department_impacts(base: dict, scenario: dict) -> dict[str, dict]:
    result = {}
    for dept_id, base_dept in base["departments"].items():
        sim_dept = scenario["departments"][dept_id]
        base_pressure = base_dept["pressure_score"][-1]
        sim_pressure = sim_dept["pressure_score"][-1]
        base_wait = base_dept["avg_wait_min"][-1]
        sim_wait = sim_dept["avg_wait_min"][-1]
        base_queue = base_dept["queue_length"][-1]
        sim_queue = sim_dept["queue_length"][-1]
        result[dept_id] = {
            "name": base_dept["name"],
            "pressure_delta": round(sim_pressure - base_pressure, 3),
            "queue_delta": round(sim_queue - base_queue, 2),
            "wait_delta_min": round(sim_wait - base_wait, 1),
            "projected_pressure": round(sim_pressure, 3),
            "projected_level": sim_dept["level"][-1],
        }
    return result


def build_simulation(df: pd.DataFrame, horizon_minutes: int, scenario: Scenario) -> dict:
    if horizon_minutes not in (30, 60, 120):
        raise ValueError("horizon_minutes must be 30, 60, or 120")

    latest_time = df["timestamp"].max()
    latest_rows = df[df["timestamp"] == latest_time].set_index("department_id")
    baseline, scenario_state = _state_pair(df)
    base_path = _run_path(df, baseline, horizon_minutes, Scenario())
    scenario_path = _run_path(df, scenario_state, horizon_minutes, scenario)

    impacts = _department_impacts(base_path, scenario_path)
    overall_base = base_path["overall"]["pressure_score"][-1]
    overall_scenario = scenario_path["overall"]["pressure_score"][-1]

    return {
        "as_of": latest_time.to_pydatetime(),
        "horizon_minutes": horizon_minutes,
        "interval_minutes": cfg.INTERVAL_MIN,
        "timestamps": base_path["timestamps"],
        "scenario": {
            "emergency_arrival_pct": scenario.emergency_arrival_pct,
            "walkin_arrival_pct": scenario.walkin_arrival_pct,
            "emergency_staff_delta": scenario.emergency_staff_delta,
            "laboratory_staff_delta": scenario.laboratory_staff_delta,
            "discharge_staff_delta": scenario.discharge_staff_delta,
            "laboratory_capacity_pct": scenario.laboratory_capacity_pct,
            "discharge_capacity_pct": scenario.discharge_capacity_pct,
        },
        "current": {
            "overall_pressure": round(float(latest_rows["pressure"].mean() * 0.5 + latest_rows["pressure"].max() * 0.5), 3),
            "overall_level": metrics.level_for_score(float(latest_rows["pressure"].mean() * 0.5 + latest_rows["pressure"].max() * 0.5)),
            "projected_pressure": round(overall_base, 3),
            "projected_level": base_path["overall"]["level"][-1],
        },
        "baseline": base_path,
        "simulated": scenario_path,
        "overall_impact": {
            "pressure_delta": round(overall_scenario - overall_base, 3),
            "pressure_points": round((overall_scenario - overall_base) * 100, 1),
            "projected_pressure": round(overall_scenario, 3),
            "projected_level": scenario_path["overall"]["level"][-1],
        },
        "department_impacts": impacts,
    }
