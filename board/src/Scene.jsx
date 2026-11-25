import { memo, useLayoutEffect, useMemo, useRef } from 'react'
import { useFrame, useThree } from '@react-three/fiber'
import { Html, Line, OrbitControls, Stars } from '@react-three/drei'
import * as THREE from 'three'
import { RESOLUTION, layout, pieceAt, regionOf, resolvedIndex } from './layout.js'

const GOLD = '#ffd780'
const PASS = '#74efb4'
const FAIL = '#ff796f'
const DARK = '#101620'
const UP = [-Math.PI / 2, 0, 0]

function verdictColor(verdict) {
  if (verdict === 'pass') return PASS
  if (verdict === 'budget_exhausted') return GOLD
  return verdict ? FAIL : '#354052'
}

function OrbitRing({ color, radius, width = 0.025, glow = 1, ...props }) {
  return (
    <mesh rotation={UP} {...props}>
      <torusGeometry args={[radius, width, 6, 48]} />
      <meshStandardMaterial color={color} emissive={color} emissiveIntensity={glow} />
    </mesh>
  )
}

function Attempts({ results, active, reducedMotion }) {
  return (
    <group position={[0, 1.68, 0]}>
      {[0, 1, 2].map((i) => (
        <AttemptCrystal key={i} index={i} verdict={results[i]}
          active={active && i === results.length} reducedMotion={reducedMotion} />
      ))}
    </group>
  )
}

function AttemptCrystal({ index, verdict, active, reducedMotion }) {
  const ref = useRef()
  const color = active ? GOLD : verdictColor(verdict)
  useFrame(({ clock }, delta) => {
    if (reducedMotion) {
      ref.current.scale.setScalar(1)
      return
    }
    const scale = active ? 1 + Math.sin(clock.elapsedTime * 8) * 0.2 : 1
    ref.current.scale.setScalar(scale)
    ref.current.rotation.y += delta * (verdict || active ? 1.8 : 0.5)
  })
  return (
    <mesh ref={ref} position={[(index - 1) * 0.46, 0, 0]}>
      <octahedronGeometry args={[0.13]} />
      <meshStandardMaterial color={color} emissive={color}
        emissiveIntensity={verdict || active ? 1.5 : 0.15} />
    </mesh>
  )
}

const StageIsland = memo(function StageIsland({ row, active, resolved, gateway, onSelect }) {
  const region = regionOf(row.region)
  const color = resolved ? (row.cleared ? PASS : FAIL) : active ? GOLD : region.color
  return (
    <group position={row.position}>
      <group onClick={(event) => { event.stopPropagation(); onSelect(row.index0) }}>
        <mesh position={[0, -0.33, 0]}>
          <cylinderGeometry args={[1.56, 1.36, 0.54, 8]} />
          <meshStandardMaterial color="#263249" metalness={0.55} roughness={0.62} />
        </mesh>
        <mesh position={[0, -1.05, 0]} rotation={[0, Math.PI / 8, 0]}>
          <cylinderGeometry args={[1.35, 0.32, 1.0, 7]} />
          <meshStandardMaterial color={region.color} roughness={0.95}
            emissive={DARK} emissiveIntensity={0.3} />
        </mesh>
        <mesh position={[0, -0.58, 0]}>
          <cylinderGeometry args={[1.4, 1.36, 0.08, 8]} />
          <meshStandardMaterial color={color} emissive={color}
            emissiveIntensity={active || resolved ? 0.65 : 0.14} />
        </mesh>
        <mesh position={[0, 0, 0]}>
          <cylinderGeometry args={[1.28, 1.33, 0.16, 8]} />
          <meshStandardMaterial color={DARK} metalness={0.35} roughness={0.45} />
        </mesh>
      </group>
      <OrbitRing color={color} radius={1.11} position={[0, 0.09, 0]}
        glow={active ? 1.3 : resolved ? 0.7 : 0.16} />
      <OrbitRing color={region.color} radius={0.87} width={0.012}
        position={[0, 0.087, 0]} glow={0.2} />
      <mesh position={[0, 0.19, 0]} rotation={[0, row.angle, 0]}>
        <cylinderGeometry args={[0.44, 0.54, 0.23, 6]} />
        <meshStandardMaterial color={color} emissive={color}
          emissiveIntensity={resolved || active ? 0.65 : 0.13} />
      </mesh>
      {gateway && (
        <group rotation={[0, -row.angle, 0]}>
          {[-1, 1].map((side) => (
            <group key={side} position={[side * 0.9, 0.33, -0.58]}>
              <mesh>
                <cylinderGeometry args={[0.09, 0.18, 0.55, 5]} />
                <meshStandardMaterial color="#344463" metalness={0.45} />
              </mesh>
              <mesh position={[0, 0.32, 0]}>
                <octahedronGeometry args={[0.18]} />
                <meshStandardMaterial color={region.color} emissive={region.color}
                  emissiveIntensity={active ? 1.2 : 0.35} />
              </mesh>
            </group>
          ))}
        </group>
      )}
      {active && <pointLight color={color} position={[0, 0.65, 0]} intensity={3} distance={6} />}
    </group>
  )
})

