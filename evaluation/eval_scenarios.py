"""
eval_scenarios.py
Behaviour bank of everyday questions and statements for each twin plus interlinked ones.

Each case states what the advisor's deterministic layers must do: which twins answer
(routing), which life events get recorded (none for questions or plans), whether a
missing detail must be asked, and which what-if calculation runs.  Gemini only words
the answer from these results, so this bank checks the decisions that make answers right.

Run:  python -m evaluation.eval_scenarios   (from the project root; prints per-domain accuracy and every failure)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from event_engine import complete_pending, detect_events
from orchestrator import Orchestrator


@dataclass(frozen=True)
class Case:
    domain: str
    text: str
    route: str  # letters h/f/i of the twins that must answer
    events: tuple[str, ...] = ()
    needs: bool = False
    scenario: str | None = None
    prev: str | None = None
    prev_pending: bool = False


def _cases(domain: str, rows: list[tuple]) -> list[Case]:
    out = []
    for row in rows:
        text, route, *rest = row
        opts = rest[0] if rest else {}
        out.append(Case(domain, text, route, **opts))
    return out


HEALTH = _cases("health", [
    ("How is my heart doing?", "h"),
    ("what is my bmi", "h"),
    ("Am I overweight?", "h"),
    ("Is my blood pressure normal?", "h"),
    ("My bp is 140/90, is that bad?", "h", {"events": ("bp",)}),
    ("I feel weak, suggest me something", "h"),
    ("I feel tired all the time", "h"),
    ("I get dizzy when I stand up", "h"),
    ("I have a headache since morning", "h"),
    ("I have chest pain while climbing stairs", "h"),
    ("I can't sleep properly at night", "h"),
    ("I'm feeling very stressed lately", "h"),
    ("what should I eat to lower my sugar", "h"),
    ("Give me a diet plan", "h"),
    ("How many steps should I walk daily?", "h"),
    ("Is running good for me?", "h"),
    ("how much exercise do i need per week", "h"),
    ("Am I at risk of diabetes?", "h"),
    ("what is my cardiovascular risk", "h"),
    ("Why is my health score low?", "h"),
    ("What is driving my heart risk?", "h"),
    ("How can I reduce my cholesterol?", "h"),
    ("Is my glucose level fine?", "h"),
    ("my sugar levels are high what to do", "h"),
    ("Should I quit smoking?", "h", {"scenario": "health"}),
    ("What happens if I quit smoking?", "h", {"scenario": "health"}),
    ("If I lose 5 kg what will change?", "h", {"scenario": "health"}),
    ("What if I start exercising daily?", "h", {"scenario": "health"}),
    ("if my bp becomes 120/80 how much does my risk drop", "h", {"scenario": "health"}),
    ("How much weight should I lose?", "h"),
    ("What is my ideal weight?", "h"),
    ("is drinking alcohol bad for my heart", "h"),
    ("Should I stop drinking?", "h", {"scenario": "health"}),
    ("I quit smoking last month", "h", {"events": ("habit",)}),
    ("I have stopped smoking", "h", {"events": ("habit",)}),
    ("I lost 4 kg this month", "h", {"events": ("weight",)}),
    ("I gained 3 kg after Diwali", "h", {"events": ("weight",)}),
    ("My weight is now 68 kg", "h", {"events": ("weight",)}),
    ("My BP is now 128/82", "h", {"events": ("bp",)}),
    ("my blood pressure came down to 125/80", "h", {"events": ("bp",)}),
    ("My fasting sugar was 110 today", "h", {"events": ("glucose",)}),
    ("My glucose is 95 now", "h", {"events": ("glucose",)}),
    ("I started going to the gym", "h", {"events": ("habit",)}),
    ("I joined a yoga class", "h", {"events": ("habit",)}),
    ("I started walking every morning", "h", {"events": ("habit",)}),
    ("I stopped going to the gym", "h"),  # persona is already inactive: nothing to change
    ("I was diagnosed with diabetes", "h", {"events": ("condition",)}),
    ("Doctor said I have high blood pressure", "h", {"events": ("condition",)}),
    ("I had a stroke last year", "h", {"events": ("condition",)}),
    ("I had a heart attack", "h", {"events": ("condition",)}),
    ("I underwent angioplasty last week", "h", {"events": ("condition",)}),
    ("I've been diagnosed with cancer", "h", {"events": ("condition",)}),
    ("I am diabetic now", "h", {"events": ("condition",)}),
    ("My father has diabetes, am I at risk?", "h"),
    ("my mother had a heart attack at 50", "h"),
    ("How do I recover after a heart attack?", "h"),
    ("what are the symptoms of diabetes", "h"),
    ("Is 130/85 high blood pressure?", "h", {"scenario": "health"}),
    ("How often should I check my bp?", "h"),
    ("Can stress increase my blood pressure?", "h"),
    ("Which blood tests should I get done?", "h"),
    ("When should I go for a full body checkup?", "h"),
    ("Why is my CVD risk high?", "h"),
    ("Explain my hypertension stage", "h"),
    ("I smoke 10 cigarettes a day, how bad is it?", "h"),
    ("I drink beer every weekend", "h"),
    ("Is my weight okay for my height?", "h"),
    ("How can I improve my health score?", "h"),
    ("what lifestyle changes will help my heart", "h"),
    ("I feel breathless after walking a little", "h"),
    ("I have back pain", "h"),
    ("My knees hurt when I run", "h"),
    ("I have a fever and cough", "h", {"events": ("illness",)}),
    ("I'm feeling anxious and low", "h"),
    ("I'm not feeling well today", "h"),
    ("I eat a lot of junk food", "h"),
    ("Is intermittent fasting good for me?", "h"),
    ("How much water should I drink?", "h"),
    ("What is a good resting heart rate?", "h"),
    ("Should I take vitamin D supplements?", "h"),
    ("my cholesterol report came 240", "h"),
    ("I sleep only 5 hours", "h"),
    ("I sit all day at work, is that harmful?", "h"),
    ("How do I lose belly fat?", "h"),
    ("What should my target BMI be?", "h"),
    ("I have a family history of heart disease", "h"),
    ("I walk 10000 steps daily", "h"),
    ("I burn 500 calories in the gym", "h"),
    ("how many calories should i eat", "h"),
    ("Is my heart risk higher than average for my age?", "h"),
    ("Compare my health now vs last month", "h"),
    ("what if I gain 5 kg", "h", {"scenario": "health"}),
    ("if I sleep 8 hours will my health improve", "h"),
    ("Should I see a cardiologist?", "h"),
    ("I got my HbA1c done, it is 6.2", "h", {"events": ("glucose",)}),
    ("My doctor put me on BP medicines", "h"),
    ("I'm pregnant, what should I take care of?", "h"),
    ("suggest some exercises for a 32 year old", "h"),
    ("My energy is very low these days", "h"),
    ("I keep getting headaches and feel nauseous", "h"),
])

FINANCE = _cases("finance", [
    ("Is my emergency fund enough?", "f"),
    ("How much should I save every month?", "f"),
    ("What is my debt to income ratio?", "f"),
    ("Am I spending too much?", "f"),
    ("How can I reduce my expenses?", "f"),
    ("Can I afford a car?", "f"),
    ("Can I afford a bike for 1.2 lakh?", "f", {"scenario": "purchase"}),
    ("If I take a bike on EMI of 15000 per month for 24 months how will it affect me?", "f", {"scenario": "emi"}),
    ("Should I buy a house worth 60 lakh?", "f", {"scenario": "purchase"}),
    ("What if I buy an iPhone for 80k?", "f", {"scenario": "purchase"}),
    ("Can I go on a Europe trip costing 3 lakh?", "f", {"scenario": "purchase"}),
    ("My salary increased by 10%", "f", {"events": ("income",)}),
    ("I got a 15% hike", "f", {"events": ("income",)}),
    ("My salary is now 1.5 lakh", "f", {"events": ("income",)}),
    ("I lost my job", "f", {"events": ("income",), "needs": True}),
    ("I was laid off yesterday", "f", {"events": ("income",), "needs": True}),
    ("What if I lose my job?", "f", {"scenario": "income"}),
    ("What if my income drops by 20%?", "f", {"scenario": "income"}),
    ("If my salary increases to 1.5 lakh, what changes?", "f", {"scenario": "income"}),
    ("I bought a car for 8 lakh, EMI is 15000 for 5 years", "f", {"events": ("loan",)}),
    ("I purchased a bike for 1.2 lakh paid from savings", "f", {"events": ("purchase",)}),
    ("I took a home loan of 30 lakh for 20 years", "f", {"events": ("loan",)}),
    ("I bought a new phone", "f", {"events": ("purchase",), "needs": True}),
    ("I closed my car loan", "f", {"events": ("loan_closed",), "needs": True}),
    ("I paid off my personal loan of EMI 5000", "f", {"events": ("loan_closed",)}),
    ("My rent increased to 20000", "f", {"events": ("expense",), "needs": True}),
    ("My rent went up by 3000", "f", {"events": ("expense",)}),
    ("My monthly expenses went up by 5000", "f", {"events": ("expense",)}),
    ("My expenses reduced by 4000 per month", "f", {"events": ("expense",)}),
    ("Kids school fees increased by 2000 per month", "f", {"events": ("expense",)}),
    ("I spent 50000 on a wedding", "f", {"events": ("spend",)}),
    ("How long will my savings last if I stop working?", "f", {"scenario": "income"}),
    ("What is my financial stability score?", "f"),
    ("Why is my stability score low?", "f"),
    ("How much EMI can I afford?", "f"),
    ("What's the max loan I can take?", "f"),
    ("Should I prepay my home loan?", "f"),
    ("Is it better to invest in SIP or FD?", "f"),
    ("How much should I invest monthly?", "f"),
    ("Can I start a SIP of 10000 per month?", "f"),
    ("What if my rent goes up by 5000 per month?", "f", {"scenario": "expense"}),
    ("If my expenses increase by 10k a month, am I okay?", "f", {"scenario": "expense"}),
    ("How much cash do I have left each month?", "f"),
    ("Am I saving enough for retirement?", "f"),
    ("How do I build an emergency fund?", "f"),
    ("Is my savings of 4.5 lakh enough?", "f"),
    ("My savings are 5 lakh now", "f", {"events": ("savings",)}),
    ("My bank balance is 2 lakh now", "f", {"events": ("savings",)}),
    ("I got a bonus of 1 lakh", "f", {"events": ("savings",)}),
    ("I received an inheritance of 10 lakh", "f", {"events": ("savings",)}),
    ("Should I take a personal loan for my wedding?", "f"),
    ("Is 36% DTI good?", "f"),
    ("How is my financial health?", "f"),
    ("Give me a monthly budget plan", "f"),
    ("How can I pay off my debt faster?", "f"),
    ("Which loan should I close first?", "f"),
    ("Should I use savings to close my car loan?", "f"),
    ("my credit card bill is 40000 this month", "f"),
    ("I have 3 EMIs running, is that okay?", "f"),
    ("What are my monthly outflows?", "f"),
    ("Will I be able to retire at 50?", "f"),
    ("How much tax will I pay?", "f"),
    ("Should I buy or rent a house?", "f"),
    ("my wife started working and earns 50000", "f", {"events": ("income",)}),
    ("I started a side business earning 20k a month", "f", {"events": ("income",)}),
    ("I got promoted", "f", {"events": ("income",), "needs": True}),
    ("My salary got cut by 10%", "f", {"events": ("income",)}),
    ("Can I afford a 25 lakh house loan for 20 years?", "f", {"scenario": "emi"}),
    ("If I take a loan of 5 lakh for 3 years what would be the EMI?", "f", {"scenario": "emi"}),
    ("What happens if I pay 10000 EMI for a car?", "f", {"scenario": "emi"}),
    ("bike emi 3k for 2 years ok?", "f", {"scenario": "emi"}),
    ("Is it wise to buy a laptop for 70000?", "f", {"scenario": "purchase"}),
    ("I want to buy gold worth 2 lakh", "f", {"scenario": "purchase"}),
    ("Planning to renovate my house for 4 lakh", "f", {"scenario": "purchase"}),
    ("Should I lend 1 lakh to my friend?", "f", {"scenario": "purchase"}),
    ("What if I put 1 lakh in fixed deposit?", "f"),
    ("How much can I spend on a car?", "f"),
    ("Is my income enough for my lifestyle?", "f"),
    ("I want to reduce my EMIs", "f"),
    ("How many months can I survive without salary?", "f", {"scenario": "income"}),
    ("My salary is 80000, what's a good budget?", "f", {"events": ("income",)}),
    ("my in-hand salary is 95000 per month", "f", {"events": ("income",)}),
    ("I earn 1 lakh a month", "f", {"events": ("income",)}),
    ("What will my savings be in 5 years?", "f"),
    ("How much interest will I pay on a 10 lakh loan?", "f"),
    ("Should I break my FD to pay for the car?", "f"),
    ("I have no savings, what should I do?", "f"),
    ("Is 20% savings rate good?", "f"),
    ("What's the 50/30/20 rule?", "f"),
    ("Explain my disposable income", "f"),
    ("I'm getting married next year, how should I plan finances?", "f"),
    ("I paid 30000 for my sister's wedding", "f", {"events": ("spend",)}),
    ("How do I improve my financial stability?", "f"),
    ("My EMI is 8000 right now", "f"),  # equals the stored EMI total: nothing to change
    ("My total EMIs are now 20000", "f", {"events": ("emis",)}),
    ("Should I take a top-up loan?", "f"),
    ("Is a 6 month emergency fund enough?", "f"),
    ("How much will I have saved by December?", "f"),
    ("I want to stop overspending on food delivery", "f"),
    ("My electricity bill went up by 1500 a month", "f", {"events": ("expense",)}),
])

INSURANCE = _cases("insurance", [
    ("Is my insurance cover enough?", "i"),
    ("Which riders am I missing?", "i"),
    ("Should I add a critical illness rider?", "i"),
    ("How much sum insured do I need?", "i"),
    ("What is my insurance adequacy score?", "i"),
    ("Is 5 lakh cover enough for my family?", "i"),
    ("What if I increase my cover to 15 lakh?", "i", {"scenario": "insurance"}),
    ("Should I buy a super top-up of 10 lakh?", "i", {"scenario": "insurance"}),
    ("My premium is 18000 a year, is that too much?", "i"),
    ("I added a critical illness rider", "i", {"events": ("rider",)}),
    ("I bought a personal accident rider", "i", {"events": ("rider",)}),
    ("My sum insured is now 10 lakh", "i", {"events": ("cover",)}),
    ("I increased my cover to 15 lakh", "i", {"events": ("cover",)}),
    ("My premium increased to 22000", "i", {"events": ("premium",)}),
    ("I bought a new health insurance policy of 10 lakh", "i", {"events": ("cover",)}),
    ("I took a family floater health insurance", "i", {"events": ("cover",), "needs": True}),
    ("What is a co-pay?", "i"),
    ("What does waiting period mean in insurance?", "i"),
    ("Does my policy cover pre-existing diseases?", "i"),
    ("Will insurance cover my heart surgery?", "hi"),
    ("Is cashless hospitalization available?", "hi"),
    ("How do I file a claim?", "i"),
    ("My claim got rejected, what now?", "i"),
    ("What is the difference between term and health insurance?", "i"),
    ("Should I buy term insurance?", "i"),
    ("How much life cover do I need?", "i"),
    ("Is my term plan of 1 crore enough?", "i"),
    ("Why is my insurance score low?", "i"),
    ("Do I need a hospital cash rider?", "i"),
    ("Is diabetes care rider useful for me?", "hi"),
    ("What is the projected medical cost in 5 years?", "hfi"),
    ("My premium is 1500 per month", "i"),  # = ₹18,000/yr, the stored premium
    ("I cancelled my health insurance", "i", {"events": ("cover",), "needs": True}),
    ("My policy lapsed", "i", {"events": ("cover",), "needs": True}),
    ("I renewed my policy", "i"),
    ("I ported my policy to another insurer", "i"),
    ("Should I increase my sum insured by 5 lakh?", "i", {"scenario": "insurance"}),
    ("What if my cover is 20 lakh?", "i", {"scenario": "insurance"}),
    ("Is it worth buying insurance at my age?", "i"),
    ("Explain my coverage adequacy ratio", "i"),
    ("What does deductible mean?", "i"),
    ("What is no claim bonus?", "i"),
    ("Does my insurance cover maternity?", "i"),
    ("Is OPD covered in my plan?", "i"),
    ("My employer insurance covers 3 lakh, do I need more?", "i"),
    ("Which is better, 10 lakh cover or 15 lakh?", "i", {"scenario": "insurance"}),
    ("What is the waiting period for pre-existing conditions?", "i"),
    ("I want a policy with lower premium", "i"),
    ("How do riders work?", "i"),
    ("Is my premium too high for my cover?", "i"),
    ("What does my insurance not cover?", "i"),
    ("Should I buy insurance for my parents?", "i"),
    ("My parents are 60, which policy is best for them?", "i"),
    ("Do I need accident insurance?", "i"),
    ("What is critical illness cover?", "i"),
    ("I added critical illness rider and personal accident rider", "i", {"events": ("rider", "rider")}),
    ("I removed the hospital cash rider", "i", {"events": ("rider",)}),
    ("Is 18000 premium reasonable for 5 lakh cover?", "i"),
    ("My insurer increased premium by 10%", "i", {"events": ("premium",)}),
    ("Explain the claim settlement ratio", "i"),
    ("Do I need a super top up?", "i"),
    ("What's the best health insurance for me?", "i"),
    ("How is my insurance doing?", "i"),
    ("Is my family covered?", "i"),
    ("Should I switch insurers?", "i"),
    ("What is room rent capping?", "i"),
    ("Does my policy have a sub-limit?", "i"),
    ("What's the claim process for cashless?", "i"),
    ("How many claims can I make in a year?", "i"),
    ("Is my cover inflation adjusted?", "i"),
    ("I got a new policy from my company with 5 lakh cover", "i", {"events": ("cover",)}),
    ("My sum insured increased by 2 lakh after no claim bonus", "i", {"events": ("cover",)}),
    ("What will happen if I don't renew my policy?", "i"),
    ("Is my premium tax deductible?", "fi"),
    ("How much premium should I pay for 10 lakh cover?", "i", {"scenario": "insurance"}),
    ("Do I need disability insurance?", "i"),
    ("Explain my rider recommendations", "i"),
    ("What is the coverage gap?", "i"),
    ("Why do I need critical illness cover?", "i"),
    ("Can I add my spouse to my policy?", "i"),
    ("Is a 1 crore cover too much?", "i", {"scenario": "insurance"}),
    ("My premium is due next week, should I pay?", "i"),
    ("I switched to a policy with 7 lakh sum insured", "i", {"events": ("cover",)}),
    ("Should I take a separate cover for my parents?", "i"),
    ("What is a family floater?", "i"),
    ("Which rider gives the most value?", "i"),
    ("Does insurance pay for ambulance?", "i"),
    ("Are diagnostics covered?", "i"),
    ("What is the restore benefit?", "i"),
    ("How do I check my policy status?", "i"),
    ("my insurance renewal is coming, should I upgrade?", "i"),
    ("Is daycare treatment covered?", "hi"),
    ("What is the premium for 15 lakh cover?", "i", {"scenario": "insurance"}),
    ("I have no health insurance right now", "i", {"events": ("cover",)}),
    ("What is a policy exclusion?", "i"),
    ("Are my riders worth the premium?", "i"),
    ("Explain my insurance in simple words", "i"),
    ("Should I buy a policy online or through an agent?", "i"),
    ("What is the free look period?", "i"),
    ("Does my plan cover ayush treatment?", "hi"),
])

CROSS = _cases("cross", [
    ("Can I afford a heart treatment costing 3 lakh?", "hfi", {"scenario": "purchase"}),
    ("My surgery will cost 2 lakh, will insurance cover it?", "hfi", {"scenario": "purchase"}),
    ("I had a heart attack and the hospital bill was 4 lakh", "hfi", {"events": ("condition", "medical_bill")}),
    ("I was diagnosed with diabetes, should I add the diabetes care rider?", "hi", {"events": ("condition",)}),
    ("My medical cost increases", "hfi", {"events": ("expense",), "needs": True}),
    ("I quit smoking, will my premium reduce?", "hi", {"events": ("habit",)}),
    ("I lost my job, can I still pay my insurance premium?", "fi", {"events": ("income",), "needs": True}),
    ("Should I use my savings or insurance for the surgery?", "hfi"),
    ("If I take a 15000 EMI, can I still afford my health insurance?", "fi", {"scenario": "emi"}),
    ("I'm diabetic and my medicines cost 3000 a month", "hf", {"events": ("condition", "expense")}),
    ("My dad had a stroke, should I buy a policy for him?", "hi"),
    ("My BP is high, will it affect my insurance?", "hi"),
    ("Given my heart risk, how much cover do I need?", "hi"),
    ("I'm overweight, will my premium be higher?", "hi"),
    ("Can I afford gym membership of 2000 per month?", "hf", {"scenario": "expense"}),
    ("My salary increased by 20%, should I increase my cover?", "fi", {"events": ("income",)}),
    ("I bought a car on EMI of 12000 for 4 years and I had a minor accident", "f", {"events": ("loan", "illness")}),
    ("If I get cancer, can my savings cover the treatment?", "hfi"),
    ("How will a heart attack affect my finances?", "hf"),
    ("Is my emergency fund enough for a medical emergency?", "hf"),
    ("What happens to my finances and health if I lose my job?", "hf", {"scenario": "income"}),
    ("I want to lose 10 kg and save 10000 a month", "hf", {"scenario": "health"}),
    ("Plan for my retirement and health together", "hf"),
    ("I had angioplasty and paid 2.5 lakh from savings", "hf", {"events": ("condition", "medical_bill")}),
    ("My mother is sick, should I pay for her treatment of 1 lakh from savings?", "hfi", {"scenario": "purchase"}),
    ("I started smoking again due to stress", "h"),  # persona already smokes
    ("My company stopped my health insurance and cut my salary by 10%", "fi", {"events": ("income", "cover"), "needs": True}),
    ("what about 10k?", "f", {"prev": "Can I afford a bike EMI of 15000?", "scenario": "emi"}),
    ("How can I improve it?", "h", {"prev": "How is my heart?"}),
    ("how much do they cost?", "i", {"prev": "Which insurance riders am I missing?"}),
    ("around 6000 per month", "hfi", {"prev": "My medical cost increases.", "prev_pending": True, "events": ("expense",)}),
    ("EMI 12000 for 3 years", "f", {"prev": "I bought a car", "prev_pending": True, "events": ("loan",)}),
    ("now I earn 40000 per month", "f", {"prev": "I lost my job", "prev_pending": True, "events": ("income",)}),
    ("what should I eat?", "h", {"prev": "I feel weak"}),
    ("I feel dizzy", "h", {"prev": "Can I afford a bike EMI of 15000?"}),
    ("and what about my savings?", "f", {"prev": "Is my cover enough?"}),
    ("and if I pay it over 5 years?", "f", {"prev": "What if I buy a car for 8 lakh?", "scenario": "emi"}),
    ("thanks", "h", {"prev": "How is my heart?"}),
    ("I'm going to the hospital for a checkup, will insurance pay?", "hfi"),
    ("My dad's surgery cost 3 lakh and I paid it from savings", "hfi", {"events": ("medical_bill",)}),
    ("I got diagnosed with hypertension and my doctor bills are 2000 a month", "hf", {"events": ("condition", "expense")}),
    ("Should I prepay my loan or buy a bigger health cover?", "fi"),
    ("Is it okay to skip insurance and invest the premium?", "fi"),
    ("If my BP is 150/95, will my premium change?", "hi", {"scenario": "health"}),
    ("My weight is 85 kg and BMI 30, can I get insurance?", "hi", {"events": ("weight",)}),
    ("I'm a smoker with 8 lakh savings, how much cover do I need?", "hfi"),
    ("After my heart attack, my medicines cost 5000 every month", "hf", {"events": ("condition", "expense")}),
    ("I have 2 kids and my wife doesn't work, how much life cover do I need?", "i"),
    ("Compare my health, money and insurance status", "hfi"),
    ("My diabetes is under control now, can I reduce my cover?", "hi"),
])

CASES = HEALTH + FINANCE + INSURANCE + CROSS

H = {"age": 32, "gender": "female", "height_cm": 162, "weight_kg": 70, "ap_hi": 135, "ap_lo": 85, "cholesterol": 1,
     "gluc": 1, "smoke": 1, "alco": 0, "active": 0, "blood_glucose_level": 88, "conditions": []}
F = {"income": 120_000, "fixed_expenses": 30_000, "variable_expenses": 25_000, "emis": 8_000, "savings_balance": 450_000}
I = {"sum_insured": 500_000, "annual_premium": 18_000, "annual_income": 1_440_000, "existing_riders": ["Hospital Cash Rider"]}
HEALTH_PROFILE = {"bmi": 26.7, "hypertension_stage": "Stage 1", "overall_health_score": 70,
                  "cardio_risk": {"probability": 0.4, "label": "Moderate"}, "diabetes_indicator": "Low"}
TODAY = date(2026, 11, 24)


def _orchestrator() -> Orchestrator:
    o = Orchestrator.__new__(Orchestrator)
    o.health_inputs, o.finance_inputs, o.insurance_inputs = H, F, I
    o.health_profile, o.health_assess = HEALTH_PROFILE, None
    o._llm_route = lambda q: {"twins": ["<llm fallback>"], "mode": "", "simulate": False}
    return o


def evaluate(case: Case) -> dict:
    """Run one case through routing, event detection and scenario maths, as /query does."""
    o = _orchestrator()
    events = detect_events(case.text, H, F, I, commitments=[], today=TODAY, previous_text=case.prev)
    if not events and case.prev and case.prev_pending:
        events = complete_pending(case.prev, case.text, H, F, I, commitments=[], today=TODAY)
    history = [{"query": case.prev, "answer": "..."}] if case.prev else []
    state = o._route_node({"query": case.text, "history": history})
    state["life_context"] = {
        "just_recorded": [e for e in events if e["ops"] and not e["needs"]],
        "pending_questions": [e["needs"] for e in events if e["needs"]],
    }
    scenarios = o._compute_scenarios(state)
    got = {
        "route": "".join(sorted(t[0] for t in state["routing"]["twins"] if t[0] in "hfi"))
        if "<llm fallback>" not in state["routing"]["twins"] else "<llm>",
        "events": tuple(sorted(e["type"] for e in events)),
        "needs": any(e["needs"] for e in events),
        "scenario": scenarios[0]["kind"] if scenarios else None,
    }
    want = {"route": "".join(sorted(case.route)), "events": tuple(sorted(case.events)),
            "needs": case.needs, "scenario": case.scenario}
    return {"case": case, "got": got, "want": want, "ok": got == want}


def run(cases: list[Case] = CASES) -> list[dict]:
    return [evaluate(c) for c in cases]


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8")
    results = run()
    for domain in ("health", "finance", "insurance", "cross"):
        rs = [r for r in results if r["case"].domain == domain]
        print(f"{domain:10s} {sum(r['ok'] for r in rs):3d}/{len(rs)}")
    print(f"{'total':10s} {sum(r['ok'] for r in results):3d}/{len(results)}\n")
    for r in results:
        if not r["ok"]:
            diff = {k: (r["got"][k], r["want"][k]) for k in r["want"] if r["got"][k] != r["want"][k]}
            prev = f"  [prev: {r['case'].prev}]" if r["case"].prev else ""
            print(f"FAIL {r['case'].domain:9s} {r['case'].text!r}{prev}\n     got/want: {diff}")
