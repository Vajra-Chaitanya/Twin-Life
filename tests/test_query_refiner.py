import pytest

from query_refiner import refine_query, validate_refinement


def fake(reply):
    calls = []

    def call(client, system, user, **kw):
        calls.append(user)
        if isinstance(reply, Exception):
            raise reply
        return reply

    return call, calls


@pytest.mark.parametrize(
    "original, refined",
    [("i got promotion ill extra 50k every month", "I got a promotion; I'll get an extra ₹50,000 every month."),
     ("had a surgery and paid 3 lakshs", "I had a surgery and paid 3 lakh."),
     ("hw is my hart", "How is my heart?"),
     ("i didnt buy the car", "I didn't buy the car.")],
)
def test_valid_rewrites_are_accepted(original, refined):
    assert validate_refinement(original, refined)


@pytest.mark.parametrize(
    "original, refined",
    [("paid 3 lakh for surgery", "I paid 30 lakh for surgery."),          # amount changed
     ("i didnt buy the car", "I bought the car."),                       # negation dropped
     ("can i afford a bike for 1 lakh?", "I can afford a bike for 1 lakh."),  # question became statement
     ("i bought a bike", "Should I buy a bike?"),                        # fact became question
     ("bp high", "x" * 500)],                                            # runaway output
)
def test_meaning_changing_rewrites_are_rejected(original, refined):
    assert not validate_refinement(original, refined)


def test_refine_uses_gemini_output_and_previous_context():
    call, calls = fake('{"refined": "I borrowed it from my aunt."}')
    out = refine_query("i took it frm my aunty", ["I had a surgery and paid 3 lakh."], client=object(), call=call)
    assert out == {"text": "I borrowed it from my aunt.", "refined": True, "error": None}
    assert "PREVIOUS MESSAGES" in calls[0] and "3 lakh" in calls[0]


def test_refine_falls_back_to_original_on_error_or_rejection():
    call, _ = fake(RuntimeError("503 UNAVAILABLE"))
    assert refine_query("hw is my hart", client=object(), call=call) == {"text": "hw is my hart", "refined": False, "error": "RuntimeError"}
    call, _ = fake('{"refined": "I paid 5 lakh"}')
    assert refine_query("paid 3 lakh", client=object(), call=call)["text"] == "paid 3 lakh"


def test_button_commands_skip_refinement():
    call, calls = fake('{"refined": "x"}')
    assert refine_query('Undo "Took car" (#12)', client=object(), call=call)["text"] == 'Undo "Took car" (#12)'
    assert calls == []
