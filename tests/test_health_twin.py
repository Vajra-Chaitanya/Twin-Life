import numpy as np
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
                 "gender_Female", "gender_Male", "gender_Other", "smoking_current", "smoking_never"]


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
        "conditions": ["heart_attack"],
    })

    assert loaded_paths == [health_twin.CARDIO_MODEL_PATH, health_twin.DIABETES_MODEL_PATH, health_twin.DIABETES_COLS_PATH]
    assert profile["diabetes_indicator"] == "High"
    # HbA1c is estimated from glucose when not supplied: (140 + 46.7) / 28.7 = 6.5.
    assert profile["diabetes_risk"] == {"probability": 0.8, "label": "Very High", "hba1c": 6.5,
                                        "hba1c_estimated": True, "diagnosed": False}
    row = diabetes.rows[0].iloc[0]
    assert (row["heart_disease"], row["gender_Female"], row["smoking_never"], row["hypertension"]) == (1, 1, 1, 0)


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


def test_health_twin_simulate_requires_baseline_assessment(monkeypatch):
    monkeypatch.setattr(health_twin.joblib, "load", fake_loader([]))
    twin = HealthTwin()

    with pytest.raises(RuntimeError, match=r"Call assess\(\) before simulate\(\)"):
        twin.simulate({"weight_kg": 80})