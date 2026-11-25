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


_FOOD_PATHWAYS = {
    "weight": r"fast food|junk|fried|oily|sweets?|desserts?|ice ?creams?|chocolates?|sugar\w*|soft drinks?|soda|cola"
              r"|pizzas?|burgers?|fries|overeat\w*|snack\w*|bakery|cakes?|pastr\w*|alcohol|beer|mithai"
              r"|rice|white bread|maida|refined\w*|noodles|biryani",
    "bp": r"fast food|junk|salt\w*|pickles?|chips|namkeen|processed|instant noodles|pizzas?|burgers?|fries|alcohol|beer",
    "cholesterol": r"fast food|junk|fried|oily|butter|ghee|red meat|cheese|pizzas?|burgers?|fries|bakery|pastr\w*",
    "glucose": r"sweets?|desserts?|ice ?creams?|chocolates?|sugar\w*|soft drinks?|soda|cola|juices?|cakes?|pastr\w*|mithai"
               r"|rice|white bread|maida|refined\w*|biryani",
}
_HEALTHY_FOOD = r"vegetables?|salads?|fruits?|whole grains?|millets?|oats|sprouts|home[- ]cooked|healthy (?:food|diet|eating)"
_REDUCING = r"\b(stop\w*|quit\w*|avoid\w*|reduc\w*|cut\w*|less|fewer|give up|limit\w*|skip\w*)\b"
# Typical extra kcal per serving (Indian/US food composition references); most specific first.
_SERVING_KCAL = [
    (r"ice ?creams?", 270, "2-scoop serving"), (r"biryani", 500, "plate"), (r"pizzas?", 600, "3 slices"),
    (r"burgers?", 500, "burger"), (r"fries", 350, "medium portion"), (r"fast food|junk", 500, "meal"),
    (r"chocolates?", 230, "bar"), (r"cakes?|pastr\w*", 350, "slice"), (r"sweets?|mithai|desserts?", 300, "serving"),
    (r"soft drinks?|soda|cola", 140, "330 ml can"), (r"juices?", 120, "glass"), (r"beer", 200, "pint"),
    (r"alcohol", 150, "drink"), (r"chips|namkeen", 250, "packet"), (r"fried|oily|snack\w*", 300, "serving"),
    (r"rice", 200, "extra cup cooked"), (r"white bread|maida|noodles", 200, "serving"), (r"sugar\w*", 50, "2 teaspoons"),
]
# Hall et al. (Lancet 2011): ~0.45 kg eventual change per 10 kcal/day, about half of it within the first year.
_KG_PER_KCAL_DAY_YEAR = 0.0225


def _estimate_intake(t: str) -> dict | None:
    food = next(((pattern, kcal, serving) for pattern, kcal, serving in _SERVING_KCAL if re.search(rf"\b(?:{pattern})\b", t)), None)
    if not food:
        return None
    count = re.search(r"\b(\d+(?:\.\d+)?)\s*(scoops?|cups?|servings?|plates?|slices?|bars?|packets?|cans?|glasses?"
                      r"|pieces?|bottles?|pints?|meals?)\b", t)
    if count:
        servings = float(count.group(1)) / (2 if count.group(2).startswith("scoop") else 1)
    else:
        servings = 2.0 if re.search(r"\b(excess\w*|a lot|lots|too much|heavy|huge|large)\b", t) else 1.0
    per_day = re.search(r"\b(\d+)\s*times? (?:a|per) day\b", t)
    per_week = re.search(r"\b(\d+)\s*(?:times?|days?) (?:a|per|every) week\b", t)
    if per_day or re.search(r"\b(twice|thrice) (?:a|per) day\b", t):
        weekly = 7 * (int(per_day.group(1)) if per_day else 2 if "twice" in t else 3)
    elif per_week:
        weekly = int(per_week.group(1))
    elif re.search(r"\b(daily|every ?day|each day|per day|a day)\b", t):
        weekly = 7
    elif re.search(r"\b(once a week|weekly)\b", t):
        weekly = 1
    elif re.search(r"\bweekends?\b", t):
        weekly = 2
    elif re.search(r"\b(once a month|monthly)\b", t):
        weekly = 0.25
    else:
        weekly = None
    return {"kcal_serving": food[1], "serving": food[2], "servings": servings, "weekly": weekly or 3,
            "frequency_assumed": weekly is None,
            "kcal_day": food[1] * servings * (weekly or 3) / 7}


