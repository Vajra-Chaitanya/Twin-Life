from fastapi.testclient import TestClient
from sqlalchemy import select

from api import (
    ChatHistoryRecord,
    FinanceInputRecord,
    HealthInputRecord,
    InsuranceInputRecord,
    SnapshotRecord,
    UserRecord,
    create_app,
)


class FakeHealthTwin:
    def __init__(self):
        self.calls = []

    def assess(self, inputs):
        self.calls.append(inputs)
        return {
            "bmi": 23.9,
            "obesity_class": "Normal",
            "hypertension_stage": "Normal",
            "cardio_risk": {"probability": 0.3, "label": "Moderate"},
            "diabetes_indicator": "Low",
            "framingham_10yr_risk": 5.0,
            "overall_health_score": 80,
            "shap_top_features": [],
        }


def make_test_app():
    fake = FakeHealthTwin()
    return create_app("sqlite://", health_twin_factory=lambda: fake), fake


def valid_onboarding_payload():
    return {
        "user_id": "synthetic-user-001",
        "health_inputs": {
            "age": 40,
            "gender": "female",
            "height_cm": 165,
            "weight_kg": 65,
            "ap_hi": 120,
            "ap_lo": 78,
            "cholesterol": 1,
            "gluc": 1,
            "smoke": 0,
            "alco": 0,
            "active": 1,
            "blood_glucose_level": 90,
        },
        "finance_inputs": {
            "income": 100_000,
            "fixed_expenses": 25_000,
            "variable_expenses": 35_000,
            "emis": 10_000,
            "savings_balance": 300_000,
        },
        "insurance_inputs": {
            "sum_insured": 500_000,
            "annual_premium": 15_000,
            "existing_riders": [],
        },
    }


def test_health_endpoint_and_onboarding_persistence():
    app = create_app("sqlite://")
    client = TestClient(app)

    assert client.get("/health").json() == {"status": "ok"}
    created = client.post("/onboard", json=valid_onboarding_payload())
    assert created.status_code == 201
    assert created.json() == {"user_id": "synthetic-user-001", "status": "created"}

    updated = client.post("/onboard", json=valid_onboarding_payload())
    assert updated.status_code == 201
    assert updated.json()["status"] == "updated"

    with app.state.session_factory() as session:
        assert session.scalar(select(UserRecord).where(
            UserRecord.user_id == "synthetic-user-001",
        )) is not None
        assert len(session.scalars(select(HealthInputRecord)).all()) == 2
        assert len(session.scalars(select(FinanceInputRecord)).all()) == 2
        assert len(session.scalars(select(InsuranceInputRecord)).all()) == 2

    app.state.db_engine.dispose()


def test_onboarding_rejects_invalid_health_inputs():
    app = create_app("sqlite://")
    client = TestClient(app)
    payload = valid_onboarding_payload()
    payload["health_inputs"]["cholesterol"] = 4

    response = client.post("/onboard", json=payload)

    assert response.status_code == 422
    app.state.db_engine.dispose()


def test_assess_uses_latest_inputs_and_saves_snapshot():
    app, fake = make_test_app()
    client = TestClient(app)
    client.post("/onboard", json=valid_onboarding_payload())
    newer = valid_onboarding_payload()
    newer["health_inputs"]["weight_kg"] = 70
    client.post("/onboard", json=newer)

    response = client.post("/assess", json={"user_id": "synthetic-user-001"})

    assert response.status_code == 201
    body = response.json()
    assert fake.calls[-1]["weight_kg"] == 70
    assert body["health"]["overall_health_score"] == 80
    assert body["finance"]["monthly_income"] == 100_000
    assert "insurance_adequacy_score" in body["insurance"]
    with app.state.session_factory() as session:
        assert len(session.scalars(select(SnapshotRecord)).all()) == 1
    app.state.db_engine.dispose()


def test_assess_returns_null_for_infinite_ratios():
    app, _ = make_test_app()
    client = TestClient(app)
    payload = valid_onboarding_payload()
    payload["finance_inputs"].update(fixed_expenses=0, variable_expenses=0)
    client.post("/onboard", json=payload)

    response = client.post("/assess", json={"user_id": "synthetic-user-001"})

    assert response.status_code == 201
    assert response.json()["finance"]["emergency_fund_months"] is None
    app.state.db_engine.dispose()


def test_history_returns_newest_first_and_respects_limit():
    app, _ = make_test_app()
    client = TestClient(app)
    client.post("/onboard", json=valid_onboarding_payload())
    ids = [
        client.post("/assess", json={"user_id": "synthetic-user-001"}).json()["snapshot_id"]
        for _ in range(3)
    ]

    response = client.get("/history", params={"user_id": "synthetic-user-001", "limit": 2})

    assert response.status_code == 200
    snapshots = response.json()["snapshots"]
    assert [s["snapshot_id"] for s in snapshots] == [ids[2], ids[1]]
    app.state.db_engine.dispose()


