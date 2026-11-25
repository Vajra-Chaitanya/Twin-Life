import pytest

from scenario_engine import advice_to_changes, analyze_question, inr, money_amounts, tenure_months

# Matches the "demo-ananya" persona: DTI (30k + 8k) / 120k = 0.32.
FINANCE = {"income": 120_000, "fixed_expenses": 30_000, "variable_expenses": 25_000, "emis": 8_000, "savings_balance": 450_000}
HEALTH = {
    "age": 32, "gender": "female", "height_cm": 162, "weight_kg": 70, "ap_hi": 135, "ap_lo": 85,
    "cholesterol": 1, "gluc": 1, "smoke": 1, "alco": 0, "active": 0, "blood_glucose_level": 88,
}
INSURANCE = {"sum_insured": 500_000, "annual_premium": 18_000, "annual_income": 1_440_000, "existing_riders": []}


def analyze(text, **kw):
    return analyze_question(text, HEALTH, FINANCE, INSURANCE, **kw)


@pytest.mark.parametrize(
    "text, expected",
    [("EMI of ₹15,000", [15_000]), ("a 1.2 lakh bike", [120_000]), ("15k per month", [15_000]),
     ("for 24 months at 35 kg", []), ("rs 2,50,000 surgery", [250_000])],
)
def test_money_amounts(text, expected):
    assert money_amounts(text) == expected


def test_tenure_and_inr_formatting():
    assert tenure_months("for 2 years") == 24
    assert tenure_months("over 18 months") == 18
    assert inr(1234567) == "₹12,34,567"
    assert inr(-15000) == "-₹15,000"


def _scored(inputs):
    bmi = inputs["weight_kg"] / (inputs["height_cm"] / 100) ** 2
    score = 100 - abs(bmi - 22) * 2 - (inputs["ap_hi"] - 110) / 2 - inputs["cholesterol"] * 3 \
        - max(0, inputs.get("blood_glucose_level", 90) - 90) / 5
    return {"overall_health_score": round(score), "bmi": round(bmi, 1),
            "cardio_risk": {"probability": round(1 - score / 100, 3), "label": "x"},
            "hypertension_stage": "Stage 1" if inputs["ap_hi"] >= 130 else "Normal",
            "diabetes_indicator": "Medium" if inputs.get("blood_glucose_level", 90) >= 100 else "Low"}


def test_fast_food_shows_computed_score_pathways():
    [s] = analyze("What happens if I eat fast food?", health_assess=_scored)
    assert s["kind"] == "pathway" and s["verdict"] == "conditional"
    labels = [m["label"] for m in s["metrics"]]
    assert "Weight +5 kg after ~1 year → health score" in labels
    assert "Example: Blood pressure up 10/5 mmHg → health score" in labels
    assert "Example: Cholesterol up one category → health score" in labels
    together = next(m for m in s["metrics"] if m["label"].startswith("All of these"))
    assert together["better"] is False and together["after"] != together["before"]
    assert "Not a prediction" in s["assumptions"][-1]
    assert "3 times a week (frequency not given" in s["assumptions"][0]


def test_daily_excess_ice_cream_scales_weight_with_intake():
    [s] = analyze("What happens if I eat ice cream daily excessively?", health_assess=_scored)
    labels = [m["label"] for m in s["metrics"]]
    # 270 kcal x 2 servings x 7/week = 540 kcal/day -> ~12 kg after a year.
    assert "Weight +12 kg after ~1 year → health score" in labels
    assert "540 extra kcal/day" in s["assumptions"][0] and "7 times a week" in s["assumptions"][0]
    [once] = analyze("What if I eat 2 scoops of ice cream once a week?", health_assess=_scored)
    assert "Weight +1 kg after ~1 year → health score" in [m["label"] for m in once["metrics"]]


def test_reducing_sugar_is_favourable_and_needs_model():
    [s] = analyze("What if I cut sugar and sweets?", health_assess=_scored)
    assert any(m["label"] == "Example: Fasting glucose down 15 mg/dL → health score" for m in s["metrics"])
    assert analyze("What if I cut sugar?") == []


@pytest.mark.parametrize("advice, field, target, stated", [
    ("Quit smoking immediately to cut cardiac risk.", "smoke", 0, True),
    ("Walk briskly for 30 minutes, 5 days a week.", "active", 1, True),
    ("Keep your salt intake below 5g per day.", "ap_hi", 130, False),
    ("Limit added sugar to under 25g a day.", "blood_glucose_level", 80, False),
    ("Build an emergency fund of 12 months of expenses.", "savings_balance", 660_000, True),
    ("Increase your sum insured to ₹10 lakh.", "sum_insured", 1_000_000, True),
    ("Add a critical illness rider to your policy.", "existing_riders", ["Critical Illness Rider"], True),
])
def test_advice_becomes_twin_changes(advice, field, target, stated):
    changes = {c["field"]: c for c in advice_to_changes(advice, HEALTH, FINANCE, INSURANCE)}
    assert changes[field]["target"] == target
    assert (changes[field]["basis"] == "stated in advice") is stated


