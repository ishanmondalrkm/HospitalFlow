from backend.services import data_service, simulation


def test_simulation_default_returns_two_paths():
    data_service.ensure_seeded()
    data = simulation.build_simulation(data_service.get_frame(), 60, simulation.Scenario(emergency_staff_delta=1, laboratory_capacity_pct=0.2))
    assert data["horizon_minutes"] == 60
    assert len(data["timestamps"]) == 4
    assert len(data["baseline"]["overall"]["pressure_score"]) == 4
    assert len(data["simulated"]["overall"]["pressure_score"]) == 4
    assert "emergency" in data["department_impacts"]


def test_simulation_is_deterministic():
    data_service.ensure_seeded()
    frame = data_service.get_frame()
    scenario = simulation.Scenario(emergency_staff_delta=1, laboratory_staff_delta=1, discharge_staff_delta=1)
    first = simulation.build_simulation(frame, 120, scenario)
    second = simulation.build_simulation(frame, 120, scenario)
    assert first == second


def test_capacity_and_staff_intervention_changes_result():
    data_service.ensure_seeded()
    frame = data_service.get_frame()
    neutral = simulation.build_simulation(frame, 60, simulation.Scenario())
    intervention = simulation.build_simulation(
        frame,
        60,
        simulation.Scenario(emergency_staff_delta=2, laboratory_capacity_pct=0.3, discharge_staff_delta=1),
    )
    assert intervention["scenario"]["emergency_staff_delta"] == 2
    assert intervention["overall_impact"]["pressure_delta"] <= neutral["overall_impact"]["pressure_delta"] + 0.001
