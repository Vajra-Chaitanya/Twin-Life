// Client-side mirror of formulas.py, used only for the live preview; the backend remains the source of truth.

export type Tone = "good" | "warn" | "risk";

export const bmi = (heightCm: number, weightKg: number) =>
  heightCm > 0 && weightKg > 0 ? Math.round((weightKg / (heightCm / 100) ** 2) * 10) / 10 : NaN;

export function whoObesityClass(value: number): string {
  if (value < 18.5) return "Underweight";
  if (value < 25) return "Normal weight";
  if (value < 30) return "Overweight (Pre-obese)";
  if (value < 35) return "Obese Class I";
  if (value < 40) return "Obese Class II";
  return "Obese Class III";
}

export function bpStage(systolic: number, diastolic: number): string {
  if (systolic >= 140 || diastolic >= 90) return "Stage 2";
  if (systolic >= 130 || diastolic >= 80) return "Stage 1";
  if (systolic >= 120 && systolic <= 129 && diastolic < 80) return "Elevated";
  return "Normal";
}

export function diabetesIndicator(glucose: number): string {
  if (glucose < 100) return "Low";
  if (glucose < 126) return "Medium";
  return "High";
}

const round2 = (x: number) => Math.round(x * 100) / 100;
const clamp01 = (x: number) => Math.max(0, Math.min(1, x));

export const dtiRatio = (fixed: number, emis: number, income: number) =>
  income > 0 ? round2((fixed + emis) / income) : NaN;

export const savingsRate = (income: number, fixed: number, variable: number) =>
  income > 0 ? round2((income - fixed - variable) / income) : NaN;

export const emergencyFundMonths = (savings: number, fixed: number, variable: number) =>
  fixed + variable === 0 ? Infinity : Math.round((savings / (fixed + variable)) * 10) / 10;

export function financialStabilityScore(dti: number, savRate: number, efMonths: number): number {
  const inverseDti = (1 - clamp01(dti)) * 100;
  const savings = clamp01(savRate) * 100;
  const ef = Math.min(efMonths / 6, 1) * 100;
  return Math.round(0.3 * inverseDti + 0.3 * savings + 0.2 * ef + 0.2 * inverseDti);
}

export const premiumAffordabilityRatio = (premium: number, annualIncome: number) =>
  annualIncome > 0 ? Math.round((premium / annualIncome) * 1000) / 1000 : NaN;

export function bmiTone(value: number): Tone {
  if (value >= 18.5 && value < 25) return "good";
  if (value >= 30 || value < 17) return "risk";
  return "warn";
}

export const bpTone = (stage: string): Tone =>
  stage === "Normal" ? "good" : stage === "Elevated" ? "warn" : "risk";

export const levelTone = (level: string): Tone =>
  level === "Low" ? "good" : level === "Medium" || level === "Moderate" ? "warn" : "risk";

export const dtiTone = (x: number): Tone => (x <= 0.36 ? "good" : x <= 0.43 ? "warn" : "risk");
export const savingsTone = (x: number): Tone => (x >= 0.2 ? "good" : x >= 0.1 ? "warn" : "risk");
export const efTone = (x: number): Tone => (x >= 6 ? "good" : x >= 3 ? "warn" : "risk");
export const scoreTone = (x: number): Tone => (x >= 70 ? "good" : x >= 45 ? "warn" : "risk");
export const premiumTone = (x: number): Tone => (x <= 0.05 ? "good" : x <= 0.1 ? "warn" : "risk");
