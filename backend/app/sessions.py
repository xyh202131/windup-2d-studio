from __future__ import annotations

import secrets
import threading
from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderSession:
    api_key: str = ""
    model: str = ""
    verified: bool = False
    error: str = ""

    def public(self) -> dict:
        return {"configured": bool(self.api_key), "verified": self.verified, "model": self.model, "error": self.error}


class SessionStore:
    def __init__(self, default_key: str = "", default_model: str = ""):
        self.default_key = default_key
        self.default_model = default_model
        self._items: dict[str, ProviderSession] = {}
        self._lock = threading.RLock()

    def create_id(self) -> str:
        return secrets.token_urlsafe(24)

    def get(self, session_id: str) -> ProviderSession:
        with self._lock:
            if session_id not in self._items:
                self._items[session_id] = ProviderSession(
                    api_key=self.default_key,
                    model=self.default_model,
                    verified=bool(self.default_key),
                )
            return self._items[session_id]

    def connect(self, session_id: str, api_key: str, model: str) -> ProviderSession:
        value = ProviderSession(api_key=api_key, model=model, verified=True)
        with self._lock:
            self._items[session_id] = value
        return value

    def clear(self, session_id: str) -> None:
        with self._lock:
            self._items.pop(session_id, None)
