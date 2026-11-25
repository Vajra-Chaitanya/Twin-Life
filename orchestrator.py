"""
Module 6 -- orchestrator.py
LangGraph-based orchestrator for TwinLife AI.

Defines a state-graph with nodes for each twin (health, finance, insurance),
a RAG node, a narration node, and a combined-simulator node. Routes queries
using two-step logic: keyword matching first, LLM fallback for ambiguous cases.

Usage:
    orch = Orchestrator(user_health_inputs, user_finance_inputs,
                        user_insurance_inputs)
    result = orch.process_query("Can I afford this surgery?")
"""

from __future__ import annotations

import os
import re
import json
import warnings
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.genai import types as genai_types
from langgraph.graph import StateGraph, END

from health_twin import HealthTwin
from finance_twin import FinanceTwin
from insurance_twin import InsuranceTwin
from rag_agent import RAGAgent
from narration_agent import generate_explanation, generate_ranked_whatifs
from combined_simulator import CombinedSimulator
from scenario_engine import analyze_question
from event_engine import HYPOTHETICAL

load_dotenv()
warnings.filterwarnings("ignore", category=UserWarning)


# ---------------------------------------------------------------------------
#  KEYWORD ROUTING TABLES (Step 1: deterministic, no API call)
#  Regex fragments matched on word boundaries ("premium" must not match "emi").
# ---------------------------------------------------------------------------
HEALTH_KEYWORDS = [
    r"diabet\w*", "weight", "overweight", "blood", "bp", "bmi", r"obes\w*", "cholesterol", r"cardio\w*", "cvd",
    "heart", "glucose", "sugar", "hba1c", r"hypertensi\w*", r"smok\w*", r"cigarettes?", "fitness", "health",
    "stroke", "cancer", "angioplasty", r"pregnan\w*", r"alcohol\w*", r"drink\w*", "beer",
    "weak", r"weakness", r"fatigue\w*", "tired", r"exhaust\w*", "drained", "lethargic", r"dizz\w*", r"faint\w*",
    "fever", r"cough\w*", "cold", "flu", r"nause\w*", r"vomit\w*", "unwell",
    r"symptoms?", "pain", r"\w*aches?", "hurts?", r"breath\w*", "sleep", r"stress\w*", r"anxi\w*", r"depress\w*",
    "energy", "sick", "not feeling well", r"knees?", "medical", r"medicin\w*", r"doctors?", "cardiologist",
    "dengue", "malaria", "typhoid", "covid", "corona", "jaundice", "pneumonia", r"fractur\w*", r"injur\w*",
    r"sprain\w*", "migraine", r"allerg\w*", "asthma", r"infection\w*", "viral", "flu", r"illness\w*",
    r"check-?ups?", r"recover\w*", "family history", "diet", "eat", "junk food", r"calories?", "protein",
    r"vitamins?", r"supplements?", "water", "fasting", r"exercis\w*", "gym", "yoga", r"walk\w*", r"run\w*",
    r"cycl\w*", r"swim\w*", r"jog\w*", r"(?:[89]\d|1\d\d|2[0-4]\d)\s*/\s*(?:[4-9]\d|1[0-4]\d)(?!\s*/)",
    "steps", r"workouts?", "belly fat", "kg", "sit all day",
]
FINANCE_KEYWORDS = [
    r"sav(?:e|es|ed|ing|ings)", r"afford\w*", r"loans?", "emis?", "debt", "income", r"expenses?", "budget",
    r"invest\w*", r"financ\w*", "money", r"salary", "dti", "emergency fund", "disposable", r"\w*spend\w*",
    "rent", "job", "laid off", "fired", "hike", r"raises?", "increment", r"promot\w*", "bonus", r"inherit\w*", r"earn\w*",
    "bank", "fd", "fixed deposit", "sip", r"retire\w*", "tax", "cash", "credit card", "bills?", "fees",
    r"outflows?", "stability", "50/30/20", "lend", r"interest",
]
# Generic money words: they mean "finance" unless the question is about insurance (premium cost, cover amount).
FINANCE_WEAK_KEYWORDS = [
    "buy", r"bought", r"purchas\w*", r"costs?", r"costing", "price", "worth", "spent", "paid", "pay",
    "lakh", "crore", r"\d+k", r"trips?", r"vacations?", r"holidays?", "travel", "phone", "iphone", "laptop", "car",
    "bike", "scooter", "house", "flat", "gold",
    r"wedding", r"renovat\w*", r"per month", r"a month",
]
INSURANCE_KEYWORDS = [
    r"cover\w*", "premium", r"claims?", r"riders?", r"insur\w*", r"polic(?:y|ies)", "deductible", "cashless",
    "co-?pay", "floater", "super top-?up", "waiting period", "lapsed", "opd", "room rent", "sub-?limit",
    "restore benefit", "free look", "exclusions?", r"renew\w*", r"ported", "maternity", "ambulance",
]
CROSS_DOMAIN_KEYWORDS = [
    "treatment", "medication", "surgery", "procedure", r"hospital\w*", "operation", "medical",
]
COST_KEYWORDS = [
    r"costs?", r"costing", "price", "expensive", r"afford\w*", "pay", "paid", r"bills?", "rs", r"rupees?",
    "lakh", "crore", "inr",
]
# Phrases whose words would otherwise pull in the wrong twin.
ROUTING_PHRASES = [
    (r"health (?:insurance|cover|policy|plan)|mediclaim|hospital cash|personal accident|critical illness"
     r"|life cover|term (?:plan|insurance)|no claim bonus|room rent|super top[- ]?up", " insurance "),
    (r"financial health|money health", " finances "),
    (r"\b(emis?|loans?) (?:are |is )?running\b", r" \1 active "),
]


