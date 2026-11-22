"""Child safety, login lockout, assignments, export, demo reset, audio retention, word check."""

import time
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from tests.test_api import FakeRecognizer, wav_bytes, wait_done  # noqa: F401  (sets up the temp data dir)
from tests.test_api import anon, client  # noqa: F401  (fixtures)
from app.main import app
from app.services import readings as svc


def _student_login(username="c3r02"):
    s = TestClient(app)
    s.__enter__()
    assert s.post("/api/auth/login", json={"username": username, "password": "student123"}).status_code == 200
    return s


def test_lockout_after_wrong_passwords(anon):  # noqa: F811
    c = anon
    for _ in range(5):
        assert c.post("/api/auth/login", json={"username": "c5r09", "password": "wrong"}).status_code == 401
    r = c.post("/api/auth/login", json={"username": "c5r09", "password": "student123"})
    assert r.status_code == 429 and "Try again" in r.json()["detail"]
    from app.db import SessionLocal
    from app.models import User

    with SessionLocal() as db:  # unlock so other tests can use the account
        u = db.query(User).filter(User.username == "c5r09").one()
        u.locked_until = None
        db.commit()
    assert c.post("/api/auth/login", json={"username": "c5r09", "password": "student123"}).status_code == 200


def test_assignments_and_export(client, monkeypatch):  # noqa: F811
    c = client
    cls = next(x for x in c.get("/api/classrooms").json() if x["name"] == "Class 3")
    detail = c.get(f"/api/classrooms/{cls['id']}").json()
    sid = next(s["id"] for s in detail["students"] if s["code"] == "Roll 02")
    out = c.post("/api/assignments", json={"student_ids": [sid], "pattern_key": "phala:র"}).json()
    assert out["created"] == 1 and out["words"] and out["passage"]
    s = _student_login("c3r02")
    mine = s.get("/api/my/assignments").json()
    assert mine and not mine[0]["done"] and mine[0]["words"]
    # reading the assigned passage completes it
    pid = mine[0]["passage"]["id"]
    monkeypatch.setattr(svc, "get_ctc", lambda: FakeRecognizer([]))
    assert s.post("/api/my/readings", data={"passage_id": pid},
                  files={"audio": ("a.wav", wav_bytes(), "audio/wav")}).status_code == 202
    assert s.get("/api/my/assignments").json()[0]["done"]
    s.__exit__(None, None, None)
    csv_text = c.get(f"/api/classrooms/{cls['id']}/export.csv").content.decode("utf-8-sig")
    assert csv_text.startswith("class,roll_code") and "Roll 02" in csv_text


def test_demo_reset_keeps_simulated_history(client, monkeypatch):  # noqa: F811
    c = client
    before = sum(x["stats"]["simulated"] for x in c.get("/api/classrooms").json())
    r = c.post("/api/demo/reset").json()
    assert "readings_deleted" in r
    after = c.get("/api/classrooms").json()
    assert sum(x["stats"]["simulated"] for x in after) == before
    assert sum(x["stats"]["readings"] for x in after) == before  # only simulated readings remain


def test_old_audio_is_purged(client, monkeypatch):  # noqa: F811
    c = client
    from app.config import get_settings
    from app.db import SessionLocal
    from app.models import Reading

    cls = c.get("/api/classrooms").json()[0]
    sid = c.get(f"/api/classrooms/{cls['id']}").json()["students"][0]["id"]
    pid = next(p["id"] for p in c.get("/api/passages").json() if p["language"] == "bn")
    monkeypatch.setattr(svc, "get_ctc", lambda: FakeRecognizer([]))
    rid = c.post("/api/readings", data={"student_id": sid, "passage_id": pid},
                 files={"audio": ("a.wav", wav_bytes(), "audio/wav")}).json()["id"]
    wait_done(c, rid)
    with SessionLocal() as db:
        db.get(Reading, rid).created_at = datetime.now(timezone.utc) - timedelta(days=30)
        db.commit()
    monkeypatch.setattr(get_settings(), "audio_retention_days", 14)
    assert svc.purge_old_audio() >= 1
    assert not c.get(f"/api/readings/{rid}").json()["has_audio"]


def test_word_check(monkeypatch):
    from app.speech import registry

    s = _student_login("c3r03")
    monkeypatch.setattr(registry, "get_ctc", lambda: FakeRecognizer(["প্রথম"]))
    r = s.post("/api/my/practice/check", data={"word": "প্রথম"}, files={"audio": ("w.wav", wav_bytes(1.2), "audio/wav")})
    assert r.status_code == 200 and r.json()["result"] == "right", r.text
    monkeypatch.setattr(registry, "get_ctc", lambda: FakeRecognizer(["পথম"]))
    r = s.post("/api/my/practice/check", data={"word": "প্রথম"}, files={"audio": ("w.wav", wav_bytes(1.2), "audio/wav")})
    assert r.json()["result"] in ("practise", "again")
    s.__exit__(None, None, None)
