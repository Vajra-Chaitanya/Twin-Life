"""
scenario_engine.py
Deterministic "what if" calculator for advisor questions.

Parses the user's question for concrete changes (a new EMI, a one-time purchase,
a salary or expense change, weight/BP/smoking/activity changes, a new sum
insured), re-runs the twins on the modified inputs, and returns exact
before/after metrics, a verdict, and numeric next steps.  The narration layer
only explains these numbers; it never has to estimate them.
"""

from __future__ import annotations

import re
from typing import Callable

from finance_twin import FinanceTwin
from formulas import bmi as calc_bmi, bp_stage
from insurance_twin import InsuranceTwin
from recommendation_engines import purchase_impact_simulator

DTI_COMFORT = 0.36
DTI_MAX = 0.43
EF_TARGET_MONTHS = 6

# Unit spellings people actually type: lakh, lakhs, lac, lacs, laksh, lkh, l, crore, cr, k, thousand.
MULT_PATTERN = r"k|thousand|la(?:kh?|c|ksh?)s?|lkhs?|lks?|l|crores?|cr"
_MONEY = re.compile(
    r"(?P<cur>₹|rs\.?|inr)?\s*(?P<num>\d+(?:,\d+)*(?:\.\d+)?)\s*(?P<mult>" + MULT_PATTERN + r")?\b"
    r"(?!\s*(?:%|kg|kgs|kilos?|months?|mos?|years?|yrs?|mmhg|/))",
    re.IGNORECASE,
)


def _multiplier(unit: str) -> float:
    unit = unit.lower()
    if unit in ("k", "thousand"):
        return 1e3
    return 1e7 if unit.startswith("cr") else 1e5


def inr(value: float) -> str:
    """Format rupees with Indian digit grouping, e.g. 1234567 -> ₹12,34,567."""
    sign = "-" if value < 0 else ""
    digits = str(int(round(abs(value))))
    if len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        head = ",".join(re.findall(r"\d{1,2}", head[::-1]))[::-1]
        digits = f"{head},{tail}"
    return f"{sign}₹{digits}"


def pct(value: float) -> str:
    return f"{value * 100:.0f}%"


def money_amounts(text: str) -> list[float]:
    """Rupee amounts in the text; bare numbers count only if they look like money (>= 500)."""
    amounts = []
    for m in _MONEY.finditer(text):
        value = float(m.group("num").replace(",", ""))
        mult = m.group("mult") or ""
        if mult:
            value *= _multiplier(mult)
        if m.group("cur") or mult or value >= 500:
            amounts.append(value)
    return amounts


def tenure_months(text: str) -> int | None:
    m = re.search(r"(\d+(?:\.\d+)?)\s*(months?|mos?|years?|yrs?)\b", text, re.IGNORECASE)
    if not m:
        return None
    n = float(m.group(1))
    return int(round(n * 12 if m.group(2).lower().startswith(("y", "yr")) else n))


def _metric(label: str, before: str, after: str, better: bool | None) -> dict:
    return {"label": label, "before": before, "after": after, "better": better}


def _finance_verdict(after: dict) -> str:
    income = after["monthly_income"]
    if after["dti_ratio"] > DTI_MAX or after["disposable_income"] < 0:
        return "risky"
    if after["dti_ratio"] > DTI_COMFORT or after["disposable_income"] < 0.1 * income:
        return "stretch"
    return "comfortable"


def _ef_text(profile: dict) -> str:
    months = profile["emergency_fund_months"]
    return "∞" if months == float("inf") else f"{months:.1f} mo"


def _finance_metrics(before: dict, after: dict) -> list[dict]:
    return [
        _metric("Debt-to-income", pct(before["dti_ratio"]), pct(after["dti_ratio"]), after["dti_ratio"] <= before["dti_ratio"]),
        _metric("Free cash / month", inr(before["disposable_income"]), inr(after["disposable_income"]),
                after["disposable_income"] >= before["disposable_income"]),
        _metric("Emergency fund", _ef_text(before), _ef_text(after), after["emergency_fund_months"] >= before["emergency_fund_months"]),
        _metric("Stability score", f"{before['financial_stability_score']}/100", f"{after['financial_stability_score']}/100",
                after["financial_stability_score"] >= before["financial_stability_score"]),
    ]


def _emi_headroom(inputs: dict, limit: float) -> float:
    return max(0.0, limit * inputs["income"] - inputs["fixed_expenses"] - inputs["emis"])


