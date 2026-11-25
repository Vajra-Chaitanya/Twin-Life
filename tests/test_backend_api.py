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


def test_advice_simulation_compares_three_scores_without_saving():
    app = create_app("sqlite://", health_twin_factory=ResponsiveHealthTwin)
    client = TestClient(app)
    user = {"user_id": "synthetic-user-001"}
    payload = valid_onboarding_payload()
    payload["health_inputs"]["ap_hi"] = 150
    client.post("/onboard", json=payload)
    client.post("/assess", json=user)
    original = client.get("/inputs", params=user).json()
    history = client.get("/history", params=user).json()["snapshots"]

    response = client.post("/simulate", json={**user, "health": {"ap_hi": 118},
                                               "finance": {"emis": 0},
                                               "insurance": {"sum_insured": 1_000_000},
                                               "forecast_months": 1})
    assert response.status_code == 200
    result = response.json()
    assert result["before"]["health"]["overall_health_score"] == 40
    assert result["after"]["health"]["overall_health_score"] == 80
    assert result["after"]["finance"]["financial_stability_score"] != result["before"]["finance"]["financial_stability_score"]
    assert "insurance_adequacy_score" in result["after"]["insurance"]
    assert client.get("/inputs", params=user).json() == original
    assert client.get("/history", params=user).json()["snapshots"] == history
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

    def engine(query, health_inputs, finance_inputs, insurance_inputs, history=None, life_context=None, domain=None):
        calls.append({"query": query, "insurance": insurance_inputs, "history": history, "life": life_context,
                      "finance": finance_inputs, "domain": domain})
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


def test_query_passes_same_thread_history_and_lists_threads():
    engine, calls = fake_query_engine()
    app = create_app("sqlite://", health_twin_factory=FakeHealthTwin, query_engine=engine)
    client = TestClient(app)
    client.post("/onboard", json=valid_onboarding_payload())

    def ask(q, thread):
        return client.post("/query", json={"user_id": "synthetic-user-001", "query": q, "thread_id": thread}).json()

    first = ask("How is my heart?", "t1")
    second = ask("How can I improve it?", "t1")
    other = ask("Is my cover enough?", "t2")

    assert calls[0]["history"] == []
    assert calls[1]["history"] == [{"query": "How is my heart?", "answer": "Your heart risk is low."}]
    assert calls[2]["history"] == []
    assert (first["context_turns"], second["context_turns"], other["context_turns"]) == (0, 1, 0)

    t1 = client.get("/chat-history", params={"user_id": "synthetic-user-001", "thread_id": "t1"}).json()
    assert [m["query"] for m in t1["messages"]] == ["How is my heart?", "How can I improve it?"]
    threads = {t["thread_id"]: t for t in t1["threads"]}
    assert threads["t1"]["messages"] == 2 and threads["t1"]["title"] == "How is my heart?"
    assert threads["t2"]["messages"] == 1
    bad = client.post("/query", json={"user_id": "synthetic-user-001", "query": "hello there", "thread_id": "../x"})
    assert bad.status_code == 422
    app.state.db_engine.dispose()


