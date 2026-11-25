import { useMemo, useState } from 'react'
import { regionOf } from './layout.js'

const COLUMNS = [
  { key: 'harness', label: 'Harness', get: (r) => r.harness },
  { key: 'model', label: 'Model', get: (r) => r.model },
  { key: 'stageReached', label: 'Stage', get: (r) => `${r.stageReached}/${r.boardSize}`, num: (r) => r.stageReached },
  { key: 'points', label: 'Points', get: (r) => r.points, num: (r) => r.points },
  { key: 'firstTryRate', label: 'First-try', get: (r) => `${Math.round(r.firstTryRate * 100)}%`, num: (r) => r.firstTryRate },
  { key: 'feedbackUptake', label: 'Uptake', get: (r) => `${Math.round(r.feedbackUptake * 100)}%`, num: (r) => r.feedbackUptake },
  { key: 'stoppedAt', label: 'Stopped at', get: (r) => r.stoppedAt },
  { key: 'toolCalls', label: 'Tools', get: (r) => r.toolCalls, num: (r) => r.toolCalls },
  { key: 'seconds', label: 'Time', get: (r) => `${Math.round(r.seconds)}s`, num: (r) => r.seconds },
  { key: 'tokens', label: 'Tokens', get: (r) => r.tokens, num: (r) => r.tokens },
]

/** Tiny step chart so a row shows its shape, not just its total. */
function Sparkline({ timeline, width = 120, height = 26 }) {
  const max = Math.max(1, ...timeline.map((r) => r.cumulative))
  const pts = timeline
    .map((r, i) => `${(i / Math.max(1, timeline.length - 1)) * width},${height - (r.cumulative / max) * height}`)
    .join(' ')
  return (
    <svg width={width} height={height} className="spark">
      <polyline points={pts} />
    </svg>
  )
}

export default function Results({ index, current, onOpen, onReplay }) {
  const [sort, setSort] = useState({ key: 'stageReached', dir: -1 })

  const runs = useMemo(() => {
    const col = COLUMNS.find((c) => c.key === sort.key) || COLUMNS[2]
    const get = col.num || ((r) => String(col.get(r)))
    return [...(index?.runs || [])].sort((a, b) => {
      const x = get(a)
      const y = get(b)
      if (x === y) return 0
      return (x > y ? 1 : -1) * sort.dir
    })
  }, [index, sort])

  const click = (key) =>
    setSort((s) => (s.key === key ? { key, dir: -s.dir } : { key, dir: -1 }))

  if (!index) return <div className="loading">loading runs…</div>
  if (!runs.length) {
    return (
      <div className="empty">
        <h2>No runs yet</h2>
        <p>
          Play the board once and it will appear here:
          <code>python3 -m engine run --harness fake</code>
        </p>
      </div>
    )
  }

  return (
    <div className="results">
      <table>
        <thead>
          <tr>
            <th className="rank">#</th>
            {COLUMNS.map((c) => (
              <th key={c.key} onClick={() => click(c.key)} className={sort.key === c.key ? 'sorted' : ''}>
                {c.label}
                {sort.key === c.key ? (sort.dir === -1 ? ' ▾' : ' ▴') : ''}
              </th>
            ))}
            <th>Shape</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((row, i) => (
            <tr key={row.run} className={current?.run === row.run ? 'current' : ''}>
              <td className="rank">{i + 1}</td>
              {COLUMNS.map((c) => (
                <td key={c.key} className={c.num ? 'num' : ''}>
                  {c.get(row)}
                </td>
              ))}
              <td>
                <Sparkline timeline={row.timeline || []} />
              </td>
              <td className="actions">
                <button onClick={() => onOpen(row)}>Board</button>
                <button className="primary" onClick={() => onReplay(row)}>
                  ▶ Replay
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="legend">
        {[...new Set(runs.flatMap((r) => (r.timeline || []).map((t) => t.region)))].map((region) => (
          <span key={region}>
            <i style={{ background: regionOf(region).color }} /> {regionOf(region).label}
          </span>
        ))}
      </div>
      <p className="hint">
        Sorting is per column. <b>Stage</b> is the headline metric: the highest stage cleared,
        because a failed stage ends the run. <b>First-try</b> is the share of cleared stages won on
        attempt one; <b>Uptake</b> is how often a failed attempt turned into a pass on the next try.
      </p>
    </div>
  )
}
