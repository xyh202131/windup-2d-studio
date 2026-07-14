from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .api import create_router
from .config import RUNTIME, SETTINGS, ensure_runtime
from .database import Database
from .provider import QnAIGCProvider
from .service import StudioService
from .sessions import SessionStore


ensure_runtime()
database = Database(RUNTIME / "studio.sqlite3")
database.initialize()
provider = QnAIGCProvider(SETTINGS.api_base)
sessions = SessionStore(SETTINGS.default_key, SETTINGS.default_model)
service = StudioService(database, provider)

app = FastAPI(title="Windup 2D Studio API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(SETTINGS.allowed_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(create_router(service, sessions))
app.mount("/runtime-assets", StaticFiles(directory=RUNTIME), name="runtime-assets")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=SETTINGS.host, port=SETTINGS.port, reload=False)
