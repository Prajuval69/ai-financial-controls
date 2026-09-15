from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd


class AuditDatabase:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS audit_trail (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT,
                    actor_id TEXT NOT NULL,
                    event_data TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS reviews (
                    review_id TEXT PRIMARY KEY,
                    transaction_id TEXT NOT NULL,
                    reviewer_id TEXT,
                    model_score REAL NOT NULL,
                    risk_level TEXT NOT NULL,
                    rule_findings TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    notes TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                );
                """
            )

    def replace_frame(self, table: str, frame: pd.DataFrame) -> None:
        with self.connect() as conn:
            safe = frame.copy()
            for col in safe.select_dtypes(include=["datetime", "datetimetz"]).columns:
                safe[col] = safe[col].astype(str)
            safe.to_sql(table, conn, if_exists="replace", index=False)

    def append_event(self, event_type: str, entity_type: str, entity_id: str | None, actor_id: str, event_data: dict[str, Any]) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO audit_trail(event_type,entity_type,entity_id,actor_id,event_data,timestamp) VALUES(?,?,?,?,?,?)",
                (event_type, entity_type, entity_id, actor_id, json.dumps(event_data, sort_keys=True, default=str), datetime.now(UTC).isoformat()),
            )

    def read_table(self, table: str, limit: int | None = None) -> pd.DataFrame:
        query = f'SELECT * FROM "{table}"'
        params: tuple[int, ...] = ()
        if limit is not None:
            query += " LIMIT ?"
            params = (limit,)
        with self.connect() as conn:
            return pd.read_sql_query(query, conn, params=params)

