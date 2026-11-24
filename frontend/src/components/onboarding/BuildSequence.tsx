import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle, ArrowRight, Check, Loader2, RotateCcw } from "lucide-react";
import { Link } from "react-router-dom";
import type { Snapshot } from "../../lib/types";
import { ScoreRing } from "../ui/ScoreRing";

export type LogLine = { id: number; text: string; status: "running" | "done" | "error" };

type Props = {
  logs: LogLine[];
  result: Snapshot | null;
  error: string | null;
  onRetry: () => void;
  onEdit: () => void;
};

function ScannerCore({ complete }: { complete: boolean }) {
  return (
    <div className="relative flex h-56 w-56 items-center justify-center" aria-hidden>
      {[0, 1, 2].map((i) => (
        <motion.span
          key={i}
          className="absolute rounded-full border border-gold/40"
          style={{ width: 80 + i * 60, height: 80 + i * 60 }}
          animate={complete ? { scale: 1, opacity: 0.3 } : { scale: [0.9, 1.08, 0.9], opacity: [0.2, 0.7, 0.2] }}
          transition={{ duration: 2.4, repeat: complete ? 0 : Infinity, delay: i * 0.3 }}
        />
      ))}
      <motion.div
        className="absolute h-full w-full rounded-full"
        style={{ background: "conic-gradient(from 0deg, transparent 0deg, rgb(212 175 55 / 0.45) 40deg, transparent 80deg)" }}
        animate={{ rotate: 360 }}
        transition={{ duration: complete ? 6 : 1.6, repeat: Infinity, ease: "linear" }}
      />
      <motion.div
        className="relative h-20 w-20 rounded-full"
        style={{
          background: "radial-gradient(circle at 35% 30%, #F5E6B8, #D4AF37 45%, #5c4512 100%)",
          boxShadow: "0 0 50px rgb(212 175 55 / 0.6)",
        }}
        animate={{ scale: complete ? [1, 1.25, 1] : [1, 1.06, 1] }}
        transition={{ duration: complete ? 0.8 : 1.2, repeat: complete ? 0 : Infinity }}
      />
    </div>
  );
}

export function BuildSequence({ logs, result, error, onRetry, onEdit }: Props) {
  return (
    <div className="mx-auto flex max-w-4xl flex-col items-center gap-8">
      <ScannerCore complete={Boolean(result)} />
      <motion.h2
        key={result ? "done" : error ? "error" : "building"}
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center font-display text-3xl font-bold"
      >
        {result ? (
          <span className="text-metal-animated">Your twin is alive.</span>
        ) : error ? (
          <span className="text-risk">Calibration interrupted</span>
        ) : (
          <span className="text-metal">Building your twin…</span>
        )}
      </motion.h2>

      <div className="glass w-full max-w-xl p-5 font-mono text-sm" role="log" aria-live="polite">
        <div className="mb-3 flex gap-1.5" aria-hidden>
          <span className="h-2.5 w-2.5 rounded-full bg-risk/70" />
          <span className="h-2.5 w-2.5 rounded-full bg-warn/70" />
          <span className="h-2.5 w-2.5 rounded-full bg-good/70" />
        </div>
        <ul className="flex flex-col gap-1.5">
          <AnimatePresence initial={false}>
            {logs.map((line) => (
              <motion.li
                key={line.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                className="flex items-center gap-2"
              >
                <span className="text-gold">&gt;</span>
                <span className={line.status === "error" ? "text-risk" : "text-ivory/90"}>{line.text}</span>
                <span className="ml-auto">
                  {line.status === "running" && <Loader2 className="h-3.5 w-3.5 animate-spin text-gold" />}
                  {line.status === "done" && <Check className="h-3.5 w-3.5 text-good" />}
                  {line.status === "error" && <AlertTriangle className="h-3.5 w-3.5 text-risk" />}
                </span>
              </motion.li>
            ))}
          </AnimatePresence>
        </ul>
      </div>

      {error && (
        <div className="flex flex-col items-center gap-4 text-center">
          <p className="max-w-md text-sm text-taupe">{error}</p>
          <div className="flex gap-3">
            <button type="button" onClick={onRetry} className="btn-gold">
              <RotateCcw className="h-4 w-4" /> Retry
            </button>
            <button type="button" onClick={onEdit} className="btn-ghost">
              Edit inputs
            </button>
          </div>
        </div>
      )}

      {result && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.6 }}
          className="flex w-full flex-col items-center gap-8"
        >
          <div className="flex flex-wrap justify-center gap-10">
            <ScoreRing value={result.health.overall_health_score} label="Health" color="#E0A899" />
            <ScoreRing value={result.finance.financial_stability_score} label="Financial stability" color="#D4AF37" delay={0.15} />
            <ScoreRing value={result.insurance.insurance_adequacy_score} label="Insurance adequacy" color="#C9CED6" delay={0.3} />
          </div>
          <div className="flex flex-wrap justify-center gap-3">
            <Link to="/dashboard" className="btn-gold">
              Enter dashboard <ArrowRight className="h-4 w-4" />
            </Link>
            <button type="button" onClick={onEdit} className="btn-ghost">
              Recalibrate
            </button>
          </div>
          <p className="max-w-lg text-center text-xs text-taupe/70">{result.insurance.disclaimer}</p>
        </motion.div>
      )}
    </div>
  );
}
