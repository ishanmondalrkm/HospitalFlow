// All network access lives here. The React components never call fetch directly,
// and none of the intelligence logic lives in the frontend: it only displays what
// the API returns.
const BASE_URL = (import.meta.env?.VITE_API_BASE_URL ?? '').replace(/\/$/, '')
const TOKEN_KEY = 'hospitalflow-access-token'

export class ApiError extends Error {
  constructor(message, { status, cause } = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.cause = cause
  }
}

async function request(path, { signal, method = 'GET', body } = {}) {
  let response
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      method,
      signal,
      headers: {
        Accept: 'application/json',
        ...(localStorage.getItem(TOKEN_KEY) ? { Authorization: `Bearer ${localStorage.getItem(TOKEN_KEY)}` } : {}),
        ...(body ? { 'Content-Type': 'application/json' } : {}),
      },
      ...(body ? { body: JSON.stringify(body) } : {}),
    })
  } catch (cause) {
    if (cause?.name === 'AbortError') throw cause
    throw new ApiError('Cannot reach the HospitalFlow API.', { cause })
  }
  if (response.status === 401) {
    window.dispatchEvent(new Event('hospitalflow-auth-expired'))
  }
  if (!response.ok) {
    let detail = ''
    try {
      detail = (await response.json()).detail
    } catch {
      // The body was not JSON; fall back to the status code below.
    }
    throw new ApiError(detail || `The API answered with status ${response.status}.`, {
      status: response.status,
    })
  }
  return response.json()
}

export const getDashboard = (options) => request('/api/dashboard', options)
export const getDepartments = (options) => request('/api/departments', options)
export const getDepartment = (id, options) => request(`/api/departments/${id}`, options)
export const getHealth = (options) => request('/api/health', options)
export const getForecast = (horizon = 120, options) => request(`/api/forecast?horizon=${horizon}`, options)
export const getBottlenecks = (options) => request('/api/bottlenecks', options)
export const runSimulation = (payload, options) => request('/api/simulation', { ...options, method: 'POST', body: payload })

export const getInsights = (horizon = 60, options) => request(`/api/insights?horizon=${horizon}`, options)

export const getAlerts = (options = {}) => {
  const { limit = 8, ...requestOptions } = options
  return request(`/api/alerts?limit=${limit}`, requestOptions)
}
export const acknowledgeAlert = (alertId, acknowledgedBy = "operator", options = {}) =>
  request(`/api/alerts/${alertId}/acknowledge`, { ...options, method: "POST", body: { acknowledged_by: acknowledgedBy } })

export const getOperationalHistory = (options = {}) => {
  const { departmentId = "", source = "", hours = 24, limit = 5000, ...requestOptions } = options
  const params = new URLSearchParams({ hours: String(hours), limit: String(limit) })
  if (departmentId) params.set("department_id", departmentId)
  if (source) params.set("source", source)
  return request(`/api/history/operational?${params.toString()}`, requestOptions)
}
