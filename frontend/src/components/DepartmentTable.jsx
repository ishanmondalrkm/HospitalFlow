import { Fragment, useState } from 'react'
import LevelBadge from './LevelBadge'
import { LEVEL_LABEL, toPoints } from '../lib/format'

// The four parts of a pressure score, in plain language. Keys match the API's
// `breakdown` and `scoring.weights`.
const PARTS = [
  {
    key: 'queue',
    label: () => 'Waiting time',
    hint: () => 'How far the wait has moved from normal towards critical.',
  },
  {
    key: 'utilization',
    label: (d) => (d.kind === 'beds' ? 'Beds occupied' : 'Capacity in use'),
    hint: (d) =>
      d.kind === 'beds'
        ? 'Occupancy, counted from 80% full.'
        : 'Share of capacity in use over the last hour, counted from 70%.',
  },
  {
    key: 'arrival_surge',
    label: () => 'Arrivals above usual',
    hint: () => 'Arrivals compared with the same time of day on other days.',
  },
  {
    key: 'resource_constraint',
    label: (d) => (d.kind === 'beds' ? 'Beds held by discharges' : 'Staff shortfall'),
    hint: (d) =>
      d.kind === 'beds'
        ? 'Occupied beds waiting on discharge processing.'
        : 'Staff on duty compared with the roster.',
  },
]

function Chevron() {
  return (
    <svg className="dept-row__chevron" viewBox="0 0 8 12" width="8" height="12" aria-hidden="true">
      <path d="M1.5 1.5 6 6l-4.5 4.5" fill="none" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function Delta({ points }) {
  if (points === 0) return <span className="delta delta--flat">No change</span>
  const up = points > 0
  const size = Math.abs(points)
  return (
    <span
      className={`delta delta--${up ? 'bad' : 'good'}`}
      title={`${up ? 'Up' : 'Down'} ${size} ${size === 1 ? 'point' : 'points'} in the last hour`}
    >
      <svg className={up ? '' : 'is-down'} viewBox="0 0 8 8" width="8" height="8" aria-hidden="true">
        <path d="M4 1 7.5 7h-7z" />
      </svg>
      <span className="num">{size}</span>
      <span className="visually-hidden">{up ? ' points up' : ' points down'}</span>
    </span>
  )
}

function Breakdown({ department, weights }) {
  return (
    <div className="breakdown">
      {PARTS.map((part) => {
        const value = department.breakdown[part.key]
        const weight = weights[part.key]
        const points = Math.round(value * weight * 100)
        const most = Math.round(weight * 100)
        return (
          <div className="breakdown__item" key={part.key}>
            <div className="breakdown__label">{part.label(department)}</div>
            <span
              className="meter meter--neutral"
              role="img"
              aria-label={`${Math.round(value * 100)} percent of the maximum`}
            >
              <span className="meter__fill" style={{ width: `${value * 100}%` }} />
            </span>
            <div className="breakdown__points num">
              {points === 0 ? 'Adds nothing' : `Adds ${points} of up to ${most} points`}
            </div>
            <div className="breakdown__hint">{part.hint(department)}</div>
          </div>
        )
      })}
    </div>
  )
}

export default function DepartmentTable({ departments, weights }) {
  const [openId, setOpenId] = useState(null)

  return (
    <section className="panel departments" aria-labelledby="departments-title">
      <div className="panel__head">
        <h2 id="departments-title">Departments</h2>
        <p className="panel__note">In patient-flow order. Select a row to see how its pressure score is built.</p>
      </div>
      <div className="table-wrap">
        <table className="dept-table">
          <thead>
            <tr>
              <th scope="col">Department</th>
              <th scope="col">Pressure</th>
              <th scope="col" className="is-num">
                Wait
              </th>
              <th scope="col" className="is-num">
                Queue
              </th>
              <th scope="col" className="is-num">
                Utilization
              </th>
              <th scope="col" className="is-num" title="Change in the pressure score over the last hour">
                Last hour
              </th>
            </tr>
          </thead>
          <tbody>
            {departments.map((dept) => {
              const open = openId === dept.id
              const points = toPoints(dept.pressure_score)
              const level = dept.level.toLowerCase()
              return (
                <Fragment key={dept.id}>
                  <tr className={`dept-row${open ? ' is-open' : ''}`}>
                    <th scope="row">
                      <button
                        type="button"
                        className="dept-row__toggle"
                        aria-expanded={open}
                        aria-controls={`breakdown-${dept.id}`}
                        onClick={() => setOpenId(open ? null : dept.id)}
                      >
                        <Chevron />
                        <span>
                          <span className="dept-row__name">{dept.name}</span>
                          <span className="dept-row__sub">
                            {dept.kind === 'beds'
                              ? 'Bed occupancy'
                              : `${dept.staff_on_duty} of ${dept.staff_planned} staff`}
                          </span>
                        </span>
                      </button>
                    </th>
                    <td>
                      <div className="pressure-cell">
                        <span
                          className={`meter meter--${level}`}
                          role="img"
                          aria-label={`Pressure ${points} out of 100, ${LEVEL_LABEL[dept.level]}`}
                        >
                          <span className="meter__fill" style={{ width: `${points}%` }} />
                        </span>
                        <span className="pressure-cell__points num">{points}</span>
                        <LevelBadge level={dept.level} />
                      </div>
                    </td>
                    <td className="is-num">{Math.round(dept.avg_wait_min)} min</td>
                    <td className="is-num">{dept.queue_length}</td>
                    <td className="is-num">{Math.round(dept.utilization * 100)}%</td>
                    <td className="is-num">
                      <Delta points={Math.round(dept.pressure_delta_1h * 100)} />
                    </td>
                  </tr>
                  {open && (
                    <tr className="dept-breakdown-row">
                      <td colSpan={6} id={`breakdown-${dept.id}`}>
                        <Breakdown department={dept} weights={weights} />
                      </td>
                    </tr>
                  )}
                </Fragment>
              )
            })}
          </tbody>
        </table>
      </div>
      <p className="table-note">
        For Beds, the queue counts admitted patients waiting for a bed and utilization is bed occupancy.
      </p>
    </section>
  )
}
