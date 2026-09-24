"""Explainable bottleneck intelligence built from the same pressure model as the monitor."""
from __future__ import annotations

import pandas as pd

from backend import config as cfg
from backend.services import dashboard, metrics

COMPONENT_LABELS = {
    "queue": "Queue pressure",
    "utilization": "Utilization",
    "arrival_surge": "Arrival surge",
    "resource_constraint": "Resource constraint",
}


def _reason(component: str, row: pd.Series) -> str:
    if component == "queue":
        return f"Average wait is {float(row['avg_wait_min']):.0f} min against a {cfg.DEPARTMENT_BY_ID[row.name].base_wait:.0f}-min baseline."
    if component == "utilization":
        return f"One-hour load is {float(row['load_1h']) * 100:.0f}% of capacity."
    if component == "arrival_surge":
        return f"Recent arrivals are running above the model's typical level for this time window."
    if row.name == "beds":
        return f"{float(row['pending_discharges']):.0f} beds' worth of discharge work is holding capacity in the model."
    planned = max(float(row["staff_planned"]), 1.0)
    shortfall = max(0.0, (planned - float(row["staff_on_duty"])) / planned)
    return f"Staffing is {shortfall * 100:.0f}% below planned coverage."


def _contributor_rows(row: pd.Series) -> list[dict]:
    weights = cfg.PRESSURE_WEIGHTS
    values = {
        "queue": float(row["c_queue"]),
        "utilization": float(row["c_util"]),
        "arrival_surge": float(row["c_surge"]),
        "resource_constraint": float(row["c_resource"]),
    }
    total = max(float(row["pressure"]), 1e-9)
    parts = []
    for key, value in values.items():
        contribution = value * float(weights[key])
        parts.append(
            {
                "key": key,
                "label": COMPONENT_LABELS[key],
                "value": round(value, 3),
                "weight": round(float(weights[key]), 3),
                "contribution": round(contribution, 3),
                "share": round(contribution / total, 3),
                "reason": _reason(key, row),
            }
        )
    return sorted(parts, key=lambda item: item["contribution"], reverse=True)


def _headline(bottleneck: dict, high_count: int) -> str:
    if bottleneck["level"] in ("HIGH", "CRITICAL"):
        top = bottleneck["contributors"][0]
        return f"{bottleneck['name']} is the leading pressure point; {top['label'].lower()} is its largest modeled contributor."
    if high_count:
        return f"{high_count} department{'s' if high_count != 1 else ''} are at medium pressure or above; the largest pressure signal is {bottleneck['name']}."
    return f"No department is at high pressure. {bottleneck['name']} has the highest modeled pressure."


def build_bottlenecks(df: pd.DataFrame) -> dict:
    now, latest, earlier = dashboard._snapshot(df)
    statuses = []
    for dept in cfg.DEPARTMENTS:
        row = latest.loc[dept.id]
        contributors = _contributor_rows(row)
        statuses.append(
            {
                "id": dept.id,
                "name": dept.name,
                "kind": dept.kind,
                "pressure_score": round(float(row["pressure"]), 3),
                "level": str(row["level"]),
                "queue_length": int(round(float(row["queue_length"]))),
                "avg_wait_min": round(float(row["avg_wait_min"]), 1),
                "utilization": round(float(row["load_1h"]), 3),
                "pressure_delta_1h": round(float(row["pressure"] - earlier.loc[dept.id, "pressure"]), 3),
                "contributors": contributors,
            }
        )

    by_id = {item["id"]: item for item in statuses}
    # These are the configured downstream routes, scored by source pressure and
    # routing intensity. They describe modeled propagation, not patient-level causality.
    propagation = []
    for (source_id, target_id), routing_factor in cfg.ROUTING.items():
        source = by_id[source_id]
        target = by_id[target_id]
        propagation_score = source["pressure_score"] * float(routing_factor)
        if propagation_score <= 0.03:
            continue
        propagation.append(
            {
                "source_id": source_id,
                "source_name": source["name"],
                "source_level": source["level"],
                "target_id": target_id,
                "target_name": target["name"],
                "target_level": target["level"],
                "routing_factor": round(float(routing_factor), 3),
                "propagation_score": round(propagation_score, 3),
                "signal": f"{source['name']} work is routed into {target['name']} at {routing_factor:.0%} of upstream work in the model.",
            }
        )
    propagation.sort(key=lambda item: item["propagation_score"], reverse=True)

    leading = max(statuses, key=lambda item: item["pressure_score"])
    high_or_critical = sum(1 for item in statuses if item["level"] in ("HIGH", "CRITICAL"))
    medium_or_above = sum(1 for item in statuses if item["level"] in ("MEDIUM", "HIGH", "CRITICAL"))

    # A compact chain starting at the leading pressure point, following the
    # strongest configured downstream route at each hop.
    chain = []
    current = leading["id"]
    visited = set()
    for _ in range(4):
        if current in visited:
            break
        visited.add(current)
        current_item = by_id[current]
        chain.append({"id": current, "name": current_item["name"], "level": current_item["level"], "pressure_score": current_item["pressure_score"]})
        candidates = [
            item for item in propagation
            if item["source_id"] == current and item["target_id"] not in visited
        ]
        if not candidates:
            break
        current = max(candidates, key=lambda item: item["propagation_score"])["target_id"]

    return {
        "as_of": now.to_pydatetime(),
        "headline": _headline(leading, medium_or_above),
        "leading_department_id": leading["id"],
        "departments": statuses,
        "propagation": propagation,
        "chain": chain,
        "summary": {
            "high_or_critical": high_or_critical,
            "medium_or_above": medium_or_above,
        },
        "weights": dict(cfg.PRESSURE_WEIGHTS),
    }
