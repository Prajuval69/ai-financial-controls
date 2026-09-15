from __future__ import annotations

import json
import sqlite3
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from financial_audit_ai.config import Settings
from financial_audit_ai.persistence.database import AuditDatabase
from financial_audit_ai.remediation.service import RemediationService
from financial_audit_ai.reviews.service import ReviewService

settings = Settings.from_yaml()
database = AuditDatabase(settings.database_path)
app = FastAPI(
    title="Synthetic Financial Controls & Audit Analytics API",
    version="1.0.0",
    description="Decision-support API using entirely synthetic data. An anomaly flag is not confirmation of fraud.",
)


class ReviewDecisionRequest(BaseModel):
    reviewer_id: str = Field(min_length=1, max_length=100)
    decision: Literal["approve", "reject", "escalate", "request_more_information"]
    notes: str = Field(min_length=1, max_length=2000)


class RemediationUpdateRequest(BaseModel):
    actor_id: str = Field(min_length=1, max_length=100)
    status: Literal["Open", "In Progress", "Completed", "Deferred"]
    notes: str = Field(min_length=1, max_length=2000)


def _rows(table: str, filters: dict[str, object] | None = None, limit: int = 100) -> list[dict[str, object]]:
    if not database.path.exists():
        raise HTTPException(503, "Pipeline artifacts are unavailable; run the pipeline first.")
    filters = {k: v for k, v in (filters or {}).items() if v is not None}
    allowed = {"risk_level", "status", "transaction_type", "decision", "event_type", "result"}
    if not set(filters).issubset(allowed):
        raise HTTPException(400, "Unsupported filter")
    clauses = [f'"{key}" = ?' for key in filters]
    query = f'SELECT * FROM "{table}"' + (" WHERE " + " AND ".join(clauses) if clauses else "") + " LIMIT ?"
    try:
        with database.connect() as conn:
            return [dict(row) for row in conn.execute(query, (*filters.values(), limit)).fetchall()]
    except sqlite3.Error as exc:
        raise HTTPException(503, f"Artifact table unavailable: {table}") from exc


@app.get("/health")
def health() -> dict[str, object]:
    return {"status": "healthy" if database.path.exists() else "degraded", "synthetic_data": True, "database_available": database.path.exists(), "disclaimer": "An AI anomaly flag is not confirmation of fraud."}


@app.get("/transactions/summary")
def transaction_summary(transaction_type: str | None = None) -> dict[str, object]:
    where, params = (" WHERE transaction_type = ?", (transaction_type,)) if transaction_type else ("", ())
    try:
        with database.connect() as conn:
            row = conn.execute(f"SELECT COUNT(*) AS transaction_count, COALESCE(SUM(amount),0) AS total_value, COALESCE(AVG(amount),0) AS average_amount FROM transactions{where}", params).fetchone()
            risk = conn.execute("SELECT risk_level, COUNT(*) count FROM transaction_risks GROUP BY risk_level").fetchall()
    except sqlite3.Error as exc:
        raise HTTPException(503, "Pipeline artifacts are unavailable; run the pipeline first.") from exc
    return {**dict(row), "risk_distribution": {r["risk_level"]: r["count"] for r in risk}, "synthetic_data": True}


@app.get("/anomalies")
def anomalies(risk_level: str | None = None, transaction_type: str | None = None, limit: int = Query(100, ge=1, le=5000)) -> list[dict[str, object]]:
    return _rows("anomalies", {"risk_level": risk_level, "transaction_type": transaction_type}, limit)


@app.get("/model/performance")
def model_performance() -> dict[str, object]:
    path = settings.artifact_dir / "model_metrics.json"
    if not path.exists():
        raise HTTPException(503, "Model metrics are unavailable; run the pipeline first.")
    return {"model_version": settings.model_version, "metrics": json.loads(path.read_text(encoding="utf-8")), "synthetic_ground_truth": True}


@app.get("/controls")
def controls(result: str | None = None, limit: int = Query(100, ge=1, le=1000)) -> list[dict[str, object]]:
    return _rows("controls", {"result": result}, limit)


@app.get("/risks")
def risks(risk_level: str | None = None, status: str | None = None, limit: int = Query(100, ge=1, le=5000)) -> list[dict[str, object]]:
    return _rows("risk_register", {"risk_level": risk_level, "status": status}, limit)


@app.get("/reviews")
def reviews(decision: str | None = None, risk_level: str | None = None, limit: int = Query(100, ge=1, le=5000)) -> list[dict[str, object]]:
    return _rows("reviews", {"decision": decision, "risk_level": risk_level}, limit)


@app.post("/reviews/{review_id}/decision")
def decide_review(review_id: str, request: ReviewDecisionRequest) -> dict[str, str]:
    try:
        return ReviewService(database).decide(review_id, request.reviewer_id, request.decision, request.notes)
    except KeyError as exc:
        raise HTTPException(404, "Review not found") from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.get("/audit-trail")
def audit_trail(event_type: str | None = None, limit: int = Query(100, ge=1, le=5000)) -> list[dict[str, object]]:
    return _rows("audit_trail", {"event_type": event_type}, limit)


@app.get("/remediation")
def remediation(status: str | None = None, limit: int = Query(100, ge=1, le=1000)) -> list[dict[str, object]]:
    return _rows("remediation", {"status": status}, limit)


@app.post("/remediation/{remediation_id}")
def update_remediation(remediation_id: str, request: RemediationUpdateRequest) -> dict[str, str]:
    try:
        return RemediationService(database).update(remediation_id, request.status, request.actor_id, request.notes)
    except KeyError as exc:
        raise HTTPException(404, "Remediation item not found") from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
