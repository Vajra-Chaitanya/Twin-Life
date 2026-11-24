"""Local FastAPI entry point for TwinLife AI."""

from __future__ import annotations

import math
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator, Literal

import numpy as np
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi import Path as PathParam
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, create_engine, select

from finance_twin import FinanceTwin
from insurance_twin import InsuranceTwin
from recommendation_engines import purchase_impact_simulator
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool


class Base(DeclarativeBase):
    pass


class UserRecord(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )


class HealthInputRecord(Base):
    __tablename__ = "health_inputs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )


class FinanceInputRecord(Base):
    __tablename__ = "finance_inputs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )


class InsuranceInputRecord(Base):
    __tablename__ = "insurance_inputs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )


class SnapshotRecord(Base):
    __tablename__ = "snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )


class NotificationRecord(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )


class ChatHistoryRecord(Base):
    __tablename__ = "chat_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), index=True)
    query: Mapped[str] = mapped_column(String)
    result: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )


class LifeEventRecord(Base):
    __tablename__ = "life_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )


class ChatThreadRecord(Base):
    """User-chosen conversation titles (threads themselves live in chat_history)."""

    __tablename__ = "chat_threads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), index=True)
    thread_id: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(120))


class RenameThreadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=120)


class HealthInputs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    age: int = Field(ge=1, le=120)
    gender: Literal["male", "female"]
    height_cm: float = Field(gt=0)
    weight_kg: float = Field(gt=0)
    ap_hi: float = Field(gt=0)
    ap_lo: float = Field(gt=0)
    cholesterol: int = Field(ge=1, le=3)
    gluc: int = Field(ge=1, le=3)
    smoke: int = Field(ge=0, le=1)
    alco: int = Field(ge=0, le=1)
    active: int = Field(ge=0, le=1)
    blood_glucose_level: float = Field(default=90, gt=0)
    hba1c: float | None = Field(default=None, gt=2, le=20)
    conditions: list[str] = Field(default_factory=list, max_length=20)


class FinanceInputs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    income: float = Field(gt=0)
    fixed_expenses: float = Field(ge=0)
    variable_expenses: float = Field(ge=0)
    emis: float = Field(ge=0)
    savings_balance: float = Field(ge=0)


class Policy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["vehicle", "life", "home", "travel", "health_topup", "gadget", "other"]
    name: str = Field(min_length=1, max_length=80)
    cover: float = Field(default=0, ge=0)
    premium: float = Field(default=0, ge=0)
    renewal_date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")


class InsuranceInputs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sum_insured: float = Field(ge=0)
    annual_premium: float = Field(ge=0)
    annual_income: float | None = Field(default=None, gt=0)
    existing_riders: list[str] = Field(default_factory=list)
    # Non-health policies (vehicle, life, home...). Health cover stays in sum_insured.
    policies: list[Policy] = Field(default_factory=list, max_length=30)


class OnboardRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(min_length=1, max_length=100)
    health_inputs: HealthInputs
    finance_inputs: FinanceInputs
    insurance_inputs: InsuranceInputs


class AssessRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(min_length=1, max_length=100)


class HealthOverrides(BaseModel):
    model_config = ConfigDict(extra="forbid")

    age: int | None = Field(default=None, ge=1, le=120)
    height_cm: float | None = Field(default=None, gt=0)
    weight_kg: float | None = Field(default=None, gt=0)
    ap_hi: float | None = Field(default=None, gt=0)
    ap_lo: float | None = Field(default=None, gt=0)
    cholesterol: int | None = Field(default=None, ge=1, le=3)
    gluc: int | None = Field(default=None, ge=1, le=3)
    smoke: int | None = Field(default=None, ge=0, le=1)
    alco: int | None = Field(default=None, ge=0, le=1)
    active: int | None = Field(default=None, ge=0, le=1)
    blood_glucose_level: float | None = Field(default=None, gt=0)


class FinanceOverrides(BaseModel):
    model_config = ConfigDict(extra="forbid")

    income: float | None = Field(default=None, gt=0)
    fixed_expenses: float | None = Field(default=None, ge=0)
    variable_expenses: float | None = Field(default=None, ge=0)
    emis: float | None = Field(default=None, ge=0)
    savings_balance: float | None = Field(default=None, ge=0)


