import { Canvas, useFrame, useLoader, useThree } from "@react-three/fiber";
import { Suspense, useEffect, useMemo, useRef, type MutableRefObject, type RefObject } from "react";
import { createPortal } from "react-dom";
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { MeshSurfaceSampler } from "three/addons/math/MeshSurfaceSampler.js";
import { mergeVertices } from "three/addons/utils/BufferGeometryUtils.js";
import { prefersReducedMotion, useFullMotion } from "../lib/motion";

const MODEL_URL = "/models/LeePerrySmith.glb";
const SKIN_COUNT = 42000;
const NODE_COUNT = 950;
const FIBRE_COUNT = 420;
const FIBRE_SEGMENTS = 10;
const DOTS_PER_FIBRE = 4;
const FACE_HEIGHT = 2.5;
const INTRO_SECONDS = 9;
const CAMERA_Z = 6;
const FOV = 35;
const LIGHT = new THREE.Vector3(0.25, 0.35, 0.9).normalize();
// Eye socket centres and the mouth measured from the scan's depth map (model units).
const EYE_MODEL = [new THREE.Vector3(-0.66, 1.62, 1.95), new THREE.Vector3(0.66, 1.62, 1.95)];
const EYE_RADII_MODEL = new THREE.Vector2(0.48, 0.24);
const MOUTH_MODEL = new THREE.Vector3(0, 0.1, 2.2);
const MOUTH_RADII_MODEL = new THREE.Vector2(0.48, 0.32);

type V3 = THREE.Vector3;

function analyseHead(scene: THREE.Object3D): THREE.BufferGeometry {
  let mesh: THREE.Mesh | undefined;
  scene.traverse((o) => {
    if (!mesh && (o as THREE.Mesh).isMesh) mesh = o as THREE.Mesh;
  });
  if (!mesh) throw new Error("Face model has no mesh");

  let g = mesh.geometry.clone();
  for (const name of Object.keys(g.attributes)) if (name !== "position") g.deleteAttribute(name);
  g = mergeVertices(g, 1e-4);
  g.computeVertexNormals();
  const pos = g.getAttribute("position");
  const nor = g.getAttribute("normal");
  const index = g.index!;
  const n = pos.count;

  const sum = new Float32Array(n);
  const edge = new Float32Array(n);
  const a = new THREE.Vector3();
  const b = new THREE.Vector3();
  const na = new THREE.Vector3();
  const addPair = (i: number, j: number) => {
    a.fromBufferAttribute(pos, i);
    b.fromBufferAttribute(pos, j).sub(a);
    na.fromBufferAttribute(nor, i);
    sum[i] += na.dot(b);
    edge[i] += b.length();
  };
  for (let t = 0; t < index.count; t += 3) {
    const i = index.getX(t);
    const j = index.getX(t + 1);
    const k = index.getX(t + 2);
    addPair(i, j); addPair(i, k); addPair(j, i); addPair(j, k); addPair(k, i); addPair(k, j);
  }
  // Positive = neighbours rise above the surface (a hollow: socket, nostril, lip line).
  let curv = new Float32Array(n);
  for (let i = 0; i < n; i++) curv[i] = edge[i] > 0 ? sum[i] / edge[i] : 0;
  for (let pass = 0; pass < 2; pass++) {
    const acc = Float32Array.from(curv);
    const cnt = new Float32Array(n).fill(1);
    for (let t = 0; t < index.count; t += 3) {
      const tri = [index.getX(t), index.getX(t + 1), index.getX(t + 2)];
      for (const i of tri) for (const j of tri) if (i !== j) { acc[i] += curv[j]; cnt[i]++; }
    }
    curv = acc.map((v, i) => v / cnt[i]);
  }

  const sorted = Array.from(curv, Math.abs).sort((x, y) => x - y);
  const scale = sorted[Math.floor(n * 0.92)] || 1;
  const shade = new Float32Array(n * 3);
  const skinWeight = new Float32Array(n);
  const nodeWeight = new Float32Array(n);
  const p = new THREE.Vector3();
  for (let i = 0; i < n; i++) {
    const c = curv[i] / scale;
    const f = Math.min(1, Math.abs(c));
    p.fromBufferAttribute(pos, i);
    const inEye = EYE_MODEL.some((e) => ((p.x - e.x) / EYE_RADII_MODEL.x) ** 2 + ((p.y - e.y) / EYE_RADII_MODEL.y) ** 2 < 1);
    const mouthQ = ((p.x - MOUTH_MODEL.x) / (MOUTH_RADII_MODEL.x * 1.3)) ** 2 + ((p.y - MOUTH_MODEL.y) / (MOUTH_RADII_MODEL.y * 1.4)) ** 2;
    shade[i * 3] = THREE.MathUtils.clamp(c, 0, 1);
    shade[i * 3 + 1] = THREE.MathUtils.clamp(-c, 0, 1);
    skinWeight[i] = 0.6 + 2.5 * f;
    // Few web nodes on the eyeballs and lips, so the wireframe doesn't trace them into hard outlines.
    nodeWeight[i] = (0.15 + 5 * f * f) * (inEye ? 0.15 : 1) * (mouthQ < 1 ? 0.12 : 1);
  }
  g.setAttribute("color", new THREE.BufferAttribute(shade, 3));
  g.setAttribute("skinWeight", new THREE.BufferAttribute(skinWeight, 1));
  g.setAttribute("nodeWeight", new THREE.BufferAttribute(nodeWeight, 1));
  g.computeBoundingBox();
  const flat = g.toNonIndexed();
  flat.boundingBox = g.boundingBox;
  return flat;
}

