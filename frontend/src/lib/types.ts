export type Gender = "male" | "female";

export type HealthInputs = {
  age: number;
  gender: Gender;
  height_cm: number;
  weight_kg: number;
  ap_hi: number;
  ap_lo: number;
  cholesterol: 1 | 2 | 3;
  gluc: 1 | 2 | 3;
  smoke: 0 | 1;
  alco: 0 | 1;
  active: 0 | 1;
  blood_glucose_level: number;
};

export type FinanceInputs = {
  income: number;
  fixed_expenses: number;
  variable_expenses: number;
  emis: number;
  savings_balance: number;
};

export type InsuranceInputs = {
  sum_insured: number;
  annual_premium: number;
  existing_riders: string[];
};

export type OnboardPayload = {
  user_id: string;
  health_inputs: HealthInputs;
  finance_inputs: FinanceInputs;
  insurance_inputs: InsuranceInputs;
};

export type ShapFeature = { feature: string; impact: number; model: string };

export type HealthProfile = {
  bmi: number;
  obesity_class: string;
  hypertension_stage: string;
  cardio_risk: { probability: number; label: string };
  diabetes_indicator: string;
  framingham_10yr_risk: number;
  overall_health_score: number;
  shap_top_features: ShapFeature[];
};

export type FinanceProfile = {
  dti_ratio: number;
  savings_rate: number;
  emergency_fund_months: number | null;
  financial_stability_score: number;
  disposable_income: number;
  monthly_income: number;
  monthly_expenses: number;
  savings_balance: number;
};

export type InsuranceProfile = {
  estimated_future_cost: number;
  cost_breakdown: Record<string, number>;
  coverage_adequacy_ratio: number | null;
  premium_affordability_ratio: number;
  rider_analysis: { recommended: string[]; existing: string[]; gaps: string[]; gap_count: number };
  insurance_adequacy_score: number;
  disclaimer: string;
};

export type Snapshot = {
  snapshot_id: number;
  user_id: string;
  created_at: string;
  health: HealthProfile;
  finance: FinanceProfile;
  insurance: InsuranceProfile;
};

export type Profiles = { health: HealthProfile; finance: FinanceProfile; insurance: InsuranceProfile };

export type ToolCall = { tool: string; input: Record<string, unknown>; result: Record<string, unknown> };

export type Notification = {
  id: number;
  created_at: string;
  type: string;
  severity: "info" | "warning";
  message: string;
  data: Record<string, unknown>;
  snapshot_id: number;
  read: boolean;
};

export type ChatMessage = {
  chat_id: number;
  created_at: string;
  query: string;
  routing: { twins?: string[]; mode?: string; simulate?: boolean };
  pipeline: string[];
  narration: string;
  narration_error: string | null;
  citations: { source: string; score: number | null; excerpt: string }[];
  simulation: null | { error: string } | { recommendation: string; tool_trace: ToolCall[]; iterations: number };
};

export type SavingsBand = { month: number; p10: number; median: number; p90: number };

export type SimulateRequest = {
  user_id: string;
  health?: Partial<Omit<HealthInputs, "gender">>;
  finance?: Partial<FinanceInputs>;
  insurance?: Partial<InsuranceInputs>;
  forecast_months?: number;
};

export type SimulateResponse = {
  user_id: string;
  changes: { health: Record<string, unknown>; finance: Record<string, unknown>; insurance: Record<string, unknown> };
  before: Profiles;
  after: Profiles;
  forecast: { months: number; before: SavingsBand[]; after: SavingsBand[] };
};

export type WhatIfResponse = {
  user_id: string;
  purchase_cost: number;
  finance: FinanceProfile;
  affordable: boolean;
  affordability_score: number | null;
  impact_analysis: {
    new_dti_if_emi: number;
    new_dti_if_emi_24months: number;
    monthly_emi_12months: number;
    months_to_save: number | null;
    emergency_fund_impact: string;
    emergency_fund_months_after_purchase: number | null;
  };
  alternatives: { rank: number; strategy: string; detail: string; estimated_savings: number }[];
  disclaimer: string;
};