def test_new_chat_does_not_inherit_unrelated_life_history():
    engine, calls = fake_query_engine()
    refinements = []
    def refine(text, previous):
        refinements.append(previous)
        return {"text": text, "refined": False, "error": None}

    app = create_app("sqlite://", health_twin_factory=FakeHealthTwin, query_engine=engine, query_refiner=refine)
    client = TestClient(app)
    client.post("/onboard", json=valid_onboarding_payload())
    user = "synthetic-user-001"
    client.post("/query", json={"user_id": user, "thread_id": "old", "query": "I bought a car on EMI of 15000 for 5 years"})

    fresh = client.post("/query", json={"user_id": user, "thread_id": "new", "query": "How is my sleep?"}).json()
    assert fresh["context_turns"] == 0
    assert refinements[-1] == [] and calls[-1]["history"] == []
    assert calls[-1]["life"]["recent_events"] == [] and calls[-1]["life"]["commitments"] == []
    assert calls[-1]["finance"]["emis"] == 25_000

    client.post("/query", json={"user_id": user, "thread_id": "health", "query": "Should I exercise?"})
    assert calls[-1]["history"] == [] and calls[-1]["life"]["commitments"] == []
    client.post("/query", json={"user_id": user, "thread_id": "plan", "query": "Should I buy a bike?"})
    assert calls[-1]["history"] == [] and calls[-1]["life"]["commitments"][0]["item"] == "car"
    client.post("/query", json={"user_id": user, "thread_id": "plan", "query": "What about 5k?"})
    assert calls[-1]["history"][0]["query"] == "Should I buy a bike?"
    assert calls[-1]["life"]["commitments"][0]["item"] == "car"
    client.post("/query", json={"user_id": user, "thread_id": "new", "query": "How are you?"})
    assert calls[-1]["history"][0]["query"] == "How is my sleep?"
    assert calls[-1]["life"]["recent_events"] == [] and calls[-1]["life"]["commitments"] == []
    app.state.db_engine.dispose()


def test_query_refines_typed_text_before_detecting_events():
    engine, calls = fake_query_engine()
    fixes = {"i got promoshun ill get xtra 50k evry month": "I got a promotion and get an extra 50k every month."}
    app = create_app("sqlite://", health_twin_factory=FakeHealthTwin, query_engine=engine,
                     query_refiner=lambda text, previous: {"text": fixes.get(text, text), "refined": text in fixes, "error": None})
    client = TestClient(app)
    client.post("/onboard", json=valid_onboarding_payload())
    user = "synthetic-user-001"

    body = client.post("/query", json={"user_id": user, "query": "i got promoshun ill get xtra 50k evry month"}).json()

    assert body["query"] == "i got promoshun ill get xtra 50k evry month"
    assert body["refined_query"] == "I got a promotion and get an extra 50k every month."
    assert [u["summary"] for u in body["updates"]] == ["Monthly income changed ₹1,00,000 → ₹1,50,000"]
    assert calls[0]["query"] == body["refined_query"]
    client.post("/query", json={"user_id": user, "query": "is that good?"})
    assert calls[1]["history"][0]["query"] == body["refined_query"]
    app.state.db_engine.dispose()


