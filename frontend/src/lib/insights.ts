import { FEATURE_LABELS, formatPct } from "./format";
import type { Tone } from "./formulas";
import type { Snapshot } from "./types";

export type Signal = { tone: Tone; domain: "health" | "finance" | "insurance"; text: string };

/** Deterministic, threshold-based highlights derived from a snapshot. */
export function deriveSignals(s: Snapshot): Signal[] {
  const out: Signal[] = [];
  const { health: h, finance: f, insurance: i } = s;

  const topDriver = h.shap_top_features.find((x) => x.impact > 0);
  if (["High", "Very High", "Elevated"].includes(h.cardio_risk.label)) {
    out.push({
      tone: "risk",
      domain: "health",
      text: `Cardiovascular risk is ${h.cardio_risk.label} (${formatPct(h.cardio_risk.probability, 1)})${
        topDriver ? `, driven most by ${FEATURE_LABELS[topDriver.feature] ?? topDriver.feature}` : ""
      }.`,
    });
  }
  if (h.hypertension_stage.startsWith("Stage")) {
    out.push({ tone: h.hypertension_stage === "Stage 2" ? "risk" : "warn", domain: "health", text: `Blood pressure is in hypertension ${h.hypertension_stage}.` });
  }
  if (h.diabetes_indicator !== "Low") {
    out.push({
      tone: h.diabetes_indicator === "High" ? "risk" : "warn",
      domain: "health",
      text: `Fasting glucose indicates ${h.diabetes_indicator === "High" ? "the diabetes range" : "pre-diabetes"}.`,
    });
  }
  if (h.bmi >= 25) out.push({ tone: h.bmi >= 30 ? "risk" : "warn", domain: "health", text: `BMI ${h.bmi} (${h.obesity_class}).` });

  if (f.dti_ratio > 0.36) {
    out.push({ tone: f.dti_ratio > 0.43 ? "risk" : "warn", domain: "finance", text: `Debt-to-income ${formatPct(f.dti_ratio)} is above the 36% comfort line.` });
  }
  if (f.savings_rate < 0.1) out.push({ tone: "risk", domain: "finance", text: `Savings rate is only ${formatPct(f.savings_rate)}.` });
  if (f.emergency_fund_months !== null && f.emergency_fund_months < 6) {
    out.push({
      tone: f.emergency_fund_months < 3 ? "risk" : "warn",
      domain: "finance",
      text: `Emergency fund covers ${f.emergency_fund_months} months; 6 is recommended.`,
    });
  }
  if (f.disposable_income < 0) out.push({ tone: "risk", domain: "finance", text: "Monthly outflows exceed income." });

  if (i.coverage_adequacy_ratio !== null && i.coverage_adequacy_ratio < 1) {
    out.push({ tone: "risk", domain: "insurance", text: `Cover meets only ${formatPct(i.coverage_adequacy_ratio)} of projected 5-year medical costs.` });
  }
  if (i.rider_analysis.gap_count > 0) {
    out.push({ tone: "warn", domain: "insurance", text: `${i.rider_analysis.gap_count} recommended rider(s) missing.` });
  }
  if (i.premium_affordability_ratio > 0.1) {
    out.push({ tone: "warn", domain: "insurance", text: `Premiums take ${formatPct(i.premium_affordability_ratio, 1)} of income.` });
  }

  if (out.length === 0) out.push({ tone: "good", domain: "health", text: "All core signals are within healthy ranges." });
  const rank: Record<Tone, number> = { risk: 0, warn: 1, good: 2 };
  return out.sort((a, b) => rank[a.tone] - rank[b.tone]);
}
