import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Canvas } from '@react-three/fiber'
import { loadCatalog, loadIndex, loadRun } from './api.js'
import {
  levelLabel, regionOf, replayActivity, replayActivityRows, replayFrame, replayProgress,
  replaySchedule, replaySeconds, resolvedIndex, scoreAt, stageVerdict, worldLocation, worldSelection,
} from './layout.js'
import Scene from './Scene.jsx'
import Results from './Results.jsx'
import RunPicker from './RunPicker.jsx'
import WorldViewer from './WorldViewer.jsx'
import ScoreReplay from './ScoreReplay.jsx'
import SegmentScores from './SegmentScores.jsx'
import Activity from './Activity.jsx'
import { HowToGuide, TestsGuide } from './Guide.jsx'
import { worldTheme } from './worldThemes.js'

const SPEEDS = [0.5, 1, 2, 3, 4, 5, 10]

function useReplayClock(schedule, playing, onFinish) {
  const [progress, setProgress] = useState(0)
  const head = useRef(0)
  const seek = useCallback((position) => {
    head.current = position
    setProgress(position)
  }, [])

  useEffect(() => {
    if (!playing || !schedule.segments.length) return undefined
    let raf
    let previous = performance.now()
    let seconds = replaySeconds(schedule, head.current)
    const step = (now) => {
      seconds += Math.max(0, now - previous) / 1000
      previous = now
      seek(replayProgress(schedule, seconds))
      if (seconds < schedule.seconds) raf = requestAnimationFrame(step)
      else onFinish()
    }
    raf = requestAnimationFrame(step)
    return () => cancelAnimationFrame(raf)
  }, [schedule, playing, seek, onFinish])

  return [progress, seek]
}

function useReducedMotion() {
  const [reduced, setReduced] = useState(() => window.matchMedia('(prefers-reduced-motion: reduce)').matches)
  useEffect(() => {
    const media = window.matchMedia('(prefers-reduced-motion: reduce)')
    const update = (event) => setReduced(event.matches)
    media.addEventListener('change', update)
    return () => media.removeEventListener('change', update)
  }, [])
  return reduced
}

const VIEWS = ["board", "replay", "results", "worlds", "tests", "how-to"]

