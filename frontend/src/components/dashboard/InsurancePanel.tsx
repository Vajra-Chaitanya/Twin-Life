import { motion } from "framer-motion";
import { Check, ShieldAlert } from "lucide-react";
import { formatINR, formatPct } from "../../lib/format";
import type { InsuranceProfile } from "../../lib/types";

const CONDITION_LABELS: Record<string, string> = {
  cardio: "Cardiovascular",
  diabetes: "Diabetes",
  hypertension: "Hypertension",
};

export function InsurancePanelBody({ insurance: i }: { insurance: InsuranceProfile }) {
  const ratio = i.coverage_adequacy_ratio;
  const coveredPct = ratio === null ? 100 : Math.min(100, ratio * 100);
  const breakdown = Object.entries(i.cost_breakdown).sort((a, b) => b[1] - a[1]);
  const maxCost = Math.max(...breakdown.map(([, v]) => v), 1);
  const held = new Set(i.rider_analysis.existing.map((r) => r.toLowerCase().trim()));

  return (
    <div className="flex flex-col gap-6">
      <div>
        <div className="flex items-baseline justify-between text-sm">
          <span className="text-taupe">Cover vs projected 5-yr cost</span>
          <span className={`font-mono ${coveredPct >= 100 ? "text-good" : "text-risk"}`}>
            {ratio === null ? "Full" : `${formatPct(ratio)}`}
          </span>
        </div>
        <div className="relative mt-2 h-3 overflow-hidden rounded-full bg-gold/10">
          <motion.div
            className="h-full rounded-full"
            style={{ background: "linear-gradient(90deg, #8C6A1F, #C9CED6)" }}
            initial={{ width: 0 }}
            animate={{ width: `${coveredPct}%` }}
            transition={{ duration: 1.1, ease: [0.22, 1, 0.36, 1] }}
          />
        </div>
        <p className="mt-1 text-[11px] text-taupe/70">
          Projected cost {formatINR(i.estimated_future_cost)} · premium {formatPct(i.premium_affordability_ratio, 1)} of income
        </p>
      </div>

      <div>
        <span className="text-xs tracking-widest text-taupe uppercase">Cost drivers</span>
        <ul className="mt-3 flex flex-col gap-2.5">
          {breakdown.map(([condition, cost], idx) => (
            <li key={condition} className="grid grid-cols-[110px_1fr_90px] items-center gap-3 text-sm">
              <span className="text-ivory/90">{CONDITION_LABELS[condition] ?? condition}</span>
              <div className="h-2 overflow-hidden rounded-full bg-gold/5">
                <motion.div
                  className="h-full rounded-full bg-insurance/70"
                  initial={{ width: 0 }}
                  animate={{ width: `${(cost / maxCost) * 100}%` }}
                  transition={{ duration: 0.8, delay: 0.2 + idx * 0.1 }}
                />
              </div>
              <span className="text-right font-mono text-xs text-taupe">{formatINR(cost)}</span>
            </li>
          ))}
        </ul>
      </div>

      <div>
        <span className="text-xs tracking-widest text-taupe uppercase">Recommended riders</span>
        <ul className="mt-3 flex flex-wrap gap-2">
          {i.rider_analysis.recommended.map((rider) => {
            const ok = held.has(rider.toLowerCase().trim());
            return (
              <li
                key={rider}
                className={`relative flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs ${
                  ok ? "border-good/40 text-good" : "border-risk/50 text-risk"
                }`}
              >
                {!ok && <span className="absolute inset-0 animate-ping rounded-full border border-risk/40" aria-hidden />}
                {ok ? <Check className="h-3 w-3" /> : <ShieldAlert className="h-3 w-3" />}
                {rider}
                <span className="sr-only">{ok ? "(held)" : "(missing)"}</span>
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}
