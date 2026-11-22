"""HTTP API. All routes are mounted under /api."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..assessment.english import english_words
from ..assessment.marking import passage_words
from ..auth import STUDENT, end_other_sessions, hash_password, require_teacher
from ..bangla.normalize import normalize_word
from ..bangla.patterns import pattern_label
from ..bangla.segment import segment_normalized
from ..config import get_settings, load_thresholds
from ..db import get_db
from ..models import AcceptedVariant, Assignment, Classroom, Passage, Reading, Student, User
from ..schemas import (AccountIn, AnalyzeIn, DiffIn, ClassroomIn, FinalizeIn, MarkPatch, PassageIn, PassagePatch, StudentIn,
                       StudentPatch, StudentsBulkIn, VariantIn)
from ..services import analytics
from ..services import readings as reading_svc
from ..speech import registry
from .serializers import passage_out, reading_out

# Everything in this module is teacher-only. Public and student routes live in auth_routes.py.
router = APIRouter(prefix="/api", dependencies=[Depends(require_teacher)])
MAX_UPLOAD = 25 * 1024 * 1024


def _get(db: Session, model, id_: int):
    obj = db.get(model, id_)
    if obj is None:
        raise HTTPException(404, f"{model.__name__} {id_} not found")
    return obj


# ---------------------------------------------------------------- system
@router.get("/system")
def system() -> dict:
    s = get_settings()
    return {
        "models": registry.status(),
        "thresholds": load_thresholds().to_dict(),
        "settings": {"weak_min_errors": s.weak_min_errors, "weak_min_readings": s.weak_min_readings,
                     "count_unsure_as_correct": s.count_unsure_as_correct,
                     "database": "postgresql" if s.db_url.startswith("postgres") else "sqlite",
                     "demo_mode": s.seed_demo, "audio_retention_days": s.audio_retention_days,
                     "max_failed_logins": s.max_failed_logins, "lockout_minutes": s.lockout_minutes},
    }


@router.post("/system/warmup")
def warmup(include_whisper: bool = False) -> dict:
    registry.get_ctc()
    if include_whisper:
        registry.get_whisper()
    return registry.status()


# ------------------------------------------------------------ classrooms
@router.get("/classrooms")
def list_classrooms(db: Session = Depends(get_db)) -> list[dict]:
    out = []
    for c in db.scalars(select(Classroom).order_by(Classroom.grade, Classroom.name)):
        ov = analytics.class_overview(db, c)
        out.append({k: ov[k] for k in ("id", "name", "grade", "school", "stats")})
    return out


@router.post("/classrooms", status_code=201)
def create_classroom(body: ClassroomIn, db: Session = Depends(get_db)) -> dict:
    c = Classroom(name=body.name.strip(), grade=body.grade, school=body.school)
    db.add(c)
    db.commit()
    return analytics.class_overview(db, c)


@router.get("/classrooms/{cid}")
def get_classroom(cid: int, db: Session = Depends(get_db)) -> dict:
    return analytics.class_overview(db, _get(db, Classroom, cid))


@router.patch("/classrooms/{cid}")
def update_classroom(cid: int, body: ClassroomIn, db: Session = Depends(get_db)) -> dict:
    c = _get(db, Classroom, cid)
    c.name, c.grade, c.school = body.name.strip(), body.grade, body.school
    db.commit()
    return analytics.class_overview(db, c)


@router.delete("/classrooms/{cid}", status_code=204)
def delete_classroom(cid: int, db: Session = Depends(get_db)) -> None:
    c = _get(db, Classroom, cid)
    for st in c.students:
        for r in st.readings:
            reading_svc.delete_audio(r)
    db.delete(c)
    db.commit()


# -------------------------------------------------------------- students
@router.post("/classrooms/{cid}/students", status_code=201)
def add_student(cid: int, body: StudentIn, db: Session = Depends(get_db)) -> dict:
    _get(db, Classroom, cid)
    st = Student(classroom_id=cid, code=body.code.strip(), nickname=(body.nickname or "").strip() or None)
    db.add(st)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "A student with this code already exists in the class") from None
    return analytics.student_card(st)


@router.post("/classrooms/{cid}/students/bulk", status_code=201)
def add_students_bulk(cid: int, body: StudentsBulkIn, db: Session = Depends(get_db)) -> dict:
    c = _get(db, Classroom, cid)
    existing = {s.code for s in c.students}
    width = len(str(body.start + body.count - 1))
    added = 0
    for n in range(body.start, body.start + body.count):
        code = f"{body.prefix}{str(n).zfill(width)}"
        if code not in existing:
            db.add(Student(classroom_id=cid, code=code))
            added += 1
    db.commit()
    return {"added": added}


@router.put("/students/{sid}/account")
def set_student_account(sid: int, body: AccountIn, db: Session = Depends(get_db)) -> dict:
    """Create the student's login, or change its username/password."""
    st = _get(db, Student, sid)
    username = body.username.strip().lower()
    clash = db.scalar(select(User).where(User.username == username))
    if clash is not None and clash.student_id != st.id:
        raise HTTPException(409, "This username is already taken")
    label = f"{st.classroom.name} · {st.code}"
    if st.account is None:
        st.account = User(username=username, password_hash=hash_password(body.password), role=STUDENT,
                          display_name=label)
    else:
        st.account.username = username
        st.account.password_hash = hash_password(body.password)
        st.account.failed_logins, st.account.locked_until = 0, None  # the teacher's reset also unlocks
        end_other_sessions(db, st.account.id)  # the child logs in again with the new password
    db.commit()
    return analytics.student_card(st)


