"""API response models: the contract the React app codes against.

There is no patient-level data in HospitalFlow.  Every field is an operational
count, a duration, a ratio or a score.
"""
from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field

Level = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
DepartmentKind = Literal["station", "beds"]


class PressureBreakdown(BaseModel):
    """The unweighted 0..1 components behind a pressure score."""

    queue: float
    utilization: float
    arrival_surge: float
    resource_constraint: float


class DepartmentStatus(BaseModel):
    id: str
    name: str
    kind: DepartmentKind
    arrivals_last_hour: float
    queue_length: int  # patients waiting (patients boarding for a bed, for the beds row)
    avg_wait_min: float
    utilization: float  # 0..1, one-hour average (occupancy for beds)
    staff_on_duty: int
    staff_planned: int
    pressure_score: float  # 0..1
    level: Level
    pressure_delta_1h: float  # change in score over the last hour
    breakdown: PressureBreakdown


class Kpi(BaseModel):
    key: str
    label: str
    value: float
    unit: str
    delta_1h: float
    higher_is_worse: bool
    level: Optional[Level] = None
    sparkline: List[float]  # last 24 hours, one value per hour


class HospitalSummary(BaseModel):
    name: str
    status: str  # Stable / Elevated / Under strain / Critical
    level: Level
    overall_score: float
    overall_delta_1h: float
    headline: str
    busiest_department: str
    departments_high_or_critical: int


class BedResources(BaseModel):
    total: int
    occupied: int
    available: int
    availability_pct: float
    boarding: int  # admitted patients still waiting for a bed
    pending_discharges: int  # beds held by patients waiting for discharge processing


class StaffResource(BaseModel):
    department_id: str
    name: str
    on_duty: int
    planned: int
    utilization: float


class Resources(BaseModel):
    beds: BedResources
    staff: List[StaffResource]


class PressureHistory(BaseModel):
    timestamps: List[datetime]  # hourly, oldest first
    overall: List[float]
    departments: Dict[str, List[float]]


class ScoringModel(BaseModel):
    weights: Dict[str, float]
    thresholds: Dict[str, float]  # score at which each level starts


class DashboardResponse(BaseModel):
    as_of: datetime
    data_source: str
    hospital: HospitalSummary
    kpis: List[Kpi]
    departments: List[DepartmentStatus]
    resources: Resources
    history: PressureHistory
    scoring: ScoringModel


class StaffingByShift(BaseModel):
    night: int
    day: int
    evening: int


class DepartmentInfo(BaseModel):
    id: str
    name: str
    kind: DepartmentKind
    staffing: StaffingByShift
    rate_per_staff_hour: float
    base_wait_min: float
    critical_wait_min: float
    status: DepartmentStatus


class DepartmentSeries(BaseModel):
    timestamps: List[datetime]  # 15-minute intervals, oldest first
    arrivals: List[float]
    queue_length: List[float]
    avg_wait_min: List[float]
    utilization: List[float]
    pressure_score: List[float]


class DepartmentDetail(DepartmentInfo):
    history: DepartmentSeries




class OperationalHistorySnapshot(BaseModel):
    source: str
    department_id: str
    department_name: str
    timestamp: datetime
    arrivals: float
    served: float
    queue_length: float
    staff_planned: int
    staff_on_duty: int
    capacity: float
    utilization: float
    avg_wait_min: float
    beds_total: Optional[int] = None
    beds_occupied: Optional[float] = None
    pressure: float
    level: Level
    pressure_components: PressureBreakdown


class OperationalHistoryResponse(BaseModel):
    count: int
    hours: int
    department_id: Optional[str] = None
    source: Optional[str] = None
    snapshots: List[OperationalHistorySnapshot]

class MongoHealth(BaseModel):
    available: bool
    database: str


class HealthResponse(BaseModel):
    status: Literal["ok"]
    version: str
    data_source: str
    as_of: datetime
    rows: int
    mongodb: MongoHealth

