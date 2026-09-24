export const ROLES = { ADMIN: 'Administrator', MANAGER: 'Operations Manager', VIEWER: 'Staff / Viewer' }
const ROLE_PERMISSIONS = {
 [ROLES.ADMIN]: new Set(['view_dashboard','view_departments','view_history','view_alerts','view_live','view_forecast','view_bottlenecks','run_simulation','view_insights','control_live','acknowledge_alert','external_ingest']),
 [ROLES.MANAGER]: new Set(['view_dashboard','view_departments','view_history','view_alerts','view_live','view_forecast','view_bottlenecks','run_simulation','view_insights','control_live','acknowledge_alert']),
 [ROLES.VIEWER]: new Set(['view_dashboard','view_departments','view_history','view_alerts','view_live']),
}
export function hasPermission(user, permission) { return Boolean(user && ROLE_PERMISSIONS[user.role]?.has(permission)) }
export const ROUTE_PERMISSIONS = { '/': 'view_dashboard', '/dashboard': 'view_dashboard', '/overview': 'view_dashboard', '/flow': 'view_departments', '/history': 'view_history', '/forecast': 'view_forecast', '/bottlenecks': 'view_bottlenecks', '/simulation': 'run_simulation', '/insights': 'view_insights' }
