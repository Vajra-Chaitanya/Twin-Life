import type { OnboardPayload } from "./types";

export type Persona = { key: string; name: string; tagline: string; payload: OnboardPayload };

// Synthetic demo people only; no real personal data.
export const PERSONAS: Persona[] = [
  {
    key: "ananya",
    name: "Ananya, 32",
    tagline: "Healthy & financially balanced",
    payload: {
      user_id: "demo-ananya",
      health_inputs: {
        age: 32, gender: "female", height_cm: 162, weight_kg: 56, ap_hi: 112, ap_lo: 72,
        cholesterol: 1, gluc: 1, smoke: 0, alco: 0, active: 1, blood_glucose_level: 88,
      },
      finance_inputs: {
        income: 120_000, fixed_expenses: 30_000, variable_expenses: 25_000, emis: 8_000, savings_balance: 450_000,
      },
      insurance_inputs: { sum_insured: 1_000_000, annual_premium: 18_000, existing_riders: ["Personal Accident Rider"] },
    },
  },
  {
    key: "meera",
    name: "Meera, 45",
    tagline: "Pre-diabetic, stretched budget",
    payload: {
      user_id: "demo-meera",
      health_inputs: {
        age: 45, gender: "female", height_cm: 158, weight_kg: 72, ap_hi: 128, ap_lo: 82,
        cholesterol: 2, gluc: 2, smoke: 0, alco: 0, active: 0, blood_glucose_level: 112,
      },
      finance_inputs: {
        income: 85_000, fixed_expenses: 32_000, variable_expenses: 30_000, emis: 12_000, savings_balance: 120_000,
      },
      insurance_inputs: { sum_insured: 300_000, annual_premium: 14_000, existing_riders: [] },
    },
  },
  {
    key: "rahul",
    name: "Rahul, 56",
    tagline: "High cardiac risk, heavy EMIs",
    payload: {
      user_id: "demo-rahul",
      health_inputs: {
        age: 56, gender: "male", height_cm: 172, weight_kg: 92, ap_hi: 152, ap_lo: 96,
        cholesterol: 3, gluc: 2, smoke: 1, alco: 1, active: 0, blood_glucose_level: 134,
      },
      finance_inputs: {
        income: 140_000, fixed_expenses: 45_000, variable_expenses: 40_000, emis: 38_000, savings_balance: 200_000,
      },
      insurance_inputs: { sum_insured: 500_000, annual_premium: 42_000, existing_riders: [] },
    },
  },
];

export const DEFAULT_PAYLOAD: OnboardPayload = structuredClone(PERSONAS[0].payload);
