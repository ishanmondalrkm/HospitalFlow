from fastapi import APIRouter, Depends

from backend.models.schemas import DashboardResponse
from backend.services import dashboard, data_service
from backend.api.dependencies import require_permission

router = APIRouter(tags=["dashboard"])


@router.get(
    "/dashboard",
    response_model=DashboardResponse,
    summary="Current operational picture",
    description=(
        "Hospital status, KPIs, per-department pressure, resources and a week of pressure "
        "history. Operational data only: no patient-level records."
    ),
)
def get_dashboard(user: dict = Depends(require_permission("view_dashboard"))) -> dict:
    return dashboard.build_dashboard(data_service.get_frame())
