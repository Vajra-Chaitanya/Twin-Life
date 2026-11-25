import { AnimatePresence, MotionConfig, motion } from "framer-motion";
import { useEffect, useState } from "react";
import { markSplashDone, isSplashDone } from "../lib/splash";

/**
 * Splash intro animation sequence:
 *   1. Left ring draws in from nothing              (0 → 0.9s)
 *   2. Left ring slides right to make room          (0.9 → 1.5s)
 *   3. Right ring rotates in alongside              (1.1 → 2.0s)
 *   4. "TWINLIFE AI" text fades up                  (2.0 → 2.6s)
 *   5. Gold underline scales in                     (2.3 → 2.9s)
 *   6. Hold briefly, then fade the whole overlay    (3.6s → 4.3s)
 *
 * Only plays once per session on the home screen.
 * Skippable: click anywhere or press Escape.
 */

const RING_DRAW = { duration: 0.9, ease: [0.65, 0, 0.35, 1] } as const;

export function SplashIntro() {
  // If the splash already played this session, never show it again.
  const [visible, setVisible] = useState(() => !isSplashDone());

  useEffect(() => {
    const close = () => {
      setVisible(false);
      markSplashDone();
    };
    const timer = window.setTimeout(close, 4300);
    const skip = (event: KeyboardEvent) => event.key === "Escape" && close();
    window.addEventListener("keydown", skip);
    return () => {
      window.clearTimeout(timer);
      window.removeEventListener("keydown", skip);
    };
  }, []);

  return (
    <MotionConfig reducedMotion="never">
    <AnimatePresence>
      {visible && (
        <motion.div
          key="splash"
          role="status"
          aria-label="Loading TwinLife AI"
          onClick={() => {
            setVisible(false);
            markSplashDone();
          }}
          initial={{ opacity: 1 }}
          exit={{ opacity: 0, scale: 1.04, filter: "blur(6px)" }}
          transition={{ duration: 0.7, ease: "easeInOut" }}
          className="fixed inset-0 z-[100] flex cursor-pointer flex-col items-center justify-center bg-ink"
        >
          {/* Background glow — fades in after the rings settle */}
          <motion.div
            className="absolute h-72 w-72 rounded-full bg-gold/10 blur-3xl"
            initial={{ opacity: 0, scale: 0.6 }}
            animate={{ opacity: [0, 0.9, 0.5], scale: [0.6, 1.15, 1] }}
            transition={{ duration: 2, delay: 0.6 }}
          />

          {/* ---- Twin rings SVG ---- */}
          <svg viewBox="8 12 48 40" className="relative h-40 w-48 sm:h-52 sm:w-64" aria-hidden>
            <defs>
              <linearGradient id="splash-gold" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0" stopColor="#F5E6B8" />
                <stop offset="0.5" stopColor="#D4AF37" />
                <stop offset="1" stopColor="#8C6A1F" />
              </linearGradient>
            </defs>

            {/* LEFT ring: draws in at center, then slides left to cx=24 */}
            <motion.circle
              cy="32"
              r="13"
              fill="none"
              stroke="url(#splash-gold)"
              strokeWidth="3"
              strokeLinecap="round"
              initial={{ cx: 32, pathLength: 0, opacity: 0 }}
              animate={{
                cx:         [32, 32, 24],      // start center → stay → slide left
                pathLength: [0,  1,  1 ],      // draw in → done → keep
                opacity:    1,
              }}
              transition={{
                ...RING_DRAW,
                duration: 1.5,
                times: [0, 0.6, 1],            // 0–0.9s draw, 0.9–1.5s slide
              }}
            />

            {/* RIGHT ring: starts hidden, rotates in from behind once left starts sliding */}
            <motion.circle
              cy="32"
              r="13"
              fill="none"
              stroke="url(#splash-gold)"
              strokeWidth="3"
              strokeLinecap="round"
              style={{ transformOrigin: "32px 32px" }}
              initial={{ cx: 32, pathLength: 0, rotate: 180, opacity: 0 }}
              animate={{
                cx:         [32, 40],           // start center → slide right
                pathLength: [0,  1 ],           // draw in
                rotate:     [180, 0],           // rotate into place
                opacity:    1,
              }}
              transition={{
                duration: 1.0,
                delay: 1.0,                     // starts after left ring is mostly drawn
                ease: [0.65, 0, 0.35, 1],
              }}
            />
          </svg>

          {/* ---- "TWINLIFE AI" text ---- */}
          <motion.p
            className="relative mt-6 font-display text-2xl font-semibold tracking-[0.2em] uppercase"
            initial={{ opacity: 0, y: 14, letterSpacing: "0.5em" }}
            animate={{ opacity: 1, y: 0, letterSpacing: "0.2em" }}
            transition={{ duration: 0.8, delay: 2.1, ease: "easeOut" }}
          >
            <span className="text-metal">TwinLife</span>{" "}
            <span className="text-taupe">AI</span>
          </motion.p>

          {/* ---- Gold underline ---- */}
          <motion.span
            className="relative mt-3 h-px w-40 origin-center bg-gradient-to-r from-transparent via-gold to-transparent"
            initial={{ scaleX: 0, opacity: 0 }}
            animate={{ scaleX: 1, opacity: 1 }}
            transition={{ duration: 0.7, delay: 2.5, ease: "easeOut" }}
          />
        </motion.div>
      )}
    </AnimatePresence>
    </MotionConfig>
  );
}
