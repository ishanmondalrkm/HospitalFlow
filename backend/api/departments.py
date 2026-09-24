from typing import List

from fastapi import APIRouter, Depends, HTTPException

from backend import config as cfg
from backend.models.schemas import DepartmentDetail, DepartmentInfo
from backend.services import dashboard, data_service
from backend.api.dependencies import require_permission

router = APIRouter(tags=["departments"])


@router.get(
    "/departments",
    response_model=List[DepartmentInfo],
    summary="All departments with their current status",
)
def list_departments(user: dict = Depends(require_permission("view_departments"))) -> list:
    return dashboard.build_departments(data_service.get_frame())


@router.get(
    "/departments/{department_id}",
    response_model=DepartmentDetail,
    summary="One department with its last 24 hours",
)
def get_department(department_id: str, user: dict = Depends(require_permission("view_departments"))) -> dict:
    detail = dashboard.build_department_detail(data_service.get_frame(), department_id)
    if detail is None:
        known = ", ".join(cfg.DEPARTMENT_IDS)
        raise HTTPException(
            status_code=404,
            detail=f"Unknown department '{department_id}'. Use one of: {known}.",
        )
    return detail