@router.delete("/students/{sid}/account", status_code=204)
def delete_student_account(sid: int, db: Session = Depends(get_db)) -> None:
    st = _get(db, Student, sid)
    if st.account is not None:
        end_other_sessions(db, st.account.id)
        db.delete(st.account)
        db.commit()


@router.get("/students/{sid}")
def get_student(sid: int, db: Session = Depends(get_db)) -> dict:
    return analytics.student_detail(db, _get(db, Student, sid))


@router.patch("/students/{sid}")
def update_student(sid: int, body: StudentPatch, db: Session = Depends(get_db)) -> dict:
    st = _get(db, Student, sid)
    if body.code is not None:
        st.code = body.code.strip()
    if body.nickname is not None:
        st.nickname = body.nickname.strip() or None
    if body.active is not None:
        st.active = body.active
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "A student with this code already exists in the class") from None
    return analytics.student_card(st)


@router.delete("/students/{sid}", status_code=204)
def delete_student(sid: int, db: Session = Depends(get_db)) -> None:
    st = _get(db, Student, sid)
    for r in st.readings:
        reading_svc.delete_audio(r)
    db.delete(st)
    db.commit()


# -------------------------------------------------------------- passages
@router.get("/passages")
def list_passages(include_inactive: bool = False, language: str | None = None,
                  db: Session = Depends(get_db)) -> list[dict]:
    q = select(Passage).order_by(Passage.grade, Passage.language, Passage.code, Passage.id)
    if language:
        q = q.where(Passage.language == language)
    if not include_inactive:
        q = q.where(Passage.active.is_(True))
    return [passage_out(p, with_patterns=True) for p in db.scalars(q)]


@router.post("/passages", status_code=201)
def create_passage(body: PassageIn, db: Session = Depends(get_db)) -> dict:
    if body.language == "en" and not english_words(body.text):
        raise HTTPException(422, "The passage has no English words")
    if body.language == "bn" and not passage_words(body.text):
        raise HTTPException(422, "The passage has no Bangla words")
    p = Passage(title=body.title.strip(), grade=body.grade, language=body.language, text=body.text.strip())
    db.add(p)
    db.commit()
    return passage_out(p, True)


@router.get("/passages/{pid}")
def get_passage(pid: int, db: Session = Depends(get_db)) -> dict:
    p = _get(db, Passage, pid)
    d = passage_out(p, True)
    words = english_words(p.text) if p.language == "en" else passage_words(p.text)
    d["words"] = [{"index": w.index, "display": w.display, "norm": w.norm,
                   "units": [u.text for u in w.units]} for w in words]
    return d


@router.patch("/passages/{pid}")
def update_passage(pid: int, body: PassagePatch, db: Session = Depends(get_db)) -> dict:
    p = _get(db, Passage, pid)
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(p, k, v.strip() if isinstance(v, str) else v)
    db.commit()
    return passage_out(p, True)


@router.delete("/passages/{pid}", status_code=204)
def delete_passage(pid: int, db: Session = Depends(get_db)) -> None:
    p = _get(db, Passage, pid)
    used = db.scalar(select(Reading.id).where(Reading.passage_id == pid).limit(1))
    if used:
        p.active = False  # keep history intact
    else:
        db.delete(p)
    db.commit()


# -------------------------------------------------------------- readings
async def accept_upload(db: Session, st: Student, p: Passage, audio: UploadFile) -> Reading:
    """Store an uploaded recording and queue it for marking (shared by teacher and student routes)."""
    data = await audio.read()
    if not data:
        raise HTTPException(422, "Empty audio upload")
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, "Audio file too large")
    r = Reading(student_id=st.id, passage_id=p.id, passage_text=p.text, status="queued")
    db.add(r)
    db.flush()
    try:
        r.duration_sec = reading_svc.store_audio(r, data)
    except ValueError as e:
        db.rollback()
        raise HTTPException(422, str(e)) from None
    # reading an assigned passage completes that assignment
    for a in db.scalars(select(Assignment).where(Assignment.student_id == st.id, Assignment.passage_id == p.id,
                                                 Assignment.done_at.is_(None))):
        a.done_at = datetime.now(timezone.utc)
    db.commit()
    reading_svc.submit(r.id)
    return r


