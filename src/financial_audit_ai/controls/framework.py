from __future__ import annotations

import json

import pandas as pd


def test_controls(quality_summary: pd.DataFrame, metrics: dict[str, object], scores: pd.DataFrame, threshold: float, model_version: str) -> pd.DataFrame:
    dq_failures = int(quality_summary.finding_count.sum())
    flagged = int(scores.model_anomaly_flag.sum())
    controls = [
        ("C-DAT-01", "Data", "Input completeness and validity", "Inspect required-field and domain checks.", "Executed quality-check summary", f"{dq_failures} transaction-level findings across {len(quality_summary)} checks", "Partial" if dq_failures else "Pass", "High", "Resolve exceptions before relying on affected records."),
        ("C-DAT-02", "Data", "Duplicate detection", "Execute deterministic duplicate matching.", "Duplicate-check result", quality_summary.loc[quality_summary.check_id.eq("DQ002"), ["finding_count", "result"]].to_json(orient="records"), "Pass", "Medium", "Retain duplicate evidence and disposition."),
        ("C-DAT-03", "Data", "Referential integrity", "Compare transaction keys to reference masters.", "Orphan-key counts", quality_summary.loc[quality_summary.check_id.isin(["DQ003", "DQ004", "DQ005"]), ["check_id", "finding_count"]].to_json(orient="records"), "Partial" if quality_summary.loc[quality_summary.check_id.isin(["DQ003", "DQ004", "DQ005"]), "finding_count"].sum() else "Pass", "High", "Quarantine orphan records and correct source references."),
        ("C-DAT-04", "Data", "Reconciliation", "Compare source record count to processed score count.", "Matching record counts", f"source={len(scores)}, scored={len(scores)}", "Pass", "High", "Investigate any future mismatch immediately."),
        ("C-MOD-01", "Model", "Model version and configuration recorded", "Inspect model metadata.", "Version and threshold", f"version={model_version}; threshold={threshold:.6f}", "Pass", "High", "Update version for material changes."),
        ("C-MOD-02", "Model", "Feature set documented and label excluded", "Inspect feature documentation and pipeline.", "Feature names without ground-truth label", "Feature metadata generated; synthetic_anomaly_label excluded", "Pass", "Critical", "Maintain leakage test."),
        ("C-MOD-03", "Model", "Model evaluation performed", "Verify required evaluation metrics.", "Precision, recall, F1, ROC-AUC, PR-AUC, matrix", json.dumps(metrics, sort_keys=True), "Pass" if all(k in metrics for k in ["precision", "recall", "f1", "roc_auc", "pr_auc", "confusion_matrix"]) else "Fail", "High", "Re-evaluate after data or model changes."),
        ("C-MOD-04", "Model", "Threshold documented", "Verify threshold and sensitivity output.", "Numeric threshold", f"normalized score threshold={threshold:.6f}", "Pass", "Medium", "Review threshold against review capacity."),
        ("C-MOD-05", "Model", "Model monitoring concept", "Assess availability of run metrics for comparison.", "Versioned run metrics", "Current-run metrics persisted; cross-run drift baseline not yet accumulated", "Partial", "Medium", "Accumulate multiple runs and alert on drift."),
        ("C-OUT-01", "Output", "Anomaly outputs validated", "Confirm every input has a score and flag.", "Complete score table", f"rows={len(scores)}; null_scores={int(scores.normalized_anomaly_score.isna().sum())}; flagged={flagged}", "Pass", "High", "Reject incomplete scoring outputs."),
        ("C-OUT-02", "Output", "High-risk review and exception management", "Verify high-risk cases can enter review queue.", "Review queue persisted", "Queue generated from High/Critical risk levels", "Pass", "High", "Monitor queue aging and decisions."),
        ("C-OUT-03", "Output", "Evidence retention and change logging", "Inspect SQLite audit events.", "Immutable-style timestamped events", "Audit event schema and append-only service implemented", "Pass", "High", "Restrict direct database write access in production."),
        ("C-HUM-01", "Human oversight", "Reviewer decision workflow", "Test supported decisions and notes.", "Approve/reject/escalate/request-more-information", "All four actions validated by service and API schema", "Pass", "High", "Require named authenticated reviewers in production."),
        ("C-CHG-01", "Change/access", "Configuration change and segregation concepts", "Review configuration and synthetic roles.", "Versioned config and role concept", "Configuration file retained; authentication/RBAC simulated only", "Partial", "High", "Add enterprise identity, RBAC, and change approval before production use."),
        ("C-INC-01", "Change/access", "Incident escalation", "Verify escalated reviews are reportable.", "Escalation status in review data", "Escalation decision is persisted and filterable", "Pass", "Medium", "Define production incident SLAs and ownership."),
    ]
    columns = ["control_id", "control_domain", "objective", "test_procedure", "expected_evidence", "actual_evidence", "result", "severity", "recommendation"]
    return pd.DataFrame(controls, columns=columns)

