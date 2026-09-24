import { useCallback, useMemo, useState } from 'react'
import ApiErrorNotice from '../components/ApiErrorNotice'
import LevelBadge from '../components/LevelBadge'
import { getBottlenecks } from '../services/api'
import { useApi } from '../services/useApi'
import { toPoints } from '../lib/format'

function Contributor({ item }) {
  const percent = Math.round(item.value * 100)
  return (
    <div className="contributor">
      <div className="contributor__head">
        <strong>{item.label}</strong>
        <span className="num">{percent}% signal</span>
      </div>
      <div className="pressure-bar" aria-hidden="true">
        <span style={{ width: `${Math.max(0, Math.min(100, percent))}%` }} />
      </div>
      <p>{item.reason}</p>
    </div>
  )
}

export default function Bottlenecks() {
  const [selectedId, setSelectedId] = useState(null)
  const loader = useCallback((options) => getBottlenecks(options), [])
  const { status, data, error, reload } = useApi(loader)

  const leading = useMemo(() => {
    if (!data) return null
    return data.departments.find((item) => item.id === data.leading_department_id) ?? data.departments[0]
  }, [data])

  if (!data && status === 'error') return <ApiErrorNotice error={error} onRetry={reload} />
  if (!data) return <p className="loading" role="status">Explaining operational pressure</p>

  const selected = data.departments.find((item) => item.id === (selectedId ?? leading?.id)) ?? leading

  return (
    <section className="bottleneck-page" aria-labelledby="bottleneck-title">
      <div className="flow-page__intro">
        <div>
          <p className="eyebrow">EXPLAIN / BOTTLENECKS</p>
          <h1 id="bottleneck-title">Bottlenecks</h1>
          <p className="flow-page__subtitle">
            Break current pressure into its four model components and trace where work can propagate through the configured hospital network.
          </p>
        </div>
        <button className="button" type="button" onClick={reload} disabled={status === 'loading'}>
          {status === 'loading' ? 'Refreshing…' : 'Refresh'}
        </button>
      </div>

      {error && data && <p className="refresh-note" role="status">Showing the last successful explanation. Refresh failed.</p>}

      <section className="panel bottleneck-summary panel--accent" aria-labelledby="bottleneck-summary-title">
        <div>
          <p className="eyebrow">MODEL EXPLANATION</p>
          <h2 id="bottleneck-summary-title">{data.headline}</h2>
          <p className="panel__note">Pressure is the same score used by Monitor: queue 35%, utilization 30%, arrival surge 20%, resource constraint 15%.</p>
        </div>
        <div className="bottleneck-summary__metric">
          <span>Leading pressure point</span>
          <strong>{leading?.name}</strong>
          <span>{toPoints(leading?.pressure_score)} / 100 · <LevelBadge level={leading?.level} /></span>
        </div>
      </section>

      <div className="bottleneck-grid">
        <section className="panel" aria-labelledby="department-pressure-title">
          <div className="panel__head">
            <h2 id="department-pressure-title">Where pressure is coming from</h2>
            <p className="panel__note">Select a department to inspect its contributors.</p>
          </div>
          <div className="bottleneck-list">
            {data.departments.map((dept) => (
              <button
                className={`bottleneck-row ${selected?.id === dept.id ? 'is-selected' : ''}`}
                key={dept.id}
                type="button"
                onClick={() => setSelectedId(dept.id)}
              >
                <span className="bottleneck-row__main">
                  <strong>{dept.name}</strong>
                  <span>{dept.queue_length} in queue · {Math.round(dept.avg_wait_min)} min wait</span>
                </span>
                <span className="bottleneck-row__score num">{toPoints(dept.pressure_score)}</span>
                <LevelBadge level={dept.level} />
              </button>
            ))}
          </div>
        </section>

        <section className="panel bottleneck-detail" aria-labelledby="detail-title">
          <div className="panel__head">
            <h2 id="detail-title">Why {selected?.name}?</h2>
            <p className="panel__note">Contributors are ordered by their weighted contribution to the current pressure score.</p>
          </div>
          <div className="detail-metrics">
            <div><span>Pressure</span><strong>{toPoints(selected?.pressure_score)}</strong></div>
            <div><span>1h change</span><strong>{selected?.pressure_delta_1h >= 0 ? '+' : ''}{toPoints(selected?.pressure_delta_1h)}</strong></div>
            <div><span>Utilization</span><strong>{Math.round((selected?.utilization ?? 0) * 100)}%</strong></div>
          </div>
          <div className="contributors">
            {selected?.contributors.map((item) => <Contributor key={item.key} item={item} />)}
          </div>
        </section>
      </div>

      <section className="panel" aria-labelledby="propagation-title">
        <div className="panel__head">
          <h2 id="propagation-title">Modeled propagation</h2>
          <p className="panel__note">These links come from the configured routing model. They describe operational work moving downstream, not patient-level causality.</p>
        </div>
        <div className="propagation-layout">
          <div className="chain" aria-label="Leading bottleneck chain">
            {data.chain.map((item, index) => (
              <div className="chain__item" key={item.id}>
                <div className="chain__card">
                  <strong>{item.name}</strong>
                  <span>{toPoints(item.pressure_score)} pressure</span>
                  <LevelBadge level={item.level} />
                </div>
                {index < data.chain.length - 1 && <span className="chain__arrow" aria-hidden="true">→</span>}
              </div>
            ))}
          </div>
          <div className="propagation-list">
            {data.propagation.slice(0, 6).map((link) => (
              <div className="propagation-item" key={`${link.source_id}-${link.target_id}`}>
                <div>
                  <strong>{link.source_name} → {link.target_name}</strong>
                  <p>{link.signal}</p>
                </div>
                <span className="num propagation-score">{(link.propagation_score * 100).toFixed(0)} signal</span>
              </div>
            ))}
          </div>
        </div>
      </section>
    </section>
  )
}