def _emi_scenario(text: str, emi: float, finance_inputs: dict) -> dict:
    before = FinanceTwin().assess(finance_inputs)
    after = FinanceTwin().assess({**finance_inputs, "emis": finance_inputs["emis"] + emi})
    verdict = _finance_verdict(after)
    months = tenure_months(text)
    safe = _emi_headroom(finance_inputs, DTI_COMFORT)
    ceiling = _emi_headroom(finance_inputs, DTI_MAX)

    facts = [
        f"New EMI: {inr(emi)}/month" + (f" for {months} months (total repaid {inr(emi * months)})" if months else ""),
        f"Debt-to-income goes from {pct(before['dti_ratio'])} to {pct(after['dti_ratio'])} "
        f"(comfortable up to {pct(DTI_COMFORT)}, most lenders cap at {pct(DTI_MAX)})",
        f"Free cash per month drops from {inr(before['disposable_income'])} to {inr(after['disposable_income'])}",
        f"Largest EMI that keeps debt-to-income at or below {pct(DTI_COMFORT)}: {inr(safe)}/month; "
        f"at or below {pct(DTI_MAX)}: {inr(ceiling)}/month",
    ]
    actions = []
    if safe <= 0:
        actions.append(
            f"You have no comfortable borrowing headroom left (debt-to-income is already {pct(before['dti_ratio'])}); "
            "pay cash, wait until an existing loan closes, or raise income before taking a new EMI."
        )
    elif emi > safe:
        actions.append(f"Bring the EMI down to about {inr(safe)}/month (larger down payment or longer tenure) to stay in the comfortable zone.")
        if months:
            actions.append(f"At {months} months that means borrowing about {inr(safe * months)} instead of {inr(emi * months)}.")
    else:
        actions.append(f"This EMI fits; you would still have {inr(safe - emi)}/month of comfortable borrowing headroom.")
    if after["disposable_income"] < 0:
        actions.append("Monthly outflows would exceed income, so this is not sustainable without cutting other expenses.")
    return {
        "kind": "emi",
        "verdict": verdict,
        "headline": f"{inr(emi)}/month EMI",
        "facts": facts,
        "actions": actions,
        "assumptions": [] if months else ["Tenure not given; totals assume the EMI amount only."],
        "metrics": _finance_metrics(before, after),
    }


def _purchase_scenario(cost: float, finance_inputs: dict) -> dict:
    before = FinanceTwin().assess(finance_inputs)
    impact = purchase_impact_simulator(before, cost)["impact_analysis"]
    savings = finance_inputs["savings_balance"]
    monthly_expenses = before["monthly_expenses"]
    ef_after = (savings - cost) / monthly_expenses if monthly_expenses else float("inf")
    free = before["disposable_income"]
    if cost <= 0.3 * savings and ef_after >= EF_TARGET_MONTHS:
        verdict = "comfortable"
    elif cost <= savings and ef_after >= 3:
        verdict = "stretch"
    else:
        verdict = "risky"
    emi_24 = cost / 24
    facts = [
        f"One-time cost: {inr(cost)} against savings of {inr(savings)}",
        f"Paying cash leaves {inr(max(0, savings - cost))} ({max(0, ef_after):.1f} months of expenses; target {EF_TARGET_MONTHS})",
        f"Saving it from free cash ({inr(free)}/month) takes about {cost / free:.0f} months" if free > 0 else
        "There is no free cash each month to save toward it",
        f"As a 24-month EMI: {inr(emi_24)}/month, debt-to-income {pct(impact['new_dti_if_emi_24months'])}",
    ]
    actions = []
    keep = max(0.0, savings - EF_TARGET_MONTHS * monthly_expenses)
    if verdict != "comfortable":
        actions.append(f"Pay at most {inr(keep)} from savings so {EF_TARGET_MONTHS} months of expenses stay untouched.")
        if free > 0:
            actions.append(f"Set aside {inr(free * 0.7)}/month (70% of free cash) to close the gap in about {max(0, cost - keep) / (free * 0.7):.0f} months.")
    else:
        actions.append(f"You can pay cash and still keep {max(0, ef_after):.1f} months of emergency savings.")
    return {
        "kind": "purchase",
        "verdict": verdict,
        "headline": f"{inr(cost)} one-time cost",
        "facts": facts,
        "actions": actions,
        "assumptions": ["EMI figures exclude interest."],
        "metrics": _finance_metrics(before, FinanceTwin().assess({**finance_inputs, "savings_balance": max(0, savings - cost)})),
    }


