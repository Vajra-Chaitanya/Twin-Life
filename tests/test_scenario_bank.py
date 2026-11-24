import pytest

from evaluation.eval_heldout import HELD_OUT
from evaluation.eval_scenarios import CASES, evaluate

ALL = CASES + HELD_OUT


@pytest.mark.parametrize("case", ALL, ids=[f"{c.domain}:{c.text[:50]}" for c in ALL])
def test_advisor_behaviour(case):
    result = evaluate(case)
    diff = {k: {"got": result["got"][k], "want": result["want"][k]}
            for k in result["want"] if result["got"][k] != result["want"][k]}
    assert result["ok"], diff
