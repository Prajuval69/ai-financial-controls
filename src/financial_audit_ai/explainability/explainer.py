from __future__ import annotations

import pandas as pd


def explain_model(features: pd.DataFrame, scores: pd.DataFrame, top_n: int = 25) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Robust, dependency-light attribution; explanations are associations, not causes."""
    aligned_score = scores.normalized_anomaly_score.reset_index(drop=True)
    importance = []
    for column in features.columns:
        corr = pd.Series(features[column]).corr(aligned_score, method="spearman")
        importance.append({"feature": column, "importance": float(abs(corr)) if pd.notna(corr) else 0.0, "method": "absolute Spearman association with anomaly score"})
    global_importance = pd.DataFrame(importance).sort_values("importance", ascending=False).reset_index(drop=True)
    weights = global_importance.set_index("feature").importance.reindex(features.columns).fillna(0)
    medians = features.median()
    scale = (features.quantile(0.75) - features.quantile(0.25)).replace(0, 1)
    deviation = ((features - medians) / scale).abs().mul(weights, axis=1)
    high_indices = scores.nlargest(top_n, "normalized_anomaly_score").index
    cases = []
    for idx in high_indices:
        top = deviation.loc[idx].nlargest(3)
        reasons = [f"{name} is unusual relative to the synthetic population" for name in top.index]
        cases.append({
            "transaction_id": scores.loc[idx, "transaction_id"],
            "normalized_anomaly_score": float(scores.loc[idx, "normalized_anomaly_score"]),
            "top_features": ", ".join(top.index),
            "explanation": "; ".join(reasons) + ". This explains model behavior, not causation or fraud.",
        })
    return global_importance, pd.DataFrame(cases)

