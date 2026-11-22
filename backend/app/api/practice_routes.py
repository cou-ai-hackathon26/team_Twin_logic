"""Practice assignments, class export and demo reset.

Teachers assign practice to one child, a weak-pattern group or a whole class; each child
sees their own assignments on their home page. Assigning a weak pattern picks practice
words and a passage that contain that written unit, near the class grade.
"""

from __future__ import annotations

import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..assessment.metrics import score_of
from ..auth import require_student, require_teacher
from ..bangla.patterns import pattern_label
from ..config import get_settings
from ..db import get_db
from ..models import SIMULATED_MODEL_ID, Assignment, Classroom, Passage, Reading, Student, User, iso
from ..services import analytics
from ..services import readings as reading_svc

teacher = APIRouter(prefix="/api", dependencies=[Depends(require_teacher)])
student = APIRouter(prefix="/api")


class AssignIn(BaseModel):
    student_ids: list[int] = Field(min_length=1, max_length=200)
    passage_id: int | None = None
    pattern_key: str | None = Field(default=None, max_length=40)
    words: list[str] = Field(default_factory=list, max_length=30)
    note: str | None = Field(default=None, max_length=300)


def pattern_practice(db: Session, key: str, grade: int) -> tuple[list[str], Passage | None]:
    """Practice words containing a written unit, and the passage near this grade that practises it most."""
    passages = db.scalars(select(Passage).where(Passage.active.is_(True), Passage.language == "bn")).all()
    words: dict[str, int] = {}
    best: tuple[float, Passage] | None = None
    for ps in passages:
        occ = 0
        for w, keys in analytics._passage_opportunities(ps.text):
            if key in keys:
                occ += 1
                words[w] = words.get(w, 0) + 1
        if occ:
            score = min(occ, 6) - 3.0 * abs(ps.grade - grade)
            if best is None or score > best[0]:
                best = (score, ps)
    ranked = sorted(words, key=lambda w: (len(w), -words[w]))[:8]
    return ranked, best[1] if best else None


def assignment_out(a: Assignment) -> dict:
    return {
        "id": a.id, "student_id": a.student_id,
        "student_code": a.student.code if a.student else None,
        "passage": {"id": a.passage.id, "title": a.passage.title, "language": a.passage.language}
        if a.passage else None,
        "pattern": pattern_label(a.pattern_key) if a.pattern_key else None,
        "words": a.words or [], "note": a.note,
        "created_at": iso(a.created_at), "done_at": iso(a.done_at), "done": a.done_at is not None,
    }


# ------------------------------------------------------------------ teacher
@teacher.post("/assignments", status_code=201)
def create_assignments(body: AssignIn, db: Session = Depends(get_db)) -> dict:
    students = db.scalars(select(Student).where(Student.id.in_(body.student_ids))).all()
    if len(students) != len(set(body.student_ids)):
        raise HTTPException(404, "Student not found")
    passage = db.get(Passage, body.passage_id) if body.passage_id else None
    if body.passage_id and (passage is None or not passage.active):
        raise HTTPException(404, "Passage not found")
    words = [w.strip() for w in body.words if w.strip()]
    if body.pattern_key and not words:
        grade = students[0].classroom.grade if students[0].classroom else 1
        words, suggested = pattern_practice(db, body.pattern_key, grade)
        passage = passage or suggested
    if passage is None and not words:
        raise HTTPException(422, "Choose a passage, a weak pattern or some words")
    for st in students:
        db.add(Assignment(student_id=st.id, passage_id=passage.id if passage else None,
                          pattern_key=body.pattern_key, words=words, note=(body.note or "").strip() or None))
    db.commit()
    return {"created": len(students), "passage": passage.title if passage else None, "words": words}


@teacher.get("/students/{sid}/assignments")
def student_assignments(sid: int, db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(Assignment).where(Assignment.student_id == sid)
                      .order_by(Assignment.created_at.desc()).limit(50))
    return [assignment_out(a) for a in rows]


@teacher.get("/classrooms/{cid}/assignments")
def class_assignments(cid: int, db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(Assignment).join(Student).where(Student.classroom_id == cid)
                      .order_by(Assignment.created_at.desc()).limit(300))
    return [assignment_out(a) for a in rows]


@teacher.delete("/assignments/{aid}", status_code=204)
def delete_assignment(aid: int, db: Session = Depends(get_db)) -> None:
    a = db.get(Assignment, aid)
    if a is None:
        raise HTTPException(404, "Assignment not found")
    db.delete(a)
    db.commit()