class ForecastDepartment(BaseModel):
    id: str
    name: str
    kind: DepartmentKind
    pressure_score: List[float]
    level: List[Level]
    queue_length: List[float]
    avg_wait_min: List[float]
    utilization: List[float]

class ForecastBaseline(BaseModel):
    pressure_score: float
    level: Level
    queue_length: float
    avg_wait_min: float

class ForecastOverall(BaseModel):
    pressure_score: List[float]
    level: List[Level]

class ForecastResponse(BaseModel):
    as_of: datetime
    horizon_minutes: int
    interval_minutes: int
    timestamps: List[datetime]
    baseline: Dict[str, ForecastBaseline]
    overall: ForecastOverall
    departments: Dict[str, ForecastDepartment]
    headline: str
    leading_department_id: str


class BottleneckContributor(BaseModel):
    key: str
    label: str
    value: float
    weight: float
    contribution: float
    share: float
    reason: str


class BottleneckDepartment(BaseModel):
    id: str
    name: str
    kind: DepartmentKind
    pressure_score: float
    level: Level
    queue_length: int
    avg_wait_min: float
    utilization: float
    pressure_delta_1h: float
    contributors: List[BottleneckContributor]


class PropagationLink(BaseModel):
    source_id: str
    source_name: str
    source_level: Level
    target_id: str
    target_name: str
    target_level: Level
    routing_factor: float
    propagation_score: float
    signal: str


class BottleneckChainItem(BaseModel):
    id: str
    name: str
    level: Level
    pressure_score: float


class BottleneckSummary(BaseModel):
    high_or_critical: int
    medium_or_above: int


class BottleneckResponse(BaseModel):
    as_of: datetime
    headline: str
    leading_department_id: str
    departments: List[BottleneckDepartment]
    propagation: List[PropagationLink]
    chain: List[BottleneckChainItem]
    summary: BottleneckSummary
    weights: Dict[str, float]

class SimulationRequest(BaseModel):
    horizon_minutes: Literal[30, 60, 120] = 60
    emergency_arrival_pct: float = Field(0.0, ge=-0.30, le=0.50)
    walkin_arrival_pct: float = Field(0.0, ge=-0.30, le=0.50)
    emergency_staff_delta: int = Field(0, ge=-3, le=4)
    laboratory_staff_delta: int = Field(0, ge=-2, le=3)
    discharge_staff_delta: int = Field(0, ge=-2, le=3)
    laboratory_capacity_pct: float = Field(0.0, ge=-0.30, le=0.50)
    discharge_capacity_pct: float = Field(0.0, ge=-0.30, le=0.50)


class SimulationScenario(BaseModel):
    emergency_arrival_pct: float
    walkin_arrival_pct: float
    emergency_staff_delta: int
    laboratory_staff_delta: int
    discharge_staff_delta: int
    laboratory_capacity_pct: float
    discharge_capacity_pct: float


class SimulationPath(BaseModel):
    timestamps: List[datetime]
    overall: ForecastOverall
    departments: Dict[str, ForecastDepartment]


class SimulationCurrent(BaseModel):
    overall_pressure: float
    overall_level: Level
    projected_pressure: float
    projected_level: Level


class SimulationOverallImpact(BaseModel):
    pressure_delta: float
    pressure_points: float
    projected_pressure: float
    projected_level: Level


class SimulationDepartmentImpact(BaseModel):
    name: str
    pressure_delta: float
    queue_delta: float
    wait_delta_min: float
    projected_pressure: float
    projected_level: Level


class SimulationResponse(BaseModel):
    as_of: datetime
    horizon_minutes: int
    interval_minutes: int
    timestamps: List[datetime]
    scenario: SimulationScenario
    current: SimulationCurrent
    baseline: SimulationPath
    simulated: SimulationPath
    overall_impact: SimulationOverallImpact
    department_impacts: Dict[str, SimulationDepartmentImpact]
