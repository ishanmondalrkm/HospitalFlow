import { useCallback, useMemo, useState } from 'react'
import ApiErrorNotice from '../components/ApiErrorNotice'
import { getOperationalHistory } from '../services/api'
import { useApi } from '../services/useApi'

const RANGES = [
  { hours: 24, label: '24 hours' },
  { hours: 72, label: '3 days' },
  { hours: 168, label: '7 days' },
]

const METRICS = {
  pressure: { label: 'Pressure', suffix: '', max: 100, colorVar: '--critical-bar' },
  wait: { label: 'Average wait', suffix: ' min', max: null, colorVar: '--high-bar' },
  utilization: { label: 'Utilization', suffix: '%', max: 100, colorVar: '--medium-bar' },
}

function formatTime(value, rangeHours) {
  const date = new Date(value)
  if (rangeHours > 48) return date.toLocaleDateString(undefined, { day: '2-digit', month: 'short' })
  return date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
}

function aggregate(rows, departmentId) {
  const filtered = departmentId ? rows.filter((r) => r.department_id === departmentId) : rows
  const grouped = new Map()
  for (const row of filtered) {
    const key = new Date(row.timestamp).getTime()
    if (!grouped.has(key)) grouped.set(key, [])
    grouped.get(key).push(row)
  }
  return [...grouped.entries()].sort((a, b) => a[0] - b[0]).map(([time, items]) => ({
    time,
    pressure: items.reduce((s, r) => s + Number(r.pressure || 0), 0) / items.length * 100,
    wait: items.reduce((s, r) => s + Number(r.avg_wait_min || 0), 0) / items.length,
    utilization: items.reduce((s, r) => s + Number(r.utilization || 0), 0) / items.length,
    queue: items.reduce((s, r) => s + Number(r.queue_length || 0), 0) / items.length,
  }))
}

function linePath(points, key, width, height, maxValue) {
  if (!points.length) return ''
  const values = points.map((p) => p[key])
  const max = maxValue ?? Math.max(...values, 1) * 1.08
  const min = 0
  return points.map((p, i) => {
    const x = points.length === 1 ? width / 2 : (i / (points.length - 1)) * width
    const y = height - ((p[key] - min) / Math.max(max - min, 1)) * height
    return `${i ? 'L' : 'M'} ${x.toFixed(1)} ${Math.max(0, Math.min(height, y)).toFixed(1)}`
  }).join(' ')
}

function TrendChart({ points, metric, title, rangeHours }) {
  const cfg = METRICS[metric]
  const width = 760
  const height = 210
  const values = points.map((p) => p[metric])
  const actualMax = cfg.max ?? Math.max(...values, 1) * 1.08
  const last = points.at(-1)?.[metric]
  const first = points[0]?.[metric]
  const delta = last == null || first == null ? null : last - first

  return (
    <div className="trend-card panel">
      <div className="trend-card__head">
        <div>
          <h2>{title}</h2>
          <p className="muted">Modeled operational pattern across the selected period.</p>
        </div>
        {delta !== null && (
          <div className={`trend-change ${delta >= 0 ? 'trend-change--up' : 'trend-change--down'}`}>
            {delta >= 0 ? '+' : ''}{delta.toFixed(1)}{cfg.suffix} change over period
          </div>
        )}
      </div>
      {points.length ? (
        <div className="trend-chart-wrap">
          <svg className="trend-chart" viewBox={`0 0 ${width + 60} ${height + 42}`} role="img" aria-label={`${title} chart`}>
            {[0, .25, .5, .75, 1].map((ratio) => {
              const y = height - ratio * height
              const value = actualMax * ratio
              return <g key={ratio}>
                <line x1="0" x2={width} y1={y} y2={y} className="trend-grid" />
                <text x={width + 8} y={y + 4} className="trend-axis-label">{Math.round(value)}</text>
              </g>
            })}
            <path d={linePath(points, metric, width, height, actualMax)} className="trend-line" style={{ stroke: `var(${cfg.colorVar})` }} />
            {points.length > 1 && <circle cx={width} cy={Math.max(0, Math.min(height, height - ((last - 0) / Math.max(actualMax, 1)) * height))} r="4" className="trend-dot" style={{ fill: `var(${cfg.colorVar})` }} />}
            <text x="0" y={height + 28} className="trend-axis-label">{formatTime(points[0].time, rangeHours)}</text>
            <text x={width} y={height + 28} textAnchor="end" className="trend-axis-label">{formatTime(points.at(-1).time, rangeHours)}</text>
          </svg>
        </div>
      ) : <div className="trend-empty">No historical snapshots are available for this selection.</div>}
    </div>
  )
}

