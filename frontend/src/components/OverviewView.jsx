import ApiErrorNotice from './ApiErrorNotice'
import DepartmentTable from './DepartmentTable'
import KpiGrid from './KpiGrid'
import PressureChart from './PressureChart'
import PressureScale from './PressureScale'
import ResourcesPanel from './ResourcesPanel'
import { formatDateTime } from '../lib/format'
import LiveAlertsPanel from './LiveAlertsPanel'

// Pure view of one /api/dashboard response. Kept separate from the data loading
// in pages/Overview.jsx so it can be rendered from any payload.
export default function OverviewView({ data, onRefresh, refreshing = false, error = null }) {
  const { hospital, kpis, departments, resources, history, scoring } = data

  return (
    <div className="overview">
      <header className="page-head">
        <div>
          <h1>Overview</h1>
          <p className="page-head__sub">{hospital.name}</p>
        </div>
        <div className="page-head__meta">
          <span className="tag" title="All numbers are synthetic. HospitalFlow uses no patient-level data.">
            Synthetic data
          </span>
          <span>Data as of {formatDateTime(data.as_of)}</span>
          <button type="button" className="button" onClick={onRefresh} disabled={refreshing}>
            {refreshing ? 'Refreshing data' : 'Refresh data'}
          </button>
        </div>
      </header>

      {error && <ApiErrorNotice error={error} onRetry={onRefresh} />}

      <section className="panel status" aria-labelledby="status-title">
        <div>
          <h2 id="status-title" className="status__label">
            <span className={`status__dot status__dot--${hospital.level.toLowerCase()}`} aria-hidden="true" />
            {hospital.status}
          </h2>
          <p className="status__headline">{hospital.headline}</p>
        </div>
        <PressureScale
          score={hospital.overall_score}
          level={hospital.level}
          delta={hospital.overall_delta_1h}
          thresholds={scoring.thresholds}
        />
      </section>

      <KpiGrid kpis={kpis} />

      <LiveAlertsPanel />

      <div className="split">
        <DepartmentTable departments={departments} weights={scoring.weights} />
        <ResourcesPanel resources={resources} />
      </div>

      <PressureChart history={history} departments={departments} thresholds={scoring.thresholds} />
    </div>
  )
}
