import { useMemo, useState } from 'react'
import SegmentScores from './SegmentScores.jsx'
import { regionOf, worldSelection } from './layout.js'

const STATUS = {
  archive: 'Archived runs',
  control: 'Control runs',
  partial: 'Partial runs',
  telemetry_incomplete: 'Runs without tool accounting',
  infrastructure_error: 'Infrastructure errors',
  integrity_violation: 'Disqualified runs',
}

function cohortOf(run) {
  return JSON.stringify([run.board, run.boardVersion, run.seed, run.schema, run.status, run.selection || null])
}

const COLUMNS = [
  { key: 'harness', label: 'Harness', get: (r) => r.harness },
  { key: 'model', label: 'Model', get: (r) => r.model },
  { key: 'stageReached', label: 'Cleared', get: (r) => `${r.stageReached}/${r.selectedStages || r.boardSize}`, num: (r) => r.stageReached },
  { key: 'points', label: 'Points', get: (r) => r.points, num: (r) => r.points },
  { key: 'firstTryRate', label: 'First-try', get: (r) => `${Math.round(r.firstTryRate * 100)}%`, num: (r) => r.firstTryRate },
  { key: 'feedbackUptake', label: 'Uptake', get: (r) => r.feedbackTrials ? `${Math.round(r.feedbackUptake * 100)}% (${r.feedbackTrials})` : '—', num: (r) => r.feedbackTrials ? r.feedbackUptake : -1 },
  { key: 'stoppedAt', label: 'Stopped at', get: (r) => r.stoppedAt },
  { key: 'toolCalls', label: 'Tools', get: (r) => r.toolsReported === false ? '—' : r.toolCalls, num: (r) => r.toolsReported === false ? -1 : r.toolCalls },
  { key: 'seconds', label: 'Time', get: (r) => `${Math.round(r.seconds)}s`, num: (r) => r.seconds },
  { key: 'tokens', label: 'Tokens', get: (r) => r.tokensReported === false ? '—' : r.tokens, num: (r) => r.tokensReported === false ? -1 : r.tokens },
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

  const [selected, setSelected] = useState(null)
  const cohorts = new Map()
  for (const run of index?.runs || []) {
    const key = cohortOf(run)
    if (!cohorts.has(key)) cohorts.set(key, run)
  }
  const currentCohort = current && cohortOf(current)
  const cohort = cohorts.has(selected) ? selected : cohorts.has(currentCohort) ? currentCohort :
    [...cohorts].find(([, run]) => run.status === 'benchmark')?.[0] ||
    cohorts.keys().next().value
  const ranked = cohorts.get(cohort)?.status === 'benchmark'

  const runs = useMemo(() => {
    const col = COLUMNS.find((c) => c.key === sort.key) || COLUMNS[2]
    const get = col.num || ((r) => String(col.get(r)))
    return (index?.runs || []).filter((run) => cohortOf(run) === cohort).sort((a, b) => {
      const x = get(a)
      const y = get(b)
      if (x === y) return 0
      return (x > y ? 1 : -1) * sort.dir
    })
  }, [index, sort, cohort])

  const click = (key) =>
    setSort((s) => (s.key === key ? { key, dir: -s.dir } : { key, dir: -1 }))

  if (!index) return <div className="loading">loading runs…</div>
  if (!runs.length) {
    return (
      <div className="empty">
        <h2>No completed runs</h2>
        <p>Reload once a benchmark finishes, or open <a href="#/how-to">How to</a> for setup.</p>
      </div>
    )
  }

  return (
    <div className="results">
      <div className="results-heading">
        <div>
          <h2>Saved results</h2>
          <p>Choose <strong>View</strong> to inspect a finished run or <strong>Replay</strong> to play it from the start.</p>
        </div>
        <label>
          Comparison group
          <select value={cohort} onChange={(event) => setSelected(event.target.value)}>
            {[...cohorts].map(([key, run]) => (
              <option key={key} value={key}>
                {run.board} v{run.boardVersion} · seed {run.seed} · {STATUS[run.status] || 'Benchmark runs'}
                {run.selection ? ` · ${worldSelection(run.selection, run.scoreSegments)}` : ''}
              </option>
            ))}
          </select>
        </label>
      </div>
      <table>
        <thead>
          <tr>
            {ranked && <th className="rank">#</th>}
            <th scope="col">Run</th>
            <th scope="col">Open run</th>
            {COLUMNS.map((c) => (
              <th key={c.key} onClick={() => click(c.key)} className={sort.key === c.key ? 'sorted' : ''}>
                {c.label}
                {sort.key === c.key ? (sort.dir === -1 ? ' ▾' : ' ▴') : ''}
              </th>
            ))}
            <th scope="col">World scores</th>
            <th>Shape</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((row, i) => (
            <tr key={row.run} className={current?.run === row.run ? 'current' : ''}>
              {ranked && <td className="rank">{i + 1}</td>}
              <th scope="row" className="result-id">
                <span className="result-id-name" title={row.run}>{row.run}</span>
                {current?.run === row.run && <span className="result-current">Selected</span>}
              </th>
              <td><div className="actions">
                <button onClick={() => onOpen(row)} aria-label={`View ${row.run}`}>View</button>
                <button className="primary" onClick={() => onReplay(row)} aria-label={`Replay ${row.run}`}>
                  ▶ Replay
                </button>
              </div></td>
              {COLUMNS.map((c) => (
                <td key={c.key} className={c.num ? 'num' : ''}>
                  {c.get(row)}
                </td>
              ))}
              <td>
                <SegmentScores segments={row.scoreSegments} />
              </td>
              <td>
                <Sparkline timeline={row.timeline || []} />
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
        Each world is scored out of 100. Every level in the world contributes equally after
        adjusting for its maximum points. <b>Cleared</b> counts stages passed,
        because a failed stage ends the run. <b>First-try</b> is the share of cleared stages won on
        attempt one; <b>Uptake</b> is how often a failed attempt turned into a pass on the next try.
      </p>
    </div>
  )
}
