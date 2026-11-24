import { useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowLeft, ArrowRight, HeartPulse, ShieldCheck, Sparkles, UserRound, Wallet } from "lucide-react";
import { useRef, useState } from "react";
import { BuildSequence, type LogLine } from "../components/onboarding/BuildSequence";
import { TwinReadout } from "../components/onboarding/TwinReadout";
import { NumberField, Segmented } from "../components/ui/Fields";
import { Stepper } from "../components/ui/Stepper";
import { ApiError, assess, onboard } from "../lib/api";
import { DEFAULT_PAYLOAD, PERSONAS } from "../lib/personas";
import type { FinanceInputs, HealthInputs, InsuranceInputs, OnboardPayload, Snapshot } from "../lib/types";
import { setCurrentUser } from "../lib/user";

const STEPS = [
  { label: "Profile", icon: UserRound },
  { label: "Health", icon: HeartPulse },
  { label: "Finance", icon: Wallet },
  { label: "Insurance", icon: ShieldCheck },
];

const RIDERS = ["Critical Illness Rider", "Diabetes Care Rider", "Hospital Cash Rider", "Personal Accident Rider"];
const LEVELS = [
  { value: 1 as const, label: "Normal" },
  { value: 2 as const, label: "Above" },
  { value: 3 as const, label: "Well above" },
];
const YES_NO = [
  { value: 0 as const, label: "No" },
  { value: 1 as const, label: "Yes" },
];

type Errors = Record<string, string>;

function inRange(errors: Errors, key: string, value: number, min: number, max: number, label: string) {
  if (!Number.isFinite(value)) errors[key] = `${label} is required`;
  else if (value < min || value > max) errors[key] = `${label} must be between ${min} and ${max}`;
}

function validate(step: number, p: OnboardPayload): Errors {
  const e: Errors = {};
  if (step === 0) {
    if (!/^[A-Za-z0-9_-]{3,100}$/.test(p.user_id)) e.user_id = "3-100 characters: letters, numbers, - or _";
  }
  if (step === 1) {
    const h = p.health_inputs;
    inRange(e, "age", h.age, 1, 120, "Age");
    inRange(e, "height_cm", h.height_cm, 100, 230, "Height");
    inRange(e, "weight_kg", h.weight_kg, 25, 250, "Weight");
    inRange(e, "ap_hi", h.ap_hi, 70, 250, "Systolic");
    inRange(e, "ap_lo", h.ap_lo, 40, 150, "Diastolic");
    if (!e.ap_hi && !e.ap_lo && h.ap_lo >= h.ap_hi) e.ap_lo = "Diastolic must be lower than systolic";
    inRange(e, "blood_glucose_level", h.blood_glucose_level, 40, 400, "Fasting glucose");
  }
  if (step === 2) {
    const f = p.finance_inputs;
    inRange(e, "income", f.income, 1, 1e9, "Income");
    for (const [key, label] of [
      ["fixed_expenses", "Fixed expenses"],
      ["variable_expenses", "Variable expenses"],
      ["emis", "EMIs"],
      ["savings_balance", "Savings"],
    ] as const) {
      inRange(e, key, f[key], 0, 1e10, label);
    }
  }
  if (step === 3) {
    inRange(e, "sum_insured", p.insurance_inputs.sum_insured, 0, 1e10, "Sum insured");
    inRange(e, "annual_premium", p.insurance_inputs.annual_premium, 0, 1e9, "Annual premium");
  }
  return e;
}

