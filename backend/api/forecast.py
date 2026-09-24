from fastapi import APIRouter, Depends, HTTPException, Query

from backend.models.schemas import ForecastResponse
from backend.services import data_service, forecast
from backend.api.dependencies import require_permission

router = APIRouter(tags=["forecast"])

@router.get("/forecast", response_model=ForecastResponse, summary="Forecast operational pressure, queues and waits")
def get_forecast(user: dict = Depends(require_permission("view_forecast")), horizon: int = Query(120, description="Forecast horizon in minutes", enum=[30, 60, 120])) -> dict:
    try:
        return forecast.build_forecast(data_service.get_frame(), horizon)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
