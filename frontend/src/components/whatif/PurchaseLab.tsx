import { useQuery } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import { BadgeCheck, Car, GraduationCap, Home, Loader2, ShieldAlert, Stethoscope } from "lucide-react";
import { useState } from "react";
import { whatIf } from "../../lib/api";
import { formatINR, formatPct } from "../../lib/format";
import { dtiTone, efTone, type Tone } from "../../lib/formulas";
import { useDebounced } from "../../lib/useDebounced";
import { NumberField } from "../ui/Fields";

const PRESETS = [
  { label: "Surgery", icon: Stethoscope, cost: 300_000 },
  { label: "Car", icon: Car, cost: 800_000 },
  { label: "Education", icon: GraduationCap, cost: 1_200_000 },
  { label: "Home down payment", icon: Home, cost: 2_000_000 },
];

const TONE_TEXT: Record<Tone, string> = { good: "text-good", warn: "text-warn", risk: "text-risk" };

function Stat({ label, value, tone, sub }: { label: string; value: string; tone?: Tone; sub?: string }) {
  return (
    <div className="rounded-xl border border-gold/10 bg-ink/40 p-4">
      <p className="text-[10px] tracking-widest text-taupe uppercase">{label}</p>
      <p className={`mt-1 font-display text-xl font-semibold ${tone ? TONE_TEXT[tone] : "text-ivory"}`}>{value}</p>
      {sub && <p className="mt-0.5 text-[11px] text-taupe/70">{sub}</p>}
    </div>
  );
}

export function PurchaseLab({ userId }: { userId: string }) {
  const [cost, setCost] = useState(800_000);
  const debounced = useDebounced(cost, 350);
  const valid = Number.isFinite(debounced) && debounced >= 0;
  const result = useQuery({
    queryKey: ["whatif", userId, debounced],
    queryFn: () => whatIf(userId, debounced),
    enabled: valid,
    placeholderData: (previous) => previous,
  });
  const r = result.data;

  return (
    <div className="grid gap-5 lg:grid-cols-[360px_1fr]">
      <div className="glass flex flex-col gap-6 p-6">
        <h2 className="font-display text-sm font-semibold tracking-[0.18em] text-champagne uppercase">Planned expense</h2>
        <div className="grid grid-cols-2 gap-2">
          {PRESETS.map(({ label, icon: Icon, cost: c }) => (
            <motion.button
              key={label}
              type="button"
              whileTap={{ scale: 0.96 }}
              onClick={() => setCost(c)}
              className={`flex items-center gap-2 rounded-xl border px-3 py-2 text-left text-xs transition-colors ${
                cost === c ? "border-gold/60 bg-gold/10 text-champagne" : "border-gold/15 text-taupe hover:border-gold/40"
              }`}
            >
              <Icon className="h-4 w-4 shrink-0 text-gold" />
              <span>
                {label}
                <span className="block font-mono text-[10px] text-taupe">{formatINR(c)}</span>
              </span>
            </motion.button>
          ))}
        </div>
        <NumberField label="Cost" unit="₹" value={cost} min={0} max={5_000_000} step={10_000} slider onChange={setCost} error={valid || !Number.isFinite(cost) ? undefined : "Must be 0 or more"} />
        {r && <p className="text-[11px] text-taupe/70">{r.disclaimer}</p>}
      </div>

      <div className="flex flex-col gap-5">
        {result.isError && <p className="rounded-xl border border-risk/40 bg-risk/10 px-4 py-2 text-sm text-risk">{result.error.message}</p>}
        {!r ? (
          <div className="glass flex h-64 items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin text-gold" />
          </div>
        ) : (
          <>
            <motion.div
              key={String(r.affordable)}
              initial={{ scale: 0.96, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              className={`glass flex items-center gap-5 p-6 ${r.affordable ? "border-good/40" : "border-risk/40"}`}
            >
              {r.affordable ? <BadgeCheck className="h-12 w-12 text-good" /> : <ShieldAlert className="h-12 w-12 text-risk" />}
              <div className="flex-1">
                <p className={`font-display text-2xl font-bold ${r.affordable ? "text-good" : "text-risk"}`}>
                  {r.affordable ? "Affordable within 12 months" : "Stretches your finances"}
                </p>
                <p className="mt-1 text-sm text-taupe">
                  {formatINR(r.purchase_cost)} vs {formatINR(r.finance.disposable_income)}/month free cash · affordability score{" "}
                  <span className="font-mono text-champagne">{r.affordability_score === null ? "∞" : r.affordability_score.toFixed(2)}</span>
                </p>
              </div>
              {result.isFetching && <Loader2 className="h-5 w-5 animate-spin text-gold" />}
            </motion.div>

            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <Stat label="DTI now" value={formatPct(r.finance.dti_ratio)} tone={dtiTone(r.finance.dti_ratio)} />
              <Stat
                label="DTI with 12-mo EMI"
                value={formatPct(r.impact_analysis.new_dti_if_emi)}
                tone={dtiTone(r.impact_analysis.new_dti_if_emi)}
                sub={`${formatINR(r.impact_analysis.monthly_emi_12months)}/month`}
              />
              <Stat label="DTI with 24-mo EMI" value={formatPct(r.impact_analysis.new_dti_if_emi_24months)} tone={dtiTone(r.impact_analysis.new_dti_if_emi_24months)} />
              <Stat
                label="Emergency fund after"
                value={r.impact_analysis.emergency_fund_months_after_purchase === null ? "∞" : `${r.impact_analysis.emergency_fund_months_after_purchase} mo`}
                tone={r.impact_analysis.emergency_fund_months_after_purchase === null ? "good" : efTone(r.impact_analysis.emergency_fund_months_after_purchase)}
                sub={r.impact_analysis.emergency_fund_impact.split(" — ")[0]}
              />
            </div>

            <div className="glass p-6">
              <h3 className="font-display text-sm font-semibold tracking-[0.18em] text-champagne uppercase">Ranked alternatives</h3>
              <ol className="mt-4 grid gap-3 md:grid-cols-2">
                <AnimatePresence initial={false}>
                  {r.alternatives.map((alt, i) => (
                    <motion.li
                      key={alt.strategy}
                      layout
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.06 }}
                      className="flex gap-3 rounded-xl border border-gold/10 bg-ink/40 p-4"
                    >
                      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gold/15 font-display text-sm font-bold text-gold">
                        {alt.rank}
                      </span>
                      <div>
                        <p className="font-medium text-ivory">{alt.strategy}</p>
                        <p className="mt-1 text-xs text-taupe">{alt.detail}</p>
                        {alt.estimated_savings > 0 && (
                          <p className="mt-1 text-xs text-good">Est. saving {formatINR(alt.estimated_savings)}</p>
                        )}
                      </div>
                    </motion.li>
                  ))}
                </AnimatePresence>
              </ol>
              {r.alternatives.length === 0 && <p className="mt-3 text-sm text-taupe">No alternatives needed for this amount.</p>}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