type Sample = { p: V3; n: V3; cav: number; ridge: number };

function sampleFace(geometry: THREE.BufferGeometry, weight: string, count: number): Sample[] {
  const box = geometry.boundingBox!;
  const size = box.getSize(new THREE.Vector3());
  // Face "mask" only: chin tip (model y≈-0.85) to brow, front half, camera-facing (model faces +Z).
  const yMin = box.min.y + size.y * 0.39;
  const yMax = box.max.y - size.y * 0.04;
  const sampler = new MeshSurfaceSampler(new THREE.Mesh(geometry)).setWeightAttribute(weight).build();
  const p = new THREE.Vector3();
  const nn = new THREE.Vector3();
  const c = new THREE.Color();
  const out: Sample[] = [];
  while (out.length < count) {
    sampler.sample(p, nn, c);
    if (p.y > yMin && p.y < yMax && p.z > 0 && nn.z > 0.05) out.push({ p: p.clone(), n: nn.clone(), cav: c.r, ridge: c.g });
  }
  return out;
}

// Egg-shaped silhouette: narrows toward a pointed chin so the jaw sides dissolve.
const faceRadius = (y: number) => {
  const taper = THREE.MathUtils.smoothstep(-y, 0.15, 1.25);
  return { rx: 1.0 - 0.48 * taper, ry: y < 0 ? 1.5 : 1.3 };
};
const edgeFade = (v: V3) => {
  const { rx, ry } = faceRadius(v.y);
  return THREE.MathUtils.smoothstep(1 - Math.hypot(v.x / rx, v.y / ry), 0, 0.3);
};

/** Lift the mouth corners into a slight smile (face space, in place). Smooth falloff avoids particle bunching. */
function sculpt(s: Sample, mouth: V3, mouthRadii: THREE.Vector2) {
  const p = s.p;
  const qx = (p.x - mouth.x) / mouthRadii.x;
  const qy = (p.y - mouth.y) / mouthRadii.y;
  p.y += 0.032 * qx * qx * Math.exp(-(qx * qx) / 2.2 - (qy * qy) / 1.4);
}

function knnPairs(points: V3[], k: number): [number, number][] {
  const seen = new Set<number>();
  const pairs: [number, number][] = [];
  const n = points.length;
  for (let i = 0; i < n; i++) {
    const best: { j: number; d: number }[] = [];
    for (let j = 0; j < n; j++) {
      if (j === i) continue;
      const d = points[i].distanceToSquared(points[j]);
      if (best.length < k || d < best[best.length - 1].d) {
        best.push({ j, d });
        best.sort((x, y) => x.d - y.d);
        if (best.length > k) best.pop();
      }
    }
    for (const { j } of best) {
      const key = i < j ? i * n + j : j * n + i;
      if (!seen.has(key)) {
        seen.add(key);
        pairs.push([i, j]);
      }
    }
  }
  return pairs;
}

function percentileLength(points: V3[], pairs: [number, number][], q: number) {
  const lengths = pairs.map(([i, j]) => points[i].distanceTo(points[j])).sort((x, y) => x - y);
  return lengths[Math.floor(lengths.length * q)] ?? 1;
}

function attrs(g: THREE.BufferGeometry, entries: Record<string, [Float32Array, number]>) {
  for (const [name, [array, size]] of Object.entries(entries)) g.setAttribute(name, new THREE.BufferAttribute(array, size));
  return g;
}

function lineGeometry(pairs: [number, number][], face: V3[], scatter: V3[], seeds: number[], shade: number[]) {
  const count = pairs.length * 2;
  const position = new Float32Array(count * 3);
  const other = new Float32Array(count * 3);
  const scat = new Float32Array(count * 3);
  const otherScat = new Float32Array(count * 3);
  const seed = new Float32Array(count);
  const otherSeed = new Float32Array(count);
  const sh = new Float32Array(count);
  pairs.forEach(([i, j], k) => {
    for (const [v, self, peer] of [[2 * k, i, j], [2 * k + 1, j, i]] as const) {
      position.set(face[self].toArray(), v * 3);
      other.set(face[peer].toArray(), v * 3);
      scat.set(scatter[self].toArray(), v * 3);
      otherScat.set(scatter[peer].toArray(), v * 3);
      seed[v] = seeds[self];
      otherSeed[v] = seeds[peer];
      sh[v] = shade[self];
    }
  });
  return attrs(new THREE.BufferGeometry(), {
    position: [position, 3], aOther: [other, 3], aScatter: [scat, 3], aOtherScatter: [otherScat, 3],
    aSeed: [seed, 1], aOtherSeed: [otherSeed, 1], aShade: [sh, 1],
  });
}

