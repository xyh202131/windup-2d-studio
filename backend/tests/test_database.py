from app.database import Database, now_iso


def test_active_jobs_are_interrupted_on_restart(tmp_path):
    database = Database(tmp_path / "studio.sqlite3")
    database.initialize()
    timestamp = now_iso()
    database.create_character({
        "id": "char_1", "name": "Test", "description": "A detailed test character", "style": "hand_drawn",
        "custom_style": "", "reference_path": "", "status": "draft", "created_at": timestamp, "updated_at": timestamp,
    })
    database.create_job({
        "id": "job_1", "type": "character", "character_id": "char_1", "status": "generating", "progress": 40,
        "message": "working", "payload": {}, "outputs": {}, "error": "", "created_at": timestamp, "updated_at": timestamp,
    })
    database.initialize()
    assert database.get_job("job_1")["status"] == "interrupted"

