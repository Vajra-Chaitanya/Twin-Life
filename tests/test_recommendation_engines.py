import pytest

from finance_twin import FinanceTwin
from recommendation_engines import purchase_impact_simulator


def test_purchase_impact_uses_actual_monthly_income_for_new_dti():
    finance_profile = FinanceTwin().assess({
        "income": 120_000,
        "fixed_expenses": 30_000,
        "variable_expenses": 20_000,
        "emis": 15_000,
        "savings_balance": 500_000,
    })

    result = purchase_impact_simulator(finance_profile, 100_000)

    expected_dti = finance_profile["dti_ratio"] + 100_000 / 12 / 120_000
    assert result["impact_analysis"]["new_dti_if_emi"] == pytest.approx(
        expected_dti, abs=0.001,
    )
    expected_24_month_dti = finance_profile["dti_ratio"] + 100_000 / 24 / 120_000
    assert result["impact_analysis"]["new_dti_if_emi_24months"] == pytest.approx(
        expected_24_month_dti, abs=0.001,
    )


def test_purchase_impact_compares_purchase_to_actual_savings():
    finance_profile = FinanceTwin().assess({
        "income": 200_000,
        "fixed_expenses": 20_000,
        "variable_expenses": 20_000,
        "emis": 10_000,
        "savings_balance": 50_000,
    })

    result = purchase_impact_simulator(finance_profile, 40_000)

    assert result["impact_analysis"]["emergency_fund_impact"].startswith("Moderate")
    assert result["impact_analysis"]["emergency_fund_months_after_purchase"] == 0.2


def test_purchase_impact_rejects_negative_cost():
    finance_profile = FinanceTwin().assess({
        "income": 120_000,
        "fixed_expenses": 30_000,
        "variable_expenses": 20_000,
        "emis": 15_000,
        "savings_balance": 500_000,
    })

    with pytest.raises(ValueError, match="purchase_cost must be non-negative"):
        purchase_impact_simulator(finance_profile, -100)