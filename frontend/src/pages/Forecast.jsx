import { useCallback, useMemo, useState } from 'react'
import ApiErrorNotice from '../components/ApiErrorNotice'
import LevelBadge from '../components/LevelBadge'
import { getForecast } from '../services/api'
import { useApi } from '../services/useApi'
import { formatShortDateTime, toPoints } from '../lib/format'

const WIDTH = 900
const HEIGHT = 300
const MARGIN = { top: 18, right: 18, bottom: 38, left: 46 }
const HORIZONS = [30, 60, 120]

function ForecastChart({ data, seriesId }) {
  const series = seriesId === 'overall' ? data.overall : data.departments[seriesId]
  const values = series?.pressure_score ?? []
  if (!values.length) return null

  const plotW = WIDTH - MARGIN.left - MARGIN.right
  const plotH = HEIGHT - MARGIN.top - MARGIN.bottom
  const x = (i) => MARGIN.left + (values.length === 1 ? 0 : (i / (values.length - 1)) * plotW)
  const y = (v) => MARGIN.top + (1 - Math.max(0, Math.min(1, v))) * plotH
  const path = values.map((v, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ')
  const thresholds = { medium: 0.35, high: 0.55, critical: 0.75 }
  const zones = [
    { key: 'low', from: 0, to: thresholds.medium },
    { key: 'medium', from: thresholds.medium, to: thresholds.high },
    { key: 'high', from: thresholds.high, to: thresholds.critical },
    { key: 'critical', from: thresholds.critical, to: 1 },
  ]

  return (
    <div className="chart-wrap">
      <svg className="chart" viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label="Forecast pressure chart">
        {zones.map((zone) => (
          <rect key={zone.key} className={`chart__zone chart__zone--${zone.key}`} x={MARGIN.left} y={y(zone.to)} width={plotW} height={y(zone.from) - y(zone.to)} />
        ))}
        {[0.35, 0.55, 0.75].map((t) => (
          <line key={t} className="chart__grid" x1={MARGIN.left} x2={MARGIN.left + plotW} y1={y(t)} y2={y(t)} />
        ))}
        {[0, 0.35, 0.55, 0.75, 1].map((t) => (
          <text key={t} className="chart__axis-label" x={MARGIN.left - 8} y={y(t) + 4} textAnchor="end">{toPoints(t)}</text>
        ))}
        <path className="chart__line" d={path} />
        {values.map((value, index) => (
          <circle key={index} className="chart__point" cx={x(index)} cy={y(value)} r="4" />
        ))}
        {data.timestamps.map((stamp, index) => (
          <text key={stamp} className="chart__axis-label" x={x(index)} y={HEIGHT - 10} textAnchor="middle">
            {new Date(stamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </text>
        ))}
      </svg>
    </div>
  )
}

export default function Forecast() {
  const [horizon, setHorizon] = useState(60)
  const [seriesId, setSeriesId] = useState('overall')
  const loader = useCallback((options) => getForecast(horizon, options), [horizon])
  const { status, data, error, reload } = useApi(loader)

  const leading = useMemo(() => {
    if (!data) return null
    const dept = data.departments[data.leading_department_id]
    return dept ?? null
  }, [data])

  if (!data && status === 'error') return <ApiErrorNotice error={error} onRetry={reload} />
  if (!data) return <p className="loading" role="status">Building operational forecast</p>

  const selected = seriesId === 'overall' ? data.overall : data.departments[seriesId]
  const first = selected.pressure_score[0]
  const last = selected.pressure_score[selected.pressure_score.length - 1]
  const selectedName = seriesId === 'overall' ? 'Hospital overall' : data.departments[seriesId]?.name

  return (
    <section className="forecast-page" aria-labelledby="forecast-title">
      <div className="flow-page__intro">
        <div>
          <p className="eyebrow">PREDICT / FORECAST</p>
          <h1 id="forecast-title">Forecast</h1>
          <p className="flow-page__subtitle">
            Project queues, waiting times and pressure forward from the latest hospital state using the same connected model as the monitor.
          </p>
        </div>
        <button className="button" type="button" onClick={reload} disabled={status === 'loading'}>
          {status === 'loading' ? 'Refreshing…' : 'Refresh'}
        </button>
      </div>

      {error && data && <p className="refresh-note" role="status">Showing the last successful forecast. Refresh failed.</p>}

      <section className="panel forecast-summary panel--accent" aria-labelledby="forecast-summary-title">
        <div>
          <p className="eyebrow">PROJECTED OUTLOOK</p>
          <h2 id="forecast-summary-title">{data.headline}</h2>
          <p className="panel__note">Forecast starts after {formatShortDateTime(data.as_of)} and advances in {data.interval_minutes}-minute intervals.</p>
        </div>
        {leading && (
          <div className="forecast-summary__metric">
            <span>Largest projected pressure change</span>
            <strong>{leading.name}</strong>
            <span>{leading.pressure_score[0] * 100 > 0 ? `${(leading.pressure_score[0] * 100).toFixed(0)} → ${(leading.pressure_score.at(-1) * 100).toFixed(0)}` : `${(leading.pressure_score.at(-1) * 100).toFixed(0)}`} points</span>
          </div>
        )}
      </section>

      <div className="forecast-controls panel">
        <div className="history__controls">
          <label className="select">
            <span className="visually-hidden">Forecast department</span>
            <select value={seriesId} onChange={(event) => setSeriesId(event.target.value)}>
              <option value="overall">Hospital overall</option>
              {Object.values(data.departments).map((dept) => <option key={dept.id} value={dept.id}>{dept.name}</option>)}
            </select>
          </label>
          <div className="segmented" role="group" aria-label="Forecast horizon">
            {HORIZONS.map((minutes) => (
              <button key={minutes} type="button" aria-pressed={minutes === horizon} onClick={() => setHorizon(minutes)}>
                {minutes} min
              </button>
            ))}
          </div>
        </div>
      </div>

      <section className="panel history" aria-labelledby="forecast-chart-title">
        <div className="panel__head">
          <h2 id="forecast-chart-title">Projected pressure</h2>
          <p className="panel__note">{selectedName} · future pressure score, with the same Low / Medium / High / Critical thresholds used by the monitor.</p>
        </div>
        <div className="history__readout num">
          <span>First forecast point</span>
          <strong>{toPoints(first)} → {toPoints(last)} of 100</strong>
          <LevelBadge level={selected.level.at(-1)} />
        </div>
        <ForecastChart data={data} seriesId={seriesId} />
      </section>

      <section className="panel" aria-labelledby="department-forecast-title">
        <div className="panel__head">
          <h2 id="department-forecast-title">Department outlook</h2>
          <p className="panel__note">The final forecast point shows the projected queue and waiting time at the selected horizon.</p>
        </div>
        <div className="forecast-table-wrap">
          <table className="dept-table">
            <thead><tr><th>Department</th><th>Current pressure</th><th>Projected pressure</th><th>Queue</th><th>Wait</th><th>Level</th></tr></thead>
            <tbody>
              {Object.values(data.departments).map((dept) => {
                const base = data.baseline[dept.id]
                const end = dept.pressure_score.at(-1)
                return (
                  <tr key={dept.id}>
                    <th>{dept.name}</th>
                    <td className="is-num">{toPoints(base.pressure_score)}</td>
                    <td className="is-num">{toPoints(end)}</td>
                    <td className="is-num">{Math.round(dept.queue_length.at(-1))}</td>
                    <td className="is-num">{Math.round(dept.avg_wait_min.at(-1))} min</td>
                    <td><LevelBadge level={dept.level.at(-1)} /></td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </section>
    </section>
  )
}
