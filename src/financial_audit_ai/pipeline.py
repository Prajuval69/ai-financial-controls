from __future__ import annotations

import argparse
import json
import logging
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import joblib
import pandas as pd

from financial_audit_ai.analytics.financial import calculate_financial_analytics
from financial_audit_ai.analytics.rules import aggregate_rule_findings, run_rules
from financial_audit_ai.config import Settings
from financial_audit_ai.controls.framework import test_controls
from financial_audit_ai.data.generator import generate_synthetic_data
from financial_audit_ai.explainability.explainer import explain_model
from financial_audit_ai.modeling.detector import fit_score_model
from financial_audit_ai.modeling.evaluation import evaluate_model
from financial_audit_ai.modeling.features import FEATURE_COLUMNS, build_features
from financial_audit_ai.persistence.database import AuditDatabase
from financial_audit_ai.quality.validator import validate_data
from financial_audit_ai.reporting.generator import generate_reports
from financial_audit_ai.reviews.service import create_review_queue
from financial_audit_ai.risk.engine import build_risk_register, score_risk

LOGGER = logging.getLogger(__name__)


def _json_default(value: object) -> object:
    if hasattr(value, "item"):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(type(value).__name__)


def run_pipeline(settings: Settings) -> dict[str, object]:
    settings.ensure_directories()
    database = AuditDatabase(settings.database_path)
    database.initialize()
    database.append_event("pipeline_started", "pipeline", settings.model_version, "system", {"seed": settings.seed})
    bundle = generate_synthetic_data(settings)
    for name, frame in asdict(bundle).items():
        frame.to_csv(settings.data_dir / f"{name}.csv", index=False)

    quality_findings, quality_summary = validate_data(bundle.transactions, bundle.accounts, bundle.vendors, bundle.customers)
    analytics = calculate_financial_analytics(bundle.transactions)
    rule_findings = run_rules(bundle.transactions, settings)
    rule_agg = aggregate_rule_findings(bundle.transactions, rule_findings)
    features = build_features(bundle.transactions)
    if "synthetic_anomaly_label" in features.columns:
        raise RuntimeError("Ground-truth label leaked into model features")
    model_result = fit_score_model(features, bundle.transactions.transaction_id, settings)
    metrics, sensitivity = evaluate_model(bundle.transactions.synthetic_anomaly_label, model_result.scores)
    global_importance, case_explanations = explain_model(features, model_result.scores)
    controls_pre = test_controls(quality_summary, metrics, model_result.scores, model_result.threshold, settings.model_version)
    control_effectiveness = float(controls_pre.result.map({"Pass": 1.0, "Partial": 0.5, "Fail": 0.0, "Not Tested": 0.0}).mean())
    risks = score_risk(bundle.transactions, model_result.scores, rule_agg, quality_findings, control_effectiveness)
    risk_register = build_risk_register(risks, rule_findings)
    reviews = create_review_queue(risks, settings.review_risk_levels)
    controls = test_controls(quality_summary, metrics, model_result.scores, model_result.threshold, settings.model_version)
    remediation = controls.loc[controls.result.isin(["Partial", "Fail"]), ["control_id", "control_domain", "severity", "recommendation"]].copy()
    remediation.insert(0, "remediation_id", [f"REM{i:04d}" for i in range(1, len(remediation) + 1)])
    remediation["owner"] = "Synthetic Control Owner"
    remediation["status"] = "Open"
    remediation["target_date"] = "2026-12-31"

    anomaly_report = bundle.transactions[["transaction_id", "transaction_date", "account_id", "vendor_id", "transaction_type", "amount", "synthetic_anomaly_label", "synthetic_anomaly_type"]].merge(model_result.scores, on="transaction_id").merge(rule_agg, on="transaction_id", how="left").merge(risks[["transaction_id", "risk_score", "risk_level", "rationale", "recommended_action"]], on="transaction_id")
    anomaly_report[["rule_count", "max_rule_severity"]] = anomaly_report[["rule_count", "max_rule_severity"]].fillna(0)
    anomaly_report["rule_flags"] = anomaly_report.rule_flags.fillna("")

    artifacts: dict[str, pd.DataFrame] = {
        "quality_findings": quality_findings,
        "quality_summary": quality_summary,
        "rule_findings": rule_findings,
        "features": features.assign(transaction_id=bundle.transactions.transaction_id),
        "model_scores": model_result.scores,
        "threshold_sensitivity": sensitivity,
        "global_feature_importance": global_importance,
        "case_explanations": case_explanations,
        "transaction_risks": risks,
        "risk_register": risk_register,
        "controls": controls,
        "reviews": reviews,
        "remediation": remediation,
        "anomalies": anomaly_report,
        "monthly_analytics": analytics["monthly"],
        "account_activity": analytics["account_activity"],
        "vendor_activity": analytics["vendor_activity"],
        "transaction_types": analytics["transaction_types"],
    }
    for name, frame in artifacts.items():
        frame.to_csv(settings.artifact_dir / f"{name}.csv", index=False)
        database.replace_frame(name, frame)
    database.replace_frame("transactions", bundle.transactions)
    database.replace_frame("reviews", reviews)
    joblib.dump({"model": model_result.model, "scaler": model_result.scaler, "features": FEATURE_COLUMNS, "threshold": model_result.threshold, "version": settings.model_version}, settings.artifact_dir / "isolation_forest.joblib")
    (settings.artifact_dir / "model_metrics.json").write_text(json.dumps(metrics, indent=2, default=_json_default), encoding="utf-8")
    (settings.artifact_dir / "run_metadata.json").write_text(json.dumps({"completed_at": datetime.now(UTC).isoformat(), "model_version": settings.model_version, "seed": settings.seed, "transaction_count": len(bundle.transactions), "threshold": model_result.threshold, "synthetic_data": True}, indent=2), encoding="utf-8")
    generate_reports(settings.report_dir, analytics, quality_summary, rule_findings, metrics, model_result.threshold, global_importance, case_explanations, controls, risk_register, reviews, remediation, settings.model_version)
    anomaly_report.to_csv(settings.report_dir / "anomaly_report.csv", index=False)
    database.append_event("model_trained", "model", settings.model_version, "system", {"threshold": model_result.threshold, "metrics": metrics})
    database.append_event("control_tests_completed", "controls", "current", "system", {"count": len(controls), "results": controls.result.value_counts().to_dict()})
    database.append_event("risks_created", "risk_register", "current", "system", {"count": len(risk_register)})
    database.append_event("pipeline_completed", "pipeline", settings.model_version, "system", {"transactions": len(bundle.transactions), "reviews": len(reviews)})
    return {"transactions": len(bundle.transactions), "rule_findings": len(rule_findings), "reviews": len(reviews), "controls": len(controls), "metrics": metrics, "threshold": model_result.threshold}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the synthetic financial audit analytics pipeline")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()
    logging.basicConfig(level=args.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    result = run_pipeline(Settings.from_yaml(args.config))
    LOGGER.info("Pipeline completed: %s", result)
    print(json.dumps(result, indent=2, default=_json_default))


if __name__ == "__main__":
    main()

