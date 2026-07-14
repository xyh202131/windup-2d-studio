from __future__ import annotations

import json
import secrets
import shutil
import threading
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .config import CONTRACT, RUNTIME, SETTINGS
from .database import Database, now_iso
from .processing import ImageQualityError, normalize_hd, sequence_quality
from .provider import ProviderError, QnAIGCProvider
from .sessions import ProviderSession


ACTIVE = {"queued", "planning", "generating", "processing", "promoting"}


def identifier(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(6)}"


class StudioService:
    def __init__(self, database: Database, provider: QnAIGCProvider):
        self.db = database
        self.provider = provider
        self.executor = ThreadPoolExecutor(max_workers=SETTINGS.max_workers, thread_name_prefix="windup2d")
        self._locks: dict[str, threading.RLock] = {}
        self._locks_guard = threading.RLock()

    def _lock(self, job_id: str) -> threading.RLock:
        with self._locks_guard:
            return self._locks.setdefault(job_id, threading.RLock())

    @staticmethod
    def public_job(job: dict) -> dict:
        result = dict(job)
        result["characterId"] = result.pop("character_id")
        result["createdAt"] = result.pop("created_at")
        result["updatedAt"] = result.pop("updated_at")
        payload = dict(result.get("payload", {}))
        payload.pop("referencePath", None)
        result["payload"] = payload
        for output in result.get("outputs", {}).values():
            for version in output.get("versions", []):
                version.pop("path", None)
        return result

    def character_public(self, record: dict) -> dict:
        result = {
            "id": record["id"], "name": record["name"], "description": record["description"],
            "style": record["style"], "customStyle": record["custom_style"], "status": record["status"],
            "createdAt": record["created_at"], "updatedAt": record["updated_at"], "masters": {}, "actions": [],
        }
        asset_root = RUNTIME / "assets" / record["id"]
        for view in CONTRACT["views"]:
            path = asset_root / "masters" / f"{view}.png"
            if path.exists():
                result["masters"][view] = f"/runtime-assets/assets/{record['id']}/masters/{view}.png"
        for job in self.db.list_jobs(record["id"]):
            if job["type"] == "action" and job["status"] == "approved":
                result["actions"].append({
                    "jobId": job["id"], "action": job["payload"]["action"], "view": job["payload"]["view"],
                    "frameCount": job["payload"]["frameCount"], "loop": job["payload"]["loop"],
                })
        return result

    def create_character(self, fields: dict, reference_path: str, session: ProviderSession) -> dict:
        character_id, job_id, timestamp = identifier("char"), identifier("job"), now_iso()
        self.db.create_character({
            "id": character_id, "name": fields["name"], "description": fields["description"],
            "style": fields["style"], "custom_style": fields.get("customStyle", ""),
            "reference_path": reference_path, "status": "draft", "created_at": timestamp, "updated_at": timestamp,
        })
        job = self.db.create_job({
            "id": job_id, "type": "character", "character_id": character_id, "status": "queued", "progress": 0,
            "message": "人物母版任务已排队", "payload": {**fields, "referencePath": reference_path}, "outputs": {},
            "error": "", "created_at": timestamp, "updated_at": timestamp,
        })
        self.executor.submit(self._run_character, job_id, session)
        return self.public_job(job)

    def _cancelled(self, job_id: str) -> bool:
        return self.db.get_job(job_id)["status"] == "cancelled"

    def _prompt_master(self, character: dict, view: str) -> str:
        style = CONTRACT["styles"][character["style"]]["prompt"]
        custom = f"Additional art direction: {character['custom_style']}. " if character.get("custom_style") else ""
        return (
            f"Create one original full-body {style}. Character: {character['description']}. {custom}"
            f"Camera: {CONTRACT['views'][view]['prompt']}. Preserve exact identity, face, hairstyle, costume, palette and proportions. "
            "Neutral standing pose, centered head-to-feet, clean readable silhouette, no text, no frame, no shadow. "
            "Use a perfectly flat vivid magenta #ff00d4 background with no gradient. Native high-resolution 1024 square image."
        )

    def _version(self, job_id: str, slot: str, raw: bytes, target: int, label: str) -> dict:
        version_id = identifier("ver")
        folder = RUNTIME / "jobs" / job_id / slot.replace(":", "_") / version_id
        raw_path, output_path = folder / "raw.png", folder / "output.png"
        folder.mkdir(parents=True, exist_ok=True)
        raw_path.write_bytes(raw)
        quality = normalize_hd(raw_path, output_path, target)
        relative = output_path.relative_to(RUNTIME).as_posix()
        return {
            "id": version_id, "label": label, "url": f"/runtime-assets/{relative}", "path": str(output_path),
            "width": target, "height": target, "quality": quality, "createdAt": now_iso(),
        }

    @staticmethod
    def _slot(slot: str, label: str, kind: str, version: dict, index: int | None = None) -> dict:
        return {
            "slot": slot, "label": label, "kind": kind, "index": index, "selectedVersionId": version["id"],
            "review": {"decision": "pending", "note": ""}, "versions": [version],
        }

    def _run_character(self, job_id: str, session: ProviderSession) -> None:
        with self._lock(job_id):
            try:
                job = self.db.update_job(job_id, status="generating", progress=4, message="正在建立三视角身份母版")
                character = self.db.get_character(job["character_id"])
                refs = [Path(character["reference_path"])] if character["reference_path"] else []
                outputs = job["outputs"]
                views = list(CONTRACT["views"])
                for index, view in enumerate(views):
                    if self._cancelled(job_id):
                        return
                    raw = self.provider.generate_image(
                        self._prompt_master(character, view), refs, session.api_key, session.model,
                        size=CONTRACT["masterSize"], seed_label=f"{view} master",
                    )
                    version = self._version(job_id, f"master:{view}", raw, CONTRACT["masterSize"], "初始母版")
                    outputs[f"master:{view}"] = self._slot(f"master:{view}", CONTRACT["views"][view]["label"], "master", version)
                    self.db.update_job(job_id, outputs=outputs, progress=15 + round((index + 1) / len(views) * 72), message=f"已完成{CONTRACT['views'][view]['label']}母版")
                self.db.update_job(job_id, status="awaiting_review", progress=100, message="三视角母版已完成，请逐项审核", outputs=outputs)
            except (ProviderError, ImageQualityError, Exception) as error:
                self.db.update_job(job_id, status="failed", error=str(error), message=str(error))

    def action_plan(self, request: dict) -> dict:
        count = request["frameCount"]
        action = request["action"]
        source = CONTRACT["actions"].get(action)
        anchors = source["anchors"] if source else ["preparation", "first key pose", "main impact", "recovery"]
        description = request.get("description", "")
        frames = []
        for index in range(count):
            phase = index / count if request.get("loop", True) else index / max(1, count - 1)
            anchor = anchors[min(3, int(phase * 4))]
            frames.append({"index": index, "phase": round(phase, 4), "description": f"{description or action}: {anchor}, phase {index + 1}/{count}"})
        return {"action": action, "label": source["label"] if source else action, "loop": request["loop"], "frameCount": count, "anchors": anchors, "frames": frames}

    def create_action(self, character_id: str, request: dict, session: ProviderSession) -> dict:
        character = self.db.get_character(character_id)
        if character["status"] != "approved":
            raise ValueError("角色母版尚未审核入库")
        master = RUNTIME / "assets" / character_id / "masters" / f"{request['view']}.png"
        if not master.exists():
            raise ValueError("所选视角没有正式母版")
        job_id, timestamp = identifier("job"), now_iso()
        plan = self.action_plan(request)
        job = self.db.create_job({
            "id": job_id, "type": "action", "character_id": character_id, "status": "queued", "progress": 0,
            "message": "动作任务已排队", "payload": {**request, "plan": plan}, "outputs": {}, "error": "",
            "created_at": timestamp, "updated_at": timestamp,
        })
        self.executor.submit(self._run_action, job_id, session)
        return self.public_job(job)

    def _frame_prompt(self, character: dict, job: dict, frame: dict) -> str:
        payload = job["payload"]
        custom = f"Creator constraint: {payload.get('customPrompt')}. " if payload.get("customPrompt") else ""
        return (
            f"Redraw the exact same character as a high fidelity 2D animation frame. Identity: {character['description']}. "
            f"Action pose: {frame['description']}. Camera: {CONTRACT['views'][payload['view']]['prompt']}. {custom}"
            "Preserve face, hair, clothing construction, accessories, colors, body proportions and scale exactly. "
            "One full body only, feet aligned to a shared ground line, no text, no border, no shadow. "
            "Use flat vivid magenta #ff00d4 background. Native high-resolution square image, never pixel art."
        )

    def _run_action(self, job_id: str, session: ProviderSession) -> None:
        with self._lock(job_id):
            try:
                job = self.db.update_job(job_id, status="planning", progress=2, message="正在锁定动作关键帧")
                character = self.db.get_character(job["character_id"])
                payload, frames = job["payload"], job["payload"]["plan"]["frames"]
                count = payload["frameCount"]
                master = RUNTIME / "assets" / job["character_id"] / "masters" / f"{payload['view']}.png"
                anchor_indices = sorted({0, count // 4, count // 2, count * 3 // 4})
                order = anchor_indices + [index for index in range(count) if index not in anchor_indices]
                outputs = job["outputs"]
                generated: dict[int, Path] = {}
                self.db.update_job(job_id, status="generating", message="先生成四个动作锚点")
                for position, index in enumerate(order):
                    if self._cancelled(job_id):
                        return
                    references = [master]
                    if index not in anchor_indices and generated:
                        nearest = sorted(generated, key=lambda item: abs(item - index))[:2]
                        references.extend(generated[item] for item in nearest)
                    raw = self.provider.generate_image(
                        self._frame_prompt(character, job, frames[index]), references, session.api_key, session.model,
                        size=CONTRACT["frameSize"], seed_label=f"frame {index + 1}",
                    )
                    slot = f"frame:{index:03d}"
                    version = self._version(job_id, slot, raw, CONTRACT["frameSize"], "初始帧")
                    outputs[slot] = self._slot(slot, f"第 {index + 1} 帧", "frame", version, index)
                    generated[index] = Path(version["path"])
                    progress = 8 + round((position + 1) / count * 84)
                    self.db.update_job(job_id, outputs=outputs, progress=progress, message=f"已生成 {position + 1}/{count} 帧")
                self.db.update_job(job_id, status="processing", progress=94, message="正在执行序列连续性质检")
                paths = [Path(outputs[f"frame:{index:03d}"]["versions"][0]["path"]) for index in range(count)]
                quality = sequence_quality(paths, payload["loop"])
                payload["sequenceQuality"] = quality
                self.db.update_job(job_id, status="awaiting_review", progress=100, message="动作序列已完成，请逐帧审核", outputs=outputs, payload=payload)
            except (ProviderError, ImageQualityError, Exception) as error:
                self.db.update_job(job_id, status="failed", error=str(error), message=str(error))

    def select_version(self, job_id: str, slot: str, version_id: str) -> dict:
        with self._lock(job_id):
            job = self.db.get_job(job_id)
            output = job["outputs"].get(slot)
            if not output or not any(item["id"] == version_id for item in output["versions"]):
                raise KeyError(version_id)
            output["selectedVersionId"] = version_id
            output["review"] = {"decision": "pending", "note": ""}
            return self.public_job(self.db.update_job(job_id, outputs=job["outputs"], message="已切换候选版本，请重新审核"))

    def review(self, job_id: str, slot: str, decision: str, note: str) -> dict:
        with self._lock(job_id):
            job = self.db.get_job(job_id)
            if job["status"] != "awaiting_review":
                raise ValueError("任务当前不可审核")
            output = job["outputs"].get(slot)
            if not output:
                raise KeyError(slot)
            output["review"] = {"decision": decision, "note": note, "updatedAt": now_iso()}
            approved = sum(item["review"]["decision"] == "approved" for item in job["outputs"].values())
            total = len(job["outputs"])
            return self.public_job(self.db.update_job(job_id, outputs=job["outputs"], message=f"审核进度 {approved}/{total}"))

    def regenerate(self, job_id: str, slot: str, note: str, session: ProviderSession) -> dict:
        job = self.db.get_job(job_id)
        if slot not in job["outputs"]:
            raise KeyError(slot)
        self.executor.submit(self._run_regenerate, job_id, slot, note, session)
        return self.public_job(self.db.update_job(job_id, status="generating", message=f"正在重生 {job['outputs'][slot]['label']}"))

    def _run_regenerate(self, job_id: str, slot: str, note: str, session: ProviderSession) -> None:
        with self._lock(job_id):
            try:
                job = self.db.get_job(job_id)
                character = self.db.get_character(job["character_id"])
                output = job["outputs"][slot]
                if output["kind"] == "master":
                    view = slot.split(":", 1)[1]
                    refs = [Path(character["reference_path"])] if character["reference_path"] else []
                    prompt = self._prompt_master(character, view) + f" Revision request: {note}"
                    target = CONTRACT["masterSize"]
                else:
                    index = int(output["index"])
                    payload = job["payload"]
                    master = RUNTIME / "assets" / job["character_id"] / "masters" / f"{payload['view']}.png"
                    refs = [master]
                    for adjacent in (index - 1, index + 1):
                        adjacent_output = job["outputs"].get(f"frame:{adjacent:03d}")
                        if adjacent_output:
                            chosen = next(v for v in adjacent_output["versions"] if v["id"] == adjacent_output["selectedVersionId"])
                            refs.append(Path(chosen["path"]))
                    prompt = self._frame_prompt(character, job, payload["plan"]["frames"][index]) + f" Revision request: {note}"
                    target = CONTRACT["frameSize"]
                raw = self.provider.generate_image(prompt, refs, session.api_key, session.model, size=target, seed_label=f"revision {slot}")
                version = self._version(job_id, slot, raw, target, f"变体 {len(output['versions']) + 1}")
                output["versions"].append(version)
                output["selectedVersionId"] = version["id"]
                output["review"] = {"decision": "pending", "note": ""}
                self.db.update_job(job_id, status="awaiting_review", outputs=job["outputs"], message=f"{output['label']} 已生成新变体")
            except Exception as error:
                self.db.update_job(job_id, status="awaiting_review", error=str(error), message=f"重生失败：{error}")

    def promote(self, job_id: str) -> dict:
        with self._lock(job_id):
            job = self.db.get_job(job_id)
            if not job["outputs"] or any(item["review"]["decision"] != "approved" for item in job["outputs"].values()):
                raise ValueError("所有候选均审核通过后才能入库")
            self.db.update_job(job_id, status="promoting", message="正在原子写入正式资产")
            character_id = job["character_id"]
            asset_root = RUNTIME / "assets" / character_id
            if job["type"] == "character":
                target = asset_root / "masters"
                mapping = {slot: target / f"{slot.split(':')[1]}.png" for slot in job["outputs"]}
            else:
                payload = job["payload"]
                target = asset_root / "actions" / payload["view"] / payload["action"] / job_id
                mapping = {slot: target / f"frame-{int(output['index']) + 1:03d}.png" for slot, output in job["outputs"].items()}
            staging = target.parent / f".{target.name}-{identifier('staging')}"
            if staging.exists():
                shutil.rmtree(staging)
            staging.mkdir(parents=True, exist_ok=True)
            for slot, destination in mapping.items():
                output = job["outputs"][slot]
                selected = next(item for item in output["versions"] if item["id"] == output["selectedVersionId"])
                shutil.copy2(selected["path"], staging / destination.name)
            if target.exists():
                backup = RUNTIME / "backups" / character_id / f"{job_id}-{target.name}"
                backup.parent.mkdir(parents=True, exist_ok=True)
                if backup.exists():
                    shutil.rmtree(backup)
                shutil.move(target, backup)
            target.parent.mkdir(parents=True, exist_ok=True)
            staging.replace(target)
            if job["type"] == "character":
                self.db.update_character(character_id, status="approved")
            return self.public_job(self.db.update_job(job_id, status="approved", progress=100, message="正式资产已安全入库"))

    def cancel(self, job_id: str) -> dict:
        job = self.db.get_job(job_id)
        if job["status"] not in ACTIVE:
            raise ValueError("当前任务不可取消")
        return self.public_job(self.db.update_job(job_id, status="cancelled", message="任务已取消"))

    def retry(self, job_id: str, session: ProviderSession) -> dict:
        job = self.db.get_job(job_id)
        if job["status"] not in {"failed", "interrupted"}:
            raise ValueError("只有失败或中断任务可以重试")
        self.db.update_job(job_id, status="queued", progress=0, error="", message="任务已重新排队")
        runner = self._run_character if job["type"] == "character" else self._run_action
        self.executor.submit(runner, job_id, session)
        return self.public_job(self.db.get_job(job_id))

    def export_character(self, character_id: str) -> Path:
        character = self.db.get_character(character_id)
        if character["status"] != "approved":
            raise ValueError("角色尚未入库")
        output = RUNTIME / "exports" / f"{character_id}.zip"
        root = RUNTIME / "assets" / character_id
        metadata = self.character_public(character)
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in root.rglob("*.png"):
                archive.write(path, path.relative_to(root).as_posix())
            archive.writestr("character.json", json.dumps(metadata, ensure_ascii=False, indent=2))
        return output
