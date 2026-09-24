from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.services import alerts
from backend.api.dependencies import require_permission

router = APIRouter(tags=["alerts"])


class AcknowledgeRequest(BaseModel):
    acknowledged_by: str = Field(default="operator", min_length=1, max_length=80)


@router.get("/alerts", summary="List operational alerts")
async def list_alerts(
    user: dict = Depends(require_permission("view_alerts")),
    status: str | None = Query(default=None),
    department_id: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict:
    items = alerts.list_alerts(status=status, department_id=department_id, severity=severity, limit=limit)
    return {"count": len(items), "alerts": items}


@router.post("/alerts/{alert_id}/acknowledge", summary="Acknowledge an operational alert")
async def acknowledge_alert(alert_id: str, payload: AcknowledgeRequest, user: dict = Depends(require_permission("acknowledge_alert"))) -> dict:
    if not alerts.acknowledge(alert_id, payload.acknowledged_by):
        raise HTTPException(status_code=404, detail="Open alert not found")
    return {"status": "ACKNOWLEDGED", "alert_id": alert_id}
