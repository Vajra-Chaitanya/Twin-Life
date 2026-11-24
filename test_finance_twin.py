import pytest

from finance_twin import FinanceTwin


def assessed_twin():
    twin = FinanceTwin()
    twin.assess({
        "income": 100_000,
        "fixed_expenses": 25_000,
        "variable_expenses": 35_000,
        "emis": 10_000,
        "savings_balance": 300_000,
    })
    return twin


def test_monte_carlo_forecast_is_reproducible_and_returns_metric_ranges():
    twin = assessed_twin()

    first = twin.monte_carlo_forecast(months=12, iterations=500, seed=7)
    second = twin.monte_carlo_forecast(months=12, iterations=500, seed=7)

    assert first == second
    assert first["months"] == 12
    assert first["iterations"] == 500
    for metric in first["metrics"].values():
        assert metric["p10"] <= metric["median"] <= metric["p90"]


def test_monte_carlo_forecast_applies_modified_inputs_without_mutating_baseline():
    twin = assessed_twin()
    baseline_inputs = dict(twin.latest_inputs)
    baseline_profile = dict(twin.latest_profile)

    baseline = twin.monte_carlo_forecast(months=12, iterations=500, seed=11)
    higher_income = twin.monte_carlo_forecast(
        months=12,
        iterations=500,
        modified_inputs={"income": 120_000},
        seed=11,
    )

    assert higher_income["metrics"]["ending_savings_balance"]["median"] > (
        baseline["metrics"]["ending_savings_balance"]["median"]
    )
    assert twin.latest_inputs == baseline_inputs
    assert twin.latest_profile == baseline_profile


def test_monte_carlo_forecast_requires_assessment_and_valid_parameters():
    with pytest.raises(
        RuntimeError,
        match=r"Call assess\(\) before monte_carlo_forecast\(\)",
    ):
        FinanceTwin().monte_carlo_forecast()

    twin = assessed_twin()
    with pytest.raises(ValueError, match="months must be positive"):
        twin.monte_carlo_forecast(months=0)
    with pytest.raises(ValueError, match="iterations must be positive"):
        twin.monte_carlo_forecast(iterations=0)