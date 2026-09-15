from __future__ import annotations

import numpy as np
import pandas as pd


def calculate_financial_analytics(transactions: pd.DataFrame) -> dict[str, object]:
    tx = transactions.copy()
    tx["transaction_date"] = pd.to_datetime(tx["transaction_date"], errors="coerce")
    valid_amounts = pd.to_numeric(tx["amount"], errors="coerce")
    tx["month"] = tx["transaction_date"].dt.to_period("M").astype(str)
    monthly = tx.groupby("month", dropna=False).agg(transaction_count=("transaction_id", "count"), transaction_value=("amount", "sum")).reset_index()
    monthly["value_change_pct"] = monthly["transaction_value"].pct_change().replace([np.inf, -np.inf], np.nan) * 100
    account = tx.groupby("account_id", dropna=False).agg(transaction_count=("transaction_id", "count"), transaction_value=("amount", "sum")).reset_index()
    vendor = tx.groupby("vendor_id", dropna=False).agg(transaction_count=("transaction_id", "count"), transaction_value=("amount", "sum")).reset_index()
    type_dist = tx.groupby("transaction_type").agg(transaction_count=("transaction_id", "count"), transaction_value=("amount", "sum")).reset_index()
    debit_total = float(tx.loc[tx.debit_credit.eq("Debit"), "amount"].sum())
    credit_total = float(tx.loc[tx.debit_credit.eq("Credit"), "amount"].sum())
    return {
        "summary": {
            "transaction_count": len(tx),
            "total_transaction_value": float(valid_amounts.sum()),
            "average_transaction_amount": float(valid_amounts.mean()),
            "median_transaction_amount": float(valid_amounts.median()),
            "manual_journal_count": int(tx.journal_source.isin(["Manual", "Spreadsheet Upload"]).sum()),
            "period_end_count": int(tx.transaction_date.dt.is_month_end.sum()),
            "debit_total": debit_total,
            "credit_total": credit_total,
            "debit_credit_difference": debit_total - credit_total,
        },
        "monthly": monthly,
        "account_activity": account,
        "vendor_activity": vendor,
        "transaction_types": type_dist,
    }

