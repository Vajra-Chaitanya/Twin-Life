# TwinLife AI — Document Index
### Read in this order. Each document covers exactly one part of the project.

Everything we've discussed has been sorted into 7 focused documents. Nothing overlaps — if you're looking for something, this index tells you exactly which file it's in.

| # | Document | What's in it | What it does NOT cover |
|---|---|---|---|
| 1 | `01_What_Is_TwinLife_AI.md` | The idea in plain English, who uses it, what problem it solves, why it's worth building | No technical detail — read this first, or hand it to anyone (supervisor, friend) who needs the concept in 2 minutes |
| 2 | `02_System_Architecture_and_AI_Concepts.md` | How the whole system fits together, and — critically — **exactly what job each AI component does and does NOT do** (Model vs. Formulas vs. RAG vs. SHAP vs. LLM narration vs. Orchestrator) | No input field lists, no code, no build steps |
| 3 | `03_Data_Inputs_and_Twin_Processing.md` | Exact input fields for Health/Finance/Insurance, and how each is processed (which use the model, which use formulas), with output JSON shapes | No architecture explanation (that's Doc 2), no model training detail (that's Doc 4) |
| 4 | `04_ML_Model_Specification.md` | The ONE model decision: which dataset, which features, which target, how to train it | No formulas (those are in Doc 3) |
| 5 | `05_Simulation_Engines_and_Orchestrator_Routing.md` | Individual what-if simulators, the combined cross-domain decision tree, and how the Orchestrator decides which twins to call for a given query | No AI-concept theory (that's Doc 2) |
| 6 | `06_Proactive_and_Recommendation_Engines.md` | The Monitoring Agent (proactive alerts), Finance investment/restriction logic, Health restriction logic | No simulation-engine mechanics (that's Doc 5) |
| 7 | `07_Tech_Stack_Build_Roadmap_and_Demo.md` | The exact tech stack, week-by-week build plan, daily-use interactive features (WhatsApp, voice, photo scanning), demo script, submission checklist | No conceptual/architecture explanation (that's Doc 2) |

### The one-sentence version of how it all connects
> Doc 3's inputs feed into Doc 4's model and Doc 3's formulas → their outputs are combined and routed by Doc 5's Orchestrator → Doc 6's engines add proactive/recommendation behavior on top → Doc 2 explains exactly how RAG and SHAP turn all of that into a trustworthy, cited explanation → Doc 7 tells you how to actually build and demo all of it.

If you only read one document before a supervisor meeting to re-orient yourself, read **Doc 2** — it's the one that ties every AI buzzword in your abstract (ML, Agentic AI, RAG, Explainable AI, Simulation) to one specific, non-overlapping job in the pipeline.
