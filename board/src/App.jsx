import { useCallback, useEffect, useRef, useState } from 'react'
import { Canvas } from '@react-three/fiber'
import { loadIndex, loadRun } from './api.js'
import { regionOf, scoreAt } from './layout.js'
import Scene from './Scene.jsx'
import Results from './Results.jsx'
import ScoreReplay from './ScoreReplay.jsx'

const SPEEDS = [0.5, 1, 2, 4]

function useReplayClock(length, playing, speed, onTick) {
  const [progress, setProgress] = useState(length ? length - 1 : 0)
  const raf = useRef()
  const last = useRef(0)

  useEffect(() => {
    setProgress(length ? length - 1 : 0)
  }, [length])

  useEffect(() => {
    if (!playing) return undefined
    last.current = performance.now()
    const step = (now) => {
      const dt = (now - last.current) / 1000
      last.current = now
      setProgress((p) => {
        const next = p + dt * speed
        if (next >= length - 1) {
          onTick?.(length - 1, true)
          return length - 1
        }
        onTick?.(next, false)
        return next
      })
      raf.current = requestAnimationFrame(step)
    }
    raf.current = requestAnimationFrame(step)
    return () => cancelAnimationFrame(raf.current)
  }, [playing, speed, length, onTick])

  return [progress, setProgress]
}

export default function App() {
  const [index, setIndex] = useState(null)
  const [error, setError] = useState('')
  const [entry, setEntry] = useState(null)
  const [run, setRun] = useState(null)
  const [view, setView] = useState('board')
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState(1)
  const [scrub, setScrub] = useState(null)

  const timeline = run?.timeline || []
  const length = timeline.length
  const [progress, setProgress] = useReplayClock(length, playing, speed, (p, done) => {
    if (done) setPlaying(false)
  })
  const focusIndex = Math.round(scrub ?? progress)

  const refresh = useCallback(() => {
    loadIndex().then(setIndex).catch((e) => setError(String(e.message || e)))
  }, [])

  useEffect(refresh, [refresh])

  const openRun = useCallback(
    async (next) => {
      setEntry(next)
      const data = await loadRun(next)
      setRun(data)
      // Open on the finished board; Replay rewinds and plays it back.
      setProgress(Math.max(0, (data.timeline?.length || 1) - 1))
      setScrub(null)
      setPlaying(false)
    },
    [setProgress],
  )

  useEffect(() => {
    if (index?.runs?.length && !entry) openRun(index.runs[0])
  }, [index, entry, openRun])

  const restart = () => {
    setScrub(null)
    setProgress(-1)
    setPlaying(true)
  }

  const score = scoreAt(timeline, focusIndex)
  const current = timeline[Math.min(length - 1, Math.max(0, focusIndex))]

  return (
    <div className="app">
      <header>
        <div className="brand">
          <h1>Agentic Board</h1>
          <span className="sub">
            {run ? `${run.harness} · ${run.model} · board ${run.board} v${run.board_version}` : 'loading…'}
          </span>
        </div>
        <nav>
          <button className={view === 'board' ? 'on' : ''} onClick={() => setView('board')}>Board</button>
          <button className={view === 'replay' ? 'on' : ''} onClick={() => setView('replay')}>Score replay</button>
          <button className={view === 'results' ? 'on' : ''} onClick={() => setView('results')}>
            Results {index ? `(${index.runs.length})` : ''}
          </button>
          <button onClick={refresh}>Reload</button>
        </nav>
      </header>

      {error ? (
        <div className="error">
          <b>No data to show.</b>
          <p>{error}</p>
        </div>
      ) : view === 'results' ? (
        <Results index={index} current={entry} onOpen={openRun} onReplay={async (e) => { await openRun(e); setView('replay'); restart() }} />
      ) : !run ? (
        <div className="loading">loading run…</div>
      ) : (
        <>
          <div className="stage-area">
            {view === 'board' ? (
              <div className="canvas-wrap">
                <Canvas camera={{ position: [16, 14, 22], fov: 55 }} dpr={[1, 2]}>
                  <Scene
                    timeline={timeline}
                    progress={focusIndex}
                    focusIndex={focusIndex}
                    autoOrbit={!playing}
                    onSelect={(i) => { setPlaying(false); setScrub(i) }}
                  />
                </Canvas>
              </div>
            ) : (
              <ScoreReplay timeline={timeline} progress={focusIndex} />
            )}

            <aside className="hud">
              <div className="score">
                <span className="points">{score.toFixed(1)}</span>
                <span className="of">of {run.final.points}</span>
              </div>
              <dl>
                <dt>Stage reached</dt>
                <dd>{run.final.stageReached} / {run.final.boardSize}</dd>
                <dt>Stopped at</dt>
                <dd>{run.final.stoppedAt}</dd>
                <dt>First-try rate</dt>
                <dd>{Math.round(run.final.firstTryRate * 100)}%</dd>
                <dt>Feedback uptake</dt>
                <dd>{Math.round(run.final.feedbackUptake * 100)}%</dd>
                <dt>Tools / tokens</dt>
                <dd>{run.final.tool_calls} / {run.final.tokens}</dd>
              </dl>
              {current ? (
                <div className="now">
                  <b>{current.index + 1}. {current.name}</b>
                  <span className="region">{regionOf(current.region).label}</span>
                  <span className={current.cleared ? 'verdict pass' : 'verdict fail'}>
                    {current.cleared ? `cleared on attempt ${current.attempts}` : 'failed'}
                    {current.attemptResults?.length
                      ? ` · ${current.attemptResults.map((r) => (r === 'pass' ? '●' : '○')).join(' ')}`
                      : ''}
                  </span>
                  <span className="muted">
                    {current.tool_calls} tool calls · {current.seconds}s
                  </span>
                </div>
              ) : null}
              <ol className="spine">
                {timeline.map((row) => (
                  <li
                    key={row.stage}
                    className={`${row.index === focusIndex ? 'focus' : ''} ${row.cleared ? 'pass' : 'fail'}`}
                    onClick={() => { setPlaying(false); setScrub(row.index) }}
                  >
                    <i style={{ background: regionOf(row.region).color }} />
                    {row.index + 1}. {row.stage}
                    <b>{row.cleared ? `+${row.points}` : '—'}</b>
                  </li>
                ))}
              </ol>
            </aside>
          </div>

          <footer className="transport">
            <button className="play" onClick={() => (playing ? setPlaying(false) : restart())}>
              {playing ? 'Pause' : 'Replay'}
            </button>
            <input
              type="range"
              min={0}
              max={Math.max(0, length - 1)}
              step={0.01}
              value={focusIndex}
              onChange={(e) => { setPlaying(false); setScrub(Number(e.target.value)) }}
            />
            <span className="where">{Math.min(length, focusIndex + 1)} / {length}</span>
            <label>
              speed
              <select value={speed} onChange={(e) => setSpeed(Number(e.target.value))}>
                {SPEEDS.map((s) => <option key={s} value={s}>{s}×</option>)}
              </select>
            </label>
          </footer>
        </>
      )}
    </div>
  )
}
