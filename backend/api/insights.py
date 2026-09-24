from fastapi import APIRouter, Depends, Query

from backend.services import data_service, insights
from backend.api.dependencies import require_permission

router = APIRouter(prefix="/insights", tags=["decide"])


@router.get("")
def get_insights(user: dict = Depends(require_permission("view_insights")), horizon: int = Query(60, enum=[30, 60, 120])) -> dict:
    return insights.build_insights(data_service.get_frame(), int(horizon))
