import { useState } from 'react'
import LevelBadge from './LevelBadge'
import {
  formatHour,
  formatShortDateTime,
  formatWeekdayDay,
  levelForScore,
  toPoints,
} from '../lib/format'

const WIDTH = 880
const HEIGHT = 264
const MARGIN = { top: 12, right: 14, bottom: 30, left: 40 }
const RANGES = [
  { id: '24h', label: '24 hours', points: 24 },
  { id: '7d', label: '7 days', points: Infinity },
]

export default function PressureChart({ history, departments, thresholds }) {
  const [rangeId, setRangeId] = useState('24h')
  const [seriesId, setSeriesId] = useState('overall')
  const [hover, setHover] = useState(null)

  const range = RANGES.find((r) => r.id === rangeId)
  const total = history.timestamps.length
  if (total === 0) {
    return (
      <section className="panel history" aria-labelledby="history-title">
        <div className="panel__head">
          <h2 id="history-title">Pressure history</h2>
          <p className="panel__note">There is no history to show yet.</p>
        </div>
      </section>
    )
  }

  const count = Math.min(total, range.points)
  const first = total - count
  const source = seriesId === 'overall' ? history.overall : (history.departments[seriesId] ?? history.overall)
  const values = source.slice(first)
  const stamps = history.timestamps.slice(first)
  const seriesName =
    seriesId === 'overall' ? 'Hospital overall' : (departments.find((d) => d.id === seriesId)?.name ?? seriesId)

  const plotW = WIDTH - MARGIN.left - MARGIN.right
  const plotH = HEIGHT - MARGIN.top - MARGIN.bottom
  const x = (i) => MARGIN.left + (count > 1 ? (i / (count - 1)) * plotW : 0)
  const y = (v) => MARGIN.top + (1 - Math.min(1, Math.max(0, v))) * plotH

  const zones = [
    { key: 'low', label: 'Low', from: 0, to: thresholds.medium },
    { key: 'medium', label: 'Medium', from: thresholds.medium, to: thresholds.high },
    { key: 'high', label: 'High', from: thresholds.high, to: thresholds.critical },
    { key: 'critical', label: 'Critical', from: thresholds.critical, to: 1 },
  ]
  const path = values.map((v, i) => `${i === 0 ? 'M' : 'L'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ')

  const ticks = []
  stamps.forEach((stamp, i) => {
    const date = new Date(stamp)
    if (rangeId === '24h' && date.getHours() % 4 === 0) ticks.push({ i, label: formatHour(date) })
    if (rangeId === '7d' && date.getHours() === 0) ticks.push({ i, label: formatWeekdayDay(date) })
  })

  const shown = hover ?? count - 1
  const shownValue = values[shown]

  function handleMove(event) {
    const box = event.currentTarget.getBoundingClientRect()
    if (!box.width) return
    const px = ((event.clientX - box.left) / box.width) * WIDTH
    const index = Math.round(((px - MARGIN.left) / plotW) * (count - 1))
    setHover(Math.min(count - 1, Math.max(0, index)))
  }

  return (
    <section className="panel history" aria-labelledby="history-title">
      <div className="panel__head history__head">
        <div>
          <h2 id="history-title">Pressure history</h2>
          <p className="panel__note">Pressure score by hour. The bands mark the Low, Medium, High and Critical levels.</p>
        </div>
        <div className="history__controls">
          <label className="select">
            <span className="visually-hidden">Show pressure for</span>
            <select value={seriesId} onChange={(event) => setSeriesId(event.target.value)}>
              <option value="overall">Hospital overall</option>
              {departments.map((dept) => (
                <option key={dept.id} value={dept.id}>
                  {dept.name}
                </option>
              ))}
            </select>
          </label>
          <div className="segmented" role="group" aria-label="Time range">
            {RANGES.map((r) => (
              <button
                key={r.id}
                type="button"
                aria-pressed={r.id === rangeId}
                onClick={() => {
                  setRangeId(r.id)
                  setHover(null)
                }}
              >
                {r.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <p className="history__readout num">
        <span>{formatShortDateTime(stamps[shown])}</span>
        <strong>{toPoints(shownValue)} of 100</strong>
        <LevelBadge level={levelForScore(shownValue, thresholds)} />
      </p>

      <div className="chart-wrap">
        <svg
          className="chart"
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          role="img"
          aria-label={`${seriesName} pressure over the last ${range.id === '24h' ? '24 hours' : '7 days'}. Latest value ${toPoints(values[count - 1])} out of 100.`}
          onPointerMove={handleMove}
          onPointerLeave={() => setHover(null)}
        >
          {zones.map((zone) => (
            <rect
              key={zone.key}
              className={`chart__zone chart__zone--${zone.key}`}
              x={MARGIN.left}
              y={y(zone.to)}
              width={plotW}
              height={y(zone.from) - y(zone.to)}
            />
          ))}
          {[thresholds.medium, thresholds.high, thresholds.critical].map((t) => (
            <line key={t} className="chart__grid" x1={MARGIN.left} x2={MARGIN.left + plotW} y1={y(t)} y2={y(t)} />
          ))}
          {[0, thresholds.medium, thresholds.high, thresholds.critical, 1].map((t) => (
            <text key={`y-${t}`} className="chart__axis-label" x={MARGIN.left - 8} y={y(t) + 4} textAnchor="end">
              {toPoints(t)}
            </text>
          ))}
          {zones.map((zone) => (
            <text
              key={`z-${zone.key}`}
              className="chart__zone-label"
              x={WIDTH - MARGIN.right - 8}
              y={y(zone.to) + 15}
              textAnchor="end"
            >
              {zone.label}
            </text>
          ))}
          {ticks.map((tick) => (
            <g key={tick.i}>
              <line className="chart__tick" x1={x(tick.i)} x2={x(tick.i)} y1={MARGIN.top + plotH} y2={MARGIN.top + plotH + 5} />
              <text className="chart__axis-label" x={x(tick.i)} y={HEIGHT - 8} textAnchor="middle">
                {tick.label}
              </text>
            </g>
          ))}
          <path className="chart__line" d={path} />
          {hover !== null && (
            <line className="chart__guide" x1={x(shown)} x2={x(shown)} y1={MARGIN.top} y2={MARGIN.top + plotH} />
          )}
          <circle className="chart__point" cx={x(shown)} cy={y(shownValue)} r="4.5" />
        </svg>
      </div>
    </section>
  )
}
