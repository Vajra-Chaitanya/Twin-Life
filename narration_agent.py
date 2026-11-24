"""
Module 7 -- narration_agent.py
Narration layer for TwinLife AI.

Uses the Gemini API to generate warm, plain-language explanations that
combine computed scores, SHAP feature contributions, and RAG guideline
chunks. Also generates ranked what-if scenario comparisons.

Usage:
    explanation = generate_explanation(twin_outputs, shap_features, rag_chunks)
    whatif_text = generate_ranked_whatifs(scenarios)
"""

from __future__ import annotations

import os
import json
import time
import warnings

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
warnings.filterwarnings("ignore", category=UserWarning)


# ---------------------------------------------------------------------------
#  GEMINI CLIENT HELPER
# ---------------------------------------------------------------------------
def _get_gemini_client() -> genai.Client:
    """Create a Gemini API client from the environment variable."""
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY environment variable not set. "
            "Get a free key at https://aistudio.google.com/apikey"
        )
    return genai.Client(api_key=api_key)


def _call_gemini(
    client: genai.Client,
    system_prompt: str,
    user_prompt: str,
    model: str = "gemini-3.5-flash-lite",
    max_retries: int = 3,
) -> str:
    """Call Gemini API with automatic retry on rate-limit errors.

    Args:
        client:        Gemini API client.
        system_prompt: System instruction for the model.
        user_prompt:   User message content.
        model:         Model name to use.
        max_retries:   Maximum number of retry attempts.

    Returns:
        Generated text response.
    """
    for attempt in range(max_retries + 1):
        try:
            response = client.models.generate_content(
                model=model,
                contents=[
                    types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=user_prompt)],
                    ),
                ],
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.4,
                    max_output_tokens=1500,
                ),
            )
            # Gemini can split one answer across several parts; join them all.
            parts = response.candidates[0].content.parts or []
            text = "".join(p.text or "" for p in parts).strip()
            if not text:
                raise RuntimeError("Gemini returned an empty response")
            return text
        except Exception as e:
            error_str = str(e)
            if ("429" in error_str or "RESOURCE_EXHAUSTED" in error_str) and attempt < max_retries:
                wait = 30 * (attempt + 1)
                print(f"    [Rate limited — waiting {wait}s before retry "
                      f"{attempt + 1}/{max_retries}...]")
                time.sleep(wait)
            elif any(s in error_str for s in ("503", "UNAVAILABLE", "overloaded", "500", "INTERNAL", "empty response")) \
                    and attempt < max_retries:
                time.sleep(2 * (attempt + 1))  # transient server-side failure
            else:
                raise


# ---------------------------------------------------------------------------
#  GENERATE EXPLANATION
# ---------------------------------------------------------------------------
def _pct(value) -> str:
    return f"{value * 100:.0f}%" if isinstance(value, (int, float)) else str(value)


def _pct1(value) -> str:
    return f"{value * 100:.1f}%" if isinstance(value, (int, float)) else "N/A"