@teacher.get("/classrooms/{cid}/export.csv")
def export_class(cid: int, db: Session = Depends(get_db)) -> StreamingResponse:
    """Every reading of the class as CSV (opens in Excel), for school records."""
    c = db.get(Classroom, cid)
    if c is None:
        raise HTTPException(404, "Class not found")
    buf = io.StringIO()
    buf.write("﻿")  # BOM so Excel shows Bangla correctly
    w = csv.writer(buf)
    w.writerow(["class", "roll_code", "nickname", "date", "passage", "language", "status", "teacher_reviewed",
                "simulated_demo_data", "mark_out_of_10", "words_correct", "words_total", "wcpm", "accuracy",
                "errors", "unsure", "weak_patterns"])
    for st in sorted(c.students, key=lambda s: s.code):
        weak = "; ".join(p.get("bn") or p["key"] for p in analytics.student_patterns(st) if p["candidate"])
        for r in st.readings:
            m = r.metrics or {}
            w.writerow([c.name, st.code, st.nickname or "", iso(r.created_at), r.passage.title if r.passage else "",
                        r.passage.language if r.passage else "", r.status, "yes" if r.reviewed else "no",
                        "yes" if r.model_id == SIMULATED_MODEL_ID else "no", score_of(m), m.get("correct"),
                        m.get("total_words"), m.get("wcpm"), m.get("accuracy"), m.get("errors"), m.get("unsure"),
                        weak])
    name = f"porabondhu_{c.name.replace(' ', '_')}_{datetime.now():%Y%m%d}.csv"
    return StreamingResponse(iter([buf.getvalue().encode("utf-8")]), media_type="text/csv; charset=utf-8",
                             headers={"Content-Disposition": f'attachment; filename="{name}"'})


@teacher.post("/demo/reset")
def demo_reset(db: Session = Depends(get_db)) -> dict:
    """Demo only: delete every real recording and assignment made on this demo server.

    The simulated history stays, so the next visitor (e.g. the next judge) starts clean and
    never sees someone else's voice. Disabled when PB_SEED_DEMO=false (a real school)."""
    if not get_settings().seed_demo:
        raise HTTPException(403, "Demo reset is only available on the demo server")
    readings = db.scalars(select(Reading).where(Reading.model_id.is_distinct_from(SIMULATED_MODEL_ID))).all()
    for r in readings:
        reading_svc.delete_audio(r)
        db.delete(r)
    n_assign = 0
    for a in db.scalars(select(Assignment)):
        db.delete(a)
        n_assign += 1
    db.commit()
    return {"readings_deleted": len(readings), "assignments_deleted": n_assign}


# ------------------------------------------------------------------ student
@student.get("/my/assignments")
def my_assignments(user: User = Depends(require_student), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(Assignment).where(Assignment.student_id == user.student.id)
                      .order_by(Assignment.done_at.is_not(None), Assignment.created_at.desc()).limit(20))
    return [assignment_out(a) for a in rows]


@student.post("/my/assignments/{aid}/done")
def my_assignment_done(aid: int, user: User = Depends(require_student), db: Session = Depends(get_db)) -> dict:
    a = db.get(Assignment, aid)
    if a is None or a.student_id != user.student.id:
        raise HTTPException(404, "Assignment not found")
    a.done_at = a.done_at or datetime.now(timezone.utc)
    db.commit()
    return assignment_out(a)


# ------------------------------------------------------------- word check
_check_lock = __import__("threading").Lock()


@student.post("/my/practice/check")
async def my_practice_check(word: str = Form(..., max_length=60), audio: UploadFile = File(...),
                            user: User = Depends(require_student)) -> dict:
    """The child says one practice word; the same speech model checks it at once.

    Uses the normal two-signal marking on a one-word "passage", so an unclear recording
    comes back as "unsure" (try again), never as a wrong answer."""
    import numpy as np

    from ..config import load_thresholds
    from ..pipeline import run_porabondhu
    from ..speech.audio import load_audio_bytes
    from ..speech.registry import get_ctc

    word = word.strip()
    if not word or not any("ঀ" <= ch <= "৿" for ch in word):
        raise HTTPException(422, "Word check works for Bangla words")
    data = await audio.read()
    if not data or len(data) > 2_000_000:
        raise HTTPException(422, "Record the word again (1-5 seconds)")
    try:
        x = load_audio_bytes(data)
    except ValueError as e:
        raise HTTPException(422, str(e)) from None
    if len(x) < 0.3 * 16000 or float(np.sqrt(np.mean(x ** 2))) < 0.005:
        return {"word": word, "result": "again", "heard": "", "message_bn": "শোনা যায়নি, আরেকবার জোরে বলো",
                "message_en": "I could not hear you. Say it again, a bit louder."}
    def _run():
        with _check_lock:  # one check at a time on the CPU
            return run_porabondhu(x, word, get_ctc(), load_thresholds(), skip_quality=True)

    from starlette.concurrency import run_in_threadpool

    res = await run_in_threadpool(_run)
    m = res.marks[0] if res.marks else None
    status = m.status if m else "unsure"
    result = {"correct": "right", "misread": "practise", "skipped": "again"}.get(status, "again")
    msg = {
        "right": ("খুব ভালো! ঠিক বলেছ", "Well done! That was right."),
        "practise": ("প্রায় হয়েছে, শুনে আবার বলো", "Nearly! Listen to it and try again."),
        "again": ("পরিষ্কার শোনা যায়নি, আরেকবার বলো", "Not clear. Say it once more."),
    }[result]
    return {"word": word, "result": result, "heard": m.heard if m else "", "message_bn": msg[0], "message_en": msg[1]}