@router.post("/readings", status_code=202)
async def create_reading(student_id: int = Form(...), passage_id: int = Form(...), audio: UploadFile = File(...),
                         db: Session = Depends(get_db)) -> dict:
    st = _get(db, Student, student_id)
    p = _get(db, Passage, passage_id)
    r = await accept_upload(db, st, p, audio)
    return reading_out(r, with_marks=False)


@router.get("/readings")
def list_readings(limit: int = 50, status: str | None = None, reviewed: bool | None = None,
                  db: Session = Depends(get_db)) -> list[dict]:
    q = select(Reading).order_by(Reading.created_at.desc()).limit(min(limit, 500))
    if status:
        q = q.where(Reading.status == status)
    if reviewed is not None:
        q = q.where(Reading.reviewed.is_(reviewed))
    return [analytics.reading_summary(r) | {
        "student_code": r.student.code, "student_nickname": r.student.nickname,
        "classroom_id": r.student.classroom_id, "classroom_name": r.student.classroom.name,
    } for r in db.scalars(q)]


@router.get("/search")
def search(q: str = "", db: Session = Depends(get_db)) -> dict:
    """Quick search for the command palette: students, classes and passages."""
    term = q.strip().lower()
    students, classes, passages = [], [], []
    for c in db.scalars(select(Classroom).order_by(Classroom.grade, Classroom.name)):
        if not term or term in c.name.lower() or term in (c.school or "").lower():
            classes.append({"id": c.id, "name": c.name, "grade": c.grade})
        for st in c.students:
            hay = f"{st.code} {st.nickname or ''} {c.name}".lower()
            if term and all(t in hay for t in term.split()):
                students.append({"id": st.id, "code": st.code, "nickname": st.nickname,
                                 "classroom": c.name, "grade": c.grade})
    if term:
        for p in db.scalars(select(Passage).where(Passage.active.is_(True)).order_by(Passage.grade, Passage.code)):
            if term in p.title.lower() or term in (p.code or "").lower() or term in p.text.lower():
                passages.append({"id": p.id, "title": p.title, "grade": p.grade, "language": p.language})
    return {"students": students[:8], "classes": classes[:6], "passages": passages[:6]}


@router.get("/readings/{rid}")
def get_reading(rid: int, db: Session = Depends(get_db)) -> dict:
    return reading_out(_get(db, Reading, rid))


@router.get("/readings/{rid}/audio")
def get_reading_audio(rid: int, db: Session = Depends(get_db)):
    r = _get(db, Reading, rid)
    if not r.audio_path or not os.path.exists(r.audio_path):
        raise HTTPException(404, "Audio is not stored for this reading")
    return FileResponse(r.audio_path, media_type="audio/wav")


@router.patch("/readings/{rid}/marks/{index}")
def update_mark(rid: int, index: int, body: MarkPatch, db: Session = Depends(get_db)) -> dict:
    r = _get(db, Reading, rid)
    try:
        status = body.validated()
    except ValueError as e:
        raise HTTPException(422, str(e)) from None
    mark = next((m for m in r.marks if m.index == index), None)
    if mark is None:
        raise HTTPException(404, "Word not found")
    mark.teacher_status = None if status == mark.status else status
    reading_svc.recompute_metrics(r)
    db.commit()
    return reading_out(r)


@router.post("/readings/{rid}/finalize")
def finalize_reading(rid: int, body: FinalizeIn, db: Session = Depends(get_db)) -> dict:
    r = _get(db, Reading, rid)
    if r.status != "done":
        raise HTTPException(409, "Only processed readings can be finalised")
    r.reviewed = True
    r.reviewed_at = datetime.now(timezone.utc)
    r.keep_audio = body.keep_audio
    if not body.keep_audio:
        reading_svc.delete_audio(r)
    db.commit()
    return reading_out(r)


@router.post("/readings/{rid}/reprocess", status_code=202)
def reprocess_reading(rid: int, db: Session = Depends(get_db)) -> dict:
    r = _get(db, Reading, rid)
    if not r.audio_path or not os.path.exists(r.audio_path):
        raise HTTPException(409, "Audio was not kept for this reading")
    r.status = "queued"
    db.commit()
    reading_svc.submit(r.id)
    return reading_out(r, with_marks=False)


