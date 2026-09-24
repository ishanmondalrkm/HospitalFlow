from fastapi import APIRouter, Depends

from backend.models.schemas import BottleneckResponse
from backend.services import bottlenecks, data_service
from backend.api.dependencies import require_permission

router = APIRouter(tags=["explain"])


@router.get(
    "/bottlenecks",
    response_model=BottleneckResponse,
    summary="Explain current operational bottlenecks and modeled propagation",
)
def get_bottlenecks(user: dict = Depends(require_permission("view_bottlenecks"))) -> dict:
    return bottlenecks.build_bottlenecks(data_service.get_frame())
