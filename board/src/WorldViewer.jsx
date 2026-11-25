import { useMemo, useState } from 'react'
import { Canvas } from '@react-three/fiber'
import Scene from './Scene.jsx'
import { levelLabel, regionOf } from './layout.js'
import { worldTheme } from './worldThemes.js'

export default function WorldViewer({ board, reducedMotion }) {
  const [selectedWorld, setSelectedWorld] = useState(null)
  const [focused, setFocused] = useState(null)
  const worlds = useMemo(() => {
    const groups = new Map()
    for (const [i, stage] of board.stages.entries()) {
      const world = stage.world ?? 1
      const levels = groups.get(world) || []
      levels.push({ ...stage, stage: stage.id, index: i + 1, world, level: stage.level ?? levels.length + 1 })
      groups.set(world, levels)
    }
    return groups
  }, [board])

  const world = worlds.has(selectedWorld) ? selectedWorld : worlds.keys().next().value
  const stages = worlds.get(world) || []
  const current = stages[focused]
  const theme = worldTheme(world)

  return (
    <main className="world-viewer">
      <header className="world-viewer-toolbar">
        <h2>Explore the worlds</h2>
        <div className="world-viewer-options" role="group" aria-label="Choose a world">
          {[...worlds.keys()].map((number) => (
            <button key={number} aria-pressed={number === world} className={number === world ? 'on' : ''}
              onClick={() => { setSelectedWorld(number); setFocused(null) }}>
              World {number}
            </button>
          ))}
        </div>
      </header>
      <div className="stage-area">
        <div className="canvas-wrap" style={{ '--sky-top': theme.sky[0], '--sky-bottom': theme.sky[1] }}>
          <Canvas key={world} camera={{ fov: 55 }} dpr={[1, 2]} aria-label={`3D view of World ${world}`}>
            <Scene timeline={stages} preview overview={focused == null} frame={{ index: focused ?? 0, phase: 1 }}
              reducedMotion={reducedMotion} onSelect={setFocused} />
          </Canvas>
          <div className="board-caption" style={{ '--region-color': theme.accent || '#e4c994' }}>
            <span>World {world}</span>
            <b>{current ? `${levelLabel(current)} · ${current.name}` : `${stages.length} levels`}</b>
          </div>
        </div>
        <aside className="hud world-sidebar">
          <button className={focused == null ? 'on' : ''} aria-pressed={focused == null}
            onClick={() => setFocused(null)}>
            Show whole world
          </button>
          <p className="muted">Drag to orbit, scroll to zoom, or pick a level to inspect it.</p>
          {current && (
            <div className="now">
              <b>{current.name}</b>
              <span className="region">{regionOf(current.region).label}</span>
              {current.description && <span>{current.description}</span>}
            </div>
          )}
          <ol className="spine">
            {stages.map((stage, index) => (
              <li key={stage.id}>
                <button className={`stage-link ${focused === index ? 'focus' : ''}`}
                  aria-current={focused === index ? 'step' : undefined} onClick={() => setFocused(index)}>
                  <i style={{ background: theme.accent || regionOf(stage.region).color }} />
                  <span>{levelLabel(stage)} · {stage.name}</span>
                </button>
              </li>
            ))}
          </ol>
        </aside>
      </div>
    </main>
  )
}