def lifestyle_pathways(text: str, health_inputs: dict, health_profile: dict | None,
                       health_assess: Callable[[dict], dict] | None) -> dict | None:
    """Score sensitivity for habits the models can't take directly, via the measurable factors they act through."""
    t = text.lower()
    if not health_assess:
        return None
    matched = {k for k, p in _FOOD_PATHWAYS.items() if re.search(rf"\b(?:{p})\b", t)}
    favourable = bool(re.search(_REDUCING, t))
    if not matched and re.search(rf"\b(?:{_HEALTHY_FOOD})\b", t):
        matched, favourable = {"weight", "bp", "cholesterol"}, True
    if not matched:
        return None
    sign = -1 if favourable else 1
    word = "down" if favourable else "up"
    steps = []
    intake = _estimate_intake(t) if "weight" in matched else None
    if intake:
        kg = round(min(15.0, max(0.5, intake["kcal_day"] * _KG_PER_KCAL_DAY_YEAR)) * 2) / 2
        if favourable:
            kg = min(kg, max(0.0, health_inputs["weight_kg"] - 18.5 * (health_inputs["height_cm"] / 100) ** 2))
        if kg:
            steps.append((f"Weight {'-' if favourable else '+'}{kg:g} kg after ~1 year",
                          {"weight_kg": round(health_inputs["weight_kg"] + sign * kg, 1)}, False))
    elif "weight" in matched:
        steps.append((f"Weight {'-' if favourable else '+'}3 kg", {"weight_kg": round(health_inputs["weight_kg"] + sign * 3, 1)}, True))
    if "bp" in matched:
        steps.append((f"Blood pressure {word} 10/5 mmHg",
                      {"ap_hi": health_inputs["ap_hi"] + sign * 10, "ap_lo": health_inputs["ap_lo"] + sign * 5}, True))
    if "cholesterol" in matched:
        level = min(3, max(1, health_inputs["cholesterol"] + sign))
        if level != health_inputs["cholesterol"]:
            steps.append((f"Cholesterol {word} one category", {"cholesterol": level}, True))
    if "glucose" in matched:
        glucose = health_inputs.get("blood_glucose_level", 90)
        steps.append((f"Fasting glucose {word} 15 mg/dL", {"blood_glucose_level": max(70, glucose + sign * 15)}, True))
    if not steps:
        return None

    before = health_profile or health_assess(health_inputs)
    score = before["overall_health_score"]
    metrics, facts = [], []
    for label, change, example in steps:
        after = health_assess({**health_inputs, **change})
        metrics.append(_metric(f"{'Example: ' if example else ''}{label} → health score", f"{score}/100",
                               f"{after['overall_health_score']}/100", after["overall_health_score"] >= score))
        facts.append(f"If {label[0].lower()}{label[1:]}: health score {score} → {after['overall_health_score']}/100, "
                     f"cardiovascular model {before['cardio_risk']['probability'] * 100:.1f}% → "
                     f"{after['cardio_risk']['probability'] * 100:.1f}%")
    combined = {k: v for _, change, _ in steps for k, v in change.items()}
    after = health_assess({**health_inputs, **combined})
    if len(steps) > 1:
        metrics.append(_metric("All of these together → health score", f"{score}/100",
                               f"{after['overall_health_score']}/100", after["overall_health_score"] >= score))
    b, a = before["cardio_risk"]["probability"], after["cardio_risk"]["probability"]
    metrics.append(_metric("Cardiovascular model estimate", f"{b * 100:.1f}%", f"{a * 100:.1f}%", a <= b))
    metrics.append(_metric("BMI", f"{before['bmi']}", f"{after['bmi']}", abs(after["bmi"] - 22) <= abs(before["bmi"] - 22)))
    metrics.append(_metric("Blood pressure", before["hypertension_stage"], after["hypertension_stage"], None))
    metrics.append(_metric("Glucose indicator", before["diabetes_indicator"], after["diabetes_indicator"], None))
    facts.append(f"All together: health score {score} → {after['overall_health_score']}/100, "
                 f"cardiovascular model {b * 100:.1f}% → {a * 100:.1f}%")
    assumptions = []
    if intake and not steps[0][2]:
        frequency = ("3 times a week (frequency not given; tell me how often)" if intake["frequency_assumed"]
                     else f"{intake['weekly']:g} times a week")
        assumptions.append(
            f"Weight estimated from about {intake['kcal_day']:.0f} {'fewer' if favourable else 'extra'} kcal/day: "
            f"{intake['kcal_serving']} kcal per {intake['serving']} × {intake['servings']:g} per occasion × {frequency}, "
            "using the NIH weight-change rule (about 1 kg per 45 kcal/day after a year). Bodies vary.")
    if any(example for _, _, example in steps):
        assumptions.append("Rows marked 'Example' use illustrative sizes the models can't derive from food. "
                           "Not a prediction or diagnosis.")
    return {
        "kind": "pathway",
        "verdict": "conditional",
        "headline": ("Weight estimated from your intake; other rows are examples" if intake and not steps[0][2]
                     else "Example shifts (illustrative sizes, not predicted from your intake)"),
        "facts": facts,
        "actions": [],
        "assumptions": assumptions,
        "metrics": metrics,
    }


