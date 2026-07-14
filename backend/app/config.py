from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "runtime"
CONTRACT_PATH = ROOT / "contracts" / "studio.v1.json"


@dataclass(frozen=True)
class Settings:
    host: str = os.getenv("WINDUP_2D_HOST", "127.0.0.1")
    port: int = int(os.getenv("WINDUP_2D_PORT", "8002"))
    api_base: str = os.getenv("QNAIGC_BASE", "https://api.qnaigc.com/v1")
    default_model: str = os.getenv("QNAIGC_IMAGE_MODEL", "gemini-3.1-flash-image-preview")
    default_key: str = os.getenv("QNAIGC_KEY", "")
    max_workers: int = max(1, int(os.getenv("WINDUP_2D_MAX_WORKERS", "2")))
    allowed_origins: tuple[str, ...] = tuple(
        item.strip() for item in os.getenv(
            "WINDUP_2D_ALLOWED_ORIGINS",
            "http://127.0.0.1:5175,http://localhost:5175",
        ).split(",") if item.strip()
    )


SETTINGS = Settings()
CONTRACT = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def ensure_runtime() -> None:
    for name in ("uploads", "jobs", "assets", "backups", "exports", "logs"):
        (RUNTIME / name).mkdir(parents=True, exist_ok=True)