export default function History() {
  const [range, setRange] = useState(24)
  const [department, setDepartment] = useState('')
  const [metric, setMetric] = useState('pressure')
  const loadHistory = useCallback(
    ({ signal }) => getOperationalHistory({ hours: range, departmentId: department, signal }),
    [range, department],
  )
  const { status, data, error, reload } = useApi(loadHistory)

  const rows = data?.snapshots ?? []
  const points = useMemo(() => aggregate(rows, department), [rows, department])
  const departments = useMemo(() => {
    const map = new Map()
    rows.forEach((r) => map.set(r.department_id, r.department_name))
    return [...map.entries()].sort((a, b) => a[1].localeCompare(b[1]))
  }, [rows])

  const latest = points.at(-1)
  const peak = points.length ? Math.max(...points.map((p) => p.pressure)) : null
  const avgWait = points.length ? points.reduce((s, p) => s + p.wait, 0) / points.length : null

  if (!data && status === 'error') return <ApiErrorNotice error={error} onRetry={reload} />
  if (!data) return <p className="loading" role="status">Loading historical operational data</p>

  return (
    <div className="page-stack history-page">
      <header className="page-heading">
        <div>
          <p className="eyebrow">Monitor · Historical view</p>
          <h1>Historical trends</h1>
          <p>See how hospital pressure, waiting time and utilization have changed over time.</p>
        </div>
        <div className="history-controls">
          <label>Department<select value={department} onChange={(e) => setDepartment(e.target.value)}><option value="">All departments</option>{departments.map(([id, name]) => <option key={id} value={id}>{name}</option>)}</select></label>
          <label>Period<select value={range} onChange={(e) => setRange(Number(e.target.value))}>{RANGES.map((r) => <option key={r.hours} value={r.hours}>{r.label}</option>)}</select></label>
        </div>
      </header>

      <section className="history-summary">
        <div className="summary-card"><span>Snapshots</span><strong>{data.count.toLocaleString()}</strong><small>MongoDB operational history</small></div>
        <div className="summary-card"><span>Current pressure</span><strong>{latest ? latest.pressure.toFixed(0) : '—'}</strong><small>out of 100</small></div>
        <div className="summary-card"><span>Peak pressure</span><strong>{peak !== null ? peak.toFixed(0) : '—'}</strong><small>selected period</small></div>
        <div className="summary-card"><span>Average wait</span><strong>{avgWait !== null ? avgWait.toFixed(1) : '—'}<em> min</em></strong><small>selected period</small></div>
      </section>

      <div className="trend-tabs" role="tablist" aria-label="Historical metric">
        {Object.entries(METRICS).map(([key, cfg]) => <button key={key} className={metric === key ? 'trend-tab trend-tab--active' : 'trend-tab'} onClick={() => setMetric(key)}>{cfg.label}</button>)}
      </div>

      <TrendChart points={points} metric={metric} title={`${METRICS[metric].label} over time`} rangeHours={range} />

      <section className="history-secondary">
        <div className="panel history-insight panel--accent">
          <p className="eyebrow">Operational context</p>
          <h2>What the history shows</h2>
          <p>{peak !== null ? `The selected period reached a peak modeled pressure of ${peak.toFixed(0)}. ` : ''}{avgWait !== null ? `Average modeled wait across the selected snapshots was ${avgWait.toFixed(1)} minutes.` : 'Historical metrics will appear as snapshots accumulate.'}</p>
          <p className="muted">Historical data is aggregate operational information. It does not contain patient-level records.</p>
        </div>
        <div className="panel history-source">
          <p className="eyebrow">Historical data</p>
          <h2>Operational history</h2>
          <p>Historical operational snapshots help track how hospital pressure, waiting time and resource utilization have changed over the selected period.</p>
          <span className="source-pill">Historical operational data</span>
        </div>
      </section>
    </div>
  )
}