const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export function Onboarding() {
  const queryClient = useQueryClient();
  const [payload, setPayload] = useState<OnboardPayload>(() => structuredClone(DEFAULT_PAYLOAD));
  const [step, setStep] = useState(0);
  const [direction, setDirection] = useState(1);
  const [errors, setErrors] = useState<Errors>({});
  const [phase, setPhase] = useState<"form" | "building">("form");
  const [logs, setLogs] = useState<LogLine[]>([]);
  const [result, setResult] = useState<Snapshot | null>(null);
  const [buildError, setBuildError] = useState<string | null>(null);
  const logId = useRef(0);

  const setHealth = <K extends keyof HealthInputs>(key: K, value: HealthInputs[K]) =>
    setPayload((p) => ({ ...p, health_inputs: { ...p.health_inputs, [key]: value } }));
  const setFinance = <K extends keyof FinanceInputs>(key: K, value: FinanceInputs[K]) =>
    setPayload((p) => ({ ...p, finance_inputs: { ...p.finance_inputs, [key]: value } }));
  const setInsurance = <K extends keyof InsuranceInputs>(key: K, value: InsuranceInputs[K]) =>
    setPayload((p) => ({ ...p, insurance_inputs: { ...p.insurance_inputs, [key]: value } }));

  const goTo = (next: number) => {
    setDirection(next > step ? 1 : -1);
    setErrors({});
    setStep(next);
  };

  const next = () => {
    const found = validate(step, payload);
    setErrors(found);
    if (Object.keys(found).length > 0) return;
    if (step < STEPS.length - 1) goTo(step + 1);
    else void build();
  };

  const pushLog = (text: string) => {
    const id = ++logId.current;
    setLogs((l) => [...l, { id, text, status: "running" }]);
    return id;
  };
  const finishLog = (id: number, status: LogLine["status"] = "done", text?: string) =>
    setLogs((l) => l.map((line) => (line.id === id ? { ...line, status, text: text ?? line.text } : line)));

  async function build() {
    setPhase("building");
    setLogs([]);
    setResult(null);
    setBuildError(null);
    let current = 0;
    try {
      current = pushLog("Establishing link to twin engine");
      await wait(450);
      finishLog(current);

      current = pushLog("Persisting calibration inputs");
      const [onboarded] = await Promise.all([onboard(payload), wait(500)]);
      finishLog(current, "done", `Calibration ${onboarded.status} for ${onboarded.user_id}`);

      current = pushLog("Running cardiovascular Random Forest + SHAP");
      const [snapshot] = await Promise.all([assess(payload.user_id), wait(700)]);
      const cvd = snapshot.health.cardio_risk;
      finishLog(current, "done", `CVD risk ${(cvd.probability * 100).toFixed(1)}% (${cvd.label}) · ${snapshot.health.shap_top_features.length} drivers explained`);

      for (const text of [
        `Financial stability ${snapshot.finance.financial_stability_score}/100`,
        `Insurance adequacy ${snapshot.insurance.insurance_adequacy_score}/100 · ${snapshot.insurance.rider_analysis.gap_count} rider gap(s)`,
        `Snapshot #${snapshot.snapshot_id} saved`,
      ]) {
        current = pushLog(text);
        await wait(350);
        finishLog(current);
      }

      setCurrentUser(payload.user_id);
      queryClient.setQueryData(["latest", payload.user_id], snapshot);
      await queryClient.invalidateQueries({ queryKey: ["history", payload.user_id] });
      void queryClient.invalidateQueries({ queryKey: ["notifications", payload.user_id] });
      void queryClient.invalidateQueries({ queryKey: ["inputs", payload.user_id] });
      setResult(snapshot);
    } catch (err) {
      finishLog(current, "error");
      setBuildError(
        err instanceof ApiError
          ? `The engine rejected the request (${err.status}): ${err.message}`
          : "Could not reach the twin engine. Make sure the backend is running on port 8000.",
      );
    }
  }

  if (phase === "building") {
    return (
      <BuildSequence
        logs={logs}
        result={result}
        error={buildError}
        onRetry={() => void build()}
        onEdit={() => {
          setPhase("form");
          goTo(0);
        }}
      />
    );
  }

  const h = payload.health_inputs;
  const fi = payload.finance_inputs;
  const ins = payload.insurance_inputs;

  return (
    <div className="mx-auto grid max-w-6xl gap-6 lg:grid-cols-[1fr_320px]">
      <div className="flex flex-col gap-6">
        <div className="glass flex flex-wrap items-center gap-3 p-4">
          <span className="flex items-center gap-2 text-xs font-semibold tracking-widest text-champagne uppercase">
            <Sparkles className="h-3.5 w-3.5 text-gold" /> Demo personas
          </span>
          {PERSONAS.map((persona) => (
            <motion.button
              key={persona.key}
              type="button"
              whileHover={{ y: -2 }}
              whileTap={{ scale: 0.97 }}
              onClick={() => {
                setPayload(structuredClone(persona.payload));
                setErrors({});
              }}
              className={`rounded-xl border px-3 py-2 text-left transition-colors ${
                payload.user_id === persona.payload.user_id
                  ? "border-gold/60 bg-gold/10"
                  : "border-gold/15 hover:border-gold/40"
              }`}
            >
              <span className="block text-sm font-medium text-ivory">{persona.name}</span>
              <span className="block text-[11px] text-taupe">{persona.tagline}</span>
            </motion.button>
          ))}
        </div>

        <div className="glass p-6 md:p-8">
          <Stepper steps={STEPS} current={step} onSelect={goTo} />

          <form
            className="mt-10 overflow-hidden"
            onSubmit={(e) => {
              e.preventDefault();
              next();
            }}
            noValidate
          >
            <AnimatePresence mode="wait" custom={direction}>
              <motion.div
                key={step}
                custom={direction}
                variants={{
                  enter: (d: number) => ({ opacity: 0, x: d * 40 }),
                  center: { opacity: 1, x: 0 },
                  exit: (d: number) => ({ opacity: 0, x: d * -40 }),
                }}
                initial="enter"
                animate="center"
                exit="exit"
                transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
                className="grid gap-5 md:grid-cols-2"
              >
                {step === 0 && (
                  <>
                    <div className="md:col-span-2">
                      <h2 className="font-display text-2xl font-semibold">Who is this twin for?</h2>
                      <p className="mt-1 text-sm text-taupe">
                        Use a synthetic ID for demos. Data is stored only in your local database.
                      </p>
                    </div>
                    <div className="flex flex-col gap-2 md:col-span-2">
                      <label htmlFor="user-id" className="text-xs font-medium tracking-wide text-taupe uppercase">
                        Twin ID
                      </label>
                      <input
                        id="user-id"
                        value={payload.user_id}
                        onChange={(e) => setPayload((p) => ({ ...p, user_id: e.target.value.trim() }))}
                        aria-invalid={Boolean(errors.user_id)}
                        className={`rounded-xl border bg-ink/60 px-3 py-2.5 font-mono text-ivory outline-none focus:border-gold/70 ${
                          errors.user_id ? "border-risk/60" : "border-gold/15"
                        }`}
                      />
                      {errors.user_id && <span className="text-xs text-risk">{errors.user_id}</span>}
                    </div>
                    <NumberField label="Age" unit="years" value={h.age} min={18} max={90} slider onChange={(v) => setHealth("age", v)} error={errors.age} />
                    <Segmented
                      label="Sex"
                      value={h.gender}
                      options={[
                        { value: "female", label: "Female" },
                        { value: "male", label: "Male" },
                      ]}
                      onChange={(v) => setHealth("gender", v)}
                    />
                  </>
                )}

                {step === 1 && (
                  <>
                    <NumberField label="Height" unit="cm" value={h.height_cm} min={130} max={210} slider onChange={(v) => setHealth("height_cm", v)} error={errors.height_cm} />
                    <NumberField label="Weight" unit="kg" value={h.weight_kg} min={35} max={160} slider onChange={(v) => setHealth("weight_kg", v)} error={errors.weight_kg} />
                    <NumberField label="Systolic BP" unit="mmHg" value={h.ap_hi} min={80} max={200} slider onChange={(v) => setHealth("ap_hi", v)} error={errors.ap_hi} />
                    <NumberField label="Diastolic BP" unit="mmHg" value={h.ap_lo} min={50} max={130} slider onChange={(v) => setHealth("ap_lo", v)} error={errors.ap_lo} />
                    <NumberField
                      label="Fasting glucose"
                      unit="mg/dL"
                      value={h.blood_glucose_level}
                      min={60}
                      max={250}
                      slider
                      onChange={(v) => setHealth("blood_glucose_level", v)}
                      error={errors.blood_glucose_level}
                      hint="Below 100 is normal; 126+ is in the diabetes range."
                    />
                    <Segmented label="Cholesterol" value={h.cholesterol} options={LEVELS} onChange={(v) => setHealth("cholesterol", v)} />
                    <Segmented label="Glucose (lab category)" value={h.gluc} options={LEVELS} onChange={(v) => setHealth("gluc", v)} />
                    <Segmented label="Smoker" value={h.smoke} options={YES_NO} onChange={(v) => setHealth("smoke", v)} />
                    <Segmented label="Regular alcohol" value={h.alco} options={YES_NO} onChange={(v) => setHealth("alco", v)} />
                    <Segmented label="Physically active" value={h.active} options={YES_NO} onChange={(v) => setHealth("active", v)} />
                  </>
                )}

                {step === 2 && (
                  <>
                    <NumberField label="Monthly income" unit="₹" value={fi.income} step={1000} onChange={(v) => setFinance("income", v)} error={errors.income} />
                    <NumberField label="Savings balance" unit="₹" value={fi.savings_balance} step={1000} onChange={(v) => setFinance("savings_balance", v)} error={errors.savings_balance} />
                    <NumberField label="Fixed expenses" unit="₹ / month" value={fi.fixed_expenses} step={500} onChange={(v) => setFinance("fixed_expenses", v)} error={errors.fixed_expenses} hint="Rent, utilities, school fees" />
                    <NumberField label="Variable expenses" unit="₹ / month" value={fi.variable_expenses} step={500} onChange={(v) => setFinance("variable_expenses", v)} error={errors.variable_expenses} hint="Food, travel, shopping" />
                    <NumberField label="Loan EMIs" unit="₹ / month" value={fi.emis} step={500} onChange={(v) => setFinance("emis", v)} error={errors.emis} />
                  </>
                )}

                {step === 3 && (
                  <>
                    <NumberField label="Sum insured" unit="₹" value={ins.sum_insured} step={50000} onChange={(v) => setInsurance("sum_insured", v)} error={errors.sum_insured} />
                    <NumberField label="Annual premium" unit="₹ / year" value={ins.annual_premium} step={500} onChange={(v) => setInsurance("annual_premium", v)} error={errors.annual_premium} />
                    <fieldset className="flex flex-col gap-2 md:col-span-2">
                      <legend className="mb-2 text-xs font-medium tracking-wide text-taupe uppercase">Riders you already hold</legend>
                      <div className="flex flex-wrap gap-2">
                        {RIDERS.map((rider) => {
                          const held = ins.existing_riders.includes(rider);
                          return (
                            <motion.button
                              key={rider}
                              type="button"
                              whileTap={{ scale: 0.95 }}
                              aria-pressed={held}
                              onClick={() =>
                                setInsurance(
                                  "existing_riders",
                                  held ? ins.existing_riders.filter((r) => r !== rider) : [...ins.existing_riders, rider],
                                )
                              }
                              className={`rounded-full border px-3 py-1.5 text-sm transition-colors ${
                                held ? "border-gold bg-gold/15 text-champagne" : "border-gold/15 text-taupe hover:border-gold/40"
                              }`}
                            >
                              {rider}
                            </motion.button>
                          );
                        })}
                      </div>
                    </fieldset>
                  </>
                )}
              </motion.div>
            </AnimatePresence>

            <div className="mt-10 flex items-center justify-between">
              <button
                type="button"
                onClick={() => goTo(step - 1)}
                className={`btn-ghost ${step === 0 ? "invisible" : ""}`}
              >
                <ArrowLeft className="h-4 w-4" /> Back
              </button>
              <button type="submit" className="btn-gold">
                {step === STEPS.length - 1 ? (
                  <>
                    Build my twin <Sparkles className="h-4 w-4" />
                  </>
                ) : (
                  <>
                    Continue <ArrowRight className="h-4 w-4" />
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>

      <TwinReadout payload={payload} step={Math.max(step, 1)} />
    </div>
  );
}
