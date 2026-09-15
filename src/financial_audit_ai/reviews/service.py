from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd

from financial_audit_ai.persistence.database import AuditDatabase

ALLOWED_DECISIONS = {"approve", "reject", "escalate", "request_more_information", "pending"}


def create_review_queue(risks: pd.DataFrame, risk_levels: list[str]) -> pd.DataFrame:
    queue = risks.loc[risks.risk_level.isin(risk_levels)].copy().sort_values("risk_score", ascending=False)
    now = datetime.now(UTC).isoformat()
    return pd.DataFrame({
        "review_id": [f"REV{i:07d}" for i in range(1, len(queue) + 1)],
        "transaction_id": queue.transaction_id.values,
        "reviewer_id": None,
        "model_score": queue.normalized_anomaly_score.values,
        "risk_level": queue.risk_level.values,
        "rule_findings": queue.rule_flags.fillna("").values,
        "decision": "pending",
        "notes": "AI anomaly flag is not a confirmation of fraud; human review required.",
        "timestamp": now,
    })


class ReviewService:
    def __init__(self, database: AuditDatabase):
        self.database = database

    def decide(self, review_id: str, reviewer_id: str, decision: str, notes: str) -> dict[str, str]:
        if decision not in ALLOWED_DECISIONS - {"pending"}:
            raise ValueError(f"Unsupported decision: {decision}")
        if not reviewer_id.strip() or not notes.strip():
            raise ValueError("Reviewer ID and notes are required")
        timestamp = datetime.now(UTC).isoformat()
        with self.database.connect() as conn:
            row = conn.execute("SELECT transaction_id FROM reviews WHERE review_id=?", (review_id,)).fetchone()
            if row is None:
                raise KeyError(review_id)
            conn.execute("UPDATE reviews SET reviewer_id=?, decision=?, notes=?, timestamp=? WHERE review_id=?", (reviewer_id, decision, notes, timestamp, review_id))
        self.database.append_event("review_decision", "review", review_id, reviewer_id, {"decision": decision, "notes": notes, "transaction_id": row["transaction_id"]})
        return {"review_id": review_id, "decision": decision, "timestamp": timestamp}

