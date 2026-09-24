import math

from backend import config as cfg
from backend.services import dashboard, data_service, metrics


def _payload():
    data_service.ensure_seeded()
    return dashboard.build_dashboard(data_service.get_frame())


def _all_numbers(value):
    if isinstance(value, dict):
        for v in value.values():
            yield from _all_numbers(v)
    elif isinstance(value, (list, tuple)):
        for v in value:
            yield from _all_numbers(v)
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        yield value


def test_payload_has_the_expected_shape():
    p = _payload()
    assert [d["id"] for d in p["departments"]] == list(cfg.DEPARTMENT_IDS)
    assert [k["key"] for k in p["kpis"]] == [
        "avg_wait",
        "emergency_wait",
        "patients_in_system",
        "bed_availability",
        "staff_utilization",
        "lab_queue",
        "radiology_queue",
        "discharge_pending",
    ]
    assert all(len(k["sparkline"]) == 24 for k in p["kpis"])
    history = p["history"]
    assert len(history["timestamps"]) == len(history["overall"]) == 168
    assert set(history["departments"]) == set(cfg.DEPARTMENT_IDS)
    assert p["data_source"] == "synthetic"


def test_every_number_is_finite_so_json_is_safe():
    assert all(math.isfinite(n) for n in _all_numbers(_payload()))


def test_levels_agree_with_scores():
    p = _payload()
    for d in p["departments"]:
        assert d["level"] == metrics.level_for_score(d["pressure_score"]), d["id"]
        assert 0.0 <= d["pressure_score"] <= 1.0
        parts = d["breakdown"]
        assert all(0.0 <= v <= 1.0 for v in parts.values())
        weights = cfg.PRESSURE_WEIGHTS
        rebuilt = (
            weights["queue"] * parts["queue"]
            + weights["utilization"] * parts["utilization"]
            + weights["arrival_surge"] * parts["arrival_surge"]
            + weights["resource_constraint"] * parts["resource_constraint"]
        )
        assert abs(rebuilt - d["pressure_score"]) < 0.01, d["id"]  # the score is explainable
    assert p["hospital"]["level"] == metrics.level_for_score(p["hospital"]["overall_score"])


def test_resources_add_up():
    beds = _payload()["resources"]["beds"]
    assert beds["occupied"] + beds["available"] == beds["total"] == cfg.TOTAL_BEDS


def test_department_detail_and_unknown_department():
    data_service.ensure_seeded()
    frame = data_service.get_frame()
    detail = dashboard.build_department_detail(frame, "emergency")
    assert len(detail["history"]["timestamps"]) == 96
    assert detail["status"]["id"] == "emergency"
    assert dashboard.build_department_detail(frame, "nope") is None