@router.post("/readings/{rid}/compare", status_code=202)
def compare_reading(rid: int, db: Session = Depends(get_db)) -> dict:
    r = _get(db, Reading, rid)
    if reading_svc.reading_language(r) != "bn":
        raise HTTPException(409, "The system comparison is only for Bangla readings")
    if not r.audio_path or not os.path.exists(r.audio_path):
        raise HTTPException(409, "Audio was not kept for this reading, so it cannot be compared")
    r.comparison_status = "queued"
    db.commit()
    reading_svc.submit_comparison(r.id)
    return reading_out(r, with_marks=False)


@router.delete("/readings/{rid}", status_code=204)
def delete_reading(rid: int, db: Session = Depends(get_db)) -> None:
    r = _get(db, Reading, rid)
    reading_svc.delete_audio(r)
    db.delete(r)
    db.commit()


# -------------------------------------------------------------- variants
@router.get("/variants")
def list_variants(db: Session = Depends(get_db)) -> list[dict]:
    return [{"id": v.id, "word": v.word, "variant": v.variant, "note": v.note}
            for v in db.scalars(select(AcceptedVariant).order_by(AcceptedVariant.word))]


@router.post("/variants", status_code=201)
def add_variant(body: VariantIn, db: Session = Depends(get_db)) -> dict:
    w, v = normalize_word(body.word), normalize_word(body.variant)
    if not w or not v or w == v:
        raise HTTPException(422, "Word and variant must be different Bangla words")
    obj = AcceptedVariant(word=w, variant=v, note=body.note)
    db.add(obj)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "This variant already exists") from None
    return {"id": obj.id, "word": obj.word, "variant": obj.variant, "note": obj.note}


@router.delete("/variants/{vid}", status_code=204)
def delete_variant(vid: int, db: Session = Depends(get_db)) -> None:
    db.delete(_get(db, AcceptedVariant, vid))
    db.commit()


# ------------------------------------------------------------ engine demo
@router.post("/bangla/analyze")
def analyze(body: AnalyzeIn) -> dict:
    words = []
    for w in passage_words(body.text):
        units = []
        for u in segment_normalized(w.norm):
            units.append({
                "text": u.text, "kind": u.kind, "consonants": list(u.consonants), "core": list(u.core),
                "phalas": list(u.phalas), "reph": u.reph, "kar": u.kar, "signs": list(u.signs),
                "hasanta": u.hasanta, "vowel": u.vowel, "is_conjunct": u.is_conjunct,
                "codepoints": [f"U+{ord(ch):04X}" for ch in u.text],
                "patterns": [pattern_label(k) for k in u.patterns()],
            })
        words.append({"display": w.display, "norm": w.norm, "units": units})
    return {"words": words}


@router.post("/bangla/diff")
def diff_words(body: DiffIn) -> dict:
    """Explain how a heard word differs from the expected word, unit by unit."""
    from dataclasses import asdict

    from ..alignment.words import align_units
    from ..bangla.phonetics import diff_units

    e_norm, h_norm = normalize_word(body.expected), normalize_word(body.heard)
    e_units, h_units = segment_normalized(e_norm), segment_normalized(h_norm)
    ops, cost = align_units(e_units, h_units)
    rows = []
    for op in ops:
        eu = e_units[op.i] if op.i is not None else None
        hu = h_units[op.j] if op.j is not None else None
        errs = [] if op.kind == "match" else (
            [asdict(x) for x in diff_units(eu, hu)] if eu is not None else
            [{"pattern": "", "kind": "added", "expected": None, "heard": hu.text,
              "description_bn": f"অতিরিক্ত {hu.text}", "description_en": f"Extra {hu.text} added"}])
        rows.append({"op": op.kind if (op.kind != "sub" or errs) else "spelling", "expected": eu.text if eu else None,
                     "heard": hu.text if hu else None, "cost": round(op.cost, 3),
                     "errors": [{**e, "label": pattern_label(e["pattern"]) if e["pattern"] else None} for e in errs]})
    return {"expected": e_norm, "heard": h_norm, "cost": round(cost, 3), "ops": rows}


# --------------------------------------------------------------- benchmark
@router.get("/benchmark")
def benchmark_report() -> dict:
    # the published report (results/, tracked in git) unless a newer local run exists
    from ..config import RESULTS_DIR

    candidates = [get_settings().reports_dir / "benchmark_latest.json", RESULTS_DIR / "benchmark_latest.json"]
    found = [p for p in candidates if p.exists()]
    if not found:
        return {"available": False}
    rep = [json.loads(p.read_text(encoding="utf-8")) for p in found]
    real = [r for r in rep if "SYNTHETIC" not in str(r.get("label", "")).upper()]
    return {"available": True, **(real or rep)[0]}