/** Light fibres sprouting from the crown and outline, curving outward and fading at the tips. */
function buildFibres(skin: Sample[]) {
  const roots = skin
    .filter((s) => s.p.y > 0.3 || (Math.hypot(s.p.x / 1.0, s.p.y / 1.3) > 0.8 && s.p.y > -0.45))
    .map((s) => ({ s, key: Math.random() / (1 + Math.max(0, s.p.y) * 2.5) }))
    .sort((a, b) => a.key - b.key)
    .slice(0, FIBRE_COUNT)
    .map(({ s }) => s);
  const fibres = roots.map((s) => {
    const radial = new THREE.Vector3(s.p.x * 0.8, s.p.y + 0.6, 0).normalize();
    const dir = radial.multiplyScalar(0.85).add(s.n.clone().multiplyScalar(0.3)).add(new THREE.Vector3(0, 0, 0.1)).normalize();
    const perp = new THREE.Vector3(-dir.y, dir.x, 0).multiplyScalar((Math.random() - 0.5) * 0.6);
    const crown = Math.max(0, s.p.y);
    const len = (0.18 + Math.random() ** 2 * 1.1) * (0.6 + crown * 1.4);
    return { root: s.p, dir, bend: perp, len, seed: Math.random() };
  });

  const segVerts = fibres.length * FIBRE_SEGMENTS * 2;
  const lines = {
    aRoot: new Float32Array(segVerts * 3), aDir: new Float32Array(segVerts * 3), aBend: new Float32Array(segVerts * 3),
    aLen: new Float32Array(segVerts), aT: new Float32Array(segVerts), aSeed: new Float32Array(segVerts),
  };
  const dotCount = fibres.length * (DOTS_PER_FIBRE + 1);
  const dots = {
    aRoot: new Float32Array(dotCount * 3), aDir: new Float32Array(dotCount * 3), aBend: new Float32Array(dotCount * 3),
    aLen: new Float32Array(dotCount), aT: new Float32Array(dotCount), aSeed: new Float32Array(dotCount), aSpark: new Float32Array(dotCount),
  };
  let v = 0;
  let d = 0;
  for (const f of fibres) {
    for (let s = 0; s < FIBRE_SEGMENTS; s++) {
      for (const t of [s / FIBRE_SEGMENTS, (s + 1) / FIBRE_SEGMENTS]) {
        lines.aRoot.set(f.root.toArray(), v * 3); lines.aDir.set(f.dir.toArray(), v * 3); lines.aBend.set(f.bend.toArray(), v * 3);
        lines.aLen[v] = f.len; lines.aT[v] = t; lines.aSeed[v] = f.seed;
        v++;
      }
    }
    for (let k = 0; k <= DOTS_PER_FIBRE; k++) {
      dots.aRoot.set(f.root.toArray(), d * 3); dots.aDir.set(f.dir.toArray(), d * 3); dots.aBend.set(f.bend.toArray(), d * 3);
      dots.aLen[d] = f.len; dots.aSeed[d] = Math.random();
      // The last entry per fibre is a moving spark; the rest are static nodes biased toward the root.
      dots.aSpark[d] = k === DOTS_PER_FIBRE ? 1 : 0;
      dots.aT[d] = k === DOTS_PER_FIBRE ? f.seed : Math.random() ** 1.1;
      d++;
    }
  }
  const lineGeo = attrs(new THREE.BufferGeometry(), {
    position: [new Float32Array(segVerts * 3), 3], aRoot: [lines.aRoot, 3], aDir: [lines.aDir, 3], aBend: [lines.aBend, 3],
    aLen: [lines.aLen, 1], aT: [lines.aT, 1], aSeed: [lines.aSeed, 1],
  });
  const dotGeo = attrs(new THREE.BufferGeometry(), {
    position: [new Float32Array(dotCount * 3), 3], aRoot: [dots.aRoot, 3], aDir: [dots.aDir, 3], aBend: [dots.aBend, 3],
    aLen: [dots.aLen, 1], aT: [dots.aT, 1], aSeed: [dots.aSeed, 1], aSpark: [dots.aSpark, 1],
  });
  return { lineGeo, dotGeo };
}

