import { AnimatePresence, motion } from "framer-motion";
import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";
import { formatPct } from "../../lib/format";
import type { Snapshot } from "../../lib/types";

type Metric = {
  label: string;
  get: (s: Snapshot) => number | null;
  format: (v: number | null) => string;
  better: "up" | "down";
};

const num = (digits = 0) => (v: number | null) => (v === null ? "∞" : v.toFixed(digits));

const METRICS: Metric[] = [
  { label: "Health score", get: (s) => s.health.overall_health_score, format: num(), better: "up" },
  { label: "CVD risk", get: (s) => s.health.cardio_risk.probability, format: (v) => formatPct(v, 1), better: "down" },
  { label: "BMI", get: (s) => s.health.bmi, format: num(1), better: "down" },
  { label: "Stability score", get: (s) => s.finance.financial_stability_score, format: num(), better: "up" },
  { label: "Debt-to-income", get: (s) => s.finance.dti_ratio, format: (v) => formatPct(v), better: "down" },
  { label: "Emergency fund (mo)", get: (s) => s.finance.emergency_fund_months, format: num(1), better: "up" },
  { label: "Insurance score", get: (s) => s.insurance.insurance_adequacy_score, format: num(), better: "up" },
  { label: "Coverage ratio", get: (s) => s.insurance.coverage_adequacy_ratio, format: (v) => (v === null ? "Full" : formatPct(v)), better: "up" },
];

export function DeltaTable({ from, to }: { from: Snapshot; to: Snapshot }) {
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-left text-[10px] tracking-widest text-taupe uppercase">
          <th className="pb-3 font-medium">Metric</th>
          <th className="pb-3 text-right font-medium">#{from.snapshot_id}</th>
          <th className="pb-3 text-right font-medium">#{to.snapshot_id}</th>
          <th className="pb-3 text-right font-medium">Change</th>
        </tr>
      </thead>
      <tbody>
        {METRICS.map((m) => {
          const a = m.get(from);
          const b = m.get(to);
          const diff = a !== null && b !== null ? b - a : 0;
          const flat = Math.abs(diff) < 1e-9;
          const improved = !flat && (diff > 0) === (m.better === "up");
          const Icon = flat ? Minus : diff > 0 ? ArrowUpRight : ArrowDownRight;
          return (
            <tr key={m.label} className="border-t border-gold/10">
              <td className="py-2.5 text-ivory/90">{m.label}</td>
              <td className="py-2.5 text-right font-mono text-taupe">{m.format(a)}</td>
              <td className="py-2.5 text-right font-mono text-ivory">
                <AnimatePresence mode="popLayout" initial={false}>
                  <motion.span
                    key={m.format(b)}
                    initial={{ opacity: 0, y: -8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 8 }}
                    className="inline-block"
                  >
                    {m.format(b)}
                  </motion.span>
                </AnimatePresence>
              </td>
              <td className="py-2.5 text-right">
                <span
                  className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs ${
                    flat ? "text-taupe" : improved ? "bg-good/10 text-good" : "bg-risk/10 text-risk"
                  }`}
                >
                  <Icon className="h-3 w-3" />
                  {flat ? "—" : improved ? "Better" : "Worse"}
                </span>
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
