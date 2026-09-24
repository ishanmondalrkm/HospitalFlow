import ApiErrorNotice from '../components/ApiErrorNotice'
import LevelBadge from '../components/LevelBadge'
import { getDashboard } from '../services/api'
import { useApi } from '../services/useApi'

const NODE_POSITIONS = {
  registration: { x: 70, y: 90 },
  opd: { x: 250, y: 90 },
  emergency: { x: 250, y: 255 },
  laboratory: { x: 470, y: 90 },
  radiology: { x: 470, y: 255 },
  pharmacy: { x: 690, y: 90 },
  beds: { x: 690, y: 255 },
  discharge: { x: 900, y: 255 },
}

const ROUTES = [
  ['registration', 'opd'],
  ['opd', 'laboratory'],
  ['opd', 'radiology'],
  ['opd', 'pharmacy'],
  ['opd', 'beds'],
  ['emergency', 'laboratory'],
  ['emergency', 'radiology'],
  ['emergency', 'pharmacy'],
  ['emergency', 'beds'],
  ['discharge', 'pharmacy'],
]

function scoreWidth(score) {
  return `${Math.max(0, Math.min(100, score * 100))}%`
}

function FlowNode({ department }) {
  const position = NODE_POSITIONS[department.id]
  return (
    <g transform={`translate(${position.x} ${position.y})`}>
      <rect className={`flow-svg__node flow-svg__node--${department.level.toLowerCase()}`} x="-72" y="-38" width="144" height="76" rx="10" />
      <text className="flow-svg__name" x="0" y="-8" textAnchor="middle">{department.name}</text>
      <text className="flow-svg__metric" x="0" y="13" textAnchor="middle">{Math.round(department.pressure_score * 100)}% pressure</text>
      <text className="flow-svg__wait" x="0" y="31" textAnchor="middle">{Math.round(department.avg_wait_min)} min wait</text>
    </g>
  )
}

function Arrow({ from, to }) {
  const a = NODE_POSITIONS[from]
  const b = NODE_POSITIONS[to]
  const startX = a.x + (b.x >= a.x ? 72 : -72)
  const endX = b.x + (b.x >= a.x ? -72 : 72)
  const startY = a.y
  const endY = b.y
  const midX = (startX + endX) / 2
  const path = startY === endY
    ? `M ${startX} ${startY} L ${endX} ${endY}`
    : `M ${startX} ${startY} C ${midX} ${startY}, ${midX} ${endY}, ${endX} ${endY}`
  return <path className="flow-svg__edge" d={path} markerEnd="url(#flow-arrow)" />
}

export default function Flow() {
  const { status, data, error, reload } = useApi(getDashboard)

  if (!data && status === 'error') return <ApiErrorNotice error={error} onRetry={reload} />
  if (!data) return <p className="loading" role="status">Loading hospital flow</p>

  const byId = Object.fromEntries(data.departments.map((department) => [department.id, department]))

  return (
    <section className="flow-page" aria-labelledby="flow-title">
      <div className="flow-page__intro">
        <div>
          <p className="eyebrow">MONITOR / HOSPITAL FLOW</p>
          <h1 id="flow-title">Hospital flow</h1>
          <p className="flow-page__subtitle">
            Follow operational pressure through the connected hospital network. The values below are live from the same model used by the overview dashboard.
          </p>
        </div>
        <button className="button" type="button" onClick={reload} disabled={status === 'loading'}>
          {status === 'loading' ? 'Refreshing…' : 'Refresh'}
        </button>
      </div>

      {error && data && <p className="refresh-note" role="status">Showing the last successful snapshot. Refresh failed.</p>}

      <section className="panel flow-panel panel--accent" aria-labelledby="network-title">
        <div className="panel__head">
          <h2 id="network-title">Operational network</h2>
          <p className="panel__note">Arrows show modeled downstream work. Pressure is the current department score.</p>
        </div>
        <div className="flow-svg-wrap">
          <svg className="flow-svg" viewBox="0 0 990 345" role="img" aria-label="Connected hospital department flow">
            <defs>
              <marker id="flow-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
                <path d="M0,0 L8,4 L0,8 Z" className="flow-svg__arrow" />
              </marker>
            </defs>
            {ROUTES.map(([from, to]) => <Arrow key={`${from}-${to}`} from={from} to={to} />)}
            {data.departments.map((department) => <FlowNode key={department.id} department={department} />)}
          </svg>
        </div>
      </section>

      <div className="flow-grid">
        <section className="panel" aria-labelledby="pressure-title">
          <div className="panel__head">
            <h2 id="pressure-title">Pressure by department</h2>
            <p className="panel__note">Higher bars indicate greater operational pressure.</p>
          </div>
          <div className="flow-list">
            {data.departments.map((department) => (
              <div className="flow-row" key={department.id}>
                <div className="flow-row__top">
                  <strong>{department.name}</strong>
                  <LevelBadge level={department.level} />
                </div>
                <div className="flow-row__bar" aria-hidden="true">
                  <span style={{ width: scoreWidth(department.pressure_score) }} />
                </div>
                <div className="flow-row__meta">
                  <span>{Math.round(department.pressure_score * 100)}% pressure</span>
                  <span>{department.queue_length} waiting · {Math.round(department.avg_wait_min)} min wait</span>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="panel" aria-labelledby="handoff-title">
          <div className="panel__head">
            <h2 id="handoff-title">Flow watch</h2>
            <p className="panel__note">Operational signals that can propagate through the network.</p>
          </div>
          <div className="flow-watch">
            {['emergency', 'laboratory', 'beds', 'discharge'].map((id) => {
              const department = byId[id]
              return (
                <div className="flow-watch__item" key={id}>
                  <div>
                    <strong>{department.name}</strong>
                    <span>{department.queue_length} in queue</span>
                  </div>
                  <span className="num">{Math.round(department.utilization * 100)}%</span>
                </div>
              )
            })}
          </div>
        </section>
      </div>
    </section>
  )
}
