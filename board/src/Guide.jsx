import { useState } from 'react'
import { regionOf } from './layout.js'

const METHODS = {
  file_exact: 'Exact file match',
  file_normalized: 'Normalized text match',
  json_equal: 'JSON structure match',
  diff_budget: 'Changed-line limit',
  command: 'Command check',
  script: 'Scripted checker',
  differential: 'Differential testing',
  mutation: 'Mutation testing',
  timing: 'Timing check',
}

function methodLabel({ kind, maxChangedLines, minKillRate, mutantCount }) {
  if (kind === 'diff_budget') return `≤ ${maxChangedLines} changed lines`
  if (kind === 'mutation') return `Mutation testing · ${minKillRate * 100}% of ${mutantCount} mutants`
  return METHODS[kind] || kind
}

const ROUTING_GROUPS = [
  { id: 'gates', title: 'Switches and gates' },
  { id: 'prices', title: 'Tolls and finishing rules' },
  { id: 'signals', title: 'Switches working together' },
]

function StageCards({ stages }) {
  if (!stages.length) return null
  return (
    <div className="guide-grid">
      {stages.map((stage) => {
        const region = regionOf(stage.region)
        return (
          <article key={stage.id} className="guide-card" style={{ '--card-accent': region.color }}>
            <p className="guide-card-kicker">Stage {stage.number} · {region.label} · Tier {stage.tier}</p>
            {stage.routingGroup ? <h5>{stage.name}</h5> : <h3>{stage.name}</h3>}
            {stage.description && <p>{stage.description}</p>}
            <p className="guide-check-label">How it’s measured</p>
            {stage.measurement && <p>{stage.measurement}</p>}
            <ul className="guide-tags" aria-label="Verification methods">
              {stage.checks.map((check, index) => <li key={index}>{methodLabel(check)}</li>)}
              {stage.seeded && <li>Seeded cases</li>}
            </ul>
            <p className="guide-meta">
              {stage.attempts} attempts · {stage.seconds}s stage clock · {stage.toolBudget} tools per attempt · {stage.basePoints} base points
            </p>
          </article>
        )
      })}
    </div>
  )
}

export function TestsGuide({ board }) {
  const [query, setQuery] = useState('')
  const filter = query.trim().toLowerCase()
  const stages = board.stages
    .map((stage, index) => ({ ...stage, number: index + 1 }))
    .filter((stage) => [
      stage.id, stage.name, regionOf(stage.region).label, stage.description, stage.measurement,
      ...stage.checks.map(methodLabel),
    ].some((field) => field?.toLowerCase().includes(filter)))

  return (
    <main className="guide">
      <div className="guide-heading">
        <div>
          <h2>Benchmark tests</h2>
          <p>Board v{board.version} · {board.stages.length} stages</p>
        </div>
        <label className="guide-search">
          Find a stage
          <input type="search" value={query} onChange={(event) => setQuery(event.target.value)}
            placeholder="Name, region, or check" />
        </label>
      </div>
      <p className="guide-intro">
        Each attempt starts with a fresh workspace and a new harness session. On a retry,
        the harness receives the grader’s feedback from earlier attempts at that stage.
        Earlier edits are discarded. A submission clears the stage when it passes every
        required check. Base points are adjusted for the clearing attempt and tool budget.
      </p>
      <StageCards stages={stages.filter((stage) => !stage.routingGroup)} />
      {stages.some((stage) => stage.routingGroup) && (
        <section className="guide-routing" aria-labelledby="routing-heading">
          <div className="guide-intro">
            <h3 id="routing-heading">Summit routing tests</h3>
            <p>
              Think of a map of toll roads and switches. Each level adds a rule and keeps the
              earlier ones. The program must give the cheapest valid trip, or report that no trip is possible.
            </p>
            <p>
              The agent writes one solver per attempt. After the attempt ends, the grader starts
              the submitted program once and sends it all the hidden maps, one per line. The
              program answers each map in order. The grader compares those answers with an
              independently written solver’s answers to the same maps. This is differential testing.
            </p>
          </div>
          {ROUTING_GROUPS.map(({ id, title }) => {
            const group = stages.filter((stage) => stage.routingGroup === id)
            return group.length > 0 && (
              <section key={id} aria-labelledby={`routing-${id}`}>
                <h4 id={`routing-${id}`} className="guide-section-title">{title}</h4>
                <StageCards stages={group} />
              </section>
            )
          })}
        </section>
      )}
      {!stages.length && <p role="status">No stages match “{query.trim()}”.</p>}
    </main>
  )
}

export function HowToGuide({ connectors }) {
  return (
    <main className="guide">
      <div className="guide-heading">
        <div>
          <h2>Run the benchmark</h2>
          <p>Harness setup, telemetry, and replay</p>
        </div>
      </div>
      <section className="guide-intro">
        <h3>Start a run</h3>
        <p>Install and authenticate the CLI you want to test, then select it from the engine.</p>
        <pre>python3 -m engine run --harness codex --limit 1</pre>
        <p>
          Use <code>--model</code> to choose a model, <code>--only</code> to try a specific stage,
          and <code>--harness-bin</code> to override the executable. Use the same board version
          and seed when comparing full runs.
        </p>
        <h3>Watch the results</h3>
        <p>
          While a run is active, progress appears in the terminal. The viewer opens completed
          run records. When your run ends, choose <strong>Reload</strong>, then open
          <strong> Results</strong> and choose <strong>Replay</strong> for the run.
        </p>
      </section>
      <h3 className="guide-section-title">Harness connectors</h3>
      <div className="guide-grid">
        {connectors.map((item) => (
          <article key={item.id} className="guide-card">
            <h3>{item.label}</h3>
            <p className="guide-meta"><code>--harness {item.id}</code> · {item.executable}</p>
            <p>{item.setup}</p>
            <h4>How it’s wired</h4>
            <p>{item.wiring}</p>
          </article>
        ))}
      </div>
      <section className="guide-intro guide-wrapper">
        <h3>Connect another agent or model</h3>
        <p>
          For DeepSeek and other model providers, configure the provider in a compatible
          harness and select its model. The result measures that harness and model together.
        </p>
        <p>
          For an agent with its own SDK or protocol, supply a one-shot wrapper. The wrapper
          runs in the attempt workspace, reads a JSON request with <code>prompt</code>,{' '}
          <code>model</code>, <code>stage_id</code>, <code>attempt</code>, and{' '}
          <code>timeout_s</code> from stdin, and writes one JSON event per line to stdout.
        </p>
        <pre>python3 -m engine run --harness command --harness-bin /path/to/wrapper</pre>
        <p>Report each tool call and one terminal result containing the attempt’s total tokens.</p>
        <pre>{`{"type":"tool.call","tool":"read","id":"call-1"}
{"type":"result","ok":true,"tokens":145}`}</pre>
        <p>The wrapper stops its agent before exiting. The engine then checks the submitted files.</p>
      </section>
    </main>
  )
}
