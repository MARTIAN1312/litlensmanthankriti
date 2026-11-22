import type { CharacterSpec } from 'wobnimo';

/**
 * Hoot — a night-owl scholar for LitLens.
 *
 * A round, chestnut owl with golden eyes, round spectacles, ear tufts,
 * wings and a scholar's mortarboard. Colours are fixed hex values so it
 * looks identical in light and dark mode. The Wobnimo engine animates the
 * ten states (idle, thinking, listening, speaking, working, error,
 * surprised, celebrating, sad, sleeping) from the `acting` map below.
 */
export const owl: CharacterSpec = {
  id: 'owl',
  name: 'Hoot',
  tagline: 'A scholarly night-owl who reads, thinks and celebrates your discoveries',
  accent: '#7a4a2a',

  frame: { target: 0.5, radius: 0.66 },
  bound: { y: 0.5, radius: 0.72 },
  motion: { hop: 0.14, squash: 1.15, snap: 1, talkSquash: 0.7 },

  materials: {
    skin: { color: '#7a4a2a', f0: 0.05, spec: 0.5, shininess: 40, rim: 0.7, sss: 0.18, sssColor: '#b57a4a' },
    wing: { color: '#5e3a22', shadeOf: 'skin', f0: 0.05, spec: 0.4, shininess: 30, rim: 0.6 },
    tuft: { color: '#8a5a35', f0: 0.05, spec: 0.5, shininess: 40, rim: 0.7 },
    beak: { color: '#e8a33d', f0: 0.1, spec: 1.2, shininess: 120, rim: 0.9 },
    foot: { color: '#d97b33', shadeOf: 'beak', f0: 0.05, spec: 0.6, shininess: 40, rim: 0.6 },
    glass: { color: '#c8a24b', f0: 0.5, spec: 2.5, shininess: 220, rim: 1.6, sss: 0.2, sssColor: '#f0e6c8', gloss: 0.9 },
    cap: { color: '#3d3a5c', f0: 0.1, spec: 0.9, shininess: 80, rim: 0.9 },
    tassel: { color: '#e8a33d', f0: 0.1, spec: 1.4, shininess: 140, rim: 1 },
  },

  bones: [
    { name: 'body', pivot: [0, 0, 0], drive: { ry: [['yaw', 0.3]], rz: [['roll', 0.4]] } },
    { name: 'head', parent: 'body', pivot: [0, 0.3, 0], drive: { rx: [['pitch', -0.6]], ry: [['yaw', 0.6]], rz: [['roll', 0.5]] } },
    { name: 'earL', parent: 'head', pivot: [-0.22, 0.34, -0.02], jiggle: { axis: [0, 1, 0], length: 0.1, freq: 2.4, damping: 0.12 } },
    { name: 'earR', parent: 'head', pivot: [0.22, 0.34, -0.02], jiggle: { axis: [0, 1, 0], length: 0.1, freq: 2.4, damping: 0.12 } },
    { name: 'wingL', parent: 'body', pivot: [-0.22, 0.3, -0.12], drive: { rz: [['flap', -1.2]] }, wave: { rz: [0.06, 0.7, 0] } },
    { name: 'wingR', parent: 'body', pivot: [0.22, 0.3, -0.12], drive: { rz: [['flap', 1.2]] }, wave: { rz: [-0.06, 0.7, 1.6] } },
  ],

  parts: [
    // plump owl body
    { bone: 'body', shape: 'ellipsoid', at: [0, 0.19, 0], radii: [0.25, 0.19, 0.23], material: 'skin' },
    // large round head melting onto the body
    { bone: 'head', shape: 'ellipsoid', at: [0, 0.22, 0], radii: [0.3, 0.26, 0.28], blend: 0.08, material: 'skin' },
    // ear tufts (owl "horns")
    { bone: 'earL', shape: 'roundCone', from: [0, -0.05, 0], to: [-0.12, 0.13, 0.03], r1: 0.05, r2: 0.012, material: 'tuft' },
    { bone: 'earR', shape: 'roundCone', from: [0, -0.05, 0], to: [0.12, 0.13, 0.03], r1: 0.05, r2: 0.012, material: 'tuft' },
    // folded wings at the sides
    { bone: 'wingL', shape: 'ellipsoid', at: [-0.12, 0.1, 0], rot: [0, 0, 0.5], radii: [0.13, 0.18, 0.016], material: 'wing' },
    { bone: 'wingR', shape: 'ellipsoid', at: [0.12, 0.1, 0], rot: [0, 0, -0.5], radii: [0.13, 0.18, 0.016], material: 'wing' },
    // talons
    { bone: 'body', shape: 'roundCone', from: [-0.12, 0.06, 0.1], to: [-0.15, 0.01, 0.17], r1: 0.045, r2: 0.016, material: 'foot' },
    { bone: 'body', shape: 'roundCone', from: [0.12, 0.06, 0.1], to: [0.15, 0.01, 0.17], r1: 0.045, r2: 0.016, material: 'foot' },
    // little beak
    { bone: 'head', shape: 'roundCone', from: [0, 0.09, 0.29], to: [0, 0.04, 0.4], r1: 0.036, r2: 0.009, material: 'beak' },
    // round spectacles: a frame around each eye + a bridge
    { bone: 'head', shape: 'frame', at: [-0.13, 0.16, 0.225], rot: [0, 0, 0], half: [0.075, 0.075], corner: 0.04, width: 0.014, depth: 0.008, material: 'glass' },
    { bone: 'head', shape: 'frame', at: [0.13, 0.16, 0.225], rot: [0, 0, 0], half: [0.075, 0.075], corner: 0.04, width: 0.014, depth: 0.008, material: 'glass' },
    { bone: 'head', shape: 'cylinder', at: [0, 0.16, 0.3], rot: [0, 0, Math.PI / 2], half: 0.03, radius: 0.01, round: 0.016, material: 'glass' },
    // scholar's mortarboard with a tassel
    { bone: 'head', shape: 'plate', at: [0, 0.48, -0.02], half: [0.18, 0.18], corner: 0.03, depth: 0.016, material: 'cap' },
    { bone: 'head', shape: 'roundCone', from: [0.03, 0.5, -0.04], to: [-0.08, 0.54, -0.2], r1: 0.014, r2: 0.005, material: 'tassel' },
  ],

  paints: [
    // cream belly
    { bone: 'body', on: ['skin'], kind: 'ellipse', at: [0, 0.14, 0.2], radii: [0.14, 0.13], color: '#f0ddc2', soft: 0.45, opacity: 0.95 },
    // pale facial disc around the eyes
    { bone: 'head', on: ['skin'], kind: 'ellipse', at: [0, 0.16, 0.27], radii: [0.18, 0.14], color: '#f0ddc2', soft: 0.5, opacity: 0.55 },
    // a soft brow shading above the eyes
    { bone: 'head', on: ['skin'], kind: 'sphere', at: [-0.13, 0.23, 0.24], radius: 0.03, color: '#5e3a22', soft: 0.6, opacity: 0.6 },
    { bone: 'head', on: ['skin'], kind: 'sphere', at: [0.13, 0.23, 0.24], radius: 0.03, color: '#5e3a22', soft: 0.6, opacity: 0.6 },
  ],

  eyes: {
    kind: 'ball',
    bone: 'head',
    at: [
      [-0.13, 0.16, 0.2],
      [0.13, 0.16, 0.2],
    ],
    radius: 0.052,
    iris: '#f2b84b',
    irisSize: 0.85,
    pupilSize: 0.55,
    lid: 'skin',
  },

  face: { kind: 'mouth', bone: 'head', on: ['skin'], at: [0, -0.01, 0.195], width: 0.032, color: '#3a2010', tongue: '#ff7d8a' },

  anchors: {
    top: { bone: 'head', at: [0, 0.5, 0.02] },
    mouth: { bone: 'head', at: [0, 0.02, 0.31] },
    ear: { bone: 'head', at: [-0.28, 0.3, -0.02] },
    feet: { bone: 'root', at: [0, 0.02, 0.15] },
  },

  acting: {
    idle: { head: { ry: [0, 0.04, 0.4, 0] } },
    thinking: { head: { rz: 0.16 }, earL: { rz: [0, 0.12, 1.4, 0] }, earR: { rz: [0, -0.12, 1.4, 0] } },
    listening: { earL: { rz: 0.3, ry: -0.18 }, earR: { rz: -0.3, ry: 0.18 }, head: { rz: -0.08 } },
    speaking: { head: { ry: [0, 0.05, 3, 0] }, earL: { rz: [0, 0.06, 3, 0] }, earR: { rz: [0, -0.06, 3, 1.5] } },
    working: { head: { rx: -0.08 }, wingL: { rz: 0.22 }, wingR: { rz: -0.22 } },
    error: { head: { rz: [0, 0.08, 10, 0] }, wingL: { rz: 0.5, ry: 0.4 }, wingR: { rz: -0.5, ry: -0.4 }, earL: { rz: 0.3 }, earR: { rz: -0.3 } },
    surprised: { head: { rx: -0.18 }, wingL: { rz: 0.7 }, wingR: { rz: -0.7 }, earL: { rz: 0.5 }, earR: { rz: -0.5 } },
    celebrating: { wingL: { rz: [0, 0.5, 9, 0] }, wingR: { rz: [0, 0.5, 9, Math.PI] }, earL: { rz: [0, 0.2, 3, 0] }, earR: { rz: [0, -0.2, 3, 0] } },
    sad: { head: { rx: 0.25 }, earL: { rz: 0.5, rx: 0.5 }, earR: { rz: -0.5, rx: 0.5 }, wingL: { rz: -0.4 }, wingR: { rz: 0.4 } },
    sleeping: { head: { rx: 0.15 }, earL: { rz: 0.4, rx: 0.3 }, earR: { rz: -0.4, rx: 0.3 }, wingL: { rz: -0.25 }, wingR: { rz: 0.25 } },
  },

  fx: {
    replace: ['land'],
    land: [{ glyph: 'drop', anchor: 'feet', rate: 6, spread: 0.15, velocity: [0, 0.5, 0.05], jitter: 0.6, gravity: 3, life: [0.4, 0.55], size: [0.03, 0.018], color: '#d97b33', align: true }],
    'enter:happy': [{ glyph: 'sparkle', anchor: 'top', rate: 6, velocity: [0, 0.6, 0.04], jitter: 0.9, gravity: 2, life: [0.5, 0.7], size: [0.03, 0.015], color: '#f2b84b', align: true }],
    'enter:celebrating': [{ glyph: 'confetti', anchor: 'top', rate: 14, spread: 0.25, velocity: [0, 0.8, 0.3], jitter: 1.2, gravity: 2.2, life: [0.7, 1.1], size: [0.025, 0.02], color: '#e8a33d' }],
  },
};

export default owl;
