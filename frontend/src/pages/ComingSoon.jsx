import { Link } from 'react-router-dom'
import { UPCOMING } from '../lib/loop'

export default function ComingSoon({ path }) {
  const page = UPCOMING[path]
  return (
    <section className="panel soon" aria-labelledby="soon-title">
      <h1 id="soon-title" className="soon__title">
        {page.title}
      </h1>
      <p>{page.description}</p>
      <p className="soon__phase">
        Not built yet. Part of {page.stage}, planned for {page.phase.toLowerCase()}.
      </p>
      <p>
        <Link to="/">Back to the overview</Link>
      </p>
    </section>
  )
}
