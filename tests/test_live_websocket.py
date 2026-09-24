from backend.main import app


def test_live_websocket_route_registered():
    routes = {getattr(route, "path", None) for route in app.routes}
    assert "/ws/live" in routes