function buildScene(scene: THREE.Object3D) {
  const head = analyseHead(scene);
  const skinRaw = sampleFace(head, "skinWeight", SKIN_COUNT);
  const nodeRaw = sampleFace(head, "nodeWeight", NODE_COUNT);

  const box = new THREE.Box3().setFromPoints(skinRaw.map((s) => s.p));
  const center = box.getCenter(new THREE.Vector3());
  const scale = FACE_HEIGHT / box.getSize(new THREE.Vector3()).y;
  const toFace = (v: V3) => v.clone().sub(center).multiplyScalar(scale);
  for (const s of [...skinRaw, ...nodeRaw]) s.p.sub(center).multiplyScalar(scale);
  const eyes = EYE_MODEL.map(toFace);
  const eyeRadii = EYE_RADII_MODEL.clone().multiplyScalar(scale);
  const mouth = toFace(MOUTH_MODEL);
  const mouthRadii = MOUTH_RADII_MODEL.clone().multiplyScalar(scale);
  for (const s of [...skinRaw, ...nodeRaw]) sculpt(s, mouth, mouthRadii);

  const skin = new THREE.BufferGeometry();
  const sPos = new Float32Array(SKIN_COUNT * 3);
  const sNor = new Float32Array(SKIN_COUNT * 3);
  const sScat = new Float32Array(SKIN_COUNT * 3);
  const sShade = new Float32Array(SKIN_COUNT * 2);
  const sSeed = new Float32Array(SKIN_COUNT);
  skinRaw.forEach((s, i) => {
    sPos.set(s.p.toArray(), i * 3);
    sNor.set(s.n.toArray(), i * 3);
    sScat.set(s.p.clone().add(new THREE.Vector3().randomDirection().multiplyScalar(0.4 + Math.random() * 1.2)).toArray(), i * 3);
    sShade.set([s.cav, s.ridge], i * 2);
    sSeed[i] = Math.random();
  });
  attrs(skin, { position: [sPos, 3], aNormal: [sNor, 3], aScatter: [sScat, 3], aShade: [sShade, 2], aSeed: [sSeed, 1] });

  // Web nodes start in a loose halo hugging the head (face space) and contract onto the face.
  const face = nodeRaw.map((s) => s.p);
  const scatter = face.map((v) => {
    const angle = Math.random() * Math.PI * 2;
    const radius = 0.75 + Math.random() ** 0.7 * 1.0;
    const pull = new THREE.Vector3(Math.cos(angle) * radius * 0.95, Math.sin(angle) * radius * 1.15, (Math.random() - 0.5) * 1.4);
    return pull.lerp(v, 0.25);
  });
  const seeds = face.map(() => Math.random());
  const shade = nodeRaw.map((s) =>
    THREE.MathUtils.clamp((0.25 + Math.max(0, s.n.dot(LIGHT)) * 0.75) * edgeFade(s.p) * (1 - s.cav * 0.5) + s.ridge * 0.25, 0, 1),
  );
  const warm = face.map((v) => (Math.random() < 0.1 + 0.35 * Math.max(0, v.y) ? 1 : 0));
  const nodes = attrs(new THREE.BufferGeometry(), {
    position: [new Float32Array(face.flatMap((v) => v.toArray())), 3],
    aScatter: [new Float32Array(scatter.flatMap((v) => v.toArray())), 3],
    aSeed: [new Float32Array(seeds), 1],
    aShade: [new Float32Array(shade), 1],
    aWarm: [new Float32Array(warm), 1],
  });

  const facePairs = knnPairs(face, 3);
  const webPairs = knnPairs(scatter, 2);
  return {
    skin,
    nodes,
    faceLines: lineGeometry(facePairs, face, scatter, seeds, shade),
    webLines: lineGeometry(webPairs, face, scatter, seeds, shade),
    fibres: buildFibres(skinRaw),
    faceMaxLocal: percentileLength(face, facePairs, 0.9) * 1.3,
    webMax: percentileLength(scatter, webPairs, 0.9) * 1.3,
    eyes,
    eyeRadii,
    mouth,
    mouthRadii,
  };
}

const COMMON = /* glsl */ `
  uniform float uProgress;
  uniform float uTime;
  uniform mat4 uFace;
  float nodeEase(float seed) {
    float t = clamp((uProgress - 0.32 - seed * 0.22) / 0.4, 0.0, 1.0);
    return t < 0.5 ? 4.0 * t * t * t : 1.0 - pow(-2.0 * t + 2.0, 3.0) / 2.0;
  }
  // Web nodes blink in and out independently before the web condenses into the face.
  float flicker(float seed) {
    return smoothstep(0.2, 0.95, 0.5 + 0.5 * sin(uTime * (0.7 + seed * 1.1) + seed * 40.0));
  }
  vec3 nodePos(vec3 face, vec3 scatter, float seed) {
    float e = nodeEase(seed);
    vec3 drift = vec3(sin(uTime * 0.4 + seed * 40.0), cos(uTime * 0.35 + seed * 31.0), sin(uTime * 0.3 + seed * 17.0)) * 0.06 * (1.0 - e);
    return (uFace * vec4(mix(scatter + drift, face, e), 1.0)).xyz;
  }
  vec3 fibrePos(vec3 root, vec3 dir, vec3 bend, float len, float t, float seed) {
    vec3 sway = vec3(sin(uTime * 0.6 + seed * 20.0), cos(uTime * 0.5 + seed * 13.0), 0.0) * 0.03 * t * len;
    return root + dir * len * t + bend * len * t * t + sway;
  }
`;

