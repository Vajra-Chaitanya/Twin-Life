import numpy as np
import pytest

import health_twin
from health_twin import HealthTwin


class FakeCardioModel:
    def predict_proba(self, row):
        return np.array([[0.7, 0.3]])


def test_health_twin_loads_one_model_and_uses_glucose_indicator(monkeypatch):
    loaded_paths = []

    def load_model(path):
        loaded_paths.append(path)
        return FakeCardioModel()

    monkeypatch.setattr(health_twin.joblib, "load", load_model)
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
    })

    assert loaded_paths == [health_twin.CARDIO_MODEL_PATH]
    assert profile["diabetes_indicator"] == "High"
    assert "diabetes_risk" not in profile


def test_health_twin_simulate_returns_before_after_and_preserves_baseline(monkeypatch):
    monkeypatch.setattr(health_twin.joblib, "load", lambda _: FakeCardioModel())
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
    monkeypatch.setattr(health_twin.joblib, "load", lambda _: FakeCardioModel())
    twin = HealthTwin()

    with pytest.raises(RuntimeError, match=r"Call assess\(\) before simulate\(\)"):
        twin.simulate({"weight_kg": 80})