from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from financial_audit_ai.config import Settings


@dataclass
class SyntheticDataBundle:
    accounts: pd.DataFrame
    vendors: pd.DataFrame
    customers: pd.DataFrame
    transactions: pd.DataFrame
    journal_entries: pd.DataFrame
    account_balances: pd.DataFrame


ANOMALY_TYPES = [
    "duplicate",
    "large_amount",
    "round_amount",
    "weekend_after_hours",
    "period_end",
    "unusual_vendor_account",
    "reversal",
    "out_of_period",
]


def _references(settings: Settings, rng: np.random.Generator) -> tuple[pd.DataFrame, ...]:
    account_types = ["Asset", "Liability", "Equity", "Revenue", "Expense"]
    accounts = pd.DataFrame(
        {
            "account_id": [f"A{i:04d}" for i in range(1, settings.n_accounts + 1)],
            "account_name": [f"Synthetic {account_types[(i - 1) % 5]} Account {i:02d}" for i in range(1, settings.n_accounts + 1)],
            "account_type": [account_types[(i - 1) % 5] for i in range(1, settings.n_accounts + 1)],
            "normal_balance": ["Debit" if account_types[(i - 1) % 5] in {"Asset", "Expense"} else "Credit" for i in range(1, settings.n_accounts + 1)],
            "active_flag": rng.choice([True, False], settings.n_accounts, p=[0.96, 0.04]),
        }
    )
    vendors = pd.DataFrame(
        {
            "vendor_id": [f"V{i:04d}" for i in range(1, settings.n_vendors + 1)],
            "vendor_name": [f"Synthetic Vendor {i:04d}" for i in range(1, settings.n_vendors + 1)],
            "vendor_category": rng.choice(["Technology", "Professional Services", "Facilities", "Travel", "Supplies"], settings.n_vendors),
            "region": rng.choice(["North", "South", "East", "West", "Central"], settings.n_vendors),
            "active_flag": rng.choice([True, False], settings.n_vendors, p=[0.97, 0.03]),
        }
    )
    customers = pd.DataFrame(
        {
            "customer_id": [f"C{i:05d}" for i in range(1, settings.n_customers + 1)],
            "customer_name": [f"Synthetic Customer {i:05d}" for i in range(1, settings.n_customers + 1)],
            "customer_segment": rng.choice(["Enterprise", "Mid-market", "Small business"], settings.n_customers, p=[0.2, 0.35, 0.45]),
            "region": rng.choice(["North", "South", "East", "West", "Central"], settings.n_customers),
            "active_flag": rng.choice([True, False], settings.n_customers, p=[0.98, 0.02]),
        }
    )
    return accounts, vendors, customers


