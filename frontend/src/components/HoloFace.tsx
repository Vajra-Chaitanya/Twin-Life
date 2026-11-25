import { Canvas, useFrame, useLoader, useThree } from "@react-three/fiber";
import { Suspense, useEffect, useMemo, useRef, useState, type MutableRefObject, type RefObject } from "react";
import { createPortal } from "react-dom";
import * as THREE from "three";
import { prefersReducedMotion, useFullMotion } from "../lib/motion";
import { onSplashDone } from "../lib/splash";

// Low-poly head generated offline by scripts/lowpoly-face.mjs from the CC BY 3.0 Lee Perry-Smith scan.
const MODEL_URL = "/models/face-lowpoly.json";
const HEAD_HEIGHT = 3;
const EYE_LEVEL_MODEL_Y = 1.62;
const INTRO_SECONDS = 7;
const CAMERA_Z = 6;
const FOV = 35;

type LowPoly = { positions: number[]; indices: number[] };

function buildHead(json: LowPoly) {
  const src = new THREE.BufferGeometry();
  src.setAttribute("position", new THREE.Float32BufferAttribute(json.positions, 3));
  src.setIndex(json.indices);
  src.computeBoundingBox();
  const box = src.boundingBox!;
  const center = box.getCenter(new THREE.Vector3());
  const scale = HEAD_HEIGHT / box.getSize(new THREE.Vector3()).y;
  src.translate(-center.x, -center.y, -center.z);
  src.scale(scale, scale, scale);
  const eyeY = (EYE_LEVEL_MODEL_Y - center.y) * scale;

  const pos = src.getAttribute("position") as THREE.BufferAttribute;
  const idx = src.index!.array;
  const vCount = pos.count;
  const verts = Array.from({ length: vCount }, (_, i) => new THREE.Vector3().fromBufferAttribute(pos, i));

  // Web start positions: a loose halo hugging the head, pulled slightly toward each vertex.
  const scatter = verts.map((v) => {
    const a = Math.random() * Math.PI * 2;
    const r = 0.9 + Math.random() ** 0.7 * 1.1;
    return new THREE.Vector3(Math.cos(a) * r * 0.9, Math.sin(a) * r * 1.1, (Math.random() - 0.5) * 1.6).lerp(v, 0.2);
  });
  const seeds = verts.map(() => Math.random());

  // Flat-shaded facets.
  const solid = src.toNonIndexed();
  solid.computeVertexNormals();
  const facetSeed = new Float32Array(solid.getAttribute("position").count);
  for (let f = 0; f < facetSeed.length; f += 3) facetSeed.fill(Math.random(), f, f + 3);
  solid.setAttribute("aFacet", new THREE.BufferAttribute(facetSeed, 1));

  // Unique edges with dihedral angle, so the sharpest creases can glow.
  const faceNormal = (t: number) =>
    new THREE.Triangle(verts[idx[t]], verts[idx[t + 1]], verts[idx[t + 2]]).getNormal(new THREE.Vector3());
  const edgeFaces = new Map<string, { a: number; b: number; normals: THREE.Vector3[] }>();
  for (let t = 0; t < idx.length; t += 3) {
    const n = faceNormal(t);
    for (const [a, b] of [[idx[t], idx[t + 1]], [idx[t + 1], idx[t + 2]], [idx[t + 2], idx[t]]]) {
      const key = a < b ? `${a}-${b}` : `${b}-${a}`;
      const entry = edgeFaces.get(key) ?? { a: Math.min(a, b), b: Math.max(a, b), normals: [] };
      entry.normals.push(n);
      edgeFaces.set(key, entry);
    }
  }
  const edges = [...edgeFaces.values()];
  const count = edges.length * 2;
  const buf = {
    position: new Float32Array(count * 3), aOther: new Float32Array(count * 3),
    aScatter: new Float32Array(count * 3), aOtherScatter: new Float32Array(count * 3),
    aSeed: new Float32Array(count), aOtherSeed: new Float32Array(count),
    aGlow: new Float32Array(count), aEdgeSeed: new Float32Array(count), aT: new Float32Array(count),
  };
  const lengths: number[] = [];
  edges.forEach((e, k) => {
    const angle = e.normals.length === 2 ? e.normals[0].angleTo(e.normals[1]) : 0;
    const frontFacing = Math.min(verts[e.a].z, verts[e.b].z) > -0.1;
    const glow = frontFacing && (angle > 0.5 ? Math.random() < 0.22 : Math.random() < 0.02) ? 1 : 0;
    const edgeSeed = Math.random();
    lengths.push(verts[e.a].distanceTo(verts[e.b]));
    for (const [v, self, peer, t] of [[2 * k, e.a, e.b, 0], [2 * k + 1, e.b, e.a, 1]] as const) {
      buf.position.set(verts[self].toArray(), v * 3);
      buf.aOther.set(verts[peer].toArray(), v * 3);
      buf.aScatter.set(scatter[self].toArray(), v * 3);
      buf.aOtherScatter.set(scatter[peer].toArray(), v * 3);
      buf.aSeed[v] = seeds[self];
      buf.aOtherSeed[v] = seeds[peer];
      buf.aGlow[v] = glow;
      buf.aEdgeSeed[v] = edgeSeed;
      buf.aT[v] = t;
    }
  });
  const lines = new THREE.BufferGeometry();
  for (const [name, array] of Object.entries(buf)) {
    lines.setAttribute(name, new THREE.BufferAttribute(array, array.length === count * 3 ? 3 : 1));
  }

  const nodes = new THREE.BufferGeometry();
  nodes.setAttribute("position", new THREE.Float32BufferAttribute(verts.flatMap((v) => v.toArray()), 3));
  nodes.setAttribute("aScatter", new THREE.Float32BufferAttribute(scatter.flatMap((v) => v.toArray()), 3));
  nodes.setAttribute("aSeed", new THREE.Float32BufferAttribute(seeds, 1));

  lengths.sort((x, y) => x - y);
  return { solid, lines, nodes, eyeY, maxEdge: lengths[Math.floor(lengths.length * 0.95)] * 1.4 };
}

