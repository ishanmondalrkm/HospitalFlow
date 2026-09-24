from backend.services import data_service, forecast


def test_forecast_is_deterministic_and_has_requested_points():
    data_service.ensure_seeded()
    frame = data_service.get_frame()
    first = forecast.build_forecast(frame, 60)
    second = forecast.build_forecast(frame, 60)
    assert first == second
    assert len(first["timestamps"]) == 4
    assert len(first["overall"]["pressure_score"]) == 4
    assert set(first["departments"]) == set(frame["department_id"].unique())


def test_forecast_contains_queue_wait_and_pressure_series():
    data_service.ensure_seeded()
    result = forecast.build_forecast(data_service.get_frame(), 120)
    assert len(result["timestamps"]) == 8
    for department in result["departments"].values():
        assert len(department["pressure_score"]) == 8
        assert len(department["queue_length"]) == 8
        assert len(department["avg_wait_min"]) == 8
        assert all(0 <= value <= 1 for value in department["pressure_score"])
