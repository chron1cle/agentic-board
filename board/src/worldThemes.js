// Board geometry and colours by world. Coordinates are in the same units as the bot.
function spiral(level) {
  const angle = level * 0.62
  return { x: Math.cos(angle) * 9.5, z: Math.sin(angle) * 9.5, angle }
}

function zigzag(level) {
  return { x: level % 2 === 0 ? 4.5 : -4.5, z: -2.6 + level * 3.6, angle: 0 }
}

const SPIRAL = {
  path: spiral,
  rise: 1.15,
  deck: '#263249',
  surface: '#101620',
  bridge: '#182844',
  bridgeIdle: '#455570',
  sky: ['#25233f', '#142d40'],
  platform: { sides: 8, rockSides: 7, rockRotation: Math.PI / 8, insetSides: 6, traceSides: 0 },
}

export const WORLD_THEMES = {
  1: SPIRAL,
  2: {
    path: zigzag,
    rise: 1.15,
    accent: '#83e4ee',
    deck: '#24536b',
    surface: '#182637',
    rock: '#514879',
    bridge: '#263f68',
    bridgeIdle: '#577ea2',
    sky: ['#172f51', '#263057'],
    platform: { sides: 4, rockSides: 4, rockRotation: 0, insetSides: 4, traceSides: 4 },
  },
}

export function worldTheme(world) {
  return WORLD_THEMES[world] || SPIRAL
}
