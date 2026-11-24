import { AnimatePresence, motion } from "framer-motion";
import { ArrowLeft, ArrowRight, Presentation, X } from "lucide-react";
import { useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { TOUR, tour, useTour } from "../lib/tour";

export function DemoTour() {
  const { active, step } = useTour();
  const navigate = useNavigate();
  const location = useLocation();
  const current = TOUR[step];

  useEffect(() => {
    if (active && location.pathname !== current.path) navigate(current.path);
    // Navigate only when the step changes, not when the user browses during the tour.
  }, [active, step]);

  useEffect(() => {
    if (!active) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      if (e.key === "ArrowRight") tour.go(step + 1);
      if (e.key === "ArrowLeft") tour.go(step - 1);
      if (e.key === "Escape") tour.stop();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [active, step]);

  const last = step === TOUR.length - 1;

  return (
    <AnimatePresence>
      {active && (
        <motion.div
          role="dialog"
          aria-label="Guided demo tour"
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 40 }}
          transition={{ type: "spring", stiffness: 260, damping: 28 }}
          className="fixed bottom-6 left-1/2 z-50 w-[min(560px,calc(100vw-2rem))] -translate-x-1/2"
        >
          <div className="glass relative overflow-hidden border-gold/40 p-5 shadow-[0_20px_60px_-10px_rgb(212_175_55/0.35)]">
            <motion.div
              className="absolute top-0 left-0 h-0.5"
              style={{ background: "linear-gradient(90deg, #8C6A1F, #D4AF37, #F5E6B8)" }}
              animate={{ width: `${((step + 1) / TOUR.length) * 100}%` }}
            />
            <div className="flex items-start gap-3">
              <Presentation className="mt-1 h-5 w-5 shrink-0 text-gold" />
              <AnimatePresence mode="wait">
                <motion.div key={step} initial={{ opacity: 0, x: 12 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -12 }} className="flex-1">
                  <p className="text-[10px] tracking-[0.25em] text-taupe uppercase">
                    Demo tour · {step + 1} / {TOUR.length}
                  </p>
                  <h3 className="mt-1 font-display text-lg font-semibold text-metal">{current.title}</h3>
                  <p className="mt-1 text-sm leading-relaxed text-ivory/85">{current.body}</p>
                </motion.div>
              </AnimatePresence>
              <button type="button" aria-label="End tour" onClick={tour.stop} className="text-taupe hover:text-ivory">
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="mt-4 flex items-center justify-between">
              <div className="flex gap-1.5">
                {TOUR.map((s, i) => (
                  <button
                    key={s.path}
                    type="button"
                    aria-label={`Go to step ${i + 1}`}
                    onClick={() => tour.go(i)}
                    className={`h-1.5 rounded-full transition-all ${i === step ? "w-6 bg-gold" : "w-1.5 bg-gold/25 hover:bg-gold/50"}`}
                  />
                ))}
              </div>
              <div className="flex gap-2">
                <button type="button" onClick={() => tour.go(step - 1)} disabled={step === 0} className="btn-ghost px-3 py-1.5 text-xs disabled:opacity-30">
                  <ArrowLeft className="h-3.5 w-3.5" />
                </button>
                <button type="button" onClick={() => (last ? tour.stop() : tour.go(step + 1))} className="btn-gold px-4 py-1.5 text-xs">
                  {last ? "Finish" : "Next"} {!last && <ArrowRight className="h-3.5 w-3.5" />}
                </button>
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
