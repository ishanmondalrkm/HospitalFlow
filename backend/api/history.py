from fastapi import APIRouter, Depends, HTTPException, Query

from backend import config as cfg
from backend.models.schemas import OperationalHistoryResponse
from backend.services import history
from backend.api.dependencies import require_permission

router = APIRouter(tags=["history"])


@router.get(
    "/history/operational",
    response_model=OperationalHistoryResponse,
    summary="Recent MongoDB-backed operational history",
    description=(
        "Returns operational snapshots persisted in MongoDB. This endpoint contains "
        "aggregate hospital operations only and no patient-level information."
    ),
)
def get_operational_history(
    user: dict = Depends(require_permission("view_history")),
    department_id: str | None = Query(default=None),
    source: str | None = Query(default=None),
    hours: int = Query(default=24, ge=1, le=24 * 30),
    limit: int = Query(default=5000, ge=1, le=10000),
) -> dict:
    if department_id is not None and department_id not in cfg.DEPARTMENT_BY_ID:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown department '{department_id}'. Use one of: {', '.join(cfg.DEPARTMENT_IDS)}",
        )

    documents = history.get_history(department_id=department_id, source=source, hours=hours, limit=limit)
    return {
        "count": len(documents),
        "hours": hours,
        "department_id": department_id,
        "source": source,
        "snapshots": documents,
    }
