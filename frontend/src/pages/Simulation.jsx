import { useCallback, useEffect, useMemo, useState } from 'react'
import ApiErrorNotice from '../components/ApiErrorNotice'
import LevelBadge from '../components/LevelBadge'
import { runSimulation } from '../services/api'
import { toPoints, formatShortDateTime } from '../lib/format'

const DEFAULTS = {
  horizon_minutes: 60,
  emergency_arrival_pct: 0,
  walkin_arrival_pct: 0,
  emergency_staff_delta: 1,
  laboratory_staff_delta: 0,
  discharge_staff_delta: 1,
  laboratory_capacity_pct: 0.2,
  discharge_capacity_pct: 0.1,
}

const PRESETS = [
  {
    id: 'emergency-staff',
    label: 'Add emergency staff',
    hint: '+2 emergency staff',
    changes: { emergency_staff_delta: 2 },
  },
  {
    id: 'lab-capacity',
    label: 'Increase lab capacity',
    hint: '+30% laboratory capacity',
    changes: { laboratory_capacity_pct: 0.3 },
  },
  {
    id: 'discharge',
    label: 'Speed up discharge',
    hint: '+20% discharge capacity',
    changes: { discharge_capacity_pct: 0.2, discharge_staff_delta: 2 },
  },
  {
    id: 'reduce-demand',
    label: 'Reduce emergency demand',
    hint: '-10% emergency arrivals',
    changes: { emergency_arrival_pct: -0.1 },
  },
]

function signedPercent(value) {
  const pct = Math.round(value * 100)
  return `${pct > 0 ? '+' : ''}${pct}%`
}

