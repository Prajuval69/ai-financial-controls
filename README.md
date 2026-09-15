# AI-Driven Financial Controls & Audit Analytics Engine

A production-style, fully local portfolio project showing how rule-based analytics and machine learning can support financial exception review while preserving traceability, human judgment, and control evidence.

> **Synthetic-data disclaimer:** every account, counterparty, user, transaction, anomaly, defect, control result, and review record is synthetic. This project is not an audit, fraud investigation, financial-statement opinion, regulatory certification, or production financial system. An AI anomaly flag is not confirmation of fraud.

## Business problem

Financial teams need to examine large transaction populations without turning opaque model scores into unsupported conclusions. This engine combines deterministic accounting-style checks with an unsupervised model, evaluates the model against controlled synthetic labels, explains why cases appear unusual, routes material cases to people, and records evidence in an audit trail.

## Architecture

```text
Synthetic reference data + transactions
                 │
                 ▼
      Data-quality validation ─────┐
                 │                 │
        ┌────────┴────────┐        │
        ▼                 ▼        │
 Financial analytics  Rule engine  │
        │                 │        │
        └────────┬────────┘        │
                 ▼                 │
 Feature engineering → Isolation Forest
                 │                 │
          Evaluation + explanation
                 │                 │
                 └────────┬────────┘
                          ▼
             Transparent risk engine
                          │
          ┌───────────────┴───────────────┐
          ▼                               ▼
   Control testing                 Human review queue
          └───────────────┬───────────────┘
                          ▼
              SQLite audit evidence
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
       Reports         FastAPI         Streamlit
```

## Capabilities

- Generates 50 accounts, 300 vendors, 500 customers, and 20,000 deterministic synthetic transactions by default.
- Injects controlled anomalies and data defects while keeping labels separate from model predictions.
- Calculates transaction, account, vendor, journal, monthly-trend, and reconciliation-style analytics.
- Executes ten independent rules with IDs, descriptions, severity, evidence, and transaction linkage.
- Trains an Isolation Forest using leakage-safe engineered features and a robust scaler.
- Calculates precision, recall, F1, ROC-AUC, PR-AUC, confusion matrix, false positives/negatives, and threshold sensitivity from actual outputs.
- Provides global and case-level explanations using robust deviation and score association, explicitly presented as non-causal.
- Produces likelihood, impact, inherent risk, control effectiveness, residual risk, risk level, rationale, and recommended action.
- Tests data, model, output, human-oversight, change/access, and escalation controls with retained evidence.
- Persists review decisions, remediation updates, model events, controls, risks, and pipeline events in SQLite.
- Serves generated artifacts through FastAPI and a nine-page Streamlit dashboard.

## Technology stack

Python 3.11+, pandas, NumPy, SciPy, scikit-learn, FastAPI, Pydantic, Uvicorn, Streamlit, SQLite, PyYAML, Matplotlib, pytest, Ruff, and joblib. No API key, cloud account, paid service, external database, or proprietary dataset is required.

## Data model

The generated source layer contains accounts, vendors, customers, transactions, journal entries, and account balances. Transactions carry accounting-style fields including account/counterparty references, amount, debit/credit indicator, journal source, preparer, dates, timestamps, descriptions, and separate synthetic ground-truth fields.

The evidence layer contains quality findings, rule findings, features, model scores, evaluation outputs, explanations, transaction risks, the risk register, controls, reviews, remediation actions, and audit events.

## Analytical methodology

### Data quality and financial analytics

Checks cover required-field completeness, duplicates at the intended grain, account/vendor/customer references, timestamp validity, amount validity, and debit/credit domains. Analytics preserve detected defects so their downstream effect remains inspectable. Mixed synthetic currencies are deliberately not converted; totals are illustrative and labeled accordingly.

### Rule and ML anomaly detection

Rules cover duplicates, weekend and after-hours posting, round-dollar amounts, robust large-amount outliers, period-end activity, rare vendor/account combinations, reversals, out-of-period activity, and invalid required data. Each rule is independently implemented.

Isolation Forest features include log absolute amount, posting hour, weekday, days to period end, account/vendor frequency, manual-entry indicator, round-amount indicator, and negative-amount indicator. The synthetic anomaly label is never included in the feature matrix. The operating threshold is configuration-driven; a separate sensitivity table measures alternative thresholds.

### Explainability

To keep the project stable offline, explainability uses absolute Spearman association between each feature and the anomaly score plus robust case-level deviations. This is a dependency-light alternative to SHAP for an unsupervised pipeline. It explains model behavior; it does not identify a causal mechanism, intent, error, or fraud.

### Risk and controls

Likelihood combines model score, maximum rule severity, and capped data-quality findings. Impact is based on amount percentile. Inherent risk is likelihood × impact × 4, and residual risk applies the measured control-effectiveness factor. The documented operational score maps to Low, Moderate, High, and Critical levels. Exact weights and thresholds are in [`reports/methodology.md`](reports/methodology.md).

