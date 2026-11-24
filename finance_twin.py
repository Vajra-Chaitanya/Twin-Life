"""
Module 3B -- finance_twin.py
FinanceTwin: rule-based financial health assessment using formulas.py only
(no ML model).

Usage:
    twin = FinanceTwin()
    profile = twin.assess(inputs_dict)
    score   = twin.affordability_for(cost)
"""

import numpy as np

from formulas import (
    dti_ratio,
    savings_rate,
    emergency_fund_months,
    financial_stability_score,
    affordability_score,
)


class FinanceTwin:
    """Digital twin for financial health assessment.

    All computations are deterministic rule/formula-based (no ML model).
    The twin stores the latest inputs so that affordability_for() can be
    called without re-supplying the full input dict.

    Attributes:
        latest_inputs: The most recent inputs dict passed to assess().
        latest_profile: The most recent computed finance_profile.
    """

    def __init__(self) -> None:
        self.latest_inputs: dict | None = None
        self.latest_profile: dict | None = None

    def assess(self, inputs: dict) -> dict:
        """Compute a full financial profile.

        Args:
            inputs: Dict with keys:
                income (float)            - monthly gross income
                fixed_expenses (float)    - monthly fixed outflows (rent, etc.)
                variable_expenses (float) - monthly variable outflows
                emis (float)              - monthly loan EMI payments
                savings_balance (float)   - total liquid savings

        Returns:
            finance_profile dict matching the spec shape:
            {
                "dti_ratio": float,
                "savings_rate": float,
                "emergency_fund_months": float,
                "financial_stability_score": int,  # 0-100
                "disposable_income": float,
            }
        """
        income   = inputs["income"]
        fixed    = inputs["fixed_expenses"]
        variable = inputs["variable_expenses"]
        emis_val = inputs["emis"]
        savings  = inputs["savings_balance"]

        dti   = dti_ratio(fixed, emis_val, income)
        s_rate = savings_rate(income, fixed, variable)
        ef_months = emergency_fund_months(savings, fixed, variable)
        stability = financial_stability_score(dti, s_rate, ef_months)
        disposable = income - fixed - variable - emis_val

        profile = {
            "dti_ratio": dti,
            "savings_rate": s_rate,
            "emergency_fund_months": ef_months,
            "financial_stability_score": stability,
            "disposable_income": round(disposable, 2),
            "monthly_income": round(income, 2),
            "monthly_expenses": round(fixed + variable, 2),
            "savings_balance": round(savings, 2),
        }

        # Cache for affordability_for()
        self.latest_inputs = inputs
        self.latest_profile = profile
        return profile

    def affordability_for(self, cost: float, months: float = 12) -> float:
        """Check how affordable a one-time cost is given current finances.

        Uses the disposable income and a configurable saving horizon.

        Args:
            cost:   Total cost of the item/treatment.
            months: Months available to save for the cost (default 12).

        Returns:
            Affordability score (>= 1.0 means fully coverable).

        Raises:
            RuntimeError: If assess() has not been called yet.
        """
        if self.latest_inputs is None or self.latest_profile is None:
            raise RuntimeError(
                "Call assess() before affordability_for() so that "
                "disposable income is available."
            )
        disposable = self.latest_profile["disposable_income"]
        return affordability_score(disposable, months, cost)

    def monte_carlo_forecast(
        self,
        months: int = 12,
        iterations: int = 1000,
        modified_inputs: dict | None = None,
        seed: int | None = 42,
        income_volatility: float = 0.05,
        variable_expense_volatility: float = 0.10,
    ) -> dict:
        """Project financial metrics under monthly income/expense variation.

        Income and variable expenses use independent normal distributions,
        clipped at zero. Fixed expenses and EMIs remain constant. The returned
        quantiles are illustrative, not financial advice.
        """
        if self.latest_inputs is None:
            raise RuntimeError("Call assess() before monte_carlo_forecast()")
        if months <= 0:
            raise ValueError("months must be positive")
        if iterations <= 0:
            raise ValueError("iterations must be positive")
        if income_volatility < 0 or variable_expense_volatility < 0:
            raise ValueError("volatility values must be non-negative")

        inputs = {**self.latest_inputs, **(modified_inputs or {})}
        income = float(inputs["income"])
        fixed_expenses = float(inputs["fixed_expenses"])
        variable_expenses = float(inputs["variable_expenses"])
        emis = float(inputs["emis"])
        if income <= 0:
            raise ValueError("income must be positive")

        rng = np.random.default_rng(seed)
        ending_savings = np.full(iterations, float(inputs["savings_balance"]))
        final_income = np.zeros(iterations)
        final_variable_expenses = np.zeros(iterations)

        for _ in range(months):
            final_income = np.maximum(
                rng.normal(income, income * income_volatility, iterations), 0,
            )
            final_variable_expenses = np.maximum(
                rng.normal(
                    variable_expenses,
                    variable_expenses * variable_expense_volatility,
                    iterations,
                ),
                0,
            )
            ending_savings += (
                final_income - fixed_expenses - final_variable_expenses - emis
            )

        dti = np.divide(
            fixed_expenses + emis,
            final_income,
            out=np.ones(iterations),
            where=final_income > 0,
        )
        projected_savings_rate = np.divide(
            final_income - fixed_expenses - final_variable_expenses,
            final_income,
            out=np.full(iterations, -1.0),
            where=final_income > 0,
        )
        monthly_expenses = fixed_expenses + final_variable_expenses
        emergency_fund_months = np.divide(
            np.maximum(ending_savings, 0),
            monthly_expenses,
            out=np.full(iterations, 6.0),
            where=monthly_expenses > 0,
        )
        stability_scores = np.fromiter(
            (
                financial_stability_score(dti_value, savings_rate_value, fund_months)
                for dti_value, savings_rate_value, fund_months in zip(
                    dti, projected_savings_rate, emergency_fund_months,
                )
            ),
            dtype=float,
            count=iterations,
        )

        def summarize(values: np.ndarray) -> dict:
            p10, median, p90 = np.quantile(values, [0.1, 0.5, 0.9])
            return {
                "p10": round(float(p10), 2),
                "median": round(float(median), 2),
                "p90": round(float(p90), 2),
            }

        return {
            "months": months,
            "iterations": iterations,
            "seed": seed,
            "assumptions": {
                "income_volatility": income_volatility,
                "variable_expense_volatility": variable_expense_volatility,
                "fixed_expenses_and_emis": "constant",
            },
            "metrics": {
                "ending_savings_balance": summarize(ending_savings),
                "debt_to_income_ratio": summarize(dti),
                "savings_rate": summarize(projected_savings_rate),
                "financial_stability_score": summarize(stability_scores),
            },
            "probabilities": {
                "negative_ending_savings_balance": round(
                    float(np.mean(ending_savings < 0)), 4,
                ),
                "debt_to_income_above_0_40": round(float(np.mean(dti > 0.40)), 4),
            },
            "disclaimer": (
                "This stochastic forecast is illustrative guidance only and "
                "is not licensed financial advice."
            ),
        }


# ======================================================================
#  STANDALONE VERIFICATION (python finance_twin.py)
# ======================================================================
if __name__ == "__main__":
    import json

    twin = FinanceTwin()

    samples = [
        {
            "label": "Comfortable salaried professional",
            "inputs": {
                "income": 120000,
                "fixed_expenses": 30000,
                "variable_expenses": 20000,
                "emis": 15000,
                "savings_balance": 500000,
            },
        },
        {
            "label": "Stretched household budget",
            "inputs": {
                "income": 50000,
                "fixed_expenses": 20000,
                "variable_expenses": 15000,
                "emis": 12000,
                "savings_balance": 30000,
            },
        },
        {
            "label": "High-earner with heavy EMIs",
            "inputs": {
                "income": 250000,
                "fixed_expenses": 60000,
                "variable_expenses": 40000,
                "emis": 80000,
                "savings_balance": 200000,
            },
        },
    ]

    for s in samples:
        print("=" * 60)
        print(f"  {s['label']}")
        print("=" * 60)
        profile = twin.assess(s["inputs"])
        print(json.dumps(profile, indent=2))

        # Test affordability for a 500,000 treatment cost
        aff = twin.affordability_for(500000)
        print(f"  Affordability for 500,000 (12 months): {aff}")
        print()
