// Shared layout so the 3D board, the score replay, and the results table all
// agree on where a stage is and what it looks like.

export const REGIONS = {
  'plains-of-edit': { label: 'Plains of Edit', color: '#d9c49a', look: 'tidy scriptorium' },
  'caverns-of-search': { label: 'Caverns of Search', color: '#6f86a6', look: 'lantern-lit tunnels' },
  'the-foundry': { label: 'The Foundry', color: '#d98b4a', look: 'forges and sparks' },
  'labyrinth-of-debug': { label: 'Labyrinth of Debug', color: '#a35d6e', look: 'broken machinery' },
  'spire-of-systems': { label: 'Spire of Systems', color: '#6fa8a1', look: 'interlocking gears' },
  'the-summit': { label: 'The Summit', color: '#b9a7d6', look: 'storm and a single beacon' },
}

export const REGION_ORDER = Object.keys(REGIONS)

export function regionOf(name) {
  return REGIONS[name === 'summit' ? 'the-summit' : name] || { label: name || 'Uncharted', color: '#8a8f99', look: '' }
}

/** Place the stages of an archived run on an ascending helix. */
export function layout(timeline) {
  const points = timeline.map((row, i) => {
    const angle = i * 0.62
    const radius = 9.5
    return {
      ...row,
      index0: i,
      position: [Math.cos(angle) * radius, i * 1.15, Math.sin(angle) * radius],
      angle,
    }
  })
  return points
}

export const ARRIVAL = 0.27
export const RESOLUTION = 0.78
export const FINISH_HOLD = 0.35
const ATTEMPT_END = 0.76

export function resolvedIndex(progress) {
  return Math.floor(progress + (1 - RESOLUTION) + Number.EPSILON)
}

/** The current stage occupies one unit, ending at its zero-based index. */
export function replayFrame(timeline, progress) {
  const index = Math.max(0, Math.min(timeline.length - 1, Math.ceil(progress)))
  const row = timeline[index]
  const phase = progress - index + 1
  const attempts = row?.attemptResults || []
  const visible = phase >= ATTEMPT_END ? attempts.length :
    Math.max(0, Math.floor((phase - ARRIVAL) * attempts.length / (ATTEMPT_END - ARRIVAL)))
  return {
    index,
    row,
    phase,
    arrived: phase >= ARRIVAL,
    resolved: resolvedIndex(progress) >= index,
    attempting: phase >= ARRIVAL && visible < attempts.length,
    attempts: attempts.slice(0, visible),
  }
}

/** The piece hops between islands and waits at the destination during attempts. */
export function pieceAt(points, frame, reducedMotion) {
  if (!points.length) return [0, 0, 0]
  const b = points[frame.index].position
  const a = points[frame.index - 1]?.position || [b[0] + 3, b[1] - 0.7, b[2] - 3]
  const t = Math.max(0, Math.min(1, frame.phase / ARRIVAL))
  const eased = t * t * (3 - 2 * t)
  const hop = reducedMotion ? 0 : Math.sin(Math.PI * t) * 1.15
  return [
    a[0] + (b[0] - a[0]) * eased,
    a[1] + (b[1] - a[1]) * eased + 1.15 + hop,
    a[2] + (b[2] - a[2]) * eased,
  ]
}

export function scoreAt(timeline, progress) {
  return timeline[Math.min(timeline.length - 1, resolvedIndex(progress))]?.cumulative || 0
}

const WORK_SHARE = 0.78
const USAGE_FIELDS = ['tools', 'tokens', 'seconds']

function usage(attempt) {
  return {
    tools: attempt.tools_reported === false ? null : attempt.tools,
    tokens: attempt.tokens_reported === false ? null : attempt.tokens,
    seconds: attempt.s,
  }
}

function addUsage(a, b) {
  return Object.fromEntries(USAGE_FIELDS.map((key) => [
    key, a[key] == null || b[key] == null ? null : a[key] + b[key],
  ]))
}

const ZERO_USAGE = { tools: 0, tokens: 0, seconds: 0 }