def test_domain_chats_policies_dues_and_due_alerts():
    engine, calls = fake_query_engine()
    app = create_app("sqlite://", health_twin_factory=FakeHealthTwin, query_engine=engine)
    client = TestClient(app)
    client.post("/onboard", json=valid_onboarding_payload())
    user = "synthetic-user-001"

    def ask(q, domain=None, thread="t"):
        body = {"user_id": user, "query": q, "thread_id": f"{domain or 'main'}-{thread}"}
        return client.post("/query", json={**body, **({"domain": domain} if domain else {})}).json()

    # A money update said in the Health Twin chat is not saved there.
    off = ask("I bought a car for 8 lakh, EMI 15000 for 5 years", domain="health")
    assert off["updates"] == [] and "Financial Twin" in off["pending_questions"][0]
    assert calls[-1]["life"]["dues"] == [] and off["domain"] == "health"
    ok = ask("I bought a car for 8 lakh, EMI 15000 for 5 years", domain="finance")
    assert [u["type"] for u in ok["updates"]] == ["loan"]
    factors = ok["updates"][0]["factor_impacts"]
    assert {factor["domain"] for factor in factors} == {"health", "finance", "insurance"}
    dti = next(factor for factor in factors if factor["label"] == "Debt-to-income ratio")
    assert dti["status"] == "changed" and dti["delta"] > 0
    assert all(factor["status"] != "changed" for factor in factors if factor["domain"] == "health")

    # Non-health insurance is stored as a policy and creates a renewal due.
    pol = ask("I took bike insurance for 2500 a year, renewal date 2030-01-15", domain="insurance")
    assert pol["updates"][0]["type"] == "policy"
    premium_factor = next(factor for factor in pol["updates"][0]["factor_impacts"]
                          if factor["label"] == "Annual portfolio premiums")
    assert premium_factor["status"] == "changed"
    policies = client.get("/inputs", params={"user_id": user}).json()["insurance_inputs"]["policies"]
    assert policies[0]["type"] == "vehicle" and policies[0]["premium"] == 2500

    dues = client.get("/dues", params={"user_id": user}).json()["dues"]
    kinds = {d["kind"]: d for d in dues}
    assert kinds["instalment"]["amount"] == 15000 and kinds["renewal"]["domain"] == "insurance"
    # The car has no vehicle policy recorded (only the bike's), so it is flagged.
    assert kinds["missing_policy"]["status"] == "missing"
    alerts = client.get("/notifications", params={"user_id": user}).json()["notifications"]
    assert any(a["type"] == "due_missing" for a in alerts)
    again = client.get("/notifications", params={"user_id": user}).json()["notifications"]
    assert len(again) == len(alerts)  # due alerts are not duplicated

    # Each twin page lists only its own conversations.
    health_threads = client.get("/chat-history", params={"user_id": user, "domain": "health"}).json()["threads"]
    main_threads = client.get("/chat-history", params={"user_id": user}).json()["threads"]
    assert [t["thread_id"] for t in health_threads] == ["health-t"] and main_threads == []
    app.state.db_engine.dispose()


def test_policy_renewal_alert_becomes_historical_when_new_date_is_unknown():
    engine, _ = fake_query_engine()
    app = create_app("sqlite://", health_twin_factory=FakeHealthTwin, query_engine=engine)
    client = TestClient(app)
    client.post("/onboard", json=valid_onboarding_payload())
    user = "synthetic-user-001"
    ask = lambda query: client.post("/query", json={"user_id": user, "query": query, "domain": "insurance"}).json()
    assert ask("I took bike insurance for 2500 a year, renewal date 2020-01-15")["updates"]
    alerts = client.get("/notifications", params={"user_id": user}).json()["notifications"]
    expired = next(alert for alert in alerts if alert["type"] == "due_expired")
    assert not expired.get("historical")
    assert ask("I renewed my bike insurance")["updates"]
    alerts = client.get("/notifications", params={"user_id": user}).json()["notifications"]
    old = next(alert for alert in alerts if alert["id"] == expired["id"])
    assert old["historical"] and old["read"]
    assert "no longer current" in old["message"]
    assert not any(due["kind"] == "renewal" for due in client.get("/dues", params={"user_id": user}).json()["dues"])
    app.state.db_engine.dispose()


def test_treatment_cost_prompt_only_for_treatment_questions():
    from api import _build_query_result

    state = {"routing": {"simulate": True}, "narration": "x",
             "simulation_result": {"error": "Please include a specific treatment cost to run this simulation."}}
    assert _build_query_result("I stopped eating ice cream daily.", state, [])["simulation"] is None
    assert "error" in _build_query_result("Can I afford this surgery?", state, [])["simulation"]


def test_only_actionable_advice_lines_are_marked_simulatable():
    from api import _simulatable_advice

    inputs = ({**valid_onboarding_payload()["health_inputs"], "smoke": 1},
              valid_onboarding_payload()["finance_inputs"], valid_onboarding_payload()["insurance_inputs"])
    result = {"narration": "**Verdict**\n\nYour plan:\n1. **Quit smoking** this month.\n"
                           "2. See your cardiologist for a lipid profile.\n3. Add a critical illness rider."}
    assert _simulatable_advice(result, inputs) == ["quit smoking this month.", "add a critical illness rider."]
    assert _simulatable_advice(result, None) == []


