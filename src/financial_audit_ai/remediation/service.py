from __future__ import annotations

from financial_audit_ai.persistence.database import AuditDatabase

ALLOWED_STATUSES = {"Open", "In Progress", "Completed", "Deferred"}


class RemediationService:
    def __init__(self, database: AuditDatabase):
        self.database = database

    def update(self, remediation_id: str, status: str, actor_id: str, notes: str) -> dict[str, str]:
        if status not in ALLOWED_STATUSES:
            raise ValueError(f"Unsupported remediation status: {status}")
        if not actor_id.strip() or not notes.strip():
            raise ValueError("Actor ID and notes are required")
        with self.database.connect() as conn:
            row = conn.execute("SELECT control_id FROM remediation WHERE remediation_id=?", (remediation_id,)).fetchone()
            if row is None:
                raise KeyError(remediation_id)
            conn.execute("UPDATE remediation SET status=? WHERE remediation_id=?", (status, remediation_id))
        self.database.append_event("remediation_updated", "remediation", remediation_id, actor_id, {"status": status, "notes": notes, "control_id": row["control_id"]})
        return {"remediation_id": remediation_id, "status": status}

