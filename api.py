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


class FinanceInputs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    income: float = Field(gt=0)
    fixed_expenses: float = Field(ge=0)
    variable_expenses: float = Field(ge=0)
    emis: float = Field(ge=0)
    savings_balance: float = Field(ge=0)


class InsuranceInputs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sum_insured: float = Field(ge=0)
    annual_premium: float = Field(ge=0)
    annual_income: float | None = Field(default=None, gt=0)
    existing_riders: list[str] = Field(default_factory=list)


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


class MarkReadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(min_length=1, max_length=100)
    ids: list[int] | None = Field(default=None, max_length=500)


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
    query_engine: Callable[[str, dict, dict, dict], tuple[dict, list[dict]]] | None = None,
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

    def orchestrator_engine(query: str, health_inputs: dict, finance_inputs: dict, insurance_inputs: dict):
        from orchestrator import Orchestrator

        orchestrator = Orchestrator(health_inputs, finance_inputs, insurance_inputs)
        # Reuse the API's loaded model and RAG index instead of rebuilding per query.
        orchestrator.health_profile = assess_health(health_inputs)
        orchestrator.finance_twin = FinanceTwin()
        orchestrator.finance_profile = orchestrator.finance_twin.assess(finance_inputs)
        rag = get_rag_agent()
        orchestrator.rag_agent = rag
        state = orchestrator.process_query(query)
        return state, rag.retrieve_with_metadata(query, top_k=3)

    run_query = query_engine or orchestrator_engine

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

        session.add_all([
            HealthInputRecord(
                user_id=payload.user_id,
                payload=payload.health_inputs.model_dump(mode="json"),
            ),
            FinanceInputRecord(
                user_id=payload.user_id,
                payload=payload.finance_inputs.model_dump(mode="json"),
            ),
            InsuranceInputRecord(
                user_id=payload.user_id,
                payload=payload.insurance_inputs.model_dump(mode="json"),
            ),
        ])
        session.commit()
        return {"user_id": payload.user_id, "status": status}

    @app.post("/assess", status_code=201)
    def assess(
        payload: AssessRequest,
        session: Session = Depends(get_session),
    ) -> dict:
        user_id = payload.user_id
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
        session.commit()
        return {**_snapshot_response(snapshot), "alerts_generated": len(alerts)}

    @app.get("/notifications")
    def notifications(
        user_id: str = Query(min_length=1, max_length=100),
        limit: int = Query(default=30, ge=1, le=200),
        session: Session = Depends(get_session),
    ) -> dict:
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

    @app.post("/query")
    def query(
        payload: QueryRequest,
        session: Session = Depends(get_session),
    ) -> dict:
        inputs = load_inputs(session, payload.user_id)
        text = payload.query.strip()
        state, citations = run_query(text, *inputs)
        result = json_safe(_build_query_result(text, state, citations))
        record = ChatHistoryRecord(user_id=payload.user_id, query=text, result=result)
        session.add(record)
        session.commit()
        return {"chat_id": record.id, "created_at": record.created_at.isoformat(), **result}

    @app.get("/chat-history")
    def chat_history(
        user_id: str = Query(min_length=1, max_length=100),
        limit: int = Query(default=30, ge=1, le=200),
        session: Session = Depends(get_session),
    ) -> dict:
        records = session.scalars(
            select(ChatHistoryRecord)
            .where(ChatHistoryRecord.user_id == user_id)
            .order_by(ChatHistoryRecord.id.desc())
            .limit(limit),
        ).all()
        return {
            "user_id": user_id,
            "messages": [
                {"chat_id": r.id, "created_at": r.created_at.isoformat(), **r.result}
                for r in reversed(records)
            ],
        }

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