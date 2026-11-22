"""API flow test with a fake recogniser (no model download needed)."""

import io
import os
import tempfile
import time

import numpy as np
import pytest

os.environ["PB_DATA_DIR"] = tempfile.mkdtemp(prefix="pb_test_")
os.environ["PB_DATABASE_URL"] = ""

from fastapi.testclient import TestClient  # noqa: E402

from app.assessment import types as T  # noqa: E402
from app.bangla.normalize import normalize_word  # noqa: E402
from app.bangla.segment import segment_normalized  # noqa: E402
from app.main import app  # noqa: E402
from app.services import readings as svc  # noqa: E402
from app.speech.audio import SR  # noqa: E402


class FakeRecognizer:
    """Pretends the child read 'আজ আমার স্কুলের পথম দিন' etc."""

    model_id = "fake"

    def __init__(self, heard):
        self.heard = heard

    def logits(self, audio):
        return np.zeros((10, 3), dtype=np.float32)

    def log_probs(self, logits, temperature=1.0):
        return logits

    def greedy_decode(self, lp):
        out, t = [], 0.3
        for w in self.heard:
            n = normalize_word(w)
            u = segment_normalized(n)
            out.append(T.RecognizedWord(n, u, [0.95] * len(u), t, t + 0.4))
            t += 0.5
        return out

    def expected_evidence(self, lp, words):
        ev, t = [], 0.3
        for w in words:
            heard = w.norm in [normalize_word(h) for h in self.heard]
            ev.append(T.ExpectedEvidence(t, t + 0.4, [3.0 if heard else -4.0] * len(w.units)))
            t += 0.5
        return ev


def wav_bytes(seconds=3.0):
    import soundfile as sf

    t = np.arange(int(SR * seconds)) / SR
    x = (0.3 * np.sin(2 * np.pi * 220 * t) * (np.sin(2 * np.pi * 2 * t) > 0)).astype(np.float32)
    x += np.random.default_rng(0).normal(0, 0.001, len(x)).astype(np.float32)
    buf = io.BytesIO()
    sf.write(buf, x, SR, format="WAV")
    return buf.getvalue()


@pytest.fixture()
def client(monkeypatch):
    with TestClient(app) as c:
        r = c.post("/api/auth/login", json={"username": "teacher", "password": "teacher123", "role": "teacher"})
        assert r.status_code == 200, r.text
        yield c


@pytest.fixture()
def anon():
    with TestClient(app) as c:
        yield c


def wait_done(c, rid, timeout=20):
    for _ in range(int(timeout / 0.1)):
        r = c.get(f"/api/readings/{rid}").json()
        if r["status"] not in ("queued", "processing"):
            return r
        time.sleep(0.1)
    raise AssertionError("timeout")


def test_full_flow(client, monkeypatch):
    c = client
    passages = c.get("/api/passages").json()
    p04 = next(p for p in passages if p["code"] == "P04")
    words = p04["text"].replace("।", "").split()
    heard = [w if w != "প্রথম" else "পথম" for w in words]
    monkeypatch.setattr(svc, "get_ctc", lambda: FakeRecognizer(heard))

    cid = c.post("/api/classrooms", json={"name": "Test", "grade": 2}).json()["id"]
    assert c.post(f"/api/classrooms/{cid}/students/bulk", json={"count": 3}).json()["added"] == 3
    sid = c.get(f"/api/classrooms/{cid}").json()["students"][0]["id"]

    r = c.post("/api/readings", data={"student_id": sid, "passage_id": p04["id"]},
               files={"audio": ("a.wav", wav_bytes(), "audio/wav")})
    assert r.status_code == 202, r.text
    done = wait_done(c, r.json()["id"])
    assert done["status"] == "done", done
    misread = [m for m in done["marks"] if m["final_status"] == "misread"]
    assert [m["expected"] for m in misread] == ["প্রথম"]
    assert misread[0]["patterns"][0]["key"] == "phala:র"

    # teacher override recomputes metrics
    n = done["metrics"]["total_words"]
    assert done["score"] == round(10 * (n - 1) / n, 1)
    before = done["metrics"]["errors"]
    upd = c.patch(f"/api/readings/{done['id']}/marks/{misread[0]['index']}", json={"teacher_status": "correct"}).json()
    assert upd["metrics"]["errors"] == before - 1
    assert upd["score"] == 10.0

    fin = c.post(f"/api/readings/{done['id']}/finalize", json={"keep_audio": False}).json()
    assert fin["reviewed"] and not fin["has_audio"]

    st = c.get(f"/api/students/{sid}").json()
    assert st["readings"] == 1
    assert c.get(f"/api/classrooms/{cid}").json()["stats"]["readings"] == 1


