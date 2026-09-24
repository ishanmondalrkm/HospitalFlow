"""Decision-support options built from the same hospital model used by forecast and simulation."""
from __future__ import annotations

import pandas as pd

from backend import config as cfg
from backend.services import bottlenecks, simulation


ACTIONS = [
    {
        "id": "emergency-coverage",
        "title": "Add emergency coverage",
        "description": "Increase emergency staffing for the next hour.",
        "scenario": {"emergency_staff_delta": 2},
        "tradeoff": "Uses additional emergency staffing capacity.",
        "when": "Useful when Emergency is a leading pressure point or queue pressure is prominent.",
    },
    {
        "id": "lab-capacity",
        "title": "Increase laboratory capacity",
        "description": "Increase laboratory processing capacity for the next hour.",
        "scenario": {"laboratory_capacity_pct": 0.30},
        "tradeoff": "Requires additional laboratory processing capacity.",
        "when": "Useful when laboratory pressure or downstream diagnostic work is elevated.",
    },
    {
        "id": "discharge-throughput",
        "title": "Accelerate discharge",
        "description": "Add discharge coverage and processing capacity for the next hour.",
        "scenario": {"discharge_staff_delta": 2, "discharge_capacity_pct": 0.20},
        "tradeoff": "Uses additional discharge coverage and throughput capacity.",
        "when": "Useful when beds or discharge pressure are constraining downstream flow.",
    },
    {
        "id": "demand-reduction",
        "title": "Reduce emergency demand",
        "description": "Model a temporary 10% reduction in emergency arrivals.",
        "scenario": {"emergency_arrival_pct": -0.10},
        "tradeoff": "Represents a demand-side change rather than adding operational capacity.",
        "when": "Useful for testing how sensitive the network is to incoming emergency volume.",
    },
]


def _scenario_payload(changes: dict) -> simulation.Scenario:
    return simulation.Scenario(**changes)


def _fit_reason(action: dict, leading: dict, contributors: list[dict]) -> str:
    top = contributors[0]["key"] if contributors else ""
    if leading["id"] == "emergency" and action["id"] == "emergency-coverage":
        return "Directly addresses the leading Emergency pressure point."
    if leading["id"] == "laboratory" and action["id"] == "lab-capacity":
        return "Directly addresses laboratory processing capacity."
    if leading["id"] in ("beds", "discharge") and action["id"] == "discharge-throughput":
        return "Directly tests additional discharge throughput against the current bed/discharge constraint."
    if top == "queue" and action["id"] in ("emergency-coverage", "discharge-throughput"):
        return "Tests additional operational capacity against the current queue signal."
    if top == "utilization" and action["id"] == "lab-capacity":
        return "Tests whether added processing capacity relieves the current load signal."
    return "Provides a counterfactual comparison using the connected hospital model."


def build_insights(df: pd.DataFrame, horizon_minutes: int = 60) -> dict:
    bottle = bottlenecks.build_bottlenecks(df)
    leading = next(item for item in bottle["departments"] if item["id"] == bottle["leading_department_id"])
    contributors = leading["contributors"]

    options = []
    for action in ACTIONS:
        result = simulation.build_simulation(df, horizon_minutes, _scenario_payload(action["scenario"]))
        impact = result["overall_impact"]
        options.append(
            {
                "id": action["id"],
                "title": action["title"],
                "description": action["description"],
                "scenario": result["scenario"],
                "pressure_delta": impact["pressure_delta"],
                "pressure_points": impact["pressure_points"],
                "projected_pressure": impact["projected_pressure"],
                "projected_level": impact["projected_level"],
                "tradeoff": action["tradeoff"],
                "when": action["when"],
                "fit_reason": _fit_reason(action, leading, contributors),
                "department_impacts": result["department_impacts"],
            }
        )

    reductions = [o for o in options if o["pressure_delta"] < 0]
    if reductions:
        strongest = min(reductions, key=lambda item: item["pressure_delta"])
        headline = (
            f"{strongest['title']} has the largest modeled pressure reduction among the tested options "
            f"over {horizon_minutes} minutes."
        )
        headline_note = "This is a model comparison, not an automatic instruction to act."
    else:
        headline = f"The tested options do not reduce projected hospital pressure over {horizon_minutes} minutes."
        headline_note = "Use the scenario details and department impacts to inspect the trade-offs."

    return {
        "as_of": bottle["as_of"],
        "horizon_minutes": horizon_minutes,
        "headline": headline,
        "headline_note": headline_note,
        "leading_department_id": leading["id"],
        "leading_department_name": leading["name"],
        "leading_pressure": leading["pressure_score"],
        "leading_level": leading["level"],
        "leading_contributor": contributors[0] if contributors else None,
        "options": options,
    }