def test_assess_and_history_reject_unknown_user():
    app, _ = make_test_app()
    client = TestClient(app)

    assert client.post("/assess", json={"user_id": "nobody"}).status_code == 404
    assert client.get("/history", params={"user_id": "nobody"}).status_code == 404
    app.state.db_engine.dispose()


class ResponsiveHealthTwin:
    """Fake twin whose cardio label tracks systolic BP, so insurance costs react."""

    def assess(self, inputs):
        high = inputs["ap_hi"] >= 140
        return {
            "bmi": round(inputs["weight_kg"] / (inputs["height_cm"] / 100) ** 2, 1),
            "obesity_class": "Normal",
            "hypertension_stage": "Stage 2" if high else "Normal",
            "cardio_risk": {"probability": 0.8 if high else 0.2, "label": "High" if high else "Low"},
            "diabetes_indicator": "Low",
            "framingham_10yr_risk": 5.0,
            "overall_health_score": 40 if high else 80,
            "shap_top_features": [],
        }


def test_simulate_returns_before_after_without_saving_snapshot():
    app = create_app("sqlite://", health_twin_factory=ResponsiveHealthTwin)
    client = TestClient(app)
    payload = valid_onboarding_payload()
    payload["health_inputs"]["ap_hi"] = 150
    client.post("/onboard", json=payload)

    response = client.post("/simulate", json={
        "user_id": "synthetic-user-001",
        "health": {"ap_hi": 118},
        "finance": {"emis": 0},
        "forecast_months": 6,
    })

    assert response.status_code == 200
    body = response.json()
    assert body["changes"]["health"] == {"ap_hi": 118}
    assert body["before"]["health"]["overall_health_score"] == 40
    assert body["after"]["health"]["overall_health_score"] == 80
    assert (
        body["after"]["insurance"]["estimated_future_cost"]
        < body["before"]["insurance"]["estimated_future_cost"]
    )
    assert body["after"]["finance"]["dti_ratio"] < body["before"]["finance"]["dti_ratio"]
    before_tl, after_tl = body["forecast"]["before"], body["forecast"]["after"]
    assert [p["month"] for p in after_tl] == [1, 2, 3, 4, 5, 6]
    assert all(p["p10"] <= p["median"] <= p["p90"] for p in after_tl)
    assert after_tl[-1]["median"] > before_tl[-1]["median"]
    with app.state.session_factory() as session:
        assert session.scalars(select(SnapshotRecord)).all() == []
    app.state.db_engine.dispose()


def test_simulate_rejects_invalid_overrides_and_unknown_user():
    app, _ = make_test_app()
    client = TestClient(app)
    client.post("/onboard", json=valid_onboarding_payload())

    bad = client.post("/simulate", json={"user_id": "synthetic-user-001", "health": {"cholesterol": 9}})
    unknown_field = client.post("/simulate", json={"user_id": "synthetic-user-001", "health": {"height": 1}})
    missing = client.post("/simulate", json={"user_id": "nobody"})

    assert bad.status_code == 422
    assert unknown_field.status_code == 422
    assert missing.status_code == 404
    app.state.db_engine.dispose()


def test_inputs_returns_latest_onboarding_payload():
    app, _ = make_test_app()
    client = TestClient(app)
    client.post("/onboard", json=valid_onboarding_payload())
    newer = valid_onboarding_payload()
    newer["finance_inputs"]["emis"] = 0
    client.post("/onboard", json=newer)

    response = client.get("/inputs", params={"user_id": "synthetic-user-001"})

    assert response.status_code == 200
    assert response.json()["finance_inputs"]["emis"] == 0
    assert response.json()["health_inputs"]["age"] == 40
    assert client.get("/inputs", params={"user_id": "nobody"}).status_code == 404
    app.state.db_engine.dispose()


def fake_query_engine(narration="Your heart risk is low.", simulation=None):
    calls = []

    def engine(query, health_inputs, finance_inputs, insurance_inputs):
        calls.append({"query": query, "insurance": insurance_inputs})
        state = {
            "routing": {"twins": ["health"], "mode": "single-domain", "simulate": simulation is not None},
            "health_profile": {"overall_health_score": 80},
            "finance_profile": None,
            "insurance_profile": None,
            "narration": narration,
            "simulation_result": simulation,
        }
        citations = [{"text": "Walk 150 minutes per week.", "source": "C:/data/guidelines/cardiovascular_guidelines.txt", "score": 0.71}]
        return state, citations

    return engine, calls


