import { Navigate, Outlet } from 'react-router-dom'
import Layout from './Layout'
import { useAuth } from '../context/AuthContext'

export default function ProtectedLayout() {
  const { token, user, checking } = useAuth()
  if (checking) return <div className="auth-loading">Checking session…</div>
  if (!token || !user) return <Navigate to="/login" replace />
  return <Layout />
}
