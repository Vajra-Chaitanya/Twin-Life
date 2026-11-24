# 5. Simulation Engines and Orchestrator Routing

## Part A — Individual "What-If" Simulators
Each twin gets its own simulator: take a hypothetical input change, re-run the SAME formulas/model from Doc 3/4, and compare before vs. after.

| Twin | User adjusts | How it recomputes |
|---|---|---|
| Health | Weight change, smoking status, activity level, glucose (via diet) | Re-run the same model + formulas with new hypothetical inputs → new health_profile |
| Finance | +savings/month, income change, new EMI, one-time expense | Monte Carlo simulation (NumPy) — 1,000 simulated months forward → probability distribution, not a single number |
| Insurance | +coverage amount, add rider, change premium | Pure arithmetic recompute (cheap, instant — no simulation needed) |

## Part B — The Combined Simulation Engine (Cross-Domain Decision Tree)

This is the centerpiece: coordinating all three twins for one task, like "should I go ahead with this ₹C treatment plan?" This logic is **plain code (if/else), not an LLM decision** — the LLM only narrates whichever branch gets reached.

```
1. HEALTH TWIN confirms relevance, provides/confirms cost basis C

2. FINANCE TWIN → affordability_score = affordability_fn(C)
   IF affordable:
        → Recommend "self-fund, no insurance needed." STOP.
   IF NOT affordable:
        → CALL INSURANCE TWIN

3. INSURANCE TWIN → coverage_for_C = min(sum_insured, C)
                     gap = C − coverage_for_C
   IF gap <= 0:
        → Recommend "fully covered — file a claim." STOP.
   IF gap > 0:
        → RE-CHECK FINANCE TWIN on just the gap amount
        IF gap affordable:
             → Recommend "partial self-fund + claim for the rest." STOP.
        IF NOT affordable:
             → Look up a cheaper treatment alternative (Health Twin's
               cost table, next tier down)
             → RE-RUN from step 2 with the new lower cost
             → If still unaffordable at the lowest tier:
                  → Recommend increasing coverage / a payment plan
```

## Part C — Orchestrator Query Routing (what makes this "agentic")

**Step 1 — Rule-based fast path (no API cost):**
| Query contains... | Twins called |
|---|---|
| "diabetes", "blood pressure", "weight" only | Health only |
| "save", "afford", "loan", "EMI" only | Finance only |
| "coverage", "premium", "claim" only | Insurance only |
| "treatment"/"medication" + a cost/money word | All three (triggers Part B tree) |
| Ambiguous | Falls through to Step 2 |

**Step 2 — LLM fallback (Claude API) for ambiguous queries only:**
```
System: Decide which of ["health","finance","insurance"] are relevant,
whether this is single-domain or cross-domain, and whether simulation
is needed. Respond ONLY as JSON.

Example: "What if I save ₹5000 more per month?"
→ {"twins": ["finance"], "mode": "single-domain", "simulate": true}
```

**Why this matters:** if the user only asks about finance, Health and Insurance are never called — this is the literal implementation of "the orchestrator should decide what all it should call" from your original ask.

## Part D — Ranking Multiple What-If Options
For open-ended questions ("how can I reduce my risk?"), generate 3-4 candidate scenarios and rank them, instead of returning one answer:

| Scenario | Health impact | Cost | Insurance impact |
|---|---|---|---|
| Aggressive lifestyle change | 42%→22% in 6mo | ~₹5,000 | None needed |
| Moderate lifestyle + checkup | 42%→30% in 6mo | ~₹15,000 | Uses OPD rider |
| Medication-assisted | 42%→18% in 3mo | ~₹40,000/yr | Needs Critical Illness rider |
| Do nothing | Worsens to ~50% | ₹0 | Future cost risk increases |

Ranking formula: `risk_reduction × 0.5 + (1/cost) × 0.3 + insurance_fit × 0.2` — then the narration layer (Doc 2) presents them ranked, in plain language, letting the user choose.

---
*Next: read `06_Proactive_and_Recommendation_Engines.md` for the Monitoring Agent and Finance/Health recommendation logic.*
