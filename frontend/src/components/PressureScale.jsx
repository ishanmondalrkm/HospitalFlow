import { useEffect, useState } from 'react'
import { LEVEL_LABEL, toPoints } from '../lib/format'

// The overall pressure score on the same 0-100 scale the backend uses, with the
// real level thresholds drawn as zones. The marker settles into place once on load.
export default function PressureScale({ score, level, delta, thresholds }) {
  const [shown, setShown] = useState(0)
  useEffect(() => {
    const frame = requestAnimationFrame(() => setShown(score))
    return () => cancelAnimationFrame(frame)
  }, [score])

  const zones = [
    { key: 'low', label: 'Low', from: 0, to: thresholds.medium },
    { key: 'medium', label: 'Medium', from: thresholds.medium, to: thresholds.high },
    { key: 'high', label: 'High', from: thresholds.high, to: thresholds.critical },
    { key: 'critical', label: 'Critical', from: thresholds.critical, to: 1 },
  ]
  const change = Math.round(delta * 100)
  const tone = change === 0 ? 'flat' : change > 0 ? 'bad' : 'good'
  const changeText =
    change === 0
      ? 'Unchanged in the last hour'
      : `${change > 0 ? 'Up' : 'Down'} ${Math.abs(change)} ${Math.abs(change) === 1 ? 'point' : 'points'} in the last hour`

  return (
    <div className="scale">
      <div className="scale__head">
        <span>Overall pressure</span>
        <span>
          <strong className="num">{toPoints(score)}</strong> of 100
        </span>
        <span className={`scale__delta scale__delta--${tone}`}>{changeText}</span>
      </div>
      <div className="scale__body">
        <div
          className="scale__track"
          role="img"
          aria-label={`Overall pressure is ${toPoints(score)} out of 100, level ${LEVEL_LABEL[level]}`}
        >
          {zones.map((zone) => (
            <div
              key={zone.key}
              className={`scale__zone scale__zone--${zone.key}`}
              style={{ width: `${(zone.to - zone.from) * 100}%` }}
            />
          ))}
        </div>
        <div className="scale__marker" style={{ left: `${shown * 100}%` }} aria-hidden="true" />
        <div className="scale__labels" aria-hidden="true">
          {zones.map((zone) => (
            <span key={zone.key} className="scale__label" style={{ left: `${zone.from * 100}%` }}>
              {zone.label}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}
