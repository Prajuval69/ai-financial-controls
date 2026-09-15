from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Settings:
    seed: int = 20260915
    n_accounts: int = 50
    n_vendors: int = 300
    n_customers: int = 500
    n_transactions: int = 20_000
    anomaly_rate: float = 0.035
    quality_defect_rate: float = 0.004
    model_contamination: float = 0.04
    model_threshold_quantile: float = 0.96
    review_risk_levels: list[str] = field(default_factory=lambda: ["High", "Critical"])
    data_dir: Path = Path("data/generated")
    artifact_dir: Path = Path("artifacts")
    report_dir: Path = Path("reports")
    database_path: Path = Path("artifacts/audit_analytics.db")
    model_version: str = "isolation-forest-v1.0"
    period_start: str = "2025-01-01"
    period_end: str = "2025-12-31"

    @classmethod
    def from_yaml(cls, path: str | Path = "configs/default.yaml") -> Settings:
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        for key in ("data_dir", "artifact_dir", "report_dir", "database_path"):
            if key in raw:
                raw[key] = Path(raw[key])
        return cls(**raw)

    def ensure_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        self.report_dir.mkdir(parents=True, exist_ok=True)

