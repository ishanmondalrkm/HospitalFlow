"""HospitalFlow configuration and hospital operational model parameters.

This module is the single source of truth for *what the hospital looks like*:
departments, staffing per shift, how patients route between departments, how
strongly departments influence each other, how "pressure" is scored, and the
scripted incidents injected into the synthetic history.

The generator, the metrics layer and (in later phases) the forecasting and
simulation engines all read from here, so they always agree on one model.
Nothing in this project is patient-level: every number is an operational count.
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# --------------------------------------------------------------------------- app
API_VERSION = "0.1.0"
HOSPITAL_NAME = "Demo General Hospital"
DATA_SOURCE = "synthetic"

# MongoDB is introduced in Phase 8A as the persistence foundation for live
# operational data, alerts and historical snapshots. Keep credentials/configuration
# outside source control; local development defaults to the standard MongoDB port.
MONGODB_URI = os.getenv("HOSPITALFLOW_MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DATABASE = os.getenv("HOSPITALFLOW_MONGODB_DATABASE", "hospitalflow")
MONGODB_SERVER_SELECTION_TIMEOUT_MS = int(os.getenv("HOSPITALFLOW_MONGODB_SERVER_SELECTION_TIMEOUT_MS", "1500"))
MONGODB_CONNECT_TIMEOUT_MS = int(os.getenv("HOSPITALFLOW_MONGODB_CONNECT_TIMEOUT_MS", "1500"))

# Phase 8C live operational feed. One simulator tick represents one hospital
# 15-minute interval, while LIVE_INTERVAL_SECONDS controls how quickly the
# demo advances that clock. Set HOSPITALFLOW_LIVE_SIMULATOR_ENABLED=false to
# keep the feed manual.
LIVE_SIMULATOR_ENABLED = os.getenv("HOSPITALFLOW_LIVE_SIMULATOR_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
LIVE_INTERVAL_SECONDS = max(2, int(os.getenv("HOSPITALFLOW_LIVE_INTERVAL_SECONDS", "15")))
LIVE_HOSPITAL_INTERVAL_MIN = int(os.getenv("HOSPITALFLOW_LIVE_HOSPITAL_INTERVAL_MIN", "15"))

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("HOSPITALFLOW_DB", BASE_DIR / "data" / "hospitalflow.db"))
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "HOSPITALFLOW_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if origin.strip()
]

# ------------------------------------------------------- synthetic history window
GENERATOR_VERSION = "1"  # bump when hospital_model.py or the generator code changes
# Curated seed: at REFERENCE_NOW the hospital is busy but stable (Emergency near 95% utilised,
# about 16% of beds free, no department above LOW), which is the starting point of the demo.
# Found by scoring seeds 1-400 against that target (Emergency leading and rising); any seed works, the snapshot just differs.
SEED = 245
INTERVAL_MIN = 15  # every metric is recorded per 15-minute interval
HISTORY_DAYS = 14
WARMUP_DAYS = 3  # simulated but discarded, so queues and occupancy start in a natural state
# A fixed "now" keeps the demo deterministic (a Tuesday, mid-morning).
REFERENCE_NOW = datetime(2026, 9, 15, 10, 0)

# ------------------------------------------------------------------- departments


@dataclass(frozen=True)
class Department:
    id: str
    name: str
    kind: str  # "station" processes patients; "beds" is a stock of beds
    staff: tuple[int, int, int]  # planned staff: night (23-07), day (07-15), evening (15-23)
    rate: float  # patients (or orders) one staff member processes per hour
    base_wait: float  # minutes a patient waits even with nobody ahead (triage, sampling, paperwork)
    critical_wait: float  # wait (minutes) at which queue pressure saturates


# Listed in patient-flow order.
DEPARTMENTS: tuple[Department, ...] = (
    Department("registration", "Registration", "station", (1, 7, 4), 14.0, 3, 30),
    Department("opd", "OPD", "station", (1, 16, 12), 5.2, 10, 90),
    Department("emergency", "Emergency", "station", (6, 8, 10), 2.5, 26, 90),
    Department("laboratory", "Laboratory", "station", (3, 5, 4), 9.5, 20, 120),
    Department("radiology", "Radiology", "station", (2, 4, 3), 4.5, 15, 90),
    Department("pharmacy", "Pharmacy", "station", (2, 5, 4), 10.0, 5, 45),
    Department("beds", "Beds", "beds", (0, 0, 0), 0.0, 45, 240),
    Department("discharge", "Discharge", "station", (1, 4, 3), 2.2, 40, 180),
)
DEPARTMENT_BY_ID = {d.id: d for d in DEPARTMENTS}
DEPARTMENT_IDS = tuple(d.id for d in DEPARTMENTS)
STATION_IDS = tuple(d.id for d in DEPARTMENTS if d.kind == "station")
# Departments patients actually queue in (used for the "average wait" KPI).
PATIENT_FACING = ("registration", "opd", "emergency", "laboratory", "radiology", "pharmacy")

# -------------------------------------------------------------------- bed model
TOTAL_BEDS = 220
USABLE_BED_FRACTION = 0.94  # the rest is isolation, cleaning, maintenance
AVG_LENGTH_OF_STAY_DAYS = 4.0
INITIAL_OCCUPANCY = 0.80

# ----------------------------------------------------------------- routing
# Work created downstream per patient served upstream (orders, referrals, admissions).
ROUTING: dict[tuple[str, str], float] = {
    ("registration", "opd"): 0.97,
    ("opd", "laboratory"): 0.40,
    ("opd", "radiology"): 0.10,
    ("opd", "pharmacy"): 0.55,
    ("opd", "beds"): 0.008,
    ("emergency", "laboratory"): 0.85,
    ("emergency", "radiology"): 0.35,
    ("emergency", "pharmacy"): 0.20,
    ("emergency", "beds"): 0.13,
    ("discharge", "pharmacy"): 0.60,
}


@dataclass(frozen=True)
class Coupling:
    """Feedback loops that turn separate queues into one connected system.

    The chain they encode (from the project plan):
      emergency surge -> emergency queue -> staff load -> lab orders -> lab queue
      -> slower bed turnover -> discharge delay -> fewer free beds -> emergency pressure
    """

    # Patients boarding in Emergency because no bed is free block treatment space.
    boarding_penalty_per_patient: float = 0.012
    boarding_penalty_max: float = 0.25
    # Slow lab turnaround keeps Emergency patients in bays waiting for results ...
    lab_to_emergency_penalty_max: float = 0.12
    # ... and delays discharge decisions on the wards.
    lab_to_discharge_penalty_max: float = 0.30


COUPLING = Coupling()

# ------------------------------------------------------------- demand profiles
# Expected external arrivals per hour, by hour of day (weekday).  Each value is
# the rate at the middle of that hour; the model interpolates between them.
WALKIN_PER_HOUR = (
    1.5, 1.0, 1.0, 1.0, 1.0, 2.0, 7.0, 22.0, 50.0, 66.0, 70.0, 62.0,
    46.0, 40.0, 46.0, 44.0, 34.0, 22.0, 12.0, 6.0, 4.0, 3.0, 2.0, 2.0,
)  # patients entering through Registration and becoming OPD patients
EMERGENCY_PER_HOUR = (
    9.0, 7.5, 6.5, 6.0, 6.0, 6.5, 8.0, 10.0, 13.0, 15.0, 16.0, 16.5,
    16.0, 15.5, 15.0, 15.5, 17.0, 18.5, 20.0, 20.0, 19.0, 17.0, 14.0, 11.0,
)
# Relative rate of discharge decisions through the day (ward rounds peak late morning).
DISCHARGE_SHAPE = (
    0.1, 0.1, 0.1, 0.1, 0.1, 0.15, 0.3, 0.6, 1.2, 1.9, 2.2, 2.2,
    2.0, 1.6, 1.4, 1.2, 1.0, 0.8, 0.6, 0.4, 0.3, 0.2, 0.15, 0.1,
)
# Weekly mean of the discharge factor is 1: (5 * 1.10 + 2 * 0.75) / 7.
WEEKDAY_DISCHARGE_FACTOR = 1.10
WEEKEND_FACTOR = {"walkin": 0.40, "emergency": 1.12, "discharge": 0.75}

# --------------------------------------------------------------- pressure model
# pressure = sum(weight * component); every component is scaled to 0..1 so the
# score is easy to explain: "queue 0.6, utilisation 0.9, arrivals 0.3, staffing 0.0".
PRESSURE_WEIGHTS = {
    "queue": 0.35,  # how far the wait has moved from normal towards its critical value
    "utilization": 0.30,  # how close to full capacity (occupancy for beds)
    "arrival_surge": 0.20,  # arrivals compared with the typical level for this time of day
    "resource_constraint": 0.15,  # missing staff (stations) or beds blocked by pending discharges
}
STATION_LOAD_FLOOR = 0.70  # utilisation below this adds no pressure
BED_LOAD_FLOOR = 0.80
BED_LOAD_CEIL = 0.95
SURGE_WINDOW_INTERVALS = 8  # arrivals are compared over two hours to smooth Poisson noise
SURGE_DEADZONE = 0.10  # arrivals within +10% of typical add no pressure
SURGE_SATURATION = 0.50  # +50% vs typical arrivals means full surge pressure
SURGE_MIN_VOLUME = 16.0  # arrivals per window; damps noise for low-volume departments
STAFF_SHORTFALL_GAIN = 2.5  # a 40% staffing gap means full resource pressure
BLOCKED_BEDS_GAIN = 10.0  # 10% of occupied beds waiting on discharge means full pressure
LEVEL_THRESHOLDS = {"MEDIUM": 0.35, "HIGH": 0.55, "CRITICAL": 0.75}
STATUS_LABELS = {
    "LOW": "Stable",
    "MEDIUM": "Elevated",
    "HIGH": "Under strain",
    "CRITICAL": "Critical",
}

# --------------------------------------------------------------- scripted incidents


@dataclass(frozen=True)
class Incident:
    name: str
    days_ago: int  # calendar days before REFERENCE_NOW's date
    start_hour: float
    hours: float
    emergency_arrivals: float = 1.0  # multiplier
    walkin_arrivals: float = 1.0  # multiplier
    capacity: dict[str, float] = field(default_factory=dict)  # department -> capacity multiplier
    staff_loss: dict[str, int] = field(default_factory=dict)  # department -> staff missing


# They give the history the patterns the plan asks for: rush hours, an emergency
# surge, laboratory delays, discharge bottlenecks and staffing constraints.
INCIDENTS: tuple[Incident, ...] = (
    Incident("Radiology scanner outage", 12, 10, 4, capacity={"radiology": 0.4}),
    Incident("Emergency evening shift short-staffed", 10, 15, 8, staff_loss={"emergency": 3}),
    Incident("Seasonal illness spike", 8, 9, 6, emergency_arrivals=1.45, walkin_arrivals=1.3),
    Incident("Laboratory analyser downtime", 6, 8, 4, capacity={"laboratory": 0.55}),
    Incident("Discharge processing slowdown", 5, 10, 8, capacity={"discharge": 0.4}),
    Incident("Saturday evening emergency surge", 3, 18, 4, emergency_arrivals=1.7),
)

for _profile in (WALKIN_PER_HOUR, EMERGENCY_PER_HOUR, DISCHARGE_SHAPE):
    assert len(_profile) == 24, "hourly profiles need exactly 24 values"


def model_fingerprint() -> str:
    """Short hash of everything that shapes the synthetic data.

    Stored next to the database, so tuning any parameter above rebuilds a stale
    database automatically instead of silently serving old numbers.
    """
    shaping = (
        GENERATOR_VERSION, SEED, INTERVAL_MIN, HISTORY_DAYS, WARMUP_DAYS, REFERENCE_NOW,
        DEPARTMENTS, TOTAL_BEDS, USABLE_BED_FRACTION, AVG_LENGTH_OF_STAY_DAYS, INITIAL_OCCUPANCY,
        sorted(ROUTING.items()), COUPLING, WALKIN_PER_HOUR, EMERGENCY_PER_HOUR, DISCHARGE_SHAPE,
        WEEKDAY_DISCHARGE_FACTOR, sorted(WEEKEND_FACTOR.items()), INCIDENTS,
    )
    return hashlib.sha1(repr(shaping).encode("utf-8")).hexdigest()[:12]
