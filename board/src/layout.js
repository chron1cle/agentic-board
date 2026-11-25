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
  return REGIONS[name] || { label: name || 'Uncharted', color: '#8a8f99', look: '' }
}

/**
 * Place every stage on an ascending helix, grouped by region.
 * Deterministic: the same timeline always produces the same coordinates.
 */
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
  const regions = []
  for (const row of points) {
    const last = regions[regions.length - 1]
    if (last && last.region === row.region) last.rows.push(row)
    else regions.push({ region: row.region, rows: [row] })
  }
  for (const group of regions) {
    const xs = group.rows.map((r) => r.position[0])
    const ys = group.rows.map((r) => r.position[1])
    const zs = group.rows.map((r) => r.position[2])
    group.center = [
      xs.reduce((a, b) => a + b, 0) / xs.length,
      ys.reduce((a, b) => a + b, 0) / ys.length - 1.6,
      zs.reduce((a, b) => a + b, 0) / zs.length,
    ]
    group.meta = regionOf(group.region)
  }
  return { points, regions }
}

/** Where the piece is at continuous progress p (0 = before stage 1). */
export function pieceAt(points, p) {
  if (!points.length) return [0, 0, 0]
  const clamped = Math.max(0, Math.min(points.length - 1, p))
  const low = Math.floor(clamped)
  const high = Math.min(points.length - 1, low + 1)
  const t = clamped - low
  const a = points[low].position
  const b = points[high].position
  return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t + 1.1, a[2] + (b[2] - a[2]) * t]
}

/** Cumulative score at continuous progress p, for the animated readout.
 *  p is the piece position: stage i is resolved once p >= i, and before the
 *  first stage the score is 0. */
export function scoreAt(timeline, p) {
  if (!timeline.length) return 0
  const at = (i) => (i < 0 ? 0 : timeline[Math.min(i, timeline.length - 1)].cumulative)
  const clamped = Math.max(-1, Math.min(timeline.length - 1, p))
  const low = Math.floor(clamped)
  return at(low) + (at(low + 1) - at(low)) * (clamped - low)
}
