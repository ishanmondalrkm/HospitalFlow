import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (event) => {
    event.preventDefault()
    setError('')
    setBusy(true)
    try {
      await login(username, password)
      navigate('/', { replace: true })
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="login-page">
      <section className="login-card" aria-labelledby="login-title">
        <div className="login-brand"><span className="login-mark" aria-hidden="true">HF</span><span>HospitalFlow</span></div>
        <div className="login-heading">
          <p className="eyebrow">Operational decision support</p>
          <h1 id="login-title">Sign in</h1>
          <p>Access the hospital operations workspace.</p>
        </div>
        <form className="login-form" onSubmit={submit}>
          <label>Username<input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required /></label>
          <label>Password<input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required /></label>
          {error && <div className="login-error" role="alert">{error}</div>}
          <button className="login-submit" type="submit" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button>
        </form>
        <div className="login-demo">
          <strong>Demo accounts</strong>
          <span>admin / admin123</span>
          <span>manager / manager123</span>
          <span>viewer / viewer123</span>
        </div>
        <p className="login-footnote">Demo credentials are for local development only. Production deployments should disable demo seeding and set a strong authentication secret.</p>
      </section>
    </main>
  )
}
