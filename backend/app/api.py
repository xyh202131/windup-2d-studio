from __future__ import annotations

import json
import secrets
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse

from .config import CONTRACT, RUNTIME
from .database import now_iso
from .models import (
    ActionCreateRequest,
    ActionPlanRequest,
    CharacterCreateFields,
    ProviderConnect,
    RegenerateRequest,
    ReviewRequest,
    SelectionRequest,
)
from .processing import ImageQualityError, validate_upload
from .provider import ProviderError
from .service import StudioService
from .sessions import SessionStore


COOKIE = "windup_2d_session"


def create_router(service: StudioService, sessions: SessionStore) -> APIRouter:
    router = APIRouter(prefix="/api/v1")

    def session_id(request: Request, response: Response) -> str:
        value = request.cookies.get(COOKIE)
        if not value:
            value = sessions.create_id()
            response.set_cookie(COOKIE, value, httponly=True, samesite="lax", secure=False, max_age=60 * 60 * 12)
        return value

    def session(request: Request, response: Response):
        return sessions.get(session_id(request, response))

    def fail(error: Exception) -> HTTPException:
        if isinstance(error, KeyError):
            return HTTPException(404, "资源不存在")
        if isinstance(error, (ValueError, ImageQualityError)):
            return HTTPException(409, str(error))
        if isinstance(error, ProviderError):
            return HTTPException(error.status or 502, str(error))
        return HTTPException(500, str(error))

    @router.get("/health")
    def health() -> dict:
        return {"ok": True, "service": "windup-2d-studio", "contractVersion": CONTRACT["version"], "time": now_iso()}

    @router.get("/contract")
    def contract() -> dict:
        return CONTRACT

    @router.get("/provider/session")
    def provider_status(request: Request, response: Response) -> dict:
        current = session(request, response)
        return {**current.public(), "models": CONTRACT["imageModels"]}

    @router.put("/provider/session")
    def connect_provider(payload: ProviderConnect, request: Request, response: Response) -> dict:
        sid = session_id(request, response)
        try:
            service.provider.verify(payload.apiKey)
            models = service.provider.models(payload.apiKey)
            if payload.model not in models and payload.apiKey != "demo":
                raise ValueError("所选模型不在当前账户可用列表中")
            current = sessions.connect(sid, payload.apiKey, payload.model)
            return {**current.public(), "models": models}
        except Exception as error:
            raise fail(error)

    @router.delete("/provider/session")
    def disconnect_provider(request: Request, response: Response) -> dict:
        sid = session_id(request, response)
        sessions.clear(sid)
        response.delete_cookie(COOKIE)
        return {"configured": False, "verified": False, "model": "", "models": CONTRACT["imageModels"]}

    @router.post("/characters", status_code=202)
    async def create_character(
        request: Request,
        response: Response,
        name: str = Form(...),
        description: str = Form(...),
        style: str = Form(...),
        customStyle: str = Form(""),
        reference: UploadFile | None = File(None),
    ) -> dict:
        try:
            current = session(request, response)
            if not current.verified:
                raise ValueError("请先连接生成服务")
            fields = CharacterCreateFields(name=name, description=description, style=style, customStyle=customStyle).model_dump()
            reference_path = ""
            if reference and reference.filename:
                data = await reference.read()
                suffix, _ = validate_upload(data, reference.filename)
                upload_id = f"ref_{secrets.token_hex(8)}{suffix}"
                destination = RUNTIME / "uploads" / upload_id
                destination.write_bytes(data)
                reference_path = str(destination)
            return service.create_character(fields, reference_path, current)
        except Exception as error:
            raise fail(error)

    @router.get("/characters")
    def list_characters() -> dict:
        return {"items": [service.character_public(item) for item in service.db.list_characters()]}

    @router.get("/characters/{character_id}")
    def get_character(character_id: str) -> dict:
        try:
            return service.character_public(service.db.get_character(character_id))
        except Exception as error:
            raise fail(error)

    @router.post("/characters/{character_id}/actions/plan")
    def plan_action(character_id: str, payload: ActionPlanRequest) -> dict:
        try:
            service.db.get_character(character_id)
            return service.action_plan(payload.model_dump())
        except Exception as error:
            raise fail(error)

    @router.post("/characters/{character_id}/actions", status_code=202)
    def create_action(character_id: str, payload: ActionCreateRequest, request: Request, response: Response) -> dict:
        try:
            current = session(request, response)
            if not current.verified:
                raise ValueError("请先连接生成服务")
            return service.create_action(character_id, payload.model_dump(), current)
        except Exception as error:
            raise fail(error)

    @router.get("/jobs")
    def list_jobs(characterId: str | None = None) -> dict:
        return {"items": [service.public_job(item) for item in service.db.list_jobs(characterId)]}

    @router.get("/jobs/{job_id}")
    def get_job(job_id: str) -> dict:
        try:
            return service.public_job(service.db.get_job(job_id))
        except Exception as error:
            raise fail(error)

    @router.post("/jobs/{job_id}/retry", status_code=202)
    def retry_job(job_id: str, request: Request, response: Response) -> dict:
        try:
            current = session(request, response)
            if not current.verified:
                raise ValueError("请先连接生成服务")
            return service.retry(job_id, current)
        except Exception as error:
            raise fail(error)

    @router.post("/jobs/{job_id}/cancel")
    def cancel_job(job_id: str) -> dict:
        try:
            return service.cancel(job_id)
        except Exception as error:
            raise fail(error)

    @router.post("/jobs/{job_id}/outputs/{slot:path}/regenerate", status_code=202)
    def regenerate(job_id: str, slot: str, payload: RegenerateRequest, request: Request, response: Response) -> dict:
        try:
            current = session(request, response)
            if not current.verified:
                raise ValueError("请先连接生成服务")
            return service.regenerate(job_id, slot, payload.note, current)
        except Exception as error:
            raise fail(error)

    @router.put("/jobs/{job_id}/outputs/{slot:path}/selection")
    def select(job_id: str, slot: str, payload: SelectionRequest) -> dict:
        try:
            return service.select_version(job_id, slot, payload.versionId)
        except Exception as error:
            raise fail(error)

    @router.put("/jobs/{job_id}/outputs/{slot:path}/review")
    def review(job_id: str, slot: str, payload: ReviewRequest) -> dict:
        try:
            return service.review(job_id, slot, payload.decision, payload.note)
        except Exception as error:
            raise fail(error)

    @router.post("/jobs/{job_id}/promote")
    def promote(job_id: str) -> dict:
        try:
            return service.promote(job_id)
        except Exception as error:
            raise fail(error)

    @router.get("/characters/{character_id}/export")
    def export(character_id: str) -> FileResponse:
        try:
            path = service.export_character(character_id)
            return FileResponse(path, media_type="application/zip", filename=f"{character_id}.zip")
        except Exception as error:
            raise fail(error)

    return router

