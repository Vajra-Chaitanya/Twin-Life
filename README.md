# TwinLife AI — Autonomous Multi-Domain Digital Twin Platform

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Gemini API](https://img.shields.io/badge/LLM-Google%20Gemini-orange.svg)](https://aistudio.google.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**TwinLife AI** is an intelligent digital-twin platform that models an individual's **Health**, **Financial**, and **Insurance** profiles. It combines machine learning risk prediction models (Random Forest, SHAP explainability), deterministic clinical and financial formulas, an autonomous LLM tool-use agent, RAG-based guideline retrieval, a LangGraph orchestrator, proactive monitoring, and AI-narrated explanations to deliver a comprehensive wellness advisory system.

---

## 📌 Table of Contents

- [Quick Start](#-quick-start)
- [How to Use TwinLife AI](#-how-to-use-twinlife-ai)
- [Talking to the Advisor](#-talking-to-the-advisor)
- [Run Modes (Dev, Production, Tests)](#-run-modes-dev-production-tests)
- [Demo Script](#-demo-script)
- [Project Structure](#-project-structure)
- [Overview & Architecture](#-overview--architecture)
- [Module Breakdown](#-module-breakdown)
- [Web Platform (API + Frontend)](#-web-platform-api--frontend)
- [Command Guide (individual modules)](#-command-guide-individual-modules)
- [Autonomous Agent Workflow](#-autonomous-agent-workflow)
- [RAG Pipeline](#-rag-pipeline)
- [Orchestrator Routing](#-orchestrator-routing)
- [Health Score Calculation](#-health-score-calculation)
- [Troubleshooting](#-troubleshooting)
- [License & Disclaimer](#-license--disclaimer)

---

## 🚀 Quick Start

**You need:** Python **3.12**, Node.js **20.19+ or 22.12+** (required by Vite 8), and a free Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey). Internet is needed for the install and for advisor answers.

```powershell
# 1. Get the code: unzip the project folder (or clone it) and open a terminal inside it
git clone https://github.com/Vajra-Chaitanya/Twin-Life.git
cd Twin-Life

# 2. Backend: virtual environment + exact tested dependencies (a few minutes; downloads PyTorch)
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
#    macOS/Linux: python3.12 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt

# 3. Gemini key: copy the template and paste your key into .env
copy .env.example .env          # macOS/Linux: cp .env.example .env

# 4. Frontend dependencies (exact versions from package-lock.json)
cd frontend; npm ci; cd ..
```

Then start the two servers in two terminals:

```powershell
# Terminal 1 – API on http://127.0.0.1:8000
.\.venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2 – web app on http://127.0.0.1:5173
cd frontend; npm run dev
```

Open **http://127.0.0.1:5173**, go to **Calibrate Twin** and pick a demo persona (or enter your own data) to create the first twin. The guideline index (`data/chroma_db/`) is included; the first advisor question downloads the small MiniLM embedding model once.

> **Models:** `models/*.pkl` are included in the shared zip but not in git. After a fresh `git clone`, run `python training/train_cardio_model.py` and `python training/train_diabetes_model.py` once (about a minute each).

> Only the advisor features call Gemini, and they send the twin profile to Google. Use synthetic demo data.

---

## 🧭 How to Use TwinLife AI

### 1. Create your twin — *Calibrate Twin*
Fill the 4-step form (profile → health → money → insurance) or click a **demo persona** (Ananya, Rahul, …) to prefill it. Press **Build twin**: the three twins are computed and your first snapshot is saved. Revisiting the page loads your latest values, including anything the advisor changed.

### 2. See the whole picture — *Dashboard*
Score rings for **Health**, **Financial stability** and **Insurance adequacy**, the **cardiovascular** and **diabetes** risk gauges (Random Forest models), *Why these risks?* SHAP explanations (Heart / Diabetes tabs), cash flow, coverage and key signals. **Re-assess** recomputes from your latest data.

### 3. Go deep on one area — the three *Twin* pages
| Page | What you see | Its chat |
|---|---|---|
| **Health Twin** | Health score, conditions & habits, heart and diabetes risk with SHAP, health timeline (illnesses, injuries, readings) | Answers only health questions and records health updates |
| **Financial Twin** | Stability score, **commitments & dues** (EMIs with next due date, money you owe or lent), cash flow, subscriptions, finance timeline | Money only |
| **Insurance Twin** | Adequacy score, **all policies** (health, vehicle, life/term, home, travel, gadget) with renewal dates, life-cover gap, renewals & gaps, rider analysis | Insurance only |

Ask a twin chat about another area and it points you to the right page instead of guessing.

### 4. Ask anything — *AI Advisor*
A ChatGPT-style assistant across all three twins:
- **Conversations sidebar**: *New chat*, search, conversations grouped by *Today / Yesterday / Previous 7 days…*, hover to **rename** or **delete**. Twin pages have the same list behind their **Chats** button.
- Answers start with a verdict, show exact **before → after** numbers, cite guidelines and end with concrete actions. The agent trace (wide screens) shows routing, twins run and tool calls.
- Typos and shorthand are cleaned up first (shown as *Understood as: …* under your message).

### 5. Keep it up to date by just telling it what happened
Say what changed in plain words and the twin updates itself — a **Twin updated** card shows the before → after change, the dashboard and every page refresh, and a snapshot is saved. If a key number is missing, it asks (e.g. *"How much per month?"*) and your short reply completes the update. Plans and questions (*"If I buy…"*, *"Should I…"*) never change your data; they get a computed what-if instead. See [Talking to the Advisor](#-talking-to-the-advisor) for examples.

### 6. Undo a mistake
Reverting happens only through the advisor: type *"undo that"*, *"revert the car loan"*, *"I didn't buy the bike"*, *"undo #12"* or *"undo everything"*, or press **Undo** on an update card. The twin is recomputed and the answer confirms what changed back.

### 7. Watch your story — *Time Machine*
Scrub or play through every snapshot, compare *vs first* / *vs previous*, and browse the **Life events** timeline with Health / Finance / Insurance filters and twin badges.

### 8. Test decisions safely — *What-If Lab*
Drag sliders (weight, BP, income, EMIs…) or use presets to compare *today* with a simulated future, including Monte Carlo savings bands and purchase impact. Nothing is saved.

### 9. Stay ahead — *Alerts*
The watchdog raises alerts when scores drop or debt rises, and for **dues**: overdue repayment plans, debts with no plan for 30+ days, money lent and not returned for 30+ days, policies expired or renewing within 30 days, and vehicles without insurance. Each alert links to the right twin page; close it by telling the advisor (e.g. *"I paid back my aunt"*, *"I renewed my car insurance"*).

---

## 💬 Talking to the Advisor

| You say | What happens |
|---|---|
| *I bought a car for 8 lakh, EMI 15000 for 5 years* | EMI added, commitment tracked until the end date, debt-to-income recomputed |
| *I bought a bike for 1.2 lakh paid from savings* | Savings reduced |
| *I got a 15% hike* / *I got promoted, extra 50k every month* | Income updated |
| *I lost my job* | Asks if you have any income now |
| *My medical cost increases* → *around 6000 per month* | Asks how much, then adds it to expenses |
| *Had a surgery and paid 3 lakh* | One-time medical bill (Health + Finance) |
| *I took it from my aunt* → *I'll pay my aunt within 3 months* | Informal loan, then a monthly repayment plan with an end date |
| *I lent 50k to my friend* / *my friend returned the money* | Tracked as money owed to you, then settled |
| *I subscribed to Netflix for 649 a month* | Added to monthly expenses |
| *I had a heart attack* / *I was diagnosed with diabetes* | Added to medical history; health score, costs and rider advice adjust |
| *I had dengue for 5 days* / *I fractured my leg* | Logged on the health timeline (scores unchanged) |
| *My mother had a heart attack* | Treated as family history, not your diagnosis |
| *My BP is now 128/82*, *I lost 4 kg*, *My HbA1c is 6.1*, *I quit smoking* | Readings and habits updated |
| *I took bike insurance for 2500 a year* / *I bought a term plan of 1 crore* | Policy added with a renewal date |
| *I added a critical illness rider*, *My sum insured is now 10 lakh* | Health cover updated |
| *Can I afford a 15000 EMI?* / *What if I lose 5 kg?* | Computed what-if card (verdict + before → after), no data change |
| *What do I owe right now?* | Lists commitments and dues with dates |
| *Undo that* | Reverts the last update |

---

## ▶️ Run Modes (Dev, Production, Tests)

### Development
The two-terminal setup in [Quick Start](#-quick-start). Vite proxies `/api/*` to the backend, so no CORS setup is needed; the backend auto-reloads on code changes.

### Production (single process)
```powershell
cd frontend; npm run build; cd ..
.\.venv\Scripts\python.exe -m uvicorn serve:create_server --factory --host 0.0.0.0 --port 8000
```

`serve.py` serves the built app and mounts the API at `/api` (same paths as dev), gzips responses,
caches hashed assets for a year and always revalidates `index.html`, so refreshes on any route work
and new deployments show up immediately. Use `npm run preview` (port 4173) to check a build against the dev API.

Data is stored in SQLite at `data/twinlife.sqlite3`; set `DATABASE_URL` to use PostgreSQL.

### Tests
```powershell
# Offline suite (no network) – unit, API and 390-case behaviour bank in tests/
.\.venv\Scripts\python.exe -m pytest -q

# Advisor behaviour report: accuracy per domain + every failure
.\.venv\Scripts\python.exe -m evaluation.eval_scenarios

# Frontend type-check + production build
cd frontend; npm run build
```

`scripts/manual/test_api.py` and `scripts/manual/test_combined_simulator.py` are manual scripts that call the live Gemini API.

---

## 🎬 Demo Script

1. Open `http://127.0.0.1:5173`, switch **Motion: full**. The landing page shows **Twin: <name>** with the three scores under the hologram.
2. Press **Ctrl+K → Prepare demo data** (calibrates synthetic personas; watchdog alerts appear).
3. **Ctrl+K → Start guided demo tour**, or walk through manually:
   - **Dashboard**: heart and diabetes gauges; switch the SHAP tabs to explain the top risk drivers.
   - **AI Advisor**: *"I bought a car for 8 lakh, EMI 15000 for 5 years"* → Twin updated card; then *"I had a heart attack"*; then *"I'm planning to buy a bike on EMI of 4000, should I?"* (it remembers both); finally *"undo the car loan"*.
   - **Financial Twin**: the car EMI under *Commitments & dues* with its next due date.
   - **Insurance Twin**: *"I took bike insurance for 2500 a year"* in its chat; note the *No insurance recorded for your car* alert.
   - **Health Twin**: ask *"can I afford a 20000 EMI?"* to show it stays on health.
   - **What-If Lab**: **Job loss**, then **Clear all EMIs**; watch the fan chart move.
   - **Time Machine**: filter Life events by twin, press ▶ on the trajectory.
   - **Alerts**: dues and watchdog alerts with links to the twin pages.

---

## 🗂️ Project Structure

```
Project/
├── api.py                  # FastAPI backend (dev: uvicorn api:app)
├── serve.py                # Production server: built frontend + API under /api
├── formulas.py             # Module 1: pure health/finance/insurance formulas
├── health_twin.py  finance_twin.py  insurance_twin.py   # Module 3: the three twins
├── combined_simulator.py   # Module 4: Gemini tool-calling treatment agent
├── rag_agent.py            # Module 5: ChromaDB guideline retrieval
├── orchestrator.py         # Module 6: LangGraph routing
├── narration_agent.py      # Module 7: Gemini narration
├── monitoring_agent.py     # Module 8: watchdog alerts
├── recommendation_engines.py  # Module 9
├── event_engine.py  scenario_engine.py  query_refiner.py  # advisor intelligence
├── requirements.txt  pytest.ini  .env (your Gemini key, not committed)
│
├── frontend/               # React + Vite web app (src/pages, src/components, public/models)
├── data/                   # datasets, guideline texts, ChromaDB index, SQLite database
├── models/                 # trained cardio and diabetes models (.pkl)
├── training/               # scripts that train the models
├── tests/                  # pytest suite (run: python -m pytest -q)
├── evaluation/             # advisor behaviour bank (350 + 57 held-out cases)
├── scripts/manual/         # scripts that call the live Gemini API
└── docs/
    ├── PROJECT_SPEC.md  instruction.txt  TWIN-LIFE AI_Project Documentation.docx
    ├── design/             # original design notes (00–07)
    ├── research/           # notes/ and papers/ (base research PDFs)
    ├── review-2/           # literature survey, research gap, methodology
    ├── prompts/            # implementation prompts
    ├── dev-chat/           # development chat log
    └── archive/            # zipped copy of the design notes
```

The Python app modules stay in the project root because the servers and every import (`uvicorn api:app`, `serve.py`) load them from there.

---

## 🏗️ Overview & Architecture

TwinLife AI operates on a modular pipeline where deterministic mathematical formulas and trained ML models power higher-level "Digital Twins". An autonomous AI agent interacts with these twin interfaces via function calling, while a LangGraph orchestrator routes queries and a narration layer provides human-friendly explanations grounded in retrieved medical/financial guidelines.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      MODULE 6: ORCHESTRATOR (LangGraph)                 │
│         Routes queries → Twins → RAG → Simulation → Narration          │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
     ┌───────────────────────────────┼───────────────────────────────┐
     ▼                               ▼                               ▼
┌─────────────┐   ┌──────────────────────────────────┐   ┌─────────────┐
│  MODULE 7   │   │      MODULE 4: COMBINED           │   │  MODULE 5   │
│  Narration  │   │      SIMULATOR (Gemini Agent)      │   │  RAG Agent  │
│  Agent      │   └────────────────┬─────────────────┘   │  (ChromaDB) │
└─────────────┘                    │ (4 Deterministic     └─────────────┘
                                   │  Tool Calls)
     ┌─────────────────────────────┼─────────────────────────────┐
     ▼                             ▼                             ▼
┌───────────────────┐   ┌───────────────────┐   ┌───────────────────┐
│    MODULE 3A      │   │    MODULE 3B      │   │    MODULE 3C      │
│    HealthTwin     │   │    FinanceTwin    │   │   InsuranceTwin   │
└────────┬──────────┘   └────────┬──────────┘   └────────┬──────────┘
    ┌────┴────┐                  │                       │
    ▼         ▼                  │                       │
┌────────┐┌────────┐             │                       │
│MODULE 2││MODULE 2│             │                       │
│Cardio  ││Diabetes│             │                       │
│Model   ││Model   │             │                       │
└───┬────┘└───┬────┘             │                       │
    └─────────┴──────────┬───────┴───────────────────────┘
                         ▼
            ┌─────────────────────────┐
            │        MODULE 1         │     ┌────────────────────┐
            │ Pure Domain Formulas    │     │ MODULE 8: Monitor  │
            │ (formulas.py)           │     │ (APScheduler)      │
            └─────────────────────────┘     └────────────────────┘
                                            ┌────────────────────┐
                                            │ MODULE 9: Engines  │
                                            │ (Recommendations)  │
                                            └────────────────────┘
```

---

## 📦 Module Breakdown

### Module 1: Domain Formulas (`formulas.py`)
- **Pure, deterministic functions** with 0 external side-effects or I/O.
- **Health**: Body Mass Index (BMI), WHO Obesity Staging, Blood Pressure Staging (AHA/ACC 2017), Framingham 10-Year Cardiovascular Disease Risk, Blood Glucose Diabetes Indicator.
- **Finance**: Debt-to-Income (DTI) Ratio, Savings Rate, Emergency Fund Coverage (Months), Financial Stability Score (0-100), Treatment Affordability Score.
- **Insurance**: Coverage Adequacy Ratio, Premium Affordability Ratio, Composite Insurance Adequacy Score (0-100).
- **Unit Tests**: Full test suite in `tests/test_formulas.py` (70 unit tests passing).

### Module 2: Health ML Models (`training/`)
- **Cardiovascular Disease Classifier**:
  - Dataset: `data/cardio_train.csv` (70,000 rows).
  - Preprocessing: Age converted from days to years (`age // 365`), BMI derived, physiological filtering (`ap_lo <= ap_hi`).
  - Model: `RandomForestClassifier(n_estimators=200, max_depth=10, min_samples_leaf=20)`.
  - Metrics: **Accuracy: 73.6% | F1-Score: 72.0% | ROC-AUC: 80.3%**. Saved to `models/cardio_model.pkl`.
- **Diabetes Classifier** (`training/train_diabetes_model.py`): Random Forest on `data/diabetes_prediction_dataset.csv` (100,000 rows, balanced class weights), saved to `models/diabetes_model.pkl`. HbA1c is estimated from fasting glucose when the user hasn't given a lab value, and is labelled as estimated.
- A deterministic glucose-threshold indicator is still reported alongside the model.

### Module 3: Digital Twin Classes (`health_twin.py`, `finance_twin.py`, `insurance_twin.py`)
- **`HealthTwin`**: Integrates the CVD and diabetes model predictions, SHAP feature importance, recorded conditions and Module 1 formulas into a unified health profile and a 0-100 composite health score.
- **`FinanceTwin`**: Evaluates financial stability, debt obligations, emergency funds, and computes 12-month treatment affordability (`affordability_for(cost)`).
- **`InsuranceTwin`**: Estimates 5-year condition-specific medical costs, checks sum insured limits, performs rider gap analysis, and summarises the full policy portfolio (vehicle, life, home, travel…) including the life-cover gap.

### Advisor intelligence (`event_engine.py`, `scenario_engine.py`, `query_refiner.py`)
- **`query_refiner`**: First Gemini call per message; fixes typos and shorthand, guarded so amounts, negations and intent can never change.
- **`event_engine`**: Turns facts in chat into versioned twin updates (loans, purchases, income, expenses, borrowing/lending, subscriptions, conditions, episodes, readings, habits, policies), asks for missing numbers, handles reverts, and computes **dues** (instalments, debts, receivables, renewals, missing vehicle insurance).
- **`scenario_engine`**: Exact before → after numbers for what-if questions (EMI, purchase, income, expense, health, insurance cover).
- **Behaviour bank** (`evaluation/eval_scenarios.py`, `evaluation/eval_heldout.py`): 390 everyday messages with expected routing, updates and calculations, run as tests.

### Module 4: Autonomous Combined Simulator (`combined_simulator.py`)
- **Agent Architecture**: Autonomous function-calling agent using the Google Gemini API (`google-genai` SDK).
- **Deterministic Tools Registered**:
  1. `check_affordability(cost)`: Evaluates user's financial capacity over 12 months.
  2. `check_insurance_coverage(cost)`: Computes covered amount and out-of-pocket gap.
  3. `get_cheaper_alternative(condition, current_cost)`: Looks up next lower-cost medical tier.
  4. `get_health_context(condition)`: Retrieves clinical risk level and urgency.
- **Explainability**: Every tool execution is recorded in an ordered `tool_trace` for full transparency.

### Module 5: RAG Pipeline (`rag_agent.py`)
- **Document Indexing**: Chunks 5 guideline documents (cardiovascular, diabetes, financial planning, insurance, general wellness) using LangChain's `RecursiveCharacterTextSplitter` (~2000 chars/chunk, 200 overlap).
- **Embedding Model**: `sentence-transformers/all-MiniLM-L6-v2` (runs locally, no API key needed).
- **Vector Store**: ChromaDB with persistent local storage (`data/chroma_db/`).
- **Retrieval**: `retrieve(topic, top_k=3)` returns the most semantically relevant guideline chunks for any query.
- **Guideline Sources**: AHA/ACC cardiovascular guidelines, ADA diabetes standards, RBI/SEBI financial planning, IRDAI insurance guidelines, WHO/ICMR wellness guidelines.

### Module 6: Orchestrator (`orchestrator.py`, LangGraph)
- **Two-Step Routing**:
  - **Step 1 (Deterministic)**: Keyword matching against domain-specific terms (e.g., "diabetes" → health, "EMI" → finance, "premium" → insurance, "treatment cost" → all three + simulate).
  - **Step 2 (LLM Fallback)**: For ambiguous queries, calls Gemini API to classify into `{twins, mode, simulate}`.
- **LangGraph State Graph**: Conditional edges route through health → finance → insurance → RAG → simulate → narrate → END based on routing decisions.
- **Full Pipeline**: Processes a natural language query end-to-end through twin assessments, RAG retrieval, optional simulation, and narrated explanation.

### Module 7: Narration Layer (`narration_agent.py`)
- **`generate_explanation(twin_outputs, shap_features, rag_chunks)`**: Calls Gemini API to produce a warm, plain-language explanation combining computed scores, SHAP-driven factor analysis, and cited RAG guideline references.
- **`generate_ranked_whatifs(scenarios)`**: Ranks candidate what-if scenarios using `score = risk_reduction×0.5 + (1/cost)×0.3 + insurance_fit×0.2` and narrates trade-offs.
- **Rules**: No invented numbers, natural source citations, disclaimers included, under 300 words.

### Module 8: Monitoring Agent (`monitoring_agent.py`, APScheduler)
- **Scheduled Checks**: Weekly (configurable) profile recomputation using APScheduler's `BackgroundScheduler`.
- **Threshold Alerts**:
  - Health score drop > 10 points
  - DTI ratio rise above 0.40
  - Savings rate fall below 10%
  - Insurance score drop > 15 points
  - New insurance rider gaps detected
- **Persistence**: File-based snapshots (`data/snapshots/`) and notification logs (`data/notifications/`).

### Module 9: Recommendation Engines (`recommendation_engines.py`)
- **`investment_recommendation(finance_profile, age)`**: Rule-based tier logic — emergency fund first → growth allocation → balanced → conservative → no new investment.
- **`purchase_impact_simulator(finance_profile, purchase_cost)`**: Analyzes DTI impact, months to save, emergency fund depletion. Generates ranked alternatives: defer, cheaper tier, EMI split (24 months), expense reallocation.
- **`lifestyle_impact_simulator(health_profile, habit_changes)`**: Projects health score changes from lifestyle modifications (quit smoking, weight loss, exercise, diet). Generates substitute/moderate/offset alternatives for worsening habits.

---

## 🌐 Web Platform (API + Frontend)

### Module 10: FastAPI Backend (`api.py`)
SQLAlchemy persistence (SQLite by default at `data/twinlife.sqlite3`; set `DATABASE_URL` for PostgreSQL).

| Endpoint | Purpose |
|---|---|
| `GET /health` | Liveness check |
| `POST /onboard` | Validate and store versioned health/finance/insurance inputs |
| `GET /inputs` | Latest stored inputs for a user |
| `POST /assess` | Run all three twins, save a snapshot, raise watchdog alerts vs. the previous snapshot |
| `GET /history` | Snapshots, newest first |
| `POST /simulate` | Before/after twins for overrides + 12-month Monte Carlo savings bands (not persisted) |
| `POST /whatif` | Purchase impact and ranked alternatives |
| `POST /query` | Refine → detect life events/reverts → LangGraph orchestrator → RAG citations → Gemini narration; optional `domain` scopes it to one twin; saved to chat history |
| `GET /chat-history` | Conversations (threads) and messages; `domain` filter for twin chats |
| `PATCH /chat-threads/{id}`, `DELETE /chat-threads/{id}` | Rename or delete a conversation |
| `GET /events` | Life-event timeline with twin labels, per-twin counts and active commitments |
| `GET /dues` | Payment and renewal schedule with status (overdue, expired, missing, outstanding, due soon) |
| `GET /notifications`, `POST /notifications/read` | Watchdog and dues alerts, read state |

Raw AI errors are mapped to user-safe messages. Interactive docs: `http://127.0.0.1:8000/docs`.

### Module 11: React Frontend (`frontend/`)
React 19 + Vite + TypeScript + Tailwind v4 + Framer Motion + React Three Fiber, in a dark black-and-gold theme.

| Page | Highlights |
|---|---|
| Landing | Low-poly faceted head hologram (simplified from a real head scan by `frontend/scripts/lowpoly-face.mjs`) that assembles from a flickering web, with **Twin: name** and the three scores beneath (2D fallback without WebGL) |
| Calibrate Twin | 4-step wizard, demo personas, loads your latest saved values, live formula readout, "building your twin" sequence |
| Dashboard | Score rings, CVD and diabetes gauges, SHAP charts (Heart / Diabetes), cash-flow, coverage and rider gaps, key signals |
| Health / Financial / Insurance Twin | Everything for one domain plus a chat scoped to that domain, dues and a domain timeline |
| What-If Lab | Parallel timelines (today vs. simulated), presets, Monte Carlo fan chart, purchase impact |
| Time Machine | Animated trend chart, scrubber/playback, metric deltas, life-events timeline with twin filters |
| AI Advisor | ChatGPT-style conversation sidebar, twin-update and what-if cards, citations, agent trace, voice input |
| Alerts | Watchdog and dues timeline, unread badge, toasts |

Global: **Ctrl+K** command palette, guided demo tour, motion toggle (respects reduced-motion by default), per-page code splitting, responsive from 360 px phones to wide desktops.

**Asset credit:** `frontend/public/models/LeePerrySmith.glb` is the *Infinite, 3D Head Scan* by Lee Perry-Smith, licensed under [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/), obtained from the three.js examples repository (license file alongside the model).

---

## 🧰 Command Guide (individual modules)

Run from the project root with the virtual environment's Python (`.\.venv\Scripts\python.exe`).

### Retrain the ML models (optional; trained models are included)
```bash
python training/train_cardio_model.py      # models/cardio_model.pkl
python training/train_diabetes_model.py    # models/diabetes_model.pkl + diabetes_feature_cols.pkl
```

### Run Module 1 Unit Tests
```bash
python -m pytest tests/test_formulas.py
```

### Evaluate Digital Twins (Module 3)
```bash
python health_twin.py
python finance_twin.py
python insurance_twin.py
```

### Run Autonomous Treatment Advisor (Module 4)
```bash
python scripts/manual/test_combined_simulator.py
```

### Build & Query RAG Pipeline (Module 5)
```bash
python rag_agent.py
```

### Test Orchestrator Routing (Module 6)
```bash
python orchestrator.py
```

### Generate AI Narrations (Module 7)
```bash
python narration_agent.py
```

### Run Monitoring Agent Check (Module 8)
```bash
python monitoring_agent.py
```

### Test Recommendation Engines (Module 9)
```bash
python recommendation_engines.py
```

---

## 🤖 Autonomous Agent Workflow

When evaluating a treatment plan cost (e.g. ₹5,00,000), the Gemini agent reasons step-by-step without hardcoded rules:

```
[Agent Initiated] → Prompt: Evaluate ₹5,00,000 Cardio Treatment Plan

  ├── Call Tool 1: get_health_context("cardio") → { risk_level: "High", urgency: "Urgent" }
  ├── Call Tool 2: check_affordability(500000) → { affordable: false, score: 0.45 }
  ├── Call Tool 3: check_insurance_coverage(500000) → { covered_amount: 300000, gap: 200000 }
  ├── Call Tool 4: get_cheaper_alternative("cardio", 500000) → { new_cost: 200000, tier: "Moderate" }
  └── Call Tool 5: check_insurance_coverage(200000) → { covered_amount: 200000, gap: 0 }

[Agent Synthesis] → Generates detailed recommendation explaining optimal insurance & self-funding path.
```

---

## 📚 RAG Pipeline

The RAG system indexes 5 authoritative guideline documents into ChromaDB:

| Document | Source | Topics Covered |
|----------|--------|---------------|
| `cardiovascular_guidelines.txt` | AHA/ACC 2019 | BP staging, cholesterol, Framingham risk, lifestyle |
| `diabetes_management_guidelines.txt` | ADA 2024 | Glucose classification, HbA1c targets, pharmacology |
| `financial_planning_guidelines.txt` | RBI/SEBI | DTI management, savings benchmarks, investment allocation |
| `insurance_planning_guidelines.txt` | IRDAI | Sum insured adequacy, premium ratios, rider analysis |
| `general_wellness_guidelines.txt` | WHO/ICMR | BMI, physical activity, nutrition, sleep, screening |

Each query retrieves the top-3 most semantically relevant chunks using cosine similarity over `all-MiniLM-L6-v2` embeddings.

---

## 🔀 Orchestrator Routing

The LangGraph orchestrator uses two-step routing:

| Query Example | Routed To | Mode |
|--------------|-----------|------|
| "What is my blood pressure?" | Health | Single-domain |
| "Am I saving enough?" | Finance | Single-domain |
| "How much is my coverage?" | Insurance | Single-domain |
| "Can I afford ₹5L surgery?" | Health + Finance + Insurance | Cross-domain + Simulate |
| "Treatment for diabetes Rs.3L" | Health + Finance + Insurance | Cross-domain + Simulate |

---

## 🧮 Health Score Calculation

The `overall_health_score` (0-100) in `HealthTwin` is calculated using a 5-component weighted model:

$$\text{Overall Score} = 0.25(\text{BMI Score}) + 0.25(\text{BP Score}) + 0.25(\text{Cardio Score}) + 0.15(\text{Diabetes Score}) + 0.10(\text{Framingham Score})$$

Recorded diagnoses (e.g. heart attack, stroke, diabetes) then subtract a documented penalty, capped at 35 points.

---

## 🛠️ Troubleshooting

| Symptom | Fix |
|---|---|
| Header shows **Engine offline** | The API isn't running. Start Terminal 1 (`uvicorn api:app …`). |
| Advisor says *Gemini API key is not configured* | Add `GEMINI_API_KEY=…` to `.env` in the project root and restart the API. |
| *Gemini rate limit reached* | Free-tier quota; wait a minute and ask again. |
| Pages say *Calibrate a twin first* | No twin is selected in this browser. Use **Calibrate Twin** or a demo persona. |
| Diabetes panel shows **Re-assess now** | The snapshot predates the diabetes model; click it once. |
| Something was recorded wrongly | Tell the advisor *"undo that"* (or *"undo #id"* from the Time Machine timeline). |
| Hologram missing / static | WebGL is unavailable or reduced motion is on; switch **Motion: full** in the header. |
| Port already in use | Stop the old server or change `--port` (API) / `--port` in `npm run dev -- --port 5174`. |

---

## 📜 License & Disclaimer

This software is developed for academic and demonstration purposes only. All financial figures, insurance coverage rules, and health estimates do not constitute licensed medical or financial advice.

Distributed under the MIT License. See `LICENSE` for more information.
