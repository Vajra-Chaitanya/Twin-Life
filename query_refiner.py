"""
query_refiner.py
First Gemini call of every advisor turn: cleans up what the user typed (typos, shorthand,
filler) into one clear sentence, without changing its meaning.

The refined text drives life-event detection, routing and narration, so a wrong rewrite
could silently change the user's data.  ``validate_refinement`` therefore rejects any
rewrite that changes amounts, drops a negation, or turns a statement into a question (or
back); on rejection or any API error the original text is used unchanged.
"""

from __future__ import annotations

import json
import re

from scenario_engine import money_amounts

SYSTEM_PROMPT = (
    "You clean up messages a user typed to their personal health, money and insurance advisor. "
    "Rewrite the CURRENT MESSAGE as clear, correctly spelled English that means exactly the same thing.\n"
    "Rules:\n"
    "- Fix typos and shorthand (\"ill\" -> \"I'll\" when it means I will, \"u\" -> \"you\", \"lakshs\"/\"lacs\" -> \"lakh\", "
    "\"emi\" -> \"EMI\", \"bp\" -> \"BP\"). Remove filler words, greetings and repeated words.\n"
    "- Keep every number and its unit exactly as written in meaning (\"50k\" stays \"50k\" or \"₹50,000\"; never change a value).\n"
    "- Keep the tense and intent: a past event stays past (\"I bought\"), a plan stays a plan (\"I'm planning to\"), "
    "a question stays a question ending with '?'. Keep negations (not, didn't, never, no).\n"
    "- Keep who it happened to (\"my mother had\" must not become \"I had\").\n"
    "- Do NOT add facts, amounts, advice or details that are not in the message. If a word like 'it' clearly refers "
    "to something in the PREVIOUS MESSAGES, you may name it, but do not copy amounts from them.\n"
    "- If the message is already clear, return it unchanged.\n"
    'Respond with ONLY JSON: {"refined": "<rewritten message>"}'
)

_NEGATION = re.compile(r"\b(not|no|never|didn'?t|don'?t|doesn'?t|haven'?t|hasn'?t|wasn'?t|isn'?t|won'?t|can'?t|cannot|nothing|none)\b"
                       r"|n't\b", re.IGNORECASE)
_FACT = re.compile(r"\b(bought|purchased|paid|had|got|took|lost|started|stopped|quit|joined|added|lent|borrowed|spent|received"
                   r"|closed|cancell?ed|subscribed|increased|decreased|diagnosed|gained|dropped|became)\b", re.IGNORECASE)


def _is_question(text: str) -> bool:
    return text.strip().endswith("?")


def validate_refinement(original: str, refined: str) -> bool:
    """True if the rewrite preserves the facts that drive data updates."""
    if not refined or len(refined) > 3 * len(original) + 120:
        return False
    if sorted(money_amounts(original)) != sorted(money_amounts(refined)):
        return False
    if bool(_NEGATION.search(original)) != bool(_NEGATION.search(refined)):
        return False
    # A question must stay a question; a reported fact must not become one (its update would be lost).
    if _is_question(original) and not _is_question(refined):
        return False
    if not _is_question(original) and _is_question(refined) and _FACT.search(original):
        return False
    return True


def refine_query(text: str, previous: list[str] | None = None, client=None, call=None) -> dict:
    """Return {"text": what the pipeline should use, "refined": bool, "error": str | None}.

    ``client``/``call`` default to the Gemini helpers and are injectable for tests.
    """
    original = text.strip()
    # Button-generated commands ("Undo ... (#12)") and tiny inputs are already exact.
    if len(original) < 4 or re.search(r"#\d+", original):
        return {"text": original, "refined": False, "error": None}
    try:
        if client is None or call is None:
            from narration_agent import _call_gemini, _get_gemini_client
            client = client or _get_gemini_client()
            call = call or _call_gemini
        user_prompt = ""
        if previous:
            user_prompt += "PREVIOUS MESSAGES (context only, do not rewrite):\n" + "\n".join(f"- {p}" for p in previous[-2:]) + "\n\n"
        user_prompt += f"CURRENT MESSAGE:\n{original}"
        raw = call(client, SYSTEM_PROMPT, user_prompt, max_retries=0)
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        refined = (json.loads(match.group(0)).get("refined") if match else "") or ""
        refined = " ".join(str(refined).split())
    except Exception as exc:  # Refinement is an enhancement; never block the answer.
        return {"text": original, "refined": False, "error": type(exc).__name__}
    if not validate_refinement(original, refined):
        return {"text": original, "refined": False, "error": "rejected"}
    return {"text": refined, "refined": refined.casefold() != original.casefold(), "error": None}
