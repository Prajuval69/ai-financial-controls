from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import RobustScaler

from financial_audit_ai.config import Settings


@dataclass
class ModelResult:
    model: IsolationForest
    scaler: RobustScaler
    scores: pd.DataFrame
    threshold: float


def fit_score_model(features: pd.DataFrame, transaction_ids: pd.Series, settings: Settings) -> ModelResult:
    scaler = RobustScaler()
    x = scaler.fit_transform(features)
    model = IsolationForest(n_estimators=200, contamination=settings.model_contamination, random_state=settings.seed, n_jobs=-1)
    model.fit(x)
    raw = -model.score_samples(x)
    minimum, maximum = float(raw.min()), float(raw.max())
    normalized = (raw - minimum) / (maximum - minimum) if maximum > minimum else np.zeros_like(raw)
    threshold = float(np.quantile(normalized, settings.model_threshold_quantile))
    scores = pd.DataFrame({
        "transaction_id": transaction_ids.values,
        "model_anomaly_score": raw,
        "normalized_anomaly_score": normalized,
        "model_anomaly_flag": (normalized >= threshold).astype(int),
    })
    return ModelResult(model, scaler, scores, threshold)

