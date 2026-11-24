# 1. What Is TwinLife AI

## The idea in one paragraph
TwinLife AI creates a digital copy of a person's health, finances, and insurance, watched over by an AI "manager" (the Orchestrator) that pulls in the right specialist — Health Twin, Finance Twin, or Insurance Twin — depending on what's actually being asked, and coordinates between them when a decision touches more than one domain (e.g., "can I afford this treatment, and does my insurance cover it?").

## The core insight the whole project is built on
Health apps, finance apps, and insurance apps today are all separate and disconnected. A person with rising diabetes risk who also has high debt and thin insurance coverage gets three unrelated pieces of advice from three unrelated apps — nobody tells them "start this lifestyle change AND here's how to afford the checkup AND here's the insurance gap you should close first." TwinLife AI's entire value is reasoning **across** these domains, not just within one.

## Who uses it

| Persona | What they get |
|---|---|
| Individual/working professional | One dashboard: health risk trend + financial risk trend + whether insurance covers the gap between them |
| Middle-income families | Help with afford-vs-need trade-offs ("can I afford this checkup without hurting my EMI capacity?") |
| Chronic-risk patients (pre-diabetic, hypertensive) | Early health warnings paired with a realistic financial plan for future treatment costs |
| Insurance advisors (secondary use case) | A tool to show clients personalized coverage-gap analysis backed by real risk prediction |

## What problem it solves
- Health apps predict risk but ignore affordability.
- Finance apps track spending but ignore future medical liabilities.
- Insurance apps sell policies without reasoning about actual health trajectory or financial cushion.
- Everything today is single-domain and reactive. TwinLife AI is cross-domain, proactive, and explains *why* it's recommending something instead of just showing numbers.

## Why this project is worth building (for your panel)
1. It's **agentic**, not just predictive — the Orchestrator decides what to do, it isn't a fixed pipeline.
2. It's **explainable** — every recommendation can be traced back to a real computed number and a real cited guideline, not an LLM guessing.
3. It **simulates the future** — "what if I do X" is a genuinely strong live-demo moment.
4. It's **grounded**, not hallucinated — recommendations cite real medical/financial guidelines via RAG.
5. It's designed to be **used daily**, not opened once and forgotten (WhatsApp nudges, proactive alerts, photo-based logging) — most student projects stop at "dashboard," this one doesn't.

---
*Next: read `02_System_Architecture_and_AI_Concepts.md` to understand how the pieces fit together and what each AI component is actually responsible for.*
