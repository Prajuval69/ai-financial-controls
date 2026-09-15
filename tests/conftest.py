from __future__ import annotations

from pathlib import Path

import pytest

from financial_audit_ai.config import Settings


@pytest.fixture(scope="session")
def small_settings(tmp_path_factory: pytest.TempPathFactory) -> Settings:
    root: Path = tmp_path_factory.mktemp("financial-audit")
    return Settings(
        seed=12345,
        n_accounts=20,
        n_vendors=40,
        n_customers=60,
        n_transactions=1200,
        anomaly_rate=0.05,
        quality_defect_rate=0.01,
        model_contamination=0.06,
        model_threshold_quantile=0.94,
        data_dir=root / "data",
        artifact_dir=root / "artifacts",
        report_dir=root / "reports",
        database_path=root / "artifacts" / "test.db",
    )

