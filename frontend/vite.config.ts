import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

const apiProxy = {
  // Same-origin proxy to FastAPI, so the backend needs no CORS config.
  "/api": {
    target: "http://127.0.0.1:8000",
    changeOrigin: true,
    rewrite: (path: string) => path.replace(/^\/api/, ""),
  },
};

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { dedupe: ["react", "react-dom"] },
  // Pre-bundle the lazily imported 3D stack so Vite never re-optimizes mid-session.
  optimizeDeps: {
    include: [
      "three",
      "@react-three/fiber",
      "three/addons/loaders/GLTFLoader.js",
      "three/addons/math/MeshSurfaceSampler.js",
      "three/addons/utils/BufferGeometryUtils.js",
    ],
  },
  // three.js is ~900 kB but only loaded on demand by the hologram.
  build: { chunkSizeWarningLimit: 1000, target: "es2022", cssMinify: true },
  server: { host: "127.0.0.1", port: 5173, proxy: apiProxy },
  // `npm run preview` behaves like production but still reaches the dev API.
  preview: { host: "127.0.0.1", port: 4173, proxy: apiProxy },
});
