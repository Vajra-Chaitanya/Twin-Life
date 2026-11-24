"""End-to-end API journey: calibrate, assess, explore, ask, monitor (no network, fake model and AI)."""

from fastapi.testclient import TestClient

from api import create_app
from test_backend_api import ResponsiveHealthTwin, fake_query_engine, valid_onboarding_payload


def test_full_user_journey():
    engine, _ = fake_query_engine()
    app = create_app("sqlite://", health_twin_factory=ResponsiveHealthTwin, query_engine=engine)
    client = TestClient(app)
    user = {"user_id": "synthetic-user-001"}

    assert client.get("/health").json() == {"status": "ok"}

    # Calibrate and take a baseline snapshot.
    assert client.post("/onboard", json=valid_onboarding_payload()).status_code == 201
    baseline = client.post("/assess", json=user).json()
    assert baseline["health"]["overall_health_score"] == 80
    assert client.get("/inputs", params=user).json()["finance_inputs"]["income"] == 100_000

    # Explore futures without touching history.
    sim = client.post("/simulate", json={**user, "health": {"ap_hi": 150}, "finance": {"emis": 0}}).json()
    assert sim["after"]["health"]["overall_health_score"] < sim["before"]["health"]["overall_health_score"]
    assert len(sim["forecast"]["after"]) == 12
    purchase = client.post("/whatif", json={**user, "purchase_cost": 2_000_000}).json()
    assert purchase["affordable"] is False
    assert len(client.get("/history", params=user).json()["snapshots"]) == 1

    # Ask the advisor; the exchange is persisted.
    answer = client.post("/query", json={**user, "query": "How is my heart?"}).json()
    assert answer["narration"] and answer["citations"]
    assert len(client.get("/chat-history", params=user).json()["messages"]) == 1

    # Life gets worse; the watchdog notices on the next assessment.
    worse = valid_onboarding_payload()
    worse["health_inputs"]["ap_hi"] = 150
    worse["finance_inputs"]["emis"] = 20_000
    client.post("/onboard", json=worse)
    second = client.post("/assess", json=user).json()
    assert second["alerts_generated"] >= 2

    history = client.get("/history", params=user).json()["snapshots"]
    assert [s["snapshot_id"] for s in history] == [second["snapshot_id"], baseline["snapshot_id"]]
    feed = client.get("/notifications", params=user).json()
    assert {"health_score_drop", "dti_high"} <= {n["type"] for n in feed["notifications"]}

    client.post("/notifications/read", json=user)
    assert client.get("/notifications", params=user).json()["unread"] == 0
    app.state.db_engine.dispose()
