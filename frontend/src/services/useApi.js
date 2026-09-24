import { useCallback, useEffect, useState } from 'react'

// Loads data with `loader({ signal })` and exposes { status, data, error, reload }.
// Previous data is kept while reloading or after a failed reload, so a refresh
// never blanks the screen.
export function useApi(loader) {
  const [state, setState] = useState({ status: 'loading', data: null, error: null })
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    setState((previous) => ({ ...previous, status: 'loading', error: null }))
    loader({ signal: controller.signal })
      .then((data) => setState({ status: 'ready', data, error: null }))
      .catch((error) => {
        if (error?.name === 'AbortError') return
        setState((previous) => ({ status: 'error', data: previous.data, error }))
      })
    return () => controller.abort()
  }, [loader, attempt])

  const reload = useCallback(() => setAttempt((n) => n + 1), [])
  return { ...state, reload }
}