const COMMON = /* glsl */ `
  uniform float uProgress;
  uniform float uTime;
  uniform mat4 uFace;
  float nodeEase(float seed) {
    float t = clamp((uProgress - 0.28 - seed * 0.2) / 0.4, 0.0, 1.0);
    return t < 0.5 ? 4.0 * t * t * t : 1.0 - pow(-2.0 * t + 2.0, 3.0) / 2.0;
  }
  // Web nodes blink in and out independently before the web condenses into the head.
  float flicker(float seed) {
    return smoothstep(0.2, 0.95, 0.5 + 0.5 * sin(uTime * (0.7 + seed * 1.1) + seed * 40.0));
  }
  vec3 nodePos(vec3 face, vec3 scatter, float seed) {
    float e = nodeEase(seed);
    vec3 drift = vec3(sin(uTime * 0.4 + seed * 40.0), cos(uTime * 0.35 + seed * 31.0), sin(uTime * 0.3 + seed * 17.0)) * 0.06 * (1.0 - e);
    return (uFace * vec4(mix(scatter + drift, face, e), 1.0)).xyz;
  }
`;

const solidVertex = /* glsl */ `
  uniform mat4 uFace;
  attribute float aFacet;
  varying vec3 vNormal;
  varying float vFacet;
  varying float vY;
  void main() {
    vNormal = normalize(mat3(uFace) * normal);
    vFacet = aFacet;
    vY = position.y;
    gl_Position = projectionMatrix * viewMatrix * (uFace * vec4(position, 1.0));
  }
`;

const solidFragment = /* glsl */ `
  uniform float uSolid;
  uniform vec3 uWarm;
  uniform vec3 uCool;
  uniform vec3 uCyan;
  uniform vec3 uAmbient;
  varying vec3 vNormal;
  varying float vFacet;
  varying float vY;
  void main() {
    vec3 n = normalize(vNormal);
    float warm = max(dot(n, normalize(vec3(-0.9, 0.1, 0.55))), 0.0);
    float cool = max(dot(n, normalize(vec3(0.85, 0.3, 0.5))), 0.0);
    float top = max(dot(n, normalize(vec3(0.1, 1.0, 0.35))), 0.0);
    float fresnel = pow(1.0 - abs(n.z), 3.0);
    vec3 col = uAmbient
      + uWarm * pow(warm, 1.2) * 0.95
      + uCool * pow(cool, 1.1) * 0.85
      + uCyan * pow(top, 1.8) * 0.75 * smoothstep(-0.6, 0.2, vY)
      + uCyan * fresnel * 0.22;
    // Lavender where warm and cool light overlap, like the reference.
    col += vec3(0.96, 0.90, 0.72) * warm * cool * 0.4;
    col *= 0.88 + vFacet * 0.2;
    // Soften only the very bottom edge of the neck.
    float neck = smoothstep(-1.5, -1.25, vY);
    gl_FragColor = vec4(col, uSolid * neck);
  }
`;

