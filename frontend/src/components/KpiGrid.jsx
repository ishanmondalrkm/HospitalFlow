import Sparkline from './Sparkline'
import { LEVEL_LABEL, deltaTone, formatDelta, formatValue } from '../lib/format'

// Quiet by default: a KPI only shows a level marker once its department is above Low.
export default function KpiGrid({ kpis }) {
  return (
    <section className="kpis" aria-label="Key indicators">
      {kpis.map((kpi) => {
        const attention = kpi.level && kpi.level !== 'LOW' ? kpi.level.toLowerCase() : null
        return (
          <div className="kpi" key={kpi.key}>
            <div className="kpi__label">
              {attention && (
                <>
                  <span className={`kpi__flag kpi__flag--${attention}`} aria-hidden="true" />
                  <span className="visually-hidden">{LEVEL_LABEL[kpi.level]} pressure. </span>
                </>
              )}
              {kpi.label}
            </div>
            <div className="kpi__main">
              <div className="kpi__value num">
                {formatValue(kpi.value, kpi.unit)}
                <span className="kpi__unit">{kpi.unit}</span>
              </div>
              <Sparkline values={kpi.sparkline} tone={attention ?? 'neutral'} />
            </div>
            <div className={`kpi__delta kpi__delta--${deltaTone(kpi.delta_1h, kpi.unit, kpi.higher_is_worse)}`}>
              {formatDelta(kpi.delta_1h, kpi.unit)}
            </div>
          </div>
        )
      })}
    </section>
  )
}
