import ApiErrorNotice from '../components/ApiErrorNotice'
import OverviewView from '../components/OverviewView'
import { getDashboard } from '../services/api'
import { useApi } from '../services/useApi'
import { useEffect } from 'react'

export default function Overview() {
  const { status, data, error, reload } = useApi(getDashboard)

  useEffect(() => {
    const handler = () => reload()
    window.addEventListener('hospitalflow:live-tick', handler)
    return () => window.removeEventListener('hospitalflow:live-tick', handler)
  }, [reload])

  if (!data && status === 'error') return <ApiErrorNotice error={error} onRetry={reload} />
  if (!data) {
    return (
      <p className="loading" role="status">
        Loading operational data
      </p>
    )
  }
  // A failed refresh keeps the last good data on screen and says so above it.
  return <OverviewView data={data} onRefresh={reload} refreshing={status === 'loading'} error={error} />
}
