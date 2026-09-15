from __future__ import annotations

import pandas as pd


def _finding(check_id: str, category: str, severity: str, mask: pd.Series, detail: str) -> pd.DataFrame:
    ids = mask.index[mask].tolist()
    return pd.DataFrame(
        {
            "finding_id": [f"{check_id}-{i + 1:06d}" for i in range(len(ids))],
            "check_id": check_id,
            "category": category,
            "severity": severity,
            "transaction_index": ids,
            "detail": detail,
        }
    )


def validate_data(transactions: pd.DataFrame, accounts: pd.DataFrame, vendors: pd.DataFrame, customers: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return transaction-level findings and a compact quality summary."""
    checks = [
        _finding("DQ001", "Completeness", "High", transactions["transaction_id"].isna() | transactions["account_id"].isna() | transactions["amount"].isna(), "Required transaction field is missing."),
        _finding("DQ002", "Uniqueness", "High", transactions.duplicated(["transaction_date", "account_id", "vendor_id", "customer_id", "amount", "transaction_type"], keep=False), "Potential duplicate at the intended transaction grain."),
        _finding("DQ003", "Referential integrity", "High", transactions["account_id"].notna() & ~transactions["account_id"].isin(accounts["account_id"]), "Account reference does not exist."),
        _finding("DQ004", "Referential integrity", "Medium", transactions["vendor_id"].notna() & ~transactions["vendor_id"].isin(vendors["vendor_id"]), "Vendor reference does not exist."),
        _finding("DQ005", "Referential integrity", "Medium", transactions["customer_id"].notna() & ~transactions["customer_id"].isin(customers["customer_id"]), "Customer reference does not exist."),
        _finding("DQ006", "Validity", "High", transactions["posting_timestamp"].isna(), "Posting timestamp is invalid or missing."),
        _finding("DQ007", "Validity", "High", transactions["amount"].isna() | transactions["amount"].eq(0), "Amount is missing or zero."),
        _finding("DQ008", "Validity", "Medium", ~transactions["debit_credit"].isin(["Debit", "Credit"]), "Debit/credit indicator is invalid."),
    ]
    findings = pd.concat(checks, ignore_index=True)
    if not findings.empty:
        findings["transaction_id"] = findings["transaction_index"].map(transactions["transaction_id"])
    summary = (
        findings.groupby(["check_id", "category", "severity", "detail"], dropna=False)
        .size()
        .rename("finding_count")
        .reset_index()
    )
    expected = pd.DataFrame({"check_id": [f"DQ{i:03d}" for i in range(1, 9)]})
    summary = expected.merge(summary, on="check_id", how="left")
    summary["finding_count"] = summary["finding_count"].fillna(0).astype(int)
    summary["result"] = summary["finding_count"].map(lambda n: "Pass" if n == 0 else "Fail")
    return findings, summary

