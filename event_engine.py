"""
event_engine.py
Detects factual life events in chat ("I bought a car on a ₹15,000 EMI", "I had a
heart attack") and turns them into precise operations on the twin inputs.

Hypotheticals ("if I buy...", "planning to...", "can I...") are ignored here; the
scenario engine handles those.  When an essential number is missing, the event is
returned with a ``needs`` question instead of guessing.
"""

from __future__ import annotations

import re
from copy import deepcopy
from datetime import date

from scenario_engine import MULT_PATTERN, inr, money_amounts, tenure_months

HYPOTHETICAL = re.compile(
    r"\b(if|what if|suppose|planning|plan to|thinking|considering|should i|can i|could i|would|will|"
    r"(?:am|is|are|i'm)\s+going to|want to|wish|hope|afford|maybe|might)\b",
    re.IGNORECASE,
)
ITEMS = r"(car|bike|scooter|motorcycle|house|home|flat|apartment|plot|land|phone|laptop|tv|furniture|vehicle|gold|loan)"
RIDERS = {
    "critical illness": "Critical Illness Rider",
    "hospital cash": "Hospital Cash Rider",
    "personal accident": "Personal Accident Rider",
    "diabetes care": "Diabetes Care Rider",
}
CONDITIONS = [
    (r"heart attack|cardiac arrest|myocardial infarction", "heart_attack", "Heart attack"),
    (r"\bstroke\b", "stroke", "Stroke"),
    (r"angioplasty|bypass surgery|\bstent\b|heart disease|coronary", "heart_disease", "Heart disease"),
    (r"\bcancer\b", "cancer", "Cancer"),
    (r"kidney disease|renal failure|dialysis", "kidney_disease", "Kidney disease"),
    (r"\bdiabetes\b|diabetic", "diabetes", "Diabetes"),
    (r"hypertension|high blood pressure|high bp", "hypertension", "Hypertension"),
]
_MONTHLY = re.compile(r"per month|a month|monthly|/\s*month|\bp\.?m\.?\b|every month", re.IGNORECASE)
FAMILY = re.compile(
    r"\b(mother|mom|mum|father|dad|papa|parents?|brother|sister|wife|husband|son|daughter|grand\w+|uncle|aunt|"
    r"friend|family history|relative|cousin|in-laws?)\b",
    re.IGNORECASE,
)
_LENDERS = (r"aunt|aunty|auntie|uncle|mother|mom|mum|father|dad|papa|parents|brother|sister|friend|cousin|relative"
            r"|in-laws?|grandfather|grandmother|grandpa|grandma|boss|colleague|neighbou?r")


def _statement_part(sentence: str) -> str | None:
    """The factual part of a sentence: whole if it is a statement, the lead clause of "fact, question?"."""
    if not (HYPOTHETICAL.search(sentence) or sentence.rstrip().endswith("?")):
        return sentence
    head = re.split(r",\s+", sentence, maxsplit=1)[0]
    if head == sentence or HYPOTHETICAL.search(head) or re.match(r"\s*(is|are|am|do|does|how|what|which|why|when|who|can|should)\b", head, re.IGNORECASE):
        return None
    return head


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?;])\s+|\s+(?:and then|also|and)\s+(?=i\b)", text) if s.strip()]


def _amount_after(sentence: str, pattern: str) -> float | None:
    m = re.search(rf"(?:{pattern})" + r"\D{0,25}?(?P<amount>(?:₹|rs\.?|inr)?\s*\d[\d,]*(?:\.\d+)?\s*(?:" + MULT_PATTERN + r")?)\b", sentence, re.IGNORECASE)
    if not m:
        return None
    found = money_amounts(m.group("amount"))
    return found[0] if found else None


def _op(domain: str, field: str, mode: str, value) -> dict:
    return {"domain": domain, "field": field, "mode": mode, "value": value}


def _event(kind: str, summary: str, ops: list[dict], commitment: dict | None = None, needs: str | None = None,
           log: bool = False) -> dict:
    """``log`` marks a timeline-only event (e.g. a fever) that is worth recording but changes no inputs."""
    e = {"type": kind, "summary": summary, "ops": ops, "commitment": commitment, "needs": needs, "log": log}
    e["domains"] = event_domains(e)
    return e


# Twins an event type belongs to even when its ops touch only one domain (a paid surgery is health + finance).
TYPE_DOMAINS = {
    "condition": {"health"}, "illness": {"health"}, "weight": {"health"}, "bp": {"health"}, "glucose": {"health"},
    "habit": {"health"}, "medical_bill": {"health", "finance"}, "loan": {"finance"}, "purchase": {"finance"},
    "loan_closed": {"finance"}, "income": {"finance"}, "expense": {"finance"}, "spend": {"finance"},
    "savings": {"finance"}, "emis": {"finance"}, "borrowed": {"finance"}, "repayment": {"finance"},
    "lent": {"finance"}, "subscription": {"finance"}, "cover": {"insurance"}, "premium": {"insurance", "finance"},
    "rider": {"insurance"}, "life_cover": {"insurance"}, "policy": {"insurance"}, "settled": {"finance"},
}
TWIN_ORDER = ("health", "finance", "insurance")


def event_domains(event: dict) -> list[str]:
    found = {op["domain"] for op in event.get("ops", [])} | TYPE_DOMAINS.get(event.get("type", ""), set())
    if re.search(r"medical|medicine|hospital|surgery|doctor|treatment|gym|fitness", event.get("summary", ""), re.IGNORECASE):
        found.add("health")
    return [d for d in TWIN_ORDER if d in found] or ["finance"]


def _add_months(start: date, months: int) -> str:
    y, m = divmod(start.month - 1 + months, 12)
    return date(start.year + y, m + 1, min(start.day, 28)).isoformat()


