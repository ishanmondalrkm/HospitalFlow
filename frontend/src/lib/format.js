export const LEVEL_LABEL = { LOW: 'Low', MEDIUM: 'Medium', HIGH: 'High', CRITICAL: 'Critical' }

// Same rule as the backend (`metrics.level_for_score`); thresholds come from the API.
export function levelForScore(score, thresholds) {
  if (score >= thresholds.critical) return 'CRITICAL'
  if (score >= thresholds.high) return 'HIGH'
  if (score >= thresholds.medium) return 'MEDIUM'
  return 'LOW'
}

// Scores are 0..1 in the API and shown as points out of 100.
export const toPoints = (score) => Math.round(score * 100)

const pad = (n) => String(n).padStart(2, '0')
export const clockTime = (date) => `${pad(date.getHours())}:${pad(date.getMinutes())}`

// The API sends hospital-local times without a zone (e.g. 2026-09-15T10:00:00);
// browsers read that as local time, so the clock shown matches the hospital's.
const longDay = new Intl.DateTimeFormat('en-GB', { weekday: 'long', day: 'numeric', month: 'long' })
const shortDay = new Intl.DateTimeFormat('en-GB', { weekday: 'short', day: 'numeric', month: 'short' })

export const formatDateTime = (iso) => {
  const date = new Date(iso)
  return `${longDay.format(date)}, ${clockTime(date)}`
}
export const formatShortDateTime = (iso) => {
  const date = new Date(iso)
  return `${shortDay.format(date)}, ${clockTime(date)}`
}

const digitsFor = (unit) => (unit === '%' ? 1 : 0)

export const formatValue = (value, unit) => value.toFixed(digitsFor(unit))

export function formatDelta(delta, unit) {
  const digits = digitsFor(unit)
  const rounded = Number(delta.toFixed(digits))
  if (rounded === 0) return 'No change in the last hour'
  const sign = rounded > 0 ? '+' : '\u2212'
  const suffix = unit === 'min' ? ' min' : unit === '%' ? ' points' : ''
  return `${sign}${Math.abs(rounded).toFixed(digits)}${suffix} in the last hour`
}

// 'bad' when the change is in the unwelcome direction, 'good' when welcome, 'flat' when none.
export function deltaTone(delta, unit, higherIsWorse) {
  const rounded = Number(delta.toFixed(digitsFor(unit)))
  if (rounded === 0) return 'flat'
  return rounded > 0 === higherIsWorse ? 'bad' : 'good'
}

const weekdayDay = new Intl.DateTimeFormat('en-GB', { weekday: 'short', day: 'numeric' })
export const formatWeekdayDay = (date) => weekdayDay.format(date)
export const formatHour = (date) => `${pad(date.getHours())}:00`
