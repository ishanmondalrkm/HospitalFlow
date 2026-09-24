from fastapi import APIRouter, Depends, HTTPException

from backend.models.schemas import SimulationRequest, SimulationResponse
from backend.services import data_service, simulation
from backend.api.dependencies import require_permission

router = APIRouter(tags=["simulation"])


@router.post("/simulation", response_model=SimulationResponse, summary="Run a deterministic hospital what-if scenario")
def run_simulation(payload: SimulationRequest, user: dict = Depends(require_permission("run_simulation"))) -> dict:
    try:
        scenario = simulation.Scenario(
            emergency_arrival_pct=payload.emergency_arrival_pct,
            walkin_arrival_pct=payload.walkin_arrival_pct,
            emergency_staff_delta=payload.emergency_staff_delta,
            laboratory_staff_delta=payload.laboratory_staff_delta,
            discharge_staff_delta=payload.discharge_staff_delta,
            laboratory_capacity_pct=payload.laboratory_capacity_pct,
            discharge_capacity_pct=payload.discharge_capacity_pct,
        )
        return simulation.build_simulation(data_service.get_frame(), payload.horizon_minutes, scenario)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
