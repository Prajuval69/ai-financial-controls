# Methodology

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
