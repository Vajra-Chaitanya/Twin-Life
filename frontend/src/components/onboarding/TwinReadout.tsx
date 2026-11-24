import { AnimatePresence, motion } from "framer-motion";
import { Activity } from "lucide-react";
import * as f from "../../lib/formulas";
import type { OnboardPayload } from "../../lib/types";

const TONE_TEXT: Record<f.Tone, string> = { good: "text-good", warn: "text-warn", risk: "text-risk" };
const TONE_DOT: Record<f.Tone, string> = { good: "bg-good", warn: "bg-warn", risk: "bg-risk" };

type Metric = { label: string; value: string; tone: f.Tone | null };

const pct = (x: number) => (Number.isFinite(x) ? `${(x * 100).toFixed(0)}%` : "—");

function buildMetrics(p: OnboardPayload, step: number): { group: string; color: string; metrics: Metric[] }[] {
  const h = p.health_inputs;
  const fi = p.finance_inputs;
  const bmiValue = f.bmi(h.height_cm, h.weight_kg);
  const bp = Number.isFinite(h.ap_hi) && Number.isFinite(h.ap_lo) ? f.bpStage(h.ap_hi, h.ap_lo) : "—";
  const glucose = Number.isFinite(h.blood_glucose_level) ? f.diabetesIndicator(h.blood_glucose_level) : "—";

  const dti = f.dtiRatio(fi.fixed_expenses, fi.emis, fi.income);
  const sav = f.savingsRate(fi.income, fi.fixed_expenses, fi.variable_expenses);
  const ef = f.emergencyFundMonths(fi.savings_balance, fi.fixed_expenses, fi.variable_expenses);
  const stability = [dti, sav, ef].every((x) => !Number.isNaN(x)) ? f.financialStabilityScore(dti, sav, ef) : NaN;
  const premium = f.premiumAffordabilityRatio(p.insurance_inputs.annual_premium, fi.income * 12);

  const groups = [
    {
      group: "Health",
      color: "text-health",
      metrics: [
        {
          label: "BMI",
          value: Number.isFinite(bmiValue) ? `${bmiValue} · ${f.whoObesityClass(bmiValue)}` : "—",
          tone: Number.isFinite(bmiValue) ? f.bmiTone(bmiValue) : null,
        },
        { label: "Blood pressure", value: bp, tone: bp === "—" ? null : f.bpTone(bp) },
        { label: "Glucose indicator", value: glucose, tone: glucose === "—" ? null : f.levelTone(glucose) },
      ],
    },
    {
      group: "Finance",
      color: "text-finance",
      metrics: [
        { label: "Debt-to-income", value: pct(dti), tone: Number.isFinite(dti) ? f.dtiTone(dti) : null },
        { label: "Savings rate", value: pct(sav), tone: Number.isFinite(sav) ? f.savingsTone(sav) : null },
        {
          label: "Emergency fund",
          value: Number.isFinite(ef) ? `${ef} months` : ef === Infinity ? "∞" : "—",
          tone: Number.isNaN(ef) ? null : f.efTone(ef),
        },
        {
          label: "Stability score",
          value: Number.isFinite(stability) ? `${stability} / 100` : "—",
          tone: Number.isFinite(stability) ? f.scoreTone(stability) : null,
        },
      ],
    },
    {
      group: "Insurance",
      color: "text-insurance",
      metrics: [
        {
          label: "Premium / income",
          value: Number.isFinite(premium) ? `${(premium * 100).toFixed(1)}%` : "—",
          tone: Number.isFinite(premium) ? f.premiumTone(premium) : null,
        },
      ],
    },
  ];
  // Reveal groups progressively as the user reaches each step.
  return groups.slice(0, Math.max(1, step));
}

export function TwinReadout({ payload, step }: { payload: OnboardPayload; step: number }) {
  const groups = buildMetrics(payload, step);
  return (
    <aside className="glass sticky top-6 overflow-hidden p-6" aria-live="polite">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-24 bg-gradient-to-b from-gold/10 to-transparent" />
      <div className="relative flex items-center gap-2">
        <Activity className="h-4 w-4 text-gold" />
        <h2 className="font-display text-sm font-semibold tracking-[0.2em] text-champagne uppercase">Live twin readout</h2>
      </div>
      <p className="relative mt-1 text-xs text-taupe">Computed instantly with the same formulas as the engine.</p>

      <div className="relative mt-6 flex flex-col gap-6">
        <AnimatePresence initial={false}>
          {groups.map(({ group, color, metrics }) => (
            <motion.section
              key={group}
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.4 }}
            >
              <h3 className={`mb-3 text-xs font-semibold tracking-widest uppercase ${color}`}>{group}</h3>
              <dl className="flex flex-col gap-2.5">
                {metrics.map(({ label, value, tone }) => (
                  <div key={label} className="flex items-center justify-between gap-3 text-sm">
                    <dt className="text-taupe">{label}</dt>
                    <dd className="flex items-center gap-2 text-right">
                      <motion.span
                        key={value}
                        initial={{ opacity: 0.3, y: -4 }}
                        animate={{ opacity: 1, y: 0 }}
                        className={`font-mono ${tone ? TONE_TEXT[tone] : "text-taupe"}`}
                      >
                        {value}
                      </motion.span>
                      <span className={`h-1.5 w-1.5 rounded-full ${tone ? TONE_DOT[tone] : "bg-taupe/40"}`} />
                    </dd>
                  </div>
                ))}
              </dl>
            </motion.section>
          ))}
        </AnimatePresence>
      </div>
    </aside>
  );
}
