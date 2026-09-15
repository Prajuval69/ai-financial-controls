from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from financial_audit_ai.config import Settings
from financial_audit_ai.persistence.database import AuditDatabase
from financial_audit_ai.remediation.service import RemediationService
from financial_audit_ai.reviews.service import ReviewService

settings = Settings.from_yaml(ROOT / "configs/default.yaml")
database = AuditDatabase(ROOT / settings.database_path)

st.set_page_config(page_title="Synthetic Financial Controls", page_icon="◈", layout="wide")
st.markdown("""
<style>
:root { --ink:#18211c; --sage:#59766a; --paper:#f5f2e9; --amber:#c58a36; }
.stApp { background: var(--paper); color: var(--ink); }
.stApp p, .stApp label, .stApp [data-testid="stCaptionContainer"],
.stApp [data-testid="stMetricLabel"], .stApp [data-testid="stMarkdownContainer"] { color:var(--ink); }
[data-baseweb="tab"] { color:#496057 !important; font-weight:600; }
[data-baseweb="tab"][aria-selected="true"] { color:#a94f45 !important; }
[data-testid="stMetric"] { background:#fffdf7; border:1px solid #ded9ca; padding:14px; border-radius:4px; }
[data-testid="stMetricValue"] { color:var(--ink); font-family:Georgia,serif; }
.synthetic-note { border-left:4px solid var(--amber); padding:10px 14px; background:#fff8e8; margin-bottom:18px; }
h1,h2,h3 { font-family:Georgia,serif !important; color:var(--ink) !important; }
</style>
""", unsafe_allow_html=True)

st.title("Financial Controls & Audit Analytics")
st.caption("AI-assisted exception triage • synthetic portfolio environment")
st.markdown('<div class="synthetic-note"><b>Decision-support only.</b> All data, users, controls, and findings are synthetic. An AI anomaly flag is not confirmation of fraud or an audit opinion.</div>', unsafe_allow_html=True)

if not database.path.exists():
    st.error("Generated artifacts are not available. Run `python scripts/run_pipeline.py` first.")
    st.stop()


@st.cache_data(ttl=10)
def load(table: str) -> pd.DataFrame:
    return database.read_table(table)


transactions = load("transactions")
anomalies = load("anomalies")
controls = load("controls")
risks = load("risk_register")
reviews = load("reviews")
remediation = load("remediation")
monthly = load("monthly_analytics")

pages = st.tabs(["Executive Overview", "Transaction Analytics", "Anomaly Detection", "Model Performance", "Controls Testing", "Risk Register", "Human Review", "Audit Trail", "Remediation"])

with pages[0]:
    audit = load("audit_trail")
    metrics = [
        ("Transactions", f"{len(transactions):,}"),
        ("Transaction value", f"{pd.to_numeric(transactions.amount).sum()/1e6:,.1f}M"),
        ("Model flags", f"{int(anomalies.model_anomaly_flag.sum()):,}"),
        ("High/Critical", f"{len(risks):,}"),
        ("Control pass rate", f"{controls.result.eq('Pass').mean():.0%}"),
        ("Open reviews", f"{int(reviews.decision.eq('pending').sum()):,}"),
        ("Escalations", f"{int(reviews.decision.eq('escalate').sum()):,}"),
    ]
    for row_metrics in (metrics[:4], metrics[4:]):
        cols = st.columns(len(row_metrics))
        for col, (label, value) in zip(cols, row_metrics, strict=True):
            col.metric(label, value)
    left, right = st.columns([1.6, 1])
    with left:
        st.subheader("Monthly transaction value")
        st.line_chart(monthly.set_index("month")["transaction_value"])
    with right:
        st.subheader("Risk distribution")
        st.bar_chart(load("transaction_risks").risk_level.value_counts())

with pages[1]:
    selected_types = st.multiselect("Transaction type", sorted(transactions.transaction_type.dropna().unique()), default=[])
    view = transactions if not selected_types else transactions[transactions.transaction_type.isin(selected_types)]
    c1, c2, c3 = st.columns(3)
    c1.metric("Filtered records", f"{len(view):,}"); c2.metric("Average amount", f"{pd.to_numeric(view.amount).mean():,.2f}"); c3.metric("Manual journals", f"{view.journal_source.isin(['Manual','Spreadsheet Upload']).sum():,}")
    left, right = st.columns(2)
    with left: st.bar_chart(view.groupby("transaction_type").amount.sum())
    with right: st.bar_chart(view.groupby("account_id").amount.sum().nlargest(15))
    st.dataframe(view.sort_values("transaction_date", ascending=False).head(500), use_container_width=True)

