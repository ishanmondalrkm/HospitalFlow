export default function ResourcesPanel({ resources }) {
  const { beds, staff } = resources
  const occupiedShare = beds.total ? (beds.occupied / beds.total) * 100 : 0

  return (
    <aside className="resources" aria-label="Resources">
      <section className="panel resource" aria-labelledby="beds-title">
        <h2 id="beds-title" className="resource__title">
          Beds
        </h2>
        <p className="resource__figure">
          <span className="resource__big num">{beds.occupied}</span>
          of {beds.total} occupied
        </p>
        <div
          className="bedbar"
          role="img"
          aria-label={`${beds.occupied} of ${beds.total} beds occupied, ${beds.availability_pct.toFixed(1)} percent available`}
        >
          <span className="bedbar__occupied" style={{ width: `${occupiedShare}%` }} />
        </div>
        <dl className="facts">
          <div className="facts__row">
            <dt>Available</dt>
            <dd className="num">
              {beds.available} ({beds.availability_pct.toFixed(1)}%)
            </dd>
          </div>
          <div className="facts__row">
            <dt>Waiting for a bed</dt>
            <dd className="num">{beds.boarding}</dd>
          </div>
          <div className="facts__row">
            <dt>Held by pending discharges</dt>
            <dd className="num">{beds.pending_discharges}</dd>
          </div>
        </dl>
      </section>

      <section className="panel resource" aria-labelledby="staff-title">
        <h2 id="staff-title" className="resource__title">
          Staff
        </h2>
        <p className="resource__note">On duty against the roster, and the share of the last hour spent working.</p>
        <ul className="staff-list">
          {staff.map((row) => {
            const short = row.on_duty < row.planned
            const share = Math.round(row.utilization * 100)
            return (
              <li className="staff-row" key={row.department_id}>
                <div>
                  <span className="staff-row__name">{row.name}</span>
                  <span className={`staff-row__roster${short ? ' is-short' : ''}`}>
                    {short
                      ? `${row.on_duty} of ${row.planned} on duty, ${row.planned - row.on_duty} short`
                      : `${row.on_duty} of ${row.planned} on duty`}
                  </span>
                </div>
                <span className="meter meter--neutral" role="img" aria-label={`${share} percent in use`}>
                  <span className="meter__fill" style={{ width: `${Math.min(100, share)}%` }} />
                </span>
                <span className="num staff-row__share">{share}%</span>
              </li>
            )
          })}
        </ul>
      </section>
    </aside>
  )
}
