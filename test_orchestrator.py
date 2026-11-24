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