def test_simulate_advice_derives_changes_without_saving():
    app = create_app("sqlite://", health_twin_factory=FakeHealthTwin)
    client = TestClient(app)
    client.post("/onboard", json=valid_onboarding_payload())
    user = "synthetic-user-001"
    snapshots = len(client.get("/history", params={"user_id": user}).json()["snapshots"])
    body = client.post("/simulate-advice", json={"user_id": user, "advice": "Increase your sum insured to ₹10 lakh."}).json()
    assert [(c["field"], c["target"]) for c in body["changes"]] == [("sum_insured", 1_000_000)]
    assert body["after"]["insurance"]["insurance_adequacy_score"] >= body["before"]["insurance"]["insurance_adequacy_score"]
    assert any(f["label"] == "Health cover" for f in body["factor_impacts"])
    none = client.post("/simulate-advice", json={"user_id": user, "advice": "See your cardiologist this month."}).json()
    assert none["changes"] == [] and none["factor_impacts"] == []
    assert len(client.get("/history", params={"user_id": user}).json()["snapshots"]) == snapshots
    app.state.db_engine.dispose()


def test_greeting_gets_short_reply_without_twin_report():
    engine, calls = fake_query_engine()
    app = create_app("sqlite://", health_twin_factory=FakeHealthTwin, query_engine=engine)
    client = TestClient(app)
    client.post("/onboard", json=valid_onboarding_payload())
    before = len(calls)
    for text in ("hi", "Hello!", "thanks"):
        body = client.post("/query", json={"user_id": "synthetic-user-001", "query": text, "domain": "health"}).json()
        assert body["citations"] == [] and body["updates"] == []
        assert "score" not in body["narration"].lower()
    assert len(calls) == before
    app.state.db_engine.dispose()


def test_conversations_can_be_renamed_and_deleted():
    engine, _ = fake_query_engine()
    app = create_app("sqlite://", health_twin_factory=FakeHealthTwin, query_engine=engine)
    client = TestClient(app)
    client.post("/onboard", json=valid_onboarding_payload())
    user = "synthetic-user-001"
    for q, t in [("How is my heart?", "t1"), ("And my BP?", "t1"), ("Is my cover enough?", "t2")]:
        client.post("/query", json={"user_id": user, "query": q, "thread_id": t})

    renamed = client.patch("/chat-threads/t1", json={"user_id": user, "title": "  Heart   check "})
    assert renamed.json()["title"] == "Heart check"
    threads = client.get("/chat-history", params={"user_id": user}).json()["threads"]
    assert [(t["thread_id"], t["title"]) for t in threads] == [("t2", "Is my cover enough?"), ("t1", "Heart check")]
    assert client.patch("/chat-threads/nope", json={"user_id": user, "title": "x"}).status_code == 404

    assert client.delete("/chat-threads/t1", params={"user_id": user}).json()["deleted_messages"] == 2
    threads = client.get("/chat-history", params={"user_id": user}).json()["threads"]
    assert [t["thread_id"] for t in threads] == ["t2"]
    assert client.delete("/chat-threads/t1", params={"user_id": user}).status_code == 404
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


