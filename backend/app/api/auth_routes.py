"""Public, login and student-only routes.

Students can only see active passages of their own class grade, submit their
own readings and see their own results. Everything else is teacher-only (see routes.py).

Child-safe results: a child sees the mark out of 10 and the words to practise only
after the teacher has reviewed the reading. Until then the AI's marks are suggestions
that may be wrong, so they are withheld (enforced here, not only in the UI).
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..assessment.metrics import score_of
from ..bangla.patterns import pattern_label
from ..auth import (COOKIE, create_session, current_user, end_other_sessions, end_session, hash_password,
                    require_student, user_out, verify_password)
from ..config import get_settings
from ..db import get_db
from ..models import Passage, Reading, User
from ..schemas import LoginIn, PasswordIn
from ..seed.demo import is_demo_login
from ..services import analytics
from .routes import accept_upload
from .serializers import passage_out, reading_out

router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict:
    # demo_mode lets the login and recording screens warn: public test logins, no real children
    return {"ok": True, "demo_mode": get_settings().seed_demo}


# ------------------------------------------------------------------ auth
_demo_failures: dict[tuple[str, str], tuple[int, datetime | None]] = {}  # demo server only, in memory
@router.post("/auth/login")
def login(body: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)) -> dict:
    user = db.scalar(select(User).where(User.username == body.username.strip().lower()))
    if user is None:
        raise HTTPException(401, "Wrong username or password")
    s = get_settings()
    now = datetime.now(timezone.utc)
    if s.seed_demo:
        # public demo: lock per (login, client address), so a stranger typing wrong passwords for
        # "teacher" cannot lock every judge out of the shared demo login
        key = (user.username, request.client.host if request.client else "?")
        fails, locked = _demo_failures.get(key, (0, None))
    else:
        # real installation: the whole account locks, which also stops guessing from many addresses
        key, fails, locked = None, user.failed_logins or 0, user.locked_until
        if locked is not None and locked.tzinfo is None:
            locked = locked.replace(tzinfo=timezone.utc)  # SQLite returns naive UTC datetimes
    if locked is not None and locked > now:
        mins = max(1, round((locked - now).total_seconds() / 60))
        raise HTTPException(429, f"Too many wrong passwords. Try again in {mins} minute{'s' if mins > 1 else ''}.")
    if not verify_password(body.password, user.password_hash):
        fails += 1
        locked = now + timedelta(minutes=s.lockout_minutes) if fails >= s.max_failed_logins else None
        if locked:
            fails = 0
        if key is not None:
            _demo_failures[key] = (fails, locked)
        else:
            user.failed_logins, user.locked_until = fails, locked
            db.commit()
        raise HTTPException(401, "Wrong username or password")
    if key is not None:
        _demo_failures.pop(key, None)
    elif user.failed_logins or user.locked_until:
        user.failed_logins, user.locked_until = 0, None
        db.commit()
    if body.role and body.role != user.role and not (body.role == "teacher" and user.role in ("admin", "district")):
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
def change_password(body: PasswordIn, request: Request, user: User = Depends(current_user),
                    db: Session = Depends(get_db)) -> None:
    if get_settings().seed_demo and is_demo_login(user.username):
        raise HTTPException(403, "This is a shared demo login, so its password stays as published. "
                                 "On a real installation (PB_SEED_DEMO=false) you can change it here.")
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(403, "The current password is wrong")
    user.password_hash = hash_password(body.new_password)
    user.failed_logins, user.locked_until = 0, None
    end_other_sessions(db, user.id, keep_token=request.cookies.get(COOKIE))  # other devices must log in again
    db.commit()


# ---------------------------------------------------------- student area
def _own_passage(db: Session, user: User, pid: int) -> Passage:
    p = db.get(Passage, pid)
    if p is None or not p.active or p.grade != user.student.classroom.grade:
        raise HTTPException(404, "This passage is not available for your class")
    return p


def child_summary(r: Reading) -> dict:
    """A reading as the child sees it. Before teacher review the child sees the AI's provisional
    result (flagged ai_provisional); the reading still waits in the teacher's review queue."""
    d = analytics.reading_summary(r)
    d["pending_review"] = r.status == "done" and not r.reviewed
    d["ai_provisional"] = d["pending_review"]
    return d


@router.get("/my/overview")
def my_overview(user: User = Depends(require_student)) -> dict:
    st = user.student
    card = analytics.student_card(st)
    tests = [child_summary(r) for r in reversed(st.readings) if r.status != "failed"]
    checked = [t for t in tests if t["status"] == "done" and not t["pending_review"]]
    latest = card["latest"]
    return {
        **card,
        "latest": child_summary(next(r for r in st.readings if r.id == latest["id"])) if latest else None,
        "mean_score": analytics._mean([t["score"] for t in checked]),
        "candidate_patterns": [p for p in analytics.student_patterns(st, reviewed_only=True) if p["candidate"]][:5],
        "classroom": {"id": st.classroom.id, "name": st.classroom.name, "grade": st.classroom.grade},
        "history": tests,
        "best_score": max((t["score"] for t in checked if t["score"] is not None), default=None),
        "tests_done": sum(1 for t in tests if t["status"] == "done"),
        "tests_checked": len(checked),
        "words_read_correctly": sum(t["correct"] or 0 for t in checked),
    }


@router.get("/my/practice")
def my_practice(user: User = Depends(require_student)) -> list[dict]:
    """Words this student misread or skipped, newest first, one entry per word.

    Each entry points at the reading and the time span where the child said it, so the
    page can play the child's own attempt next to the model pronunciation."""
    words: dict[str, dict] = {}
    for r in sorted(user.student.readings, key=lambda x: x.created_at, reverse=True):
        if r.status != "done" or not r.reviewed:  # only teacher-checked words
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
    attempted = {r.passage_id for r in user.student.readings if r.status == "done"}
    for r in user.student.readings:
        if r.status == "done" and r.reviewed:  # marks count once the teacher has checked them
            s = score_of(r.metrics)
            prev = done.get(r.passage_id)
            done[r.passage_id] = s if prev is None or (s is not None and s > prev) else prev
    out = []
    for p in db.scalars(q):
        d = passage_out(p)
        d["attempted"] = p.id in attempted
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
    r = await accept_upload(db, user.student, p, audio, uploader_id=user.id)
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
    for k in ("comparison", "comparison_status", "thresholds", "transcript", "review_stats"):  # teacher tools only
        d[k] = None
    if d.get("error"):
        d["error"] = "Something went wrong while checking this reading. Please ask your teacher."
    d["pending_review"] = r.status == "done" and not r.reviewed
    d["ai_provisional"] = d["pending_review"]  # AI result shown now; teacher review can still change it
    return d
