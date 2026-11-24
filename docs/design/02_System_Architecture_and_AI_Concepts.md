# 2. System Architecture and AI Concepts
### This document exists specifically to answer: "what is each AI piece actually doing, and how do they NOT overlap?"

## The full pipeline, in order

```
1. USER INPUT (form, chat query, or voice/photo)
        ↓
2. TWINS COMPUTE RAW NUMBERS
   (Health = 1 ML model + formulas | Finance = formulas | Insurance = rules)
        ↓
3. SHAP EXPLAINS THE MODEL'S NUMBER
   (only applies to the ML model's prediction, not the formulas)
        ↓
4. ORCHESTRATOR DECIDES WHAT WAS ASKED
   (routes to one twin, or triggers the cross-domain decision tree)
        ↓
5. RAG RETRIEVES REAL GUIDANCE
   (fetches relevant chunks from real documents, based on the result)
        ↓
6. CLAUDE API NARRATES THE FINAL ANSWER
   (combines steps 2+3+5 into one readable, cited explanation)
        ↓
7. SIMULATION ENGINE (only if a what-if was asked)
   (re-runs steps 2-6 on hypothetical inputs, shows before/after)
```

Six different "AI-sounding" terms appear in your abstract. Here is exactly what each one does, with **zero overlap** between them:

---

## Machine Learning Model — "computes a number"
- **What it is:** One Random Forest classifier, trained on the Cardiovascular Disease dataset.
- **What it does:** Takes structured inputs (age, BMI, BP, glucose, cholesterol, lifestyle) → outputs a probability/label (e.g., "Cardio risk: 42%, Medium").
- **What it does NOT do:** It does not explain itself, it does not retrieve documents, it does not decide what to do with the result — it just predicts.

## Formulas (Framingham, BMI/WHO bands, BP staging, DTI, savings rate, coverage adequacy) — "computes a number, without training"
- **What they are:** Plain deterministic Python functions using established clinical/financial standards.
- **What they do:** Same job as the ML model (produce a number) but for cases where a validated formula already exists and training a model would be redundant.
- **What they do NOT do:** Same as the model — no explanation, no retrieval, no decision-making. They're a second way of getting Step 2's numbers, not a different pipeline stage.

## SHAP — "explains WHY the model said that number"
- **What it is:** A mathematical technique that attributes a model's prediction to its input features.
- **What it does:** For the ML model's output ONLY (not the formulas — formulas are already self-explanatory by construction), computes which features pushed the risk up or down (e.g., "glucose contributed +18%, BMI +12%").
- **What it does NOT do:** It does not generate any text, it does not know about guidelines, it does not talk to the user directly. It produces numbers (feature attributions), same as the model produces a number.

## Orchestrator — "decides what needs to happen"
- **What it is:** LangGraph-based routing logic (rule-based fast path + LLM fallback for ambiguous queries).
- **What it does:** Reads the user's query and decides: which twin(s) to call, whether this is single-domain or cross-domain, whether a simulation is needed.
- **What it does NOT do:** It does not compute risk scores itself, it does not write explanations, it does not retrieve documents. It's purely the "who do I call and in what order" decision-maker — the control flow, not the content.

## RAG (Retrieval-Augmented Generation) — "finds real supporting evidence for the recommendation"
- **What it is:** A vector database (ChromaDB) of real documents (ADA diabetes guidelines, WHO hypertension guidelines, RBI financial literacy docs, IRDAI circulars) + a retrieval function.
- **What it does:** Given a topic (e.g., "diabetes medium risk management"), fetches the 2-3 most relevant real text chunks from those documents.
- **What it does NOT do:** It does not predict anything, it does not write the final explanation itself — it only supplies grounding material for the next step to use. Without RAG, the final explanation would be the LLM's own unguided guess about "what's usually recommended" — RAG replaces that guess with a citation.

## Claude API / LLM Narration — "turns numbers + evidence into one readable, cited answer"
- **What it is:** A single API call (or a few, per component) that takes everything computed/retrieved above and writes the final response.
- **What it does:** Combines the model/formula's number (Step 2), SHAP's feature attribution (Step 3), and RAG's retrieved guideline text (Step 5) into one coherent paragraph, with a citation.
- **What it does NOT do:** It does not decide the risk score (that already happened), it does not decide which twin to call (the Orchestrator already did that), and it does not invent medical/financial facts — it only writes in plain language using what it was given.

## Simulation Engine — "re-runs the whole pipeline on a hypothetical"
- **What it is:** Either a pure recompute (individual twin what-ifs) or a Monte Carlo run (finance forecasting) or the cross-domain decision tree (treatment-plan → finance-check → insurance-check → fallback).
- **What it does:** Takes a "what if X changed" input, re-runs Steps 2-6 with the modified input, and shows a before/after comparison.
- **What it does NOT do:** It's not a separate AI technique — it's the same pipeline (model/formula → SHAP → Orchestrator routing → RAG → narration) run twice, once with real data and once with hypothetical data.

---

## The one sentence that ties it together for your report/viva
> *"Risk scores come from a trained ML model and domain-standard formulas; SHAP explains the model's reasoning; the Orchestrator decides which components to invoke for a given query; RAG grounds the final recommendation in real guidelines; and the LLM narration layer synthesizes all of this into one transparent, cited response — with the entire pipeline re-runnable on hypothetical inputs for what-if simulation."*

If an examiner asks "isn't this all just the LLM doing everything?" — the answer is no, and this document is your proof: the LLM only ever touches Steps 5-6 (retrieval-context assembly and final writing). Every number in the system comes from Step 2, and every explanation of *why* a number is what it is comes from Step 3 — both of which are fully deterministic and independently testable without ever calling an API.

---
*Next: read `03_Data_Inputs_and_Twin_Processing.md` for the exact input fields and processing logic per twin.*
