import narration_agent


def test_truncated_answer_is_trimmed_to_last_complete_line():
    text = "**Verdict.**\n\nYour plan:\n1. Quit smoking.\n2. Schedule a comprehensive cardiovascular evaluation to mon"
    assert narration_agent._trim_to_complete(text).endswith("1. Quit smoking.")
    assert narration_agent._trim_to_complete("Done.") == "Done."


def test_score_components_are_not_described_as_risk():
    line = narration_agent._impact_line({"label": "Cardiovascular model", "before": 52.9, "after": 52.5,
                                         "weight_percent": 25, "before_weighted_points": 13.2,
                                         "after_weighted_points": 13.1, "note": "x"})
    assert "not a risk %" in line and "Health model impact" not in line


def test_explanation_prompt_includes_question_and_recent_history(monkeypatch):
    captured = {}
    monkeypatch.setattr(narration_agent, "_get_gemini_client", lambda: object())
    monkeypatch.setattr(
        narration_agent,
        "_call_gemini",
        lambda client, system, user, **kw: captured.update(system=system, user=user) or "answer",
    )
    history = [{"query": f"q{i}", "answer": f"a{i}"} for i in range(5)]

    result = narration_agent.generate_explanation(
        twin_outputs={}, shap_features=[], rag_chunks=[], question="How can I improve it?", history=history,
    )

    assert result == "answer"
    assert "=== CURRENT QUESTION ===\nHow can I improve it?" in captured["user"]
    assert "User: q4\nAdvisor: a4" in captured["user"]
    assert "q1" not in captured["user"]
    assert "follow-ups" in captured["system"]


def test_explanation_prompt_without_question_keeps_original_behaviour(monkeypatch):
    captured = {}
    monkeypatch.setattr(narration_agent, "_get_gemini_client", lambda: object())
    monkeypatch.setattr(narration_agent, "_call_gemini", lambda client, system, user, **kw: captured.update(user=user) or "x")

    narration_agent.generate_explanation(twin_outputs={}, shap_features=[], rag_chunks=["guide"])

    assert "CURRENT QUESTION" not in captured["user"]
    assert "CONVERSATION SO FAR" not in captured["user"]


def test_computed_scenario_and_percentages_reach_the_prompt(monkeypatch):
    captured = {}
    monkeypatch.setattr(narration_agent, "_get_gemini_client", lambda: object())
    monkeypatch.setattr(narration_agent, "_call_gemini", lambda client, system, user, **kw: captured.update(system=system, user=user) or "x")
    scenario = {
        "headline": "₹15,000/month EMI", "verdict": "risky",
        "facts": ["Debt-to-income goes from 32% to 44%"], "actions": ["Bring the EMI down to about ₹5,200/month"],
        "assumptions": ["Tenure not given"],
    }

    narration_agent.generate_explanation(
        twin_outputs={"finance": {"dti_ratio": 0.32, "monthly_income": 120000}, "scenarios": [scenario]},
        shap_features=[], rag_chunks=[], question="How does a 15k EMI affect me?",
    )

    assert "Verdict: RISKY" in captured["user"]
    assert "- Debt-to-income goes from 32% to 44%" in captured["user"]
    assert "- Bring the EMI down to about ₹5,200/month" in captured["user"]
    assert "Debt-to-income: 32%" in captured["user"]
    assert "vague phrases" in captured["system"]


def test_life_context_reaches_the_prompt(monkeypatch):
    captured = {}
    monkeypatch.setattr(narration_agent, "_get_gemini_client", lambda: object())
    monkeypatch.setattr(narration_agent, "_call_gemini", lambda client, system, user, **kw: captured.update(system=system, user=user) or "x")
    life = {
        "commitments": [{"item": "car", "emi": 15000, "end": "2031-11-24"}],
        "recent_events": [{"date": "2026-11-24", "summary": "Had a heart attack"}],
        "just_recorded": [{"summary": "Car loan EMI ₹15,000", "changes": [{"label": "Debt-to-income %", "before": 35, "after": 50}]}],
        "pending_questions": ["How much more per month are your medical costs?"],
    }

    narration_agent.generate_explanation(twin_outputs={"life_context": life}, shap_features=[], rag_chunks=[], question="Should I buy a bike?")

    assert "Car EMI Rs.15,000/month until 2031-11-24" in captured["user"]
    assert "- 2026-11-24: Had a heart attack" in captured["user"]
    assert "Debt-to-income %: 35 -> 50" in captured["user"]
    assert "- How much more per month are your medical costs?" in captured["user"]
    assert "ACTIVE COMMITMENTS" in captured["system"]


def test_system_prompt_requires_question_relevance(monkeypatch):
    captured = {}
    monkeypatch.setattr(narration_agent, "_get_gemini_client", lambda: object())
    monkeypatch.setattr(narration_agent, "_call_gemini", lambda client, system, user, **kw: captured.update(system=system) or "x")

    narration_agent.generate_explanation(twin_outputs={}, shap_features=[], rag_chunks=[], question="Is ice cream bad?")

    assert "personally assigned expert team" in captured["system"]
    for section in ("For you specifically", "What happens", "Effect on your scores", "Your plan", "Try a simulation"):
        assert section in captured["system"]
    assert "Expert assessment" in captured["system"] and "do NOT stop at 'not modeled'" in captured["system"]