const nodeVertex = /* glsl */ `
  ${COMMON}
  uniform float uPixelRatio;
  attribute vec3 aScatter;
  attribute float aSeed;
  attribute float aShade;
  attribute float aWarm;
  varying float vAlpha;
  varying float vWarm;
  void main() {
    vec3 p = nodePos(position, aScatter, aSeed);
    vec4 mv = viewMatrix * vec4(p, 1.0);
    gl_Position = projectionMatrix * mv;
    float e = nodeEase(aSeed);
    float pulse = 0.7 + 0.3 * sin(uTime * 2.2 + aSeed * 50.0);
    float blink = mix(flicker(aSeed), 1.0, e);
    vAlpha = smoothstep(0.0, 0.08, uProgress) * mix(0.8, aShade, e) * pulse * blink;
    vWarm = mix(1.0, aWarm, e);
    gl_PointSize = mix(6.0, mix(3.5, 11.0, aWarm) * (0.5 + aShade), e) * uPixelRatio * (${CAMERA_Z.toFixed(1)} / -mv.z);
  }
`;

const glowFragment = /* glsl */ `
  uniform vec3 uIce;
  uniform vec3 uEmber;
  varying float vAlpha;
  varying float vWarm;
  float glow(vec2 coord) {
    float d = length(coord - 0.5);
    return smoothstep(0.14, 0.0, d) + exp(-d * d * 22.0) * 0.55;
  }
  void main() {
    float g = glow(gl_PointCoord);
    if (g < 0.01) discard;
    gl_FragColor = vec4(mix(uIce, uEmber, vWarm), g * vAlpha);
  }
`;

const lineVertex = /* glsl */ `
  ${COMMON}
  uniform float uMode;
  uniform float uFaceMax;
  uniform float uWebMax;
  attribute vec3 aOther;
  attribute vec3 aScatter;
  attribute vec3 aOtherScatter;
  attribute float aSeed;
  attribute float aOtherSeed;
  attribute float aShade;
  varying float vAlpha;
  varying float vWarm;
  void main() {
    vec3 p = nodePos(position, aScatter, aSeed);
    vec3 q = nodePos(aOther, aOtherScatter, aOtherSeed);
    float len = distance(p, q);
    float e = 0.5 * (nodeEase(aSeed) + nodeEase(aOtherSeed));
    float blink = mix(min(flicker(aSeed), flicker(aOtherSeed)), 1.0, e);
    float a = uMode < 0.5
      ? smoothstep(uFaceMax, uFaceMax * 0.4, len) * mix(0.2, aShade, e) * 0.4
      : (1.0 - e) * smoothstep(uWebMax * 1.6, uWebMax * 0.5, len) * 0.5;
    vAlpha = a * blink * smoothstep(0.0, 0.08, uProgress);
    vWarm = 1.0 - e;
    gl_Position = projectionMatrix * viewMatrix * vec4(p, 1.0);
  }
`;

const lineFragment = /* glsl */ `
  uniform vec3 uIce;
  uniform vec3 uEmber;
  varying float vAlpha;
  varying float vWarm;
  void main() {
    gl_FragColor = vec4(mix(uIce, uEmber, vWarm), vAlpha);
  }
`;

const fibreLineVertex = /* glsl */ `
  ${COMMON}
  uniform float uGrow;
  attribute vec3 aRoot;
  attribute vec3 aDir;
  attribute vec3 aBend;
  attribute float aLen;
  attribute float aT;
  attribute float aSeed;
  varying float vAlpha;
  varying float vT;
  void main() {
    float reach = clamp(uGrow * 1.4 - aSeed * 0.4, 0.0, 1.0);
    float t = min(aT, reach);
    vec3 p = fibrePos(aRoot, aDir, aBend, aLen, t, aSeed);
    gl_Position = projectionMatrix * viewMatrix * (uFace * vec4(p, 1.0));
    vAlpha = pow(1.0 - aT, 2.0) * step(0.001, reach) * 0.42 * (0.75 + 0.25 * sin(uTime * 1.3 + aSeed * 30.0));
    vT = aT;
  }
`;

const fibreLineFragment = /* glsl */ `
  uniform vec3 uIce;
  uniform vec3 uEmber;
  varying float vAlpha;
  varying float vT;
  void main() {
    gl_FragColor = vec4(mix(uIce, uEmber, smoothstep(0.0, 0.7, vT)), vAlpha);
  }
`;

const fibreDotVertex = /* glsl */ `
  ${COMMON}
  uniform float uGrow;
  uniform float uPixelRatio;
  attribute vec3 aRoot;
  attribute vec3 aDir;
  attribute vec3 aBend;
  attribute float aLen;
  attribute float aT;
  attribute float aSeed;
  attribute float aSpark;
  varying float vAlpha;
  varying float vWarm;
  void main() {
    float reach = clamp(uGrow * 1.4 - aSeed * 0.4, 0.0, 1.0);
    float t = aSpark > 0.5 ? fract(uTime * (0.08 + aSeed * 0.12) + aT) : aT;
    vec3 p = fibrePos(aRoot, aDir, aBend, aLen, t, aSeed);
    vec4 mv = viewMatrix * (uFace * vec4(p, 1.0));
    gl_Position = projectionMatrix * mv;
    float twinkle = 0.6 + 0.4 * sin(uTime * 3.0 + aSeed * 70.0);
    vAlpha = step(t, reach) * pow(1.0 - t, 0.7) * (aSpark > 0.5 ? 1.0 : 0.85 * twinkle);
    vWarm = smoothstep(0.05, 0.5, t);
    gl_PointSize = (aSpark > 0.5 ? 13.0 : 8.0) * (1.0 - t * 0.5) * uPixelRatio * (${CAMERA_Z.toFixed(1)} / -mv.z);
  }
`;

