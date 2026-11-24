import { motion } from "framer-motion";
import { FEATURE_LABELS } from "../../lib/format";
import type { ShapFeature } from "../../lib/types";

/** Diverging bar chart: right = pushes risk up, left = pulls risk down. */
export function ShapChart({ features }: { features: ShapFeature[] }) {
  if (features.length === 0) {
    return <p className="text-sm text-taupe">SHAP explanations are unavailable for this snapshot.</p>;
  }
  const maxAbs = Math.max(...features.map((f) => Math.abs(f.impact)), 1e-6);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex justify-between text-[10px] tracking-widest text-taupe uppercase">
        <span>← lowers risk</span>
        <span>raises risk →</span>
      </div>
      {features.map((f, i) => {
        const width = (Math.abs(f.impact) / maxAbs) * 50;
        const up = f.impact > 0;
        return (
          <div key={f.feature} className="grid grid-cols-[110px_1fr_64px] items-center gap-3 text-sm">
            <span className="truncate text-ivory/90">{FEATURE_LABELS[f.feature] ?? f.feature}</span>
            <div className="relative h-3 rounded-full bg-gold/5">
              <span className="absolute top-[-4px] bottom-[-4px] left-1/2 w-px bg-gold/30" />
              <motion.span
                className="absolute top-0 h-full rounded-full"
                style={{
                  [up ? "left" : "right"]: "50%",
                  background: up
                    ? "linear-gradient(90deg, rgb(229 83 75 / 0.5), #E5534B)"
                    : "linear-gradient(270deg, rgb(127 183 126 / 0.5), #7FB77E)",
                  boxShadow: `0 0 12px ${up ? "rgb(229 83 75 / 0.5)" : "rgb(127 183 126 / 0.5)"}`,
                }}
                initial={{ width: 0 }}
                animate={{ width: `${width}%` }}
                transition={{ duration: 0.9, delay: 0.3 + i * 0.1, ease: [0.22, 1, 0.36, 1] }}
              />
            </div>
            <span className={`text-right font-mono text-xs ${up ? "text-risk" : "text-good"}`}>
              {up ? "+" : "−"}
              {Math.abs(f.impact * 100).toFixed(1)} pts
            </span>
          </div>
        );
      })}
    </div>
  );
}