def generate_explanation(
    twin_outputs: dict,
    shap_features: list[dict],
    rag_chunks: list[str],
    question: str | None = None,
    history: list[dict] | None = None,
) -> str:
    """Generate a plain-language explanation combining scores, SHAP, and RAG.

    Args:
        twin_outputs: Dict with keys like "health", "finance", "insurance",
                      "simulation" — each containing the respective profile.
        shap_features: List of SHAP feature dicts from HealthTwin:
                       [{"feature": str, "impact": float, "model": str}, ...]
        rag_chunks:   List of retrieved guideline text chunks from RAGAgent.
        question:     The user's current question, answered directly.
        history:      Earlier turns, oldest first: [{"query": str, "answer": str}].

    Returns:
        A warm, cited, plain-language explanation string.
    """
    client = _get_gemini_client()

    system_prompt = (
        "You are the TwinLife AI advisor. You answer a user's question about their "
        "own health, money and insurance using ONLY the computed data provided.\n\n"
        "ANSWER FORMAT (markdown, under 220 words):\n"
        "1. First line: a direct verdict in bold that answers the question "
        "(e.g. '**Not advisable at ₹15,000/month** — it pushes your debt load past the safe limit.'). "
        "If COMPUTED SCENARIO is present, its verdict decides this line. The verdict must agree with the "
        "numbers that follow (never say 'No' and then show the target is met).\n"
        "2. Section 2 depends on the question:\n"
        "   - If a COMPUTED SCENARIO, JUST RECORDED UPDATES or JUST REVERTED UPDATES exist: 'What changes' — 2-4 "
        "bullets with exact before → after numbers copied from them.\n"
        "   - Otherwise (a status question or symptom): 'Where you stand' — 2-4 bullets of current values "
        "with their targets (e.g. 'Emergency fund: 8.2 months (target 6)'). Never write an arrow or a 'before' "
        "value when nothing changed, and never use 0 as a starting value.\n"
        "3. 'Why it matters' — one or two sentences linking the numbers to the thresholds or guidelines "
        "(cite guidelines naturally, e.g. 'AHA guidelines recommend...').\n"
        "4. 'What you can do' — 2-3 numbered, specific actions with amounts or targets from the data.\n"
        "5. One short italic disclaimer line.\n\n"
        "RULES:\n"
        "- Never invent numbers; use only values given. Show ratios as percentages (32%, not 0.32; 68%, not 0.68) "
        "and money as ₹ amounts.\n"
        "- Symptoms (weakness, dizziness, pain, breathlessness): give 2-3 safe immediate steps, the warning "
        "signs that need emergency care, and relevant personal risk factors from the data; do not list "
        "unrelated financial numbers.\n"
        "- A relative's illness is family history: explain how it adds to the user's own risk; never treat it "
        "as the user's diagnosis.\n"
        "- Never use vague phrases like 'a bit higher', 'moderate impact' or 'somewhat' without the number.\n"
        "- No greetings, no praise filler, no repeating the question.\n"
        "- If an essential detail is missing (e.g. loan tenure or cost), state the assumption used and end "
        "with ONE short clarifying question.\n"
        "- Use the CONVERSATION SO FAR to understand follow-ups (resolve 'it', 'that', 'what about...'); "
        "build on earlier answers instead of repeating them, and stay consistent with them.\n"
        "- If no CURRENT QUESTION is given, summarise the most important findings in the same format.\n"
        "- If JUST RECORDED UPDATES are present, the user told you something that happened. Start with a bold "
        "line confirming the twin was updated, list the before → after changes, then explain what it means "
        "for them now. Be empathetic for health events.\n"
        "- Only say the twin, dashboard or data was updated if JUST RECORDED UPDATES or JUST REVERTED UPDATES "
        "are present in THIS prompt. If the user asks whether something was updated, answer from RECENT LIFE "
        "EVENTS: if it is not listed there, say clearly it was NOT saved and ask them to restate it with the amount.\n"
        "- The twin data sections are the saved truth. If numbers in CONVERSATION SO FAR differ from them, the "
        "conversation is wrong; never repeat unsaved figures as current values.\n"
        "- If DOMAIN FOCUS is present, answer ONLY for that twin. If the question belongs to another twin "
        "(e.g. a money question in the Health Twin chat), reply in one or two lines that this chat covers only "
        "that twin and they should ask on the matching Twin page (Health, Financial or Insurance); do not answer it.\n"
        "- If PAYMENTS & RENEWALS NEEDING ATTENTION lists OVERDUE, EXPIRED, MISSING or OUTSTANDING items relevant to "
        "the question (or the user asks what they owe), mention them with exact amounts and dates.\n"
        "- If JUST REVERTED UPDATES are present, the user asked to undo them: open with a bold line confirming "
        "exactly what was reverted, list the before → after changes, and say the dashboard and history now "
        "reflect it. Do not re-advise on the reverted item.\n"
        "- If PENDING QUESTIONS are present, ask them clearly (one bullet each) so the twin can be updated. "
        "If there are NO JUST RECORDED UPDATES, the twin was NOT changed: never say it was updated, open with "
        "a bold line asking for the missing detail, skip 'What changes', and briefly say what you will "
        "recompute once they answer.\n"
        "- Copy dates exactly as given; a commitment's end date is the date after 'until'.\n"
        "- When the user plans something new, ALWAYS factor in ACTIVE COMMITMENTS and RECENT LIFE EVENTS "
        "(e.g. 'you already pay ₹15,000/month for your car until 2031 and had a heart attack in Nov 2026'), "
        "and say what they are locked into before advising."
    )

    # Build the user prompt with all available data
    sections = []

    if "health" in twin_outputs:
        hp = twin_outputs["health"]
        cardio = hp.get("cardio_risk") or {}
        diabetes = hp.get("diabetes_risk") or {}
        lines = [
            f"BMI: {hp.get('bmi')} ({hp.get('obesity_class')})",
            f"Blood Pressure: {hp.get('hypertension_stage')}",
            f"Cardiovascular risk (ML model): {_pct1(cardio.get('probability'))} ({cardio.get('label', 'N/A')})",
            f"Glucose indicator: {hp.get('diabetes_indicator', 'N/A')}",
        ]
        if diabetes:
            lines.append(
                f"Diabetes risk (ML model): {_pct1(diabetes.get('probability'))} ({diabetes.get('label')}); "
                f"HbA1c {diabetes.get('hba1c')}%{' (estimated from glucose)' if diabetes.get('hba1c_estimated') else ''}"
                + ("; ALREADY DIAGNOSED with diabetes" if diabetes.get("diagnosed") else "")
            )
        if hp.get("conditions"):
            lines.append(f"Diagnosed conditions: {', '.join(c.replace('_', ' ') for c in hp['conditions'])}")
        lines.append(f"Overall Health Score: {hp.get('overall_health_score')}/100")
        sections.append("=== HEALTH PROFILE ===\n" + "\n".join(lines))

    if "finance" in twin_outputs:
        fp = twin_outputs["finance"]
        sections.append(
            "=== FINANCE PROFILE ===\n"
            f"Monthly income: Rs.{fp.get('monthly_income', 0):,.0f}\n"
            f"Monthly living expenses: Rs.{fp.get('monthly_expenses', 0):,.0f}\n"
            f"Free cash after expenses and EMIs: Rs.{fp.get('disposable_income', 0):,.0f}/month\n"
            f"Savings balance: Rs.{fp.get('savings_balance', 0):,.0f}\n"
            f"Debt-to-income: {_pct(fp.get('dti_ratio'))} (comfortable <= 36%, lender limit 43%)\n"
            f"Savings rate: {_pct(fp.get('savings_rate'))}\n"
            f"Emergency fund: {fp.get('emergency_fund_months')} months (target 6)\n"
            f"Financial Stability Score: {fp.get('financial_stability_score')}/100"
        )

    if "insurance" in twin_outputs:
        ip = twin_outputs["insurance"]
        lines = [
            f"Projected 5-year medical cost: Rs.{ip.get('estimated_future_cost', 0):,.0f}",
            f"Health cover vs projected cost: {_pct(ip.get('coverage_adequacy_ratio'))}",
            f"Health premium as share of income: {_pct1(ip.get('premium_affordability_ratio'))}",
            f"Rider gaps: {', '.join(ip.get('rider_analysis', {}).get('gaps', [])) or 'none'}",
            f"Insurance Score (health cover): {ip.get('insurance_adequacy_score')}/100",
        ]
        portfolio = ip.get("portfolio") or {}
        for p in portfolio.get("policies", []):
            lines.append(f"Policy: {p.get('name')} ({p.get('type')}), cover Rs.{p.get('cover', 0):,.0f}, "
                         f"premium Rs.{p.get('premium', 0):,.0f}/yr, renews {p.get('renewal_date') or 'unknown'}")
        if portfolio:
            lines.append(f"Total annual premium (all policies): Rs.{portfolio.get('total_annual_premium', 0):,.0f}")
            lines.append(f"Life cover: Rs.{portfolio.get('life_cover', 0):,.0f} vs about Rs.{portfolio.get('life_cover_recommended', 0):,.0f} "
                         "recommended (10x annual income)")
        sections.append("=== INSURANCE PROFILE ===\n" + "\n".join(lines))

    if "simulation" in twin_outputs and twin_outputs["simulation"]:
        sim = twin_outputs["simulation"]
        if "recommendation" in sim:
            sections.append(
                "=== TREATMENT SIMULATION ===\n"
                f"Agent Recommendation:\n{sim['recommendation'][:500]}"
            )

    for scenario in twin_outputs.get("scenarios") or []:
        lines = [f"Scenario: {scenario.get('headline')}", f"Verdict: {str(scenario.get('verdict', '')).upper()}"]
        lines += [f"- {fact}" for fact in scenario.get("facts", [])]
        if scenario.get("actions"):
            lines.append("Computed actions:")
            lines += [f"- {action}" for action in scenario["actions"]]
        if scenario.get("assumptions"):
            lines.append("Assumptions: " + "; ".join(scenario["assumptions"]))
        sections.append("=== COMPUTED SCENARIO (exact, use these numbers) ===\n" + "\n".join(lines))

    life = twin_outputs.get("life_context") or {}
    if life.get("dues"):
        sections.append("=== PAYMENTS & RENEWALS NEEDING ATTENTION ===\n" + "\n".join(
            f"- [{d['status'].upper()}] {d['title']}: Rs.{d.get('amount') or 0:,.0f}"
            + (f", due {d['due_date']}" if d.get("due_date") else "") + f" ({d['detail']})"
            for d in life["dues"]
        ))
    if twin_outputs.get("domain_focus"):
        focus = twin_outputs["domain_focus"]
        sections.append(f"=== DOMAIN FOCUS: {focus.upper()} TWIN ===\n"
                        f"This chat belongs to the {focus.capitalize()} Twin page. Answer only about {focus}.")
    if life.get("commitments"):
        sections.append("=== ACTIVE COMMITMENTS ===\n" + "\n".join(
            f"- Owes {c['lender']} Rs.{c.get('principal', 0):,.0f} (no repayment plan yet)" if c.get("informal") else
            f"- {c.get('item', 'loan').title()} EMI Rs.{c.get('emi', 0):,.0f}/month"
            + (f" until {c['end']}" if c.get("end") else " (tenure not recorded)")
            for c in life["commitments"]
        ))
    if life.get("recent_events"):
        sections.append("=== RECENT LIFE EVENTS ===\n" + "\n".join(
            f"- {e['date']}: {e['summary']}" for e in life["recent_events"]
        ))
    elif life:
        sections.append("=== RECENT LIFE EVENTS ===\nNone saved.")
    if life.get("just_recorded"):
        lines = []
        for e in life["just_recorded"]:
            lines.append(f"- {e['summary']}")
            lines += [f"    {c['label']}: {c['before']} -> {c['after']}" for c in e.get("changes", [])]
        sections.append("=== JUST RECORDED UPDATES (twin already recomputed) ===\n" + "\n".join(lines))
    if life.get("just_reverted"):
        changes = life["just_reverted"][0].get("changes", [])
        sections.append("=== JUST REVERTED UPDATES (twin already recomputed) ===\n" + "\n".join(
            [f"- Reverted: {e['summary']}" for e in life["just_reverted"]]
            + [f"    {c['label']}: {c['before']} -> {c['after']}" for c in changes]
        ))
    if life.get("pending_questions"):
        sections.append("=== PENDING QUESTIONS (ask the user) ===\n" + "\n".join(f"- {q}" for q in life["pending_questions"]))

    if shap_features:
        shap_text = "\n".join(
            f"  - {sf['feature']}: impact {sf['impact']:+.4f} ({sf['model']} model)"
            for sf in shap_features[:5]
        )
        sections.append(f"=== KEY FACTORS (SHAP Analysis) ===\n{shap_text}")

    if rag_chunks:
        rag_text = "\n---\n".join(chunk[:500] for chunk in rag_chunks[:3])
        sections.append(f"=== GUIDELINE REFERENCES ===\n{rag_text}")

    if history:
        turns = "\n\n".join(
            f"User: {turn.get('query', '')}\nAdvisor: {str(turn.get('answer', ''))[:600]}"
            for turn in history[-3:]
        )
        sections.append(f"=== CONVERSATION SO FAR ===\n{turns}")

    if question:
        sections.append(f"=== CURRENT QUESTION ===\n{question}")

    user_prompt = (
        "Based on the following data, answer the user's current question "
        "(or, if none is given, write a personalized health and financial "
        "wellness explanation):\n\n"
        + "\n\n".join(sections)
    )

    return _call_gemini(client, system_prompt, user_prompt)


