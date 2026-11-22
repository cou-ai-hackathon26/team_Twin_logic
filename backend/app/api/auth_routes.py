"""Public, login and student-only routes.

Students can only see active passages of their own class grade, submit their
own readings and see their own results (marks out of 10). Everything else is
teacher-only (see routes.py).
"""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..assessment.metrics import score_of
from ..bangla.patterns import pattern_label
from ..auth import (COOKIE, create_session, current_user, end_session, hash_password, require_student, user_out,
                    verify_password)
from ..config import get_settings
from ..db import get_db
from ..models import Passage, Reading, User
from ..schemas import LoginIn, PasswordIn
from ..services import analytics
from .routes import accept_upload
from .serializers import passage_out, reading_out

router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict:
    return {"ok": True}


# ------------------------------------------------------------------ auth
@router.post("/auth/login")
def login(body: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)) -> dict:
    user = db.scalar(select(User).where(User.username == body.username.strip().lower()))
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Wrong username or password")
    if body.role and body.role != user.role:
        raise HTTPException(403, f"This is a {user.role} account. Use the {user.role.capitalize()} login.")
    token, max_age = create_session(db, user)
    samesite = get_settings().cookie_samesite.lower()
    secure = request.url.scheme == "https" or samesite == "none"
    response.set_cookie(COOKIE, token, max_age=max_age, httponly=True, samesite=samesite,
                        secure=secure, path="/")
    return user_out(user)


@router.post("/auth/logout", status_code=204)
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> None:
    end_session(db, request)
    response.delete_cookie(COOKIE, path="/")


@router.get("/auth/me")
def me(user: User = Depends(current_user)) -> dict:
    return user_out(user)


@router.post("/auth/password", status_code=204)
def change_password(body: PasswordIn, user: User = Depends(current_user), db: Session = Depends(get_db)) -> None:
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(403, "The current password is wrong")
    user.password_hash = hash_password(body.new_password)
    db.commit()


# ---------------------------------------------------------- student area
def _own_passage(db: Session, user: User, pid: int) -> Passage:
    p = db.get(Passage, pid)
    if p is None or not p.active or p.grade != user.student.classroom.grade:
        raise HTTPException(404, "This passage is not available for your class")
    return p


@router.get("/my/overview")
def my_overview(user: User = Depends(require_student)) -> dict:
    st = user.student
    card = analytics.student_card(st)
    tests = [analytics.reading_summary(r) for r in reversed(st.readings) if r.status != "failed"]
    return {
        **card,
        "classroom": {"id": st.classroom.id, "name": st.classroom.name, "grade": st.classroom.grade},
        "history": tests,
        "best_score": max((t["score"] for t in tests if t["score"] is not None), default=None),
    }


@router.get("/my/practice")
def my_practice(user: User = Depends(require_student)) -> list[dict]:
    """Words this student misread or skipped, newest first, one entry per word.

    Each entry points at the reading and the time span where the child said it, so the
    page can play the child's own attempt next to the model pronunciation."""
    words: dict[str, dict] = {}
    for r in sorted(user.student.readings, key=lambda x: x.created_at, reverse=True):
        if r.status != "done":
            continue
        has_audio = bool(r.audio_path and os.path.exists(r.audio_path))
        for m in r.marks:
            st = m.final_status
            if st not in ("misread", "skipped"):
                continue
            key = m.expected or m.display
            e = words.get(key)
            if e is None:
                words[key] = {
                    "word": m.display.strip("।,.!?;:\"'“”‘’"), "expected": m.expected, "heard": m.heard,
                    "status": st, "count": 1, "language": r.passage.language if r.passage else "bn",
                    "reading_id": r.id, "passage_title": r.passage.title if r.passage else "",
                    "date": r.created_at.isoformat(),
                    "clip": {"start": m.start, "end": m.end} if has_audio and m.start is not None and m.end is not None else None,
                    "patterns": [pattern_label(k) for k in (m.error_patterns or [])],
                }
            else:
                e["count"] += 1
    return sorted(words.values(), key=lambda e: (e["count"], e["date"]), reverse=True)[:60]


@router.get("/my/passages")
def my_passages(user: User = Depends(require_student), db: Session = Depends(get_db)) -> list[dict]:
    grade = user.student.classroom.grade
    q = (select(Passage).where(Passage.active.is_(True), Passage.grade == grade)
         .order_by(Passage.language, Passage.code, Passage.id))
    done: dict[int, float | None] = {}
    for r in user.student.readings:
        if r.status == "done":
            s = score_of(r.metrics)
            prev = done.get(r.passage_id)
            done[r.passage_id] = s if prev is None or (s is not None and s > prev) else prev
    out = []
    for p in db.scalars(q):
        d = passage_out(p)
        d["attempted"] = p.id in done
        d["best_score"] = done.get(p.id)
        out.append(d)
    return out


@router.get("/my/passages/{pid}")
def my_passage(pid: int, user: User = Depends(require_student), db: Session = Depends(get_db)) -> dict:
    return passage_out(_own_passage(db, user, pid))


@router.post("/my/readings", status_code=202)
async def my_create_reading(passage_id: int = Form(...), audio: UploadFile = File(...),
                            user: User = Depends(require_student), db: Session = Depends(get_db)) -> dict:
    p = _own_passage(db, user, passage_id)
    r = await accept_upload(db, user.student, p, audio)
    return reading_out(r, with_marks=False)


def _own_reading(db: Session, user: User, rid: int) -> Reading:
    r = db.get(Reading, rid)
    if r is None or r.student_id != user.student.id:
        raise HTTPException(404, "Reading not found")
    return r


@router.get("/my/readings/{rid}/audio")
def my_reading_audio(rid: int, user: User = Depends(require_student), db: Session = Depends(get_db)):
    """A student can listen to their own recording."""
    r = _own_reading(db, user, rid)
    if not r.audio_path or not os.path.exists(r.audio_path):
        raise HTTPException(404, "Audio is not stored for this reading")
    return FileResponse(r.audio_path, media_type="audio/wav")


@router.get("/my/readings/{rid}")
def my_reading(rid: int, user: User = Depends(require_student), db: Session = Depends(get_db)) -> dict:
    r = _own_reading(db, user, rid)
    d = reading_out(r)
    for k in ("comparison", "comparison_status", "thresholds"):  # teacher tools only
        d[k] = None
    return d