def test_quality_rejects_silence(client, monkeypatch):
    c = client
    monkeypatch.setattr(svc, "get_ctc", lambda: FakeRecognizer([]))
    cid = c.post("/api/classrooms", json={"name": "Q", "grade": 1}).json()["id"]
    sid = c.post(f"/api/classrooms/{cid}/students", json={"code": "R1"}).json()["id"]
    import soundfile as sf

    buf = io.BytesIO()
    sf.write(buf, np.zeros(SR * 3, dtype=np.float32), SR, format="WAV")
    pid = c.get("/api/passages").json()[0]["id"]
    r = c.post("/api/readings", data={"student_id": sid, "passage_id": pid},
               files={"audio": ("s.wav", buf.getvalue(), "audio/wav")}).json()
    done = wait_done(c, r["id"])
    assert done["status"] == "rejected"
    assert "too_quiet" in done["quality"]["reasons"]


def test_engine_endpoints(client):
    d = client.post("/api/bangla/diff", json={"expected": "শিক্ষক", "heard": "শিকক"}).json()
    keys = [e["pattern"] for o in d["ops"] for e in o["errors"]]
    assert "conj:ক্ষ" in keys
    a = client.post("/api/bangla/analyze", json={"text": "কার্য"}).json()
    assert [u["text"] for u in a["words"][0]["units"]] == ["কা", "র্য"]


def test_login_required_and_roles(anon, monkeypatch):
    c = anon
    assert c.get("/api/health").status_code == 200
    assert c.get("/api/classrooms").status_code == 401
    assert c.post("/api/auth/login", json={"username": "teacher", "password": "nope"}).status_code == 401
    # wrong login tab
    assert c.post("/api/auth/login", json={"username": "c2r01", "password": "student123",
                                           "role": "teacher"}).status_code == 403
    me = c.post("/api/auth/login", json={"username": "c2r01", "password": "student123", "role": "student"}).json()
    assert me["role"] == "student" and me["student"]["grade"] == 2
    assert c.get("/api/classrooms").status_code == 403  # teacher-only
    passages = c.get("/api/my/passages").json()
    assert passages and all(p["grade"] == 2 for p in passages)
    assert {p["language"] for p in passages} == {"bn", "en"}

    p04 = next(p for p in passages if p["code"] == "P04")
    words = p04["text"].replace("।", "").split()
    monkeypatch.setattr(svc, "get_ctc", lambda: FakeRecognizer(words))
    r = c.post("/api/my/readings", data={"passage_id": p04["id"]}, files={"audio": ("a.wav", wav_bytes(), "audio/wav")})
    assert r.status_code == 202, r.text
    rid = r.json()["id"]
    for _ in range(200):
        d = c.get(f"/api/my/readings/{rid}").json()
        if d["status"] not in ("queued", "processing"):
            break
        time.sleep(0.1)
    assert d["status"] == "done" and d["score"] == 10.0
    ov = c.get("/api/my/overview").json()
    assert ov["history"][0]["score"] == 10.0
    # another grade's passage is not available
    from app.db import SessionLocal
    from app.models import Passage

    with SessionLocal() as db:
        other = db.query(Passage).filter(Passage.code == "P01").one().id  # grade 1
    assert c.get(f"/api/my/passages/{other}").status_code == 404
    c.post("/api/auth/logout")
    assert c.get("/api/auth/me").status_code == 401


def test_teacher_sets_student_login(client):
    c = client
    cid = c.post("/api/classrooms", json={"name": "Acc", "grade": 3}).json()["id"]
    sid = c.post(f"/api/classrooms/{cid}/students", json={"code": "R9"}).json()["id"]
    card = c.put(f"/api/students/{sid}/account", json={"username": "Rina9", "password": "abcd"}).json()
    assert card["username"] == "rina9"
    assert c.put(f"/api/students/{sid}/account", json={"username": "c1r01", "password": "abcd"}).status_code == 409
    with TestClient(app) as s:
        assert s.post("/api/auth/login", json={"username": "rina9", "password": "abcd"}).json()["role"] == "student"


def test_english_marking():
    from app.assessment.english import assess_english, english_words

    pw = english_words("I have a red ball. The ball is big.")
    heard = [("I", 0.1, 0.2, 0.9), ("have", 0.3, 0.5, 0.9), ("a", 0.6, 0.7, 0.9), ("bed", 0.8, 1.0, 0.95),
             ("ball,", 1.1, 1.3, 0.9), ("the", 1.4, 1.5, 0.9)]
    marks = assess_english(pw, heard, T.Thresholds())
    assert [m.status for m in marks] == ["correct", "correct", "correct", "misread", "correct", "correct",
                                         "not_reached", "not_reached", "not_reached"]
    assert marks[3].heard == "bed"
    from app.assessment.metrics import compute_metrics

    assert compute_metrics([m.to_dict() for m in marks]).score == round(10 * 5 / 9, 1)