function viewFromHash() {
  const hash = (window.location.hash || "").replace(/^#\/?/, "")
  return VIEWS.includes(hash) ? hash : "board"
}

export default function App() {
  const [index, setIndex] = useState(null)
  const [error, setError] = useState('')
  const [catalog, setCatalog] = useState(null)
  const [catalogError, setCatalogError] = useState('')
  const [entry, setEntry] = useState(null)
  const [run, setRun] = useState(null)
  const [loadingRun, setLoadingRun] = useState(null)
  const [runError, setRunError] = useState('')
  const requestId = useRef(0)
  const [view, setView] = useState(viewFromHash)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState(1)
  const reducedMotion = useReducedMotion()
  const watching = view === 'board' || view === 'replay'
  const catalogView = ['worlds', 'tests', 'how-to'].includes(view)
  const hud = useRef(null)

  const timeline = run?.timeline || []
  const length = timeline.length
  const pause = useCallback(() => setPlaying(false), [])
  const activityRows = useMemo(() => replayActivityRows(run), [run])
  const schedule = useMemo(() => replaySchedule(activityRows, speed), [activityRows, speed])
  const [progress, seek] = useReplayClock(schedule, playing, pause)
  const frame = replayFrame(timeline, progress)
  const activity = replayActivity(activityRows, frame)
  const selectStage = useCallback((position) => {
    pause()
    seek(position)
  }, [pause, seek])

  const refresh = useCallback(() => {
    loadIndex().then((data) => {
      setIndex(data)
      setError('')
      setRunError('')
    }).catch((e) => setError(String(e.message || e)))
  }, [])

  const refreshCatalog = useCallback(() => {
    loadCatalog().then((data) => {
      setCatalog(data)
      setCatalogError('')
    }).catch((e) => setCatalogError(String(e.message || e)))
  }, [])

  useEffect(refresh, [refresh])
  useEffect(() => {
    if (catalogView && !catalog) refreshCatalog()
  }, [catalogView, catalog, refreshCatalog])

  // The view lives in the URL, so a replay of a specific run is a link you can
  // paste to someone: #/replay
  const go = useCallback((next) => {
    setView(next)
    window.location.hash = `#/${next}`
  }, [])

  useEffect(() => {
    const onHash = () => setView(viewFromHash())
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])

  const openRun = useCallback(async (next, replay = false) => {
    const request = ++requestId.current
    pause()
    setRunError('')
    setLoadingRun(next.run)
    try {
      const data = await loadRun(next)
      if (request !== requestId.current) return
      setEntry(next)
      setRun(data)
      if (hud.current) hud.current.scrollTop = 0
      seek(replay ? -1 : Math.max(0, (data.timeline?.length || 1) - 1))
      setPlaying(replay && Boolean(data.timeline?.length))
    } catch {
      if (request === requestId.current) setRunError(`Could not open “${next.run}”. Choose a run or reload the list.`)
    } finally {
      if (request === requestId.current) setLoadingRun(null)
    }
  }, [pause, seek])

  useEffect(() => {
    if (watching && index?.runs?.length && !entry && !loadingRun && !runError) openRun(index.runs[0])
  }, [watching, index, entry, loadingRun, runError, openRun])

  const chooseFromResults = (picked, replay) => {
    go('board')
    openRun(picked, replay)
  }

  const restart = () => {
    if (hud.current) hud.current.scrollTop = 0
    seek(-1)
    setPlaying(true)
  }

  const score = scoreAt(timeline, progress)
  const resolved = resolvedIndex(progress)
  const complete = resolved >= length - 1
  const cleared = timeline.reduce((count, row, i) => count + Number(i <= resolved && row.cleared), 0)
  const worldScores = entry?.scoreSegments ?? run?.scoreSegments
  const selection = worldSelection(run?.selection ?? entry?.selection, worldScores)
  const current = frame.row
  const location = current && worldLocation(current, worldScores)
  const theme = worldTheme(location?.world)
  const outcome = stageVerdict(current)
  const stoppedLabel = outcome === 'incomplete' ? 'Incomplete · stage clock expired' : 'Run stopped'
  const verdict = frame.resolved
    ? current?.cleared ? `Cleared on attempt ${current.attempts}${current.timedOut ? ' · verified at deadline' : ''}` : stoppedLabel
    : frame.arrived ? 'Attempts in progress' : 'Approaching stage'
  const icon = { pass: '✓', fail: '×', budget_exhausted: '◷', incomplete: '◷', integrity_violation: '!', infrastructure_error: '!' }

  return (
    <div className="app">
      <header>
        <div className="brand">
          <h1>Agentic Board</h1>
          <span className="sub">
            {run ? `${run.harness} · ${run.model} · board ${run.board} v${run.board_version}` : 'Benchmark viewer'}
          </span>
        </div>
        <nav>
          <button className={view === 'board' ? 'on' : ''} onClick={() => go('board')}>Board</button>
          <button className={view === 'replay' ? 'on' : ''} onClick={() => go('replay')}>Score replay</button>
          <button className={view === 'results' ? 'on' : ''} onClick={() => go('results')}>
            Results {index ? `(${index.runs.length})` : ''}
          </button>
          <button className={view === 'worlds' ? 'on' : ''} onClick={() => go('worlds')}>Worlds</button>
          <button className={view === 'tests' ? 'on' : ''} onClick={() => go('tests')}>Tests</button>
          <button className={view === 'how-to' ? 'on' : ''} onClick={() => go('how-to')}>How to</button>
          <button onClick={catalogView ? refreshCatalog : refresh}>Reload</button>
        </nav>
      </header>

      {watching && !error && (
        <RunPicker runs={index?.runs || []} current={entry?.run} loading={loadingRun} error={runError}
          onSelect={openRun} onReplay={restart} />
      )}
      {catalogView ? (
        catalogError ? (
          <div className="error" role="alert"><b>Guide unavailable.</b><p>{catalogError}</p></div>
        ) : catalog ? (
          view === 'worlds' ? <WorldViewer board={catalog.board} reducedMotion={reducedMotion} /> :
            view === 'tests' ? <TestsGuide board={catalog.board} /> : <HowToGuide connectors={catalog.connectors} />
        ) : <div className="loading">Loading guide…</div>
      ) : error ? (
        <div className="error">
          <b>No data to show.</b>
          <p>{error}</p>
        </div>
      ) : view === 'results' ? (
        <Results index={index} current={entry} onOpen={(picked) => chooseFromResults(picked, false)}
          onReplay={(picked) => chooseFromResults(picked, true)} />
      ) : !run ? (
        index?.runs.length === 0 ? (
          <div className="empty"><h2>No saved runs</h2><p>Open <a href="#/how-to">How to</a> to run a benchmark.</p></div>
        ) : !runError && <div className="loading">Loading run…</div>
      ) : (
        <>
          <div className="stage-area">
            {view === 'board' ? (
              <div className="canvas-wrap" style={{ '--sky-top': theme.sky[0], '--sky-bottom': theme.sky[1] }}>
                <Canvas camera={{ position: [16, 14, 22], fov: 55 }} dpr={[1, 2]}>
                  <Scene
                    timeline={timeline}
                    worlds={worldScores}
                    progress={progress}
                    frame={frame}
                    activity={activity}
                    playing={playing}
                    reducedMotion={reducedMotion}
                    onSelect={selectStage}
                  />
                </Canvas>
                {current && (
                  <div className="board-caption" style={{ '--region-color': theme.accent || regionOf(current.region).color }}>
                    <span>{location && `World ${location.world} · `}{regionOf(current.region).label}</span>
                    <b>{levelLabel(current, worldScores)} · {current.name || current.stage}</b>
                  </div>
                )}
              </div>
            ) : (
              <ScoreReplay timeline={timeline} worlds={worldScores} progress={Math.min(length - 1, progress)} />
            )}

            <aside className="hud" ref={hud}>
              <div className="score">
                <span className="points">{score.toFixed(1)}</span>
                <span className="of">of {run.final.points} raw pts</span>
              </div>
              {current ? (
                <div className="now">
                  <b>{levelLabel(current, worldScores)} · {current.name}</b>
                  <span className="region">{regionOf(current.region).label}</span>
                  <span className={`verdict ${frame.resolved ? outcome : 'pending'}`}>
                    {verdict}
                  </span>
                  {frame.arrived && (
                    <div className="attempts" aria-label="Stage attempts">
                      {[0, 1, 2].map((i) => {
                        const result = frame.attempts[i]
                        const status = result || (frame.attempting && i === frame.attempts.length ? 'running' : 'unused')
                        return (
                          <span key={i} className={status} title={status.replaceAll('_', ' ')}>
                            Attempt {i + 1} <b>{icon[result] || '·'}</b>
                          </span>
                        )
                      })}
                    </div>
                  )}
                  {frame.resolved && (
                    <span className="muted">{activity.stage.tools ?? "—"} tool calls · {current.seconds}s</span>
                  )}
                </div>
              ) : null}
              <Activity activity={activity} frame={frame} reducedMotion={reducedMotion} />
              <dl className="run-details">
                {selection && <><dt>Selected run</dt><dd>{selection}</dd></>}
                <dt>{selection ? 'Stages cleared' : 'Stage reached'}</dt>
                <dd>{cleared} / {run.final.selectedStages || run.final.boardSize}</dd>
                <dt>{!complete || ['complete', 'selection_complete'].includes(run.final.stoppedAt) ? 'Result' : 'Stopped at'}</dt>
                <dd>{!complete ? '—' : run.final.stoppedAt === 'complete' ? 'board complete' :
                  run.final.stoppedAt === 'selection_complete' ? 'selection complete' : run.final.stoppedAt}</dd>
                <dt>First-try rate</dt>
                <dd>{Math.round(run.final.firstTryRate * 100)}%</dd>
                <dt>Feedback uptake</dt>
                <dd>{run.final.feedbackTrials ? `${Math.round(run.final.feedbackUptake * 100)}%` : '—'}</dd>
                <dt>Run status</dt>
                <dd>{(run.status || 'archive').replaceAll('_', ' ')}</dd>
              </dl>
              {complete && Boolean(worldScores?.length) && (
                <div className="segment-summary">
                  <b>World scores</b>
                  <SegmentScores segments={worldScores} />
                </div>
              )}
              <ol className="spine">
                {timeline.map((row, i) => (
                  <li key={row.stage}>
                    <button
                      className={`stage-link ${i === frame.index ? 'focus' : ''} ${resolved >= i ? stageVerdict(row) : ''}`}
                      onClick={() => selectStage(i)}
                      aria-current={i === frame.index ? 'step' : undefined}
                    >
                      <i style={{ background: regionOf(row.region).color }} />
                      <span>{levelLabel(row, worldScores)} · {row.name || row.stage}</span>
                      <b>{resolved >= i && row.cleared ? `+${row.points} raw` : '—'}</b>
                    </button>
                  </li>
                ))}
              </ol>
            </aside>
          </div>

          <footer className="transport">
            <button
              className="play"
              onClick={() => playing ? pause() : progress >= length - 1 ? restart() : setPlaying(true)}
              disabled={!length || Boolean(loadingRun)}
            >
              {playing ? 'Ⅱ  Pause' : progress >= length - 1 ? '↻  Replay' : '▶  Play'}
            </button>
            <input
              type="range"
              min={-1}
              max={Math.max(0, length - 1)}
              step={0.01}
              value={Math.min(length - 1, progress)}
              aria-label="Replay position"
              onChange={(e) => selectStage(Number(e.target.value))}
            />
            <span className="where">{length ? frame.index + 1 : 0} / {length}</span>
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