def test_life_event_in_chat_updates_twin_logs_event_and_can_be_undone():
    engine, calls = fake_query_engine()
    app = create_app("sqlite://", health_twin_factory=FakeHealthTwin, query_engine=engine)
    client = TestClient(app)
    client.post("/onboard", json=valid_onboarding_payload())
    user = "synthetic-user-001"

    body = client.post("/query", json={
        "user_id": user, "query": "I purchased a car for 8 lakh and my EMI is 15000 for 5 years. I had a heart attack.",
    }).json()

    assert {u["type"] for u in body["updates"]} == {"loan", "condition"}
    loan = next(u for u in body["updates"] if u["type"] == "loan")
    assert {"label": "Debt-to-income %", "before": 35, "after": 50} in loan["changes"]
    assert {"label": "Free cash / month", "before": 30_000, "after": 15_000} in loan["changes"]
    inputs = client.get("/inputs", params={"user_id": user}).json()
    assert inputs["finance_inputs"]["emis"] == 25_000
    assert inputs["health_inputs"]["conditions"] == ["heart_attack"]
    assert calls[0]["finance"]["emis"] == 25_000  # the advisor answers on the updated twin
    assert calls[0]["life"]["just_recorded"] and calls[0]["life"]["commitments"][0]["emi"] == 15_000
    assert len(client.get("/history", params={"user_id": user}).json()["snapshots"]) == 1

    # Later planning questions carry the commitment; hypotheticals do not change the twin.
    client.post("/query", json={"user_id": user, "query": "If I buy a bike for 1 lakh on EMI 5000, is it ok?"})
    assert calls[1]["life"]["just_recorded"] == [] and calls[1]["life"]["commitments"][0]["item"] == "car"
    assert client.get("/inputs", params={"user_id": user}).json()["finance_inputs"]["emis"] == 25_000

    # Missing details become questions rather than guesses.
    asked = client.post("/query", json={"user_id": user, "query": "My medical cost increases."}).json()
    assert asked["updates"] == [] and "how much" in asked["pending_questions"][0].lower()
    # A short reply completes the event the advisor asked about.
    answered = client.post("/query", json={"user_id": user, "query": "6000 per month"}).json()
    assert [u["summary"] for u in answered["updates"]] == ["Medical costs up by ₹6,000/month"]
    assert client.get("/inputs", params={"user_id": user}).json()["finance_inputs"]["variable_expenses"] == 41_000

    events = client.get("/events", params={"user_id": user}).json()
    assert len(events["events"]) == 3 and events["commitments"][0]["end"]
    snapshots_before = len(client.get("/history", params={"user_id": user}).json()["snapshots"])

    # Reverting happens only through the advisor.
    assert client.post(f"/events/{loan['id']}/undo", json={"user_id": user}).status_code in (404, 405)
    reverted = client.post("/query", json={"user_id": user, "query": "Undo the car loan, I didn't buy it"}).json()
    assert [r["id"] for r in reverted["reverted"]] == [loan["id"]] and reverted["updates"] == []
    assert {"label": "Debt-to-income %", "before": 50, "after": 35} in reverted["reverted"][0]["changes"]
    assert calls[-1]["life"]["just_reverted"][0]["summary"].startswith("Took car")
    assert client.get("/inputs", params={"user_id": user}).json()["finance_inputs"]["emis"] == 10_000
    assert client.get("/events", params={"user_id": user}).json()["commitments"] == []
    # The dashboard reads the newest snapshot, so the revert creates one.
    assert len(client.get("/history", params={"user_id": user}).json()["snapshots"]) == snapshots_before + 1

    unclear = client.post("/query", json={"user_id": user, "query": "revert the bike"}).json()
    assert unclear["reverted"] == [] and "couldn't find" in unclear["pending_questions"][0]
    everything = client.post("/query", json={"user_id": user, "query": "undo everything"}).json()
    assert len(everything["reverted"]) == 2
    assert client.get("/inputs", params={"user_id": user}).json()["health_inputs"]["conditions"] == []
    assert client.get("/inputs", params={"user_id": user}).json()["finance_inputs"]["variable_expenses"] == 35_000
    nothing = client.post("/query", json={"user_id": user, "query": "undo that"}).json()
    assert "no recorded updates" in nothing["pending_questions"][0].lower()

    # Recalibrating via onboarding keeps recorded medical history.
    client.post("/query", json={"user_id": user, "query": "I had a heart attack"})
    client.post("/onboard", json=valid_onboarding_payload())
    assert client.get("/inputs", params={"user_id": user}).json()["health_inputs"]["conditions"] == ["heart_attack"]
    app.state.db_engine.dispose()


