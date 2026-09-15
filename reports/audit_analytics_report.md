# Audit Analytics Report

> Synthetic decision-support demonstration only. This is not an audit opinion or fraud determination.

## Executive Summary

The pipeline processed **20,000** synthetic transactions with an absolute/net transaction value of **49,724,635.94** in mixed synthetic currencies. It produced **13,640** rule findings, routed **429** High/Critical cases for human review, and recorded a **73.3%** control pass rate. The Isolation Forest achieved F1 **0.265** against designed synthetic labels; those labels are not real-world ground truth.

## Scope

Calendar period represented: synthetic configured period. Components include data validation, financial analytics, ten deterministic rules, Isolation Forest anomaly scoring, evaluation, explanation, risk scoring, controls testing, review workflow, remediation, SQLite audit evidence, API, and dashboard.

## Synthetic Data Description

All accounts, counterparties, users, events, anomalies, and defects were generated with a fixed seed. Ground-truth labels are retained solely for evaluation and excluded from model features.

## Data Quality

Detected **168** transaction-level quality findings across completeness, uniqueness, validity, and referential-integrity checks. Findings are preserved rather than silently corrected so downstream impact remains visible.

## Financial Analytics

- Average amount: 2,486.23
- Median amount: 1,369.92
- Manual or spreadsheet journal entries: 1,983
- Final-two-day/month-end records: 735
- Debit/credit difference: 302,597.92 (synthetic reconciliation indicator, not a misstatement)

## Rule-Based Controls

Top rule volumes: `{"R002": 5810, "R003": 759, "R005": 217, "R006": 1359, "R007": 5084}`. Rules remain separate from model outputs for traceability.

## ML Anomaly Detection

Algorithm: Isolation Forest. Normalized flag threshold: **0.5659**. Features exclude synthetic labels.

## Model Evaluation

- Precision: 0.261
- Recall: 0.268
- F1: 0.265
- ROC-AUC: 0.847
- PR-AUC: 0.289
- Confusion matrix: `{"tn": 18629, "fp": 591, "fn": 571, "tp": 209}`

## Explainability

Global importance uses absolute Spearman association between each feature and the model anomaly score; case explanations combine that association with robust feature deviation. This describes model behavior, not causal inference.

## Human Oversight

429 cases are pending simulated human review. Supported decisions are approve, reject, escalate, and request more information. An AI anomaly flag is not confirmation of fraud.

## Controls Testing

Pass: 11; Partial: 4; Fail: 0; Not Tested: 0.

## Risk Register

The register contains 429 material transaction risks with deterministic likelihood, impact, inherent risk, control effectiveness, and residual risk.

## Remediation

4 prioritized actions were generated from Partial/Fail controls.

## Limitations

Synthetic data and designed labels simplify reality; currencies are not converted; control execution and reviewer identities are simulated; explanations are associative; no authentication, enterprise RBAC, external system integration, or audit opinion is provided.