def _income_scenario(new_income: float, finance_inputs: dict, label: str) -> dict:
    before = FinanceTwin().assess(finance_inputs)
    outflow = finance_inputs["fixed_expenses"] + finance_inputs["variable_expenses"] + finance_inputs["emis"]
    if new_income <= 0:
        runway = finance_inputs["savings_balance"] / outflow if outflow else float("inf")
        return {
            "kind": "income",
            "verdict": "risky" if runway < EF_TARGET_MONTHS else "stretch",
            "headline": "No income",
            "facts": [f"Monthly outflows of {inr(outflow)} (including EMIs) would be paid from savings of {inr(finance_inputs['savings_balance'])}",
                      f"Savings last about {runway:.1f} months"],
            "actions": [f"Cutting variable spending by half ({inr(finance_inputs['variable_expenses'] / 2)}) would stretch that to "
                        f"{finance_inputs['savings_balance'] / max(1, outflow - finance_inputs['variable_expenses'] / 2):.1f} months."],
            "assumptions": [],
            "metrics": [],
        }
    after = FinanceTwin().assess({**finance_inputs, "income": new_income})
    return {
        "kind": "income",
        "verdict": _finance_verdict(after),
        "headline": label,
        "facts": [f"Income changes from {inr(finance_inputs['income'])} to {inr(new_income)}/month",
                  f"Debt-to-income {pct(before['dti_ratio'])} → {pct(after['dti_ratio'])}; "
                  f"free cash {inr(before['disposable_income'])} → {inr(after['disposable_income'])}/month"],
        "actions": [],
        "assumptions": [],
        "metrics": _finance_metrics(before, after),
    }


def _expense_scenario(change: float, finance_inputs: dict, decrease: bool) -> dict:
    delta = -change if decrease else change
    before = FinanceTwin().assess(finance_inputs)
    after = FinanceTwin().assess({**finance_inputs, "variable_expenses": max(0, finance_inputs["variable_expenses"] + delta)})
    verdict = "comfortable" if decrease else _finance_verdict(after)
    free_after = after["disposable_income"]
    actions = []
    if not decrease and free_after < 0.2 * finance_inputs["income"]:
        actions.append(f"Free cash would fall to {inr(free_after)}/month (below 20% of income); trim other spending by "
                       f"{inr(0.2 * finance_inputs['income'] - free_after)}/month to keep a 20% buffer.")
    return {
        "kind": "expense",
        "verdict": verdict,
        "headline": f"Monthly spending {'-' if decrease else '+'}{inr(change)}",
        "facts": [f"Monthly expenses change by {inr(delta)}",
                  f"Free cash {inr(before['disposable_income'])} → {inr(free_after)}/month",
                  f"Emergency fund {_ef_text(before)} → {_ef_text(after)}"],
        "actions": actions,
        "assumptions": [],
        "metrics": _finance_metrics(before, after),
    }


def _health_scenario(changes: dict, health_inputs: dict, health_profile: dict | None,
                     health_assess: Callable[[dict], dict] | None) -> dict:
    after_inputs = {**health_inputs, **changes}
    if health_assess and health_profile:
        after = health_assess(after_inputs)
        before = health_profile
    else:
        def lite(inp: dict) -> dict:
            return {"bmi": calc_bmi(inp["height_cm"], inp["weight_kg"]), "hypertension_stage": bp_stage(inp["ap_hi"], inp["ap_lo"])}
        before, after = lite(health_inputs), lite(after_inputs)

    metrics = [
        _metric("BMI", f"{before['bmi']}", f"{after['bmi']}", after["bmi"] <= before["bmi"]),
        _metric("Blood pressure", before["hypertension_stage"], after["hypertension_stage"], None),
    ]
    facts = [f"BMI {before['bmi']} → {after['bmi']}", f"Blood pressure stage {before['hypertension_stage']} → {after['hypertension_stage']}"]
    if "cardio_risk" in after:
        b, a = before["cardio_risk"]["probability"], after["cardio_risk"]["probability"]
        metrics.insert(0, _metric("CVD risk", f"{b * 100:.1f}%", f"{a * 100:.1f}%", a <= b))
        metrics.append(_metric("Health score", f"{before['overall_health_score']}/100", f"{after['overall_health_score']}/100",
                               after["overall_health_score"] >= before["overall_health_score"]))
        facts.insert(0, f"Predicted cardiovascular risk {b * 100:.1f}% → {a * 100:.1f}% "
                        f"({before['cardio_risk']['label']} → {after['cardio_risk']['label']})")
        facts.append(f"Health score {before['overall_health_score']} → {after['overall_health_score']}/100")
    improved = sum(1 for m in metrics if m["better"]) >= sum(1 for m in metrics if m["better"] is False)
    described = ", ".join(f"{k.replace('_', ' ')} → {v}" for k, v in changes.items())
    return {
        "kind": "health",
        "verdict": "improves" if improved else "worsens",
        "headline": described,
        "facts": facts,
        "actions": [],
        "assumptions": ["Model estimate of the same person with only these inputs changed; not a clinical prediction."],
        "metrics": metrics,
    }


