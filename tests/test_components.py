from __future__ import annotations

import pandas as pd
import pytest

from financial_audit_ai.analytics.financial import calculate_financial_analytics
from financial_audit_ai.analytics.rules import default_rules, run_rules
from financial_audit_ai.data.generator import generate_synthetic_data
from financial_audit_ai.explainability.explainer import explain_model
from financial_audit_ai.modeling.detector import fit_score_model
from financial_audit_ai.modeling.evaluation import evaluate_model
from financial_audit_ai.modeling.features import FEATURE_COLUMNS, build_features
from financial_audit_ai.quality.validator import validate_data
from financial_audit_ai.risk.engine import score_risk


@pytest.fixture(scope="module")
def bundle(small_settings):
    return generate_synthetic_data(small_settings)


def test_generation_is_deterministic_and_has_expected_entities(small_settings):
    first = generate_synthetic_data(small_settings)
    second = generate_synthetic_data(small_settings)
    pd.testing.assert_frame_equal(first.transactions, second.transactions)
    assert len(first.accounts) == 20
    assert len(first.transactions) == 1200
    assert first.transactions.synthetic_anomaly_label.sum() > 0
    assert set(first.transactions.synthetic_anomaly_type) >= {"none", "large_amount", "data_quality"}


def test_quality_engine_detects_controlled_defects(bundle):
    findings, summary = validate_data(bundle.transactions, bundle.accounts, bundle.vendors, bundle.customers)
    assert not findings.empty
    assert set(summary.check_id) == {f"DQ{i:03d}" for i in range(1, 9)}
    assert summary.loc[summary.check_id.eq("DQ003"), "finding_count"].iloc[0] > 0
    assert summary.loc[summary.check_id.eq("DQ007"), "finding_count"].iloc[0] > 0


def test_financial_analytics_reconcile_record_count(bundle):
    result = calculate_financial_analytics(bundle.transactions)
    assert result["summary"]["transaction_count"] == len(bundle.transactions)
    assert int(result["monthly"].transaction_count.sum()) == len(bundle.transactions)
    assert {"debit_total", "credit_total", "debit_credit_difference"} <= result["summary"].keys()


def test_rules_are_independent_and_auditable(bundle, small_settings):
    rules = default_rules()
    findings = run_rules(bundle.transactions, small_settings)
    assert len(rules) == 10
    assert len({rule.rule_id for rule in rules}) == 10
    assert {"rule_id", "severity", "evidence", "transaction_id"} <= set(findings.columns)
    assert findings.rule_id.nunique() >= 8


def test_features_have_no_ground_truth_leakage(bundle):
    features = build_features(bundle.transactions)
    assert list(features.columns) == FEATURE_COLUMNS
    assert "synthetic_anomaly_label" not in features
    assert features.notna().all().all()


def test_model_scores_and_evaluation_are_real(bundle, small_settings):
    features = build_features(bundle.transactions)
    result = fit_score_model(features, bundle.transactions.transaction_id, small_settings)
    metrics, sensitivity = evaluate_model(bundle.transactions.synthetic_anomaly_label, result.scores)
    assert len(result.scores) == len(bundle.transactions)
    assert result.scores.normalized_anomaly_score.between(0, 1).all()
    assert 0 < result.scores.model_anomaly_flag.sum() < len(result.scores)
    assert all(0 <= metrics[key] <= 1 for key in ["precision", "recall", "f1", "roc_auc", "pr_auc"])
    assert sensitivity.threshold.is_monotonic_increasing


def test_explanations_are_noncausal_and_transaction_linked(bundle, small_settings):
    features = build_features(bundle.transactions)
    scores = fit_score_model(features, bundle.transactions.transaction_id, small_settings).scores
    global_importance, cases = explain_model(features, scores, top_n=7)
    assert len(global_importance) == len(FEATURE_COLUMNS)
    assert len(cases) == 7
    assert cases.explanation.str.contains("not causation or fraud").all()


def test_risk_score_is_transparent_and_bounded(bundle, small_settings):
    features = build_features(bundle.transactions)
    scores = fit_score_model(features, bundle.transactions.transaction_id, small_settings).scores
    findings = run_rules(bundle.transactions, small_settings)
    from financial_audit_ai.analytics.rules import aggregate_rule_findings
    rule_agg = aggregate_rule_findings(bundle.transactions, findings)
    quality, _ = validate_data(bundle.transactions, bundle.accounts, bundle.vendors, bundle.customers)
    risks = score_risk(bundle.transactions, scores, rule_agg, quality)
    assert risks.risk_score.between(0, 100).all()
    assert set(risks.risk_level) <= {"Low", "Moderate", "High", "Critical"}
    assert risks.rationale.str.contains("Model score").all()

