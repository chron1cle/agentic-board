import { useMemo, useRef } from 'react'
import { useFrame, useThree } from '@react-three/fiber'
import { Html, Line, OrbitControls, Stars } from '@react-three/drei'
import * as THREE from 'three'
import { layout, pieceAt, regionOf } from './layout.js'

const STATE_STYLE = {
  cleared: { color: '#7fe3a1', emissive: 1.0 },
  failed: { color: '#e2604f', emissive: 0.6 },
  unplayed: { color: '#59606b', emissive: 0.05 },
  locked: { color: '#2c313a', emissive: 0.0 },
}

function stateOf(row, progress) {
  const reached = progress >= row.index0
  if (!reached) return 'locked'
  if (row.cleared) return 'cleared'
  return 'failed'
}

function AttemptCrystals({ row }) {
  // Three crystals beside the piece: the three attempts, lit by their verdict.
  const attempts = row.attemptResults || []
  return (
    <group position={[1.5, 0.9, 0]}>
      {[0, 1, 2].map((i) => {
        const verdict = attempts[i]
        const color = verdict === 'pass' ? '#7fe3a1' : verdict ? '#e2604f' : '#3a4048'
        return (
          <mesh key={i} position={[i * 0.55, 0, 0]}>
            <tetrahedronGeometry args={[0.16, 0]} />
            <meshStandardMaterial color={color} emissive={color} emissiveIntensity={verdict ? 0.8 : 0.05} />
          </mesh>
        )
      })}
    </group>
  )
}

function StageNode({ row, progress, focus, onSelect }) {
  const ref = useRef()
  const state = stateOf(row, progress)
  const style = STATE_STYLE[state]
  const region = regionOf(row.region)
  const base = row.cleared ? region.color : style.color

  useFrame(({ clock }) => {
    if (!ref.current) return
    const pulse = focus ? 1 + Math.sin(clock.elapsedTime * 3) * 0.08 : 1
    ref.current.scale.setScalar(pulse)
    ref.current.rotation.y += focus ? 0.01 : 0.002
  })

  const geometry = row.cleared ? <octahedronGeometry args={[0.85, 0]} /> : <boxGeometry args={[1.1, 1.1, 1.1]} />

  return (
    <group position={row.position}>
      <mesh
        ref={ref}
        onClick={(e) => {
          e.stopPropagation()
          onSelect(row.index0)
        }}
        rotation={row.cleared ? [0, 0, 0] : [0.2, 0.4, 0.1]}
      >
        {geometry}
        <meshStandardMaterial
          color={base}
          emissive={base}
          emissiveIntensity={style.emissive}
          roughness={0.35}
          metalness={0.35}
          transparent
          opacity={state === 'locked' ? 0.35 : 1}
        />
      </mesh>
      {state === 'locked' ? null : (
        <mesh position={[0, -0.85, 0]}>
          <cylinderGeometry args={[0.9, 1.1, 0.3, 6]} />
          <meshStandardMaterial color={region.color} roughness={0.8} opacity={0.85} transparent />
        </mesh>
      )}
      {focus ? (
        <Html center distanceFactor={22} position={[0, 1.6, 0]} className="node-label">
          <div className={row.cleared ? 'label cleared' : 'label failed'}>
            <b>{row.index0 + 1}. {row.stage}</b>
            <span>
              {row.cleared ? `+${row.points} pts · ${row.attempts} attempt(s)` : 'stage failed'}
            </span>
          </div>
        </Html>
      ) : null}
      {focus ? <AttemptCrystals row={row} /> : null}
    </group>
  )
}

function RegionPlatform({ group }) {
  const width = 7 + group.rows.length * 1.5
  return (
    <group position={group.center}>
      <mesh position={[0, -0.6, 0]}>
        <cylinderGeometry args={[width / 2, width / 2 + 0.6, 1.0, 7]} />
        <meshStandardMaterial color={group.meta.color} roughness={0.9} metalness={0.05} transparent opacity={0.5} />
      </mesh>
      <Html center position={[0, -1.9, 0]} distanceFactor={40} className="region-label">
        <div className="label region">{group.meta.label}</div>
      </Html>
    </group>
  )
}

function Piece({ position }) {
  const ref = useRef()
  useFrame(({ clock }) => {
    if (ref.current) ref.current.position.y = position[1] + 0.25 + Math.sin(clock.elapsedTime * 2) * 0.12
  })
  return (
    <group ref={ref} position={position}>
      <mesh>
        <icosahedronGeometry args={[0.42, 1]} />
        <meshStandardMaterial color="#ffe9a8" emissive="#ffcf5c" emissiveIntensity={1.6} />
      </mesh>
      <pointLight color="#ffd479" intensity={12} distance={9} decay={2} />
    </group>
  )
}

function CameraRig({ focusPosition, controls }) {
  const { camera } = useThree()
  const target = useMemo(() => new THREE.Vector3(), [])
  const desired = useMemo(() => new THREE.Vector3(), [])
  useFrame(() => {
    target.lerp(new THREE.Vector3(...focusPosition), 0.06)
    if (controls.current) controls.current.target.copy(target)
    desired.set(target.x * 1.45 + 6, target.y + 7.5, target.z * 1.45 + 10)
    camera.position.lerp(desired, 0.04)
    camera.lookAt(target)
  })
  return null
}

export default function Scene({ timeline, progress, focusIndex, onSelect, autoOrbit }) {
  const { points, regions } = useMemo(() => layout(timeline), [timeline])
  const controls = useRef()
  const focusRow = points[Math.min(points.length - 1, Math.max(0, focusIndex))]
  const piecePos = pieceAt(points, progress)
  const pathPoints = points.map((p) => p.position)

  return (
    <>
      <color attach="background" args={['#0a0d14']} />
      <fog attach="fog" args={['#0a0d14', 26, 78]} />
      <ambientLight intensity={0.45} />
      <directionalLight position={[12, 22, 8]} intensity={1.1} color="#cfe0ff" />
      <hemisphereLight args={['#4a5f8a', '#120d0a', 0.5]} />
      <Stars radius={90} depth={40} count={1800} factor={3.5} fade speed={0.4} />

      {pathPoints.length > 1 ? (
        <Line points={pathPoints} color="#46536b" lineWidth={1.5} dashed dashSize={0.5} gapSize={0.3} />
      ) : null}

      {regions.map((group) => (
        <RegionPlatform key={group.region + group.rows[0].index0} group={group} />
      ))}

      {points.map((row) => (
        <StageNode
          key={row.stage}
          row={row}
          progress={progress}
          focus={row.index0 === focusIndex}
          onSelect={onSelect}
        />
      ))}

      <Piece position={piecePos} />
      <CameraRig focusPosition={piecePos} controls={controls} />
      <OrbitControls ref={controls} enablePan={false} autoRotate={autoOrbit} autoRotateSpeed={0.35} minDistance={6} maxDistance={60} />
    </>
  )
}
