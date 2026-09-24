import { useEffect, useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'


const stages = [
  ['MONITOR', 'See hospital flow, pressure, queues, utilisation and alerts.'],
  ['PREDICT', 'Forecast where operational pressure is heading next.'],
  ['EXPLAIN', 'Identify the bottlenecks and factors driving pressure.'],
  ['SIMULATE', 'Test operational scenarios before changing the plan.'],
  ['DECIDE', 'Turn modeled evidence into clearer operational decisions.'],
]

const features = [
  ['Operational overview', 'A connected view of pressure, queues, waiting time, utilisation, staffing and bed availability.'],
  ['Hospital flow', 'Visualise how pressure can move between departments instead of viewing each department in isolation.'],
  ['Forecasting', 'Project near-term pressure, queue and waiting-time changes across multiple horizons.'],
  ['Bottleneck explanation', 'Break pressure into interpretable contributors such as queue, utilisation, arrivals and resource constraints.'],
  ['Simulation lab', 'Change operational inputs and compare projected outcomes before acting on the live system.'],
  ['Decision insights', 'Review modeled intervention scenarios, projected effects and operational trade-offs.'],
]

function ProductMark() {
  return <span className="landing-mark" aria-hidden="true">HF</span>
}

function ThemeToggle() {
  const [darkMode, setDarkMode] = useState(() => {
    if (typeof window === 'undefined') return false
    return localStorage.getItem('hospitalflow-theme') === 'dark'
  })

  useEffect(() => {
    document.documentElement.dataset.theme = darkMode ? 'dark' : 'light'
    localStorage.setItem('hospitalflow-theme', darkMode ? 'dark' : 'light')
  }, [darkMode])

  return (
    <button
      type="button"
      className={`landing-theme-toggle${darkMode ? ' is-on' : ''}`}
      role="switch"
      aria-checked={darkMode}
      aria-label={`Switch to ${darkMode ? 'light' : 'dark'} mode`}
      onClick={() => setDarkMode((value) => !value)}
    >
      <span>{darkMode ? 'Dark' : 'Light'}</span>
      <span className="landing-theme-toggle__track" aria-hidden="true">
        <span className="landing-theme-toggle__thumb" />
      </span>
      <span aria-hidden="true">{darkMode ? '☾' : '☀'}</span>
    </button>
  )
}

export function HomeGate() {
  const { token, user, checking } = useAuth()
  if (checking) return <div className="auth-loading">Checking session…</div>
 if (token && user) return <Navigate to="/dashboard" replace />
  return <Landing />
}

export default function Landing() {
  const navigate = useNavigate()

  return (
    <main className="landing-page">
      <section className="landing-shell" aria-labelledby="landing-title">
        <header className="landing-header">
          <div className="landing-brand">
            <ProductMark />
            <div>
              <div className="landing-name">HospitalFlow</div>
              <div className="landing-tagline">Hospital operations intelligence</div>
            </div>
          </div>
          <div className="landing-header-actions">
            <ThemeToggle />
            <button type="button" className="landing-signin landing-signin--outline" onClick={() => navigate('/login')}>
              Sign in
            </button>
          </div>
        </header>

        <div className="landing-hero">
          <div className="landing-hero__copy">
            <p className="eyebrow">Operational decision support</p>
            <h1 id="landing-title">See hospital operations as a connected system.</h1>
            <p className="landing-hero__lead">
              HospitalFlow brings operational data, forecasting, bottleneck explanation and what-if simulation into one workspace — helping hospital teams understand what is happening now, what may happen next and what could change the outcome.
            </p>
            <div className="landing-actions">
              <button type="button" className="landing-signin" onClick={() => navigate('/login')}>
                Enter HospitalFlow
              </button>
              <span className="landing-note">Monitor → Predict → Explain → Simulate → Decide</span>
            </div>
            <div className="landing-hero__microstats" aria-label="HospitalFlow principles">
              <div><strong>Connected</strong><span>Across hospital operations</span></div>
              <div><strong>Predictive</strong><span>Not just retrospective</span></div>
              <div><strong>Scenario-based</strong><span>Before operational action</span></div>
            </div>
          </div>

          <div className="landing-hero__panel" aria-label="HospitalFlow workflow">
            <div className="landing-panel-label">The HospitalFlow decision loop</div>
            <div className="landing-loop">
              {stages.map(([title, description], index) => (
                <div className="landing-stage" key={title}>
                  <div className="landing-stage__number">0{index + 1}</div>
                  <div>
                    <strong>{title}</strong>
                    <p>{description}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <section className="landing-section" aria-labelledby="why-title">
          <div className="landing-section__heading">
            <p className="eyebrow">From dashboard to decision support</p>
            <h2 id="why-title">One operational picture, six practical capabilities.</h2>
            <p>HospitalFlow is designed around operational aggregates rather than clinical diagnosis or treatment recommendations.</p>
          </div>
          <div className="landing-feature-grid">
            {features.map(([title, description], index) => (
              <article className="landing-feature" key={title}>
                <span className="landing-feature__number">0{index + 1}</span>
                <h3>{title}</h3>
                <p>{description}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="landing-section landing-section--flow" aria-labelledby="flow-title">
          <div className="landing-flow-card">
            <div>
              <p className="eyebrow">A connected operational model</p>
              <h2 id="flow-title">Pressure does not stop at one department.</h2>
              <p>
                A surge in one part of a hospital can increase downstream workload, waiting times and resource pressure. HospitalFlow is built to make those relationships visible and test how operational changes may propagate through the system.
              </p>
            </div>
            <div className="landing-flow-chain" aria-label="Example operational chain">
              <span>Emergency surge</span><b>→</b><span>Queue pressure</span><b>→</b><span>Diagnostic load</span><b>→</b><span>Bed pressure</span>
            </div>
          </div>
        </section>

        <section className="landing-value" aria-label="HospitalFlow operating principles">
          <div>
            <span className="landing-value__label">LIVE OPERATIONS</span>
            <strong>Current pressure and flow</strong>
            <p>Track operational conditions as the live feed changes.</p>
          </div>
          <div>
            <span className="landing-value__label">FORECASTING</span>
            <strong>See what may happen next</strong>
            <p>Use recent operational patterns to anticipate pressure.</p>
          </div>
          <div>
            <span className="landing-value__label">SCENARIO PLANNING</span>
            <strong>Test decisions before acting</strong>
            <p>Compare modeled scenarios without changing the live system.</p>
          </div>
        </section>

        <section className="landing-cta" aria-label="Enter HospitalFlow">
          <div>
            <p className="eyebrow">Ready to explore the workspace?</p>
            <h2>Start with the operational picture.</h2>
            <p>Sign in to open the HospitalFlow operations workspace.</p>
          </div>
          <button type="button" className="landing-signin" onClick={() => navigate('/login')}>Sign in to HospitalFlow</button>
        </section>

        <footer className="landing-footer">
          <span>HospitalFlow · Operational decision support</span>
          <span>Designed for hospital operations, not clinical diagnosis.</span>
        </footer>
      </section>
    </main>
  )
}
