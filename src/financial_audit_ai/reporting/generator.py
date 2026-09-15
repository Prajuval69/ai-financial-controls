from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def generate_reports(report_dir: Path, analytics: dict[str, object], quality_summary: pd.DataFrame, rule_findings: pd.DataFrame, metrics: dict[str, object], threshold: float, global_importance: pd.DataFrame, case_explanations: pd.DataFrame, controls: pd.DataFrame, risk_register: pd.DataFrame, reviews: pd.DataFrame, remediation: pd.DataFrame, model_version: str) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    summary = analytics["summary"]
    control_pass = float(controls.result.eq("Pass").mean())
    open_reviews = int(reviews.decision.eq("pending").sum())
    top_rules = rule_findings.rule_id.value_counts().head(5).to_dict()
    audit_report = f"""# Audit Analytics Report

> Synthetic decision-support demonstration only. This is not an audit opinion or fraud determination.

## Executive Summary

The pipeline processed **{summary['transaction_count']:,}** synthetic transactions with an absolute/net transaction value of **{summary['total_transaction_value']:,.2f}** in mixed synthetic currencies. It produced **{len(rule_findings):,}** rule findings, routed **{open_reviews:,}** High/Critical cases for human review, and recorded a **{_pct(control_pass)}** control pass rate. The Isolation Forest achieved F1 **{metrics['f1']:.3f}** against designed synthetic labels; those labels are not real-world ground truth.

## Scope

Calendar period represented: synthetic configured period. Components include data validation, financial analytics, ten deterministic rules, Isolation Forest anomaly scoring, evaluation, explanation, risk scoring, controls testing, review workflow, remediation, SQLite audit evidence, API, and dashboard.

## Synthetic Data Description

All accounts, counterparties, users, events, anomalies, and defects were generated with a fixed seed. Ground-truth labels are retained solely for evaluation and excluded from model features.

## Data Quality

Detected **{int(quality_summary.finding_count.sum()):,}** transaction-level quality findings across completeness, uniqueness, validity, and referential-integrity checks. Findings are preserved rather than silently corrected so downstream impact remains visible.

## Financial Analytics

- Average amount: {summary['average_transaction_amount']:,.2f}
- Median amount: {summary['median_transaction_amount']:,.2f}
- Manual or spreadsheet journal entries: {summary['manual_journal_count']:,}
- Final-two-day/month-end records: {summary['period_end_count']:,}
- Debit/credit difference: {summary['debit_credit_difference']:,.2f} (synthetic reconciliation indicator, not a misstatement)

## Rule-Based Controls

Top rule volumes: `{json.dumps(top_rules, sort_keys=True)}`. Rules remain separate from model outputs for traceability.

## ML Anomaly Detection

Algorithm: Isolation Forest. Normalized flag threshold: **{threshold:.4f}**. Features exclude synthetic labels.

## Model Evaluation

- Precision: {metrics['precision']:.3f}
- Recall: {metrics['recall']:.3f}
- F1: {metrics['f1']:.3f}
- ROC-AUC: {metrics['roc_auc']:.3f}
- PR-AUC: {metrics['pr_auc']:.3f}
- Confusion matrix: `{json.dumps(metrics['confusion_matrix'])}`

## Explainability

Global importance uses absolute Spearman association between each feature and the model anomaly score; case explanations combine that association with robust feature deviation. This describes model behavior, not causal inference.

## Human Oversight

{open_reviews:,} cases are pending simulated human review. Supported decisions are approve, reject, escalate, and request more information. An AI anomaly flag is not confirmation of fraud.

## Controls Testing

Pass: {int(controls.result.eq('Pass').sum())}; Partial: {int(controls.result.eq('Partial').sum())}; Fail: {int(controls.result.eq('Fail').sum())}; Not Tested: {int(controls.result.eq('Not Tested').sum())}.

## Risk Register

The register contains {len(risk_register):,} material transaction risks with deterministic likelihood, impact, inherent risk, control effectiveness, and residual risk.

## Remediation

{len(remediation):,} prioritized actions were generated from Partial/Fail controls.

## Limitations

Synthetic data and designed labels simplify reality; currencies are not converted; control execution and reviewer identities are simulated; explanations are associative; no authentication, enterprise RBAC, external system integration, or audit opinion is provided.
"""
    (report_dir / "audit_analytics_report.md").write_text(audit_report, encoding="utf-8")

    control_lines = ["# Control Testing Report", "", "> Synthetic controls assessment; not a compliance certification.", "", f"Controls tested: **{len(controls)}**. Pass rate: **{_pct(control_pass)}**.", "", "| Control | Domain | Result | Severity | Evidence | Recommendation |", "|---|---|---|---|---|---|"]
    for row in controls.itertuples():
        evidence = str(row.actual_evidence).replace("|", "/").replace("\n", " ")[:180]
        control_lines.append(f"| {row.control_id} | {row.control_domain} | {row.result} | {row.severity} | {evidence} | {row.recommendation} |")
    (report_dir / "control_testing_report.md").write_text("\n".join(control_lines), encoding="utf-8")

    model_card = f"""# Model Card: {model_version}

## Purpose and intended use
Prioritize unusual synthetic financial transactions for human review and portfolio demonstration.

## Data and features
Deterministic synthetic transactions. Features: {', '.join(global_importance.feature.tolist())}. Ground-truth anomaly labels are excluded from training features.

## Algorithm and threshold
Isolation Forest with a normalized anomaly threshold of {threshold:.6f}.

## Evaluation
Precision {metrics['precision']:.4f}; recall {metrics['recall']:.4f}; F1 {metrics['f1']:.4f}; ROC-AUC {metrics['roc_auc']:.4f}; PR-AUC {metrics['pr_auc']:.4f}. Results reflect designed synthetic labels only.

## Explainability
Dependency-light robust feature-deviation explanations are used instead of SHAP to ensure stable offline execution. They indicate association with model behavior, not causation.

## Limitations and prohibited interpretation
Do not treat a score as proof of fraud, an audit conclusion, or evidence of performance on real financial data. Synthetic labels and injected patterns may be easier to detect than real anomalies.

## Monitoring and human oversight
Record model version, threshold, score distribution, metrics, and review outcomes per run. High/Critical cases require human disposition.
"""
    (report_dir / "model_card.md").write_text(model_card, encoding="utf-8")

    methodology = """# Methodology

## Pipeline
Synthetic data → quality validation → financial analytics and independent rules → feature engineering → Isolation Forest → evaluation and explanation → transparent risk scoring → control tests → human review → SQLite audit trail → reports/API/dashboard.

## Determinism and data quality
Generation and modeling use a fixed seed. Controlled missing fields, duplicates, invalid references, timestamps, and amounts are deliberately preserved and detected.

## Rules and model
Ten separately implemented rules produce rule ID, severity, evidence, and transaction linkage. The model uses robust-scaled transaction features and excludes the synthetic label. Threshold sensitivity is calculated independently of the configured operating threshold.

## Risk formula
Likelihood combines 55% model score, 25% maximum rule severity, and 20% capped data-quality findings on a 1–5 scale. Impact is amount percentile on a 1–5 scale. Inherent risk is likelihood × impact × 4. Residual risk applies a documented control-effectiveness factor. The operational 0–100 risk score combines 65% inherent risk, model score, rule count, and quality findings, capped at 100; levels are Low <30, Moderate <55, High <75, Critical ≥75.

## Explainability boundary
Feature-score association and robust deviation explain why a record appears unusual to the model. They do not establish cause, intent, error, or fraud.

## Human review and evidence
High/Critical items enter a persisted queue. Decisions require reviewer ID and notes, and append a timestamped audit event.
"""
    (report_dir / "methodology.md").write_text(methodology, encoding="utf-8")
    risk_register.to_csv(report_dir / "risk_register.csv", index=False)
    remediation.to_csv(report_dir / "remediation_plan.csv", index=False)
    case_explanations.to_csv(report_dir / "case_explanations.csv", index=False)