with pages[2]:
    levels = st.multiselect("Risk level", ["Critical", "High", "Moderate", "Low"], default=["Critical", "High"])
    filtered = anomalies[anomalies.risk_level.isin(levels)]
    c1, c2, c3 = st.columns(3); c1.metric("Selected cases", len(filtered)); c2.metric("Model flags", int(filtered.model_anomaly_flag.sum())); c3.metric("Rule findings", int(filtered.rule_count.sum()))
    left, right = st.columns(2)
    with left: st.bar_chart(load("rule_findings").rule_id.value_counts())
    with right: st.bar_chart(anomalies.normalized_anomaly_score.value_counts(bins=20, sort=False))
    st.dataframe(filtered.sort_values("risk_score", ascending=False).head(1000), use_container_width=True)

with pages[3]:
    metric_data = json.loads((ROOT / settings.artifact_dir / "model_metrics.json").read_text(encoding="utf-8"))
    cols = st.columns(5)
    for col, key in zip(cols, ["precision", "recall", "f1", "roc_auc", "pr_auc"], strict=True): col.metric(key.replace("_", " ").upper(), f"{metric_data[key]:.3f}")
    left, right = st.columns(2)
    with left:
        st.subheader("Threshold sensitivity")
        st.line_chart(load("threshold_sensitivity").set_index("threshold")[["precision", "recall", "f1"]])
    with right:
        st.subheader("Global feature importance")
        st.bar_chart(load("global_feature_importance").set_index("feature")["importance"])
    st.info("Metrics use designed synthetic labels. Feature explanations describe model behavior, not causal inference.")

with pages[4]:
    selected_results = st.multiselect("Result", ["Pass", "Partial", "Fail", "Not Tested"], default=["Partial", "Fail"])
    st.bar_chart(controls.result.value_counts())
    st.dataframe(controls[controls.result.isin(selected_results)] if selected_results else controls, use_container_width=True)

with pages[5]:
    risk_levels = st.multiselect("Register risk level", ["Critical", "High"], default=["Critical", "High"])
    st.dataframe(risks[risks.risk_level.isin(risk_levels)], use_container_width=True)

with pages[6]:
    st.metric("Pending queue", int(reviews.decision.eq("pending").sum()))
    pending = reviews[reviews.decision.eq("pending")]
    st.dataframe(pending.head(500), use_container_width=True)
    if not pending.empty:
        with st.form("review_form"):
            review_id = st.selectbox("Review ID", pending.review_id.tolist())
            reviewer = st.text_input("Synthetic reviewer ID", value="U-REVIEWER-001")
            decision = st.selectbox("Decision", ["approve", "reject", "escalate", "request_more_information"])
            notes = st.text_area("Review notes")
            submitted = st.form_submit_button("Record decision")
        if submitted:
            try:
                ReviewService(database).decide(review_id, reviewer, decision, notes)
                st.cache_data.clear(); st.success("Decision recorded with an audit event. Refresh to view updated queue.")
            except (ValueError, KeyError) as exc: st.error(str(exc))

with pages[7]:
    audit = load("audit_trail")
    event_types = st.multiselect("Event type", sorted(audit.event_type.unique()))
    st.dataframe(audit[audit.event_type.isin(event_types)] if event_types else audit, use_container_width=True)

with pages[8]:
    status = st.multiselect("Status", sorted(remediation.status.unique()), default=list(remediation.status.unique()))
    st.dataframe(remediation[remediation.status.isin(status)], use_container_width=True)
    if not remediation.empty:
        with st.form("remediation_form"):
            remediation_id = st.selectbox("Remediation ID", remediation.remediation_id.tolist())
            new_status = st.selectbox("New status", ["Open", "In Progress", "Completed", "Deferred"])
            actor_id = st.text_input("Synthetic owner ID", value="U-CONTROL-001")
            remediation_notes = st.text_area("Update notes")
            update_submitted = st.form_submit_button("Record remediation update")
        if update_submitted:
            try:
                RemediationService(database).update(remediation_id, new_status, actor_id, remediation_notes)
                st.cache_data.clear()
                st.success("Remediation status and audit event recorded. Refresh to view the update.")
            except (ValueError, KeyError) as exc:
                st.error(str(exc))
