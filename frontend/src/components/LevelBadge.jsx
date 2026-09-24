import { LEVEL_LABEL } from '../lib/format'

// Text plus colour, so the level never depends on colour alone.
// Low stays quiet (no tinted background); Medium and above stand out.
export default function LevelBadge({ level }) {
  return (
    <span className={`badge badge--${level.toLowerCase()}`}>
      <span className="badge__dot" aria-hidden="true" />
      {LEVEL_LABEL[level]}
    </span>
  )
}
