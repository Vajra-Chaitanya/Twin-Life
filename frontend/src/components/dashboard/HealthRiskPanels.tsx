import { BrainCircuit, Droplets, HeartPulse, RefreshCw } from "lucide-react";
import { useState } from "react";
import { bmiTone, bpTone, levelTone, type Tone } from "../../lib/formulas";
import { useReassess } from "../../lib/queries";
import type { HealthProfile } from "../../lib/types";
import { useCurrentUser } from "../../lib/user";
import { Panel } from "./Panel";
import { RiskGauge } from "./RiskGauge";
import { ShapChart } from "./ShapChart";

const TONE_TEXT: Record<Tone, string> = { good: "text-good", warn: "text-warn", risk: "text-risk" };
const TONE_BORDER: Record<Tone, string> = { good: "border-good/30", warn: "border-warn/30", risk: "border-risk/40" };

export function Vital({ label, value, tone }: { label: string; value: string; tone: Tone }) {
  return (
    <div className={`rounded-xl border bg-ink/40 px-3 py-2.5 ${TONE_BORDER[tone]}`}>
      <p className="text-[10px] tracking-widest text-taupe uppercase">{label}</p>
      <p className={`mt-0.5 font-mono text-sm ${TONE_TEXT[tone]}`}>{value}</p>
    </div>
  );
}

export function CardioRiskPanel({ h, className }: { h: HealthProfile; className?: string }) {
  const framinghamTone: Tone = h.framingham_10yr_risk < 10 ? "good" : h.framingham_10yr_risk < 20 ? "warn" : "risk";
  return (
    <Panel title="Cardiovascular model estimate" icon={HeartPulse} accent="text-health" subtitle="Experimental disease classification; not a future-risk forecast" className={className}>
      {h.cardio_model_version === "smoking_monotonic_v1" ? (
        <RiskGauge probability={h.cardio_risk.probability} label={h.cardio_risk.label} />
      ) : <ReassessPrompt />}
      <div className="mt-5 grid grid-cols-2 gap-2">
        <Vital label="BMI" value={`${h.bmi}`} tone={bmiTone(h.bmi)} />
        <Vital label="Blood pressure" value={h.hypertension_stage} tone={bpTone(h.hypertension_stage)} />
        <Vital label="Framingham 10y" value={`${h.framingham_10yr_risk}%`} tone={framinghamTone} />
        <Vital label="Obesity class" value={h.obesity_class.replace(/ \(.*\)/, "")} tone={bmiTone(h.bmi)} />
      </div>
    </Panel>
  );
}

export function DiabetesRiskPanel({ h, className }: { h: HealthProfile; className?: string }) {
  const d = h.diabetes_risk?.hba1c_estimated ? null : h.diabetes_risk;
  const hba1cTone: Tone = !d ? "good" : d.hba1c >= 6.5 ? "risk" : d.hba1c >= 5.7 ? "warn" : "good";
  return (
    <Panel title="Diabetes model estimate" icon={Droplets} accent="text-health" subtitle="Experimental disease classification; not a diagnosis" className={className}>
      {d ? (
        <>
          {d.diagnosed ? (
            <div className="flex h-[150px] flex-col items-center justify-center text-center">
              <p className="font-display text-3xl font-semibold text-risk">Diagnosed</p>
              <p className="mt-2 text-xs text-taupe">Recorded in your medical history. Discuss individual targets with your clinician.</p>
            </div>
          ) : (
            <RiskGauge probability={d.probability} label={d.label} />
          )}
          <div className="mt-5 grid grid-cols-2 gap-2">
            <Vital label={d.hba1c_estimated ? "HbA1c (est.)" : "HbA1c"} value={`${d.hba1c}%`} tone={hba1cTone} />
            <Vital label="Glucose level" value={h.diabetes_indicator} tone={levelTone(h.diabetes_indicator)} />
          </div>
          <p className="mt-3 text-[11px] text-taupe/70">This dataset model is not clinically validated and must not be used to diagnose diabetes.</p>
        </>
      ) : h.diabetes_unavailable_reason === "missing_hba1c" || h.diabetes_risk?.hba1c_estimated ? (
        <p className="text-sm text-taupe">A measured HbA1c is needed for the diabetes model. Tell the advisor your laboratory result, for example: "My HbA1c is 6.1".</p>
      ) : h.diabetes_unavailable_reason === "model_unavailable" ? (
        <p className="text-sm text-taupe">The diabetes model is unavailable on this installation.</p>
      ) : (
        <ReassessPrompt />
      )}
    </Panel>
  );
}

function ReassessPrompt() {
  const reassess = useReassess(useCurrentUser());
  return (
    <div className="flex flex-col items-start gap-3">
      <p className="text-sm text-taupe">This snapshot predates the current models. Reassess to update it.</p>
      <button type="button" onClick={() => reassess.mutate()} disabled={reassess.isPending} className="btn-gold px-3 py-1.5 text-xs disabled:opacity-60">
        <RefreshCw className={`h-3.5 w-3.5 ${reassess.isPending ? "animate-spin" : ""}`} /> {reassess.isPending ? "Re-assessing…" : "Re-assess now"}
      </button>
    </div>
  );
}

export function RiskExplainPanel({ h, className }: { h: HealthProfile; className?: string }) {
  const [model, setModel] = useState<"cardio" | "diabetes">("cardio");
  const features = model === "cardio" ? (h.cardio_model_version === "smoking_monotonic_v1" ? h.shap_top_features : []) : h.diabetes_risk?.hba1c_estimated ? [] : h.diabetes_shap ?? [];
  return (
    <Panel
      title="Why these risks?"
      icon={BrainCircuit}
      accent="text-health"
      subtitle="SHAP attribution: each factor's push on the model's prediction"
      className={className}
      action={
        <div role="radiogroup" aria-label="Model" className="flex rounded-lg border border-gold/15 p-0.5 text-xs">
          {(["cardio", "diabetes"] as const).map((m) => (
            <button
              key={m}
              type="button"
              role="radio"
              aria-checked={model === m}
              onClick={() => setModel(m)}
              className={`rounded-md px-2.5 py-1 ${model === m ? "bg-gold/20 text-champagne" : "text-taupe"}`}
            >
              {m === "cardio" ? "Heart" : "Diabetes"}
            </button>
          ))}
        </div>
      }
    >
      <ShapChart features={features} />
      <p className="mt-5 text-[11px] text-taupe/70">
        Values are percentage-point contributions to the predicted probability relative to the model's average.
      </p>
    </Panel>
  );
}
