import { useQuery } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import {
  ArrowDownRight,
  ArrowUpRight,
  Ban,
  Dumbbell,
  FlaskConical,
  HeartPulse,
  Landmark,
  Loader2,
  RotateCcw,
  Scale,
  ShieldPlus,
  ShoppingBag,
  TrendingDown,
} from "lucide-react";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { NumberField, Segmented } from "../components/ui/Fields";
import { ScoreRing } from "../components/ui/ScoreRing";
import { FanChart } from "../components/whatif/FanChart";
import { PurchaseLab } from "../components/whatif/PurchaseLab";
import { getInputs, simulate } from "../lib/api";
import { formatINR, formatPct } from "../lib/format";
import type { OnboardPayload, Profiles, SimulateRequest } from "../lib/types";
import { useDebounced } from "../lib/useDebounced";
import { useCurrentUser } from "../lib/user";

type Draft = OnboardPayload;

const PRESETS: { label: string; icon: typeof Scale; apply: (d: Draft, base: Draft) => Draft }[] = [
  { label: "Lose 10 kg", icon: Scale, apply: (d, b) => ({ ...d, health_inputs: { ...d.health_inputs, weight_kg: Math.max(40, b.health_inputs.weight_kg - 10) } }) },
  { label: "Quit smoking & alcohol", icon: Ban, apply: (d) => ({ ...d, health_inputs: { ...d.health_inputs, smoke: 0, alco: 0 } }) },
  { label: "Get active", icon: Dumbbell, apply: (d) => ({ ...d, health_inputs: { ...d.health_inputs, active: 1 } }) },
  { label: "Control BP", icon: HeartPulse, apply: (d) => ({ ...d, health_inputs: { ...d.health_inputs, ap_hi: 118, ap_lo: 76 } }) },
  { label: "Clear all EMIs", icon: Landmark, apply: (d) => ({ ...d, finance_inputs: { ...d.finance_inputs, emis: 0 } }) },
  {
    label: "Upgrade cover to ₹15L",
    icon: ShieldPlus,
    apply: (d, b) => ({
      ...d,
      insurance_inputs: { ...d.insurance_inputs, sum_insured: 1_500_000, annual_premium: Math.round(b.insurance_inputs.annual_premium * 1.4) },
    }),
  },
  { label: "Job loss (−50% income)", icon: TrendingDown, apply: (d, b) => ({ ...d, finance_inputs: { ...d.finance_inputs, income: Math.round(b.finance_inputs.income * 0.5) } }) },
];

function diff<T extends object>(base: T, draft: T): Partial<T> {
  const out: Partial<T> = {};
  for (const key of Object.keys(draft) as (keyof T)[]) {
    const a = base[key];
    const b = draft[key];
    if (JSON.stringify(a) !== JSON.stringify(b)) out[key] = b;
  }
  return out;
}

function buildRequest(userId: string, base: Draft, draft: Draft): SimulateRequest {
  const { gender: _ignored, ...health } = diff(base.health_inputs, draft.health_inputs);
  return {
    user_id: userId,
    health,
    finance: diff(base.finance_inputs, draft.finance_inputs),
    insurance: diff(base.insurance_inputs, draft.insurance_inputs),
    forecast_months: 12,
  };
}

function Delta({ before, after, better, format }: { before: number | null; after: number | null; better: "up" | "down"; format: (v: number | null) => string }) {
  const d = before !== null && after !== null ? after - before : 0;
  const flat = Math.abs(d) < 1e-9;
  const good = !flat && (d > 0) === (better === "up");
  return (
    <div className="flex items-center justify-between gap-2 border-t border-gold/10 py-2 text-sm first:border-t-0">
      <span className="font-mono text-taupe">{format(before)}</span>
      <span className={`flex items-center gap-1 font-mono ${flat ? "text-ivory" : good ? "text-good" : "text-risk"}`}>
        {!flat && (d > 0 ? <ArrowUpRight className="h-3.5 w-3.5" /> : <ArrowDownRight className="h-3.5 w-3.5" />)}
        <AnimatePresence mode="popLayout" initial={false}>
          <motion.span key={format(after)} initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 6 }}>
            {format(after)}
          </motion.span>
        </AnimatePresence>
      </span>
    </div>
  );
}

const ROWS: { label: string; get: (p: Profiles) => number | null; better: "up" | "down"; format: (v: number | null) => string }[] = [
  { label: "CVD risk", get: (p) => p.health.cardio_risk.probability, better: "down", format: (v) => formatPct(v, 1) },
  { label: "BMI", get: (p) => p.health.bmi, better: "down", format: (v) => (v === null ? "—" : v.toFixed(1)) },
  { label: "Debt-to-income", get: (p) => p.finance.dti_ratio, better: "down", format: (v) => formatPct(v) },
  { label: "Free cash / month", get: (p) => p.finance.disposable_income, better: "up", format: formatINR },
  { label: "Emergency fund (mo)", get: (p) => p.finance.emergency_fund_months, better: "up", format: (v) => (v === null ? "∞" : v.toFixed(1)) },
  { label: "Projected 5-yr medical cost", get: (p) => p.insurance.estimated_future_cost, better: "down", format: formatINR },
  { label: "Coverage ratio", get: (p) => p.insurance.coverage_adequacy_ratio, better: "up", format: (v) => (v === null ? "Full" : formatPct(v)) },
];

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-4">
      <h3 className="text-xs font-semibold tracking-widest text-champagne uppercase">{title}</h3>
      {children}
    </div>
  );
}

