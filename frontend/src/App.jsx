import { Route, Routes } from 'react-router-dom'
import Overview from './pages/Overview'
import ComingSoon from './pages/ComingSoon'
import Flow from './pages/Flow'
import Forecast from './pages/Forecast'
import Bottlenecks from './pages/Bottlenecks'
import Simulation from './pages/Simulation'
import Insights from './pages/Insights'
import History from './pages/History'
import NotFound from './pages/NotFound'
import { UPCOMING } from './lib/loop'
import ProtectedLayout from './components/ProtectedLayout'
import Login from './pages/Login'
import { HomeGate } from './pages/Landing'
import AccessDenied from './pages/AccessDenied'
import { ROUTE_PERMISSIONS, hasPermission } from './lib/rbac'
import { useAuth } from './context/AuthContext'

export default function App() {
  const { user } = useAuth()
  const can = (path) => !ROUTE_PERMISSIONS[path] || hasPermission(user, ROUTE_PERMISSIONS[path])

  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route index element={<HomeGate />} />
      <Route element={<ProtectedLayout />}>
        <Route path="overview" element={can('/overview') ? <Overview /> : <AccessDenied />} />
        <Route path="dashboard" element={can('/dashboard') ? <Overview /> : <AccessDenied />} />
        <Route path="flow" element={can('/flow') ? <Flow /> : <AccessDenied />} />
        <Route path="history" element={can('/history') ? <History /> : <AccessDenied />} />
        <Route path="forecast" element={can('/forecast') ? <Forecast /> : <AccessDenied />} />
        <Route path="bottlenecks" element={can('/bottlenecks') ? <Bottlenecks /> : <AccessDenied />} />
        <Route path="simulation" element={can('/simulation') ? <Simulation /> : <AccessDenied />} />
        <Route path="insights" element={can('/insights') ? <Insights /> : <AccessDenied />} />
        {Object.keys(UPCOMING)
          .filter((path) => !['/overview', '/dashboard', '/flow', '/history', '/forecast', '/bottlenecks', '/simulation', '/insights'].includes(path))
          .map((path) => (
            <Route key={path} path={path.slice(1)} element={<ComingSoon path={path} />} />
          ))}
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}