def _purchase(s: str, today: date) -> dict | None:
    item_m = re.search(r"\b(bought|purchased|took|got|financed|booked)\b.*?\b" + ITEMS + r"\b", s, re.IGNORECASE)
    # A bare "EMI" only means a new loan when the sentence says one was taken.
    if not item_m and not re.search(r"\b(took|taken|started|new)\b.*\b(emi|loan)\b", s, re.IGNORECASE):
        return None
    if re.search(r"\b(closed|paid off|cleared|finished|completed|foreclosed)\b", s, re.IGNORECASE):
        return None
    item = item_m.group(2).lower() if item_m else "loan"
    emi = _amount_after(s, r"\bemi\b") or next((a for a in money_amounts(s) if _MONTHLY.search(s)), None)
    months = tenure_months(s)
    down = _amount_after(s, r"down ?payment|paid upfront|upfront")
    amounts = [a for a in money_amounts(s) if a not in (emi, down)]
    cost = max(amounts) if amounts else None
    label = item if item != "loan" else "a loan"

    if emi is None and cost and months and re.search(r"\b(loan|emi|financ)", s, re.IGNORECASE):
        emi = round(cost / months)
    cash = re.search(r"\b(cash|full payment|paid fully|from (my )?savings|outright)\b", s, re.IGNORECASE)

    if emi is None and cash and cost:
        return _event("purchase", f"Bought {label} for {inr(cost)} (paid from savings)",
                      [_op("finance", "savings_balance", "add", -cost)])
    if emi is None:
        return _event("purchase", f"Bought {label}" + (f" for {inr(cost)}" if cost else ""), [],
                      needs=f"Did you take a loan for the {label}? If so, what is the monthly EMI and for how many months? "
                            "If you paid in full, say 'paid from savings'.")
    ops = [_op("finance", "emis", "add", emi)]
    if down:
        ops.append(_op("finance", "savings_balance", "add", -down))
    summary = f"Took {label} on EMI of {inr(emi)}/month" + (f" for {months} months" if months else "")
    if cost:
        summary += f" (cost {inr(cost)})"
    commitment = {"item": item, "emi": emi, "months": months, "start": today.isoformat(),
                  "end": _add_months(today, months) if months else None}
    return _event("loan", summary, ops, commitment=commitment)


def _emi_total(s: str) -> dict | None:
    m = re.search(r"\b(?:my|total)\s+(?:total\s+)?emis?\s+(?:is|are)\s+(?:now\s+)?", s, re.IGNORECASE)
    amounts = money_amounts(s[m.end():]) if m else []
    if not amounts:
        return None
    return _event("emis", f"Total EMIs now {inr(amounts[0])}/month", [_op("finance", "emis", "set", amounts[0])])


def _savings(s: str) -> dict | None:
    lowered = s.lower()
    balance = re.search(r"\b(savings|bank balance|balance)\b\s+(?:is|are|stands at)\s+(?:now\s+)?", lowered)
    if balance and money_amounts(lowered[balance.end():]):
        value = money_amounts(lowered[balance.end():])[0]
        return _event("savings", f"Savings now {inr(value)}", [_op("finance", "savings_balance", "set", value)])
    windfall = re.search(r"\b(bonus|inheritance|inherited|windfall|gift|maturity|refund)\b", lowered)
    if windfall and money_amounts(lowered) and not _MONTHLY.search(lowered) and "no claim" not in lowered:
        value = money_amounts(lowered)[0]
        return _event("savings", f"Received {inr(value)} ({windfall.group(1)}) into savings",
                      [_op("finance", "savings_balance", "add", value)])
    return None


def _spend(s: str) -> dict | None:
    lowered = s.lower()
    if not re.search(r"\b(spent|paid)\b", lowered) or _MONTHLY.search(lowered):
        return None
    if re.search(r"\b(emi|loan|premium|rent|medical|hospital|surgery|doctor|treatment|bill|angioplasty|operation"
                 r"|procedure|medicines?|therapy)\b", lowered):
        return None
    amounts = money_amounts(lowered)
    if not amounts:
        return None
    purpose = re.search(r"\b(?:on|for)\s+(?:my\s+|a\s+|the\s+)?([\w' ]{3,30})$", lowered)
    what = f" on {purpose.group(1).strip()}" if purpose else ""
    return _event("spend", f"Spent {inr(amounts[0])}{what} from savings", [_op("finance", "savings_balance", "add", -amounts[0])])


def _borrowed(s: str, previous_text: str | None) -> dict | None:
    """Money borrowed from family/friends ("took it from my aunt"): it funds the spend, so savings are restored."""
    m = re.search(r"\b(?:took|borrowed|got|taken)\b.*?\bfrom (?:my |our |a )?(?P<who>" + _LENDERS + r")\b", s, re.IGNORECASE)
    if not m:
        return None
    who = m.group("who").lower()
    amounts = money_amounts(s) or (money_amounts(previous_text) if previous_text and re.search(r"\b(it|that|the money|this)\b", s, re.IGNORECASE) else [])
    if not amounts:
        return _event("borrowed", f"Borrowed money from {who}", [], needs=f"How much did you borrow from your {who}?")
    principal = amounts[0]
    return _event("borrowed", f"Borrowed {inr(principal)} from {who} (informal loan)",
                  [_op("finance", "savings_balance", "add", principal)],
                  commitment={"item": f"loan from {who}", "lender": who, "principal": principal, "emi": 0, "informal": True})


def _repayment(s: str, commitments: list[dict], today: date) -> dict | None:
    """A decided repayment plan ("I'll pay my aunt back within 3 months") turns an informal debt into a monthly outflow."""
    m = re.search(r"\b(?:i'?ll|ill|i will|i am going to|i'm going to|planning to|plan to)\s+(?:re)?pay\s+(?:back\s+)?(?:my |the |our )?"
                  r"(?P<who>" + _LENDERS + r")\b", s, re.IGNORECASE)
    if not m:
        return None
    who = m.group("who").lower()
    debt = next((c for c in reversed(commitments) if c.get("informal") and c.get("lender") == who), None)
    months = tenure_months(s)
    principal = (money_amounts(s) or [None])[0] or (debt or {}).get("principal")
    if not principal:
        return _event("repayment", f"Repaying {who}", [], needs=f"How much do you owe your {who}, and over how many months will you repay?")
    if not months:
        return _event("repayment", f"Repaying {who}", [], needs=f"Over how many months will you repay the {inr(principal)} to your {who}?")
    emi = round(principal / months)
    return _event("repayment", f"Repaying {who} {inr(emi)}/month for {months} months ({inr(principal)})",
                  [_op("finance", "emis", "add", emi)],
                  commitment={"item": f"repay {who}", "lender": who, "emi": emi, "months": months, "principal": principal,
                              "settles": who, "start": today.isoformat(), "end": _add_months(today, months)})