_LOWERING = r"\b(reduc\w*|cut\w*|limit\w*|lower\w*|avoid\w*|less|below|under|restrict\w*|keep|stop\w*|quit\w*|minimi[sz]\w*)\b"
_ADVICE_RIDERS = {"critical illness": "Critical Illness Rider", "hospital cash": "Hospital Cash Rider",
                  "personal accident": "Personal Accident Rider", "diabetes care": "Diabetes Care Rider"}


def advice_to_changes(advice: str, health: dict, finance: dict, insurance: dict) -> list[dict]:
    """Turn one piece of advice into twin input changes; each says whether its value is stated or assumed."""
    t = advice.lower().replace("**", "")
    lowering = re.search(_LOWERING, t)
    changes: list[dict] = []

    def add(domain: str, field: str, label: str, current, target, basis: str) -> None:
        if target is not None and not any(c["field"] == field for c in changes):
            changes.append({"domain": domain, "field": field, "label": label, "current": current,
                            "target": target, "basis": basis, "already": target == current})

    if re.search(r"\b(quit\w*|stop\w*|give up|avoid\w*|cessation)\b.*\b(smok\w*|cigarettes?|tobacco)|\bsmoking cessation\b", t):
        add("health", "smoke", "Smoking", health["smoke"], 0, "stated in advice")
    if re.search(r"\b(quit\w*|stop\w*|give up|avoid\w*|cut\w*|limit\w*|reduc\w*|abstain\w*)\b.*\b(alcohol|drink\w*|beer|liquor)", t):
        add("health", "alco", "Alcohol use", health["alco"], 0, "stated in advice")
    if re.search(r"\b(exercis\w*|walk\w*|physical activity|gym|yoga|cycl\w*|swim\w*|jog\w*|aerobic|workouts?|brisk)\b", t) \
            and not re.search(r"\b(stop|avoid)\w*\s+(exercis|walk)", t):
        add("health", "active", "Physically active", health["active"], 1, "stated in advice")

    height_m = health["height_cm"] / 100
    kg = re.search(r"\b(lose|losing|reduc\w*|drop\w*|shed\w*|cut\w*)\s+(?:about\s+|around\s+|at least\s+)?(\d+(?:\.\d+)?)\s*(kg|kgs|kilos?)\b", t)
    if kg:
        add("health", "weight_kg", "Weight (kg)", health["weight_kg"],
            round(health["weight_kg"] - float(kg.group(2)), 1), "stated in advice")
    elif re.search(r"\b(lose|reduc\w*|bring down)\s+(?:your\s+|some\s+)?weight\b|\bweight loss\b", t) \
            and health["weight_kg"] / height_m ** 2 > 24.9:
        add("health", "weight_kg", "Weight (kg)", health["weight_kg"], round(24.9 * height_m ** 2, 1),
            "assumed: weight for a BMI of 24.9, the top of the healthy range")

    bp = re.search(r"\b(\d{2,3})\s*/\s*(\d{2,3})\b", t)
    if bp and re.search(r"\b(bp|blood pressure|mmhg)\b", t) and int(bp.group(1)) < health["ap_hi"]:
        add("health", "ap_hi", "Systolic blood pressure", health["ap_hi"], int(bp.group(1)), "stated in advice")
        add("health", "ap_lo", "Diastolic blood pressure", health["ap_lo"], min(health["ap_lo"], int(bp.group(2))),
            "stated in advice")
    elif re.search(r"\b(salt|sodium)\b", t) and lowering:
        add("health", "ap_hi", "Systolic blood pressure", health["ap_hi"], health["ap_hi"] - 5,
            "assumed: about 5/3 mmHg lower, a typical effect of cutting salt in trials")
        add("health", "ap_lo", "Diastolic blood pressure", health["ap_lo"], health["ap_lo"] - 3,
            "assumed: about 5/3 mmHg lower, a typical effect of cutting salt in trials")

    glucose = health.get("blood_glucose_level", 90)
    stated_glucose = re.search(r"(?:glucose|sugar)\D{0,30}?(?:below|under|less than|<)\s*(\d{2,3})\s*mg", t)
    if stated_glucose and int(stated_glucose.group(1)) < glucose:
        add("health", "blood_glucose_level", "Blood glucose (mg/dL)", glucose, int(stated_glucose.group(1)) - 1,
            "stated in advice")
    elif re.search(r"\b(sugar\w*|sweets?|refined carb\w*|desserts?|soft drinks?)\b", t) and lowering:
        add("health", "blood_glucose_level", "Blood glucose (mg/dL)", glucose, max(80, glucose - 10),
            "assumed: about 10 mg/dL lower fasting glucose")
    if re.search(r"\b(cholesterol|ldl|saturated|trans fats?|fried|visible fats?|oily)\b", t) and lowering \
            and health["cholesterol"] > 1:
        add("health", "cholesterol", "Cholesterol category", health["cholesterol"], health["cholesterol"] - 1,
            "assumed: one category lower")

    amounts = money_amounts(t)
    monthly_spend = finance["fixed_expenses"] + finance["variable_expenses"]
    months = re.search(r"\b(\d{1,2})\s*(?:-\s*\d{1,2}\s*)?months?\b", t)
    if re.search(r"\bemergency fund\b", t) and months and int(months.group(1)) * monthly_spend > finance["savings_balance"]:
        add("finance", "savings_balance", "Savings balance (₹)", finance["savings_balance"],
            int(months.group(1)) * monthly_spend, "stated in advice")
    if re.search(r"\b(expenses?|spending|discretionary|lifestyle costs?)\b", t) and lowering:
        cut = next((a for a in amounts if a < finance["variable_expenses"]), None)
        add("finance", "variable_expenses", "Monthly variable expenses (₹)", finance["variable_expenses"],
            round(finance["variable_expenses"] - cut) if cut else round(finance["variable_expenses"] * 0.9),
            "stated in advice" if cut else "assumed: a 10% cut in variable spending")
    elif re.search(r"\bsave\b|\bsaving\b", t) and _MONTHLY_WORD.search(t) and amounts and amounts[0] < finance["variable_expenses"]:
        add("finance", "variable_expenses", "Monthly variable expenses (₹)", finance["variable_expenses"],
            round(finance["variable_expenses"] - amounts[0]), "assumed: saved by cutting variable spending")
    emi_target = re.search(r"\bemis?\b.*?\bto\b\s*(?:about\s+)?((?:₹|rs\.?)\s*[\d,]+(?:\.\d+)?\s*(?:k|lakhs?)?)", t)
    if emi_target and money_amounts(emi_target.group(1)) and money_amounts(emi_target.group(1))[0] < finance["emis"]:
        add("finance", "emis", "Monthly EMIs (₹)", finance["emis"], money_amounts(emi_target.group(1))[0], "stated in advice")

    cover = [a for a in amounts if a >= 100_000]
    if cover and re.search(r"\b(sum insured|cover\w*|top-?up|health insurance|policy)\b", t):
        adds = re.search(r"\b(top-?up|add\w*|additional|extra|increase\w* by)\b", t)
        target = insurance["sum_insured"] + cover[0] if adds else max(cover)
        if target > insurance["sum_insured"]:
            add("insurance", "sum_insured", "Health cover (₹)", insurance["sum_insured"], target, "stated in advice")
    held = list(insurance.get("existing_riders", []))
    mentioned = [rider for key, rider in _ADVICE_RIDERS.items() if key in t]
    if mentioned and not re.search(r"\b(drop\w*|remov\w*|cancel\w*|surrender\w*)\b", t):
        explicit = re.search(r"\b(add\w*|buy\w*|get|take|opt\w*|include\w*|rider)\b", t)
        add("insurance", "existing_riders", "Riders", held, held + [r for r in mentioned if r not in held],
            "stated in advice" if explicit else f"assumed: adding the {', '.join(mentioned)}")
    return changes


_MONTHLY_WORD = re.compile(r"per month|a month|monthly|/\s*month|every month", re.IGNORECASE)


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
    else:
        pathway = lifestyle_pathways(t, health_inputs, health_profile, health_assess)
        if pathway:
            scenarios.append(pathway)

    return scenarios[:2]