const lineVertex = /* glsl */ `
  ${COMMON}
  uniform float uSolid;
  uniform float uMaxEdge;
  attribute vec3 aOther;
  attribute vec3 aScatter;
  attribute vec3 aOtherScatter;
  attribute float aSeed;
  attribute float aOtherSeed;
  attribute float aGlow;
  attribute float aEdgeSeed;
  attribute float aT;
  varying float vAlpha;
  varying float vGlow;
  varying float vT;
  varying float vEdgeSeed;
  void main() {
    vec3 p = nodePos(position, aScatter, aSeed);
    vec3 q = nodePos(aOther, aOtherScatter, aOtherSeed);
    float e = 0.5 * (nodeEase(aSeed) + nodeEase(aOtherSeed));
    float len = distance(p, q) / length(mat3(uFace) * vec3(1.0, 0.0, 0.0));
    float blink = mix(min(flicker(aSeed), flicker(aOtherSeed)), 1.0, e);
    float webAlpha = smoothstep(uMaxEdge * 2.5, uMaxEdge, len) * 0.45 * blink;
    // Once solid, only the selected "crack" edges remain, glowing cyan.
    vAlpha = mix(webAlpha, aGlow, uSolid) * smoothstep(0.0, 0.08, uProgress) * smoothstep(-1.5, -1.25, position.y);
    vGlow = aGlow * uSolid;
    vT = aT;
    vEdgeSeed = aEdgeSeed;
    vec4 clip = projectionMatrix * viewMatrix * vec4(p, 1.0);
    // Nudge toward the camera so edges sit on top of their own facets.
    clip.z -= 0.002 * clip.w;
    gl_Position = clip;
  }
`;

const lineFragment = /* glsl */ `
  uniform float uTime;
  uniform vec3 uCyan;
  varying float vAlpha;
  varying float vGlow;
  varying float vT;
  varying float vEdgeSeed;
  void main() {
    float travel = fract(uTime * (0.25 + vEdgeSeed * 0.35) + vEdgeSeed);
    float pulse = exp(-pow(travel - vT, 2.0) / 0.01);
    float breathe = 0.65 + 0.35 * sin(uTime * 1.5 + vEdgeSeed * 30.0);
    float energy = mix(1.0, breathe + pulse * 1.2, vGlow);
    gl_FragColor = vec4(uCyan * energy, vAlpha * energy);
  }
`;

const nodeVertex = /* glsl */ `
  ${COMMON}
  uniform float uSolid;
  uniform float uPixelRatio;
  attribute vec3 aScatter;
  attribute float aSeed;
  varying float vAlpha;
  void main() {
    vec3 p = nodePos(position, aScatter, aSeed);
    vec4 mv = viewMatrix * vec4(p, 1.0);
    gl_Position = projectionMatrix * mv;
    float e = nodeEase(aSeed);
    vAlpha = smoothstep(0.0, 0.08, uProgress) * mix(flicker(aSeed), 0.8, e) * (1.0 - uSolid) * smoothstep(-1.5, -1.25, position.y);
    gl_PointSize = 6.0 * uPixelRatio * (${CAMERA_Z.toFixed(1)} / -mv.z);
  }
`;

const nodeFragment = /* glsl */ `
  uniform vec3 uCyan;
  varying float vAlpha;
  void main() {
    float d = length(gl_PointCoord - 0.5);
    float g = smoothstep(0.12, 0.0, d) + exp(-d * d * 22.0) * 0.5;
    if (g < 0.01) discard;
    gl_FragColor = vec4(uCyan, g * vAlpha);
  }
`;

const bandVertex = /* glsl */ `
  uniform mat4 uBand;
  varying vec2 vUv;
  void main() {
    vUv = uv * 2.0 - 1.0;
    gl_Position = projectionMatrix * viewMatrix * (uBand * vec4(position, 1.0));
  }
`;