def _lent(s: str) -> dict | None:
    m = re.search(r"\b(?:lent|loaned|gave)\b.*?\b(?:to\s+)?(?:my |a |our )?(?P<who>" + _LENDERS + r")\b", s, re.IGNORECASE)
    if not m or (m.group(0).lower().startswith("gave") and not re.search(r"\b(loan|lend|lent|borrow|return|back)\b", s, re.IGNORECASE)):
        return None
    amounts = money_amounts(s)
    who = m.group("who").lower()
    if not amounts:
        return _event("lent", f"Lent money to {who}", [], needs=f"How much did you lend your {who}?")
    return _event("lent", f"Lent {inr(amounts[0])} to {who} (to be returned)",
                  [_op("finance", "savings_balance", "add", -amounts[0])],
                  commitment={"item": f"lent to {who}", "lender": who, "principal": amounts[0], "emi": 0, "receivable": True})


_SUBSCRIPTIONS = (r"netflix|prime|hotstar|spotify|youtube premium|ott|subscription|membership|broadband|wifi|internet"
                  r"|mobile plan|newspaper|magazine|cloud storage|icloud|chatgpt|tuition|coaching|course|classes")


def _subscription(s: str) -> dict | None:
    m = re.search(r"\b(subscribed|signed up|took|got|joined|bought|started|renewed|cancell?ed|stopped|unsubscribed)\b.*?\b(?P<what>"
                  + _SUBSCRIPTIONS + r")\b", s, re.IGNORECASE)
    if not m:
        return None
    what = m.group("what").lower()
    stopping = m.group(1).lower() in ("cancelled", "canceled", "stopped", "unsubscribed")
    amounts = money_amounts(s)
    if not amounts:
        # Subscriptions are often below the generic ₹500 floor for bare numbers ("119 a month").
        small = re.search(r"(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(?:rs|rupees|/-)?\s*(?:a|per|/|every|each)\s*(?:month|year|annum)"
                          r"|\b(?:of|for|costs?|at|₹|rs\.?)\s*(\d+(?:\.\d+)?)\b", s, re.IGNORECASE)
        if small:
            amounts = [float(small.group(1) or small.group(2))]
    if not amounts:
        if stopping:
            return _event("subscription", f"Cancelled {what}", [], needs=f"How much per month was the {what}?")
        return _event("subscription", f"Started {what}", [], needs=f"How much does the {what} cost per month (or per year)?")
    monthly = amounts[0] / 12 if re.search(r"\b(year|yearly|annual\w*|per annum|p\.?a\.?)\b", s, re.IGNORECASE) else amounts[0]
    sign = -1 if stopping else 1
    return _event("subscription", f"{'Cancelled' if stopping else 'Started'} {what} ({inr(monthly)}/month)",
                  [_op("finance", "variable_expenses", "add", sign * round(monthly))])


ILLNESSES = [
    (r"dengue|malaria|typhoid|covid|corona|chikungunya|jaundice|pneumonia|tuberculosis|\btb\b", "infection"),
    (r"fever|flu|viral|cold and cough|infection", "fever / infection"),
    (r"fracture\w*|broke my|sprain\w*|injur\w*|accident", "injury"),
    (r"hospitali[sz]ed|admitted|icu|emergency room|\ber\b", "hospital stay"),
    (r"migraine|food poisoning|stomach infection|kidney stone|appendicitis|asthma attack|allergy", "acute illness"),
    (r"depression|anxiety|panic attack|burnout", "mental health"),
]


def _illness(s: str) -> dict | None:
    """Short-term health episodes: logged on the timeline (they don't change long-term risk inputs)."""
    lowered = s.lower()
    if FAMILY.search(lowered) or not re.search(r"\b(had|got|have|caught|suffered|was|were|been|diagnosed|admitted|broke|fractured|met with|recovered)\b", lowered):
        return None
    for pattern, label in ILLNESSES:
        m = re.search(pattern, lowered)
        if m:
            days = re.search(r"(\d+)\s*(days?|weeks?)", lowered)
            span = f" for {days.group(0)}" if days else ""
            return _event("illness", f"Health episode: {m.group(0)}{span} ({label})", [], log=True)
    return None


POLICY_TYPES = [
    ("vehicle", r"(?:bike|car|two[- ]?wheeler|scooter|motor(?:cycle)?|vehicle|auto)\s+(?:insurance|policy|cover)", "{w} insurance"),
    ("life", r"term (?:plan|insurance|policy)|life (?:insurance|cover|policy)|lic (?:policy|plan)|endowment|ulip", "{w}"),
    ("home", r"(?:home|house|property|fire|flat)\s+(?:insurance|policy|cover)", "{w} insurance"),
    ("travel", r"travel\s+(?:insurance|policy|cover)", "Travel insurance"),
    ("gadget", r"(?:phone|mobile|gadget|laptop)\s+(?:insurance|protection|policy)", "{w} insurance"),
]