function ScenarioChart({ data }) {
  const base = data.baseline.overall.pressure_score
  const simulated = data.simulated.overall.pressure_score
  const width = 900
  const height = 250
  const margin = { top: 16, right: 18, bottom: 34, left: 42 }
  const plotW = width - margin.left - margin.right
  const plotH = height - margin.top - margin.bottom
  const maxLen = Math.max(base.length, simulated.length)
  const x = (i) => margin.left + (maxLen === 1 ? plotW / 2 : (i / (maxLen - 1)) * plotW)
  const y = (v) => margin.top + (1 - Math.max(0, Math.min(1, v))) * plotH
  const pathFor = (series) => series.map((v, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ')

  return (
    <div className="chart-wrap simulation-chart-wrap">
      <div className="simulation-chart__legend" aria-hidden="true">
        <span><i className="simulation-dot simulation-dot--base" /> Current plan</span>
        <span><i className="simulation-dot simulation-dot--scenario" /> Scenario</span>
      </div>
      <svg className="chart simulation-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Current plan versus simulated hospital pressure">
        {[0, 0.35, 0.55, 0.75, 1].map((t) => (
          <g key={t}>
            <line className="chart__grid" x1={margin.left} x2={margin.left + plotW} y1={y(t)} y2={y(t)} />
            <text className="chart__axis-label" x={margin.left - 8} y={y(t) + 4} textAnchor="end">{toPoints(t)}</text>
          </g>
        ))}
        <path className="simulation-line simulation-line--base" d={pathFor(base)} />
        <path className="simulation-line simulation-line--scenario" d={pathFor(simulated)} />
        {simulated.map((value, index) => <circle className="simulation-point simulation-point--scenario" key={`s-${index}`} cx={x(index)} cy={y(value)} r="3.5" />)}
        {data.timestamps.map((stamp, index) => (
          <text key={stamp} className="chart__axis-label" x={x(index)} y={height - 9} textAnchor="middle">
            {new Date(stamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </text>
        ))}
      </svg>
    </div>
  )
}

function RangeControl({ label, value, min, max, step, display, onChange }) {
  return (
    <div className="scenario-field">
      <div className="scenario-field__head">
        <strong>{label}</strong>
        <span className="num">{display}</span>
      </div>
      <input type="range" min={min} max={max} step={step} value={value} onChange={(event) => onChange(Number(event.target.value))} />
    </div>
  )
}

function ScenarioPills({ scenario }) {
  const pills = []
  if (scenario.emergency_arrival_pct) pills.push(`Emergency arrivals ${signedPercent(scenario.emergency_arrival_pct)}`)
  if (scenario.walkin_arrival_pct) pills.push(`Walk-ins ${signedPercent(scenario.walkin_arrival_pct)}`)
  if (scenario.emergency_staff_delta) pills.push(`Emergency staff ${scenario.emergency_staff_delta > 0 ? '+' : ''}${scenario.emergency_staff_delta}`)
  if (scenario.laboratory_staff_delta) pills.push(`Lab staff ${scenario.laboratory_staff_delta > 0 ? '+' : ''}${scenario.laboratory_staff_delta}`)
  if (scenario.discharge_staff_delta) pills.push(`Discharge staff ${scenario.discharge_staff_delta > 0 ? '+' : ''}${scenario.discharge_staff_delta}`)
  if (scenario.laboratory_capacity_pct) pills.push(`Lab capacity ${signedPercent(scenario.laboratory_capacity_pct)}`)
  if (scenario.discharge_capacity_pct) pills.push(`Discharge capacity ${signedPercent(scenario.discharge_capacity_pct)}`)
  return <div className="scenario-pills">{pills.map((pill) => <span key={pill}>{pill}</span>)}</div>
}

export default function Simulation() {
  const [scenario, setScenario] = useState(DEFAULTS)
  const [horizon, setHorizon] = useState(60)
  const [data, setData] = useState(null)
  const [status, setStatus] = useState('loading')
  const [error, setError] = useState(null)
  const [activePreset, setActivePreset] = useState(null)

  const execute = useCallback(async (payload = { ...scenario, horizon_minutes: horizon }) => {
    setStatus('loading')
    setError(null)
    try {
      const result = await runSimulation(payload)
      setData(result)
      setStatus('ready')
    } catch (err) {
      setError(err)
      setStatus('error')
    }
  }, [horizon, scenario])

  useEffect(() => { execute() }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const impactRows = useMemo(() => {
    if (!data) return []
    return Object.entries(data.department_impacts).sort((a, b) => a[1].pressure_delta - b[1].pressure_delta)
  }, [data])

  const update = (key, value) => {
    setScenario((current) => ({ ...current, [key]: value }))
    setActivePreset(null)
  }

  const applyPreset = (preset) => {
    setScenario((current) => ({ ...DEFAULTS, ...current, ...preset.changes }))
    setActivePreset(preset.id)
  }

  const reset = () => {
    setScenario(DEFAULTS)
    setHorizon(60)
    setActivePreset(null)
    execute({ ...DEFAULTS, horizon_minutes: 60 })
  }

  if (!data && status === 'error') return <ApiErrorNotice error={error} onRetry={() => execute()} />
  if (!data) return <p className="loading" role="status">Running the hospital simulation</p>

  const overall = data.overall_impact
  const improved = overall.pressure_delta < 0
  const endBase = data.baseline.overall.pressure_score.at(-1)
  const endScenario = data.simulated.overall.pressure_score.at(-1)

  return (
    <section className="simulation-page" aria-labelledby="simulation-title">
      <div className="flow-page__intro simulation-intro">
        <div>
          <p className="eyebrow">SIMULATE / WHAT-IF</p>
          <h1 id="simulation-title">Simulation lab</h1>
          <p className="flow-page__subtitle">Build a what-if scenario, run the connected hospital model, and compare the projected outcome before you act.</p>
        </div>
        <button className="button button--primary simulation-run-top" type="button" onClick={() => execute()} disabled={status === 'loading'}>
          {status === 'loading' ? 'Simulating…' : 'Run simulation'}
        </button>
      </div>

      {error && data && <p className="refresh-note" role="status">Showing the last successful simulation. The latest run failed.</p>}

      <section className="panel simulation-summary" aria-labelledby="simulation-summary-title">
        <div className={`simulation-summary__message ${improved ? 'is-improved' : overall.pressure_delta > 0 ? 'is-worse' : 'is-neutral'}`}>
          <p className="eyebrow">PROJECTED EFFECT</p>
          <h2 id="simulation-summary-title">
            {improved ? 'Scenario is projected to reduce hospital pressure' : overall.pressure_delta > 0 ? 'Scenario is projected to increase hospital pressure' : 'Scenario is projected to have little effect on hospital pressure'}
          </h2>
          <p className="panel__note">Simulation starts after {formatShortDateTime(data.as_of)} and advances in {data.interval_minutes}-minute intervals.</p>
        </div>
        <div className="simulation-summary__metric">
          <span>At {data.horizon_minutes} minutes</span>
          <strong>{toPoints(endBase)} → {toPoints(endScenario)}</strong>
          <span>{overall.pressure_points > 0 ? '+' : ''}{overall.pressure_points} pressure points</span>
        </div>
      </section>

      <section className="panel scenario-builder" aria-labelledby="scenario-builder-title">
        <div className="scenario-builder__head">
          <div>
            <p className="eyebrow">STEP 1 · CONFIGURE</p>
            <h2 id="scenario-builder-title">Build your scenario</h2>
            <p className="panel__note">Start with a quick intervention or fine-tune the inputs below.</p>
          </div>
          <div className="segmented" role="group" aria-label="Simulation horizon">
            {[30, 60, 120].map((minutes) => <button key={minutes} type="button" aria-pressed={horizon === minutes} onClick={() => setHorizon(minutes)}>{minutes} min</button>)}
          </div>
        </div>

        <div className="preset-strip">
          <span className="preset-strip__label">Quick scenarios</span>
          {PRESETS.map((preset) => (
            <button key={preset.id} type="button" className={`preset-card ${activePreset === preset.id ? 'is-active' : ''}`} onClick={() => applyPreset(preset)}>
              <strong>{preset.label}</strong>
              <span>{preset.hint}</span>
            </button>
          ))}
          <button type="button" className="button button--quiet preset-reset" onClick={reset}>Reset</button>
        </div>

        <div className="scenario-groups">
          <section className="scenario-group" aria-labelledby="demand-title">
            <div className="scenario-group__head"><span className="scenario-group__icon">D</span><div><h3 id="demand-title">Demand</h3><p>Change incoming patient volume.</p></div></div>
            <div className="scenario-fields">
              <RangeControl label="Emergency arrivals" value={scenario.emergency_arrival_pct} min={-0.3} max={0.5} step={0.1} display={signedPercent(scenario.emergency_arrival_pct)} onChange={(v) => update('emergency_arrival_pct', v)} />
              <RangeControl label="Walk-in arrivals" value={scenario.walkin_arrival_pct} min={-0.3} max={0.5} step={0.1} display={signedPercent(scenario.walkin_arrival_pct)} onChange={(v) => update('walkin_arrival_pct', v)} />
            </div>
          </section>

          <section className="scenario-group" aria-labelledby="staff-title">
            <div className="scenario-group__head"><span className="scenario-group__icon">S</span><div><h3 id="staff-title">Staffing</h3><p>Add or remove operational coverage.</p></div></div>
            <div className="scenario-fields">
              <RangeControl label="Emergency staff" value={scenario.emergency_staff_delta} min={-3} max={4} step={1} display={`${scenario.emergency_staff_delta > 0 ? '+' : ''}${scenario.emergency_staff_delta} staff`} onChange={(v) => update('emergency_staff_delta', v)} />
              <RangeControl label="Laboratory staff" value={scenario.laboratory_staff_delta} min={-2} max={3} step={1} display={`${scenario.laboratory_staff_delta > 0 ? '+' : ''}${scenario.laboratory_staff_delta} staff`} onChange={(v) => update('laboratory_staff_delta', v)} />
              <RangeControl label="Discharge staff" value={scenario.discharge_staff_delta} min={-2} max={3} step={1} display={`${scenario.discharge_staff_delta > 0 ? '+' : ''}${scenario.discharge_staff_delta} staff`} onChange={(v) => update('discharge_staff_delta', v)} />
            </div>
          </section>

          <section className="scenario-group scenario-group--wide" aria-labelledby="capacity-title">
            <div className="scenario-group__head"><span className="scenario-group__icon">C</span><div><h3 id="capacity-title">Processing capacity</h3><p>Change how much work the laboratory and discharge process can handle.</p></div></div>
            <div className="scenario-fields scenario-fields--two">
              <RangeControl label="Laboratory capacity" value={scenario.laboratory_capacity_pct} min={-0.3} max={0.5} step={0.1} display={`${signedPercent(scenario.laboratory_capacity_pct)} capacity`} onChange={(v) => update('laboratory_capacity_pct', v)} />
              <RangeControl label="Discharge capacity" value={scenario.discharge_capacity_pct} min={-0.3} max={0.5} step={0.1} display={`${signedPercent(scenario.discharge_capacity_pct)} capacity`} onChange={(v) => update('discharge_capacity_pct', v)} />
            </div>
          </section>
        </div>

        <div className="scenario-builder__footer">
          <div>
            <span className="scenario-builder__footer-label">Selected scenario</span>
            <ScenarioPills scenario={scenario} />
          </div>
          <button className="button button--primary" type="button" onClick={() => execute()} disabled={status === 'loading'}>
            {status === 'loading' ? 'Running…' : 'Run simulation'}
          </button>
        </div>
      </section>

      <section className="panel simulation-result" aria-labelledby="simulation-result-title">
        <div className="simulation-result__head">
          <div>
            <p className="eyebrow">STEP 2 · UNDERSTAND</p>
            <h2 id="simulation-result-title">Simulation result</h2>
            <p className="panel__note">Lower pressure, shorter queues and shorter waits are shown as negative deltas.</p>
          </div>
          <div className="simulation-result__headline">
            <span>At {data.horizon_minutes} minutes</span>
            <strong>{toPoints(endBase)} → {toPoints(endScenario)}</strong>
            <span className={improved ? 'simulation-result__good' : ''}>{overall.pressure_points > 0 ? '+' : ''}{overall.pressure_points} pressure points</span>
          </div>
        </div>

        <div className="simulation-result-grid">
          <div><span>Current plan</span><strong>{toPoints(endBase)}</strong><LevelBadge level={data.baseline.overall.level.at(-1)} /></div>
          <div><span>Scenario</span><strong>{toPoints(endScenario)}</strong><LevelBadge level={data.simulated.overall.level.at(-1)} /></div>
          <div><span>Pressure change</span><strong>{overall.pressure_points > 0 ? '+' : ''}{overall.pressure_points}</strong></div>
        </div>

        <ScenarioChart data={data} />
      </section>

      <section className="panel" aria-labelledby="simulation-impact-title">
        <div className="panel__head">
          <h2 id="simulation-impact-title">Department impact</h2>
          <p className="panel__note">Final values at the selected horizon compared with the same horizon under the current plan.</p>
        </div>
        <div className="forecast-table-wrap">
          <table className="dept-table">
            <thead><tr><th>Department</th><th>Pressure change</th><th>Queue change</th><th>Wait change</th><th>Projected pressure</th><th>Level</th></tr></thead>
            <tbody>
              {impactRows.map(([id, item]) => (
                <tr key={id}>
                  <th>{item.name}</th>
                  <td className="is-num">{item.pressure_delta > 0 ? '+' : ''}{toPoints(item.pressure_delta)}</td>
                  <td className="is-num">{item.queue_delta > 0 ? '+' : ''}{item.queue_delta.toFixed(1)}</td>
                  <td className="is-num">{item.wait_delta_min > 0 ? '+' : ''}{item.wait_delta_min.toFixed(1)} min</td>
                  <td className="is-num">{toPoints(item.projected_pressure)}</td>
                  <td><LevelBadge level={item.projected_level} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </section>
  )
}
