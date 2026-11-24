from orchestrator import Orchestrator


def test_orchestrator_defers_twin_and_rag_initialization():
    orchestrator = Orchestrator({}, {}, {})

    assert orchestrator.health_twin is None
    assert orchestrator.finance_twin is None
    assert orchestrator.insurance_twin is None
    assert orchestrator.rag_agent is None
    assert orchestrator.health_profile is None
    assert orchestrator.finance_profile is None
    assert orchestrator.insurance_profile is None


def test_extract_cost_returns_none_when_amount_is_missing():
    assert Orchestrator._extract_cost("Can I afford this surgery?") is None


def test_follow_up_without_domain_words_inherits_previous_topic():
    orchestrator = Orchestrator.__new__(Orchestrator)
    state = {"query": "what about the cost?", "history": [{"query": "Which insurance riders am I missing?", "answer": "..."}]}

    result = orchestrator._route_node(state)

    assert "insurance" in result["routing"]["twins"]
    assert result["context_query"].startswith("Which insurance riders")


def test_follow_up_with_its_own_topic_is_routed_on_its_own():
    orchestrator = Orchestrator.__new__(Orchestrator)
    state = {"query": "Is my emergency fund enough?", "history": [{"query": "How is my heart?", "answer": "..."}]}

    result = orchestrator._route_node(state)

    assert result["routing"]["twins"] == ["finance"]
    assert result["context_query"] == "Is my emergency fund enough?"


def test_new_symptom_question_does_not_inherit_previous_finance_topic():
    orchestrator = Orchestrator.__new__(Orchestrator)
    state = {
        "query": "I feel weak, suggest me something",
        "history": [{"query": "What if I take a ₹10,000 EMI?", "answer": "..."}],
    }

    result = orchestrator._route_node(state)

    assert result["routing"]["twins"] == ["health"]
    assert result["context_query"] == "I feel weak, suggest me something"


def test_simulation_takes_cost_from_earlier_turn(monkeypatch):
    import orchestrator as orch

    seen = {}

    class FakeSimulator:
        def __init__(self, **kwargs):
            pass

        def evaluate_treatment(self, cost, condition):
            seen.update(cost=cost, condition=condition)
            return {"recommendation": "ok", "tool_trace": [], "iterations": 1}

    monkeypatch.setattr(orch, "CombinedSimulator", FakeSimulator)
    o = Orchestrator.__new__(Orchestrator)
    o.health_profile, o.finance_profile, o.finance_twin = {}, {}, object()
    o.insurance_twin, o.insurance_inputs = object(), {}
    state = {
        "query": "and can I afford that treatment?",
        "context_query": "diabetes surgery 2 lakh and can I afford that treatment?",
        "history": [{"query": "My diabetes surgery costs 2 lakh", "answer": "..."}],
        "routing": {"simulate": True},
    }

    result = o._simulation_node(state)

    assert result["simulation_result"]["recommendation"] == "ok"
    assert seen == {"cost": 200_000, "condition": "diabetes"}


def test_follow_up_amount_is_computed_against_thread_topic():
    o = Orchestrator.__new__(Orchestrator)
    o.health_inputs = {}
    o.finance_inputs = {"income": 120_000, "fixed_expenses": 30_000, "variable_expenses": 25_000, "emis": 8_000, "savings_balance": 450_000}
    o.insurance_inputs, o.health_profile, o.health_assess = {}, None, None
    state = {"query": "what if it is 10k?", "context_query": "Bike EMI of 15000 per month? what if it is 10k?"}

    [scenario] = o._compute_scenarios(state)

    assert scenario["kind"] == "emi" and scenario["headline"] == "₹10,000/month EMI"


def test_simulation_does_not_run_without_explicit_cost():
    orchestrator = Orchestrator.__new__(Orchestrator)
    state = {
        "query": "Can I afford this surgery?",
        "routing": {"simulate": True},
    }

    result = orchestrator._simulation_node(state)

    assert result["simulation_result"] == {
        "error": "Please include a specific treatment cost to run this simulation."
    }