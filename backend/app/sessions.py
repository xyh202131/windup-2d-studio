from __future__ import annotations

import secrets
import threading
from dataclasses import dataclass


def _model_basename(model: str) -> str:
    return model.strip().lower().rsplit("/", 1)[-1]


def select_available_image_model(requested: str, available: list[str], preferred: list[str]) -> str:
    models = [model.strip() for model in available if model.strip()]
    if not models:
        raise ValueError("当前账户没有可用模型")

    by_basename: dict[str, str] = {}
    for model in models:
        by_basename.setdefault(_model_basename(model), model)

    for candidate in [requested, *preferred]:
        if candidate in models:
            return candidate
        matched = by_basename.get(_model_basename(candidate))
        if matched:
            return matched

    compatible = [
        model for model in models
        if "gemini" in _model_basename(model) and "image" in _model_basename(model)
    ]
    if compatible:
        return compatible[0]
    raise ValueError("当前账户没有兼容的 Gemini 图像模型")


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
