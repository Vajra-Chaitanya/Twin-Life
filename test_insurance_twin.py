import pytest

from insurance_twin import InsuranceTwin


def test_insurance_simulation_returns_before_after_and_preserves_baseline():
    twin = InsuranceTwin()
    baseline_inputs = {
        "sum_insured": 100_000,
        "annual_premium": 10_000,
        "annual_income": 500_000,
        "existing_riders": [],
    }
    health_profile = {
        "cardio_risk": {"label": "Elevated"},
        "diabetes_indicator": "Medium",
        "hypertension_stage": "Stage 1",
    }
    finance_profile = {"financial_stability_score": 60}
    before = twin.assess(baseline_inputs, health_profile, finance_profile)

    result = twin.simulate({
        "sum_insured": 1_000_000,
        "annual_premium": 5_000,
        "existing_riders": [
            "Critical Illness Rider",
            "Diabetes Care Rider",
            "Hospital Cash Rider",
            "Personal Accident Rider",
        ],
    })

    assert result["before"] == before
    assert result["after"]["coverage_adequacy_ratio"] > before[
        "coverage_adequacy_ratio"
    ]
    assert result["after"]["premium_affordability_ratio"] < before[
        "premium_affordability_ratio"
    ]
    assert result["after"]["rider_analysis"]["gap_count"] == 0
    assert twin.latest_inputs == baseline_inputs
    assert twin.latest_profile == before


def test_insurance_simulation_requires_baseline_assessment():
    with pytest.raises(
        RuntimeError,
        match=r"Call assess\(\) before simulate\(\)",
    ):
        InsuranceTwin().simulate({"sum_insured": 1_000_000})