def test_advice_without_measurable_change_returns_nothing():
    assert advice_to_changes("Schedule a cardiologist visit and get a lipid profile.", HEALTH, FINANCE, INSURANCE) == []


def test_critical_illness_coverage_review_simulates_rider_or_reports_held():
    advice = "Review your health insurance policy to ensure you have adequate critical illness coverage."
    [change] = advice_to_changes(advice, HEALTH, FINANCE, INSURANCE)
    assert change["target"] == ["Critical Illness Rider"] and change["basis"].startswith("assumed")
    held = {**INSURANCE, "existing_riders": ["Critical Illness Rider"]}
    [met] = advice_to_changes(advice, HEALTH, FINANCE, held)
    assert met["already"] is True


def test_more_rice_flows_through_weight_and_glucose():
    [s] = analyze("What happens if I eat more rice?", health_assess=_scored)
    labels = [m["label"] for m in s["metrics"]]
    assert "Weight +2 kg after ~1 year → health score" in labels and "Example: Fasting glucose up 15 mg/dL → health score" in labels


def test_bike_emi_gives_exact_dti_and_safe_limit():
    [s] = analyze("If I take a bike on EMI of ₹15,000 per month for 24 months how will it affect me?")

    assert s["kind"] == "emi" and s["verdict"] == "risky"
    assert s["metrics"][0] == {"label": "Debt-to-income", "before": "32%", "after": "44%", "better": False}
    # 36% of 120k minus existing 38k fixed+EMI.
    assert any("₹5,200/month" in f for f in s["facts"])
    assert any("total repaid ₹3,60,000" in f for f in s["facts"])
    assert any("₹5,200" in a for a in s["actions"])


def test_cost_and_emi_in_one_question_uses_the_emi_amount():
    [s] = analyze("I'm planning to buy a bike for 1.2 lakh on EMI of 4000. Should I?")
    assert s["kind"] == "emi" and s["headline"] == "₹4,000/month EMI"


def test_no_headroom_advises_against_new_emi_instead_of_zero_emi():
    [s] = analyze_question("EMI of 4000", HEALTH, {**FINANCE, "emis": 23_000}, INSURANCE)
    assert "no comfortable borrowing headroom" in s["actions"][0]
    assert not any("₹0" in a for a in s["actions"])


def test_cost_with_tenure_becomes_emi():
    [s] = analyze("Can I buy a 3 lakh car on loan for 36 months?")
    assert s["kind"] == "emi"
    assert s["headline"] == "₹8,333/month EMI"


def test_large_amount_called_emi_is_treated_as_cost():
    [s] = analyze("bike costing 1.5 lakh on EMI for 12 months")
    assert s["headline"] == "₹12,500/month EMI"


def test_one_time_purchase_uses_savings_and_emergency_fund():
    [s] = analyze("Can I afford a surgery that costs 3 lakh?")
    assert s["kind"] == "purchase"
    # 450k - 300k = 150k over 55k expenses = 2.7 months -> below 3 -> risky.
    assert s["verdict"] == "risky"
    assert any("2.7 months" in f for f in s["facts"])


def test_job_loss_runway():
    [s] = analyze("What happens if I lose my job?")
    assert s["kind"] == "income"
    assert any("7.1 months" in f for f in s["facts"])


def test_salary_hike_percent():
    [s] = analyze("my salary increases by 20%")
    assert s["headline"] == "Income ₹1,44,000/month"


def test_health_changes_use_model_when_available():
    calls = []

    def fake_assess(inputs):
        calls.append(inputs)
        risk = 0.2 if inputs["smoke"] == 0 else 0.5
        return {"bmi": 25.0, "hypertension_stage": "Stage 1", "cardio_risk": {"probability": risk, "label": "x"}, "overall_health_score": 70}

    before = {"bmi": 26.7, "hypertension_stage": "Stage 1", "cardio_risk": {"probability": 0.5, "label": "x"}, "overall_health_score": 55}
    [s] = analyze("If I quit smoking and lose 5 kg what changes?", health_profile=before, health_assess=fake_assess)

    assert s["kind"] == "health" and s["verdict"] == "improves"
    assert calls[0]["weight_kg"] == 65 and calls[0]["smoke"] == 0
    assert s["metrics"][0] == {"label": "CVD risk", "before": "50.0%", "after": "20.0%", "better": True}


def test_increase_cover_to_amount():
    hp = {"cardio_risk": {"label": "Low"}, "diabetes_indicator": "Low", "hypertension_stage": "Normal"}
    [s] = analyze("What if I increase my cover to 10 lakh?", health_profile=hp)
    assert s["kind"] == "insurance"
    assert "₹10,00,000" in s["headline"]


def test_general_question_has_no_scenario():
    assert analyze("How is my heart health?") == []
