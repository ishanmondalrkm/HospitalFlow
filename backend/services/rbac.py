"""Role-based access control for HospitalFlow Phase 9B."""
ROLE_ADMIN = "Administrator"
ROLE_MANAGER = "Operations Manager"
ROLE_VIEWER = "Staff / Viewer"
PERMISSIONS = {
 ROLE_ADMIN: {"view_dashboard","view_departments","view_history","view_alerts","view_live","view_forecast","view_bottlenecks","run_simulation","view_insights","control_live","acknowledge_alert","external_ingest"},
 ROLE_MANAGER: {"view_dashboard","view_departments","view_history","view_alerts","view_live","view_forecast","view_bottlenecks","run_simulation","view_insights","control_live","acknowledge_alert"},
 ROLE_VIEWER: {"view_dashboard","view_departments","view_history","view_alerts","view_live"},
}
def has_permission(user: dict, permission: str) -> bool:
 return permission in PERMISSIONS.get(user.get("role"), set())