function Pilot({ position, reducedMotion }) {
  const ref = useRef()
  const rotor = useRef()
  useFrame(({ clock }, delta) => {
    const bob = reducedMotion ? 0 : Math.sin(clock.elapsedTime * 3) * 0.1
    ref.current.position.y = position[1] + bob
    rotor.current.rotation.y += reducedMotion ? 0 : delta * 2.3
  })
  return (
    <group ref={ref} position={position}>
      <mesh>
        <icosahedronGeometry args={[0.4, 0]} />
        <meshStandardMaterial color="#fff3be" emissive="#ffb347" emissiveIntensity={1.9}
          metalness={0.22} roughness={0.28} />
      </mesh>
      <group ref={rotor}>
        <OrbitRing color={GOLD} radius={0.63} rotation={[1.1, 0.15, 0.15]} />
        <OrbitRing color="#f6a651" radius={0.54} rotation={[-0.4, 0.6, 0.15]} />
      </group>
      <pointLight color={GOLD} intensity={7} distance={6} />
    </group>
  )
}

function Burst({ row, age, final }) {
  const scale = 0.65 + age * (final ? 4 : 2.4)
  const color = row.cleared ? (final ? GOLD : PASS) : FAIL
  const opacity = Math.max(0, 1 - age)
  return (
    <group position={row.position}>
      <mesh rotation={UP} position={[0, 0.22, 0]} scale={scale}>
        <torusGeometry args={[1, 0.045, 6, 48]} />
        <meshBasicMaterial color={color} transparent opacity={opacity} depthWrite={false} />
      </mesh>
      {(final ? [0, 1] : [0]).map((ring) => (
        <group key={ring} rotation={[0, ring * 0.45, 0]}>
          {Array.from({ length: 9 }, (_, i) => {
            const angle = i * Math.PI * 2 / 9
            return (
              <mesh key={i} position={[
                Math.cos(angle) * scale,
                0.4 + Math.sin(Math.PI * age) * (1 + (i % 3) * 0.35 + ring),
                Math.sin(angle) * scale,
              ]} rotation={[angle, angle, age * 2]} scale={opacity}>
                <octahedronGeometry args={[0.13]} />
                <meshBasicMaterial color={color} />
              </mesh>
            )
          })}
        </group>
      ))}
    </group>
  )
}

function FollowCamera({ position, controls, reducedMotion }) {
  const target = useRef(new THREE.Vector3())
  const movement = useMemo(() => new THREE.Vector3(), [])
  const { camera } = useThree()
  useLayoutEffect(() => {
    target.current.set(...position)
    controls.current.target.copy(target.current)
    camera.position.copy(target.current).add(new THREE.Vector3(9, 7, 12))
    controls.current.update()
    // The initial view is applied once. Later updates preserve manual orbit and zoom.
  }, [camera, controls])
  useFrame((_, delta) => {
    movement.set(...position).sub(target.current)
      .multiplyScalar(reducedMotion ? 1 : 1 - Math.exp(-7 * delta))
    target.current.add(movement)
    controls.current.target.copy(target.current)
    camera.position.add(movement)
    controls.current.update()
  }, -2)
  return null
}

