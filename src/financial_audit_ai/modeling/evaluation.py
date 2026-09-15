from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


def evaluate_model(labels: pd.Series, scores: pd.DataFrame) -> tuple[dict[str, object], pd.DataFrame]:
    y_true = labels.astype(int).to_numpy()
    y_score = scores.normalized_anomaly_score.to_numpy()
    y_pred = scores.model_anomaly_flag.astype(int).to_numpy()
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    metrics: dict[str, object] = {
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, y_score)),
        "pr_auc": float(average_precision_score(y_true, y_score)),
        "confusion_matrix": {"tn": int(cm[0, 0]), "fp": int(cm[0, 1]), "fn": int(cm[1, 0]), "tp": int(cm[1, 1])},
        "false_positive_count": int(cm[0, 1]),
        "false_negative_count": int(cm[1, 0]),
    }
    thresholds = np.linspace(0.35, 0.9, 12)
    sensitivity = pd.DataFrame(
        [
            {
                "threshold": float(t),
                "precision": float(precision_score(y_true, y_score >= t, zero_division=0)),
                "recall": float(recall_score(y_true, y_score >= t, zero_division=0)),
                "f1": float(f1_score(y_true, y_score >= t, zero_division=0)),
                "flagged_count": int((y_score >= t).sum()),
            }
            for t in thresholds
        ]
    )
    return metrics, sensitivity