def test_advisor_reassesses_health_and_insurance_updates():
    class HabitSensitiveHealthTwin(ResponsiveHealthTwin):
        def assess(self, inputs):
            profile = super().assess(inputs)
            profile["overall_health_score"] -= 10 * inputs["smoke"]
            profile["conditions"] = inputs.get("conditions", [])
            return profile

    engine, _ = fake_query_engine()
    app = create_app("sqlite://", health_twin_factory=HabitSensitiveHealthTwin, query_engine=engine)
    client = TestClient(app)
    user = {"user_id": "synthetic-user-001"}
    client.post("/onboard", json=valid_onboarding_payload())
    baseline = client.post("/assess", json=user).json()

    smoke = client.post("/query", json={**user, "query": "I smoke"}).json()
    assert smoke["updates"][0]["type"] == "habit"
    assert {"label": "Health score", "before": 80, "after": 70} in smoke["updates"][0]["changes"]
    assert client.get("/inputs", params=user).json()["health_inputs"]["smoke"] == 1
    assert client.get("/history", params=user).json()["snapshots"][0]["health"]["overall_health_score"] == 70

    bp = client.post("/query", json={**user, "query": "My blood pressure is now 150/95"}).json()
    assert bp["updates"][0]["type"] == "bp"
    inputs = client.get("/inputs", params=user).json()
    assert (inputs["health_inputs"]["ap_hi"], inputs["health_inputs"]["ap_lo"]) == (150, 95)
    latest = client.get("/history", params=user).json()["snapshots"][0]
    assert latest["snapshot_id"] != baseline["snapshot_id"] and latest["health"]["hypertension_stage"] == "Stage 2"

    cover = client.post("/query", json={**user, "query": "My health insurance cover is 10 lakh"}).json()
    assert cover["updates"][0]["type"] == "cover"
    assert client.get("/inputs", params=user).json()["insurance_inputs"]["sum_insured"] == 1_000_000
    cover_snapshot = client.get("/history", params=user).json()["snapshots"][0]
    assert cover_snapshot["snapshot_id"] == cover["updates"][0]["snapshot_id"]
    assert cover_snapshot["insurance"]["coverage_adequacy_ratio"] > latest["insurance"]["coverage_adequacy_ratio"]

    rider = client.post("/query", json={**user, "query": "I added a critical illness rider"}).json()
    assert rider["updates"][0]["type"] == "rider"
    assert "Critical Illness Rider" in client.get("/inputs", params=user).json()["insurance_inputs"]["existing_riders"]
    rider_snapshot = client.get("/history", params=user).json()["snapshots"][0]
    assert rider_snapshot["snapshot_id"] == rider["updates"][0]["snapshot_id"]
    assert "Critical Illness Rider" in rider_snapshot["insurance"]["rider_analysis"]["existing"]

    count = len(client.get("/history", params=user).json()["snapshots"])
    for query in ("I smoke", "Should I quit smoking?", "My mother has diabetes", "I don't have diabetes"):
        assert client.post("/query", json={**user, "query": query}).json()["updates"] == []
    assert len(client.get("/history", params=user).json()["snapshots"]) == count
    app.state.db_engine.dispose()


