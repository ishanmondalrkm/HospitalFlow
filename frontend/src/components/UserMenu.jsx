import { useAuth } from '../context/AuthContext'

export default function UserMenu() {
  const { user, logout } = useAuth()
  if (!user) return null
  return (
    <div className="user-menu">
      <div><strong>{user.username}</strong><span>{user.role}</span></div>
      <button className="button" type="button" onClick={logout}>Sign out</button>
    </div>
  )
}
