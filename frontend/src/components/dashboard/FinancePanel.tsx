import { motion } from "framer-motion";
import { formatINR, formatPct } from "../../lib/format";
import { dtiTone, efTone, savingsTone, type Tone } from "../../lib/formulas";
import type { FinanceProfile } from "../../lib/types";

const TONE_TEXT: Record<Tone, string> = { good: "text-good", warn: "text-warn", risk: "text-risk" };
const TONE_BG: Record<Tone, string> = { good: "#7FB77E", warn: "#E9B949", risk: "#E5534B" };

function Meter({ label, value, display, pct, tone }: { label: string; value: string; display?: string; pct: number; tone: Tone }) {
  return (
    <div>
      <div className="flex items-baseline justify-between gap-2 text-sm">
        <span className="text-taupe">{label}</span>
        <span className={`font-mono whitespace-nowrap ${TONE_TEXT[tone]}`}>{value}</span>
      </div>
      <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-gold/10">
        <motion.div
          className="h-full rounded-full"
          style={{ background: TONE_BG[tone], boxShadow: `0 0 10px ${TONE_BG[tone]}` }}
          initial={{ width: 0 }}
          animate={{ width: `${Math.max(2, Math.min(100, pct))}%` }}
          transition={{ duration: 1, ease: [0.22, 1, 0.36, 1] }}
        />
      </div>
      {display && <p className="mt-1 text-[11px] text-taupe/70">{display}</p>}
    </div>
  );
}

export function FinancePanelBody({ finance: f }: { finance: FinanceProfile }) {
  const emis = Math.max(0, f.monthly_income - f.monthly_expenses - f.disposable_income);
  const free = Math.max(0, f.disposable_income);
  const total = Math.max(f.monthly_income, f.monthly_expenses + emis);
  const segments = [
    { label: "Living expenses", value: f.monthly_expenses, color: "#8C6A1F" },
    { label: "Loan EMIs", value: emis, color: "#E5534B" },
    { label: "Free cash", value: free, color: "#D4AF37" },
  ];
  const ef = f.emergency_fund_months;

  return (
    <div className="flex flex-col gap-6">
      <div>
        <div className="flex items-baseline justify-between">
          <span className="text-xs tracking-widest text-taupe uppercase">Monthly cash flow</span>
          <span className="font-display text-lg font-semibold text-ivory">{formatINR(f.monthly_income)}</span>
        </div>
        <div className="mt-3 flex h-4 overflow-hidden rounded-full bg-gold/10">
          {segments.map((s, i) => (
            <motion.div
              key={s.label}
              title={`${s.label}: ${formatINR(s.value)}`}
              style={{ background: s.color }}
              initial={{ width: 0 }}
              animate={{ width: `${(s.value / total) * 100}%` }}
              transition={{ duration: 0.9, delay: 0.2 + i * 0.15, ease: [0.22, 1, 0.36, 1] }}
            />
          ))}
        </div>
        <ul className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-xs">
          {segments.map((s) => (
            <li key={s.label} className="flex items-center gap-1.5 text-taupe">
              <span className="h-2 w-2 rounded-full" style={{ background: s.color }} />
              {s.label} <span className="font-mono text-ivory/90">{formatINR(s.value)}</span>
            </li>
          ))}
        </ul>
      </div>

      <div className="grid gap-5 sm:grid-cols-3">
        <Meter label="Debt-to-income" value={formatPct(f.dti_ratio)} pct={f.dti_ratio * 100} tone={dtiTone(f.dti_ratio)} display="Target ≤ 36%" />
        <Meter label="Savings rate" value={formatPct(f.savings_rate)} pct={f.savings_rate * 100} tone={savingsTone(f.savings_rate)} display="Target ≥ 20%" />
        <Meter
          label="Emergency fund"
          value={ef === null ? "∞" : `${ef} mo`}
          pct={ef === null ? 100 : (ef / 6) * 100}
          tone={ef === null ? "good" : efTone(ef)}
          display={`${formatINR(f.savings_balance)} saved · target 6 mo`}
        />
      </div>
    </div>
  );
}