def _insurance_scenario(sum_insured: float, insurance_inputs: dict, health_profile: dict | None, finance_profile: dict) -> dict:
    if not health_profile:
        return {}
    before = InsuranceTwin().assess(insurance_inputs, health_profile, finance_profile)
    after = InsuranceTwin().assess({**insurance_inputs, "sum_insured": sum_insured}, health_profile, finance_profile)
    cost = before["estimated_future_cost"]
    return {
        "kind": "insurance",
        "verdict": "comfortable" if after["coverage_adequacy_ratio"] >= 1 else "stretch",
        "headline": f"Sum insured {inr(sum_insured)}",
        "facts": [f"Sum insured {inr(insurance_inputs['sum_insured'])} → {inr(sum_insured)} against projected 5-year costs of {inr(cost)}",
                  f"Coverage ratio {pct(before['coverage_adequacy_ratio'])} → {pct(after['coverage_adequacy_ratio'])}",
                  f"Insurance score {before['insurance_adequacy_score']} → {after['insurance_adequacy_score']}/100"],
        "actions": [] if after["coverage_adequacy_ratio"] >= 1 else [f"Full cover needs a sum insured of about {inr(cost)}."],
        "assumptions": ["Premium kept unchanged; a higher sum insured usually costs more."],
        "metrics": [_metric("Coverage", pct(before["coverage_adequacy_ratio"]), pct(after["coverage_adequacy_ratio"]), True),
                    _metric("Insurance score", f"{before['insurance_adequacy_score']}/100", f"{after['insurance_adequacy_score']}/100", True)],
    }


