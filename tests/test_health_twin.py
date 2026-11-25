import os

import joblib
import numpy as np
import pandas as pd
import pytest

import health_twin
from health_twin import HealthTwin


class FakeCardioModel:
    def predict_proba(self, row):
        return np.array([[0.7, 0.3]])


class FakeDiabetesModel:
    def __init__(self):
        self.rows = []

    def predict_proba(self, row):
        self.rows.append(row)
        return np.array([[0.2, 0.8]])


DIABETES_COLS = ["age", "hypertension", "heart_disease", "bmi", "HbA1c_level", "blood_glucose_level",
                 "gender_Female", "gender_Male", "gender_Other", "smoking_current", "smoking_No Info"]


def fake_loader(paths, diabetes=None):
    def load_model(path):
        paths.append(path)
        if path == health_twin.DIABETES_COLS_PATH:
            return DIABETES_COLS
        if path == health_twin.DIABETES_MODEL_PATH:
            return diabetes or FakeDiabetesModel()
        return FakeCardioModel()
    return load_model


def test_health_twin_loads_one_model_and_uses_glucose_indicator(monkeypatch):
    loaded_paths = []
    diabetes = FakeDiabetesModel()
    monkeypatch.setattr(health_twin.joblib, "load", fake_loader(loaded_paths, diabetes))
    monkeypatch.setattr(health_twin.os.path, "exists", lambda _: True)
    monkeypatch.setattr(health_twin, "SHAP_AVAILABLE", False)

    twin = HealthTwin()
    profile = twin.assess({
        "age": 45,
        "gender": "female",
        "height_cm": 165,
        "weight_kg": 70,
        "ap_hi": 125,
        "ap_lo": 78,
        "cholesterol": 1,
        "gluc": 1,
        "smoke": 0,
        "alco": 0,
        "active": 1,
        "blood_glucose_level": 140,
        "hba1c": 6.5,
        "conditions": ["heart_attack"],
    })

    assert loaded_paths == [health_twin.CARDIO_MODEL_PATH, health_twin.DIABETES_MODEL_PATH, health_twin.DIABETES_COLS_PATH]
    assert profile["diabetes_indicator"] == "High"
    assert profile["diabetes_risk"] == {"probability": 0.8, "label": "Very High", "hba1c": 6.5,
                                        "hba1c_estimated": False, "diagnosed": False}
    components = profile["score_components"]
    assert [component["weight_percent"] for component in components] == [25, 25, 25, 15, 10]
    assert sum(component["weighted_points"] for component in components) == pytest.approx(
        HealthTwin._compute_overall_score(
            profile["bmi"], profile["hypertension_stage"], profile["cardio_risk"]["probability"],
            profile["diabetes_indicator"], profile["framingham_10yr_risk"],
        ), abs=0.5,
    )
    row = diabetes.rows[0].iloc[0]
    assert (row["heart_disease"], row["gender_Female"], row["smoking_No Info"], row["hypertension"]) == (1, 1, 1, 0)


def test_health_twin_simulate_returns_before_after_and_preserves_baseline(monkeypatch):
    monkeypatch.setattr(health_twin.joblib, "load", fake_loader([]))
    monkeypatch.setattr(health_twin, "SHAP_AVAILABLE", False)
    twin = HealthTwin()
    baseline_inputs = {
        "age": 45,
        "gender": "female",
        "height_cm": 165,
        "weight_kg": 70,
        "ap_hi": 125,
        "ap_lo": 78,
        "cholesterol": 1,
        "gluc": 1,
        "smoke": 0,
        "alco": 0,
        "active": 1,
        "blood_glucose_level": 90,
    }
    before = twin.assess(baseline_inputs)

    result = twin.simulate({
        "weight_kg": 90,
        "ap_hi": 150,
        "ap_lo": 95,
        "blood_glucose_level": 140,
    })

    assert result["before"] == before
    assert result["after"]["bmi"] > result["before"]["bmi"]
    assert result["after"]["hypertension_stage"] == "Stage 2"
    assert result["after"]["diabetes_indicator"] == "High"
    assert twin.latest_inputs == baseline_inputs
    assert twin.latest_profile == before


