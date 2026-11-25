export type Gender = "male" | "female";

export type HealthInputs = {
  conditions?: string[];
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
  annual_income?: number | null;
  existing_riders: string[];
  policies?: Policy[];
};

export type OnboardPayload = {
  user_id: string;
  health_inputs: HealthInputs;
  finance_inputs: FinanceInputs;
  insurance_inputs: InsuranceInputs;
};

export type ShapFeature = { feature: string; impact: number; model: string };

export type DiabetesRisk = { probability: number; label: string; hba1c: number; hba1c_estimated: boolean; diagnosed: boolean };

export type HealthProfile = {
  bmi: number;
  obesity_class: string;
  hypertension_stage: string;
  cardio_risk: { probability: number; label: string };
  cardio_model_version?: string;
  diabetes_indicator: string;
  diabetes_risk?: DiabetesRisk | null;
  diabetes_unavailable_reason?: "missing_hba1c" | "model_unavailable" | null;
  diabetes_shap?: ShapFeature[];
  conditions?: string[];
  condition_penalty?: number;
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
  portfolio?: Portfolio;
  disclaimer: string;
};

export type PolicyType = "vehicle" | "life" | "home" | "travel" | "health_topup" | "gadget" | "other";
export type Policy = { type: PolicyType; name: string; cover: number; premium: number; renewal_date: string | null; renewal_confirmed?: boolean };
export type Portfolio = {
  policies: Policy[];
  health_cover: number;
  total_annual_premium: number;
  life_cover: number;
  life_cover_recommended: number;
  life_cover_gap: number;
  types_held: string[];
};

export type DueStatus = "overdue" | "expired" | "missing" | "outstanding" | "due_soon" | "upcoming";
export type Due = {
  kind: "instalment" | "debt" | "receivable" | "renewal" | "missing_policy";
  domain: Twin;
  title: string;
  amount: number;
  due_date: string | null;
  status: DueStatus;
  detail: string;
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
  snapshot_id: number | null;
  domain?: Twin;
  read: boolean;
  historical?: boolean;
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
  thread_id?: string;
  domain?: Twin | null;
  refined_query?: string | null;
  context_turns?: number;
  scenarios?: Scenario[];
  updates?: LifeEvent[];
  reverted?: { id: number; summary: string; changes: LifeEvent["changes"] }[];
  pending_questions?: string[];
  simulatable?: string[];
};

export type Commitment = {
  item: string;
  emi: number;
  months?: number | null;
  start?: string;
  end?: string | null;
  lender?: string;
  principal?: number;
  informal?: boolean;
  receivable?: boolean;
};

export type Twin = "health" | "finance" | "insurance";

export type LifeEvent = {
  id: number;
  created_at: string;
  type: string;
  summary: string;
  domains: Twin[];
  log?: boolean;
  changes: { label: string; before: number | null; after: number | null }[];
  factor_impacts?: {
    domain: Twin;
    label: string;
    before: number | string | null;
    after: number | string | null;
    unit: string;
    delta: number | null;
    status: "changed" | "unchanged" | "unavailable";
  }[];
  health_impacts?: {
    label: string;
    before: number | null;
    after: number | null;
    note: string;
    weight_percent?: number;
    before_weighted_points?: number | null;
    after_weighted_points?: number | null;
  }[];
  commitment?: Commitment | null;
  alerts_generated?: number;
  snapshot_id: number | null;
  undone: boolean;
};

export type Scenario = {
  kind: string;
  verdict: string;
  headline: string;
  facts: string[];
  actions: string[];
  assumptions: string[];
  metrics: { label: string; before: string; after: string; better: boolean | null }[];
};

export type ChatThread = {
  thread_id: string;
  title: string;
  messages: number;
  updated_at: string;
  created_at?: string;
  domain?: Twin | null;
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

export type AdviceChange = {
  domain: Twin;
  field: string;
  label: string;
  current: number | string[];
  target: number | string[];
  basis: string;
};

export type AdviceSimulationResponse = {
  user_id: string;
  advice: string;
  changes: AdviceChange[];
  already_met: AdviceChange[];
  before: Profiles;
  after: Profiles;
  factor_impacts: NonNullable<LifeEvent["factor_impacts"]>;
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