const bandFragment = /* glsl */ `
  uniform float uBandOn;
  uniform float uTime;
  uniform vec3 uBandColor;
  varying vec2 vUv;
  void main() {
    float y = vUv.y;
    float core = exp(-y * y / 0.004);
    float haze = exp(-y * y / 0.08) * 0.35;
    float ends = exp(-vUv.x * vUv.x / 0.35);
    float shimmer = 0.9 + 0.1 * sin(uTime * 2.0 + vUv.x * 6.0);
    gl_FragColor = vec4(uBandColor, (core + haze) * ends * shimmer * uBandOn);
  }
`;

function riskTint(risk: number): THREE.Color {
  return new THREE.Color("#FFFFFF").lerp(new THREE.Color(risk > 0.5 ? "#F5E6B8" : "#FFFFFF"), Math.min(0.3, Math.abs(risk - 0.5) * 0.6));
}

type SceneProps = {
  anchor: RefObject<HTMLDivElement | null>; risk: number; animate: boolean; replay: MutableRefObject<number>; introRunning: boolean;
};

function HeadScene({ anchor, risk, animate, replay, introRunning }: SceneProps) {
  const json = useLoader(THREE.FileLoader, MODEL_URL) as unknown as string;
  const { camera, invalidate } = useThree();
  const data = useMemo(() => buildHead(JSON.parse(json) as LowPoly), [json]);
  // Switching to on-demand rendering when the intro ends needs one fresh frame of the finished face.
  useEffect(() => {
    invalidate();
    const settle = window.setTimeout(invalidate, 100);
    return () => window.clearTimeout(settle);
  }, [introRunning, invalidate]);

  const uniforms = useMemo(
    () => ({
      uTime: { value: 0 },
      uProgress: { value: animate ? 0 : 1 },
      uSolid: { value: animate ? 0 : 1 },
      uBandOn: { value: animate ? 0 : 1 },
      uFace: { value: new THREE.Matrix4() },
      uBand: { value: new THREE.Matrix4() },
      uPixelRatio: { value: Math.min(window.devicePixelRatio, 2) },
      uMaxEdge: { value: data.maxEdge },
      uWarm: { value: new THREE.Color("#D4AF37") },
      uCool: { value: new THREE.Color("#F3EEE3") },
      uCyan: { value: new THREE.Color("#FFFFFF") },
      uAmbient: { value: new THREE.Color("#15120B") },
      uBandColor: { value: new THREE.Color("#FFFFFF") },
    }),
    [animate, data],
  );
  const materials = useMemo(
    () => ({
      solid: new THREE.ShaderMaterial({
        vertexShader: solidVertex, fragmentShader: solidFragment, uniforms, transparent: true, depthWrite: true,
      }),
      lines: new THREE.ShaderMaterial({
        vertexShader: lineVertex, fragmentShader: lineFragment, uniforms, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
      }),
      nodes: new THREE.ShaderMaterial({
        vertexShader: nodeVertex, fragmentShader: nodeFragment, uniforms, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
      }),
      band: new THREE.ShaderMaterial({
        vertexShader: bandVertex, fragmentShader: bandFragment, uniforms, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
      }),
    }),
    [uniforms],
  );
  const bandGeometry = useMemo(() => new THREE.PlaneGeometry(1, 1), []);

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
    // Wall-clock timing: the R3F clock resets whenever the frameloop mode changes.
    const now = performance.now() / 1000;
    if (start.current === null || seenReplay.current !== replay.current) {
      start.current = now;
      seenReplay.current = replay.current;
    }
    const progress = Math.min(1, Math.max(0, (now - start.current) / INTRO_SECONDS));
    uniforms.uTime.value = t;
    uniforms.uProgress.value = progress;
    uniforms.uSolid.value = THREE.MathUtils.smoothstep(progress, 0.62, 0.9);
    uniforms.uBandOn.value = THREE.MathUtils.smoothstep(progress, 0.8, 1.0);
    uniforms.uBandColor.value.lerp(riskTint(risk), 0.05);
    materials.solid.depthWrite = uniforms.uSolid.value > 0.5;

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
    const scale = ((rect.height / window.innerHeight) * frustumH * 0.92) / HEAD_HEIGHT;

    if (animate) {
      const ry = Math.sin(t * 0.22) * 0.12 + pointer.current.x * 0.35;
      const rx = -pointer.current.y * 0.1 + Math.sin(t * 0.35) * 0.02;
      rotation.current.y = THREE.MathUtils.lerp(rotation.current.y, ry, 0.035);
      rotation.current.x = THREE.MathUtils.lerp(rotation.current.x, rx, 0.035);
    }
    const breathe = animate ? 1 + Math.sin(t * 1.1) * 0.005 : 1;
    dummy.position.copy(target);
    dummy.rotation.set(rotation.current.x, rotation.current.y, 0);
    dummy.scale.setScalar(scale * breathe);
    dummy.updateMatrix();
    uniforms.uFace.value.copy(dummy.matrix);

    // Light band sits behind the head at eye level and does not rotate with it.
    dummy.position.set(target.x, target.y + data.eyeY * scale, target.z - 1.6 * scale);
    dummy.rotation.set(0, 0, 0);
    dummy.scale.set(scale * 9, scale * 1.4, 1);
    dummy.updateMatrix();
    uniforms.uBand.value.copy(dummy.matrix);
  });

  return (
    <>
      <mesh geometry={bandGeometry} material={materials.band} frustumCulled={false} renderOrder={0} />
      <mesh geometry={data.solid} material={materials.solid} frustumCulled={false} renderOrder={1} />
      <lineSegments geometry={data.lines} material={materials.lines} frustumCulled={false} renderOrder={2} />
      <points geometry={data.nodes} material={materials.nodes} frustumCulled={false} renderOrder={3} />
    </>
  );
}

