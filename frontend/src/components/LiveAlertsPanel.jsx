import { useCallback, useEffect, useState } from 'react'
import { acknowledgeAlert, getAlerts } from '../services/api'
import { formatDateTime } from '../lib/format'
import { useAuth } from '../context/AuthContext'
import { hasPermission } from '../lib/rbac'

function severityClass(severity) {
  return String(severity || 'HIGH').toLowerCase()
}

export default function LiveAlertsPanel() {
  const { user } = useAuth()
  const canAcknowledge = hasPermission(user, 'acknowledge_alert')
  const [alerts, setAlerts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    try {
      const result = await getAlerts({ limit: 8 })
      setAlerts(result.alerts ?? [])
      setError(null)
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
    const handler = () => load()
    window.addEventListener('hospitalflow:live-tick', handler)
    return () => window.removeEventListener('hospitalflow:live-tick', handler)
  }, [load])

  async function acknowledge(alertId) {
    try {
      await acknowledgeAlert(alertId)
      await load()
    } catch (err) {
      setError(err)
    }
  }

  const openCount = alerts.filter((item) => item.status === 'OPEN').length

  return (
    <section className="panel live-alerts" aria-labelledby="live-alerts-title">
      <div className="panel__head live-alerts__head">
        <div>
          <h2 id="live-alerts-title">Live operational alerts</h2>
          <p className="panel__note">Alerts generated from the live operational feed.</p>
        </div>
        <span className={`alert-count ${openCount ? 'alert-count--attention' : ''}`}>
          {openCount} open
        </span>
      </div>

      {error && <p className="live-alerts__empty">Could not load alerts. The live feed is still running.</p>}
      {!error && loading && <p className="live-alerts__empty">Loading live alerts…</p>}
      {!error && !loading && alerts.length === 0 && (
        <p className="live-alerts__empty">No operational alerts have been generated yet.</p>
      )}
      {!error && !loading && alerts.length > 0 && (
        <div className="live-alerts__list">
          {alerts.map((item) => (
            <article className={`alert-row alert-row--${severityClass(item.severity)}`} key={item.alert_id}>
              <div className="alert-row__marker" aria-hidden="true" />
              <div className="alert-row__body">
                <div className="alert-row__top">
                  <strong>{item.severity}</strong>
                  <span>{item.department_id}</span>
                  <span>{formatDateTime(item.timestamp)}</span>
                </div>
                <p>{item.message}</p>
              </div>
              <div className="alert-row__action">
                {item.status === 'OPEN' && canAcknowledge ? (
                  <button type="button" className="button" onClick={() => acknowledge(item.alert_id)}>
                    Acknowledge
                  </button>
                ) : item.status === 'OPEN' ? (
                  <span className="alert-row__status">Read-only</span>
                ) : (
                  <span className="alert-row__status">Acknowledged</span>
                )}
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  )
}
