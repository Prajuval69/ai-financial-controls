from __future__ import annotations

import importlib.util

from fastapi.testclient import TestClient

from financial_audit_ai.api.main import app
from financial_audit_ai.persistence.database import AuditDatabase
from financial_audit_ai.pipeline import run_pipeline
from financial_audit_ai.remediation.service import RemediationService
from financial_audit_ai.reviews.service import ReviewService


def test_end_to_end_pipeline_generates_required_artifacts(small_settings):
    result = run_pipeline(small_settings)
    assert result["transactions"] == small_settings.n_transactions
    expected = [
        small_settings.data_dir / "transactions.csv",
        small_settings.artifact_dir / "isolation_forest.joblib",
        small_settings.artifact_dir / "model_metrics.json",
        small_settings.artifact_dir / "controls.csv",
        small_settings.report_dir / "audit_analytics_report.md",
        small_settings.report_dir / "control_testing_report.md",
        small_settings.report_dir / "anomaly_report.csv",
        small_settings.report_dir / "risk_register.csv",
        small_settings.report_dir / "remediation_plan.csv",
        small_settings.report_dir / "model_card.md",
        small_settings.report_dir / "methodology.md",
    ]
    assert all(path.exists() and path.stat().st_size > 0 for path in expected)
    audit_text = (small_settings.report_dir / "audit_analytics_report.md").read_text(encoding="utf-8")
    assert f"{small_settings.n_transactions:,}" in audit_text
    assert "not an audit opinion" in audit_text.lower()


def test_sqlite_persistence_and_audit_trail(small_settings):
    run_pipeline(small_settings)
    database = AuditDatabase(small_settings.database_path)
    assert len(database.read_table("transactions")) == small_settings.n_transactions
    events = database.read_table("audit_trail")
    assert {"pipeline_started", "pipeline_completed", "model_trained"} <= set(events.event_type)


def test_review_workflow_records_decision_and_event(small_settings):
    run_pipeline(small_settings)
    database = AuditDatabase(small_settings.database_path)
    review = database.read_table("reviews").iloc[0]
    result = ReviewService(database).decide(review.review_id, "U-TEST-001", "escalate", "Synthetic evidence requires senior review.")
    assert result["decision"] == "escalate"
    updated = database.read_table("reviews")
    assert updated.loc[updated.review_id.eq(review.review_id), "decision"].iloc[0] == "escalate"
    assert "review_decision" in set(database.read_table("audit_trail").event_type)


def test_review_workflow_rejects_invalid_decision(small_settings):
    database = AuditDatabase(small_settings.database_path)
    with pytest.raises(ValueError):
        ReviewService(database).decide("missing", "U-TEST", "fraud", "invalid")


def test_remediation_tracking_records_status_and_event(small_settings):
    run_pipeline(small_settings)
    database = AuditDatabase(small_settings.database_path)
    item = database.read_table("remediation").iloc[0]
    result = RemediationService(database).update(item.remediation_id, "In Progress", "U-OWNER-001", "Synthetic action initiated.")
    assert result["status"] == "In Progress"
    updated = database.read_table("remediation")
    assert updated.loc[updated.remediation_id.eq(item.remediation_id), "status"].iloc[0] == "In Progress"
    assert "remediation_updated" in set(database.read_table("audit_trail").event_type)


def test_api_endpoints_against_default_pipeline():
    client = TestClient(app)
    assert client.get("/health").status_code == 200
    assert client.get("/transactions/summary").status_code == 200
    assert client.get("/anomalies", params={"risk_level": "High", "limit": 5}).status_code == 200
    assert client.get("/model/performance").status_code == 200
    for endpoint in ["/controls", "/risks", "/reviews", "/audit-trail", "/remediation"]:
        response = client.get(endpoint, params={"limit": 5})
        assert response.status_code == 200
        assert isinstance(response.json(), list)


def test_api_openapi_has_documented_routes():
    schema = TestClient(app).get("/openapi.json").json()
    required = {"/health", "/transactions/summary", "/anomalies", "/model/performance", "/controls", "/risks", "/reviews", "/audit-trail", "/remediation"}
    assert required <= set(schema["paths"])


def test_dashboard_and_api_modules_importable():
    assert importlib.util.find_spec("financial_audit_ai.api.main") is not None
    dashboard = __import__("pathlib").Path("app/streamlit_app.py")
    compile(dashboard.read_text(encoding="utf-8"), str(dashboard), "exec")


import pytest