function WorkOrbit({ row, activity }) {
  const color = activity.checking ? PASS : GOLD
  const rings = activity.checking ? [0.77, 1.05] : [0.77]
  return (
    <group position={row.position}>
      {rings.map((radius, i) => (
        <OrbitRing key={radius} radius={radius * (0.86 + activity.fraction * 0.14)}
          color={color} position={[0, 0.53 + i * 0.21, 0]} glow={0.64} />
      ))}
      {Array.from({ length: 5 }, (_, i) => {
        const t = (activity.fraction * 2.7 + i / 5) % 1
        const angle = t * 2 * Math.PI + i * 0.9
        const radius = 1.15 - t * 0.62
        return (
          <mesh key={i} position={[Math.cos(angle) * radius, 0.22 + t * 1.05, Math.sin(angle) * radius]}
            rotation={[t * 3, angle, 0]} scale={0.45 + Math.sin(Math.PI * t) * 0.55}>
            <octahedronGeometry args={[0.1]} />
            <meshBasicMaterial color={color} />
          </mesh>
        )
      })}
    </group>
  )
}

const Bridge = memo(function Bridge({ from, to, visited }) {
  const points = [from.position, to.position].map(([x, y, z]) => [x, y - 0.32, z])
  return (
    <group>
      <Line points={points} color="#182844" lineWidth={7} />
      <Line points={points} color={visited ? regionOf(to.region).color : '#455570'}
        lineWidth={2} dashed dashSize={0.27} gapSize={0.22} />
    </group>
  )
})

export default function Scene({ timeline, progress, frame, activity, playing, reducedMotion, onSelect }) {
  const points = useMemo(() => layout(timeline), [timeline])
  const controls = useRef()
  const position = pieceAt(points, frame, reducedMotion)
  const current = points[frame.index]
  const resolved = Math.min(points.length - 1, resolvedIndex(progress))
  const lastResolved = points[resolved]
  const age = lastResolved ? Math.max(0, progress - resolved + 1 - RESOLUTION) / 0.52 : 1

  return (
    <>
      <fog attach="fog" args={['#080f1b', 23, 63]} />
      <ambientLight intensity={0.65} />
      <directionalLight position={[12, 22, 8]} intensity={2.1} color="#d6e7ff" />
      <hemisphereLight args={['#799fd8', '#32233e', 1.2]} />
      <Stars radius={70} depth={40} count={2300} factor={3.2} fade speed={reducedMotion ? 0 : 0.35} />

      {points.slice(1).map((row, i) => (
        <Bridge key={row.stage} from={points[i]} to={row} visited={resolved >= i} />
      ))}
      {points.map((row, i) => (
        <StageIsland key={row.stage} row={row} active={row === current}
          gateway={regionOf(points[i - 1]?.region).label !== regionOf(row.region).label}
          resolved={resolved >= row.index0} onSelect={onSelect} />
      ))}
      {current && frame.arrived && (
        <group position={current.position}>
          <Attempts results={frame.attempts} active={frame.attempting} reducedMotion={reducedMotion} />
          <Html center position={[0, 2.32, 0]} className="node-label" style={{ pointerEvents: 'none' }}>
            <div className={`label ${frame.resolved ? (current.cleared ? 'cleared' : 'failed') : 'running'}`}>
              <b>{frame.resolved ? (current.cleared ? `+${current.points} points` : 'Run stopped') : (activity.checking ? 'Checking attempt' : 'Attempts in progress')}</b>
            </div>
          </Html>
        </group>
      )}
      {current && frame.attempting && !reducedMotion && activity.attempt?.started !== false && (
        <WorkOrbit row={current} activity={activity} />
      )}
      {playing && !reducedMotion && age < 1 && (
        <Burst row={lastResolved} age={age} final={lastResolved.index0 === points.length - 1} />
      )}

      <Pilot position={position} reducedMotion={reducedMotion} />
      <OrbitControls ref={controls} enablePan={false} minDistance={5} maxDistance={48} />
      <FollowCamera position={position} controls={controls} reducedMotion={reducedMotion} />
    </>
  )
}
