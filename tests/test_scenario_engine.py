import pytest

from scenario_engine import analyze_question, inr, money_amounts, tenure_months

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
