import { Outlet } from 'react-router-dom'
import LoopRail from './LoopRail'
import LiveStatusBar from './LiveStatusBar'
import UserMenu from './UserMenu'

export default function Layout() {
  return (
    <div className="app">
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <LoopRail />
      <main className="main" id="main" tabIndex={-1}>
        <div className="main__topbar"><LiveStatusBar /><UserMenu /></div>
        <Outlet />
      </main>
    </div>
  )
}
