from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.services import live_feed
from backend.api.dependencies import require_permission

router = APIRouter(tags=["live"])


class LiveSnapshot(BaseModel):
    department_id: str
    timestamp: datetime
    arrivals: float = Field(ge=0)
    served: float = Field(ge=0)
    queue_length: float = Field(ge=0)
    staff_planned: int = Field(ge=0)
    staff_on_duty: int = Field(ge=0)
    capacity: float = Field(ge=0)
    utilization: float = Field(ge=0)
    avg_wait_min: float = Field(ge=0)
    beds_total: int | None = Field(default=None, ge=0)
    beds_occupied: float | None = Field(default=None, ge=0)


class LiveIngestRequest(BaseModel):
    source: str = Field(min_length=2, max_length=80, pattern=r"^[a-zA-Z0-9_.:-]+$")
    snapshots: list[LiveSnapshot] = Field(min_length=1, max_length=1000)


@router.get(
    "/live/status",
    summary="Live operational feed status",
    description="Shows whether the Phase 8C feed is running and its current simulated hospital time.",
)
async def get_live_status(user: dict = Depends(require_permission("view_live"))) -> dict:
    return live_feed.manager.status().__dict__


@router.post(
    "/live/start",
    summary="Start the live simulator",
)
async def start_live(user: dict = Depends(require_permission("control_live"))) -> dict:
    return (await live_feed.manager.start()).__dict__


@router.post(
    "/live/stop",
    summary="Stop the live simulator",
)
async def stop_live(user: dict = Depends(require_permission("control_live"))) -> dict:
    return (await live_feed.manager.stop()).__dict__


@router.post(
    "/live/tick",
    summary="Advance one live hospital interval",
    description="Useful for testing or demonstrations when automatic ticking is disabled.",
)
async def live_tick(user: dict = Depends(require_permission("control_live"))) -> dict:
    if not live_feed.manager.running:
        # Manual ticks are intentionally allowed without starting the background loop.
        try:
            return await live_feed.manager.tick()
        except Exception as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
    return await live_feed.manager.tick()


@router.post(
    "/live/ingest",
    summary="Ingest external aggregate hospital data",
    description=(
        "Stores aggregate operational snapshots using the same schema as the simulator. "
        "This is the adapter boundary for a future hospital API, FHIR or HL7 connector."
    ),
)
async def ingest_live(payload: LiveIngestRequest, user: dict = Depends(require_permission("external_ingest"))) -> dict:
    try:
        return await live_feed.manager.ingest(
            payload.source,
            [snapshot.model_dump() for snapshot in payload.snapshots],
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