class InsuranceOverrides(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sum_insured: float | None = Field(default=None, ge=0)
    annual_premium: float | None = Field(default=None, ge=0)
    existing_riders: list[str] | None = None


class SimulateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(min_length=1, max_length=100)
    health: HealthOverrides = Field(default_factory=HealthOverrides)
    finance: FinanceOverrides = Field(default_factory=FinanceOverrides)
    insurance: InsuranceOverrides = Field(default_factory=InsuranceOverrides)
    forecast_months: int = Field(default=12, ge=1, le=60)


class WhatIfRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(min_length=1, max_length=100)
    purchase_cost: float = Field(ge=0, le=1e10)


class QueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(min_length=1, max_length=100)
    query: str = Field(min_length=2, max_length=1000)
    thread_id: str = Field(default="default", pattern=r"^[A-Za-z0-9_-]{1,64}$")
    domain: Literal["health", "finance", "insurance"] | None = None


class MarkReadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(min_length=1, max_length=100)
    ids: list[int] | None = Field(default=None, max_length=500)

TWIN_PAGES = {"health": "Health Twin", "finance": "Financial Twin", "insurance": "Insurance Twin"}



def _key_metrics(profiles: dict) -> dict:
    h, f, i = profiles["health"], profiles["finance"], profiles["insurance"]
    return {
        "Health score": h.get("overall_health_score"),
        "CVD risk %": round(h.get("cardio_risk", {}).get("probability", 0) * 100, 1),
        "Diabetes risk %": round((h.get("diabetes_risk") or {}).get("probability", 0) * 100, 1),
        "Debt-to-income %": round(f.get("dti_ratio", 0) * 100),
        "Free cash / month": round(f.get("disposable_income", 0)),
        "Stability score": f.get("financial_stability_score"),
        "Insurance score": i.get("insurance_adequacy_score"),
        "Projected 5-yr medical cost": round(i.get("estimated_future_cost", 0)),
    }


def _metric_changes(before: dict, after: dict) -> list[dict]:
    return [
        {"label": k, "before": before[k], "after": after[k]}
        for k in before
        if before[k] != after.get(k)
    ]


def _notification_response(record: NotificationRecord) -> dict:
    return {"id": record.id, "created_at": record.created_at.isoformat(), **record.payload}


def _friendly_ai_error(message: str) -> str:
    """Map raw LLM exceptions to user-safe messages."""
    lowered = message.lower()
    if "gemini_api_key" in lowered:
        return "Gemini API key is not configured on the server."
    if "429" in lowered or "rate limit" in lowered or "resource_exhausted" in lowered:
        return "Gemini rate limit reached. Please wait a minute and try again."
    if "404" in lowered or "not found" in lowered:
        return "The configured Gemini model is unavailable."
    return "The AI service could not complete this request."


def _build_query_result(query: str, state: dict, citations: list[dict]) -> dict:
    routing = state.get("routing") or {}
    pipeline = ["route"]
    pipeline += [d for d in ("health", "finance", "insurance") if state.get(f"{d}_profile")]
    pipeline.append("rag")
    if routing.get("simulate"):
        pipeline.append("simulate")
    pipeline.append("narrate")

    narration = state.get("narration") or ""
    narration_error = None
    if narration.startswith("[Narration error"):
        narration_error = _friendly_ai_error(narration)
        narration = ""

    simulation = state.get("simulation_result")
    if isinstance(simulation, dict) and "error" in simulation:
        error = str(simulation["error"])
        simulation = {
            "error": error if error.startswith("Please include") else _friendly_ai_error(error),
        }

    return {
        "query": query,
        "routing": routing,
        "pipeline": pipeline,
        "narration": narration,
        "narration_error": narration_error,
        "citations": [
            {
                "source": os.path.basename(str(c.get("source", "unknown"))),
                "score": c.get("score"),
                "excerpt": str(c.get("text", ""))[:500],
            }
            for c in citations
        ],
        "simulation": simulation,
        "scenarios": state.get("scenarios") or [],
    }


def _savings_timeline(twin: FinanceTwin, months: int, overrides: dict) -> list[dict]:
    """Per-month p10/median/p90 of savings, one seeded Monte Carlo run per horizon."""
    timeline = []
    for month in range(1, months + 1):
        band = twin.monte_carlo_forecast(
            months=month, iterations=400, modified_inputs=overrides,
        )["metrics"]["ending_savings_balance"]
        timeline.append({"month": month, **band})
    return timeline


def json_safe(value: Any) -> Any:
    """Convert numpy scalars and non-finite floats (e.g. infinite ratios) to JSON values."""
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _default_health_twin_factory():
    from health_twin import HealthTwin

    return HealthTwin()


def _latest_payload(session: Session, record_cls, user_id: str) -> dict:
    record = session.scalar(
        select(record_cls)
        .where(record_cls.user_id == user_id)
        .order_by(record_cls.id.desc())
        .limit(1),
    )
    if record is None:
        raise HTTPException(status_code=404, detail="No onboarding inputs for user")
    return record.payload


def _snapshot_response(record: SnapshotRecord) -> dict:
    return {
        "snapshot_id": record.id,
        "user_id": record.user_id,
        "created_at": record.created_at.isoformat(),
        **record.payload,
    }


def get_session(request: Request) -> Iterator[Session]:
    session_factory = request.app.state.session_factory
    with session_factory() as session:
        yield session


def create_app(
    database_url: str | URL | None = None,
    health_twin_factory: Callable[[], Any] | None = None,
    query_engine: Callable[..., tuple[dict, list[dict]]] | None = None,
    query_refiner: Callable[[str, list[str]], dict] | None = None,
) -> FastAPI:
    """Create the API app; defaults to a local SQLite database."""
    configured_url = database_url or os.environ.get("DATABASE_URL")
    if configured_url is None:
        data_dir = Path(__file__).resolve().parent / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        configured_url = URL.create(
            "sqlite",
            database=str(data_dir / "twinlife.sqlite3"),
        )

    url = make_url(configured_url) if isinstance(configured_url, str) else configured_url
    engine_options = {}
    if url.drivername.startswith("sqlite"):
        engine_options["connect_args"] = {"check_same_thread": False}
        if url.database in (None, "", ":memory:"):
            engine_options["poolclass"] = StaticPool

    engine = create_engine(url, **engine_options)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )

    app = FastAPI(title="TwinLife AI API", version="0.1.0")
    app.state.db_engine = engine
    app.state.session_factory = session_factory
    app.state.health_twin = None
    health_lock = threading.Lock()
    make_health_twin = health_twin_factory or _default_health_twin_factory

    def assess_health(inputs: dict) -> dict:
        # HealthTwin is shared (model load is slow) and caches state on assess.
        with health_lock:
            if app.state.health_twin is None:
                app.state.health_twin = make_health_twin()
            return app.state.health_twin.assess(inputs)

    def load_inputs(session: Session, user_id: str) -> tuple[dict, dict, dict]:
        health_inputs = _latest_payload(session, HealthInputRecord, user_id)
        finance_inputs = _latest_payload(session, FinanceInputRecord, user_id)
        insurance_inputs = dict(_latest_payload(session, InsuranceInputRecord, user_id))
        if insurance_inputs.get("annual_income") is None:
            insurance_inputs["annual_income"] = finance_inputs["income"] * 12
        return health_inputs, finance_inputs, insurance_inputs

    def run_twins(health_inputs: dict, finance_inputs: dict, insurance_inputs: dict) -> dict:
        health_profile = assess_health(health_inputs)
        finance_profile = FinanceTwin().assess(finance_inputs)
        insurance_profile = InsuranceTwin().assess(
            insurance_inputs, health_profile, finance_profile,
        )
        return {"health": health_profile, "finance": finance_profile, "insurance": insurance_profile}

    app.state.rag_agent = None
    rag_lock = threading.Lock()

    def get_rag_agent():
        with rag_lock:
            if app.state.rag_agent is None:
                from rag_agent import RAGAgent

                agent = RAGAgent()
                agent.build_index()
                app.state.rag_agent = agent
            return app.state.rag_agent

    def orchestrator_engine(
        query: str,
        health_inputs: dict,
        finance_inputs: dict,
        insurance_inputs: dict,
        history: list[dict] | None = None,
        life_context: dict | None = None,
        domain: str | None = None,
    ):
        from orchestrator import Orchestrator

        orchestrator = Orchestrator(health_inputs, finance_inputs, insurance_inputs)
        # Reuse the API's loaded model and RAG index instead of rebuilding per query.
        orchestrator.health_profile = assess_health(health_inputs)
        orchestrator.finance_twin = FinanceTwin()
        orchestrator.finance_profile = orchestrator.finance_twin.assess(finance_inputs)
        rag = get_rag_agent()
        orchestrator.rag_agent = rag
        orchestrator.health_assess = assess_health
        state = orchestrator.process_query(query, history=history, life_context=life_context, domain=domain)
        return state, rag.retrieve_with_metadata(query, top_k=3)

    run_query = query_engine or orchestrator_engine
    if query_refiner is None:
        from query_refiner import refine_query
        # Injected test engines get an identity refiner so offline tests never call Gemini.
        query_refiner = refine_query if query_engine is None else (
            lambda text, previous: {"text": text.strip(), "refined": False, "error": None})

    @app.get("/health")
    def health_check() -> dict:
        return {"status": "ok"}

    @app.post("/onboard", status_code=201)
    def onboard(
        payload: OnboardRequest,
        session: Session = Depends(get_session),
    ) -> dict:
        user = session.scalar(
            select(UserRecord).where(UserRecord.user_id == payload.user_id),
        )
        if user is None:
            user = UserRecord(user_id=payload.user_id)
            session.add(user)
            status = "created"
        else:
            user.updated_at = datetime.now(timezone.utc)
            status = "updated"

        health_payload = payload.health_inputs.model_dump(mode="json")
        if not health_payload["conditions"] and status == "updated":
            # Recalibration keeps recorded medical history unless new conditions are supplied.
            previous = session.scalar(
                select(HealthInputRecord).where(HealthInputRecord.user_id == payload.user_id)
                .order_by(HealthInputRecord.id.desc()).limit(1),
            )
            if previous:
                health_payload["conditions"] = previous.payload.get("conditions", [])
        insurance_payload = payload.insurance_inputs.model_dump(mode="json")
        if not insurance_payload["policies"] and status == "updated":
            previous_ins = session.scalar(
                select(InsuranceInputRecord).where(InsuranceInputRecord.user_id == payload.user_id)
                .order_by(InsuranceInputRecord.id.desc()).limit(1),
            )
            if previous_ins:
                insurance_payload["policies"] = previous_ins.payload.get("policies", [])

        session.add_all([
            HealthInputRecord(
                user_id=payload.user_id,
                payload=health_payload,
            ),
            FinanceInputRecord(
                user_id=payload.user_id,
                payload=payload.finance_inputs.model_dump(mode="json"),
            ),
            InsuranceInputRecord(
                user_id=payload.user_id,
                payload=insurance_payload,
            ),
        ])
        session.commit()
        return {"user_id": payload.user_id, "status": status}

    @app.post("/assess", status_code=201)
    def assess(
        payload: AssessRequest,
        session: Session = Depends(get_session),
    ) -> dict:
        snapshot, alert_count = store_assessment(session, payload.user_id)
        session.commit()
        return {**_snapshot_response(snapshot), "alerts_generated": alert_count}

    def store_assessment(session: Session, user_id: str) -> tuple[SnapshotRecord, int]:
        """Run the twins on the latest inputs, save a snapshot and watchdog alerts (caller commits)."""
        profiles = run_twins(*load_inputs(session, user_id))

        previous = session.scalar(
            select(SnapshotRecord)
            .where(SnapshotRecord.user_id == user_id)
            .order_by(SnapshotRecord.id.desc())
            .limit(1),
        )
        snapshot = SnapshotRecord(
            user_id=user_id,
            payload=json_safe(profiles),
        )
        session.add(snapshot)
        session.flush()

        from monitoring_agent import compare_snapshots

        alerts = compare_snapshots(
            user_id,
            previous.payload if previous else None,
            {**snapshot.payload, "timestamp": snapshot.created_at.isoformat()},
        )
        for alert in alerts:
            session.add(NotificationRecord(
                user_id=user_id,
                payload=json_safe({**alert, "snapshot_id": snapshot.id, "read": False}),
            ))
        return snapshot, len(alerts)

    def save_inputs(session: Session, user_id: str, health: dict, finance: dict, insurance: dict) -> None:
        session.add_all([
            HealthInputRecord(user_id=user_id, payload=json_safe(health)),
            FinanceInputRecord(user_id=user_id, payload=json_safe(finance)),
            InsuranceInputRecord(user_id=user_id, payload=json_safe(insurance)),
        ])
        session.flush()

    def stored_events(session: Session, user_id: str) -> list[LifeEventRecord]:
        return list(session.scalars(
            select(LifeEventRecord).where(LifeEventRecord.user_id == user_id).order_by(LifeEventRecord.id),
        ).all())

    def apply_life_events(session: Session, user_id: str, events: list[dict], source: str) -> list[dict]:
        """Apply ready events to the inputs, re-assess, and log each event; returns the stored payloads."""
        from event_engine import apply_ops

        ready = [e for e in events if (e["ops"] or e.get("log")) and not e["needs"]]
        if not ready:
            return []
        ops = [op for e in ready for op in e["ops"]]
        if not ops:
            # Timeline-only episodes: nothing to recompute.
            return [store_event(session, user_id, {**e, "previous": {}, "snapshot_id": None, "changes": [],
                                                    "alerts_generated": 0, "source": source, "undone": False})
                    for e in ready]
        health, finance, insurance = load_inputs(session, user_id)
        before = _key_metrics(run_twins(health, finance, insurance))
        new_h, new_f, new_i = apply_ops(health, finance, insurance, ops)
        save_inputs(session, user_id, new_h, new_f, new_i)
        snapshot, alert_count = store_assessment(session, user_id)
        after = _key_metrics(snapshot.payload)
        previous_values = {d: {op["field"]: src.get(op["field"]) for op in ops if op["domain"] == d}
                           for d, src in (("health", health), ("finance", finance), ("insurance", insurance))}
        return [
            store_event(session, user_id, {
                **e,
                "previous": {op["domain"] + "." + op["field"]: previous_values[op["domain"]][op["field"]] for op in e["ops"]},
                "snapshot_id": snapshot.id,
                "changes": _metric_changes(before, after),
                "alerts_generated": alert_count,
                "source": source,
                "undone": False,
            })
            for e in ready
        ]

    def store_event(session: Session, user_id: str, payload: dict) -> dict:
        payload = json_safe(payload)
        record = LifeEventRecord(user_id=user_id, payload=payload)
        session.add(record)
        session.flush()
        return {"id": record.id, "created_at": record.created_at.isoformat(), **payload}

    def life_context(
        session: Session, user_id: str, just_recorded: list[dict], pending: list[dict], reverted: list[dict] | None = None,
    ) -> dict:
        from event_engine import active_commitments

        events = [{"date": r.created_at.date().isoformat(), **r.payload} for r in stored_events(session, user_id)]
        live = [e for e in events if not e.get("undone")]
        return {
            "recent_events": [{"date": e["date"], "summary": e["summary"]} for e in live[-10:]],
            "commitments": active_commitments(live),
            "just_recorded": [{"summary": e["summary"] + (" (logged in history only; scores unchanged)" if e.get("log") else ""),
                               "changes": e["changes"]} for e in just_recorded],
            "just_reverted": [{"summary": e["summary"], "changes": e["changes"]} for e in (reverted or [])],
            "pending_questions": [e["needs"] for e in pending],
        }

    @app.get("/events")
    def list_events(
        user_id: str = Query(min_length=1, max_length=100),
        session: Session = Depends(get_session),
    ) -> dict:
        from event_engine import active_commitments, event_domains

        records = stored_events(session, user_id)
        payloads = [r.payload for r in records if not r.payload.get("undone")]
        events = [{"id": r.id, "created_at": r.created_at.isoformat(), **r.payload, "domains": event_domains(r.payload)}
                  for r in reversed(records)]
        return {
            "user_id": user_id,
            "events": events,
            "counts": {d: sum(1 for e in events if d in e["domains"] and not e.get("undone"))
                       for d in ("health", "finance", "insurance")},
            "commitments": active_commitments(payloads),
        }

    def revert_events(session: Session, user_id: str, ids: list[int]) -> list[dict]:
        """Undo stored events (newest first) in one recompute; returns what was reverted with metric changes."""
        records = sorted(
            (r for r in stored_events(session, user_id) if r.id in ids and not r.payload.get("undone")),
            key=lambda r: r.id, reverse=True,
        )
        if not records:
            return []
        if not any(r.payload["ops"] for r in records):
            for record in records:
                record.payload = {**record.payload, "undone": True}
            session.flush()
            return [{"id": r.id, "summary": r.payload["summary"], "changes": []} for r in records]
        health, finance, insurance = load_inputs(session, user_id)
        before = _key_metrics(run_twins(health, finance, insurance))
        targets = {"health": health, "finance": finance, "insurance": insurance}
        for record in records:
            for op in record.payload["ops"]:
                target = targets[op["domain"]]
                if op["mode"] == "add":
                    target[op["field"]] = max(0, target.get(op["field"], 0) - op["value"])
                elif op["mode"] == "append":
                    target[op["field"]] = [v for v in target.get(op["field"], []) if v != op["value"]]
                elif op["mode"] == "remove":
                    target[op["field"]] = [*target.get(op["field"], []), op["value"]]
                else:
                    target[op["field"]] = record.payload["previous"].get(f"{op['domain']}.{op['field']}", target[op["field"]])
        save_inputs(session, user_id, health, finance, insurance)
        snapshot, _ = store_assessment(session, user_id)
        changes = _metric_changes(before, _key_metrics(snapshot.payload))
        reverted = []
        for record in records:
            record.payload = {**record.payload, "undone": True, "undone_snapshot_id": snapshot.id}
            reverted.append({"id": record.id, "summary": record.payload["summary"], "changes": changes})
        session.flush()
        return reverted

    def dues_for(session: Session, user_id: str) -> list[dict]:
        from event_engine import compute_dues

        insurance = _latest_payload(session, InsuranceInputRecord, user_id)
        return compute_dues([r.payload for r in stored_events(session, user_id)], insurance)

    DUE_ALERTS = {
        "overdue": ("warning", "{title} is overdue: ₹{amount:,.0f} was due {due_date}. {detail}"),
        "expired": ("warning", "{title}: {detail}."),
        "missing": ("warning", "{title}. {detail}"),
        "outstanding": ("warning", "{title}: ₹{amount:,.0f} outstanding. {detail}"),
        "due_soon": ("info", "{title} of ₹{amount:,.0f} due on {due_date}."),
    }

    def sync_due_alerts(session: Session, user_id: str) -> int:
        """Turn actionable dues into notifications, once per item and status."""
        existing = {
            (r.payload.get("data") or {}).get("key")
            for r in session.scalars(select(NotificationRecord).where(NotificationRecord.user_id == user_id)).all()
        }
        created = 0
        for due in dues_for(session, user_id):
            if due["status"] not in DUE_ALERTS:
                continue
            key = f"{due['kind']}:{due['title']}:{due['due_date']}:{due['status']}"
            if key in existing:
                continue
            severity, template = DUE_ALERTS[due["status"]]
            session.add(NotificationRecord(user_id=user_id, payload=json_safe({
                "user_id": user_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "type": f"due_{due['status']}",
                "severity": severity,
                "domain": due["domain"],
                "message": template.format(**{**due, "due_date": due["due_date"] or "-"}),
                "data": {**due, "key": key},
                "snapshot_id": None,
                "read": False,
            })))
            created += 1
        if created:
            session.commit()
        return created

    @app.get("/dues")
    def dues(
        user_id: str = Query(min_length=1, max_length=100),
        session: Session = Depends(get_session),
    ) -> dict:
        items = dues_for(session, user_id)
        return {"user_id": user_id, "dues": items,
                "attention": sum(1 for d in items if d["status"] in ("overdue", "expired", "missing", "outstanding"))}

    @app.get("/notifications")
    def notifications(
        user_id: str = Query(min_length=1, max_length=100),
        limit: int = Query(default=30, ge=1, le=200),
        session: Session = Depends(get_session),
    ) -> dict:
        try:
            sync_due_alerts(session, user_id)
        except HTTPException:
            pass  # No twin yet, so nothing can be due.
        records = session.scalars(
            select(NotificationRecord)
            .where(NotificationRecord.user_id == user_id)
            .order_by(NotificationRecord.id.desc())
            .limit(limit),
        ).all()
        items = [_notification_response(r) for r in records]
        return {
            "user_id": user_id,
            "unread": sum(1 for n in items if not n.get("read")),
            "notifications": items,
        }

    @app.post("/notifications/read")
    def mark_notifications_read(
        payload: MarkReadRequest,
        session: Session = Depends(get_session),
    ) -> dict:
        query_ = select(NotificationRecord).where(NotificationRecord.user_id == payload.user_id)
        if payload.ids is not None:
            query_ = query_.where(NotificationRecord.id.in_(payload.ids))
        updated = 0
        for record in session.scalars(query_).all():
            if not record.payload.get("read"):
                # Reassign so SQLAlchemy detects the JSON change.
                record.payload = {**record.payload, "read": True}
                updated += 1
        session.commit()
        return {"user_id": payload.user_id, "updated": updated}

    @app.post("/simulate")
    def simulate(
        payload: SimulateRequest,
        session: Session = Depends(get_session),
    ) -> dict:
        health_inputs, finance_inputs, insurance_inputs = load_inputs(session, payload.user_id)
        health_changes = payload.health.model_dump(exclude_none=True)
        finance_changes = payload.finance.model_dump(exclude_none=True)
        insurance_changes = payload.insurance.model_dump(exclude_none=True)

        modified_finance = {**finance_inputs, **finance_changes}
        modified_insurance = {**insurance_inputs, **insurance_changes}
        if "income" in finance_changes and "annual_income" not in insurance_changes:
            modified_insurance["annual_income"] = modified_finance["income"] * 12

        before = run_twins(health_inputs, finance_inputs, insurance_inputs)
        after = run_twins({**health_inputs, **health_changes}, modified_finance, modified_insurance)

        forecaster = FinanceTwin()
        forecaster.assess(finance_inputs)
        months = payload.forecast_months
        return json_safe({
            "user_id": payload.user_id,
            "changes": {
                "health": health_changes,
                "finance": finance_changes,
                "insurance": insurance_changes,
            },
            "before": before,
            "after": after,
            "forecast": {
                "months": months,
                "before": _savings_timeline(forecaster, months, {}),
                "after": _savings_timeline(forecaster, months, finance_changes),
            },
        })

    @app.post("/whatif")
    def whatif(
        payload: WhatIfRequest,
        session: Session = Depends(get_session),
    ) -> dict:
        finance_inputs = _latest_payload(session, FinanceInputRecord, payload.user_id)
        profile = FinanceTwin().assess(finance_inputs)
        return json_safe({
            "user_id": payload.user_id,
            "purchase_cost": payload.purchase_cost,
            "finance": profile,
            **purchase_impact_simulator(profile, payload.purchase_cost),
        })

    def user_chats(session: Session, user_id: str, limit: int | None = 200) -> list[ChatHistoryRecord]:
        query_ = (select(ChatHistoryRecord).where(ChatHistoryRecord.user_id == user_id)
                  .order_by(ChatHistoryRecord.id.desc()))
        return list(session.scalars(query_.limit(limit) if limit else query_).all())

    def thread_of(record: ChatHistoryRecord) -> str:
        # Threads live in the JSON payload; records saved before threads existed belong to "default".
        return record.result.get("thread_id", "default")

    @app.post("/query")
    def query(
        payload: QueryRequest,
        session: Session = Depends(get_session),
    ) -> dict:
        inputs = load_inputs(session, payload.user_id)
        typed = payload.query.strip()

        from event_engine import active_commitments, complete_pending, detect_events, detect_revert, event_domains

        domain = payload.domain
        stored = stored_events(session, payload.user_id)
        live = [{"id": r.id, **r.payload} for r in stored if not r.payload.get("undone")
                and (domain is None or domain in event_domains(r.payload))]
        commitments = active_commitments(live)
        previous = [r for r in user_chats(session, payload.user_id) if thread_of(r) == payload.thread_id][:3]

        def understood(r: ChatHistoryRecord) -> str:
            return r.result.get("refined_query") or r.query

        refinement = query_refiner(typed, [understood(r) for r in reversed(previous)])
        text = refinement["text"]
        last_turn_ids = [u["id"] for u in (previous[0].result.get("updates") or [])] if previous else []
        recorded: list[dict] = []
        reverted: list[dict] = []
        pending: list[dict] = []
        revert = detect_revert(text, live, last_turn_ids)
        if revert:
            reverted = revert_events(session, payload.user_id, revert["ids"])
            if revert["needs"]:
                pending = [{"needs": revert["needs"]}]
        else:
            detected = detect_events(text, *inputs, commitments=commitments,
                                     previous_text=understood(previous[0]) if previous else None)
            if not detected and previous and previous[0].result.get("pending_questions"):
                detected = complete_pending(understood(previous[0]), text, *inputs, commitments=commitments)
            off_domain = [e for e in detected if domain and domain not in e["domains"]]
            detected = [e for e in detected if e not in off_domain]
            recorded = apply_life_events(session, payload.user_id, detected, source="chat")
            pending = [e for e in detected if e["needs"]] + [
                {"needs": f"\"{e['summary']}\" is a {' / '.join(e['domains'])} update. Tell it in the "
                           f"{TWIN_PAGES[e['domains'][0]]} chat (or the AI Advisor) so it is saved there."}
                for e in off_domain
            ]
        if recorded or reverted:
            inputs = load_inputs(session, payload.user_id)
        context = life_context(session, payload.user_id, recorded, pending, reverted)
        context["dues"] = [d for d in dues_for(session, payload.user_id)
                           if d["status"] != "upcoming" and (domain is None or d["domain"] == domain)][:8]
        history = [
            {
                "query": understood(r),
                "answer": r.result.get("narration")
                or (r.result.get("simulation") or {}).get("recommendation", ""),
            }
            for r in reversed(previous)
        ]
        state, citations = run_query(text, *inputs, history=history, life_context=context,
                                     **({"domain": domain} if domain else {}))
        result = json_safe({
            **_build_query_result(text, state, citations),
            "query": typed,
            "domain": domain,
            "refined_query": text if refinement["refined"] else None,
            "thread_id": payload.thread_id,
            "context_turns": len(history),
            "updates": recorded,
            "reverted": reverted,
            "pending_questions": context["pending_questions"],
        })
        record = ChatHistoryRecord(user_id=payload.user_id, query=typed, result=result)
        session.add(record)
        session.commit()
        return {"chat_id": record.id, "created_at": record.created_at.isoformat(), **result}

    @app.get("/chat-history")
    def chat_history(
        user_id: str = Query(min_length=1, max_length=100),
        thread_id: str | None = Query(default=None, pattern=r"^[A-Za-z0-9_-]{1,64}$"),
        limit: int = Query(default=500, ge=1, le=2000),
        domain: Literal["health", "finance", "insurance", "all"] | None = Query(default=None),
        session: Session = Depends(get_session),
    ) -> dict:
        # Each twin page keeps its own conversations; the main advisor sees those without a domain.
        records = [r for r in user_chats(session, user_id, limit=None)
                   if domain == "all" or r.result.get("domain") == domain]
        custom = {t.thread_id: t.title for t in session.scalars(
            select(ChatThreadRecord).where(ChatThreadRecord.user_id == user_id)).all()}
        threads: dict[str, dict] = {}
        for r in records:
            t = threads.setdefault(thread_of(r), {"thread_id": thread_of(r), "messages": 0, "domain": r.result.get("domain")})
            t["messages"] += 1
            # Records are newest-first, so the last one seen is the thread's opening question.
            t["title"] = custom.get(t["thread_id"]) or r.query[:80]
            t["created_at"] = r.created_at.isoformat()
            t.setdefault("updated_at", r.created_at.isoformat())
        selected = [r for r in records if thread_id is None or thread_of(r) == thread_id][:limit]
        return {
            "user_id": user_id,
            "threads": sorted(threads.values(), key=lambda t: t["updated_at"], reverse=True),
            "messages": [
                {"chat_id": r.id, "created_at": r.created_at.isoformat(), **r.result}
                for r in reversed(selected)
            ],
        }

    def thread_records(session: Session, user_id: str, thread_id: str) -> list[ChatHistoryRecord]:
        return [r for r in user_chats(session, user_id, limit=None) if thread_of(r) == thread_id]

    @app.patch("/chat-threads/{thread_id}")
    def rename_thread(
        payload: RenameThreadRequest,
        thread_id: str = PathParam(pattern=r"^[A-Za-z0-9_-]{1,64}$"),
        session: Session = Depends(get_session),
    ) -> dict:
        if not thread_records(session, payload.user_id, thread_id):
            raise HTTPException(status_code=404, detail="Unknown conversation")
        title = " ".join(payload.title.split())
        record = session.scalar(select(ChatThreadRecord).where(
            ChatThreadRecord.user_id == payload.user_id, ChatThreadRecord.thread_id == thread_id))
        if record is None:
            session.add(ChatThreadRecord(user_id=payload.user_id, thread_id=thread_id, title=title))
        else:
            record.title = title
        session.commit()
        return {"thread_id": thread_id, "title": title}

    @app.delete("/chat-threads/{thread_id}")
    def delete_thread(
        thread_id: str = PathParam(pattern=r"^[A-Za-z0-9_-]{1,64}$"),
        user_id: str = Query(min_length=1, max_length=100),
        session: Session = Depends(get_session),
    ) -> dict:
        records = thread_records(session, user_id, thread_id)
        if not records:
            raise HTTPException(status_code=404, detail="Unknown conversation")
        # Only the conversation is removed; twin updates it recorded stay (revert them via the advisor).
        for r in records:
            session.delete(r)
        for t in session.scalars(select(ChatThreadRecord).where(
                ChatThreadRecord.user_id == user_id, ChatThreadRecord.thread_id == thread_id)).all():
            session.delete(t)
        session.commit()
        return {"thread_id": thread_id, "deleted_messages": len(records)}

    @app.get("/inputs")
    def latest_inputs(
        user_id: str = Query(min_length=1, max_length=100),
        session: Session = Depends(get_session),
    ) -> dict:
        return {
            "user_id": user_id,
            "health_inputs": _latest_payload(session, HealthInputRecord, user_id),
            "finance_inputs": _latest_payload(session, FinanceInputRecord, user_id),
            "insurance_inputs": _latest_payload(session, InsuranceInputRecord, user_id),
        }

    @app.get("/history")
    def history(
        user_id: str = Query(min_length=1, max_length=100),
        limit: int = Query(default=20, ge=1, le=100),
        session: Session = Depends(get_session),
    ) -> dict:
        if session.scalar(select(UserRecord).where(UserRecord.user_id == user_id)) is None:
            raise HTTPException(status_code=404, detail="Unknown user")
        records = session.scalars(
            select(SnapshotRecord)
            .where(SnapshotRecord.user_id == user_id)
            .order_by(SnapshotRecord.id.desc())
            .limit(limit),
        ).all()
        return {
            "user_id": user_id,
            "snapshots": [_snapshot_response(r) for r in records],
        }

    return app


app = create_app()