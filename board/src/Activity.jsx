const number = new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 })

function Metric({ label, value, suffix = '' }) {
  return (
    <div className="activity-metric">
      <dt>{label}</dt>
      <dd>{value == null ? '—' : number.format(value) + suffix}</dd>
    </div>
  )
}

export default function Activity({ activity, frame, reducedMotion }) {
  if (!frame.row) return null
  const { attempt, fraction, checking, stage, total, checks } = activity
  const working = frame.attempting && !checking && attempt?.started !== false
  const title = frame.resolved ? 'Stage totals' :
    !frame.arrived ? 'Waiting for arrival' :
      checking ? 'Checking attempt' :
        working ? `Attempt ${attempt?.n ?? frame.attempts.length + 1} in progress` : 'Resolving stage'

  return (
    <section className="activity" aria-label="Replay activity">
      <div className="activity-heading">
        <b>{title}</b>
        {!frame.resolved && frame.arrived && <span>Tool and token counts paced for replay</span>}
      </div>
      {frame.arrived && !frame.resolved && (
        <div className="work-track" aria-hidden="true">
          <div className="work-fill" style={{ width: `${Math.round(fraction * 100)}%` }} />
          {working && !reducedMotion && (
            <div className="work-bars">
              {Array.from({ length: 12 }, (_, i) => (
                <i key={i} style={{ height: `${28 + 69 * Math.abs(Math.sin(fraction * 21 - i * 0.67))}%` }} />
              ))}
            </div>
          )}
        </div>
      )}
      <dl className="activity-metrics">
        <Metric label="Stage tools" value={stage.tools} />
        <Metric label="Stage tokens" value={stage.tokens} />
        <Metric label="Harness time" value={stage.seconds} suffix="s" />
      </dl>
      <div className="activity-summary">
        {checks && <span>Attempt {frame.attempts.length} checks: {checks.passed}/{checks.total} passed</span>}
        <span>Run: {total.tools == null ? '—' : number.format(total.tools)} tools · {total.tokens == null ? '—' : number.format(total.tokens)} tokens</span>
      </div>
    </section>
  )
}
