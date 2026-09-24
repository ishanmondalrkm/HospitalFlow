import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <section className="panel soon" aria-labelledby="notfound-title">
      <h1 id="notfound-title" className="soon__title">
        Page not found
      </h1>
      <p>There is no page at this address. The overview is the place to start.</p>
      <p>
        <Link to="/">Go to the overview</Link>
      </p>
    </section>
  )
}