def _policy(s: str, insurance: dict, today: date) -> dict | None:
    """Non-health policies (vehicle, life, home, travel, gadget): bought, renewed or cancelled."""
    lowered = s.lower()
    for kind, pattern, label in POLICY_TYPES:
        m = re.search(rf"\b(?P<w>{pattern})\b", lowered)
        if not m:
            continue
        word = m.group("w").split()[0]
        name = label.format(w=word.capitalize()) if "{w}" in label else label
        if label == "{w}":
            name = m.group("w").capitalize()
        existing = next((p for p in insurance.get("policies", []) if p.get("type") == kind
                         and p.get("name", "").split()[0].lower() == name.split()[0].lower()), None)
        if re.search(r"\b(cancell?ed|stopped|surrendered|lapsed|expired|sold)\b", lowered):
            if not existing:
                return _event("policy", f"{name} ended", [], log=True)
            return _event("policy", f"{name} ended", [_op("insurance", "policies", "remove", existing)])
        if not re.search(r"\b(bought|took|got|renewed|purchased|started|added|have|activated)\b", lowered):
            return None
        premium = _amount_after(lowered, r"premium(?: of| is)?")
        amounts = [a for a in money_amounts(lowered) if a != premium]
        cover = max(amounts) if amounts and (len(amounts) > 1 or kind in ("life", "home") or amounts[0] >= 100_000) else None
        if premium is None:
            small = [a for a in amounts if a != cover]
            premium = small[0] if small else None
        policy = {"type": kind, "name": name, "cover": cover or 0, "premium": premium or 0,
                  "renewal_date": _add_months(today, 12)}
        ops = ([_op("insurance", "policies", "remove", existing)] if existing else []) + [_op("insurance", "policies", "append", policy)]
        verb = "Renewed" if existing or "renew" in lowered else "Took"
        details = ", ".join(x for x in (f"cover {inr(cover)}" if cover else "", f"premium {inr(premium)}/yr" if premium else "") if x)
        return _event("policy", f"{verb} {name}" + (f" ({details})" if details else "") + f", renews {policy['renewal_date']}",
                      ops, commitment={"item": name, "policy_type": kind, "premium": premium or 0,
                                       "renewal_date": policy["renewal_date"], "emi": 0, "policy": True})
    return None


def _settled(s: str, commitments: list[dict]) -> dict | None:
    """Informal debts paid back ("I paid back my aunt") or money returned to the user ("my friend returned the 50k")."""
    lowered = s.lower()
    back = re.search(r"\b(?:paid|repaid|returned|gave)\b.*?\b(?:back\s+)?(?:to\s+)?(?:my |our )?(?P<who>" + _LENDERS + r")\b.*?\b(back|in full|fully|off)\b"
                     r"|\b(?:repaid|paid off|cleared|settled)\b.*?\b(?:my |our )?(?P<who2>" + _LENDERS + r")\b", lowered)
    returned = re.search(r"\b(?:my |our )?(?P<who>" + _LENDERS + r")\b.*?\b(returned|paid me back|gave (?:me )?back|repaid me|settled)\b", lowered)
    if returned and not back:
        who = returned.group("who")
        owed = next((c for c in reversed(commitments) if c.get("receivable") and c.get("lender") == who), None)
        amount = (money_amounts(lowered) or [None])[0] or (owed or {}).get("principal")
        if not amount:
            return _event("settled", f"{who.capitalize()} returned money", [], needs=f"How much did your {who} return?")
        return _event("settled", f"{who.capitalize()} returned {inr(amount)}", [_op("finance", "savings_balance", "add", amount)],
                      commitment={"item": f"lent to {who}", "emi": 0, "closed": True})
    if not back:
        return None
    who = back.group("who") or back.group("who2")
    plan = next((c for c in reversed(commitments) if c.get("settles") == who), None)
    debt = next((c for c in reversed(commitments) if c.get("informal") and c.get("lender") == who), None)
    if plan:
        return _event("settled", f"Finished repaying {who}", [_op("finance", "emis", "add", -plan["emi"])],
                      commitment={"item": plan["item"], "emi": plan["emi"], "closed": True, "settles": who})
    amount = (money_amounts(lowered) or [None])[0] or (debt or {}).get("principal")
    if not amount:
        return _event("settled", f"Paid back {who}", [], needs=f"How much did you pay back to your {who}?")
    return _event("settled", f"Paid back {inr(amount)} to {who}", [_op("finance", "savings_balance", "add", -amount)],
                  commitment={"item": f"loan from {who}", "emi": 0, "closed": True, "settles": who})


def _loan_closed(s: str, commitments: list[dict]) -> dict | None:
    if not re.search(r"\b(closed|paid off|cleared|finished|completed|foreclosed|repaid)\b.*\b(loan|emi)\b|\b(loan|emi)\b.*\b(closed|over|finished|completed|ended)\b",
                     s, re.IGNORECASE):
        return None
    emi = _amount_after(s, r"\bemi\b") or (money_amounts(s) or [None])[0]
    item_m = re.search(ITEMS, s, re.IGNORECASE)
    if emi is None:
        matches = [c for c in commitments if item_m and c.get("item") == item_m.group(1).lower()]
        if len(matches) == 1:
            emi = matches[0]["emi"]
    if emi is None:
        return _event("loan_closed", "Closed a loan", [], needs="What was the monthly EMI of the loan you closed?")
    item = item_m.group(1).lower() if item_m else "loan"
    return _event("loan_closed", f"Closed {item} loan (EMI {inr(emi)}/month)",
                  [_op("finance", "emis", "add", -emi)], commitment={"item": item, "emi": emi, "closed": True})


def _income(s: str, finance: dict) -> dict | None:
    if re.search(r"\b(lost my job|laid off|got fired|unemployed|resigned)\b", s, re.IGNORECASE):
        new = _amount_after(s, r"\b(now earn|income is|salary is)")
        if new:
            return _event("income", f"Job change; income now {inr(new)}/month", [_op("finance", "income", "set", new)])
        return _event("income", "Lost job", [], needs="Sorry to hear that. Do you have any monthly income now (even partial)? "
                                                      "Tell me the amount and I'll update your twin.")
    if not re.search(r"\b(salary|income|pay|raise|hike|increment|promot\w*|earn\w*|in-hand)\b", s, re.IGNORECASE):
        return None
    percent = re.search(r"(\d+(?:\.\d+)?)\s*%", s)
    current = finance["income"]
    amounts = money_amounts(s)
    if re.search(r"\b(wife|husband|spouse|partner)\b|\bside (business|income|hustle|job)\b|freelanc|part-time", s, re.IGNORECASE):
        if amounts:
            return _event("income", f"Additional household income {inr(amounts[0])}/month",
                          [_op("finance", "income", "add", amounts[0])])
        return None
    if re.search(r"\bpromot\w*", s, re.IGNORECASE) and not (percent or amounts):
        return _event("income", "Promotion", [], needs="Congratulations! What is your new monthly salary (or the % hike)?")
    extra = re.search(r"\b(extra|more|additional|increase[sd]? by|went up by|up by|plus)\b", s, re.IGNORECASE)
    if amounts and extra and not percent and amounts[0] < current:
        return _event("income", f"Monthly income changed {inr(current)} → {inr(current + amounts[0])}",
                      [_op("finance", "income", "add", amounts[0])])
    to_value = _amount_after(s, r"\b(to|now|is now|became|of)\b")
    stated = _amount_after(s, r"\b(?:salary|income|in-hand(?: salary)?)\s+(?:is|of)\b|\bi\s+(?:now\s+)?earn\b")
    if percent and re.search(r"\b(raise|hike|increment|promotion|increased|went up|up)\b", s, re.IGNORECASE):
        new = round(current * (1 + float(percent.group(1)) / 100))
    elif percent and re.search(r"\b(cut|reduced|decreased|went down|dropped)\b", s, re.IGNORECASE):
        new = round(current * (1 - float(percent.group(1)) / 100))
    elif to_value and re.search(r"\b(now|is now|increased to|went up to|became|reduced to|dropped to|new salary)\b", s, re.IGNORECASE):
        new = to_value
    elif stated:
        new = stated
    elif money_amounts(s) and re.search(r"\b(raise|hike|increment)\b", s, re.IGNORECASE):
        new = current + money_amounts(s)[0]
    else:
        return None
    return _event("income", f"Monthly income changed {inr(current)} → {inr(new)}", [_op("finance", "income", "set", new)])