def _kw_regex(words: list[str]) -> re.Pattern:
    return re.compile(r"(?<![\w-])(?:" + "|".join(words) + r")(?![\w-])", re.IGNORECASE)


_HEALTH_RE, _FINANCE_RE, _FINANCE_WEAK_RE, _INSURANCE_RE, _CROSS_RE, _COST_RE = map(_kw_regex, (
    HEALTH_KEYWORDS, FINANCE_KEYWORDS, FINANCE_WEAK_KEYWORDS, INSURANCE_KEYWORDS, CROSS_DOMAIN_KEYWORDS,
    COST_KEYWORDS,
))


def _normalize_for_routing(query: str) -> str:
    q = query.lower()
    for pattern, replacement in ROUTING_PHRASES:
        q = re.sub(pattern, replacement, q)
    return q


# ---------------------------------------------------------------------------
#  ORCHESTRATOR STATE
# ---------------------------------------------------------------------------
class OrchestratorState(dict):
    """TypedDict-like state for the LangGraph orchestrator.

    Keys:
        query (str):              The user's natural-language query.
        routing (dict):           Routing decision from route_query().
        health_profile (dict):    Output from HealthTwin.assess().
        finance_profile (dict):   Output from FinanceTwin.assess().
        insurance_profile (dict): Output from InsuranceTwin.assess().
        rag_chunks (list[str]):   Retrieved guideline chunks.
        simulation_result (dict): Output from CombinedSimulator.
        narration (str):          Final narrated explanation.
        error (str | None):       Error message if any step fails.
    """
    pass