const skinVertex = /* glsl */ `
  ${COMMON}
  uniform float uPixelRatio;
  uniform float uSizeScale;
  uniform float uScan;
  uniform vec3 uLight;
  uniform vec3 uEyeL;
  uniform vec3 uEyeR;
  uniform vec2 uEyeRadii;
  uniform vec3 uMouth;
  uniform vec2 uMouthRadii;
  attribute vec3 aNormal;
  attribute vec3 aScatter;
  attribute vec2 aShade;
  attribute float aSeed;
  varying float vLight;
  varying float vRim;
  varying float vScan;
  varying float vSeed;
  varying float vAlpha;

  // Returns (mask, crease) for a closed eye: soft lid shading plus a dark curved lash line.
  vec2 closedEye(vec2 p, vec3 eye) {
    vec2 q = (p - eye.xy) / uEyeRadii;
    float mask = smoothstep(1.0, 0.55, length(q));
    float lash = q.y + 0.12 - 0.35 * q.x * q.x;
    float crease = exp(-lash * lash / 0.012) * smoothstep(1.0, 0.7, abs(q.x));
    return vec2(mask, crease);
  }

  // Smiling lips only (no dark mouth line): x = faint parting, y = lip glow, z = lip-area mask.
  vec3 mouthShade(vec2 p) {
    vec2 q = (p - uMouth.xy) / uMouthRadii;
    float span = smoothstep(1.05, 0.8, abs(q.x));
    float seamY = -0.1 + 0.42 * q.x * q.x;
    float parting = exp(-pow(q.y - seamY, 2.0) / 0.003) * span;
    float bow = 0.07 * exp(-q.x * q.x / 0.02);
    // Crescent lips curving up into the corners, fullest at the centre.
    float upperEdge = seamY + 0.32 - 0.3 * q.x * q.x - bow;
    float lowerEdge = seamY - 0.42 + 0.34 * q.x * q.x;
    float upperLip = smoothstep(seamY + 0.02, seamY + 0.1, q.y) * smoothstep(upperEdge + 0.04, upperEdge - 0.06, q.y);
    float lowerLip = smoothstep(seamY - 0.02, seamY - 0.1, q.y) * smoothstep(lowerEdge - 0.04, lowerEdge + 0.1, q.y);
    float upperRim = exp(-pow(q.y - upperEdge, 2.0) / 0.0025) * span;
    float lowerRim = exp(-pow(q.y - lowerEdge, 2.0) / 0.003) * span;
    float lowerGloss = exp(-(q.x * q.x / 0.1 + pow(q.y - (seamY - 0.22), 2.0) / 0.01));
    float body = (upperLip * 0.7 + lowerLip) * span;
    // Thin band along the scan's real lip seam (model mouth centre), where its dark crease is suppressed.
    float mask = exp(-pow(q.y + 0.05, 2.0) / 0.02) * smoothstep(1.1, 0.7, abs(q.x));
    return vec3(1.0 - parting * 0.55, body * 0.14 + upperRim * 0.5 + lowerRim * 0.32 + lowerGloss * 0.22, mask);
  }

  void main() {
    float t = clamp((uProgress - 0.62 - aSeed * 0.15) / 0.23, 0.0, 1.0);
    float e = 1.0 - pow(1.0 - t, 3.0);
    vec3 local = mix(aScatter, position, e) + aNormal * sin(uTime * 1.5 + aSeed * 50.0) * 0.004;
    vec4 mv = viewMatrix * (uFace * vec4(local, 1.0));
    gl_Position = projectionMatrix * mv;

    vec3 n = normalize(mat3(uFace) * aNormal);
    float diffuse = max(dot(n, uLight), 0.0);
    vRim = pow(1.0 - abs(n.z), 2.5) * (1.0 - smoothstep(0.1, 0.9, -position.y) * 0.85);
    vec2 eL = closedEye(position.xy, uEyeL);
    vec2 eR = closedEye(position.xy, uEyeR);
    float eyeMask = max(eL.x, eR.x);
    float crease = max(eL.y, eR.y);
    vec3 m = mouthShade(position.xy);
    // Inside the lip area the scan's own mouth crease is ignored; the lips are drawn by mouthShade instead.
    float cavity = aShade.x * (1.0 - m.z * 0.85);
    float ridge = aShade.y * (1.0 - eyeMask);
    vLight = (0.24 + pow(diffuse, 1.2) * 0.95) * (1.0 - cavity * 0.55) + ridge * 0.3;
    vLight *= (1.0 - eyeMask * 0.35) * (1.0 - crease * 0.85);
    vLight = vLight * m.x + m.y * diffuse;
    vScan = smoothstep(0.035, 0.0, abs(position.y - uScan)) * e;
    float taper = smoothstep(0.15, 1.25, -position.y);
    float r = length(position.xy / vec2(1.0 - 0.48 * taper, position.y < 0.0 ? 1.5 : 1.3));
    // Random threshold breaks the outline into scattered particles; the chin stays crisper.
    float jitter = (aSeed - 0.5) * mix(0.25, 0.1, taper);
    // Underside of the jaw (normal pointing down) is hidden so the chin isn't outlined by a ledge.
    float underside = smoothstep(-0.35, -0.65, aNormal.y) * smoothstep(0.5, 0.9, -position.y);
    vAlpha = e * smoothstep(0.0, 0.22, 1.0 - r + jitter) * (1.0 - underside);
    vSeed = aSeed;
    gl_PointSize = (1.1 + aSeed * 1.3 + vScan * 0.6) * uPixelRatio * uSizeScale;
  }
`;

