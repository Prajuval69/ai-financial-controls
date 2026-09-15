from __future__ import annotations

import numpy as np
import pandas as pd


def _level(score: float) -> str:
    if score >= 75:
        return "Critical"
    if score >= 55:
        return "High"
    if score >= 30:
        return "Moderate"
    return "Low"


def score_risk(transactions: pd.DataFrame, scores: pd.DataFrame, rule_agg: pd.DataFrame, quality_findings: pd.DataFrame, control_effectiveness: float = 0.72) -> pd.DataFrame:
    merged = transactions[["transaction_id", "amount", "transaction_type"]].merge(scores, on="transaction_id", how="left").merge(rule_agg, on="transaction_id", how="left")
    merged[["rule_count", "max_rule_severity"]] = merged[["rule_count", "max_rule_severity"]].fillna(0)
    dq_counts = quality_findings.groupby("transaction_id").size().rename("data_quality_count") if not quality_findings.empty else pd.Series(dtype=int, name="data_quality_count")
    merged = merged.merge(dq_counts, on="transaction_id", how="left")
    merged["data_quality_count"] = merged.data_quality_count.fillna(0)
    amount_pct = pd.to_numeric(merged.amount, errors="coerce").abs().rank(pct=True).fillna(0)
    merged["likelihood"] = np.clip(1 + 4 * (0.55 * merged.normalized_anomaly_score + 0.25 * (merged.max_rule_severity / 4) + 0.2 * np.minimum(merged.data_quality_count, 2) / 2), 1, 5)
    merged["impact"] = np.clip(1 + 4 * amount_pct, 1, 5)
    merged["inherent_risk"] = merged.likelihood * merged.impact * 4
    merged["control_effectiveness"] = float(np.clip(control_effectiveness, 0, 0.9))
    merged["residual_risk"] = merged.inherent_risk * (1 - merged.control_effectiveness)
    merged["risk_score"] = np.clip(0.65 * merged.inherent_risk + 35 * merged.normalized_anomaly_score + 3 * merged.rule_count + 5 * merged.data_quality_count, 0, 100)
    merged["risk_level"] = merged.risk_score.map(_level)
    merged["rationale"] = merged.apply(lambda r: f"Model score {r.normalized_anomaly_score:.2f}; {int(r.rule_count)} rule finding(s); {int(r.data_quality_count)} data-quality finding(s); amount percentile {amount_pct.loc[r.name]:.2f}.", axis=1)
    merged["recommended_action"] = merged.risk_level.map({"Low": "Retain for routine monitoring.", "Moderate": "Review supporting evidence when capacity permits.", "High": "Route to timely human review.", "Critical": "Escalate promptly for senior review."})
    return merged.drop(columns=["amount", "transaction_type"])


def build_risk_register(risks: pd.DataFrame, rule_findings: pd.DataFrame) -> pd.DataFrame:
    material = risks.loc[risks.risk_level.isin(["High", "Critical"])].copy()
    material = material.sort_values("risk_score", ascending=False).head(500)
    return pd.DataFrame({
        "risk_id": [f"RSK{i:06d}" for i in range(1, len(material) + 1)],
        "transaction_id": material.transaction_id.values,
        "domain": "Financial transaction anomaly",
        "description": "Synthetic transaction requires risk-based review",
        "evidence": material.rationale.values,
        "likelihood": material.likelihood.round(2).values,
        "impact": material.impact.round(2).values,
        "inherent_risk": material.inherent_risk.round(2).values,
        "controls": "Rules, Isolation Forest, data-quality validation, human review",
        "control_effectiveness": material.control_effectiveness.round(2).values,
        "residual_risk": material.residual_risk.round(2).values,
        "risk_level": material.risk_level.values,
        "owner": "Synthetic Financial Controls Team",
        "recommendation": material.recommended_action.values,
        "status": "Open",
    })
