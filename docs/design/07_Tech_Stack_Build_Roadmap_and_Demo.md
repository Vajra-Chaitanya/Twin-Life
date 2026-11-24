# 7. Tech Stack, Build Roadmap, and Demo

## Final Tech Stack
| Layer | Tool |
|---|---|
| Health model | scikit-learn (Random Forest), pandas |
| Explainability | SHAP |
| Orchestrator | LangGraph |
| LLM | Claude API |
| RAG | LangChain + ChromaDB + sentence-transformers |
| Backend | FastAPI + PostgreSQL + SQLAlchemy |
| Scheduler (proactive agent) | APScheduler |
| Frontend | React + Vite + Tailwind + Recharts |
| Simulation | NumPy (Monte Carlo) |
| WhatsApp bot | Twilio WhatsApp API (free sandbox) |
| Voice input | Web Speech API (browser-native, free) |
| Receipt/prescription scanning | Claude API vision (send image directly) |
| Deployment | Render/Railway (backend), Vercel (frontend), Supabase (DB) |

## Week-by-Week Build Plan

**Week 1 — Foundations:** repo setup, download `cardio_train.csv`, write `formulas.py` (BMI, Framingham, BP staging, DTI, savings rate, coverage adequacy) with unit tests.

**Week 2 — The One Model:** clean the dataset, derive BMI, train Random Forest (see Doc 4), evaluate (accuracy/F1/ROC-AUC), run SHAP, save model.

**Week 3 — Twin Classes:** `health_twin.py`, `finance_twin.py`, `insurance_twin.py`, and `combined_simulator.py` (Doc 5's decision tree) — each independently testable.

**Week 4 — RAG Pipeline:** download 3-5 guideline PDFs, chunk, embed (`sentence-transformers`), store in ChromaDB, write `rag_agent.py`.

**Week 5 — Orchestrator (LangGraph):** rule-based fast-path router + LLM fallback classifier (Doc 5, Part C) wired to the twins.

**Week 6 — Narration Layer:** final Claude prompt combining model/formula output + SHAP + RAG chunks (Doc 2) into a cited explanation; ranked what-if generator (Doc 5, Part D).

**Week 7 — Backend API:** FastAPI endpoints (`/onboard`, `/assess`, `/query`, `/simulate`, `/whatif`, `/history`), PostgreSQL schema.

**Week 8 — Proactive Monitoring Agent:** APScheduler job + snapshot table + threshold-diff logic (Doc 6, Part A).

**Weeks 9-10 — Frontend:** onboarding forms, dashboard (radar chart, forecast chart, recommendation cards, notifications), chat interface, what-if sliders.

**Week 11 — Daily-Use Layer:** see below.

**Week 12 — Testing, polish, documentation, rehearse demo.**

## The Daily-Use / Interactive Layer
Priority order if time-constrained:
1. **WhatsApp companion** (Twilio) — daily check-ins, weekly digests, proactive alerts pushed here instead of a dashboard nobody opens.
2. **Photo scanning** (Claude vision) — scan a receipt → auto-populate Finance Twin expenses; scan a prescription/lab report → auto-populate Health Twin inputs. Kills manual data entry, strong live-demo moment.
3. **Gamified Twin Avatar** — a simple visual (color-shifting orb/plant icon) that reflects combined score trend over time, plus a check-in streak counter.
4. **Voice input** (Web Speech API) — mic button on the chat interface, free, browser-native.
5. **Weekly AI digest** — reuses the Monitoring Agent + Narration Agent, delivered via WhatsApp/email.
6. *(Stretch)* Wearable hook — Google Fit/Apple Health step count as a bonus Health Twin input.

## Demo Script (rehearse this exact sequence)
1. Onboarding (or pre-loaded sample user)
2. Single-domain query — "What's my diabetes risk?" → only Health Twin fires
3. Cross-domain query — "Should I go ahead with this ₹80,000 treatment?" → full decision tree runs live
4. What-if simulation — adjust a slider → before/after chart
5. Proactive alert — trigger the Monitoring Agent manually → notification appears unprompted
6. Daily-use layer — WhatsApp digest arrives, or scan a receipt photo live

## Submission Checklist
- [ ] Model metrics table (accuracy/F1/ROC-AUC)
- [ ] SHAP feature-importance chart
- [ ] Architecture diagram (Doc 2)
- [ ] RAG citation shown in a real output (screenshot)
- [ ] 10+ tested Orchestrator routing queries (screenshot)
- [ ] Proactive alert demo tested multiple times before demo day
- [ ] One daily-use feature working end-to-end
- [ ] Disclaimers on investment/medical suggestions
- [ ] All formulas documented with their source standard

---
*This is the last document in the set. Together, Docs 1-7 cover everything discussed: the concept (1), the architecture and what each AI term means (2), the data (3), the model (4), the simulation/routing logic (5), the proactive/recommendation engines (6), and the build plan (7).*