# ---------------------------------------------------------------------------
#  GENERATE RANKED WHAT-IFS
# ---------------------------------------------------------------------------
def generate_ranked_whatifs(scenarios: list[dict]) -> str:
    """Rank and narrate 3-4 candidate what-if scenarios.

    Each scenario dict should contain:
        - "name": str (e.g., "Quit smoking", "Reduce weight by 5kg")
        - "risk_reduction": float (0-1, how much risk improves)
        - "cost": float (monetary cost of the change)
        - "insurance_fit": float (0-1, how well it aligns with insurance)

    Ranking formula:
        score = risk_reduction * 0.5 + (1 / max(cost, 1)) * 0.3 + insurance_fit * 0.2

    Args:
        scenarios: List of scenario dicts.

    Returns:
        Narrated comparison text with trade-offs.
    """
    if not scenarios:
        return "No what-if scenarios to evaluate."

    # Rank scenarios
    for s in scenarios:
        risk_red = s.get("risk_reduction", 0)
        cost = max(s.get("cost", 1), 1)
        ins_fit = s.get("insurance_fit", 0)
        s["score"] = round(
            risk_red * 0.5 + (1.0 / cost) * 0.3 * 100000 + ins_fit * 0.2,
            4,
        )

    ranked = sorted(scenarios, key=lambda s: s["score"], reverse=True)

    client = _get_gemini_client()

    system_prompt = (
        "You are a wellness advisor helping a user compare what-if scenarios. "
        "You are given ranked scenarios with their scores. Narrate them in a "
        "warm, clear way, explaining trade-offs between risk reduction, cost, "
        "and insurance fit. Keep it under 250 words. Include a disclaimer."
    )

    scenario_text = "\n".join(
        f"{i+1}. {s['name']} (Score: {s['score']:.2f}) — "
        f"Risk Reduction: {s.get('risk_reduction', 0):.0%}, "
        f"Cost: Rs.{s.get('cost', 0):,.0f}, "
        f"Insurance Fit: {s.get('insurance_fit', 0):.0%}"
        for i, s in enumerate(ranked[:4])
    )

    user_prompt = (
        f"Narrate these ranked what-if scenarios for the user, "
        f"explaining trade-offs:\n\n{scenario_text}"
    )

    return _call_gemini(client, system_prompt, user_prompt)