def test_missing_hba1c_does_not_invent_a_diabetes_prediction(monkeypatch):
    diabetes = FakeDiabetesModel()
    monkeypatch.setattr(health_twin.joblib, "load", fake_loader([], diabetes))
    monkeypatch.setattr(health_twin.os.path, "exists", lambda _: True)
    monkeypatch.setattr(health_twin, "SHAP_AVAILABLE", False)
    twin = HealthTwin()
    inputs = {"age": 45, "gender": "female", "height_cm": 165, "weight_kg": 70,
              "ap_hi": 125, "ap_lo": 78, "cholesterol": 1, "gluc": 1,
              "smoke": 0, "alco": 0, "active": 1, "blood_glucose_level": 140}
    profile = twin.assess(inputs)
    assert profile["diabetes_risk"] is None
    assert profile["diabetes_unavailable_reason"] == "missing_hba1c"
    assert diabetes.rows == []


def test_trained_cardiovascular_model_does_not_reduce_prediction_for_smoking():
    if not os.path.exists(health_twin.CARDIO_MODEL_PATH):
        pytest.skip("Train the monotonic cardiovascular model to run this artifact test")
    model = joblib.load(health_twin.CARDIO_MODEL_PATH)
    rows = pd.DataFrame([
        {"age_years": age, "gender": gender, "bmi": bmi, "ap_hi": bp, "ap_lo": 80,
         "cholesterol": cholesterol, "gluc": 1, "smoke": 0, "alco": 0, "active": 1}
        for age in (35, 45, 55, 64) for gender in (1, 2)
        for bmi in (20, 27, 35) for bp in (110, 140, 180) for cholesterol in (1, 3)
    ])[health_twin.CARDIO_FEATURES]
    smoking = rows.copy()
    smoking["smoke"] = 1
    assert np.all(model.predict_proba(smoking)[:, 1] + 1e-12 >= model.predict_proba(rows)[:, 1])


@pytest.mark.parametrize("change", [
    {"alco": 1}, {"smoke": 1}, {"active": 0}, {"weight_kg": 90}, {"ap_hi": 150, "ap_lo": 95},
    {"cholesterol": 3}, {"gluc": 3}, {"blood_glucose_level": 130},
])
def test_harmful_change_never_lowers_risk_or_raises_health_score(change):
    if not os.path.exists(health_twin.CARDIO_MODEL_PATH):
        pytest.skip("Train the clinical cardiovascular model to run this artifact test")
    twin = HealthTwin()
    base = {"age": 45, "gender": "male", "height_cm": 170, "weight_kg": 83, "ap_hi": 135, "ap_lo": 85,
            "cholesterol": 1, "gluc": 1, "smoke": 0, "alco": 0, "active": 1, "blood_glucose_level": 95}
    before, after = twin.assess(base), twin.assess({**base, **change})
    assert after["cardio_risk"]["probability"] >= before["cardio_risk"]["probability"]
    assert after["overall_health_score"] <= before["overall_health_score"]


@pytest.mark.parametrize("habit, change", [("smoke", {"smoke": 1}), ("alco", {"alco": 1}), ("active", {"active": 0})])
def test_habits_carry_published_relative_risk(habit, change):
    if not os.path.exists(health_twin.CARDIO_MODEL_PATH):
        pytest.skip("Train the clinical cardiovascular model to run this artifact test")
    twin = HealthTwin()
    base = {"age": 50, "gender": "male", "height_cm": 172, "weight_kg": 80, "ap_hi": 130, "ap_lo": 85,
            "cholesterol": 1, "gluc": 1, "smoke": 0, "alco": 0, "active": 1, "blood_glucose_level": 95}
    before, after = twin.assess(base)["cardio_risk"], twin.assess({**base, **change})["cardio_risk"]
    odds = lambda p: p / (1 - p)
    expected = {"smoke": 2.0, "alco": 1.25, "active": 1.3}[habit]
    assert odds(after["probability"]) / odds(before["probability"]) == pytest.approx(expected, rel=0.05)
    assert after["habit_adjustments"] and after["model_probability"] == before["model_probability"]


def test_health_twin_simulate_requires_baseline_assessment(monkeypatch):
    monkeypatch.setattr(health_twin.joblib, "load", fake_loader([]))
    twin = HealthTwin()

    with pytest.raises(RuntimeError, match=r"Call assess\(\) before simulate\(\)"):
        twin.simulate({"weight_kg": 80})