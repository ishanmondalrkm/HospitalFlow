import { useEffect, useState } from 'react'
import { NavLink, useLocation, matchPath } from 'react-router-dom'
import { LOOP } from '../lib/loop'
import { useAuth } from '../context/AuthContext'
import { ROUTE_PERMISSIONS, hasPermission } from '../lib/rbac'

function Logo() {
  return (
    <svg className="rail__logo" viewBox="0 0 32 32" width="30" height="30" aria-hidden="true">
      <rect className="rail__logo-bg" width="32" height="32" rx="7" />
      <path className="rail__logo-line" d="M6 20c4 0 4-8 8-8s4 8 8 8 2-5 4-5" fill="none" strokeWidth="2.5" strokeLinecap="round" />
    </svg>
  )
}

export default function LoopRail() {
  const location = useLocation()
  const { user } = useAuth()
  const [darkMode, setDarkMode] = useState(() => {
    if (typeof window === 'undefined') return false
    return localStorage.getItem('hospitalflow-theme') === 'dark'
  })

  useEffect(() => {
    document.documentElement.dataset.theme = darkMode ? 'dark' : 'light'
    localStorage.setItem('hospitalflow-theme', darkMode ? 'dark' : 'light')
  }, [darkMode])

  return (
    <nav className="rail" aria-label="Main">
      <div className="rail__brand">
        <Logo />
        <div>
          <div className="rail__name">HospitalFlow</div>
          <div className="rail__tagline">Operational decision support</div>
        </div>
      </div>
      <ol className="loop">
        {LOOP.map((step) => {
          const allowedPages = step.pages.filter((page) => !ROUTE_PERMISSIONS[page.to] || hasPermission(user, ROUTE_PERMISSIONS[page.to]))
          if (!allowedPages.length) return null
          const stageIsActive = allowedPages.some((page) => Boolean(matchPath({ path: page.to, end: page.end }, location.pathname)))
          return (
            <li key={step.stage} className={`loop__stage${stageIsActive ? ' is-live' : ''}`}>
              <span className="loop__node" aria-hidden="true" />
              <div className="loop__stage-name">{step.stage}</div>
              <div className="loop__stage-blurb">{step.blurb}</div>
              <ul className="loop__links">
                {allowedPages.map((page) => (
                  <li key={page.to}>
                    <NavLink to={page.to} end={page.end} className={({ isActive }) => `loop__link${isActive ? ' is-active' : ''}`}>
                      <span>{page.label}</span>
                      {!page.ready && <span className="loop__soon">Soon</span>}
                    </NavLink>
                  </li>
                ))}
              </ul>
            </li>
          )
        })}
      </ol>
      <div className="rail__footer">
        <span className="rail__theme-label">{darkMode ? 'Dark mode' : 'Light mode'}</span>
        <button type="button" className={`theme-toggle${darkMode ? ' is-on' : ''}`} role="switch" aria-checked={darkMode} aria-label={`Switch to ${darkMode ? 'light' : 'dark'} mode`} onClick={() => setDarkMode((value) => !value)}>
          <span className="theme-toggle__track" aria-hidden="true"><span className="theme-toggle__thumb" /></span>
          <span className="theme-toggle__icon" aria-hidden="true">{darkMode ? '☾' : '☀'}</span>
        </button>
      </div>
    </nav>
  )
}
