# TwinLife AI

> An intelligent digital-twin platform that models your **Health**, **Financial**, and **Insurance** profiles — powered by ML models, an autonomous AI agent, and a beautiful React dashboard.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Gemini API](https://img.shields.io/badge/LLM-Google%20Gemini-orange.svg)](https://aistudio.google.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## What is TwinLife AI?

TwinLife AI creates a **digital twin** of you — a living model that tracks your health, finances, and insurance in one place. Ask it questions in plain English, tell it what changed in your life, and it updates everything automatically.

**Key things it does:**

- 🏥 **Health Twin** — BMI, blood pressure staging, cardiovascular & diabetes risk prediction (Random Forest + SHAP explanations)
- 💰 **Financial Twin** — Debt-to-income ratio, savings rate, emergency fund coverage, financial stability scoring
- 🛡️ **Insurance Twin** — Coverage adequacy, premium affordability, rider gap analysis, policy portfolio tracking
- 🤖 **AI Advisor** — Chat with your twin in natural language. Say *"I bought a car for 8 lakh, EMI 15000"* and it updates your financial profile automatically
- 🔮 **What-If Lab** — Test decisions safely with simulations before committing
- ⏳ **Time Machine** — Scrub through every snapshot of your twin's history
- 🔔 **Smart Alerts** — Automatic warnings when scores drop, debts are overdue, or policies expire

---

## Tech Stack

### Backend

| Technology | Purpose |
|---|---|
| **Python 3.12** | Core language |
| **FastAPI** + **Uvicorn** | REST API server |
| **SQLAlchemy** + **SQLite** | Database (PostgreSQL optional) |
| **scikit-learn** | Random Forest models for CVD & diabetes risk |
| **SHAP** | ML model explainability |
| **Google Gemini API** | LLM for natural language understanding & narration |
| **LangChain** + **LangGraph** | Orchestrator routing & RAG pipeline |
| **ChromaDB** | Vector store for guideline retrieval |
| **sentence-transformers** | Local MiniLM embeddings for semantic search |
| **APScheduler** | Background monitoring & alerts |

### Frontend

| Technology | Purpose |
|---|---|
| **React 19** + **TypeScript** | UI framework |
| **Vite** | Build tool & dev server |
| **Tailwind CSS v4** | Styling (dark black-and-gold theme) |
| **Framer Motion** | Animations & transitions |
| **React Three Fiber** + **Three.js** | 3D hologram on landing page |
| **TanStack React Query** | Server state management |
| **Recharts** | Charts & data visualization |
| **Lucide React** | Icon library |

---

## Architecture

```
                        ┌──────────────────────────┐
                        │     React Frontend       │
                        │  (Vite + Tailwind + 3D)  │
                        └────────────┬─────────────┘
                                     │ HTTP
                        ┌────────────▼─────────────┐
                        │     FastAPI Backend       │
                        │      (api.py)             │
                        └────────────┬─────────────┘
                                     │
              ┌──────────────────────┼──────────────────────┐
              │                      │                      │
    ┌─────────▼──────────┐ ┌────────▼─────────┐ ┌─────────▼──────────┐
    │   Query Refiner    │ │  Event Engine    │ │  Scenario Engine   │
    │ (typo fix, intent) │ │ (life updates)   │ │ (what-if analysis) │
    └─────────┬──────────┘ └────────┬─────────┘ └─────────┬──────────┘
              │                     │                      │
              └──────────┬──────────┘──────────────────────┘
                         │
              ┌──────────▼──────────┐
              │    Orchestrator     │
              │    (LangGraph)      │
              │  Routes to twins,   │
              │  RAG, simulation    │
              └──────────┬──────────┘
                         │
       ┌─────────────────┼─────────────────┐
       │                 │                 │
┌──────▼──────┐  ┌───────▼──────┐  ┌──────▼───────┐
│ Health Twin │  │ Finance Twin │  │Insurance Twin│
│ (CVD model, │  │ (DTI, savings│  │ (coverage,   │
│  diabetes)  │  │  stability)  │  │  riders)     │
└──────┬──────┘  └───────┬──────┘  └──────┬───────┘
       │                 │                 │
       └────────┬────────┘─────────────────┘
                │
       ┌────────▼────────┐     ┌──────────────┐
       │  Domain Formulas│     │  RAG Agent   │
       │  (formulas.py)  │     │  (ChromaDB)  │
       └─────────────────┘     └──────┬───────┘
                                      │
       ┌──────────────────┐    ┌──────▼───────┐
       │ Monitoring Agent │    │  Narration   │
       │  (alerts)        │    │  (Gemini)    │
       └──────────────────┘    └──────────────┘
```

**How a query flows:**

1. You type a message → **Query Refiner** fixes typos
2. **Event Engine** checks if it's a life update (bought something, got a diagnosis)
3. **Orchestrator** routes to the right twins
4. **Twins** compute scores using **Domain Formulas** and **ML Models**
5. **RAG Agent** pulls relevant medical/financial guidelines
6. **Narration Agent** generates a human-friendly explanation
7. Response is sent back with before→after changes, citations, and actionable advice

---

## Project Structure

```
TwinLife-AI/
│
├── api.py                    # FastAPI backend — all REST endpoints
├── serve.py                  # Production server (frontend + API)
├── formulas.py               # Pure math: BMI, DTI, Framingham risk, etc.
├── health_twin.py            # Health scoring + ML model integration
├── finance_twin.py           # Financial stability assessment
├── insurance_twin.py         # Coverage adequacy & rider analysis
├── combined_simulator.py     # Gemini tool-calling agent
├── rag_agent.py              # ChromaDB guideline retrieval
├── orchestrator.py           # LangGraph query routing
├── narration_agent.py        # AI-generated explanations
├── monitoring_agent.py       # Watchdog alerts (APScheduler)
├── event_engine.py           # Life event detection & twin updates
├── scenario_engine.py        # What-if calculations
├── query_refiner.py          # Typo/shorthand cleanup
├── recommendation_engines.py # Investment & lifestyle recommendations
│
├── frontend/                 # React + Vite web app
│   └── src/
│       ├── pages/            # Landing, Dashboard, Advisor, Twins, etc.
│       ├── components/       # Reusable UI components
│       └── lib/              # API client, utilities, types
│
├── data/                     # Datasets, guideline texts, ChromaDB index
├── models/                   # Trained ML models (.pkl files)
├── training/                 # Model training scripts
├── tests/                    # pytest test suite
├── evaluation/               # Advisor behaviour bank (390 test cases)
│
├── requirements.txt          # Python dependencies (loose)
├── requirements-lock.txt     # Python dependencies (exact versions)
├── .env.example              # Template for API key config
└── .env                      # Your Gemini API key (not committed)
```

---

## Getting Started

### Prerequisites

- **Python 3.12+**
- **Node.js 20.19+** or **22.12+**
- **Gemini API key** (free) from [Google AI Studio](https://aistudio.google.com/apikey)

### 1. Clone & install

```powershell
git clone https://github.com/Vajra-Chaitanya/Twin-Life.git
cd Twin-Life

# Backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt

# Frontend
cd frontend
npm ci
cd ..
```

### 2. Configure API key

```powershell
copy .env.example .env
```

Open `.env` and paste your Gemini API key:

```
GEMINI_API_KEY=your_actual_key_here
```

### 3. Train ML models (if not included)

```powershell
.\.venv\Scripts\python.exe training/train_cardio_model.py
.\.venv\Scripts\python.exe training/train_diabetes_model.py
```

### 4. Run the app

Open **two terminals**:

**Terminal 1 — Backend (port 8000):**
```powershell
.\.venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8000 --reload
```

**Terminal 2 — Frontend (port 5173):**
```powershell
cd frontend
npm run dev
```

### 5. Open in browser

Go to **http://127.0.0.1:5173** → Click **Calibrate Twin** → Pick a demo persona or enter your data.

---

## API Endpoints

| Method | Endpoint | What it does |
|---|---|---|
| `GET` | `/health` | Server liveness check |
| `POST` | `/onboard` | Save user health/finance/insurance inputs |
| `GET` | `/inputs` | Get latest stored inputs |
| `POST` | `/assess` | Run all three twins, save snapshot |
| `POST` | `/query` | Ask the AI advisor a question |
| `POST` | `/simulate` | Run what-if simulation |
| `POST` | `/whatif` | Purchase impact analysis |
| `GET` | `/history` | Get all snapshots |
| `GET` | `/events` | Life events timeline |
| `GET` | `/dues` | Payment & renewal schedule |
| `GET` | `/chat-history` | Conversation history |
| `GET` | `/notifications` | Alerts & warnings |

Interactive docs available at: **http://127.0.0.1:8000/docs**

---

## ML Models

### Cardiovascular Disease Classifier
- **Algorithm:** Random Forest (200 trees, max depth 10)
- **Dataset:** 70,000 patient records (`data/cardio_train.csv`)
- **Metrics:** Accuracy 73.6% · F1 72.0% · ROC-AUC 80.3%
- **Explainability:** SHAP feature importance

### Diabetes Classifier
- **Algorithm:** Random Forest (balanced class weights)
- **Dataset:** 100,000 records (`data/diabetes_prediction_dataset.csv`)
- **Explainability:** SHAP feature importance
- HbA1c is estimated from fasting glucose when no lab value is provided

---

## RAG Pipeline

The system indexes 5 authoritative guideline documents for retrieval-augmented generation:

| Document | Source |
|---|---|
| Cardiovascular guidelines | AHA/ACC 2019 |
| Diabetes management | ADA 2024 |
| Financial planning | RBI/SEBI |
| Insurance planning | IRDAI |
| General wellness | WHO/ICMR |

Uses **ChromaDB** + **all-MiniLM-L6-v2** embeddings for semantic search. Top-3 chunks are retrieved per query.

---

## Running Tests

```powershell
# Full offline test suite (no API key needed)
.\.venv\Scripts\python.exe -m pytest -q

# Advisor behaviour evaluation (needs Gemini key)
.\.venv\Scripts\python.exe -m evaluation.eval_scenarios

# Frontend type-check + build
cd frontend
npm run build
```

---

## Production Deployment

Build the frontend and serve everything from one process:

```powershell
cd frontend && npm run build && cd ..
.\.venv\Scripts\python.exe -m uvicorn serve:create_server --factory --host 0.0.0.0 --port 8000
```

---

## Troubleshooting

| Problem | Solution |
|---|---|
| **Engine offline** in header | Start the backend: `uvicorn api:app --host 127.0.0.1 --port 8000` |
| **Gemini API key not configured** | Add `GEMINI_API_KEY=...` to `.env` and restart the backend |
| **Rate limit reached** | Free-tier quota — wait a minute and try again |
| **Calibrate a twin first** | Use Calibrate Twin page or pick a demo persona |
| **Port already in use** | Stop the old server or change `--port` |
| **Hologram missing** | WebGL unavailable or reduced motion on — toggle **Motion: full** in header |

---

## License

MIT License — developed for academic and demonstration purposes.

> ⚠️ **Disclaimer:** Health estimates, financial figures, and insurance coverage rules are for demonstration only and do not constitute licensed medical, financial, or insurance advice.
