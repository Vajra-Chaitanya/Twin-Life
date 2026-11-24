from datetime import date

import pytest

from event_engine import active_commitments, apply_ops, detect_events, detect_revert

HEALTH = {"weight_kg": 80, "ap_hi": 130, "ap_lo": 85, "smoke": 1, "alco": 0, "active": 0, "blood_glucose_level": 95, "conditions": []}
FINANCE = {"income": 120_000, "fixed_expenses": 30_000, "variable_expenses": 25_000, "emis": 8_000, "savings_balance": 450_000}
INSURANCE = {"sum_insured": 500_000, "annual_premium": 18_000, "existing_riders": []}
TODAY = date(2026, 11, 24)


def detect(text, commitments=None):
    return detect_events(text, HEALTH, FINANCE, INSURANCE, commitments=commitments, today=TODAY)


def apply(events):
    return apply_ops(HEALTH, FINANCE, INSURANCE, [op for e in events for op in e["ops"]])


def test_car_loan_with_emi_and_tenure_adds_emi_and_commitment():
    [e] = detect("I purchased a car for 8 lakh and my EMI is ₹15,000 for 5 years.")
    assert e["type"] == "loan" and e["needs"] is None
    assert e["ops"] == [{"domain": "finance", "field": "emis", "mode": "add", "value": 15_000}]
    assert e["commitment"] == {"item": "car", "emi": 15_000, "months": 60, "start": "2026-11-24", "end": "2031-11-24"}
    assert apply([e])[1]["emis"] == 23_000


def test_loan_amount_and_tenure_without_emi_derives_emi():
    [e] = detect("I took a home loan of 30 lakh for 240 months")
    assert e["ops"][0]["value"] == 12_500


def test_purchase_without_payment_details_asks_instead_of_guessing():
    [e] = detect("I bought a car last week.")
    assert e["ops"] == [] and "EMI" in e["needs"]


def test_cash_purchase_reduces_savings():
    [e] = detect("I bought a bike for 1.2 lakh, paid from savings.")
    assert apply([e])[1]["savings_balance"] == 330_000


def test_heart_attack_and_vague_medical_cost_increase():
    events = detect("I had a heart attack. My medical cost increases.")
    kinds = {e["type"]: e for e in events}
    assert kinds["condition"]["ops"] == [{"domain": "health", "field": "conditions", "mode": "append", "value": "heart_attack"}]
    assert "how much" in kinds["expense"]["needs"].lower()
    assert apply(events)[0]["conditions"] == ["heart_attack"]


def test_monthly_medical_cost_increase_and_one_time_bill():
    [monthly] = detect("My medical expenses went up by 6000 per month")
    [bill] = detect("I paid a hospital bill of 2.5 lakh")
    [lump] = detect("My medical cost increases, about 2 lakh one time")
    assert apply([monthly])[1]["variable_expenses"] == 31_000
    assert apply([bill])[1]["savings_balance"] == 200_000
    assert apply([lump])[1]["savings_balance"] == 250_000


@pytest.mark.parametrize(
    "text, income",
    [("I got a 20% hike", 144_000), ("My salary is now 1.5 lakh", 150_000), ("My salary was cut by 10%", 108_000)],
)
def test_income_changes(text, income):
    [e] = detect(text)
    assert apply([e])[1]["income"] == income


def test_lost_job_without_amount_asks():
    [e] = detect("I lost my job")
    assert e["needs"]


def test_health_habits_and_measurements():
    events = detect("I lost 6 kg, quit smoking and started going to the gym. My BP is now 120/80.")
    h = apply(events)[0]
    assert (h["weight_kg"], h["smoke"], h["active"], h["ap_hi"], h["ap_lo"]) == (74, 0, 1, 120, 80)


def test_insurance_rider_and_cover():
    events = detect("I added a critical illness rider and my sum insured is now 15 lakh")
    i = apply(events)[2]
    assert i["existing_riders"] == ["Critical Illness Rider"] and i["sum_insured"] == 1_500_000


def test_closing_known_loan_uses_stored_commitment():
    commitments = [{"item": "car", "emi": 15_000, "months": 60, "start": "2026-01-01", "end": "2031-01-01"}]
    [e] = detect("I closed my car loan", commitments=commitments)
    assert e["ops"][0]["value"] == -15_000


@pytest.mark.parametrize(
    "text",
    ["If I buy a car with 15000 EMI what happens?", "I am planning to take a bike loan of 10k per month",
     "Can I afford a 3 lakh surgery?", "Should I quit smoking?", "How is my heart?"],
)
def test_hypotheticals_and_questions_are_not_events(text):
    assert detect(text) == []


def test_active_commitments_respects_end_dates_closures_and_undo():
    events = [
        {"commitment": {"item": "car", "emi": 15_000, "end": "2031-01-01"}},
        {"commitment": {"item": "phone", "emi": 2_000, "end": "2025-01-01"}},
        {"commitment": {"item": "bike", "emi": 4_000, "end": None}, "undone": True},
        {"commitment": {"item": "laptop", "emi": 3_000, "end": None}},
        {"commitment": {"item": "laptop", "emi": 3_000, "closed": True}},
    ]
    assert [c["item"] for c in active_commitments(events, TODAY)] == ["car"]


LIVE = [
    {"id": 1, "type": "loan", "summary": "Took car on EMI of ₹15,000/month", "commitment": {"item": "car"}},
    {"id": 2, "type": "condition", "summary": "Heart attack recorded in medical history", "commitment": None},
    {"id": 3, "type": "expense", "summary": "Medical costs up by ₹6,000/month", "commitment": None},
]


@pytest.mark.parametrize(
    "text, ids",
    [("undo that", [3]), ("revert the car loan", [1]), ("I didn't buy the car", [1]),
     ("that was a mistake, remove the heart attack", [2]), ("undo everything", [1, 2, 3]), ("revert #2", [2])],
)
def test_revert_targets(text, ids):
    assert detect_revert(text, LIVE, last_turn_ids=[])["ids"] == ids


def test_revert_prefers_last_turn_and_asks_when_unclear():
    assert detect_revert("undo", LIVE, last_turn_ids=[1, 2])["ids"] == [1, 2]
    unclear = detect_revert("revert the bike", LIVE, last_turn_ids=[])
    assert unclear["ids"] == [] and "Took car" in unclear["needs"]
    assert detect_revert("How is my heart?", LIVE, []) is None
    assert detect_revert("undo", [], [])["needs"]