def generate_synthetic_data(settings: Settings) -> SyntheticDataBundle:
    """Generate deterministic, explicitly synthetic financial records and defects."""
    rng = np.random.default_rng(settings.seed)
    accounts, vendors, customers = _references(settings, rng)
    n = settings.n_transactions
    start = pd.Timestamp(settings.period_start)
    end = pd.Timestamp(settings.period_end)
    dates = start + pd.to_timedelta(rng.integers(0, (end - start).days + 1, n), unit="D")
    hours = np.clip(np.rint(rng.normal(13, 3, n)), 0, 23).astype(int)
    minutes = rng.integers(0, 60, n)
    posting = dates + pd.to_timedelta(hours, unit="h") + pd.to_timedelta(minutes, unit="m")
    types = rng.choice(["Payment", "Expense", "Invoice", "Receipt", "Journal"], n, p=[0.25, 0.25, 0.2, 0.2, 0.1])
    amount = np.round(rng.lognormal(mean=7.2, sigma=1.0, size=n), 2)
    tx = pd.DataFrame(
        {
            "transaction_id": [f"T{i:07d}" for i in range(1, n + 1)],
            "transaction_date": dates,
            "posting_timestamp": posting,
            "account_id": rng.choice(accounts.account_id, n),
            "vendor_id": np.where(np.isin(types, ["Payment", "Expense"]), rng.choice(vendors.vendor_id, n), None),
            "customer_id": np.where(np.isin(types, ["Invoice", "Receipt"]), rng.choice(customers.customer_id, n), None),
            "transaction_type": types,
            "amount": amount,
            "debit_credit": rng.choice(["Debit", "Credit"], n),
            "currency": rng.choice(["USD", "EUR", "GBP", "INR"], n, p=[0.65, 0.15, 0.1, 0.1]),
            "journal_source": np.where(types == "Journal", rng.choice(["Manual", "Spreadsheet Upload"], n), "Automated"),
            "preparer_id": [f"U{x:03d}" for x in rng.integers(1, 81, n)],
            "description": [f"Synthetic {t.lower()} transaction" for t in types],
            "synthetic_anomaly_label": 0,
            "synthetic_anomaly_type": "none",
        }
    )
    anomaly_n = max(len(ANOMALY_TYPES), int(n * settings.anomaly_rate))
    anomaly_idx = rng.choice(tx.index, anomaly_n, replace=False)
    groups = np.array_split(anomaly_idx, len(ANOMALY_TYPES))
    for anomaly_type, idx in zip(ANOMALY_TYPES, groups, strict=True):
        tx.loc[idx, "synthetic_anomaly_label"] = 1
        tx.loc[idx, "synthetic_anomaly_type"] = anomaly_type
        if anomaly_type == "large_amount":
            tx.loc[idx, "amount"] *= 25
        elif anomaly_type == "round_amount":
            tx.loc[idx, "amount"] = np.ceil(tx.loc[idx, "amount"] / 10_000) * 10_000
        elif anomaly_type == "weekend_after_hours":
            tx.loc[idx, "transaction_date"] = tx.loc[idx, "transaction_date"].map(lambda d: d + pd.Timedelta(days=(5 - d.weekday()) % 7))
            tx.loc[idx, "posting_timestamp"] = pd.to_datetime(tx.loc[idx, "transaction_date"]) + pd.Timedelta(hours=23)
        elif anomaly_type == "period_end":
            tx.loc[idx, "transaction_date"] = pd.to_datetime(tx.loc[idx, "transaction_date"]).dt.to_period("M").dt.end_time.dt.normalize()
            tx.loc[idx, "posting_timestamp"] = pd.to_datetime(tx.loc[idx, "transaction_date"]) + pd.Timedelta(hours=20)
        elif anomaly_type == "unusual_vendor_account":
            tx.loc[idx, "account_id"] = accounts.account_id.iloc[-1]
            tx.loc[idx, "vendor_id"] = vendors.vendor_id.iloc[0]
        elif anomaly_type == "reversal":
            tx.loc[idx, "amount"] *= -1
            tx.loc[idx, "description"] = "Synthetic reversal adjustment"
        elif anomaly_type == "out_of_period":
            tx.loc[idx, "transaction_date"] = end + pd.to_timedelta(rng.integers(1, 31, len(idx)), unit="D")
            tx.loc[idx, "posting_timestamp"] = pd.to_datetime(tx.loc[idx, "transaction_date"]) + pd.Timedelta(hours=12)
    duplicate_sources = groups[0]
    for target, source in zip(duplicate_sources, np.roll(duplicate_sources, 1), strict=True):
        cols = ["transaction_date", "posting_timestamp", "account_id", "vendor_id", "customer_id", "transaction_type", "amount", "debit_credit", "currency", "journal_source", "preparer_id", "description"]
        tx.loc[target, cols] = tx.loc[source, cols].values
    defect_n = max(4, int(n * settings.quality_defect_rate))
    defect_idx = rng.choice(tx.index.difference(anomaly_idx), defect_n, replace=False)
    defect_groups = np.array_split(defect_idx, 4)
    tx.loc[defect_groups[0], "account_id"] = None
    tx.loc[defect_groups[1], "account_id"] = "A9999"
    tx.loc[defect_groups[2], "amount"] = 0
    tx.loc[defect_groups[3], "posting_timestamp"] = pd.NaT
    tx.loc[defect_idx, "synthetic_anomaly_label"] = 1
    tx.loc[defect_idx, "synthetic_anomaly_type"] = "data_quality"

    tx["journal_entry_id"] = np.where(tx.transaction_type.eq("Journal"), "JE" + tx.transaction_id.str[1:], None)
    journals = tx.loc[tx.transaction_type.eq("Journal")].copy()
    balances = tx.assign(signed_amount=np.where(tx.debit_credit.eq("Debit"), tx.amount, -tx.amount)).groupby("account_id", dropna=False).agg(debit_total=("amount", lambda s: float(s[tx.loc[s.index, "debit_credit"].eq("Debit")].sum())), credit_total=("amount", lambda s: float(s[tx.loc[s.index, "debit_credit"].eq("Credit")].sum())), net_balance=("signed_amount", "sum")).reset_index()
    return SyntheticDataBundle(accounts, vendors, customers, tx, journals, balances)
