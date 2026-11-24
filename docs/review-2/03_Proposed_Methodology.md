# Proposed Methodology

## Project Title: TwinLife AI — Autonomous Multi-Domain Digital Twin Platform for Personalized Health, Financial, and Insurance Decision Support

---

## Table of Contents

1. [Overview of the Proposed System](#1-overview-of-the-proposed-system)
2. [System Architecture](#2-system-architecture)
3. [Module 1: Domain Formulas (formulas.py)](#3-module-1-domain-formulas)
4. [Module 2: Machine Learning Models](#4-module-2-machine-learning-models)
5. [Module 3: Digital Twin Classes](#5-module-3-digital-twin-classes)
6. [Module 4: Orchestrator and Autonomous Agent](#6-module-4-orchestrator-and-autonomous-agent)
7. [Module 5: RAG Pipeline](#7-module-5-rag-pipeline)
8. [Module 6: Narration and Explainability Layer](#8-module-6-narration-and-explainability-layer)
9. [Module 7: Simulation Engine](#9-module-7-simulation-engine)
10. [Module 8: Proactive Monitoring Agent](#10-module-8-proactive-monitoring-agent)
11. [Module 9: Daily-Use Engagement Layer](#11-module-9-daily-use-engagement-layer)
12. [Backend API Design](#12-backend-api-design)
13. [Frontend Design](#13-frontend-design)
14. [Technology Stack](#14-technology-stack)
15. [Implementation Roadmap](#15-implementation-roadmap)
16. [Evaluation Plan](#16-evaluation-plan)

---

## 1. Overview of the Proposed System

TwinLife AI is an Autonomous Multi-Domain Digital Twin Platform that creates three coordinated virtual representations — a Health Twin, a Finance Twin, and an Insurance Twin — for each individual user. An AI Orchestrator monitors user interactions and autonomously decides which twin(s) to activate for a given query. The system integrates Machine Learning risk prediction, SHAP-based explainability, Retrieval-Augmented Generation with real clinical and financial guidelines, stochastic and deterministic simulation, and a proactive monitoring agent — delivering cross-domain, personalized, and explainable decision support.

### 1.1 Core Design Principles

| Principle | Implementation in TwinLife AI |
|---|---|
| **Grounded, not hallucinated** | Every risk score comes from a trained ML model or a validated formula — the LLM only narrates, it does not compute |
| **Explainable, not opaque** | SHAP attributes each ML prediction to input features; RAG cites the specific guideline standard supporting each recommendation |
| **Agentic, not scripted** | The Orchestrator dynamically routes each query to the relevant twins; the combined simulator autonomously calls tools in an iterative loop |
| **Proactive, not passive** | The Monitoring Agent detects threshold crossings weekly and pushes alerts without waiting for user queries |
| **Cross-domain, not siloed** | All three twins share state; the cross-domain decision tree synthesizes health, financial, and insurance data into a single optimized recommendation |

---

## 2. System Architecture

The complete system pipeline is structured as six sequential stages:

```
STAGE 1: USER INPUT
   (Onboarding form / Chat query / Voice / Photo scan)
                |
                v
STAGE 2: TWIN COMPUTATION
   Health Twin    -->  ML Model + Clinical Formulas  -->  Health Profile JSON
   Finance Twin   -->  Financial Formulas            -->  Finance Profile JSON
   Insurance Twin -->  Rule Engine                   -->  Insurance Profile JSON
                |
                v
STAGE 3: SHAP EXPLANATION
   (Applied to ML model outputs only — not formulas)
   TreeSHAP  -->  Feature attribution values per prediction
                |
                v
STAGE 4: ORCHESTRATOR ROUTING
   Rule-based fast path (keyword matching)
        OR
   LLM fallback (Gemini API, ambiguous queries only)
   --> Decides: which twins, single/cross domain, simulate yes/no
                |
                v
STAGE 5: RAG EVIDENCE RETRIEVAL
   ChromaDB semantic search over:
   ADA Guidelines | WHO Guidelines | ACC/AHA | RBI Docs | IRDAI Circulars
   --> Returns top-3 relevant chunks for the detected topic
                |
                v
STAGE 6: LLM NARRATION
   Gemini API call:
   Input: Twin scores + SHAP values + RAG chunks
   Output: Single cited, plain-language explanation
                |
                v
STAGE 7 (CONDITIONAL): SIMULATION ENGINE
   Triggered only if query contains a "what-if" or cross-domain affordability request.
   Re-runs Stages 2-6 on hypothetical modified inputs.
   Returns: Before / After comparison + ranked alternative scenarios.
```

---

## 3. Module 1: Domain Formulas

**File:** `formulas.py`
**Type:** Pure deterministic Python functions — zero external side-effects, fully unit-testable.

### 3.1 Health Formulas

| Formula | Standard | Output |
|---|---|---|
| BMI Calculation | WHO (2000) | BMI value (float) |
| Obesity Classification | WHO BMI bands | Underweight / Normal / Overweight / Obese (Class I/II/III) |
| Blood Pressure Staging | ACC/AHA 2017 | Normal / Elevated / Stage 1 HTN / Stage 2 HTN / Crisis |
| Framingham 10-Year CVD Risk | D'Agostino et al. (2008) | 10-year CVD risk percentage (float) |
| Diabetes Indicator | ADA glucose thresholds (2023) | Normal / Pre-diabetic / Diabetic |
| Overall Health Score (0-100) | Weighted composite | Score = 0.25(BMI) + 0.25(BP) + 0.25(Cardio) + 0.15(Diabetes) + 0.10(Framingham) |

### 3.2 Finance Formulas

| Formula | Standard | Output |
|---|---|---|
| Debt-to-Income (DTI) Ratio | RBI / Consumer Finance Guidelines | (Fixed Expenses + EMIs) / Monthly Income |
| Savings Rate | Personal Finance Standard | (Income - Fixed - Variable) / Income |
| Emergency Fund Coverage | Financial Planning Standard | Liquid Savings / Monthly Total Expenses (in months) |
| Financial Stability Score (0-100) | Weighted composite | Score based on DTI, savings rate, emergency fund |
| Treatment Affordability Score | Derived | (Disposable Income x N months) / Treatment Cost |

### 3.3 Insurance Formulas

| Formula | Standard | Output |
|---|---|---|
| Coverage Adequacy Ratio | IRDAI Guidelines | Sum Insured / Estimated 5-Year Treatment Cost |
| Premium Affordability Ratio | IRDAI Guidelines | Annual Premium / Annual Income |
| Out-of-pocket Expense | Rule-based | Treatment Cost - min(Sum Insured, Treatment Cost) |
| Insurance Adequacy Score (0-100) | Weighted composite | Based on Coverage Adequacy, Premium Affordability, Rider Gaps |

**Test Coverage:** All formulas are validated with a comprehensive unit test suite (`test_formulas.py`, 70+ tests).

---

## 4. Module 2: Machine Learning Models

**Files:** `train_cardio_model.py`, `train_diabetes_model.py`

TwinLife AI uses exactly two trained ML models, both within the Health Twin. Finance and Insurance twins use only formulas and rules — this is a deliberate engineering decision: DTI ratios, savings rates, and coverage adequacy calculations are inherently arithmetic problems with established standards, not pattern-recognition problems.

### 4.1 Cardiovascular Risk Model

| Attribute | Detail |
|---|---|
| Dataset | Kaggle Cardiovascular Disease Dataset (cardio_train.csv, 70,000 rows) |
| Preprocessing | Age: days to years (age // 365). BMI derived from height/weight. Physiological filtering: remove rows where ap_lo > ap_hi. Outlier removal for unrealistic height/weight/BP values. |
| Features (X) | age, gender, BMI, ap_hi (systolic BP), ap_lo (diastolic BP), cholesterol (ordinal: 1/2/3), gluc (ordinal: 1/2/3), smoke, alco, active |
| Target (y) | cardio (binary: 0 = no cardiovascular disease, 1 = cardiovascular disease) |
| Model | RandomForestClassifier(n_estimators=200, max_depth=10, min_samples_leaf=20) |
| Train/Test Split | 80% train / 20% test (stratified) |
| Achieved Metrics | Accuracy: 73.6% | F1-Score: 72.0% | ROC-AUC: 80.3% |
| Explainability | TreeSHAP applied post-training to compute per-instance feature attributions |
| Persistence | Saved to models/cardio_model.pkl using joblib |

### 4.2 Diabetes Risk Model

| Attribute | Detail |
|---|---|
| Dataset | Kaggle Diabetes Prediction Dataset (100,000 rows) |
| Preprocessing | Deduplication: 3,854 duplicate rows removed. One-hot encoding for categorical variables (gender, smoking_history). Class balancing: class_weight='balanced' to handle diabetes class imbalance (~8.5% positive). |
| Features (X) | age, gender (encoded), BMI, HbA1c_level, blood_glucose_level, hypertension, heart_disease, smoking_history (encoded) |
| Target (y) | diabetes (binary: 0 = no diabetes, 1 = diabetes) |
| Model | RandomForestClassifier(class_weight='balanced') |
| Train/Test Split | 80% train / 20% test (stratified) |
| Achieved Metrics | Accuracy: 90.2% | F1-Score: 61.7% | ROC-AUC: 97.5% |
| Explainability | TreeSHAP applied post-training |
| Persistence | Saved to models/diabetes_model.pkl using joblib |

### 4.3 Model Selection Justification

Random Forest was selected over deep learning alternatives for the following reasons:
1. **SHAP compatibility:** TreeSHAP computes exact Shapley values for tree-based models in polynomial time, making per-instance explanations computationally feasible.
2. **No GPU requirement:** 70,000 and 100,000 row datasets train in seconds on CPU, suitable for academic and local deployment environments.
3. **Robustness to tabular data:** Random Forest is empirically competitive with deep learning on structured clinical tabular datasets (Grinsztajn et al., 2022).
4. **Interpretability baseline:** The tree structure provides an inherent interpretability that is consistent with the project's explainability objectives.

---

## 5. Module 3: Digital Twin Classes

**Files:** `health_twin.py`, `finance_twin.py`, `insurance_twin.py`

Each twin class encapsulates all data, computation, and state for its domain. Twins are independently testable and communicate through the Orchestrator.

### 5.1 HealthTwin

**Input:** User health profile (age, gender, height, weight, BP, glucose, cholesterol, smoking, activity, family history, existing conditions).

**Processing Pipeline:**
1. Compute BMI and obesity class (formulas.py).
2. Compute hypertension stage (formulas.py).
3. Compute Framingham 10-Year CVD risk (formulas.py).
4. Compute diabetes indicator from glucose threshold (formulas.py).
5. Run Cardiovascular Risk ML model → predict probability and label.
6. Run Diabetes Risk ML model → predict probability and label.
7. Apply TreeSHAP to both model predictions → generate feature attribution dicts.
8. Compute Overall Health Score (0-100) using weighted formula.

**Output JSON Shape:**
```json
{
  "bmi": 27.0,
  "obesity_class": "Overweight",
  "hypertension_stage": "Stage 1",
  "framingham_10yr_risk": 0.12,
  "diabetes_indicator": "Pre-diabetic",
  "cardio_risk": {"probability": 0.42, "label": "Medium"},
  "diabetes_risk": {"probability": 0.31, "label": "Medium"},
  "shap_cardio": {"glucose": 0.18, "BMI": 0.12, "smoke": 0.09},
  "shap_diabetes": {"HbA1c_level": 0.22, "blood_glucose_level": 0.18},
  "overall_health_score": 58,
  "estimated_treatment_cost": 40000
}
```

### 5.2 FinanceTwin

**Input:** Monthly income, fixed expenses, variable expenses, savings balance, outstanding debt, dependents, employment type.

**Processing Pipeline:**
1. Compute DTI Ratio.
2. Compute Savings Rate.
3. Compute Emergency Fund Coverage (months).
4. Compute Financial Stability Score (0-100).
5. Compute Treatment Affordability Score for a given cost C over N months.
6. Generate 12-month Monte Carlo savings forecast (NumPy, N=1,000 paths) for what-if scenarios.

**Output JSON Shape:**
```json
{
  "dti_ratio": 0.31,
  "savings_rate": 0.15,
  "emergency_fund_months": 4.3,
  "financial_stability_score": 66,
  "affordability_score_for_40000": 0.72,
  "monthly_disposable_income": 14500,
  "forecast_12m_savings": {"median": 174000, "p10": 142000, "p90": 207000}
}
```

### 5.3 InsuranceTwin

**Input:** Sum insured, annual premium, policy type, existing riders, claims in last 12 months. (References HealthTwin output for estimated treatment cost and FinanceTwin output for income.)

**Processing Pipeline:**
1. Estimate 5-year condition-specific medical cost (lookup table keyed to HealthTwin risk labels).
2. Compute Coverage Adequacy Ratio.
3. Compute Premium Affordability Ratio (using income from FinanceTwin).
4. Flag rider gaps: compare HealthTwin's predicted high-risk conditions against existing riders.
5. Compute out-of-pocket expense for estimated treatment cost.
6. Compute Insurance Adequacy Score (0-100).

**Output JSON Shape:**
```json
{
  "estimated_future_cost_5yr": 200000,
  "coverage_adequacy_ratio": 2.5,
  "premium_affordability_ratio": 0.028,
  "rider_gaps": ["Critical Illness rider missing"],
  "out_of_pocket_for_treatment": 10000,
  "insurance_adequacy_score": 74
}
```

---

## 6. Module 4: Orchestrator and Autonomous Agent

**Files:** `orchestrator.py` (LangGraph router), `combined_simulator.py` (Gemini autonomous agent)

### 6.1 Orchestrator — LangGraph-Based Query Router

The Orchestrator is a two-stage routing system built with LangGraph:

**Stage 1 — Rule-Based Fast Path:**
Deterministic keyword matching routes the query to the correct twin(s) without any API call. This handles the majority of queries at zero cost.

**Stage 2 — LLM Classification Fallback:**
For queries that do not match any keyword pattern, a structured Gemini API call with a classification prompt returns a JSON routing decision specifying which twins to invoke, whether this is a single-domain or cross-domain query, and whether simulation is needed.

### 6.2 Autonomous Combined Simulator — Gemini Tool-Use Agent

For cross-domain affordability queries (e.g., "Should I proceed with a INR 500,000 cardiac treatment?"), an autonomous Gemini agent using function calling iteratively invokes four deterministic tools:

| Tool | Input | Output |
|---|---|---|
| `get_health_context(condition)` | Condition name string | Risk level, urgency, and estimated cost from HealthTwin |
| `check_affordability(cost)` | Treatment cost (INR) | Affordability score, affordable boolean, disposable income from FinanceTwin |
| `check_insurance_coverage(cost)` | Treatment cost (INR) | Covered amount, out-of-pocket gap from InsuranceTwin |
| `get_cheaper_alternative(condition, current_cost)` | Condition + current cost | Next lower-cost treatment tier name and cost |

The agent reasons autonomously — deciding which tool to call next based on the previous tool's output — until it reaches a final recommendation. Every tool call is logged in a `tool_trace` list for full transparency and auditability.

**Example Autonomous Execution Trace:**
```
[Agent] Prompt: Evaluate INR 500,000 Cardiac Treatment Plan

Step 1: CALL get_health_context("cardiac")
        --> {"risk_level": "High", "urgency": "Urgent", "estimated_cost": 500000}

Step 2: CALL check_affordability(500000)
        --> {"affordable": false, "affordability_score": 0.45, "disposable_12m": 174000}

Step 3: CALL check_insurance_coverage(500000)
        --> {"covered_amount": 300000, "out_of_pocket": 200000}

Step 4: CALL check_affordability(200000)  [checking if gap is affordable]
        --> {"affordable": false, "affordability_score": 0.51}

Step 5: CALL get_cheaper_alternative("cardiac", 500000)
        --> {"alternative": "Moderate Cardiac Intervention", "new_cost": 200000}

Step 6: CALL check_insurance_coverage(200000)
        --> {"covered_amount": 200000, "out_of_pocket": 0}

[Agent Synthesis] Final Recommendation: The moderate cardiac intervention at INR 200,000
is fully covered by your insurance. Recommend proceeding with this option and filing
an insurance claim. No out-of-pocket expense required.
```

---

## 7. Module 5: RAG Pipeline

**File:** `rag_agent.py`
**Vector Database:** ChromaDB
**Embedding Model:** sentence-transformers/all-MiniLM-L6-v2

### 7.1 Document Corpus

| Document | Domain | Source |
|---|---|---|
| ADA Standards of Medical Care in Diabetes 2023 | Health | American Diabetes Association |
| WHO Hypertension Guidelines | Health | World Health Organization |
| ACC/AHA 2017 Blood Pressure Guidelines | Health | American College of Cardiology |
| RBI Financial Literacy and Credit Counseling Guidelines | Finance | Reserve Bank of India |
| IRDAI Health Insurance Circulars | Insurance | Insurance Regulatory and Development Authority of India |

### 7.2 Ingestion Pipeline

```
1. Load PDF documents using PyPDFLoader (LangChain)
2. Split into 512-token chunks with 64-token overlap (RecursiveCharacterTextSplitter)
3. Embed each chunk using sentence-transformers/all-MiniLM-L6-v2
4. Store embeddings and metadata in ChromaDB (persistent local collection)
```

### 7.3 Retrieval Pipeline

```
1. Receive topic string from Orchestrator (e.g., "cardiovascular medium risk management")
2. Embed the topic string using the same sentence-transformers model
3. Perform cosine similarity search in ChromaDB
4. Return top-3 most semantically similar chunks with source metadata
5. Pass chunks to Narration Layer as grounding context
```

---

## 8. Module 6: Narration and Explainability Layer

**Implementation:** Gemini API (`google-genai` SDK), single structured prompt per query.

### 8.1 Prompt Structure

The narration prompt is assembled programmatically by concatenating:

```
[SYSTEM]:
You are TwinLife AI's explanation engine. You have been given:
1. Computed risk scores and financial metrics from domain formulas and ML models.
2. SHAP feature attributions explaining why the ML models produced their outputs.
3. Retrieved text chunks from real clinical and financial guidelines.

Your task: write a single, coherent, plain-language explanation for the user.
Rules:
- Every health or financial claim must cite the source guideline provided in the RAG context.
- Do not invent facts, statistics, or guideline text not present in the RAG context.
- Refer to the SHAP values to explain which specific factors are driving the risk score.
- Keep the explanation under 250 words. Use clear, non-technical language.

[USER DATA]:
Health Profile: {health_profile_json}
Finance Profile: {finance_profile_json}
Insurance Profile: {insurance_profile_json}
SHAP Attributions: {shap_dict}
Retrieved Guidelines: {rag_chunks_with_sources}
User Query: {user_query}
```

### 8.2 Output Example

```
Your cardiovascular risk score is 72% (High Risk). The two largest contributing factors are your 
blood glucose level — currently 138 mg/dL, which is above the pre-diabetic threshold of 126 mg/dL 
according to the ADA Standards of Care (2023) — and your BMI of 29.1, classified as Overweight 
by WHO guidelines. Together, these two factors account for 30% of your predicted risk elevation.

Financially, your current disposable income of INR 14,500/month means you can comfortably afford 
up to INR 3,200/month toward an ongoing treatment plan. Your emergency fund covers 4.3 months of 
expenses, which is above the 3-month recommended minimum.

Your insurance provides INR 300,000 coverage against an estimated treatment cost of INR 400,000, 
leaving a potential gap of INR 100,000. Note that your Critical Illness rider is absent; given your 
elevated cardiovascular risk, the IRDAI recommends reviewing this coverage gap proactively 
[IRDAI Health Insurance Circular, 2023].
```

---

## 9. Module 7: Simulation Engine

**File:** `combined_simulator.py` (cross-domain); twin-specific what-if recompute in each twin class.

### 9.1 Individual Twin What-If Simulators

Each twin supports what-if simulation by accepting a hypothetical modification to its input parameters and re-running the same processing pipeline:

| Twin | What-If Parameter Examples | Recomputation Method |
|---|---|---|
| HealthTwin | Weight change, smoking cessation, activity level increase, glucose reduction (via diet) | Re-run same ML models + formulas with modified inputs; return delta |
| FinanceTwin | +INR X savings/month, salary change, new EMI, one-time expense | Monte Carlo simulation (NumPy, N=1,000 paths); return probability distribution |
| InsuranceTwin | Increase sum insured, add Critical Illness rider, change premium | Pure arithmetic recompute (instantaneous) |

### 9.2 Cross-Domain What-If — Ranked Scenarios

For open-ended questions ("How can I reduce my cardiovascular risk?"), the system generates and ranks 3-4 candidate scenarios across all three domains:

```python
ranking_score = (risk_reduction * 0.5) + (1/monthly_cost * 0.3) + (insurance_fit_score * 0.2)
```

Scenarios are sorted by ranking score and presented as a comparison table to the user, with the LLM narration layer providing plain-language context for each option.

---

## 10. Module 8: Proactive Monitoring Agent

**File:** `monitoring_agent.py`
**Scheduler:** APScheduler (BackgroundScheduler, interval-based: weekly)
**Database:** PostgreSQL — `snapshots` table (user_id, timestamp, scores_json, raw_inputs_json)

### 10.1 Algorithm

```python
def run_monitoring_job(user_id):
    # 1. Fetch latest user data from DB
    current_data = db.get_latest_user_data(user_id)
    
    # 2. Re-compute all three twin scores
    health_score  = HealthTwin(current_data.health).compute().overall_health_score
    finance_score = FinanceTwin(current_data.finance).compute().financial_stability_score
    insurance_score = InsuranceTwin(current_data.insurance).compute().insurance_adequacy_score
    rider_gaps    = InsuranceTwin(current_data.insurance).compute().rider_gaps
    
    # 3. Fetch last snapshot
    prev = db.get_last_snapshot(user_id)
    
    # 4. Compute deltas
    alerts = []
    if prev.health_score - health_score > 10:
        alerts.append(f"Health Score dropped by {prev.health_score - health_score:.1f} points this week.")
    if finance_score_dti > 0.40 and prev_dti <= 0.40:
        alerts.append("DTI ratio crossed above 40% — debt burden is now elevated.")
    if prev.finance_score - finance_score > 15:
        alerts.append(f"Financial Stability Score dropped by {prev.finance_score - finance_score:.1f} points.")
    if new_rider_gaps := set(rider_gaps) - set(prev.rider_gaps):
        alerts.append(f"New insurance coverage gaps detected: {', '.join(new_rider_gaps)}.")
    if insurance_score < 50 and prev.insurance_score >= 50:
        alerts.append("Insurance Adequacy Score fell below 50 — review your coverage.")
    
    # 5. If any alerts triggered: generate narration and push notification
    if alerts:
        narrative = narration_layer.generate_alert_text(alerts, current_twin_profiles)
        push_to_dashboard(user_id, narrative)
        push_to_whatsapp(user_id, narrative)  # Via Twilio API
    
    # 6. Update snapshot regardless
    db.save_snapshot(user_id, health_score, finance_score, insurance_score, rider_gaps)
```

---

## 11. Module 9: Daily-Use Engagement Layer

### 11.1 WhatsApp Companion (Twilio)

- **Daily Check-In:** Bot sends a brief daily message (e.g., "How are you feeling today? Reply with your fasting glucose if you checked it.") and updates Health Twin on response.
- **Proactive Alerts:** Monitoring Agent pushes alerts directly to WhatsApp.
- **Weekly Digest:** Every Sunday, a 5-point summary of the week's twin score changes and top recommendation is sent.

### 11.2 Photo Scanning (Gemini Vision API)

- **Receipt Scanning:** User photographs a grocery or pharmacy receipt. Gemini Vision extracts line items and amounts. Finance Twin's variable expenses are auto-updated, eliminating manual entry.
- **Lab Report / Prescription Scanning:** User photographs a blood test report or doctor's prescription. Gemini Vision extracts glucose, HbA1c, cholesterol, BP values and auto-populates Health Twin inputs.

### 11.3 Gamified Twin Avatar

- A visual orb/plant icon on the dashboard reflects the user's combined score trend over the past 30 days (color-coded: green/amber/red).
- A daily check-in streak counter rewards consistent data updates.

### 11.4 Voice Input

- Web Speech API (browser-native, no cost) provides a microphone button on the chat interface.
- Voice input is transcribed and processed identically to typed text queries through the Orchestrator.

---

## 12. Backend API Design

**Framework:** FastAPI (Python)
**Database:** PostgreSQL + SQLAlchemy ORM
**Deployment:** Render / Railway (backend), Supabase (managed PostgreSQL)

### 12.1 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | /api/auth/register | User registration (name, email, password) |
| POST | /api/auth/login | JWT authentication |
| POST | /api/onboard/health | Submit initial health profile |
| POST | /api/onboard/finance | Submit initial finance profile |
| POST | /api/onboard/insurance | Submit initial insurance profile |
| GET | /api/assess/{user_id} | Re-compute and return all three twin profiles |
| POST | /api/query | Submit a natural language query to the Orchestrator |
| POST | /api/simulate | Submit a what-if scenario for cross-domain simulation |
| GET | /api/history/{user_id} | Retrieve historical twin score snapshots |
| POST | /api/scan/receipt | Upload receipt photo for auto-expense extraction |
| POST | /api/scan/report | Upload lab report photo for auto-health data extraction |

### 12.2 Database Schema

| Table | Key Columns |
|---|---|
| users | id, name, email, password_hash, created_at |
| health_profiles | id, user_id, age, gender, height, weight, bp_sys, bp_dia, glucose, cholesterol, smoking, activity, updated_at |
| finance_profiles | id, user_id, income, fixed_exp, variable_exp, savings, debt, dependents, employment_type, updated_at |
| insurance_profiles | id, user_id, sum_insured, premium, policy_type, riders, claims_12m, updated_at |
| twin_scores | id, user_id, health_score, finance_score, insurance_score, cardio_risk, diabetes_risk, dti_ratio, computed_at |
| snapshots | id, user_id, timestamp, scores_json, raw_inputs_json |
| query_log | id, user_id, query_text, orchestrator_routing, response_text, created_at |

---

## 13. Frontend Design

**Framework:** React + Vite
**Styling:** Tailwind CSS
**Charts:** Recharts (radar chart, line chart, bar chart)
**Deployment:** Vercel

### 13.1 Key Pages and Components

| Page / Component | Purpose |
|---|---|
| Onboarding Forms (3 steps) | Collect health, finance, and insurance profile data |
| Main Dashboard | Radar chart of 3 twin scores, trend line charts, top recommendation cards, notification panel |
| Chat Interface | Natural language query input with mic button (voice), response with SHAP chart and cited guidelines |
| What-If Simulator | Sliders for hypothetical input adjustments; before/after comparison chart |
| History Timeline | Line chart of Health / Finance / Insurance scores over time |
| Notifications Panel | List of proactive alerts from Monitoring Agent |
| Avatar Section | Gamified orb reflecting combined score trend + check-in streak counter |

---

## 14. Technology Stack

| Layer | Technology |
|---|---|
| Health ML Models | scikit-learn (RandomForestClassifier), pandas, NumPy |
| Explainability | SHAP (TreeSHAP) |
| Orchestrator | LangGraph (LangChain) |
| LLM / Agent | Google Gemini API (google-genai SDK) |
| RAG | LangChain + ChromaDB + sentence-transformers |
| Backend Framework | FastAPI |
| Database | PostgreSQL + SQLAlchemy |
| Scheduler | APScheduler |
| Frontend | React + Vite + Tailwind CSS + Recharts |
| Finance Simulation | NumPy (Monte Carlo) |
| WhatsApp Bot | Twilio WhatsApp API |
| Voice Input | Web Speech API (browser-native) |
| Photo Scanning | Gemini Vision API |
| Deployment | Render / Railway (backend), Vercel (frontend), Supabase (DB) |

---

## 15. Implementation Roadmap

| Week | Deliverable |
|---|---|
| Week 1 | Repository setup, download datasets (cardio_train.csv, diabetes_prediction_dataset.csv), implement all formulas in formulas.py with unit tests |
| Week 2 | Train and evaluate Cardiovascular Risk Model (RF, SHAP), train and evaluate Diabetes Risk Model (RF, SHAP), save both models |
| Week 3 | Implement HealthTwin, FinanceTwin, InsuranceTwin classes with independent test scripts |
| Week 4 | Build RAG pipeline: download guideline PDFs, chunk, embed with sentence-transformers, store in ChromaDB, test retrieval |
| Week 5 | Implement LangGraph Orchestrator: rule-based fast path + Gemini LLM fallback routing |
| Week 6 | Implement Narration Layer: structured Gemini API prompt combining scores + SHAP + RAG chunks; implement cross-domain decision tree |
| Week 7 | Implement FastAPI backend: all endpoints, PostgreSQL schema, JWT authentication |
| Week 8 | Implement APScheduler Monitoring Agent: snapshot table, threshold delta logic, WhatsApp alert integration (Twilio) |
| Weeks 9-10 | Build React frontend: onboarding forms, dashboard (radar + trend charts), chat interface, what-if simulator sliders |
| Week 11 | Implement daily-use layer: WhatsApp companion flows, receipt/lab photo scanning (Gemini Vision), gamified avatar |
| Week 12 | End-to-end integration testing, demo rehearsal, report documentation |

---

## 16. Evaluation Plan

### 16.1 ML Model Evaluation

| Model | Metric | Target |
|---|---|---|
| Cardiovascular Risk (RF) | ROC-AUC | >= 0.80 |
| Cardiovascular Risk (RF) | F1-Score | >= 0.70 |
| Diabetes Risk (RF) | ROC-AUC | >= 0.95 |
| Diabetes Risk (RF) | F1-Score | >= 0.60 (class-imbalanced) |

### 16.2 Formula Validation

All formulas in `formulas.py` are validated against published reference values from the corresponding clinical and financial standards. Unit test suite: 70+ tests across all formula functions.

### 16.3 Orchestrator Routing Evaluation

A minimum of 10 test queries per routing category (Health-only, Finance-only, Insurance-only, Cross-domain, Ambiguous) are evaluated for correct routing accuracy.

### 16.4 RAG Retrieval Quality

Precision@3 (fraction of top-3 retrieved chunks that are relevant to the query topic) is measured manually for a set of 20 test queries across the five document categories.

### 16.5 System Integration Test

The complete 6-step pipeline (Twin Computation → SHAP → Orchestrator → RAG → Narration → Simulation) is tested end-to-end for a set of 5 representative user scenarios:
1. Single-domain health query (diabetes risk assessment)
2. Single-domain finance query (affordability check)
3. Cross-domain query (treatment plan affordability)
4. What-if health simulation (lifestyle change impact)
5. Proactive monitoring alert trigger

### 16.6 Demo Validation Checklist

- [ ] Model metrics table (Accuracy / F1 / ROC-AUC) for both models
- [ ] SHAP feature-importance chart for cardiovascular model
- [ ] Architecture diagram showing all 6 pipeline stages
- [ ] RAG citation visible in a real output screenshot
- [ ] 10+ tested Orchestrator routing decisions logged
- [ ] Cross-domain decision tree trace for treatment affordability query
- [ ] Proactive alert triggered and delivered via WhatsApp
- [ ] One daily-use feature (photo scan or voice input) demonstrated end-to-end
- [ ] Disclaimers on investment and medical suggestions
- [ ] All formulas documented with their source standard

---

*Document prepared for Review 2 — TwinLife AI: Autonomous Multi-Domain Digital Twin Platform*
*Date: September 2026*