def _expenses(s: str, finance: dict) -> dict | None:
    medical = re.search(r"\b(medical|medicines?|medications?|treatment|hospital|doctor|therapy|health|surgery|operation"
                        r"|angioplasty|procedure)\b.*\b(costs?|bills?|expenses?|spend\w*|paid)", s, re.IGNORECASE)
    expense = re.search(r"\b(rent|expenses?|spending|bills?|school fees|fees|groceries)\b", s, re.IGNORECASE)
    if not (medical or expense) or re.search(r"\b(premium|sum insured|credit card)\b", s, re.IGNORECASE):
        return None
    amounts = money_amounts(s)
    if not amounts:
        if medical and re.search(r"\b(increas\w*|went up|rose|risen|higher|more)\b", s, re.IGNORECASE):
            return _event("expense", "Medical costs increased", [],
                          needs="By how much per month did your medical costs go up (or what was the one-time bill)?")
        return None
    amount = amounts[0]
    rising = re.search(r"\b(increas\w*|went up|rose|risen|higher|more|up by)\b", s, re.IGNORECASE)
    one_time = medical and not _MONTHLY.search(s) and (
        re.search(r"\b(spent|paid|bill was|bill of|cost me|one[- ]time|lump ?sum|once)\b", s, re.IGNORECASE)
        # A "monthly" rise larger than the whole income, or a cost stated without any rise, is a single bill.
        or amount >= finance["income"]
        or not rising
    )
    if one_time:
        return _event("medical_bill", f"Paid a one-time medical bill of {inr(amount)} from savings",
                      [_op("finance", "savings_balance", "add", -amount)])
    field = "fixed_expenses" if re.search(r"\b(rent|school fees|fees|bills?)\b", s, re.IGNORECASE) and not medical else "variable_expenses"
    down = re.search(r"\b(decreased|reduced|went down|dropped|lower|cut)\b", s, re.IGNORECASE)
    if re.search(r"\b(to|now|is now)\b", s, re.IGNORECASE) and not re.search(r"\bby\b", s, re.IGNORECASE) and field == "fixed_expenses":
        item = re.search(r"\b(rent|school fees|fees|bills?)\b", s, re.IGNORECASE).group(1).lower()
        # Fixed expenses hold more than this one item, so the change is needed, not the new total.
        return _event("expense", f"{item.capitalize()} changed to {inr(amount)}/month", [],
                      needs=f"What was your {item} before (or by how much per month did it change)?")
    sign = -1 if down else 1
    what = "Medical costs" if medical else "Monthly expenses"
    return _event("expense", f"{what} {'down' if down else 'up'} by {inr(amount)}/month",
                  [_op("finance", field, "add", sign * amount)])


def _health(s: str, health: dict) -> list[dict]:
    events = []
    lowered = s.lower()
    diagnosed = re.search(r"\b(had|suffered|survived|diagnosed|detected|got|have|underwent|went through)\b"
                          r"|\bafter (?:my|a|the)\b|\b(?:i am|i'm)\s+(?:now\s+)?(?:a\s+)?(?:diabetic|hypertensive)\b", lowered)
    # A relative's illness is family history, not the user's own condition.
    own = not FAMILY.search(lowered)
    for pattern, code, label in CONDITIONS:
        if own and diagnosed and re.search(pattern, lowered) and code not in health.get("conditions", []):
            events.append(_event("condition", f"{label} recorded in medical history", [_op("health", "conditions", "append", code)]))
    kg = re.search(r"\b(lost|gained|put on|reduced|dropped)\s+(\d+(?:\.\d+)?)\s*(kg|kgs|kilos?)\b", lowered)
    weight_now = re.search(r"\bweight is (now )?(\d+(?:\.\d+)?)\s*(kg|kgs)\b", lowered)
    if kg:
        sign = 1 if kg.group(1) in ("gained", "put on") else -1
        events.append(_event("weight", f"Weight {'+' if sign > 0 else '-'}{kg.group(2)} kg",
                             [_op("health", "weight_kg", "add", sign * float(kg.group(2)))]))
    elif weight_now:
        events.append(_event("weight", f"Weight now {weight_now.group(2)} kg", [_op("health", "weight_kg", "set", float(weight_now.group(2)))]))
    bp = re.search(r"\b(bp|blood pressure)\b.*?\b(\d{2,3})\s*/\s*(\d{2,3})\b", lowered)
    if bp:
        events.append(_event("bp", f"Blood pressure now {bp.group(2)}/{bp.group(3)}",
                             [_op("health", "ap_hi", "set", int(bp.group(2))), _op("health", "ap_lo", "set", int(bp.group(3)))]))
    sugar = re.search(r"\b(sugar|glucose)\b.*?\b(\d{2,3})\b", lowered)
    a1c = re.search(r"\b(?:hba1c|a1c|hb a1c)\b\D{0,25}?(\d{1,2}(?:\.\d)?)\b", lowered)
    if a1c and 3 <= float(a1c.group(1)) <= 18:
        events.append(_event("glucose", f"HbA1c now {a1c.group(1)}%", [_op("health", "hba1c", "set", float(a1c.group(1)))]))
    if sugar and re.search(r"\b(is|was|now|came)\b", lowered):
        events.append(_event("glucose", f"Fasting glucose now {sugar.group(2)} mg/dL",
                             [_op("health", "blood_glucose_level", "set", int(sugar.group(2)))]))
    for verb, value, label in ((r"(quit|stopped|gave up)", 0, "Quit"), (r"(started|began|picked up)", 1, "Started")):
        if re.search(rf"\b{verb}\s+(smoking|cigarettes?)", lowered):
            events.append(_event("habit", f"{label} smoking", [_op("health", "smoke", "set", value)]))
        if re.search(rf"\b{verb}\s+(drinking|alcohol)", lowered):
            events.append(_event("habit", f"{label} drinking", [_op("health", "alco", "set", value)]))
    if re.search(r"\b(started|began|joined)\s+(going to\s+)?(a\s+|an\s+|the\s+)?(exercis\w*|gym|walking|running|yoga|working out|swimming|cycling|jogging)", lowered):
        events.append(_event("habit", "Started regular exercise", [_op("health", "active", "set", 1)]))
    elif re.search(r"\b(stopped|quit)\s+(going to\s+)?(the\s+)?(exercis\w*|gym|walking|running|working out|yoga)", lowered):
        events.append(_event("habit", "Stopped exercising", [_op("health", "active", "set", 0)]))
    return events


