import { useEffect, useRef, useState } from 'react'
import { formatDateTime } from '../lib/format'

function socketUrl() {
  const configured = import.meta.env?.VITE_API_BASE_URL?.replace(/\/$/, '')
  if (configured) {
    return configured.replace(/^http:/, 'ws:').replace(/^https:/, 'wss:') + '/ws/live'
  }
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}/ws/live`
}

export default function LiveStatusBar() {
  const [connection, setConnection] = useState('connecting')
  const [status, setStatus] = useState(null)
  const [lastUpdate, setLastUpdate] = useState(null)
  const socketRef = useRef(null)
  const reconnectRef = useRef(null)
  const mountedRef = useRef(true)

  useEffect(() => {
    mountedRef.current = true

    const connect = () => {
      if (!mountedRef.current) return
      setConnection('connecting')
      const token = localStorage.getItem('hospitalflow-access-token')
      if (!token) { setConnection('disconnected'); return }
      const separator = socketUrl().includes('?') ? '&' : '?'
      const socket = new WebSocket(`${socketUrl()}${separator}token=${encodeURIComponent(token)}`)
      socketRef.current = socket

      socket.onopen = () => setConnection('live')
      socket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data)
          if (message.type === 'connected' || message.type === 'live_status') {
            setStatus(message.status)
          }
          if (message.type === 'live_tick') {
            setLastUpdate(message.data?.timestamp ?? null)
            window.dispatchEvent(new CustomEvent('hospitalflow:live-tick', { detail: message.data }))
          }
          if (message.type === 'live_status') {
            window.dispatchEvent(new CustomEvent('hospitalflow:live-status', { detail: message.status }))
          }
        } catch {
          // Ignore malformed socket messages; the REST API remains the source of truth.
        }
      }
      socket.onclose = () => {
        if (!mountedRef.current) return
        setConnection('disconnected')
        reconnectRef.current = window.setTimeout(connect, 3000)
      }
      socket.onerror = () => setConnection('disconnected')
    }

    connect()
    return () => {
      mountedRef.current = false
      if (reconnectRef.current) window.clearTimeout(reconnectRef.current)
      socketRef.current?.close()
    }
  }, [])

  const live = connection === 'live'
  const hospitalRunning = status?.running
  const displayTime = lastUpdate ?? status?.simulation_time

  return (
    <section className={`live-bar live-bar--${live ? 'live' : 'offline'}`} aria-label="Live hospital feed">
      <div className="live-bar__state">
        <span className="live-bar__dot" aria-hidden="true" />
        <strong>{live ? 'LIVE' : 'OFFLINE'}</strong>
        <span className="live-bar__muted">WebSocket feed</span>
      </div>
      <div className="live-bar__meta">
        <span>{hospitalRunning ? 'Simulator running' : 'Simulator stopped'}</span>
        {displayTime && <span>Hospital time {formatDateTime(displayTime)}</span>}
        {status?.ticks != null && <span className="num">{status.ticks} ticks</span>}
      </div>
    </section>
  )
}