export function replayActivityRows(run) {
  let previous = ZERO_USAGE
  const recorded = new Map((run?.stages || []).map((stage) => [stage.id, stage]))
  return (run?.timeline || []).map((row) => {
    const stage = recorded.get(row.stage)
    const totals = {
      tools: stage?.attempts?.some((a) => a.tools_reported === false) ? null : stage?.tool_calls ?? row.tool_calls,
      tokens: stage?.attempts?.some((a) => a.tokens_reported === false) ? null : stage?.tokens ?? row.tokens,
      seconds: stage?.seconds ?? row.seconds,
    }
    const attempts = (row.attemptResults || []).map((_, i, results) => (
      stage?.attempts?.[i] || {
        n: i + 1,
        ...(results.length === 1 ? { ...totals, s: totals.seconds } : {}),
      }
    ))
    const entry = { previous, totals, attempts }
    previous = addUsage(previous, totals)
    return entry
  })
}

/** Map the visual playhead to recorded work seconds plus short visual beats. */
export function replaySchedule(rows, speed = 1) {
  const segments = []
  let progress = -1
  let seconds = 0
  function add(end, duration) {
    segments.push({ from: progress, to: end, start: seconds, end: seconds + duration })
    progress = end
    seconds += duration
  }

  rows.forEach(({ attempts, totals }, i) => {
    const start = i - 1
    const slot = (ATTEMPT_END - ARRIVAL) / Math.max(1, attempts.length)
    const known = attempts.reduce((sum, attempt) => sum + (recordedSeconds(attempt) ?? 0), 0)
    const missing = attempts.filter((attempt) => recordedSeconds(attempt) == null).length
    const fallback = Number.isFinite(totals.seconds) ? Math.max(0, totals.seconds - known) / Math.max(1, missing) : 0.65

    add(start + ARRIVAL, 0.55)
    attempts.forEach((attempt, n) => {
      const begin = start + ARRIVAL + n * slot
      add(begin + slot * WORK_SHARE, (recordedSeconds(attempt) ?? fallback) / speed)
      add(begin + slot, 0.24)
    })
    add(start + RESOLUTION, 0.06)
    add(i, 0.65)
  })
  if (rows.length) add(rows.length - 1 + FINISH_HOLD, 0.35)
  return { segments, seconds, end: progress }
}

function recordedSeconds(attempt) {
  if (attempt.started === false) return 0
  return Number.isFinite(attempt.s) ? Math.max(0, attempt.s) : null
}

export function replaySeconds(schedule, progress) {
  const segment = schedule.segments.find(({ to }) => progress <= to)
  if (!segment) return schedule.seconds
  const fraction = Math.max(0, (progress - segment.from) / (segment.to - segment.from))
  return segment.start + fraction * (segment.end - segment.start)
}

export function replayProgress(schedule, seconds) {
  // Skip zero-duration work while retaining its attempt and verdict animations.
  const segment = schedule.segments.find(({ end }) => seconds < end)
  if (!segment) return schedule.end
  const fraction = Math.max(0, (seconds - segment.start) / (segment.end - segment.start))
  return segment.from + fraction * (segment.to - segment.from)
}

export function replayActivity(rows, frame) {
  const { previous, totals, attempts } = rows[frame.index] || {
    previous: ZERO_USAGE, totals: ZERO_USAGE, attempts: [],
  }
  const shown = frame.attempts.length
  const attempt = attempts[shown]
  const unit = (frame.phase - ARRIVAL) * attempts.length / (ATTEMPT_END - ARRIVAL)
  const attemptPhase = Math.max(0, Math.min(1, unit - shown))
  const checking = frame.attempting && attempt?.started !== false &&
    attemptPhase >= WORK_SHARE && Boolean(attempt?.checks?.length)
  const fraction = attempt?.started === false ? 0 : Math.min(1, attemptPhase / WORK_SHARE)
  let stage = attempts.slice(0, shown).reduce((sum, record) => addUsage(sum, usage(record)), ZERO_USAGE)
  if (frame.resolved) stage = totals
  else if (frame.attempting && attempt && attempt.started !== false) {
    const current = usage(attempt)
    stage = addUsage(stage, Object.fromEntries(USAGE_FIELDS.map((key) => [
      key, current[key] == null ? null : Math.floor(current[key] * fraction),
    ])))
  }
  const checks = attempts[shown - 1]?.checks
  return {
    attempt, fraction, checking, stage, total: addUsage(previous, stage),
    checks: checks?.length ? { total: checks.length, passed: checks.filter((check) => check.ok).length } : null,
  }
}
