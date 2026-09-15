# Build Status

## Status

**Complete and validated locally on 2026-09-15.** The implementation covers deterministic synthetic data, data quality, financial analytics, ten rules, Isolation Forest, measured model evaluation, explainability, transparent risk scoring, controls testing, human review, remediation tracking, SQLite audit events, generated reports, FastAPI, Streamlit, and automated tests.

## Validation performed

- Dependency installation: `python -m pip install -e ".[dev]"` — succeeded.
- Test suite: `python -m pytest` — **16 passed** in 6.66 seconds; one upstream Starlette `TestClient` deprecation warning.
- Static checks: `python -m ruff check .` — passed after automated formatting fixes.
- Pipeline: `python scripts/run_pipeline.py --config configs/default.yaml` — completed successfully with 20,000 transactions.
- API: Uvicorn started on a local port; `/health`, `/transactions/summary`, and `/openapi.json` returned HTTP 200. Health reported `healthy` and 20,000 transactions were returned by the live summary.
- Dashboard: Streamlit started locally and was inspected in a real browser. Executive Overview, Model Performance, Human Review, and Remediation rendered with populated KPIs, charts, tables, and workflow controls. A low-contrast styling issue and clipped KPI layout were found and fixed. No browser runtime errors remained; benign Vega/Streamlit compatibility warnings were observed.
- SQLite: 20,000 transactions, 20,000 model scores, 20,000 risk scores, 13,640 rule findings, 168 quality findings, 429 review records, 429 material risks, 15 controls, four remediation actions, and timestamped pipeline/model/control/risk events were verified.
- Reports: all required reports were generated, non-empty, and checked for placeholder markers.

## Measured default-run results

- Model flags: 800
- High/Critical review cases: 429 (415 High, 14 Critical)
- Precision: 0.26125
- Recall: 0.26795
- F1: 0.26456
- ROC-AUC: 0.84713
- PR-AUC: 0.28884
- Confusion matrix: TN 18,629; FP 591; FN 571; TP 209
- Normalized operating threshold: 0.565875
- Control results: 11 Pass, four Partial, zero Fail, zero Not Tested (73.3% pass rate)

These values reflect designed synthetic labels and must not be interpreted as real-world fraud-detection performance.

## Generated artifacts

- Data: `data/generated/accounts.csv`, `vendors.csv`, `customers.csv`, `transactions.csv`, `journal_entries.csv`, `account_balances.csv`
- Model/evidence: `artifacts/isolation_forest.joblib`, `model_metrics.json`, `model_scores.csv`, `features.csv`, `threshold_sensitivity.csv`, `global_feature_importance.csv`, `case_explanations.csv`
- Controls/workflow: `artifacts/quality_findings.csv`, `rule_findings.csv`, `transaction_risks.csv`, `risk_register.csv`, `controls.csv`, `reviews.csv`, `remediation.csv`, `audit_analytics.db`
- Reports: `reports/audit_analytics_report.md`, `control_testing_report.md`, `anomaly_report.csv`, `risk_register.csv`, `remediation_plan.csv`, `model_card.md`, `methodology.md`

## Limitations

Synthetic ground truth is designed rather than observed; the current model has no external validation population; currency is not normalized; explanations are associative; access control, identity, workflow notifications, and change approval are not production integrations; SQLite is intentionally local and single-environment oriented.
