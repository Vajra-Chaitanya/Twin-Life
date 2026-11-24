import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { dedupe: ["react", "react-dom"] },
  // Pre-bundle the lazily imported 3D stack so Vite never re-optimizes mid-session.
  optimizeDeps: { include: ["three", "@react-three/fiber"] },
  // three.js is ~900 kB but only loaded on demand by the hologram.
  build: { chunkSizeWarningLimit: 1000 },
  server: {
    host: "127.0.0.1",
    port: 5173,
    proxy: {
      // Same-origin proxy to FastAPI, so the backend needs no CORS config.
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