def _insurance(s: str, insurance: dict) -> list[dict]:
    lowered = s.lower()
    events = []
    for key, rider in RIDERS.items():
        if re.search(rf"\b(removed|dropped|cancelled|canceled|discontinued|stopped)\b.*{key}", lowered):
            if rider in insurance.get("existing_riders", []):
                events.append(_event("rider", f"Removed {rider}", [_op("insurance", "existing_riders", "remove", rider)]))
        elif re.search(rf"\b(added|bought|took|got)\b.*{key}", lowered) and rider not in insurance.get("existing_riders", []):
            events.append(_event("rider", f"Added {rider}", [_op("insurance", "existing_riders", "append", rider)]))
    riders_found = bool(events)
    if not riders_found and re.search(r"\b(no|don't have|do not have|without)\s+(any\s+)?(health\s+)?insurance\b", lowered):
        return [_event("cover", "No health insurance", [_op("insurance", "sum_insured", "set", 0),
                                                          _op("insurance", "annual_premium", "set", 0)])]
    if not riders_found and re.search(r"\b(cancell?ed|stopped|discontinued|surrendered|lost)\b.*\b(insurance|policy|cover)\b"
                                      r"|\b(policy|insurance|cover)\b.*\b(lapsed|got cancell?ed|was cancell?ed|cancell?ed|terminated|expired)\b", lowered):
        return [_event("cover", "Health policy stopped", [],
                       needs="Do you have any other health cover now? If yes, what is its sum insured; if not, I'll set your cover to ₹0.")]
    cover_m = re.search(r"\b(sum insured|cover(?:age)?|policy)\b", lowered)
    changed = re.search(r"\b(increased|raised|upgraded|switched|changed|reduced|is now|now|became)\b", lowered)
    cover_amounts = [a for a in money_amounts(lowered) if a >= 50_000]
    if cover_m and changed and cover_amounts:
        if re.search(r"\bby\b", lowered):
            return events + [_event("cover", f"Sum insured up by {inr(cover_amounts[0])}",
                                    [_op("insurance", "sum_insured", "add", cover_amounts[0])])]
        return events + [_event("cover", f"Sum insured now {inr(cover_amounts[-1])}",
                                [_op("insurance", "sum_insured", "set", cover_amounts[-1])])]
    new_policy = not riders_found and re.search(r"\b(bought|took|got)\b.*\b(health insurance|insurance|policy|cover)\b", lowered)
    premium = _amount_after(lowered, r"premium (is now|increased to|is|of|now)")
    premium_pct = re.search(r"premium\D{0,25}?(increased|raised|hiked|went up|reduced|decreased|cut)\D{0,10}?(\d+(?:\.\d+)?)\s*%"
                            r"|(increased|raised|hiked|reduced|decreased|cut)\s+(?:the\s+|my\s+)?premium\s+by\s+(\d+(?:\.\d+)?)\s*%", lowered)
    if new_policy:
        amounts = [a for a in money_amounts(lowered) if a != premium]
        if amounts:
            events.append(_event("cover", f"New policy adds {inr(max(amounts))} cover",
                                 [_op("insurance", "sum_insured", "add", max(amounts))]))
        else:
            events.append(_event("cover", "Bought a new policy", [], needs="What is the sum insured and the annual premium of the new policy?"))
    if premium:
        yearly = premium * 12 if _MONTHLY.search(lowered) else premium
        events.append(_event("premium", f"Annual premium now {inr(yearly)}", [_op("insurance", "annual_premium", "set", yearly)]))
    elif premium_pct:
        word = premium_pct.group(1) or premium_pct.group(3)
        rate = float(premium_pct.group(2) or premium_pct.group(4)) / 100
        sign = -1 if word in ("reduced", "decreased", "cut") else 1
        yearly = round(insurance["annual_premium"] * (1 + sign * rate))
        events.append(_event("premium", f"Annual premium now {inr(yearly)}", [_op("insurance", "annual_premium", "set", yearly)]))
    return events