The control matrix covers input completeness/validity, duplicates, referential integrity, reconciliation, version/configuration, feature leakage, evaluation, thresholds, monitoring, output completeness, review, evidence retention, reviewer actions, change/access concepts, and escalation.

### Human review

High and Critical cases enter a SQLite-backed review queue. Reviewers may `approve`, `reject`, `escalate`, or `request_more_information`; reviewer ID and notes are mandatory. Remediation owners can move actions through Open, In Progress, Completed, or Deferred. Every decision or update appends an audit event.

## Repository structure

```text
app/                         Streamlit dashboard
configs/                     Deterministic YAML settings
data/generated/              Generated synthetic source tables
artifacts/                   Model, analytical outputs, SQLite database
reports/                     Generated reports and registers
scripts/                     Pipeline entry point
src/financial_audit_ai/      Modular application package
tests/                       Unit, integration, API, and smoke tests
*.md                         Original project specifications
```

## Installation

```bash
python -m venv .venv
```

On Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

On macOS/Linux:

```bash
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## Run the complete pipeline

```bash
python scripts/run_pipeline.py --config configs/default.yaml
```

The default deterministic run produces 20,000 transactions. Edit `configs/default.yaml` to change scale or thresholds.

## Run tests and code-quality checks

```bash
python -m pytest
python -m ruff check .
```

## Start the API

```bash
python -m uvicorn financial_audit_ai.api.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for generated OpenAPI documentation.

Example calls:

```bash
curl http://127.0.0.1:8000/health
curl "http://127.0.0.1:8000/anomalies?risk_level=Critical&limit=10"
curl "http://127.0.0.1:8000/reviews?decision=pending&limit=10"
```

Review and remediation mutations are also available:

```bash
curl -X POST http://127.0.0.1:8000/reviews/REV0000001/decision -H "Content-Type: application/json" -d '{"reviewer_id":"U-REVIEWER-001","decision":"escalate","notes":"Synthetic evidence requires senior review."}'
curl -X POST http://127.0.0.1:8000/remediation/REM0001 -H "Content-Type: application/json" -d '{"actor_id":"U-CONTROL-001","status":"In Progress","notes":"Synthetic remediation action initiated."}'
```

## Start the dashboard

```bash
python -m streamlit run app/streamlit_app.py
```

Pages: Executive Overview, Transaction Analytics, Anomaly Detection, Model Performance, Controls Testing, Risk Register, Human Review, Audit Trail, and Remediation. Run the pipeline first; the dashboard reads generated data rather than hard-coded values.

## API endpoints

- `GET /health`
- `GET /transactions/summary`
- `GET /anomalies`
- `GET /model/performance`
- `GET /controls`
- `GET /risks`
- `GET /reviews`
- `POST /reviews/{review_id}/decision`
- `GET /audit-trail`
- `GET /remediation`
- `POST /remediation/{remediation_id}`

## Generated artifacts and example results

The validated default run generated 20,000 scores, 13,640 rule findings, 168 data-quality findings, 429 High/Critical review cases, and 15 tested controls. Isolation Forest results against the designed synthetic labels were precision 0.261, recall 0.268, F1 0.265, ROC-AUC 0.847, and PR-AUC 0.289. These are reproducible measurements, not claimed real-world performance.

Important outputs include:

- `artifacts/audit_analytics.db`
- `artifacts/isolation_forest.joblib`
- `artifacts/model_metrics.json`
- `artifacts/anomalies.csv`
- `artifacts/controls.csv`
- `artifacts/threshold_sensitivity.csv`
- `reports/audit_analytics_report.md`
- `reports/control_testing_report.md`
- `reports/anomaly_report.csv`
- `reports/risk_register.csv`
- `reports/remediation_plan.csv`
- `reports/model_card.md`
- `reports/methodology.md`

## Limitations

- Designed synthetic labels are simpler and more controlled than real operational ground truth.
- The model is fitted and evaluated on one synthetic population; the metrics demonstrate evaluation plumbing, not external validity.
- Feature explanations are associative rather than causal.
- Currency amounts are not converted to a common reporting currency.
- Authentication, enterprise RBAC, segregation-of-duties enforcement, workflow notifications, and production change approval are simulated or documented concepts.
- SQLite and local files suit a self-contained portfolio project, not multi-user production scale.

## Interview talking points

1. Explain why transparent rules and multivariate ML provide complementary—not interchangeable—evidence.
2. Walk through label-leakage prevention and the limits of evaluating against designed synthetic truth.
3. Show how a model score becomes a transparent risk decision through likelihood, impact, controls, and residual risk.
4. Demonstrate human review, mandatory notes, escalation, remediation tracking, and append-only-style audit events.
5. Discuss the model/data/output/human/change control matrix and evidence captured for each test.
6. Contrast behavioral explanation with causal or fraud claims and justify the stable offline alternative to SHAP.
7. Describe how the same generated evidence powers reports, SQLite, API endpoints, and dashboard views without duplicated hard-coded results.

See [`BUILD_STATUS.md`](BUILD_STATUS.md) for the latest validated build record.

