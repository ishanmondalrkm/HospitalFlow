from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend import config as cfg
from backend.db import mongo
from backend.api import alerts, auth as auth_api, bottlenecks, dashboard, departments, forecast, history, insights, live, live_ws as live_ws_api, simulation
from backend.models.schemas import HealthResponse
from backend.services import alerts as alert_service, auth as auth_service, data_service, history as history_service, live_feed


@asynccontextmanager
async def lifespan(app: FastAPI):
    data_service.ensure_seeded()
    data_service.get_frame()
    mongo.connect()
    if mongo.is_available():
        auth_service.ensure_indexes()
        auth_service.ensure_demo_users()
        history_service.initialize(data_service.get_frame())
        alert_service.ensure_indexes()
        if cfg.LIVE_SIMULATOR_ENABLED:
            await live_feed.manager.start()
    yield
    await live_feed.manager.stop()
    mongo.disconnect()


app = FastAPI(
    title="HospitalFlow API",
    version=cfg.API_VERSION,
    description=(
        "Operational decision support for hospital administrators: monitor, predict, explain, "
        "simulate, decide. Not a diagnosis, treatment or patient-risk system, and it holds no "
        "patient-level data."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cfg.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard.router, prefix="/api")
app.include_router(departments.router, prefix="/api")
app.include_router(forecast.router, prefix="/api")
app.include_router(bottlenecks.router, prefix="/api")
app.include_router(simulation.router, prefix="/api")
app.include_router(insights.router, prefix="/api")
app.include_router(history.router, prefix="/api")
app.include_router(live.router, prefix="/api")
app.include_router(live_ws_api.router)
app.include_router(alerts.router, prefix="/api")
app.include_router(auth_api.router, prefix="/api")


@app.get("/api/health", response_model=HealthResponse, tags=["system"])
def health() -> dict:
    frame = data_service.get_frame()
    return {
        "status": "ok",
        "version": cfg.API_VERSION,
        "data_source": cfg.DATA_SOURCE,
        "as_of": frame["timestamp"].max().to_pydatetime(),
        "rows": int(len(frame)),
        "mongodb": {
            "available": mongo.is_available(),
            "database": cfg.MONGODB_DATABASE,
        },
    }