/** True while the element is on screen and the tab is visible; the full-screen canvas idles otherwise. */
function useOnScreen(ref: RefObject<HTMLElement | null>) {
  const [inView, setInView] = useState(true);
  const [tabVisible, setTabVisible] = useState(() => document.visibilityState === "visible");
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(([entry]) => setInView(entry.isIntersecting), { rootMargin: "100px" });
    observer.observe(el);
    const onVisibility = () => setTabVisible(document.visibilityState === "visible");
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      observer.disconnect();
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [ref]);
  return inView && tabVisible;
}

export default function HoloFace({ risk = 0.2 }: { risk?: number }) {
  useFullMotion();
  const anchor = useRef<HTMLDivElement>(null);
  const replay = useRef(0);
  const visible = useOnScreen(anchor);
  const animate = !prefersReducedMotion();
  // The formation intro always plays; only the ongoing sway honours reduced motion.
  const [introUntil, setIntroUntil] = useState(() => Date.now() + (INTRO_SECONDS + 1) * 1000);
  const [, tick] = useState(0);
  const replayIntro = () => {
    replay.current++;
    setIntroUntil(Date.now() + (INTRO_SECONDS + 1) * 1000);
  };
  // The intro may already have run hidden behind the startup splash; form the face again as it fades.
  useEffect(() => onSplashDone(replayIntro), []);
  useEffect(() => {
    const timer = window.setTimeout(() => tick((n) => n + 1), Math.max(0, introUntil - Date.now()));
    return () => window.clearTimeout(timer);
  }, [introUntil]);
  const introRunning = Date.now() < introUntil;

  return (
    <div
      ref={anchor}
      className="relative aspect-[23/24] w-[460px] max-w-full cursor-pointer"
      role="img"
      aria-label="Holographic digital twin face"
      title="Click to re-form the twin"
      onClick={replayIntro}
    >
      {createPortal(
        // Portaled to <body> so ancestor transforms (page animations) can't break the fixed full-screen canvas.
        <div className="pointer-events-none fixed inset-0" style={{ zIndex: -5 }} aria-hidden>
          <Canvas
            dpr={[1, 2]}
            camera={{ position: [0, 0, CAMERA_Z], fov: FOV }}
            gl={{ antialias: true, alpha: true, powerPreference: "high-performance" }}
            frameloop={(animate || introRunning) && visible ? "always" : "demand"}
          >
            <Suspense fallback={null}>
              <HeadScene anchor={anchor} risk={risk} animate={animate} replay={replay} introRunning={introRunning} />
            </Suspense>
          </Canvas>
        </div>,
        document.body,
      )}
    </div>
  );
}