# ======================================================================
#  STANDALONE VERIFICATION (python narration_agent.py)
# ======================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("  Module 7: Narration Agent — Explanation Test")
    print("=" * 60)

    # Test with sample data (no twin initialization needed)
    sample_twin_outputs = {
        "health": {
            "bmi": 26.3,
            "obesity_class": "Overweight (Pre-obese)",
            "hypertension_stage": "Stage 1",
            "cardio_risk": {"probability": 0.42, "label": "Elevated"},
            "diabetes_indicator": "Medium",
            "overall_health_score": 58,
        },
        "finance": {
            "dti_ratio": 0.35,
            "savings_rate": 0.25,
            "emergency_fund_months": 4.2,
            "financial_stability_score": 62,
        },
    }

    sample_shap = [
        {"feature": "ap_hi", "impact": 0.0823, "model": "cardio"},
        {"feature": "bmi", "impact": 0.0615, "model": "cardio"},
        {"feature": "age_years", "impact": 0.0512, "model": "cardio"},
    ]

    sample_rag = [
        "For Hypertension Stage 1, if the 10-year cardiovascular risk "
        "exceeds 10%, antihypertensive medication should be initiated "
        "alongside lifestyle changes. Target blood pressure should be "
        "below 130/80 mmHg. (Source: AHA/ACC 2017 Guidelines)",
    ]

    print("\n[1] Generating personalized explanation...")
    explanation = generate_explanation(
        sample_twin_outputs, sample_shap, sample_rag,
    )
    print(f"\n{explanation}")

    # Test what-if ranking
    print(f"\n{'=' * 60}")
    print("  What-If Scenario Ranking")
    print("=" * 60)

    sample_scenarios = [
        {
            "name": "Quit smoking",
            "risk_reduction": 0.35,
            "cost": 0,
            "insurance_fit": 0.8,
        },
        {
            "name": "Lose 5kg through diet and exercise",
            "risk_reduction": 0.20,
            "cost": 5000,
            "insurance_fit": 0.5,
        },
        {
            "name": "Start blood pressure medication",
            "risk_reduction": 0.30,
            "cost": 12000,
            "insurance_fit": 0.9,
        },
    ]

    print("\n[2] Generating ranked what-if narration...")
    whatif_text = generate_ranked_whatifs(sample_scenarios)
    print(f"\n{whatif_text}")
