import { createContext, useContext, useEffect, useMemo, useState } from 'react'

const AuthContext = createContext(null)
const TOKEN_KEY = 'hospitalflow-access-token'
const USER_KEY = 'hospitalflow-user'

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY))
  const [user, setUser] = useState(() => {
    try { return JSON.parse(localStorage.getItem(USER_KEY) || 'null') } catch { return null }
  })
  const [checking, setChecking] = useState(Boolean(token))

  const logout = () => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
    setToken(null)
    setUser(null)
  }

  useEffect(() => {
    const onExpired = () => logout()
    window.addEventListener('hospitalflow-auth-expired', onExpired)
    return () => window.removeEventListener('hospitalflow-auth-expired', onExpired)
  }, [])

  useEffect(() => {
    if (!token) { setChecking(false); return }
    let cancelled = false
    fetch('/api/auth/me', { headers: { Authorization: `Bearer ${token}`, Accept: 'application/json' } })
      .then(async (response) => {
        if (!response.ok) throw new Error('Session expired')
        return response.json()
      })
      .then((data) => { if (!cancelled) setUser(data) })
      .catch(() => { if (!cancelled) logout() })
      .finally(() => { if (!cancelled) setChecking(false) })
    return () => { cancelled = true }
  }, []) // validate once when the app starts

  const login = async (username, password) => {
    const response = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ username, password }),
    })
    const data = await response.json().catch(() => ({}))
    if (!response.ok) throw new Error(data.detail || 'Unable to sign in.')
    localStorage.setItem(TOKEN_KEY, data.access_token)
    localStorage.setItem(USER_KEY, JSON.stringify(data.user))
    setToken(data.access_token)
    setUser(data.user)
  }

  const value = useMemo(() => ({ token, user, checking, login, logout }), [token, user, checking])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used inside AuthProvider')
  return context
}

export { TOKEN_KEY }
