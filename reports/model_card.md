# Model Card: isolation-forest-v1.0

## Purpose and intended use
Prioritize unusual synthetic financial transactions for human review and portfolio demonstration.

## Data and features
Deterministic synthetic transactions. Features: manual_entry, account_frequency, is_round_amount, is_negative, log_abs_amount, days_to_period_end, day_of_week, vendor_frequency, transaction_hour. Ground-truth anomaly labels are excluded from training features.

## Algorithm and threshold
Isolation Forest with a normalized anomaly threshold of 0.565875.

## Evaluation
Precision 0.2612; recall 0.2679; F1 0.2646; ROC-AUC 0.8471; PR-AUC 0.2888. Results reflect designed synthetic labels only.

## Explainability
Dependency-light robust feature-deviation explanations are used instead of SHAP to ensure stable offline execution. They indicate association with model behavior, not causation.

## Limitations and prohibited interpretation
Do not treat a score as proof of fraud, an audit conclusion, or evidence of performance on real financial data. Synthetic labels and injected patterns may be easier to detect than real anomalies.

## Monitoring and human oversight
Record model version, threshold, score distribution, metrics, and review outcomes per run. High/Critical cases require human disposition.
