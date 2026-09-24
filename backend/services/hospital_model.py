"""The hospital as a connected queue network.

`step()` advances the hospital by one interval.  It is deliberately independent
of storage and of the web layer, because three things will reuse it:

* the synthetic data generator (sampled mode, Poisson noise),
* the forecasting engine (expected-value mode, no randomness),
* the simulation engine (expected-value mode with a modified scenario).

Each station is a queue with a capacity per interval (staff x rate).  Work flows
between stations through `config.ROUTING`, and three lag-1 feedback loops
(`config.COUPLING`) let a problem in one department leak into the others.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from backend import config as cfg

MIN_RATE_PER_MIN = 0.02  # floor on throughput so a closed station cannot divide by zero


# ----------------------------------------------------------------------- sampling
def poisson(rng: random.Random, lam: float) -> int:
    """Poisson sample that only uses `rng.random()`.

    Python guarantees that stream is identical across versions and platforms, so
    the seeded demo data is identical on every machine.
    """
    if lam <= 0:
        return 0
    total = 0
    while lam > 20.0:  # Poisson(a) + Poisson(b) = Poisson(a + b)
        total += _knuth(rng, 20.0)
        lam -= 20.0
    return total + _knuth(rng, lam)


def _knuth(rng: random.Random, lam: float) -> int:
    limit = math.exp(-lam)
    k = 0
    p = 1.0
    while True:
        p *= rng.random()
        if p <= limit:
            return k
        k += 1


# ------------------------------------------------------------------ state / inputs
@dataclass
class State:
    queues: dict[str, float]  # waiting patients per station; "beds" holds patients boarding for a bed
    occupied_beds: float
    lab_delay: float = 0.0  # 0..1, how far laboratory turnaround is from normal (feeds back)


@dataclass
class Inputs:
    """What changes from interval to interval and is decided outside the model."""

    walkins: float  # expected external arrivals at Registration this interval
    emergency: float  # expected external arrivals at Emergency this interval
    discharge_shape: float  # relative rate of discharge decisions right now (weekly mean 1)
    staff: dict[str, int]  # staff on duty per station
    staff_planned: dict[str, int]  # staff rostered per station
    capacity: dict[str, float]  # 1.0 = normal, < 1.0 = outage or slowdown


def initial_state() -> State:
    queues = {station: 0.0 for station in cfg.STATION_IDS}
    queues["beds"] = 0.0
    return State(queues=queues, occupied_beds=cfg.TOTAL_BEDS * cfg.INITIAL_OCCUPANCY)


# ----------------------------------------------------------------------- demand
_DISCHARGE_MEAN = sum(cfg.DISCHARGE_SHAPE) / 24.0


def shift_index(hour: float) -> int:
    """0 = night (23-07), 1 = day (07-15), 2 = evening (15-23)."""
    if 7 <= hour < 15:
        return 1
    if 15 <= hour < 23:
        return 2
    return 0


def _interp(profile: tuple[float, ...], hour: float) -> float:
    """Linear interpolation of an hourly profile whose values sit at half past each hour."""
    position = hour - 0.5
    lower = math.floor(position)
    frac = position - lower
    return profile[lower % 24] * (1 - frac) + profile[(lower + 1) % 24] * frac


def demand_inputs(t_start: datetime, incidents: Iterable[cfg.Incident] = ()) -> Inputs:
    """Expected demand and staffing for the interval that starts at `t_start`."""
    hour = t_start.hour + t_start.minute / 60
    weekend = t_start.weekday() >= 5
    dt_h = cfg.INTERVAL_MIN / 60

    walkins = _interp(cfg.WALKIN_PER_HOUR, hour) * (cfg.WEEKEND_FACTOR["walkin"] if weekend else 1.0)
    emergency = _interp(cfg.EMERGENCY_PER_HOUR, hour) * (
        cfg.WEEKEND_FACTOR["emergency"] if weekend else 1.0
    )
    discharge_shape = (
        _interp(cfg.DISCHARGE_SHAPE, hour)
        / _DISCHARGE_MEAN
        * (cfg.WEEKEND_FACTOR["discharge"] if weekend else cfg.WEEKDAY_DISCHARGE_FACTOR)
    )

    shift = shift_index(hour)
    planned = {sid: cfg.DEPARTMENT_BY_ID[sid].staff[shift] for sid in cfg.STATION_IDS}
    staff = dict(planned)
    capacity = {sid: 1.0 for sid in cfg.STATION_IDS}

    for incident in incidents:
        walkins *= incident.walkin_arrivals
        emergency *= incident.emergency_arrivals
        for dept, mult in incident.capacity.items():
            capacity[dept] *= mult
        for dept, loss in incident.staff_loss.items():
            staff[dept] = max(1, staff[dept] - loss)

    return Inputs(
        walkins=walkins * dt_h,
        emergency=emergency * dt_h,
        discharge_shape=discharge_shape,
        staff=staff,
        staff_planned=planned,
        capacity=capacity,
    )


# -------------------------------------------------------------------------- step
def step(
    state: State, inp: Inputs, rng: random.Random | None = None
) -> tuple[State, dict[str, dict]]:
    """Advance one interval.

    With an `rng`, external and downstream arrivals are Poisson samples (realistic
    noise, used for history).  Without one, expected values are used, so the run is
    deterministic (used for forecasts and what-if scenarios).

    Returns the new state and one metrics row per department.
    """
    dt = float(cfg.INTERVAL_MIN)
    dt_h = dt / 60.0
    co = cfg.COUPLING
    route = cfg.ROUTING

    def draw(lam: float) -> float:
        return float(poisson(rng, lam)) if rng is not None else lam

    def run_station(dept_id: str, arrivals: float, efficiency: float = 1.0) -> dict:
        dept = cfg.DEPARTMENT_BY_ID[dept_id]
        staff = inp.staff[dept_id]
        capacity = staff * dept.rate * dt_h * inp.capacity[dept_id] * efficiency
        available = state.queues[dept_id] + arrivals
        served = min(available, capacity)
        queue = available - served
        wait = dept.base_wait + queue / max(capacity / dt, MIN_RATE_PER_MIN)
        return {
            "arrivals": arrivals,
            "served": served,
            "queue_length": queue,
            "staff_planned": inp.staff_planned[dept_id],
            "staff_on_duty": staff,
            "capacity": capacity,
            "utilization": served / capacity if capacity > 0 else 0.0,
            "avg_wait_min": wait,
            "beds_total": None,
            "beds_occupied": None,
        }

    # Lag-1 feedback: last interval's bed and laboratory conditions shape this one.
    boarding_penalty = min(
        co.boarding_penalty_max, co.boarding_penalty_per_patient * state.queues["beds"]
    )
    emergency_efficiency = (1.0 - boarding_penalty) * (
        1.0 - co.lab_to_emergency_penalty_max * state.lab_delay
    )

    registration = run_station("registration", draw(inp.walkins))
    opd = run_station("opd", draw(route[("registration", "opd")] * registration["served"]))
    emergency = run_station("emergency", draw(inp.emergency), emergency_efficiency)

    # Discharge decisions depend on ward occupancy and are slowed by lab delays.
    intervals_of_stay = cfg.AVG_LENGTH_OF_STAY_DAYS * 24.0 / dt_h
    ready_rate = (
        state.occupied_beds
        / intervals_of_stay
        * inp.discharge_shape
        * (1.0 - co.lab_to_discharge_penalty_max * state.lab_delay)
    )
    discharge = run_station("discharge", draw(ready_rate))

    laboratory = run_station(
        "laboratory",
        draw(
            route[("opd", "laboratory")] * opd["served"]
            + route[("emergency", "laboratory")] * emergency["served"]
        ),
    )
    radiology = run_station(
        "radiology",
        draw(
            route[("opd", "radiology")] * opd["served"]
            + route[("emergency", "radiology")] * emergency["served"]
        ),
    )
    pharmacy = run_station(
        "pharmacy",
        draw(
            route[("opd", "pharmacy")] * opd["served"]
            + route[("emergency", "pharmacy")] * emergency["served"]
            + route[("discharge", "pharmacy")] * discharge["served"]
        ),
    )

    # Beds: admissions need a free bed, discharges release one.
    usable = cfg.TOTAL_BEDS * cfg.USABLE_BED_FRACTION
    free = max(0.0, usable - state.occupied_beds)
    new_admissions = draw(
        route[("emergency", "beds")] * emergency["served"] + route[("opd", "beds")] * opd["served"]
    )
    demand = state.queues["beds"] + new_admissions
    admitted = min(demand, free)
    boarding = demand - admitted
    occupied = min(float(cfg.TOTAL_BEDS), max(0.0, state.occupied_beds + admitted - discharge["served"]))
    release_per_min = max(state.occupied_beds / (cfg.AVG_LENGTH_OF_STAY_DAYS * 1440.0), MIN_RATE_PER_MIN / 4)
    beds_dept = cfg.DEPARTMENT_BY_ID["beds"]
    beds = {
        "arrivals": new_admissions,
        "served": admitted,
        "queue_length": boarding,
        "staff_planned": 0,
        "staff_on_duty": 0,
        "capacity": free,
        "utilization": occupied / cfg.TOTAL_BEDS,
        "avg_wait_min": beds_dept.base_wait + boarding / release_per_min,
        "beds_total": cfg.TOTAL_BEDS,
        "beds_occupied": occupied,
    }

    lab_dept = cfg.DEPARTMENT_BY_ID["laboratory"]
    lab_delay = (laboratory["avg_wait_min"] - lab_dept.base_wait) / (
        lab_dept.critical_wait - lab_dept.base_wait
    )
    rows = {
        "registration": registration,
        "opd": opd,
        "emergency": emergency,
        "laboratory": laboratory,
        "radiology": radiology,
        "pharmacy": pharmacy,
        "beds": beds,
        "discharge": discharge,
    }
    new_state = State(
        queues={
            **{sid: rows[sid]["queue_length"] for sid in cfg.STATION_IDS},
            "beds": boarding,
        },
        occupied_beds=occupied,
        lab_delay=min(1.0, max(0.0, lab_delay)),
    )
    return new_state, rows
