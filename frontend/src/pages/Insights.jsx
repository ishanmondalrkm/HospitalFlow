import { useCallback, useEffect, useState } from 'react'
import ApiErrorNotice from '../components/ApiErrorNotice'
import LevelBadge from '../components/LevelBadge'
import { getInsights } from '../services/api'
import { toPoints, formatShortDateTime } from '../lib/format'

function signedPoints(value) {
  return `${value > 0 ? '+' : ''}${value}`
}

function OptionCard({ option, active, onSelect }) {
  const improved = option.pressure_delta < 0
  const worse = option.pressure_delta > 0
  return (
    <button type="button" className={`insight-option ${active ? 'is-active' : ''}`} onClick={() => onSelect(option.id)}>
      <div className="insight-option__top">
        <div>
          <strong>{option.title}</strong>
          <span>{option.description}</span>
        </div>
        <span className={`insight-impact ${improved ? 'is-improved' : worse ? 'is-worse' : ''}`}>
          {signedPoints(option.pressure_points)} pts
        </span>
      </div>
      <div className="insight-option__meta">
        <span>Projected pressure {toPoints(option.projected_pressure)}</span>
        <LevelBadge level={option.projected_level} />
      </div>
    </button>
  )
}

export default function Insights() {
  const [horizon, setHorizon] = useState(60)
  const [data, setData] = useState(null)
  const [selected, setSelected] = useState(null)
  const [status, setStatus] = useState('loading')
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    setStatus('loading')
    setError(null)
    try {
      const result = await getInsights(horizon)
      setData(result)
      setSelected((current) => current && result.options.some((item) => item.id === current) ? current : result.options[0]?.id ?? null)
      setStatus('ready')
    } catch (err) {
      setError(err)
      setStatus('error')
    }
  }, [horizon])

  useEffect(() => { load() }, [load])

  if (status === 'error' && !data) return <ApiErrorNotice error={error} onRetry={load} />
  if (!data) return <p className="loading" role="status">Building decision options</p>

  const selectedOption = data.options.find((item) => item.id === selected) ?? data.options[0]
  const improved = selectedOption?.pressure_delta < 0

  return (
    <section className="insights-page" aria-labelledby="insights-title">
      <div className="flow-page__intro insights-intro">
        <div>
          <p className="eyebrow">DECIDE / INSIGHTS</p>
          <h1 id="insights-title">Decision insights</h1>
          <p className="flow-page__subtitle">Compare modeled interventions against the same hospital state before choosing what to do next.</p>
        </div>
        <div className="segmented" role="group" aria-label="Decision horizon">
          {[30, 60, 120].map((minutes) => (
            <button key={minutes} type="button" aria-pressed={horizon === minutes} onClick={() => setHorizon(minutes)}>{minutes} min</button>
          ))}
        </div>
      </div>

      {error && data && <p className="refresh-note" role="status">Showing the last successful decision analysis. The latest refresh failed.</p>}

      <section className="panel insights-summary">
        <div className="insights-summary__copy">
          <p className="eyebrow">MODEL SIGNAL</p>
          <h2>{data.headline}</h2>
          <p className="panel__note">{data.headline_note} Analysis starts after {formatShortDateTime(data.as_of)}.</p>
        </div>
        <div className="insights-summary__focus">
          <span>Leading pressure point</span>
          <strong>{data.leading_department_name}</strong>
          <div><span>{toPoints(data.leading_pressure)} / 100</span><LevelBadge level={data.leading_level} /></div>
        </div>
      </section>

      <section className="panel insights-options" aria-labelledby="options-title">
        <div className="panel__head">
          <div>
            <p className="eyebrow">TESTED OPTIONS</p>
            <h2 id="options-title">What could change the outlook?</h2>
            <p className="panel__note">Each option is a deterministic counterfactual run over the selected horizon.</p>
          </div>
        </div>
        <div className="insight-options-grid">
          {data.options.map((option) => <OptionCard key={option.id} option={option} active={selected === option.id} onSelect={setSelected} />)}
        </div>
      </section>

      {selectedOption && (
        <section className="insight-detail" aria-labelledby="selected-option-title">
          <div className="panel insight-detail__main">
            <div className="insight-detail__header">
              <div>
                <p className="eyebrow">SELECTED OPTION</p>
                <h2 id="selected-option-title">{selectedOption.title}</h2>
                <p className="panel__note">{selectedOption.fit_reason}</p>
              </div>
              <div className={`insight-result ${improved ? 'is-improved' : selectedOption.pressure_delta > 0 ? 'is-worse' : ''}`}>
                <span>Pressure change</span>
                <strong>{signedPoints(selectedOption.pressure_points)}</strong>
                <small>at {horizon} minutes</small>
              </div>
            </div>

            <div className="insight-comparison">
              <div><span>Projected pressure</span><strong>Current → {toPoints(selectedOption.projected_pressure)}</strong></div>
              <div><span>Projected level</span><LevelBadge level={selectedOption.projected_level} /></div>
            </div>

            <div className="insight-table-wrap">
              <table className="insight-table">
                <thead><tr><th>Department</th><th>Pressure change</th><th>Queue change</th><th>Wait change</th><th>Projected</th></tr></thead>
                <tbody>
                  {Object.entries(selectedOption.department_impacts).sort((a, b) => a[1].pressure_delta - b[1].pressure_delta).map(([id, item]) => (
                    <tr key={id}>
                      <th scope="row">{item.name}</th>
                      <td className={item.pressure_delta < 0 ? 'is-improved' : item.pressure_delta > 0 ? 'is-worse' : ''}>{signedPoints(Number((item.pressure_delta * 100).toFixed(1)))} pts</td>
                      <td>{signedPoints(item.queue_delta)}</td>
                      <td>{signedPoints(item.wait_delta_min)} min</td>
                      <td><span>{toPoints(item.projected_pressure)}</span> <LevelBadge level={item.projected_level} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <aside className="panel insight-detail__side">
            <p className="eyebrow">TRADE-OFFS</p>
            <h3>Before acting</h3>
            <p>{selectedOption.tradeoff}</p>
            <h3>Why this option is shown</h3>
            <p>{selectedOption.when}</p>
            <div className="insight-note">HospitalFlow compares modeled outcomes; operational staff should confirm feasibility, staffing rules and local constraints before acting.</div>
          </aside>
        </section>
      )}
    </section>
  )
}