function LifeLab({ userId, base }: { userId: string; base: Draft }) {
  const [draft, setDraft] = useState<Draft>(base);
  useEffect(() => setDraft(base), [base]);

  const request = useMemo(() => buildRequest(userId, base, draft), [userId, base, draft]);
  const debounced = useDebounced(request, 350);
  const result = useQuery({
    queryKey: ["simulate", debounced],
    queryFn: () => simulate(debounced),
    placeholderData: (previous) => previous,
  });
  const changeCount = Object.keys(request.health ?? {}).length + Object.keys(request.finance ?? {}).length + Object.keys(request.insurance ?? {}).length;

  const h = draft.health_inputs;
  const f = draft.finance_inputs;
  const b = base.finance_inputs;
  const setH = (patch: Partial<Draft["health_inputs"]>) => setDraft((d) => ({ ...d, health_inputs: { ...d.health_inputs, ...patch } }));
  const setF = (patch: Partial<Draft["finance_inputs"]>) => setDraft((d) => ({ ...d, finance_inputs: { ...d.finance_inputs, ...patch } }));
  const r = result.data;

  return (
    <div className="grid gap-5 xl:grid-cols-[380px_1fr]">
      <aside className="glass flex flex-col gap-7 p-6">
        <div className="flex items-center justify-between">
          <h2 className="font-display text-sm font-semibold tracking-[0.18em] text-champagne uppercase">Control deck</h2>
          <button type="button" onClick={() => setDraft(base)} disabled={changeCount === 0} className="btn-ghost px-3 py-1.5 text-xs disabled:opacity-40">
            <RotateCcw className="h-3.5 w-3.5" /> Reset
          </button>
        </div>

        <div className="flex flex-wrap gap-2">
          {PRESETS.map(({ label, icon: Icon, apply }) => (
            <motion.button
              key={label}
              type="button"
              whileTap={{ scale: 0.95 }}
              whileHover={{ y: -2 }}
              onClick={() => setDraft((d) => apply(d, base))}
              className="flex items-center gap-1.5 rounded-full border border-gold/20 px-3 py-1.5 text-xs text-taupe transition-colors hover:border-gold/60 hover:text-champagne"
            >
              <Icon className="h-3.5 w-3.5 text-gold" /> {label}
            </motion.button>
          ))}
        </div>

        <Section title="Health">
          <NumberField label="Weight" unit="kg" value={h.weight_kg} min={35} max={160} slider onChange={(v) => setH({ weight_kg: v })} />
          <NumberField label="Systolic BP" unit="mmHg" value={h.ap_hi} min={90} max={200} slider onChange={(v) => setH({ ap_hi: v })} />
          <NumberField label="Fasting glucose" unit="mg/dL" value={h.blood_glucose_level} min={60} max={250} slider onChange={(v) => setH({ blood_glucose_level: v })} />
          <div className="grid grid-cols-2 gap-3">
            <Segmented label="Smoker" value={h.smoke} options={[{ value: 0 as const, label: "No" }, { value: 1 as const, label: "Yes" }]} onChange={(v) => setH({ smoke: v })} />
            <Segmented label="Active" value={h.active} options={[{ value: 0 as const, label: "No" }, { value: 1 as const, label: "Yes" }]} onChange={(v) => setH({ active: v })} />
          </div>
        </Section>

        <Section title="Finance">
          <NumberField label="Monthly income" unit="₹" value={f.income} min={Math.round(b.income * 0.3)} max={Math.round(b.income * 2)} step={1000} slider onChange={(v) => setF({ income: v })} />
          <NumberField label="Variable expenses" unit="₹" value={f.variable_expenses} min={0} max={Math.max(20_000, Math.round(b.variable_expenses * 2))} step={500} slider onChange={(v) => setF({ variable_expenses: v })} />
          <NumberField label="Loan EMIs" unit="₹" value={f.emis} min={0} max={Math.max(50_000, Math.round(b.emis * 2))} step={500} slider onChange={(v) => setF({ emis: v })} />
        </Section>

        <Section title="Insurance">
          <NumberField
            label="Sum insured"
            unit="₹"
            value={draft.insurance_inputs.sum_insured}
            min={0}
            max={5_000_000}
            step={50_000}
            slider
            onChange={(v) => setDraft((d) => ({ ...d, insurance_inputs: { ...d.insurance_inputs, sum_insured: v } }))}
          />
        </Section>
      </aside>

      <div className="flex flex-col gap-5">
        {result.isError && <p className="rounded-xl border border-risk/40 bg-risk/10 px-4 py-2 text-sm text-risk">{result.error.message}</p>}
        {!r ? (
          <div className="glass flex h-96 items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin text-gold" />
          </div>
        ) : (
          <>
            <section className="glass relative overflow-hidden p-6">
              <header className="mb-6 flex items-center justify-between">
                <h2 className="font-display text-sm font-semibold tracking-[0.18em] text-champagne uppercase">Parallel timelines</h2>
                <span className="flex items-center gap-2 text-xs text-taupe">
                  {result.isFetching && <Loader2 className="h-3.5 w-3.5 animate-spin text-gold" />}
                  {changeCount === 0 ? "Move a slider to fork your future" : `${changeCount} change${changeCount > 1 ? "s" : ""} applied`}
                </span>
              </header>
              <div className="relative grid gap-6 md:grid-cols-2">
                <div
                  className="pointer-events-none absolute top-0 bottom-0 left-1/2 hidden w-px md:block"
                  style={{ background: "linear-gradient(transparent, #D4AF37, transparent)", boxShadow: "0 0 18px #D4AF37" }}
                  aria-hidden
                />
                {(["before", "after"] as const).map((side) => {
                  const p = r[side];
                  return (
                    <div key={side} className={`flex flex-col items-center gap-5 ${side === "before" ? "opacity-75" : ""}`}>
                      <span className={`text-xs tracking-[0.25em] uppercase ${side === "after" ? "text-metal font-semibold" : "text-taupe"}`}>
                        {side === "before" ? "Today" : "Simulated future"}
                      </span>
                      <div className="flex flex-wrap justify-center gap-4">
                        <ScoreRing value={p.health.overall_health_score} label="Health" color="#E0A899" size={108} />
                        <ScoreRing value={p.finance.financial_stability_score} label="Financial" color="#D4AF37" size={108} />
                        <ScoreRing value={p.insurance.insurance_adequacy_score} label="Insurance" color="#C9CED6" size={108} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>

            <div className="grid gap-5 lg:grid-cols-2">
              <section className="glass p-6">
                <h2 className="mb-4 font-display text-sm font-semibold tracking-[0.18em] text-champagne uppercase">Impact breakdown</h2>
                <div className="grid grid-cols-[1fr_auto] gap-x-4">
                  {ROWS.map((row) => (
                    <div key={row.label} className="contents">
                      <span className="border-t border-gold/10 py-2 text-sm text-ivory/90 first-of-type:border-t-0">{row.label}</span>
                      <div className="min-w-44">
                        <Delta before={row.get(r.before)} after={row.get(r.after)} better={row.better} format={row.format} />
                      </div>
                    </div>
                  ))}
                </div>
              </section>
              <section className="glass p-6">
                <h2 className="mb-1 font-display text-sm font-semibold tracking-[0.18em] text-champagne uppercase">12-month savings forecast</h2>
                <p className="mb-4 text-xs text-taupe">Monte Carlo: 400 simulated futures per month with income and spending variation.</p>
                <FanChart before={r.forecast.before} after={r.forecast.after} />
              </section>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export function WhatIfLab() {
  const userId = useCurrentUser();
  const [tab, setTab] = useState<"life" | "purchase">("life");
  const inputs = useQuery({
    queryKey: ["inputs", userId],
    queryFn: () => getInputs(userId!),
    enabled: Boolean(userId),
  });

  if (!userId) {
    return (
      <div className="glass mx-auto mt-10 max-w-xl p-10 text-center">
        <FlaskConical className="mx-auto h-12 w-12 text-gold" />
        <h2 className="mt-5 font-display text-2xl font-semibold text-metal">Calibrate a twin first</h2>
        <Link to="/onboard" className="btn-gold mt-8">Calibrate twin</Link>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-5">
      <div role="tablist" aria-label="What-if mode" className="glass flex w-fit gap-1 p-1">
        {[
          { key: "life" as const, label: "Life changes", icon: FlaskConical },
          { key: "purchase" as const, label: "Big purchase", icon: ShoppingBag },
        ].map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            type="button"
            role="tab"
            aria-selected={tab === key}
            onClick={() => setTab(key)}
            className={`relative flex items-center gap-2 rounded-xl px-4 py-2 text-sm ${tab === key ? "text-ink" : "text-taupe hover:text-ivory"}`}
          >
            {tab === key && (
              <motion.span
                layoutId="whatif-tab"
                className="absolute inset-0 rounded-xl"
                style={{ background: "linear-gradient(135deg, #F5E6B8, #D4AF37 60%, #A8862A)" }}
              />
            )}
            <Icon className="relative h-4 w-4" />
            <span className="relative font-medium">{label}</span>
          </button>
        ))}
      </div>

      {inputs.isError ? (
        <div className="glass p-8 text-center text-taupe">
          Could not load this twin's inputs. Make sure the backend is running the latest code (restart uvicorn).
        </div>
      ) : !inputs.data ? (
        <div className="glass h-96 animate-pulse" aria-busy />
      ) : (
        <AnimatePresence mode="wait">
          <motion.div key={tab} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}>
            {tab === "life" ? <LifeLab userId={userId} base={inputs.data} /> : <PurchaseLab userId={userId} />}
          </motion.div>
        </AnimatePresence>
      )}
    </div>
  );
}
