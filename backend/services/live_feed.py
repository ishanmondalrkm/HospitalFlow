"""Live operational data ingestion for HospitalFlow.

Phase 8C adds a small live-feed layer without replacing the existing deterministic
model used by the dashboard.  The default feed is a synthetic simulator that
advances the hospital by one 15-minute operational interval every few seconds.
The same service also exposes a generic ingestion path for future hospital/API
adapters.

No patient-level data is accepted or stored here: snapshots are aggregate
operational metrics only.
"""
from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import pandas as pd

from backend import config as cfg
from backend.services import alerts, data_generator, data_service, hospital_model as model, history, metrics, live_ws

logger = logging.getLogger("hospitalflow.live")


@dataclass
class LiveStatus:
    running: bool
    source: str
    simulation_time: datetime | None
    last_tick_at: datetime | None
    ticks: int
    last_inserted: int


class LiveFeedManager:
    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._state: model.State | None = None
        self._simulation_time: datetime | None = None
        self._rng = random.Random(cfg.SEED + 100_000)
        self._ticks = 0
        self._last_tick_at: datetime | None = None
        self._last_inserted = 0
        self._lock = asyncio.Lock()
        self._live_rows: list[dict[str, Any]] = []

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    def status(self) -> LiveStatus:
        return LiveStatus(
            running=self.running,
            source="live_simulator",
            simulation_time=self._simulation_time,
            last_tick_at=self._last_tick_at,
            ticks=self._ticks,
            last_inserted=self._last_inserted,
        )

    def _bootstrap(self) -> None:
        """Start the simulator from the latest model state in the existing history."""
        frame = data_service.get_frame()
        latest_time = frame["timestamp"].max()
        latest = frame[frame["timestamp"] == latest_time].set_index("department_id")
        queues = {sid: float(latest.loc[sid, "queue_length"]) for sid in cfg.STATION_IDS}
        queues["beds"] = float(latest.loc["beds", "queue_length"])
        lab = cfg.DEPARTMENT_BY_ID["laboratory"]
        lab_delay = (float(latest.loc["laboratory", "avg_wait_min"]) - lab.base_wait) / (
            lab.critical_wait - lab.base_wait
        )
        self._state = model.State(
            queues=queues,
            occupied_beds=float(latest.loc["beds", "beds_occupied"]),
            lab_delay=max(0.0, min(1.0, lab_delay)),
        )
        self._simulation_time = latest_time.to_pydatetime()
        self._live_rows = []

    async def start(self) -> LiveStatus:
        async with self._lock:
            if self.running:
                return self.status()
            self._bootstrap()
            self._task = asyncio.create_task(self._run(), name="hospitalflow-live-feed")
            logger.info("Live simulator started at %s", self._simulation_time)
            await live_ws.manager.broadcast({"type": "live_status", "status": self.status().__dict__})
            return self.status()

    async def stop(self) -> LiveStatus:
        async with self._lock:
            task = self._task
            self._task = None
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        logger.info("Live simulator stopped")
        await live_ws.manager.broadcast({"type": "live_status", "status": self.status().__dict__})
        return self.status()

    async def _run(self) -> None:
        while True:
            try:
                await asyncio.sleep(cfg.LIVE_INTERVAL_SECONDS)
                await self.tick()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Live simulator tick failed")

    async def tick(self) -> dict[str, Any]:
        async with self._lock:
            if self._state is None or self._simulation_time is None:
                self._bootstrap()

            assert self._state is not None
            assert self._simulation_time is not None

            forecast_end = self._simulation_time + timedelta(minutes=cfg.LIVE_HOSPITAL_INTERVAL_MIN)
            t_start = forecast_end - timedelta(minutes=cfg.INTERVAL_MIN)
            incidents = data_generator.incident_windows(forecast_end)
            active = [inc for start, end, inc in incidents if start <= t_start < end]
            inputs = model.demand_inputs(t_start, active)
            self._state, raw = model.step(self._state, inputs, rng=self._rng)

            rows = []
            for dept in cfg.DEPARTMENTS:
                rows.append({
                    "department_id": dept.id,
                    "timestamp": forecast_end,
                    **raw[dept.id],
                })
            raw_frame = pd.DataFrame(rows)
            raw_frame["timestamp"] = pd.to_datetime(raw_frame["timestamp"])

            # Keep enough recent live points for the rolling pressure calculation,
            # while the 14-day synthetic history remains the baseline for typical
            # time-of-day arrivals.
            self._live_rows.extend(raw_frame.to_dict("records"))
            keep_after = forecast_end - timedelta(days=2)
            self._live_rows = [r for r in self._live_rows if r["timestamp"] >= keep_after]

            base = data_service.load_metrics()
            live_frame = pd.DataFrame(self._live_rows)
            combined = pd.concat([base, live_frame], ignore_index=True)
            enriched = metrics.enrich(combined)
            current = enriched[enriched["timestamp"] == forecast_end].copy()
            inserted = history.save_snapshot(current, source="live_simulator")
            created_alerts = alerts.evaluate(current)

            self._simulation_time = forecast_end
            self._last_tick_at = datetime.now().astimezone()
            self._ticks += 1
            self._last_inserted = inserted

            overall = metrics.overall_pressure(metrics.wide(enriched, "pressure")).loc[forecast_end]
            result = {
                "source": "live_simulator",
                "timestamp": forecast_end,
                "inserted": inserted,
                "alerts_created": len(created_alerts),
                "overall_pressure": round(float(overall), 3),
                "departments": [
                    {
                        "id": str(row.department_id),
                        "name": cfg.DEPARTMENT_BY_ID[str(row.department_id)].name,
                        "pressure": round(float(row.pressure), 3),
                        "level": str(row.level),
                        "queue_length": round(float(row.queue_length), 2),
                        "avg_wait_min": round(float(row.avg_wait_min), 1),
                    }
                    for row in current.itertuples()
                ],
            }
            await live_ws.manager.broadcast({"type": "live_tick", "data": result})
            return result

    async def ingest(self, source: str, snapshots: list[dict[str, Any]]) -> dict[str, Any]:
        """Persist externally supplied aggregate snapshots.

        This is intentionally schema-compatible with the simulator output so a
        future FHIR/HL7/hospital API adapter can call the same path.
        """
        if not snapshots:
            return {"source": source, "inserted": 0, "snapshots": 0}
        frame = pd.DataFrame(snapshots)
        required = {"department_id", "timestamp", "arrivals", "served", "queue_length", "staff_planned", "staff_on_duty", "capacity", "utilization", "avg_wait_min"}
        missing = required - set(frame.columns)
        if missing:
            raise ValueError(f"Missing required operational fields: {', '.join(sorted(missing))}")
        unknown = set(frame["department_id"].astype(str)) - set(cfg.DEPARTMENT_IDS)
        if unknown:
            raise ValueError(f"Unknown department_id values: {', '.join(sorted(unknown))}")
        frame["department_id"] = frame["department_id"].astype(str)
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True).dt.tz_localize(None)
        frame["beds_total"] = frame.get("beds_total", pd.Series([None] * len(frame)))
        frame["beds_occupied"] = frame.get("beds_occupied", pd.Series([None] * len(frame)))
        base = data_service.load_metrics()
        combined = pd.concat([base, frame], ignore_index=True)
        # If an external feed supplies the same department/timestamp as the
        # synthetic baseline, the external observation wins for this scoring run.
        combined = combined.drop_duplicates(["department_id", "timestamp"], keep="last")
        enriched = metrics.enrich(combined)
        keys = set(zip(frame["department_id"].astype(str), frame["timestamp"]))
        current = enriched[
            enriched.apply(lambda row: (str(row["department_id"]), row["timestamp"]) in keys, axis=1)
        ].copy()
        inserted = history.save_snapshots(current, source=source)
        return {"source": source, "inserted": inserted, "snapshots": len(frame)}


manager = LiveFeedManager()