def test_smoking_update_with_trained_cardiovascular_model():
    import os
    import pytest
    from health_twin import CARDIO_MODEL_PATH, HealthTwin

    if not os.path.exists(CARDIO_MODEL_PATH):
        pytest.skip("Train the monotonic cardiovascular model to run this artifact test")
    engine, _ = fake_query_engine()
    app = create_app("sqlite://", health_twin_factory=HealthTwin, query_engine=engine)
    client = TestClient(app)
    user = {"user_id": "synthetic-user-001"}
    client.post("/onboard", json=valid_onboarding_payload())
    before = client.post("/assess", json=user).json()
    result = client.post("/query", json={**user, "query": "I smoke"}).json()
    after = client.get("/history", params=user).json()["snapshots"][0]
    assert result["updates"] and after["snapshot_id"] == result["updates"][0]["snapshot_id"]
    assert after["health"]["cardio_risk"]["probability"] >= before["health"]["cardio_risk"]["probability"]
    impacts = {impact["label"]: impact for impact in result["updates"][0]["health_impacts"]}
    assert set(impacts) == {
        "Health score", "CVD model estimate", "Diabetes model estimate", "BMI", "Blood pressure",
        "Cardiovascular model", "Glucose-based diabetes indicator", "Framingham estimate",
    }
    assert impacts["Cardiovascular model"]["weight_percent"] == 25
    assert impacts["Cardiovascular model"]["after_weighted_points"] <= impacts["Cardiovascular model"]["before_weighted_points"]
    assert impacts["Diabetes model estimate"]["after"] is None
    assert "HbA1c" in impacts["Diabetes model estimate"]["note"]

    drinking = client.post("/query", json={**user, "query": "I drink beer"}).json()
    impacts = {impact["label"]: impact for impact in drinking["updates"][0]["health_impacts"]}
    assert impacts["Diabetes model estimate"]["after"] is None
    assert "not an input" in impacts["Diabetes model estimate"]["note"]
    assert "CVD model estimate" in impacts

    hba1c = client.post("/query", json={**user, "query": "My HbA1c is 6.1"}).json()
    impacts = {impact["label"]: impact for impact in hba1c["updates"][0]["health_impacts"]}
    assert impacts["Diabetes model estimate"]["after"] is not None
    assert "CVD model estimate" not in impacts

    illness = client.post("/query", json={**user, "query": "I had dengue for 5 days"}).json()
    impacts = illness["updates"][0]["health_impacts"]
    assert len(impacts) == 3 and all(item["after"] is None for item in impacts)
    assert all("not calculated" in item["note"] for item in impacts)
    app.state.db_engine.dispose()


def test_diet_report_shows_five_unchanged_components_without_new_snapshot():
    class ComponentHealthTwin(FakeHealthTwin):
        def assess(self, inputs):
            profile = super().assess(inputs)
            profile["score_components"] = [
                {"key": key, "label": label, "weight_percent": weight,
                 "score": 80.0, "weighted_points": 80.0 * weight / 100}
                for key, label, weight in (
                    ("bmi", "BMI", 25), ("blood_pressure", "Blood pressure", 25),
                    ("cardiovascular", "Cardiovascular model", 25),
                    ("diabetes", "Glucose-based diabetes indicator", 15),
                    ("framingham", "Framingham estimate", 10),
                )
            ]
            return profile

    engine, _ = fake_query_engine()
    app = create_app("sqlite://", health_twin_factory=ComponentHealthTwin, query_engine=engine)
    client = TestClient(app)
    client.post("/onboard", json=valid_onboarding_payload())
    user = {"user_id": "synthetic-user-001"}
    before_count = len(client.get("/history", params=user).json()["snapshots"])
    result = client.post("/query", json={**user, "domain": "health", "query": "I increased oily food consumption"}).json()
    update = result["updates"][0]
    assert update["log"] is True and update["snapshot_id"] is None
    impacts = {impact["label"]: impact for impact in update["health_impacts"]}
    assert len(impacts) == 6
    assert impacts["Health score"]["before"] == impacts["Health score"]["after"] == 80
    for label in ("BMI", "Blood pressure", "Cardiovascular model", "Glucose-based diabetes indicator", "Framingham estimate"):
        assert impacts[label]["before"] == impacts[label]["after"] == 80
        assert impacts[label]["before_weighted_points"] == impacts[label]["after_weighted_points"]
        assert "measured value" in impacts[label]["note"]
    assert len(client.get("/history", params=user).json()["snapshots"]) == before_count
    app.state.db_engine.dispose()