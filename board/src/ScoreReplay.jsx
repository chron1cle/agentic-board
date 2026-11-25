import { useId, useMemo } from 'react'
import { levelLabel, regionOf, resolvedIndex, scoreAt } from './layout.js'

/**
 * Show the recorded score path with completed stages highlighted.
 */
export default function ScoreReplay({ timeline, progress, worlds }) {
  const clipId = useId()
  const W = 900
  const H = 420
  const pad = { l: 56, r: 24, t: 24, b: 56 }
  const max = Math.max(1, ...timeline.map((r) => r.cumulative))
  const innerW = W - pad.l - pad.r
  const innerH = H - pad.t - pad.b
  const step = innerW / Math.max(1, timeline.length)
  const y = (v) => pad.t + innerH - (v / max) * innerH

  const line = useMemo(
    () =>
      timeline
        .map((r, i) => `${pad.l + step * (i + 0.5)},${y(r.cumulative)}`)
        .join(' '),
    [timeline, step],
  )

  const head = Math.max(pad.l, pad.l + step * (progress + 0.5))

  return (
    <div className="replay">
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="xMidYMid meet"
        role="img" aria-label="Cumulative raw points by benchmark level">
        <defs>
          <clipPath id={clipId}>
            <rect x={pad.l - 2} y={0} width={Math.max(0, head - pad.l + 3)} height={H} />
          </clipPath>
        </defs>
        {[0, 0.25, 0.5, 0.75, 1].map((f) => (
          <g key={f}>
            <line x1={pad.l} x2={W - pad.r} y1={y(max * f)} y2={y(max * f)} className="grid" />
            <text x={pad.l - 8} y={y(max * f) + 4} textAnchor="end" className="tick">
              {Math.round(max * f)}
            </text>
          </g>
        ))}

        {timeline.map((row, i) => {
          const passed = resolvedIndex(progress) >= i
          const w = step * 0.52
          const x = pad.l + step * (i + 0.5) - w / 2
          const top = y(row.cumulative)
          const h = Math.max(0, pad.t + innerH - top)
          return (
            <g key={row.stage} className={passed ? 'on' : 'off'}>
              <rect
                x={x}
                y={top}
                width={w}
                height={h}
                rx={3}
                fill={regionOf(row.region).color}
                opacity={passed ? 0.9 : 0.18}
              />
              {passed && row.points > 0 ? (
                <text x={x + w / 2} y={top - 6} textAnchor="middle" className="pts">
                  +{row.points}
                </text>
              ) : null}
              <text x={x + w / 2} y={H - pad.b + 18} textAnchor="middle" className="tick">
                {levelLabel(row, worlds)}
              </text>
            </g>
          )
        })}

        <polyline points={line} className="score-line projected" />
        <polyline points={line} className="score-line" clipPath={`url(#${clipId})`} />
        <line x1={head} x2={head} y1={pad.t - 8} y2={pad.t + innerH} className="playhead" />
        <circle cx={head} cy={y(scoreAt(timeline, progress))} r={5} className="head-dot" />
      </svg>
      <p className="hint">
        The bars and line show cumulative raw points. World scores on the 0–100 scale
        appear in Results and at the end of the replay.
      </p>
    </div>
  )
}
