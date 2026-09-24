// Says what went wrong and how to fix it, and offers a retry.
export default function ApiErrorNotice({ error, onRetry }) {
  const unreachable = !error?.status
  return (
    <div className="notice" role="alert">
      <h2 className="notice__title">
        {unreachable ? 'Can\u2019t reach the HospitalFlow API' : 'The HospitalFlow API returned an error'}
      </h2>
      <p>
        {unreachable
          ? 'The dashboard needs the backend to be running. Start it from the project root, then try again.'
          : error.message}
      </p>
      {unreachable && (
        <pre className="notice__code">
          <code>uvicorn backend.main:app --reload --port 8000</code>
        </pre>
      )}
      <button type="button" className="button" onClick={onRetry}>
        Try again
      </button>
    </div>
  )
}
