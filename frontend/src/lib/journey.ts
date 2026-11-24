import type { OnboardPayload } from "./types";

export type JourneyStep = { note: string; payload: OnboardPayload };

const lerp = (a: number, b: number, t: number) => Math.round(a + (b - a) * t);

/** A synthetic six-checkpoint improvement plan applied to a persona's baseline inputs. */
export function buildJourney(base: OnboardPayload): JourneyStep[] {
  const h0 = base.health_inputs;
  const f0 = base.finance_inputs;
  const i0 = base.insurance_inputs;
  const targetWeight = Math.min(h0.weight_kg, Math.round(24 * (h0.height_cm / 100) ** 2));
  const notes = [
    "Baseline",
    "Started daily walks",
    "Quit smoking, cut sugar",
    "Prepaid a loan, added riders",
    "Lost weight, BP improving",
    "Six-month review",
  ];

  return notes.map((note, k) => {
    const t = k / (notes.length - 1);
    const riders = k >= 3 ? ["Critical Illness Rider", "Hospital Cash Rider", "Personal Accident Rider", "Diabetes Care Rider"] : i0.existing_riders;
    return {
      note,
      payload: {
        user_id: base.user_id,
        health_inputs: {
          ...h0,
          weight_kg: lerp(h0.weight_kg, targetWeight, t),
          ap_hi: lerp(h0.ap_hi, Math.min(h0.ap_hi, 118), t),
          ap_lo: lerp(h0.ap_lo, Math.min(h0.ap_lo, 76), t),
          blood_glucose_level: lerp(h0.blood_glucose_level, Math.min(h0.blood_glucose_level, 92), t),
          active: k >= 1 ? 1 : h0.active,
          smoke: k >= 2 ? 0 : h0.smoke,
          alco: k >= 2 ? 0 : h0.alco,
          cholesterol: k >= 4 ? 1 : h0.cholesterol,
          gluc: k >= 4 ? 1 : h0.gluc,
        },
        finance_inputs: {
          ...f0,
          emis: k >= 3 ? Math.round(f0.emis * 0.4) : f0.emis,
          variable_expenses: lerp(f0.variable_expenses, f0.variable_expenses * 0.85, t),
          savings_balance: lerp(f0.savings_balance, f0.savings_balance + f0.income * 2, t),
        },
        insurance_inputs: {
          ...i0,
          existing_riders: [...new Set(riders)],
          sum_insured: k >= 3 ? Math.max(i0.sum_insured, 1_500_000) : i0.sum_insured,
          annual_premium: k >= 3 ? Math.round(i0.annual_premium * 1.35) : i0.annual_premium,
        },
      },
    };
  });
}
