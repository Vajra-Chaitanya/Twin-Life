// One-off: builds public/models/face-lowpoly.json (a faceted head) from the CC BY 3.0 Lee Perry-Smith scan.
// Run: node scripts/lowpoly-face.mjs [targetVertices]
import { readFileSync, writeFileSync } from "node:fs";
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { SimplifyModifier } from "three/addons/modifiers/SimplifyModifier.js";
import { mergeVertices } from "three/addons/utils/BufferGeometryUtils.js";

const target = Number(process.argv[2] ?? 650);
const src = new URL("../public/models/LeePerrySmith.glb", import.meta.url);
const out = new URL("../public/models/face-lowpoly.json", import.meta.url);

const buf = readFileSync(src);
const gltf = await new Promise((resolve, reject) =>
  new GLTFLoader().parse(buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength), "", resolve, reject),
);

let mesh;
gltf.scene.traverse((o) => {
  if (!mesh && o.isMesh) mesh = o;
});
let g = mesh.geometry.clone();
for (const name of Object.keys(g.attributes)) if (name !== "position") g.deleteAttribute(name);
g = mergeVertices(g, 1e-4);

// Keep head and neck only (model is ~8 units tall, facing +Z; shoulders start near y = -2.6).
const pos = g.getAttribute("position");
const idx = g.index.array;
const kept = [];
for (let t = 0; t < idx.length; t += 3) {
  const ys = [idx[t], idx[t + 1], idx[t + 2]].map((i) => pos.getY(i));
  if (Math.min(...ys) > -2.6) kept.push(idx[t], idx[t + 1], idx[t + 2]);
}
g.setIndex(kept);
g = mergeVertices(g.toNonIndexed(), 1e-4);

const before = g.getAttribute("position").count;
const simplified = await new SimplifyModifier().modify(g, Math.max(0, before - target));
const merged = mergeVertices(simplified, 1e-4);
const p = merged.getAttribute("position");
const positions = Array.from(p.array, (v) => Math.round(v * 1000) / 1000);
const indices = Array.from(merged.index.array);

writeFileSync(out, JSON.stringify({ source: "Lee Perry-Smith head scan (CC BY 3.0), simplified", positions, indices }));
console.log(`vertices ${before} -> ${p.count}, triangles ${indices.length / 3}`);
