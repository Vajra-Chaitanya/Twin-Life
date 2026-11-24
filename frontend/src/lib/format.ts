const inr = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });

export const formatINR = (value: number | null | undefined) =>
  value === null || value === undefined || !Number.isFinite(value) ? "—" : inr.format(value);

export const formatPct = (value: number | null | undefined, digits = 0) =>
  value === null || value === undefined || !Number.isFinite(value) ? "—" : `${(value * 100).toFixed(digits)}%`;

export function formatRelative(iso: string): string {
  // SQLite returns naive timestamps that were written in UTC.
  const date = new Date(/[zZ]|[+-]\d\d:\d\d$/.test(iso) ? iso : `${iso}Z`);
  const minutes = Math.round((Date.now() - date.getTime()) / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} h ago`;
  return date.toLocaleString();
}

export const FEATURE_LABELS: Record<string, string> = {
  age_years: "Age",
  gender: "Sex",
  bmi: "BMI",
  ap_hi: "Systolic BP",
  ap_lo: "Diastolic BP",
  cholesterol: "Cholesterol",
  gluc: "Glucose category",
  smoke: "Smoking",
  alco: "Alcohol",
  active: "Physical activity",
  age: "Age",
  hypertension: "Hypertension",
  heart_disease: "Heart disease",
  HbA1c_level: "HbA1c",
  blood_glucose_level: "Blood glucose",
  smoking: "Smoking history",
};
