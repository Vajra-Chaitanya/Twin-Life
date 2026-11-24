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

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      width = window.innerWidth;
      height = window.innerHeight;
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
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
        const alpha = 0.25 + 0.45 * (0.5 + 0.5 * Math.sin(p.phase));
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(232, 200, 114, ${alpha})`;
        ctx.shadowColor = "rgba(212, 175, 55, 0.8)";
        ctx.shadowBlur = p.r * 4;
        ctx.fill();
      }
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
