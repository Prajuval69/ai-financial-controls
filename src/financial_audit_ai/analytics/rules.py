from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import pandas as pd

from financial_audit_ai.config import Settings


@dataclass(frozen=True)
class Rule:
    rule_id: str
    description: str
    severity: str
    evaluate: Callable[[pd.DataFrame, Settings], pd.Series]
    evidence: Callable[[pd.DataFrame], pd.Series]


def _duplicate(tx: pd.DataFrame, _: Settings) -> pd.Series:
    return tx.duplicated(["transaction_date", "account_id", "vendor_id", "customer_id", "amount", "transaction_type"], keep=False)


def _weekend(tx: pd.DataFrame, _: Settings) -> pd.Series:
    return pd.to_datetime(tx.transaction_date, errors="coerce").dt.dayofweek.ge(5)


def _after_hours(tx: pd.DataFrame, _: Settings) -> pd.Series:
    hour = pd.to_datetime(tx.posting_timestamp, errors="coerce").dt.hour
    return hour.lt(7) | hour.ge(20)


def _round_amount(tx: pd.DataFrame, _: Settings) -> pd.Series:
    amount = pd.to_numeric(tx.amount, errors="coerce").abs()
    return amount.ge(10_000) & amount.mod(10_000).eq(0)


def _large_amount(tx: pd.DataFrame, _: Settings) -> pd.Series:
    amount = pd.to_numeric(tx.amount, errors="coerce").abs()
    q1, q3 = amount.quantile([0.25, 0.75])
    return amount.gt(q3 + 6 * (q3 - q1))


def _period_end(tx: pd.DataFrame, _: Settings) -> pd.Series:
    date = pd.to_datetime(tx.transaction_date, errors="coerce")
    return (date.dt.days_in_month - date.dt.day).le(1)


def _unusual_combo(tx: pd.DataFrame, _: Settings) -> pd.Series:
    counts = tx.groupby(["vendor_id", "account_id"], dropna=False).transaction_id.transform("count")
    return tx.vendor_id.notna() & counts.eq(1)


def _reversal(tx: pd.DataFrame, _: Settings) -> pd.Series:
    return pd.to_numeric(tx.amount, errors="coerce").lt(0) | tx.description.str.contains("reversal", case=False, na=False)


def _out_of_period(tx: pd.DataFrame, settings: Settings) -> pd.Series:
    date = pd.to_datetime(tx.transaction_date, errors="coerce")
    return date.lt(pd.Timestamp(settings.period_start)) | date.gt(pd.Timestamp(settings.period_end))


def _invalid_data(tx: pd.DataFrame, _: Settings) -> pd.Series:
    return tx.account_id.isna() | tx.posting_timestamp.isna() | pd.to_numeric(tx.amount, errors="coerce").fillna(0).eq(0)


def default_rules() -> list[Rule]:
    ev = lambda label: (lambda tx: pd.Series(label, index=tx.index) + tx.transaction_id.astype(str))
    return [
        Rule("R001", "Potential duplicate transaction", "High", _duplicate, ev("Matching transaction attributes for ")),
        Rule("R002", "Weekend posting", "Low", _weekend, ev("Weekend transaction ")),
        Rule("R003", "After-hours posting", "Moderate", _after_hours, ev("Posting outside 07:00-20:00 for ")),
        Rule("R004", "Unusual round-dollar amount", "Moderate", _round_amount, lambda tx: "Round amount " + tx.amount.astype(str)),
        Rule("R005", "Unusually large transaction", "High", _large_amount, lambda tx: "Amount " + tx.amount.astype(str) + " exceeds robust threshold"),
        Rule("R006", "Period-end concentration", "Low", _period_end, ev("Transaction posted in final two days of month: ")),
        Rule("R007", "Unusual vendor/account combination", "Moderate", _unusual_combo, lambda tx: "Rare pairing " + tx.vendor_id.astype(str) + "/" + tx.account_id.astype(str)),
        Rule("R008", "Suspicious reversal", "High", _reversal, lambda tx: "Negative/reversal amount " + tx.amount.astype(str)),
        Rule("R009", "Out-of-period activity", "Critical", _out_of_period, lambda tx: "Date outside configured period: " + tx.transaction_date.astype(str)),
        Rule("R010", "Data-quality exception", "High", _invalid_data, ev("Invalid or missing required field on ")),
    ]


def run_rules(transactions: pd.DataFrame, settings: Settings) -> pd.DataFrame:
    records: list[pd.DataFrame] = []
    for rule in default_rules():
        mask = rule.evaluate(transactions, settings).fillna(False)
        if not mask.any():
            continue
        evidence = rule.evidence(transactions)
        records.append(pd.DataFrame({
            "finding_id": [f"{rule.rule_id}-{i:07d}" for i in transactions.index[mask]],
            "transaction_id": transactions.loc[mask, "transaction_id"].values,
            "rule_id": rule.rule_id,
            "description": rule.description,
            "severity": rule.severity,
            "evidence": evidence.loc[mask].values,
        }))
    return pd.concat(records, ignore_index=True) if records else pd.DataFrame(columns=["finding_id", "transaction_id", "rule_id", "description", "severity", "evidence"])


SEVERITY_WEIGHT = {"Low": 1, "Moderate": 2, "High": 3, "Critical": 4}


def aggregate_rule_findings(transactions: pd.DataFrame, findings: pd.DataFrame) -> pd.DataFrame:
    if findings.empty:
        return pd.DataFrame({"transaction_id": transactions.transaction_id, "rule_count": 0, "max_rule_severity": 0, "rule_flags": ""})
    work = findings.assign(severity_weight=findings.severity.map(SEVERITY_WEIGHT))
    return work.groupby("transaction_id").agg(rule_count=("rule_id", "count"), max_rule_severity=("severity_weight", "max"), rule_flags=("rule_id", lambda s: ",".join(sorted(set(s))))).reset_index()