const skinFragment = /* glsl */ `
  uniform float uTime;
  uniform vec3 uLit;
  uniform vec3 uShadow;
  uniform vec3 uRimColor;
  uniform vec3 uHot;
  varying float vLight;
  varying float vRim;
  varying float vScan;
  varying float vSeed;
  varying float vAlpha;
  void main() {
    float d = length(gl_PointCoord - 0.5);
    if (d > 0.5) discard;
    float soft = smoothstep(0.5, 0.05, d);
    float twinkle = 0.88 + 0.12 * sin(uTime * 2.5 + vSeed * 80.0);
    vec3 color = mix(uShadow, uLit, clamp(vLight, 0.0, 1.0)) + uRimColor * vRim * 0.5 + uHot * vScan * 0.25;
    gl_FragColor = vec4(color, (soft * clamp(vLight + vRim * 0.3, 0.08, 1.0) * 0.9 * twinkle + vScan * 0.12) * vAlpha);
  }
`;

function riskColor(risk: number): THREE.Color {
  return new THREE.Color("#7FB77E")
    .lerp(new THREE.Color("#E9B949"), Math.min(1, risk * 2))
    .lerp(new THREE.Color("#E5534B"), Math.max(0, risk * 2 - 1));
}

function shader(vertexShader: string, fragmentShader: string, uniforms: Record<string, THREE.IUniform>) {
  return new THREE.ShaderMaterial({ vertexShader, fragmentShader, uniforms, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending });
}

type SceneProps = { anchor: RefObject<HTMLDivElement | null>; risk: number; animate: boolean; replay: MutableRefObject<number> };

