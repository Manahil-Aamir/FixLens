import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from app.domain.entities import Diagnosis


class SqliteSessionRepo:
    def __init__(self, db_path: str):
        self._path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as conn:
            with conn:
                conn.execute(
                    "CREATE TABLE IF NOT EXISTS diagnoses ("
                    "id TEXT PRIMARY KEY, data TEXT NOT NULL, updated_at TEXT NOT NULL)"
                )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path)

    def save(self, diagnosis: Diagnosis) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with closing(self._connect()) as conn:
            with conn:
                conn.execute(
                    "INSERT OR REPLACE INTO diagnoses (id, data, updated_at) VALUES (?, ?, ?)",
                    (diagnosis.id, diagnosis.model_dump_json(), now),
                )

    def get(self, diagnosis_id: str) -> Diagnosis | None:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT data FROM diagnoses WHERE id = ?", (diagnosis_id,)
            ).fetchone()
        return Diagnosis.model_validate_json(row[0]) if row else None