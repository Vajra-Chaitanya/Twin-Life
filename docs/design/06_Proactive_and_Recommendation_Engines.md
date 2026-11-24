# 6. Proactive and Recommendation Engines
### What makes the system act without being asked, and what gives investment/spending/lifestyle guidance

## A. The Monitoring Agent (proactive behavior)

Everything in Doc 5 triggers when the user asks something. This is the one piece that runs **on its own**.

```
Scheduled job (weekly, or whenever new data is logged) via APScheduler
        ↓
Re-computes all three twins' scores using latest data
        ↓
Compares new scores to the last saved snapshot (stored in DB)
        ↓
IF any score crosses a risk-band threshold
   (e.g., Health Score drops >10 pts, DTI rises above 40%,
    a new Insurance gap appears):
        → Generate an alert via the narration layer (Doc 2)
        → Push to dashboard / WhatsApp (Doc 7)
ELSE:
        → Silently update the stored snapshot, no alert
```

**What this needs:** one new DB table (`snapshots`: user_id, timestamp, scores, raw_inputs) + one scheduled Python function comparing current vs. previous snapshot. The comparison logic is plain deterministic code — same style as Doc 5's decision tree, not an LLM decision. The LLM's only job is turning "DTI rose from 28% to 35%" into a readable alert sentence.

---

## B. Finance Twin — Investment Recommendations (rule-based)

Uses the Finance Twin's existing outputs (Doc 3) to bucket the user into a risk-appetite tier:

```
IF emergency_fund_months < 3:
     → Build liquid savings/FD first — no investment yet
ELIF stability_score >= 70 AND age < 40:
     → Growth-oriented allocation (higher equity/mutual fund SIP)
ELIF stability_score >= 70 AND age >= 40:
     → Balanced allocation (equity + debt funds)
ELIF stability_score in 40-70:
     → Conservative allocation (debt funds, RDs) + improve savings rate first
ELSE (score < 40):
     → No new investment — focus entirely on reducing DTI first
```
*(Include a disclaimer: "illustrative guidance, not licensed financial advice.")*

## C. Finance Twin — Spending Restriction / Purchase Impact Simulator
This reuses the what-if pattern from Doc 5, applied to a hypothetical purchase:

```
User: "I want to buy X costing ₹P"
        ↓
Recompute finance_profile as if this month's expenses += P
        ↓
IF new savings_rate/DTI breaches healthy threshold:
     → Flag the score drop
     → Generate ranked alternatives:
        A: Defer purchase N months while saving toward it
        B: Suggest a lower-cost equivalent tier
        C: Split into EMI, recheck new DTI
        D: Trim the largest existing discretionary category instead
ELSE:
     → "This fits comfortably within your budget."
```

## D. Health Twin — Lifestyle Restriction Engine (same pattern)
```
User: "I want to eat/do X"
        ↓
Recompute health_profile with the hypothetical habit factored in
        ↓
IF this worsens diabetes/CVD risk band:
     → Flag the impact
     → Suggest ranked alternatives:
        A: Healthier substitute (lookup table)
        B: Portion/frequency moderation instead of elimination
        C: Offsetting action (e.g., extra activity that week)
ELSE:
     → "Minimal impact on your current risk profile."
```
*(Keep this at the lifestyle-habit level — not a full calorie/food-database tracker, which is a much bigger project on its own.)*

---
*Next: read `07_Tech_Stack_Build_Roadmap_and_Demo.md` for the actual build plan, tech stack, and how to make this feel used daily.*
