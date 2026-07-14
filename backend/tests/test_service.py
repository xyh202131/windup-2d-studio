import time

import app.service as service_module
from app.database import Database
from app.provider import QnAIGCProvider
from app.service import StudioService
from app.sessions import ProviderSession


def wait_for(service, job_id, statuses, timeout=20):
    started = time.time()
    while time.time() - started < timeout:
        job = service.db.get_job(job_id)
        if job["status"] in statuses:
            return job
        time.sleep(.05)
    raise AssertionError("job did not finish")


def test_demo_character_review_and_atomic_promotion(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime"
    for folder in ("uploads", "jobs", "assets", "backups", "exports"):
        (runtime / folder).mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(service_module, "RUNTIME", runtime)
    database = Database(runtime / "studio.sqlite3")
    database.initialize()
    service = StudioService(database, QnAIGCProvider("https://invalid.local"))
    session = ProviderSession(api_key="demo", model="windup-demo-image", verified=True)
    job = service.create_character({"name": "Demo", "description": "A detailed demo character", "style": "hand_drawn", "customStyle": ""}, "", session)
    completed = wait_for(service, job["id"], {"awaiting_review", "failed"})
    assert completed["status"] == "awaiting_review"
    assert len(completed["outputs"]) == 3
    for slot in completed["outputs"]:
        service.review(job["id"], slot, "approved", "")
    promoted = service.promote(job["id"])
    assert promoted["status"] == "approved"
    assert (runtime / "assets" / job["characterId"] / "masters" / "side.png").exists()

    action = service.create_action(job["characterId"], {
        "action": "idle", "description": "breathing idle", "view": "side", "frameCount": 8,
        "loop": True, "customPrompt": "keep the lantern steady",
    }, session)
    action_done = wait_for(service, action["id"], {"awaiting_review", "failed"}, timeout=30)
    assert action_done["status"] == "awaiting_review"
    assert len(action_done["outputs"]) == 8
    for slot in action_done["outputs"]:
        service.review(action["id"], slot, "approved", "")
    published_action = service.promote(action["id"])
    assert published_action["status"] == "approved"
    archive = service.export_character(job["characterId"])
    assert archive.exists()
