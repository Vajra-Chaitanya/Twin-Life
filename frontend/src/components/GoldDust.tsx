import { useEffect, useRef } from "react";
import { prefersReducedMotion, useFullMotion } from "../lib/motion";

type Particle = { x: number; y: number; r: number; vy: number; vx: number; phase: number; speed: number };

/** Slowly rising gold dust; renders a single static frame when reduced motion is requested. */
export function GoldDust({ density = 0.00008 }: { density?: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const fullMotion = useFullMotion();

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;

    const reduceMotion = prefersReducedMotion();
    let particles: Particle[] = [];
    let frame = 0;
    let width = 0;
    let height = 0;

    // One pre-rendered glow sprite replaces per-particle shadowBlur, which is the costliest 2D canvas op.
    const sprite = document.createElement("canvas");
    sprite.width = sprite.height = 32;
    const sctx = sprite.getContext("2d")!;
    const glow = sctx.createRadialGradient(16, 16, 0, 16, 16, 16);
    glow.addColorStop(0, "rgba(245, 230, 184, 1)");
    glow.addColorStop(0.25, "rgba(232, 200, 114, 0.9)");
    glow.addColorStop(1, "rgba(212, 175, 55, 0)");
    sctx.fillStyle = glow;
    sctx.fillRect(0, 0, 32, 32);

    const seed = () => {
      const count = Math.round(width * height * density);
      particles = Array.from({ length: count }, () => ({
        x: Math.random() * width,
        y: Math.random() * height,
        r: Math.random() * 1.6 + 0.3,
        vy: -(Math.random() * 0.25 + 0.05),
        vx: (Math.random() - 0.5) * 0.12,
        phase: Math.random() * Math.PI * 2,
        speed: Math.random() * 0.02 + 0.005,
      }));
    };

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const widthChanged = window.innerWidth !== width;
      width = window.innerWidth;
      height = window.innerHeight;
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      // Mobile URL bars change only the height while scrolling; keep particles so nothing jumps.
      if (widthChanged || particles.length === 0) seed();
      if (reduceMotion) draw();
    };

    const draw = () => {
      ctx.clearRect(0, 0, width, height);
      for (const p of particles) {
        p.phase += p.speed;
        if (!reduceMotion) {
          p.x += p.vx;
          p.y += p.vy;
          if (p.y < -5) {
            p.y = height + 5;
            p.x = Math.random() * width;
          }
        }
        ctx.globalAlpha = 0.25 + 0.45 * (0.5 + 0.5 * Math.sin(p.phase));
        const size = p.r * 8;
        ctx.drawImage(sprite, p.x - size / 2, p.y - size / 2, size, size);
      }
      ctx.globalAlpha = 1;
      if (!reduceMotion) frame = requestAnimationFrame(draw);
    };

    resize();
    draw();
    window.addEventListener("resize", resize);
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("resize", resize);
    };
  }, [density, fullMotion]);

  return <canvas ref={canvasRef} aria-hidden className="pointer-events-none fixed inset-0 -z-10" />;
}