def analyze_question(
    text: str,
    health_inputs: dict,
    finance_inputs: dict,
    insurance_inputs: dict,
    health_profile: dict | None = None,
    health_assess: Callable[[dict], dict] | None = None,
    focus: str | None = None,
) -> list[dict]:
    """Return computed scenarios for concrete changes mentioned in the text (empty if none).

    For follow-ups, ``text`` is the whole thread context and ``focus`` the latest message:
    the intent (EMI, purchase, ...) comes from the context, amounts prefer the latest message.
    """
    t = text.lower()
    f = (focus or text).lower()
    amounts = money_amounts(f) or money_amounts(t)
    scenarios: list[dict] = []

    monthly = re.search(r"\bemi\b|per month|a month|monthly|/\s*month|\bp\.?m\.?\b", t)
    income_word = re.search(r"\b(salary|income|pay|job)\b", t)
    up = re.search(r"\b(increas\w*|hike\w*|rais\w*|up|more|higher|gain\w*|grow\w*)\b", t)
    down = re.search(r"\b(cut\w*|drop\w*|decreas\w*|reduc\w*|lose|losing|lost|loss|less|lower\w*|fall\w*)\b", t)
    insurance_word = re.search(r"\b(sum insured|cover|coverage|policy|insurance|premium|top-?up|term plan|riders?)\b", t)
    # Money going into savings or investments is not a purchase or a loan.
    saving_plan = re.search(r"\b(sip|fd|fixed deposit|invest\w*|deposit|mutual funds?|save|saving)\b", f)
    loan_word = re.search(r"\b(emi|loan|financ\w*|instal\w*)\b|\bpay (?:it )?over\b", t)
    buy_word = re.search(r"\b(buy\w*|bought|purchas\w*|afford\w*|spend\w*|cost\w*|pay|worth|trips?|vacations?|holidays?"
                         r"|travel|renovat\w*|lend|wedding|treatment|surgery|operation|car|bike|scooter|house|flat|phone|laptop|gold)\b", t)
    expense_word = re.search(r"\b(rent|expenses?|membership|fees|bills?|subscription|groceries|maid|tuition)\b", t)

    if re.search(r"\b(lose|lost) (my )?job\b|\bjob loss\b|\blaid off\b|\bunemploy|\bstop working\b"
                 r"|\bwithout (?:a |my )?(salary|income|job)\b|\bno (salary|income)\b", t):
        scenarios.append(_income_scenario(0, finance_inputs, "Job loss"))
    elif income_word and (up or down) and not monthly:
        percent = re.search(r"(\d+(?:\.\d+)?)\s*%", t)
        current = finance_inputs["income"]
        if percent:
            delta = current * float(percent.group(1)) / 100
        elif amounts:
            delta = amounts[0] if amounts[0] < current * 3 else amounts[0] - current
        else:
            delta = 0
        if delta:
            new_income = current - delta if down and not up else current + delta
            scenarios.append(_income_scenario(new_income, finance_inputs, f"Income {inr(new_income)}/month"))
    elif insurance_word and not re.search(r"\b(costs?|costing|bills?|emi|loan|treatment|surgery|operation)\b", t):
        # Only amounts that describe cover count ("8 lakh savings" is not cover; premiums are below 1 lakh).
        cover_text = re.sub(r"[\d,.]+\s*(?:k|lakhs?|lac|crore|cr)?\s+(?:in\s+)?savings?", " ", t)
        cover_amounts = [a for a in money_amounts(cover_text) if a >= 100_000]
        # Employer/group cover sits beside the personal policy, so its amount is not a new sum insured.
        if cover_amounts and not re.search(r"\b(term plan|term insurance|life cover|employer|company|office|group)\b", t):
            adds = re.search(r"\b(increase|add|extra|additional|top-?up|by)\b", t) and not re.search(r"\bto\b", t)
            target = insurance_inputs["sum_insured"] + cover_amounts[-1] if adds else cover_amounts[-1]
            finance_profile = FinanceTwin().assess(finance_inputs)
            scenario = _insurance_scenario(target, insurance_inputs, health_profile, finance_profile) \
                if target != insurance_inputs["sum_insured"] else None
            if scenario:
                scenarios.append(scenario)
    elif saving_plan:
        pass
    elif monthly and amounts and expense_word and not loan_word:
        scenarios.append(_expense_scenario(amounts[0], finance_inputs, down and not up))
    elif monthly and amounts and (loan_word or buy_word):
        # "bike for 1.2 lakh on EMI of 4000": the amount right after "EMI" is the instalment.
        # For follow-ups ("what about 10k?") the latest message's own amount wins.
        source = f if re.search(r"\bemi\b", f) or money_amounts(f) else t
        emi_word = re.search(r"\bemi\b", source)
        after_emi = money_amounts(source[emi_word.end():]) if emi_word else []
        amount = after_emi[0] if after_emi else amounts[0]
        months = tenure_months(f) or tenure_months(t)
        # An "EMI" larger than monthly income is really the item's cost.
        if amount >= finance_inputs["income"]:
            scenarios.append(_emi_scenario(t, amount / months, finance_inputs) if months else _purchase_scenario(amount, finance_inputs))
        else:
            scenarios.append(_emi_scenario(t, amount, finance_inputs))
    elif amounts and (loan_word or buy_word) and not re.search(r"\binterest\b", t):
        cost = max(amounts)
        months = tenure_months(t)
        if months and loan_word:
            scenarios.append(_emi_scenario(t, cost / months, finance_inputs))
        else:
            scenarios.append(_purchase_scenario(cost, finance_inputs))

    health_changes: dict = {}
    kg = re.search(r"\b(lose|lost|losing|reduce|drop|cut|shed|gain|put on)\s+(\d+(?:\.\d+)?)\s*(kg|kgs|kilos?)\b", t)
    if kg:
        sign = 1 if kg.group(1) in ("gain", "put on") else -1
        health_changes["weight_kg"] = round(health_inputs["weight_kg"] + sign * float(kg.group(2)), 1)
    bp = re.search(r"\b(\d{2,3})\s*/\s*(\d{2,3})\b", t)
    if bp and 70 <= int(bp.group(1)) <= 250:
        health_changes["ap_hi"], health_changes["ap_lo"] = int(bp.group(1)), int(bp.group(2))
    if re.search(r"\b(quit|stop|give up)\s+(smoking|cigarettes?)", t):
        health_changes["smoke"] = 0
    if re.search(r"\b(quit|stop|give up)\s+(drinking|alcohol)", t):
        health_changes["alco"] = 0
    if re.search(r"\b(start|begin|regular(ly)?)\s+(exercis|walk|gym|running|workout)|\bexercise daily\b|\bget active\b", t):
        health_changes["active"] = 1
    if health_changes:
        scenarios.append(_health_scenario(health_changes, health_inputs, health_profile, health_assess))

    return scenarios[:2]