function FaceScene({ anchor, risk, animate, replay }: SceneProps) {
  const gltf = useLoader(GLTFLoader, MODEL_URL);
  const { camera, invalidate } = useThree();
  const data = useMemo(() => buildScene(gltf.scene), [gltf]);

  const uniforms = useMemo(
    () => ({
      uTime: { value: 0 },
      uProgress: { value: animate ? 0 : 1 },
      uGrow: { value: animate ? 0 : 1 },
      uFace: { value: new THREE.Matrix4() },
      uPixelRatio: { value: Math.min(window.devicePixelRatio, 2) },
      uSizeScale: { value: 1 },
      uScan: { value: 0 },
      uLight: { value: LIGHT.clone() },
      uLit: { value: new THREE.Color("#FFF1CC") },
      uShadow: { value: new THREE.Color("#1A1205") },
      uRimColor: { value: new THREE.Color("#D4AF37") },
      uHot: { value: new THREE.Color("#D4AF37") },
      uIce: { value: new THREE.Color("#F5E6B8") },
      uEmber: { value: new THREE.Color("#FFB13B") },
      uEyeL: { value: data.eyes[0] },
      uEyeR: { value: data.eyes[1] },
      uEyeRadii: { value: data.eyeRadii },
      uMouth: { value: data.mouth },
      uMouthRadii: { value: data.mouthRadii },
      uFaceMax: { value: 0.3 },
      uWebMax: { value: data.webMax },
    }),
    [animate, data],
  );
  const materials = useMemo(
    () => ({
      skin: shader(skinVertex, skinFragment, uniforms),
      nodes: shader(nodeVertex, glowFragment, uniforms),
      faceLines: shader(lineVertex, lineFragment, { ...uniforms, uMode: { value: 0 } }),
      webLines: shader(lineVertex, lineFragment, { ...uniforms, uMode: { value: 1 } }),
      fibreLines: shader(fibreLineVertex, fibreLineFragment, uniforms),
      fibreDots: shader(fibreDotVertex, glowFragment, uniforms),
    }),
    [uniforms],
  );

  const pointer = useRef({ x: 0, y: 0 });
  const rotation = useRef({ x: 0, y: 0 });
  const start = useRef<number | null>(null);
  const seenReplay = useRef(replay.current);
  const dummy = useMemo(() => new THREE.Object3D(), []);

  useEffect(() => {
    const onMove = (e: PointerEvent) => {
      pointer.current = { x: (e.clientX / window.innerWidth) * 2 - 1, y: -(e.clientY / window.innerHeight) * 2 + 1 };
    };
    // Static (reduced-motion) mode renders on demand, so re-render when the anchor moves.
    const onLayout = () => invalidate();
    window.addEventListener("pointermove", onMove);
    window.addEventListener("scroll", onLayout, { passive: true });
    window.addEventListener("resize", onLayout);
    return () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("scroll", onLayout);
      window.removeEventListener("resize", onLayout);
    };
  }, [invalidate]);

  useFrame((state) => {
    const t = state.clock.elapsedTime;
    if (start.current === null || seenReplay.current !== replay.current) {
      start.current = t;
      seenReplay.current = replay.current;
    }
    const progress = animate ? Math.min(1, (t - start.current) / INTRO_SECONDS) : 1;
    uniforms.uTime.value = t;
    uniforms.uProgress.value = progress;
    uniforms.uGrow.value = THREE.MathUtils.smoothstep(progress, 0.78, 1.0);
    // The scan line is gold to match the theme; risk only tints it slightly.
    uniforms.uHot.value.lerp(new THREE.Color("#D4AF37").lerp(riskColor(risk), 0.25), 0.05);
    uniforms.uScan.value = -FACE_HEIGHT / 2 + ((t * 0.15) % 1) * FACE_HEIGHT * 1.2;

    const el = anchor.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const ndc = new THREE.Vector3(
      ((rect.left + rect.width / 2) / window.innerWidth) * 2 - 1,
      -((rect.top + rect.height / 2) / window.innerHeight) * 2 + 1,
      0.5,
    ).unproject(camera);
    const dir = ndc.sub(camera.position).normalize();
    const target = camera.position.clone().addScaledVector(dir, -camera.position.z / dir.z);
    const frustumH = 2 * CAMERA_Z * Math.tan(THREE.MathUtils.degToRad(FOV / 2));
    // Leave headroom for the fibres that spray from the crown.
    const faceScale = ((rect.height / window.innerHeight) * frustumH * 0.72) / FACE_HEIGHT;
    target.y -= faceScale * 0.18;

    // A slight upward tilt reads as calm and alive; the scan's neutral pose looks down.
    const baseTiltX = -0.14;
    if (animate) {
      const ry = Math.sin(t * 0.2) * 0.07 + pointer.current.x * 0.12;
      const rx = baseTiltX - pointer.current.y * 0.06 + Math.sin(t * 0.35) * 0.02;
      rotation.current.y = THREE.MathUtils.lerp(rotation.current.y, ry, 0.03);
      rotation.current.x = THREE.MathUtils.lerp(rotation.current.x, rx, 0.03);
    } else {
      rotation.current.x = baseTiltX;
    }
    const breathe = animate ? 1 + Math.sin(t * 1.1) * 0.006 : 1;
    dummy.position.copy(target);
    dummy.rotation.set(rotation.current.x, rotation.current.y, 0);
    dummy.scale.setScalar(faceScale * breathe);
    dummy.updateMatrix();
    uniforms.uFace.value.copy(dummy.matrix);
    uniforms.uFaceMax.value = data.faceMaxLocal * faceScale;
    uniforms.uSizeScale.value = (rect.height / 480) * 1.25;
  });

  return (
    <>
      <lineSegments geometry={data.webLines} material={materials.webLines} frustumCulled={false} />
      <lineSegments geometry={data.fibres.lineGeo} material={materials.fibreLines} frustumCulled={false} />
      <lineSegments geometry={data.faceLines} material={materials.faceLines} frustumCulled={false} />
      <points geometry={data.skin} material={materials.skin} frustumCulled={false} />
      <points geometry={data.nodes} material={materials.nodes} frustumCulled={false} />
      <points geometry={data.fibres.dotGeo} material={materials.fibreDots} frustumCulled={false} />
    </>
  );
}

export default function HoloFace({ risk = 0.2 }: { risk?: number }) {
  useFullMotion();
  const animate = !prefersReducedMotion();
  const anchor = useRef<HTMLDivElement>(null);
  const replay = useRef(0);

  return (
    <div
      ref={anchor}
      className="relative h-[480px] w-[460px] max-w-full cursor-pointer"
      role="img"
      aria-label="Holographic digital twin face"
      title="Click to re-form the twin"
      onClick={() => replay.current++}
    >
      {createPortal(
        // Portaled to <body> so ancestor transforms (page animations) can't break the fixed full-screen canvas.
        <div className="pointer-events-none fixed inset-0" style={{ zIndex: -5 }} aria-hidden>
          <Canvas
            dpr={[1, 2]}
            camera={{ position: [0, 0, CAMERA_Z], fov: FOV }}
            gl={{ antialias: true, alpha: true, powerPreference: "high-performance" }}
            frameloop={animate ? "always" : "demand"}
          >
            <Suspense fallback={null}>
              <FaceScene anchor={anchor} risk={risk} animate={animate} replay={replay} />
            </Suspense>
          </Canvas>
        </div>,
        document.body,
      )}
    </div>
  );
}
