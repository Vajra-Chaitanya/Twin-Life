import { Canvas, useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import * as THREE from "three";
import { prefersReducedMotion, useFullMotion } from "../lib/motion";

type Part =
  | { kind: "ellipsoid"; center: [number, number, number]; radii: [number, number, number]; weight: number }
  | { kind: "capsule"; from: [number, number, number]; to: [number, number, number]; radius: number; weight: number };

// A stylised human built from simple primitives; units are roughly metres scaled to fit the camera.
const BODY: Part[] = [
  { kind: "ellipsoid", center: [0, 1.58, 0], radii: [0.2, 0.25, 0.22], weight: 1.1 },
  { kind: "capsule", from: [0, 1.28, 0], to: [0, 1.4, 0], radius: 0.08, weight: 0.15 },
  { kind: "ellipsoid", center: [0, 0.78, 0], radii: [0.4, 0.5, 0.2], weight: 2.6 },
  { kind: "ellipsoid", center: [0, 0.2, 0], radii: [0.33, 0.2, 0.18], weight: 0.9 },
  { kind: "capsule", from: [-0.46, 1.16, 0], to: [-0.62, 0.55, 0.03], radius: 0.085, weight: 0.55 },
  { kind: "capsule", from: [-0.62, 0.55, 0.03], to: [-0.7, 0.0, 0.08], radius: 0.07, weight: 0.45 },
  { kind: "capsule", from: [0.46, 1.16, 0], to: [0.62, 0.55, 0.03], radius: 0.085, weight: 0.55 },
  { kind: "capsule", from: [0.62, 0.55, 0.03], to: [0.7, 0.0, 0.08], radius: 0.07, weight: 0.45 },
  { kind: "capsule", from: [-0.17, 0.08, 0], to: [-0.2, -0.65, 0.02], radius: 0.12, weight: 0.9 },
  { kind: "capsule", from: [-0.2, -0.65, 0.02], to: [-0.22, -1.42, 0], radius: 0.09, weight: 0.75 },
  { kind: "capsule", from: [0.17, 0.08, 0], to: [0.2, -0.65, 0.02], radius: 0.12, weight: 0.9 },
  { kind: "capsule", from: [0.2, -0.65, 0.02], to: [0.22, -1.42, 0], radius: 0.09, weight: 0.75 },
];

function randomUnit(): THREE.Vector3 {
  const u = Math.random() * 2 - 1;
  const t = Math.random() * Math.PI * 2;
  const s = Math.sqrt(1 - u * u);
  return new THREE.Vector3(s * Math.cos(t), u, s * Math.sin(t));
}

function samplePart(part: Part, out: THREE.Vector3) {
  if (part.kind === "ellipsoid") {
    const d = randomUnit();
    out.set(part.center[0] + d.x * part.radii[0], part.center[1] + d.y * part.radii[1], part.center[2] + d.z * part.radii[2]);
    return;
  }
  const a = new THREE.Vector3(...part.from);
  const b = new THREE.Vector3(...part.to);
  const axis = b.clone().sub(a);
  const point = a.addScaledVector(axis, Math.random());
  const dir = randomUnit();
  dir.sub(axis.clone().normalize().multiplyScalar(dir.dot(axis.clone().normalize()))).normalize();
  out.copy(point.addScaledVector(dir, part.radius));
}

function buildBody(count: number) {
  const total = BODY.reduce((s, p) => s + p.weight, 0);
  const positions = new Float32Array(count * 3);
  const seeds = new Float32Array(count);
  const v = new THREE.Vector3();
  let i = 0;
  for (const part of BODY) {
    const n = Math.round((part.weight / total) * count);
    for (let k = 0; k < n && i < count; k++, i++) {
      samplePart(part, v);
      positions.set([v.x, v.y, v.z], i * 3);
      seeds[i] = Math.random();
    }
  }
  return { positions: positions.subarray(0, i * 3), seeds: seeds.subarray(0, i) };
}

const vertexShader = /* glsl */ `
  uniform float uTime;
  uniform float uScan;
  attribute float aSeed;
  varying float vGlow;
  varying float vSeed;
  void main() {
    vec3 p = position;
    p += normalize(p + vec3(0.0001)) * sin(uTime * 2.0 + aSeed * 40.0) * 0.006;
    vec4 mv = modelViewMatrix * vec4(p, 1.0);
    gl_Position = projectionMatrix * mv;
    float scan = smoothstep(0.18, 0.0, abs(position.y - uScan));
    vGlow = scan;
    vSeed = aSeed;
    gl_PointSize = (1.6 + aSeed * 1.8 + scan * 3.0) * (6.0 / -mv.z);
  }
`;

const fragmentShader = /* glsl */ `
  uniform float uTime;
  uniform vec3 uColor;
  uniform vec3 uHot;
  varying float vGlow;
  varying float vSeed;
  void main() {
    float d = length(gl_PointCoord - 0.5);
    if (d > 0.5) discard;
    float soft = smoothstep(0.5, 0.0, d);
    float flicker = 0.55 + 0.45 * sin(uTime * 3.0 + vSeed * 60.0);
    vec3 color = mix(uColor, uHot, vGlow * 0.8);
    gl_FragColor = vec4(color, soft * (0.35 + 0.5 * flicker + vGlow));
  }
`;

function riskColor(risk: number): THREE.Color {
  return new THREE.Color("#7FB77E").lerp(new THREE.Color("#E9B949"), Math.min(1, risk * 2)).lerp(new THREE.Color("#E5534B"), Math.max(0, risk * 2 - 1));
}

function Hologram({ risk, animate }: { risk: number; animate: boolean }) {
  const group = useRef<THREE.Group>(null);
  const heart = useRef<THREE.Mesh>(null);
  const rings = useRef<THREE.Group>(null);
  const { positions, seeds } = useMemo(() => buildBody(9000), []);
  const uniforms = useMemo(
    () => ({
      uTime: { value: 0 },
      uScan: { value: 0 },
      uColor: { value: new THREE.Color("#D4AF37") },
      uHot: { value: new THREE.Color("#F5E6B8") },
    }),
    [],
  );
  const heartColor = useMemo(() => riskColor(risk), [risk]);
  // Higher risk → faster heartbeat, purely as a visual cue.
  const bpm = 60 + risk * 50;

  useFrame((state, delta) => {
    const t = state.clock.elapsedTime;
    uniforms.uTime.value = t;
    uniforms.uScan.value = -1.5 + ((t * 0.45) % 1) * 3.4;
    if (group.current && animate) {
      group.current.rotation.y += delta * 0.25;
      group.current.rotation.x = THREE.MathUtils.lerp(group.current.rotation.x, state.pointer.y * 0.15, 0.05);
    }
    if (heart.current) {
      const phase = (t * bpm) / 60;
      const beat = Math.exp(-((phase % 1) * 10)) + 0.6 * Math.exp(-(((phase + 0.7) % 1) * 12));
      heart.current.scale.setScalar(0.07 + beat * 0.05);
    }
    if (rings.current && animate) {
      rings.current.children.forEach((ring, i) => {
        ring.rotation.z += delta * (0.3 + i * 0.15) * (i % 2 ? -1 : 1);
      });
    }
  });

  return (
    <group position={[0, -0.1, 0]}>
      <group ref={group}>
        <points>
          <bufferGeometry>
            <bufferAttribute attach="attributes-position" args={[positions, 3]} />
            <bufferAttribute attach="attributes-aSeed" args={[seeds, 1]} />
          </bufferGeometry>
          <shaderMaterial
            vertexShader={vertexShader}
            fragmentShader={fragmentShader}
            uniforms={uniforms}
            transparent
            depthWrite={false}
            blending={THREE.AdditiveBlending}
          />
        </points>
        <mesh ref={heart} position={[0.08, 0.92, 0.12]}>
          <sphereGeometry args={[1, 24, 24]} />
          <meshBasicMaterial color={heartColor} transparent opacity={0.9} blending={THREE.AdditiveBlending} />
        </mesh>
        <pointLight position={[0.08, 0.92, 0.3]} color={heartColor} intensity={2} distance={1.5} />
      </group>

      <group ref={rings} position={[0, 0.3, 0]}>
        {[
          { r: 1.05, color: "#E0A899", tilt: [1.35, 0, 0.3] },
          { r: 1.25, color: "#D4AF37", tilt: [1.5, 0.25, 0] },
          { r: 1.45, color: "#C9CED6", tilt: [1.25, -0.3, 0] },
        ].map(({ r, color, tilt }) => (
          <mesh key={r} rotation={tilt as [number, number, number]}>
            <torusGeometry args={[r, 0.006, 8, 160]} />
            <meshBasicMaterial color={color} transparent opacity={0.55} blending={THREE.AdditiveBlending} />
          </mesh>
        ))}
      </group>

      <mesh position={[0, -1.5, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[0.55, 0.62, 96]} />
        <meshBasicMaterial color="#D4AF37" transparent opacity={0.6} blending={THREE.AdditiveBlending} side={THREE.DoubleSide} />
      </mesh>
      <mesh position={[0, -1.5, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <circleGeometry args={[0.55, 64]} />
        <meshBasicMaterial color="#D4AF37" transparent opacity={0.08} blending={THREE.AdditiveBlending} />
      </mesh>
    </group>
  );
}

export default function HoloTwin({ risk = 0.2 }: { risk?: number }) {
  useFullMotion();
  const animate = !prefersReducedMotion();
  return (
    <div className="relative h-[460px] w-[440px] max-w-full" aria-label="Holographic digital twin" role="img">
      <div className="absolute inset-x-10 bottom-6 h-24 rounded-full bg-gold/20 blur-3xl" aria-hidden />
      <Canvas
        dpr={[1, 1.75]}
        camera={{ position: [0, 0.2, 5], fov: 42 }}
        gl={{ antialias: true, alpha: true, powerPreference: "high-performance" }}
        frameloop={animate ? "always" : "demand"}
      >
        <Hologram risk={risk} animate={animate} />
      </Canvas>
    </div>
  );
}
