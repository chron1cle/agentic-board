function runLabel(entry) {
  return [
    entry.run,
    [entry.harness, entry.model].filter(Boolean).join(' / '),
    entry.boardVersion ? `v${entry.boardVersion}` : '',
    entry.boardSize ? `${entry.stageReached}/${entry.boardSize} cleared` : '',
  ].filter(Boolean).join(' · ')
}

export default function RunPicker({ runs, current, loading, error, onSelect, onReplay }) {
  if (!runs.length) return null
  return (
    <section className="run-picker" aria-label="Saved benchmark runs">
      <label className="run-picker-field">
        <span>Saved run</span>
        <select value={loading || current || ''} onChange={(event) => {
          const run = runs.find((entry) => entry.run === event.target.value)
          if (run) onSelect(run)
        }}>
          <option value="" disabled>Choose a saved run</option>
          {runs.map((entry) => <option key={entry.run} value={entry.run}>{runLabel(entry)}</option>)}
        </select>
      </label>
      <button className="primary" onClick={onReplay} disabled={!current || Boolean(loading)}>
        ▶ Replay selected run
      </button>
      {loading && <span className="run-picker-status" role="status">Opening {loading}…</span>}
      {error && <span className="run-picker-status run-picker-error" role="alert">{error}</span>}
    </section>
  )
}