def detect_events(
    text: str,
    health: dict,
    finance: dict,
    insurance: dict,
    commitments: list[dict] | None = None,
    today: date | None = None,
    previous_text: str | None = None,
) -> list[dict]:
    """Factual life events in the text, each with input operations or a ``needs`` question.

    ``previous_text`` (the user's last message) resolves references like "I took it from my aunt".
    """
    today = today or date.today()
    current = {"health": health, "finance": finance, "insurance": insurance}
    events: list[dict] = []
    for sentence in _sentences(text):
        # A decided repayment plan is stated in future tense but is a commitment, not a what-if.
        plan = _repayment(sentence, commitments or [], today)
        if plan:
            events.append(plan)
            continue
        s = _statement_part(sentence)
        if s is None:
            continue
        borrowed = _settled(s, commitments or []) or _borrowed(s, previous_text) or _lent(s)
        if borrowed:
            events.append(borrowed)
            continue
        sub = _subscription(s)
        if sub:
            events.append(sub)
            events.extend(_health(s, health))
            continue
        life = _policy(s, insurance, today)
        if life:
            events.append(life)
            continue
        for found in (_loan_closed(s, commitments or []), _purchase(s, today), _emi_total(s), _income(s, finance),
                      _savings(s), _expenses(s, finance), _spend(s)):
            if found:
                events.append(found)
                if found["type"] in ("loan_closed", "loan", "purchase", "emis"):
                    break
        health_events = _health(s, health)
        events.extend(health_events)
        episode = _illness(s)
        if episode and not any(e["type"] == "condition" for e in health_events):
            events.append(episode)
        events.extend(_insurance(s, insurance))
    for e in events:
        c = e.get("commitment") or {}
        if (c.get("informal") or c.get("receivable")) and not c.get("since"):
            c["since"] = today.isoformat()
    # Restating a value the twin already has ("my premium is 18000") is not an update.
    return [e for e in events if not e["ops"] or any(
        op["mode"] != "set" or current[op["domain"]].get(op["field"]) != op["value"] for op in e["ops"]
    )]


REVERT = re.compile(
    r"\b(undo|revert|roll ?back|reverse|take back|that (?:was|is) (?:wrong|a mistake|incorrect)|that's (?:wrong|incorrect)"
    r"|(?:i )?(?:didn't|did not|never) (?:actually )?(?:buy|bought|take|took|have|had|get|got|purchase)"
    r"|cancel (?:that|it|the (?:last )?update)|delete (?:that|the (?:last )?update)|never happened|ignore (?:that|my last))\b",
    re.IGNORECASE,
)
# Words that point at a stored event, mapped to text found in its summary/commitment.
_REVERT_TARGETS = {
    r"car": "car", r"bike|scooter|motorcycle": "bike|scooter|motorcycle", r"house|home|flat": "house|home|flat",
    r"loan|emi": "emi|loan", r"heart attack": "heart attack", r"stroke": "stroke", r"diabet\w*": "diabetes",
    r"cancer": "cancer", r"hypertension|bp|blood pressure": "hypertension|blood pressure", r"smok\w*": "smoking",
    r"drink\w*": "drinking", r"exercis\w*|gym|yoga|walk\w*": "exercise", r"weight|kg": "weight",
    r"sugar|glucose": "glucose", r"salary|income|hike|job": "income|job", r"medical|medicine\w*|hospital|bill": "medical",
    r"rent|expenses?": "expense|rent", r"savings?|bonus": "savings|received", r"riders?": "rider",
    r"cover|sum insured|policy|insurance": "sum insured|policy|insurance", r"premium": "premium", r"spent|wedding": "spent",
}


def detect_revert(text: str, live_events: list[dict], last_turn_ids: list[int]) -> dict | None:
    """Revert intent in a chat message: which stored events to undo, or a question if unclear.

    ``live_events`` are stored, not-yet-undone events ({id, summary, type, commitment}) oldest first.
    """
    if not REVERT.search(text):
        return None
    lowered = text.lower()
    if not live_events:
        return {"ids": [], "needs": "There are no recorded updates to revert yet."}
    by_id = re.findall(r"#\s*(\d+)", text)
    if by_id:
        ids = [int(i) for i in by_id if any(e["id"] == int(i) for e in live_events)]
        return {"ids": ids, "needs": None if ids else "That update was already reverted or doesn't exist."}
    if re.search(r"\b(everything|all (?:the |my )?(?:updates|changes|events)|all of (?:it|them))\b", lowered):
        return {"ids": [e["id"] for e in live_events], "needs": None}
    patterns = [summary_re for word_re, summary_re in _REVERT_TARGETS.items() if re.search(rf"\b(?:{word_re})\b", lowered)]
    if patterns:
        def matches(e: dict) -> bool:
            hay = f"{e['summary']} {(e.get('commitment') or {}).get('item', '')}".lower()
            return any(re.search(p, hay) for p in patterns)
        found = [e for e in live_events if matches(e)]
        if found:
            # "the car loan" means the latest matching event, unless the user asks for all of them.
            return {"ids": [e["id"] for e in found] if re.search(r"\ball\b", lowered) else [found[-1]["id"]], "needs": None}
        options = "; ".join(e["summary"] for e in live_events[-5:])
        return {"ids": [], "needs": f"I couldn't find that update. Recent updates you can revert: {options}. Which one?"}
    recent = [i for i in last_turn_ids if any(e["id"] == i for e in live_events)]
    return {"ids": recent or [live_events[-1]["id"]], "needs": None}


def complete_pending(
    previous_query: str,
    text: str,
    health: dict,
    finance: dict,
    insurance: dict,
    commitments: list[dict] | None = None,
    today: date | None = None,
) -> list[dict]:
    """Events completed by a short reply ("6000 per month") to the advisor's missing-detail question."""
    joined = re.sub(r"[.!?\s]+$", "", previous_query) + ", " + text
    return [e for e in detect_events(joined, health, finance, insurance, commitments, today) if not e["needs"]]


def apply_ops(health: dict, finance: dict, insurance: dict, ops: list[dict]) -> tuple[dict, dict, dict]:
    """Return new input dicts with the operations applied (values clamped to valid ranges)."""
    out = {"health": deepcopy(health), "finance": deepcopy(finance), "insurance": deepcopy(insurance)}
    for op in ops:
        target = out[op["domain"]]
        field = op["field"]
        if op["mode"] == "set":
            target[field] = op["value"]
        elif op["mode"] == "add":
            target[field] = target.get(field, 0) + op["value"]
        elif op["mode"] == "append":
            target[field] = [*target.get(field, []), op["value"]]
        elif op["mode"] == "remove":
            target[field] = [v for v in target.get(field, []) if v != op["value"]]
    f = out["finance"]
    for field in ("fixed_expenses", "variable_expenses", "emis", "savings_balance"):
        f[field] = max(0, round(f[field], 2))
    f["income"] = max(1, f["income"])
    out["health"]["weight_kg"] = max(25, out["health"]["weight_kg"])
    out["insurance"]["sum_insured"] = max(0, out["insurance"]["sum_insured"])
    return out["health"], out["finance"], out["insurance"]


