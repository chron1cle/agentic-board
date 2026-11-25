// Data access for the viewer.
//
// The viewer reads run.json and runs/index.json and nothing else. That is on
// purpose: the same file is the score sheet, the replay tape, and the board
// state, so the renderer can never disagree with the scoreboard.

const INDEX_CANDIDATES = ['/runs/index.json', '../../runs/index.json']

let indexBase = null

async function getJson(url) {
  const res = await fetch(url, { cache: 'no-store' })
  if (!res.ok) throw new Error(`${url} -> HTTP ${res.status}`)
  return res.json()
}

export async function loadIndex() {
  const errors = []
  for (const candidate of INDEX_CANDIDATES) {
    try {
      const data = await getJson(candidate)
      indexBase = candidate.replace(/index\.json$/, '')
      return data
    } catch (err) {
      errors.push(err.message)
    }
  }
  throw new Error(
    'No runs/index.json found. Start the server with `python3 -m engine serve` ' +
      'and run a benchmark with `python3 -m engine run`. (' + errors.join('; ') + ')'
  )
}

export async function loadRun(entry) {
  const path = entry.path || `${entry.run}/run.json`
  return getJson(indexBase + path)
}
