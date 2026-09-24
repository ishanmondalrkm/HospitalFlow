import random
from datetime import datetime

from backend import config as cfg
from backend.services import hospital_model as model

TUESDAY_10 = datetime(2026, 9, 15, 10, 0)


def _run(steps=8, emergency_mult=1.0, extra_er_staff=0, state=None):
    state = state or model.initial_state()
    last = None
    for _ in range(steps):
        inp = model.demand_inputs(TUESDAY_10)
        inp.emergency *= emergency_mult
        inp.staff["emergency"] += extra_er_staff
        state, last = model.step(state, inp)  # no rng: expected-value mode
    return state, last


def test_poisson_sampler_has_the_right_mean_and_is_repeatable():
    rng = random.Random(1)
    samples = [model.poisson(rng, 4.0) for _ in range(5000)]
    assert abs(sum(samples) / len(samples) - 4.0) < 0.15
    rng_big = random.Random(2)
    big = [model.poisson(rng_big, 55.0) for _ in range(400)]
    assert abs(sum(big) / len(big) - 55.0) < 1.5
    assert model.poisson(random.Random(3), 0.0) == 0


def test_expected_value_mode_is_deterministic():
    _, a = _run()
    _, b = _run()
    assert a == b


def test_emergency_surge_raises_waits_and_downstream_load():
    _, base = _run(steps=8)
    _, surge = _run(steps=8, emergency_mult=1.4)
    assert surge["emergency"]["avg_wait_min"] > base["emergency"]["avg_wait_min"]
    assert surge["laboratory"]["arrivals"] > base["laboratory"]["arrivals"]  # pressure propagates


def test_extra_staff_shortens_the_emergency_wait():
    _, surge = _run(steps=8, emergency_mult=1.4)
    _, helped = _run(steps=8, emergency_mult=1.4, extra_er_staff=2)
    assert helped["emergency"]["avg_wait_min"] < surge["emergency"]["avg_wait_min"]


def test_full_beds_block_emergency_treatment_space():
    normal = model.initial_state()
    full = model.initial_state()
    full.occupied_beds = cfg.TOTAL_BEDS * cfg.USABLE_BED_FRACTION
    full.queues["beds"] = 10.0
    inp = model.demand_inputs(TUESDAY_10)
    _, normal_rows = model.step(normal, inp)
    _, full_rows = model.step(full, inp)
    assert full_rows["emergency"]["capacity"] < normal_rows["emergency"]["capacity"]
    assert full_rows["beds"]["queue_length"] > 0  # boarding: admitted patients wait for a bed


def test_slow_laboratory_slows_discharge_decisions():
    fast = model.initial_state()
    slow = model.initial_state()
    slow.lab_delay = 1.0
    inp = model.demand_inputs(TUESDAY_10)
    _, fast_rows = model.step(fast, inp)
    _, slow_rows = model.step(slow, inp)
    assert slow_rows["discharge"]["arrivals"] < fast_rows["discharge"]["arrivals"]


def test_incidents_change_capacity_and_staffing():
    incident = cfg.Incident("test", 0, 0, 1, capacity={"laboratory": 0.5}, staff_loss={"emergency": 3})
    plain = model.demand_inputs(TUESDAY_10)
    hit = model.demand_inputs(TUESDAY_10, [incident])
    assert hit.capacity["laboratory"] == 0.5 * plain.capacity["laboratory"]
    assert hit.staff["emergency"] == plain.staff["emergency"] - 3
    assert hit.staff_planned["emergency"] == plain.staff_planned["emergency"]