# ---------------------------------------------------------------------------
#  ORCHESTRATOR CLASS
# ---------------------------------------------------------------------------
class Orchestrator:
    """LangGraph-based orchestrator coordinating all TwinLife AI modules.

    Routes queries to the appropriate twin(s), retrieves RAG context,
    and narrates the final explanation using the Gemini API.

    Args:
        health_inputs:    Dict of user health vitals (for HealthTwin).
        finance_inputs:   Dict of user financial data (for FinanceTwin).
        insurance_inputs: Dict of user insurance data (for InsuranceTwin).
    """

    def __init__(
        self,
        health_inputs: dict,
        finance_inputs: dict,
        insurance_inputs: dict,
    ) -> None:
        self.health_inputs = health_inputs
        self.finance_inputs = finance_inputs
        self.insurance_inputs = insurance_inputs

        self.health_twin = None
        self.finance_twin = None
        self.insurance_twin = None
        self.rag_agent = None
        self.health_profile = None
        self.finance_profile = None
        self.insurance_profile = None
        # Optional callable(inputs) -> health profile, used to re-run the model for health what-ifs.
        self.health_assess = None

        # Build LangGraph
        self.graph = self._build_graph()

    # ------------------------------------------------------------------
    #  ROUTING LOGIC (Two-Step)
    # ------------------------------------------------------------------
    def route_query(self, query: str) -> dict:
        """Route a query to the appropriate twin(s).

        Step 1: Keyword-based deterministic matching.
        Step 2: LLM fallback for ambiguous queries.

        Args:
            query: Natural language query from the user.

        Returns:
            {"twins": [...], "mode": "single-domain"|"cross-domain",
             "simulate": bool}
        """
        q_lower = _normalize_for_routing(query)

        # --- Step 1: Keyword matching ---
        cross_match = bool(_CROSS_RE.search(q_lower))
        health_match = bool(_HEALTH_RE.search(q_lower)) or cross_match
        insurance_match = bool(_INSURANCE_RE.search(q_lower))
        finance_match = bool(_FINANCE_RE.search(q_lower)) or (
            not insurance_match and bool(_FINANCE_WEAK_RE.search(q_lower) or "₹" in q_lower)
        )
        cost_match = bool(_COST_RE.search(q_lower)) or "₹" in q_lower

        # Cross-domain: treatment/medication + cost word → all three + simulate
        if cross_match and cost_match:
            return {
                "twins": ["health", "finance", "insurance"],
                "mode": "cross-domain",
                "simulate": True,
            }

        # Single-domain matches
        matched_twins = []
        if health_match:
            matched_twins.append("health")
        if finance_match:
            matched_twins.append("finance")
        if insurance_match:
            matched_twins.append("insurance")

        if matched_twins:
            return {
                "twins": matched_twins,
                "mode": "single-domain" if len(matched_twins) == 1 else "cross-domain",
                "simulate": cross_match or (len(matched_twins) > 1 and cost_match),
            }

        # --- Step 2: LLM fallback for ambiguous queries ---
        return self._llm_route(query)

    def _llm_route(self, query: str) -> dict:
        """Use Gemini API to determine routing for ambiguous queries."""
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            # Fallback: route to all twins if no API key
            return {
                "twins": ["health", "finance", "insurance"],
                "mode": "cross-domain",
                "simulate": False,
            }

        client = genai.Client(api_key=api_key)

        system_prompt = (
            "You are a query router for a digital twin system with three domains: "
            "health, finance, insurance. Given a user query, respond ONLY with "
            "valid JSON (no markdown, no explanation) in this exact format:\n"
            '{"twins": ["health"], "mode": "single-domain", "simulate": false}\n'
            "Rules:\n"
            "- twins: list containing one or more of: health, finance, insurance\n"
            "- mode: 'single-domain' if only one twin, 'cross-domain' if multiple\n"
            "- simulate: true if the query involves comparing costs or what-if scenarios\n"
            "Respond with ONLY the JSON object, nothing else."
        )

        try:
            response = client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=[genai_types.Content(
                    role="user",
                    parts=[genai_types.Part.from_text(text=f"Route this query: {query}")],
                )],
                config=genai_types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.0,
                ),
            )
            text = response.candidates[0].content.parts[0].text.strip()
            # Strip markdown code fences if present
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
            result = json.loads(text)
            # Validate keys
            if "twins" in result and "mode" in result:
                return result
        except Exception:
            pass

        # Default fallback
        return {
            "twins": ["health", "finance", "insurance"],
            "mode": "cross-domain",
            "simulate": False,
        }

    # ------------------------------------------------------------------
    #  LANGGRAPH NODE FUNCTIONS
    # ------------------------------------------------------------------
    def _get_health_profile(self) -> dict:
        if self.health_profile is None:
            if self.health_twin is None:
                self.health_twin = HealthTwin()
            self.health_profile = self.health_twin.assess(self.health_inputs)
        return self.health_profile

    def _get_finance_profile(self) -> dict:
        if self.finance_profile is None:
            if self.finance_twin is None:
                self.finance_twin = FinanceTwin()
            self.finance_profile = self.finance_twin.assess(self.finance_inputs)
        return self.finance_profile

    def _get_insurance_profile(self) -> dict:
        if self.insurance_profile is None:
            if self.insurance_twin is None:
                self.insurance_twin = InsuranceTwin()
            self.insurance_profile = self.insurance_twin.assess(
                self.insurance_inputs,
                self._get_health_profile(),
                self._get_finance_profile(),
            )
        return self.insurance_profile

    def _get_rag_agent(self) -> RAGAgent:
        if self.rag_agent is None:
            self.rag_agent = RAGAgent()
            self.rag_agent.build_index()
        return self.rag_agent

    def _health_node(self, state: dict) -> dict:
        """Execute HealthTwin assessment."""
        state["health_profile"] = self._get_health_profile()
        return state

    def _finance_node(self, state: dict) -> dict:
        """Execute FinanceTwin assessment."""
        state["finance_profile"] = self._get_finance_profile()
        return state

    def _insurance_node(self, state: dict) -> dict:
        """Execute InsuranceTwin assessment."""
        state["insurance_profile"] = self._get_insurance_profile()
        return state

    def _rag_node(self, state: dict) -> dict:
        """Retrieve relevant guideline chunks via RAG."""
        query = state.get("context_query") or state.get("query", "")
        chunks = self._get_rag_agent().retrieve(query, top_k=3)
        state["rag_chunks"] = chunks
        return state

    def _simulation_node(self, state: dict) -> dict:
        """Run the Combined Simulator agent (if routing says simulate)."""
        routing = state.get("routing", {})
        if not routing.get("simulate", False):
            state["simulation_result"] = None
            return state

        try:
            # Extract cost from query (simple regex for Rs./₹ amounts), falling back to earlier turns.
            query = state.get("query", "")
            context = state.get("context_query") or query
            cost = self._extract_cost(query)
            if cost is None:
                for turn in reversed(state.get("history") or []):
                    cost = self._extract_cost(turn.get("query", ""))
                    if cost is not None:
                        break
            if cost is None:
                state["simulation_result"] = {
                    "error": "Please include a specific treatment cost to run this simulation."
                }
                return state
            condition = self._extract_condition(context)
            self._get_finance_profile()
            if self.insurance_twin is None:
                self.insurance_twin = InsuranceTwin()

            sim = CombinedSimulator(
                health_profile=self._get_health_profile(),
                finance_twin=self.finance_twin,
                insurance_twin=self.insurance_twin,
                insurance_inputs=self.insurance_inputs,
            )
            result = sim.evaluate_treatment(cost=cost, condition=condition)
            state["simulation_result"] = result
        except Exception as e:
            state["simulation_result"] = {"error": str(e)}

        return state

    def _narration_node(self, state: dict) -> dict:
        """Generate final narrated explanation."""
        twin_outputs = {}
        if state.get("health_profile"):
            twin_outputs["health"] = state["health_profile"]
        if state.get("finance_profile"):
            twin_outputs["finance"] = state["finance_profile"]
        if state.get("insurance_profile"):
            twin_outputs["insurance"] = state["insurance_profile"]
        if state.get("simulation_result"):
            twin_outputs["simulation"] = state["simulation_result"]

        scenarios = self._compute_scenarios(state)
        state["scenarios"] = scenarios
        if scenarios:
            twin_outputs["scenarios"] = scenarios
        if state.get("life_context"):
            twin_outputs["life_context"] = state["life_context"]
        if state.get("domain"):
            twin_outputs["domain_focus"] = state["domain"]

        shap_features = []
        hp = state.get("health_profile", {})
        if hp:
            shap_features = hp.get("shap_top_features", [])

        rag_chunks = state.get("rag_chunks", [])

        try:
            narration = generate_explanation(
                twin_outputs=twin_outputs,
                shap_features=shap_features,
                rag_chunks=rag_chunks,
                question=state.get("query"),
                history=state.get("history"),
            )
            state["narration"] = narration
        except Exception as e:
            state["narration"] = f"[Narration error: {e}]"

        return state

    # ------------------------------------------------------------------
    #  GRAPH BUILDER
    # ------------------------------------------------------------------
    def _build_graph(self) -> Any:
        """Build the LangGraph state graph."""
        builder = StateGraph(dict)

        # Add nodes
        builder.add_node("route", self._route_node)
        builder.add_node("health", self._health_node)
        builder.add_node("finance", self._finance_node)
        builder.add_node("insurance", self._insurance_node)
        builder.add_node("rag", self._rag_node)
        builder.add_node("simulate", self._simulation_node)
        builder.add_node("narrate", self._narration_node)

        # Entry point
        builder.set_entry_point("route")

        # Conditional edges from route
        def route_decision(state: dict) -> str:
            """Determine next node after routing."""
            twins = state.get("routing", {}).get("twins", [])
            if "health" in twins:
                return "health"
            elif "finance" in twins:
                return "finance"
            elif "insurance" in twins:
                return "insurance"
            return "rag"

        builder.add_conditional_edges(
            "route",
            route_decision,
            {
                "health": "health",
                "finance": "finance",
                "insurance": "insurance",
                "rag": "rag",
            },
        )

        # After health → finance (if needed) or rag
        def after_health(state: dict) -> str:
            twins = state.get("routing", {}).get("twins", [])
            if "finance" in twins:
                return "finance"
            return "rag"

        builder.add_conditional_edges(
            "health", after_health, {"finance": "finance", "rag": "rag"},
        )

        # After finance → insurance (if needed) or rag
        def after_finance(state: dict) -> str:
            twins = state.get("routing", {}).get("twins", [])
            if "insurance" in twins:
                return "insurance"
            return "rag"

        builder.add_conditional_edges(
            "finance", after_finance, {"insurance": "insurance", "rag": "rag"},
        )

        # After insurance → rag
        builder.add_edge("insurance", "rag")

        # After rag → simulate (if needed) or narrate
        def after_rag(state: dict) -> str:
            if state.get("routing", {}).get("simulate", False):
                return "simulate"
            return "narrate"

        builder.add_conditional_edges(
            "rag", after_rag, {"simulate": "simulate", "narrate": "narrate"},
        )

        # After simulate → narrate
        builder.add_edge("simulate", "narrate")

        # After narrate → END
        builder.add_edge("narrate", END)

        return builder.compile()

    def _compute_scenarios(self, state: dict) -> list[dict]:
        """Exact before/after numbers for concrete changes in the question (or, for follow-ups, the thread)."""
        # A message that reported real events (recorded, or waiting on a missing detail) is not a what-if:
        # computing one would double-count it or invent numbers from earlier turns.
        life = state.get("life_context") or {}
        recorded = life.get("just_recorded") or []
        diet_only = recorded and all(e["summary"].startswith("Diet or supplement reported") for e in recorded)
        if (recorded and not diet_only) or life.get("just_reverted") or life.get("pending_questions"):
            return []
        query = state.get("query", "")
        if not diet_only and not self._asks_or_plans(query):
            return []  # A plain statement ("I walk 10000 steps") is context, not a what-if.
        try:
            context = state.get("context_query") or query
            # Follow-ups: intent from the thread context, amounts from the latest message.
            attempts = [(context, query), (query, None)] if context != query else [(query, None)]
            for text, focus in attempts:
                scenarios = analyze_question(
                    text,
                    self.health_inputs,
                    self.finance_inputs,
                    self.insurance_inputs,
                    health_profile=state.get("health_profile") or self.health_profile,
                    health_assess=self.health_assess,
                    focus=focus,
                )
                if scenarios:
                    return scenarios
        except Exception:  # A parsing/calculation problem must not break the answer.
            return []
        return []

    def _route_node(self, state: dict) -> dict:
        """Initial routing node."""
        query = state.get("query", "")
        history = state.get("history") or []
        # Follow-ups without domain words ("what about the cost?") inherit the previous topic.
        if history and not self._has_domain_keyword(query):
            context = f"{history[-1].get('query', '')} {query}".strip()
        else:
            context = query
        state["context_query"] = context
        if state.get("domain"):
            # Twin pages each have their own chat that only answers for that twin.
            state["routing"] = {"twins": [state["domain"]], "mode": "single-domain", "simulate": False}
        else:
            state["routing"] = self.route_query(context)
        return state

    @staticmethod
    def _asks_or_plans(query: str) -> bool:
        q = query.strip().lower()
        return q.endswith("?") or bool(HYPOTHETICAL.search(q)) or bool(re.match(
            r"(how|what|which|why|when|is|are|am|do|does|can|could|should|will|would|and|tell|show|compare|calculate)\b", q,
        ))

    @staticmethod
    def _has_domain_keyword(query: str) -> bool:
        # Generic money words ("10k", "per month") don't start a new topic; they refine the previous one.
        q = _normalize_for_routing(query)
        return any(r.search(q) for r in (_HEALTH_RE, _FINANCE_RE, _INSURANCE_RE, _CROSS_RE))

    # ------------------------------------------------------------------
    #  PUBLIC API
    # ------------------------------------------------------------------
    def process_query(
        self, query: str, history: list[dict] | None = None, life_context: dict | None = None, domain: str | None = None,
    ) -> dict:
        """Process a user query through the full orchestrator pipeline.

        Args:
            query: Natural language query from the user.
            history: Earlier turns of this conversation, oldest first:
                [{"query": str, "answer": str}, ...].

        Returns:
            Final state dict containing routing, profiles, RAG chunks,
            simulation result (if any), and narration.
        """
        initial_state = {
            "query": query,
            "history": list(history or []),
            "life_context": life_context or {},
            "domain": domain,
            "context_query": query,
            "scenarios": [],
            "routing": {},
            "health_profile": None,
            "finance_profile": None,
            "insurance_profile": None,
            "rag_chunks": [],
            "simulation_result": None,
            "narration": "",
            "error": None,
        }

        result = self.graph.invoke(initial_state)
        return result

    # ------------------------------------------------------------------
    #  HELPERS
    # ------------------------------------------------------------------
    @staticmethod
    def _extract_cost(query: str) -> float | None:
        """Extract a monetary amount from a query string."""
        # Match patterns like: Rs.500000, ₹5,00,000, 5 lakh, 500000
        patterns = [
            r"(?:rs\.?|₹|inr)\s*([\d,]+(?:\.\d+)?)",
            r"([\d.]+)\s*(?:lakh|lac)",
            r"([\d.]+)\s*(?:crore|cr)",
            r"\b(\d{4,})\b",  # bare numbers >= 1000
        ]
        q_lower = query.lower()
        for i, pat in enumerate(patterns):
            match = re.search(pat, q_lower, re.IGNORECASE)
            if match:
                val = match.group(1).replace(",", "")
                num = float(val)
                if i == 1:  # lakh
                    num *= 100_000
                elif i == 2:  # crore
                    num *= 10_000_000
                return num
        return None

    @staticmethod
    def _extract_condition(query: str) -> str:
        """Extract medical condition from a query string."""
        q_lower = query.lower()
        if any(w in q_lower for w in ["diabetes", "glucose", "sugar", "hba1c"]):
            return "diabetes"
        if any(w in q_lower for w in ["blood pressure", "hypertension", "bp"]):
            return "hypertension"
        return "cardio"  # default


# ======================================================================
#  STANDALONE VERIFICATION (python orchestrator.py)
# ======================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("  Module 6: Orchestrator — Routing & Pipeline Test")
    print("=" * 60)

    # --- Test routing logic only (no full pipeline) ---
    # Create a temporary orchestrator-like object for routing tests
    class RoutingTester:
        """Minimal class to test route_query without full init."""
        route_query = Orchestrator.route_query
        _llm_route = Orchestrator._llm_route

    tester = RoutingTester()

    test_queries = [
        "What is my blood pressure status?",
        "Can I afford a ₹5,00,000 heart surgery?",
        "How much is my insurance coverage?",
        "Am I saving enough money?",
        "I need a treatment for diabetes costing Rs.300000",
        "Tell me about my overall well-being",
    ]

    for query in test_queries:
        routing = tester.route_query(query)
        print(f"\n  Query: \"{query}\"")
        print(f"  Routing: {json.dumps(routing)}")

    print("\n" + "=" * 60)
    print("  Full pipeline test requires all twins initialized.")
    print("  Use the full Orchestrator class with valid inputs.")
    print("=" * 60)