def active_commitments(events: list[dict], today: date | None = None, include_ended: bool = False) -> list[dict]:
    """EMIs and debts still running, from the stored life-event payloads (oldest first).

    ``include_ended`` keeps plans whose end date has passed (the dues engine flags those as overdue).
    """
    today_iso = (today or date.today()).isoformat()
    active: list[dict] = []
    for e in events:
        c = e.get("commitment") or {}
        # Policies are tracked from the insurance inputs, not as running commitments.
        if e.get("undone") or not c or c.get("policy"):
            continue
        if c.get("closed"):
            for i, a in enumerate(active):
                if a["item"] == c["item"] and abs(a["emi"] - c["emi"]) < 1:
                    active.pop(i)
                    break
            if c.get("settles"):
                active = [a for a in active if not (a.get("informal") and a.get("lender") == c["settles"])]
            continue
        if c.get("settles"):
            active = [a for a in active if not (a.get("informal") and a.get("lender") == c["settles"])]
        if include_ended or not c.get("end") or c["end"] >= today_iso:
            active.append(c)
    return active


def _months_between(start: date, end: date) -> int:
    return (end.year - start.year) * 12 + end.month - start.month - (end.day < start.day)


def compute_dues(events: list[dict], insurance: dict, today: date | None = None) -> list[dict]:
    """Payment and renewal schedule with status: upcoming, due_soon, overdue, outstanding, expired, missing.

    ``events`` are stored life-event payloads (with ``created_at`` ISO strings); there is no payment
    ledger, so instalments are scheduled monthly from the start date and only plans past their end,
    debts without a plan, or lapsed policies are flagged as overdue.
    """
    today = today or date.today()
    dues: list[dict] = []
    for c in active_commitments(events, today, include_ended=True):
        if c.get("informal") or c.get("receivable"):
            since = date.fromisoformat(c.get("since") or today.isoformat())
            age = (today - since).days
            if c.get("receivable"):
                dues.append({"kind": "receivable", "domain": "finance", "title": f"{c['lender'].capitalize()} owes you",
                             "amount": c.get("principal", 0), "due_date": None, "since": since.isoformat(),
                             "status": "outstanding" if age >= 30 else "upcoming",
                             "detail": f"Lent {age} days ago" if age else "Lent today"})
            else:
                dues.append({"kind": "debt", "domain": "finance", "title": f"Owed to {c['lender']}",
                             "amount": c.get("principal", 0), "due_date": None, "since": since.isoformat(),
                             "status": "outstanding" if age >= 30 else "upcoming",
                             "detail": "No repayment plan yet. Tell the advisor how you'll repay it."})
            continue
        if not c.get("emi") or not c.get("start"):
            continue
        start = date.fromisoformat(c["start"])
        end = date.fromisoformat(c["end"]) if c.get("end") else None
        title = c["item"].capitalize() + (" EMI" if not c["item"].startswith("repay") else "")
        if end and end < today:
            dues.append({"kind": "instalment", "domain": "finance", "title": title, "amount": c["emi"], "due_date": end.isoformat(),
                         "status": "overdue", "detail": f"Plan ended {end.isoformat()}. If it's fully paid, tell the advisor it's closed."})
            continue
        paid_months = max(0, _months_between(start, today))
        nxt = date.fromisoformat(_add_months(start, paid_months + 1))
        if nxt <= today:
            nxt = date.fromisoformat(_add_months(start, paid_months + 2))
        days = (nxt - today).days
        remaining = (c.get("months") or 0) - paid_months - 1 if c.get("months") else None
        dues.append({"kind": "instalment", "domain": "finance", "title": title, "amount": c["emi"], "due_date": nxt.isoformat(),
                     "status": "due_soon" if days <= 5 else "upcoming",
                     "detail": f"Monthly until {end.isoformat()}" + (f" ({remaining} after this)" if remaining is not None else "")
                     if end else "Monthly, tenure not recorded"})
    for p in insurance.get("policies", []):
        if not p.get("renewal_date"):
            continue
        renew = date.fromisoformat(p["renewal_date"])
        days = (renew - today).days
        status = "expired" if days < 0 else "due_soon" if days <= 30 else "upcoming"
        dues.append({"kind": "renewal", "domain": "insurance", "title": f"{p['name']} renewal", "amount": p.get("premium", 0),
                     "due_date": renew.isoformat(), "status": status,
                     "detail": f"Expired {-days} days ago; you may be uninsured" if days < 0 else f"Renews in {days} days"})
    vehicles = {c["item"] for c in active_commitments(events, today, include_ended=True) if c.get("item") in ("car", "bike", "scooter", "motorcycle", "vehicle")}
    vehicles |= {re.search(r"\b(car|bike|scooter|motorcycle)\b", e.get("summary", "").lower()).group(1)
                 for e in events if not e.get("undone") and e.get("type") == "purchase"
                 and re.search(r"\b(car|bike|scooter|motorcycle)\b", e.get("summary", "").lower())}
    covered = {p.get("name", "").split()[0].lower() for p in insurance.get("policies", []) if p.get("type") == "vehicle"}
    for v in sorted(vehicles):
        if v not in covered and not ({"bike", "scooter", "motorcycle"} & {v} and covered & {"bike", "scooter", "two-wheeler", "two"}):
            dues.append({"kind": "missing_policy", "domain": "insurance", "title": f"No insurance recorded for your {v}",
                         "amount": 0, "due_date": None, "status": "missing",
                         "detail": "Third-party motor insurance is mandatory in India. Tell the advisor if you already have it."})
    order = {"overdue": 0, "expired": 1, "missing": 2, "outstanding": 3, "due_soon": 4, "upcoming": 5}
    return sorted(dues, key=lambda d: (order[d["status"]], d["due_date"] or "9999"))
