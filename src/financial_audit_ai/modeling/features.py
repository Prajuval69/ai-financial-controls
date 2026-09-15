from __future__ import annotations

import numpy as np
import pandas as pd

FEATURE_COLUMNS = [
    "log_abs_amount",
    "transaction_hour",
    "day_of_week",
    "days_to_period_end",
    "account_frequency",
    "vendor_frequency",
    "manual_entry",
    "is_round_amount",
    "is_negative",
]


def build_features(transactions: pd.DataFrame) -> pd.DataFrame:
    """Create model inputs without using synthetic ground-truth labels."""
    tx = transactions.copy()
    amount = pd.to_numeric(tx.amount, errors="coerce").fillna(0)
    date = pd.to_datetime(tx.transaction_date, errors="coerce")
    posting = pd.to_datetime(tx.posting_timestamp, errors="coerce")
    account_freq = tx.account_id.map(tx.account_id.value_counts(normalize=True)).fillna(0)
    vendor_freq = tx.vendor_id.map(tx.vendor_id.value_counts(normalize=True)).fillna(0)
    features = pd.DataFrame(
        {
            "log_abs_amount": np.log1p(amount.abs()),
            "transaction_hour": posting.dt.hour.fillna(-1),
            "day_of_week": date.dt.dayofweek.fillna(-1),
            "days_to_period_end": (date.dt.days_in_month - date.dt.day).fillna(-1),
            "account_frequency": account_freq,
            "vendor_frequency": vendor_freq,
            "manual_entry": tx.journal_source.isin(["Manual", "Spreadsheet Upload"]).astype(int),
            "is_round_amount": (amount.abs().ge(10_000) & amount.abs().mod(10_000).eq(0)).astype(int),
            "is_negative": amount.lt(0).astype(int),
        },
        index=transactions.index,
    )
    return features.astype(float)

