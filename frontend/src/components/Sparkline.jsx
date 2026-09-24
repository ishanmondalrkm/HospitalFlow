const WIDTH = 104
const HEIGHT = 32
const PAD = 3

export default function Sparkline({ values, tone = 'neutral', label }) {
  if (!values || values.length < 2) return null
  const min = Math.min(...values)
  const max = Math.max(...values)
  const span = max - min
  const x = (i) => PAD + (i / (values.length - 1)) * (WIDTH - PAD * 2)
  const y = (v) => {
    const t = span === 0 ? 0.5 : (v - min) / span // a flat series sits in the middle
    return HEIGHT - PAD - t * (HEIGHT - PAD * 2)
  }
  const points = values.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ')
  const last = values.length - 1
  return (
    <svg
      className="sparkline"
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      width={WIDTH}
      height={HEIGHT}
      role="img"
      aria-label={label ?? `Trend over the last ${values.length} hours`}
    >
      <polyline
        className="sparkline__line"
        points={points}
        fill="none"
        strokeWidth="1.5"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      <circle className={`sparkline__dot sparkline__dot--${tone}`} cx={x(last)} cy={y(values[last])} r="2.5" />
    </svg>
  )
}
