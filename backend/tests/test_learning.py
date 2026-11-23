"""Learning from teacher reviews: replayable decisions, learned pronunciations, threshold updates."""

import time

from tests.test_api import FakeRecognizer, client, wait_done, wav_bytes  # noqa: F401
from app.assessment import types as T
from app.models import WordMark
from app.services import learning
from app.services import readings as svc


def _mark(raw, gop, err_free, teacher, status=None):
    m = WordMark(index=0, display="x", expected="x", heard="y", status=status or T.UNSURE, raw_status=raw,
                 teacher_status=teacher, gop=gop, err_free=err_free, free_conf=err_free)
    return m


def test_replay_follows_the_marking_rules():
    th = T.Thresholds(free_high=0.5, gop_high=1.0, gop_low=-3.0)
    assert learning.replay(_mark(T.MISREAD, 2.0, 0.9, None), th) == T.CORRECT
    assert learning.replay(_mark(T.MISREAD, -4.0, 0.9, None), th) == T.MISREAD
    assert learning.replay(_mark(T.MISREAD, -1.0, 0.9, None), th) == T.UNSURE


def test_search_moves_thresholds_towards_the_teachers():
    # teachers call words with gop around -1.5 misread, but the current gop_low (-3) leaves them unsure
    marks = [_mark(T.MISREAD, -1.5, 0.9, T.MISREAD) for _ in range(30)]
    marks += [_mark(T.MISREAD, 2.0, 0.9, T.CORRECT) for _ in range(200)]
    cur = T.Thresholds(free_high=0.5, gop_high=1.0, gop_low=-3.0)
    best, s = learning.search(marks, cur)
    assert best.gop_low >= -1.5 and s["recall"] == 1.0 and s["false_alarm"] == 0.0
    assert learning.score(marks, cur)["recall"] == 0.0


def test_teacher_corrections_teach_an_accepted_pronunciation(client, monkeypatch):  # noqa: F811
    c = client
    from app.db import SessionLocal
    from app.models import AcceptedVariant

    c.post("/api/demo/reset")  # start clean: no readings or learned variants from other tests
    with SessionLocal() as db:
        db.query(AcceptedVariant).filter(AcceptedVariant.word == "প্রথম").delete()
        db.commit()
    cls = next(x for x in c.get("/api/classrooms").json() if x["name"] == "Class 2")
    students = c.get(f"/api/classrooms/{cls['id']}").json()["students"][:3]
    p04 = next(p for p in c.get("/api/passages").json() if p["code"] == "P04")
    words = p04["text"].replace("।", "").split()
    heard = ["পথম" if w == "প্রথম" else w for w in words]
    monkeypatch.setattr(svc, "get_ctc", lambda: FakeRecognizer(heard))
    for st in students:
        rid = c.post("/api/readings", data={"student_id": st["id"], "passage_id": p04["id"]},
                     files={"audio": ("a.wav", wav_bytes(), "audio/wav")}).json()["id"]
        r = wait_done(c, rid)
        m = next(m for m in r["marks"] if m["expected"] == "প্রথম")
        assert m["status"] == "misread"
        c.patch(f"/api/readings/{rid}/marks/{m['index']}", json={"teacher_status": "correct"})
        c.post(f"/api/readings/{rid}/finalize", json={"keep_audio": False})
    time.sleep(0.5)  # finalize also starts learning in the background
    out = c.post("/api/learning/run").json()
    learned = c.get("/api/learning").json()["learned_variants"]
    assert any(v["word"] == "প্রথম" and v["variant"] == "পথম" for v in learned), (out, learned)
    # the next reading with the same pronunciation is no longer flagged
    rid = c.post("/api/readings", data={"student_id": students[0]["id"], "passage_id": p04["id"]},
                 files={"audio": ("a.wav", wav_bytes(), "audio/wav")}).json()["id"]
    m = next(m for m in wait_done(c, rid)["marks"] if m["expected"] == "প্রথম")
    assert m["status"] == "correct"
    # demo reset forgets what visitors taught and keeps the published thresholds
    c.post("/api/demo/reset")
    after = c.get("/api/learning").json()
    assert after["learned_variants"] == [] and not after["can_undo"]
