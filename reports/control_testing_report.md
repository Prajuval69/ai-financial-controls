# Control Testing Report

> Synthetic controls assessment; not a compliance certification.

Controls tested: **15**. Pass rate: **73.3%**.

| Control | Domain | Result | Severity | Evidence | Recommendation |
|---|---|---|---|---|---|
| C-DAT-01 | Data | Partial | High | 168 transaction-level findings across 8 checks | Resolve exceptions before relying on affected records. |
| C-DAT-02 | Data | Pass | Medium | [{"finding_count":88,"result":"Fail"}] | Retain duplicate evidence and disposition. |
| C-DAT-03 | Data | Partial | High | [{"check_id":"DQ003","finding_count":20},{"check_id":"DQ004","finding_count":0},{"check_id":"DQ005","finding_count":0}] | Quarantine orphan records and correct source references. |
| C-DAT-04 | Data | Pass | High | source=20000, scored=20000 | Investigate any future mismatch immediately. |
| C-MOD-01 | Model | Pass | High | version=isolation-forest-v1.0; threshold=0.565875 | Update version for material changes. |
| C-MOD-02 | Model | Pass | Critical | Feature metadata generated; synthetic_anomaly_label excluded | Maintain leakage test. |
| C-MOD-03 | Model | Pass | High | {"confusion_matrix": {"fn": 571, "fp": 591, "tn": 18629, "tp": 209}, "f1": 0.2645569620253165, "false_negative_count": 571, "false_positive_count": 591, "pr_auc": 0.288844893786267 | Re-evaluate after data or model changes. |
| C-MOD-04 | Model | Pass | Medium | normalized score threshold=0.565875 | Review threshold against review capacity. |
| C-MOD-05 | Model | Partial | Medium | Current-run metrics persisted; cross-run drift baseline not yet accumulated | Accumulate multiple runs and alert on drift. |
| C-OUT-01 | Output | Pass | High | rows=20000; null_scores=0; flagged=800 | Reject incomplete scoring outputs. |
| C-OUT-02 | Output | Pass | High | Queue generated from High/Critical risk levels | Monitor queue aging and decisions. |
| C-OUT-03 | Output | Pass | High | Audit event schema and append-only service implemented | Restrict direct database write access in production. |
| C-HUM-01 | Human oversight | Pass | High | All four actions validated by service and API schema | Require named authenticated reviewers in production. |
| C-CHG-01 | Change/access | Partial | High | Configuration file retained; authentication/RBAC simulated only | Add enterprise identity, RBAC, and change approval before production use. |
| C-INC-01 | Change/access | Pass | Medium | Escalation decision is persisted and filterable | Define production incident SLAs and ownership. |