def test_query_returns_narration_citations_and_saves_chat():
    engine, calls = fake_query_engine()
    app = create_app("sqlite://", health_twin_factory=FakeHealthTwin, query_engine=engine)
    client = TestClient(app)
    client.post("/onboard", json=valid_onboarding_payload())

    response = client.post("/query", json={"user_id": "synthetic-user-001", "query": "  How is my heart?  "})

    assert response.status_code == 200
    body = response.json()
    assert calls[0]["query"] == "How is my heart?"
    assert calls[0]["insurance"]["annual_income"] == 1_200_000
    assert body["narration"] == "Your heart risk is low."
    assert body["narration_error"] is None
    assert body["pipeline"] == ["route", "health", "rag", "narrate"]
    assert body["citations"] == [{
        "source": "cardiovascular_guidelines.txt", "score": 0.71, "excerpt": "Walk 150 minutes per week.",
    }]
    history = client.get("/chat-history", params={"user_id": "synthetic-user-001"}).json()["messages"]
    assert [m["query"] for m in history] == ["How is my heart?"]
    with app.state.session_factory() as session:
        assert len(session.scalars(select(ChatHistoryRecord)).all()) == 1
    app.state.db_engine.dispose()


def test_query_hides_raw_ai_errors():
    engine, _ = fake_query_engine(
        narration="[Narration error: 429 RESOURCE_EXHAUSTED secret-detail]",
        simulation={"error": "GEMINI_API_KEY environment variable not set at /path"},
    )
    app = create_app("sqlite://", health_twin_factory=FakeHealthTwin, query_engine=engine)
    client = TestClient(app)
    client.post("/onboard", json=valid_onboarding_payload())

    body = client.post("/query", json={"user_id": "synthetic-user-001", "query": "Can I afford surgery for 2 lakh?"}).json()

    assert body["narration"] == ""
    assert body["narration_error"] == "Gemini rate limit reached. Please wait a minute and try again."
    assert body["simulation"] == {"error": "Gemini API key is not configured on the server."}
    assert "simulate" in body["pipeline"]
    assert "secret-detail" not in str(body)
    app.state.db_engine.dispose()


def test_query_validates_input_and_user():
    engine, calls = fake_query_engine()
    app = create_app("sqlite://", health_twin_factory=FakeHealthTwin, query_engine=engine)
    client = TestClient(app)

    assert client.post("/query", json={"user_id": "nobody", "query": "hello there"}).status_code == 404
    assert client.post("/query", json={"user_id": "nobody", "query": "x" * 1001}).status_code == 422
    assert calls == []
    app.state.db_engine.dispose()


def test_assess_generates_monitoring_notifications_and_marks_read():
    app = create_app("sqlite://", health_twin_factory=ResponsiveHealthTwin)
    client = TestClient(app)
    user = {"user_id": "synthetic-user-001"}
    client.post("/onboard", json=valid_onboarding_payload())

    first = client.post("/assess", json=user).json()
    worse = valid_onboarding_payload()
    worse["health_inputs"]["ap_hi"] = 150
    worse["finance_inputs"].update(emis=20_000, variable_expenses=70_000)
    client.post("/onboard", json=worse)
    second = client.post("/assess", json=user).json()

    assert first["alerts_generated"] == 1
    assert second["alerts_generated"] >= 4
    feed = client.get("/notifications", params=user).json()
    types = {n["type"] for n in feed["notifications"]}
    assert {"baseline", "health_score_drop", "dti_high", "low_savings_rate", "new_rider_gap"} <= types
    assert feed["unread"] == len(feed["notifications"])
    assert all(n["snapshot_id"] in (first["snapshot_id"], second["snapshot_id"]) for n in feed["notifications"])

    newest_id = feed["notifications"][0]["id"]
    marked = client.post("/notifications/read", json={**user, "ids": [newest_id]}).json()
    assert marked["updated"] == 1
    assert client.get("/notifications", params=user).json()["unread"] == feed["unread"] - 1

    client.post("/notifications/read", json=user)
    assert client.get("/notifications", params=user).json()["unread"] == 0
    app.state.db_engine.dispose()


def test_whatif_reports_purchase_impact():
    app, _ = make_test_app()
    client = TestClient(app)
    client.post("/onboard", json=valid_onboarding_payload())

    response = client.post("/whatif", json={"user_id": "synthetic-user-001", "purchase_cost": 240_000})

    assert response.status_code == 200
    body = response.json()
    # Disposable 30k/month * 12 / 240k = 1.5 -> affordable.
    assert body["affordable"] is True
    assert body["affordability_score"] == 1.5
    # DTI 0.35 + (240k / 12) / 100k income.
    assert body["impact_analysis"]["new_dti_if_emi"] == 0.55
    assert body["impact_analysis"]["emergency_fund_months_after_purchase"] == 1.0
    assert client.post("/whatif", json={"user_id": "synthetic-user-001", "purchase_cost": -1}).status_code == 422
    app.state.db_engine.dispose()