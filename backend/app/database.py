from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterator


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


class Database:
    def __init__(self, path: Path):
        self.path = path
        self._write_lock = threading.RLock()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=15, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        try:
            yield connection
        finally:
            connection.close()

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._write_lock, self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS characters (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    style TEXT NOT NULL,
                    custom_style TEXT NOT NULL DEFAULT '',
                    reference_path TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    character_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    progress INTEGER NOT NULL DEFAULT 0,
                    message TEXT NOT NULL DEFAULT '',
                    payload_json TEXT NOT NULL,
                    outputs_json TEXT NOT NULL DEFAULT '{}',
                    error TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(character_id) REFERENCES characters(id)
                );
                CREATE INDEX IF NOT EXISTS idx_jobs_character ON jobs(character_id, created_at DESC);
                """
            )
            connection.execute(
                "UPDATE jobs SET status='interrupted', message='服务重启，任务可重试', updated_at=? "
                "WHERE status IN ('queued','planning','generating','processing','promoting')",
                (now_iso(),),
            )
            connection.commit()

    def create_character(self, record: dict) -> dict:
        with self._write_lock, self.connect() as connection:
            connection.execute(
                "INSERT INTO characters(id,name,description,style,custom_style,reference_path,status,created_at,updated_at) "
                "VALUES(:id,:name,:description,:style,:custom_style,:reference_path,:status,:created_at,:updated_at)",
                record,
            )
            connection.commit()
        return self.get_character(record["id"])

    def get_character(self, character_id: str) -> dict:
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM characters WHERE id=?", (character_id,)).fetchone()
        if not row:
            raise KeyError(character_id)
        return dict(row)

    def list_characters(self) -> list[dict]:
        with self.connect() as connection:
            rows = connection.execute("SELECT * FROM characters ORDER BY created_at DESC").fetchall()
        return [dict(row) for row in rows]

    def update_character(self, character_id: str, **changes) -> dict:
        allowed = {"name", "description", "style", "custom_style", "reference_path", "status", "updated_at"}
        values = {key: value for key, value in changes.items() if key in allowed}
        values["updated_at"] = now_iso()
        assignments = ",".join(f"{key}=?" for key in values)
        with self._write_lock, self.connect() as connection:
            connection.execute(f"UPDATE characters SET {assignments} WHERE id=?", (*values.values(), character_id))
            connection.commit()
        return self.get_character(character_id)

    def create_job(self, record: dict) -> dict:
        values = dict(record)
        values["payload_json"] = json.dumps(values.pop("payload"), ensure_ascii=False)
        values["outputs_json"] = json.dumps(values.pop("outputs", {}), ensure_ascii=False)
        with self._write_lock, self.connect() as connection:
            connection.execute(
                "INSERT INTO jobs(id,type,character_id,status,progress,message,payload_json,outputs_json,error,created_at,updated_at) "
                "VALUES(:id,:type,:character_id,:status,:progress,:message,:payload_json,:outputs_json,:error,:created_at,:updated_at)",
                values,
            )
            connection.commit()
        return self.get_job(record["id"])

    @staticmethod
    def _job(row: sqlite3.Row) -> dict:
        result = dict(row)
        result["payload"] = json.loads(result.pop("payload_json"))
        result["outputs"] = json.loads(result.pop("outputs_json"))
        return result

    def get_job(self, job_id: str) -> dict:
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        if not row:
            raise KeyError(job_id)
        return self._job(row)

    def list_jobs(self, character_id: str | None = None) -> list[dict]:
        with self.connect() as connection:
            if character_id:
                rows = connection.execute("SELECT * FROM jobs WHERE character_id=? ORDER BY created_at DESC", (character_id,)).fetchall()
            else:
                rows = connection.execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT 100").fetchall()
        return [self._job(row) for row in rows]

    def update_job(self, job_id: str, **changes) -> dict:
        allowed = {"status", "progress", "message", "outputs", "error", "payload"}
        values: dict = {}
        for key, value in changes.items():
            if key not in allowed:
                continue
            values[f"{key}_json" if key in {"outputs", "payload"} else key] = (
                json.dumps(value, ensure_ascii=False) if key in {"outputs", "payload"} else value
            )
        values["updated_at"] = now_iso()
        assignments = ",".join(f"{key}=?" for key in values)
        with self._write_lock, self.connect() as connection:
            connection.execute(f"UPDATE jobs SET {assignments} WHERE id=?", (*values.values(), job_id))
            connection.commit()
        return self.get_job(job_id)

