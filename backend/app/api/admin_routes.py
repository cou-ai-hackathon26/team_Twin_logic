"""Admin: schools, teacher and district-officer accounts. Teachers then create their students' logins.

Roles: admin (manages schools and accounts, sees every class) -> teacher (own and shared classes,
creates student logins on each student's page) -> student (own readings only).
District officer: sees only the district summary (counts per school), never children or recordings.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import ADMIN, DISTRICT, TEACHER, end_other_sessions, hash_password, require_admin
from ..config import get_settings
from ..db import get_db
from ..models import Classroom, School, User, iso

router = APIRouter(prefix="/api/admin", dependencies=[Depends(require_admin)])


class TeacherIn(BaseModel):
    username: str = Field(min_length=3, max_length=60, pattern=r"^[A-Za-z0-9_.-]+$")
    display_name: str | None = Field(default=None, max_length=120)
    password: str = Field(min_length=8, max_length=200)
    role: Literal["teacher", "district"] = "teacher"
    school_id: int | None = None


class PasswordReset(BaseModel):
    password: str = Field(min_length=8, max_length=200)


def _out(db: Session, u: User) -> dict:
    classes = db.scalar(select(func.count(Classroom.id)).where(Classroom.teacher_id == u.id)) or 0
    return {"id": u.id, "username": u.username, "display_name": u.display_name or u.username, "role": u.role,
            "classes": classes, "created_at": iso(u.created_at), "school_id": u.school_id,
            "locked": bool(u.locked_until)}


def _teacher(db: Session, uid: int) -> User:
    """A teacher or district-officer account (the admin account is managed at installation)."""
    u = db.get(User, uid)
    if u is None or u.role not in (TEACHER, DISTRICT):
        raise HTTPException(404, "Account not found")
    return u


def _protect_demo(u: User, action: str) -> None:
    if get_settings().seed_demo:
        from ..seed.demo import is_demo_login

        if is_demo_login(u.username):
            raise HTTPException(403, f"The shared demo login cannot {action} on the public demo")


@router.get("/teachers")
def list_teachers(db: Session = Depends(get_db)) -> list[dict]:
    users = db.scalars(select(User).where(User.role.in_([TEACHER, ADMIN, DISTRICT])).order_by(User.role, User.username))
    return [_out(db, u) for u in users]


@router.post("/teachers", status_code=201)
def create_teacher(body: TeacherIn, db: Session = Depends(get_db)) -> dict:
    username = body.username.strip().lower()
    if db.scalar(select(User.id).where(User.username == username)) is not None:
        raise HTTPException(409, "This username is already taken")
    if body.school_id is not None and db.get(School, body.school_id) is None:
        raise HTTPException(404, "School not found")
    u = User(username=username, password_hash=hash_password(body.password), role=body.role,
             display_name=(body.display_name or "").strip() or username,
             school_id=body.school_id if body.role == TEACHER else None)
    db.add(u)
    db.commit()
    return _out(db, u)


@router.put("/teachers/{uid}/password", status_code=204)
def reset_teacher_password(uid: int, body: PasswordReset, db: Session = Depends(get_db)) -> None:
    u = _teacher(db, uid)
    _protect_demo(u, "change its published password")
    u.password_hash = hash_password(body.password)
    u.failed_logins, u.locked_until = 0, None
    end_other_sessions(db, u.id)
    db.commit()


@router.delete("/teachers/{uid}", status_code=204)
def delete_teacher(uid: int, db: Session = Depends(get_db)) -> None:
    """Removes the login only. The teacher's classes stay and become shared (visible to all teachers)."""
    u = _teacher(db, uid)
    _protect_demo(u, "be removed")
    for c in db.scalars(select(Classroom).where(Classroom.teacher_id == u.id)):
        c.teacher_id = None
    end_other_sessions(db, u.id)
    db.delete(u)
    db.commit()


# ------------------------------------------------------------------ schools
class SchoolIn(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    upazila: str | None = Field(default=None, max_length=120)
    district: str | None = Field(default=None, max_length=120)


class SchoolLink(BaseModel):
    school_id: int | None = None


def _school(db: Session, sid: int) -> School:
    s = db.get(School, sid)
    if s is None:
        raise HTTPException(404, "School not found")
    return s


def _school_out(db: Session, s: School) -> dict:
    classes = db.scalars(select(Classroom).where(Classroom.school_id == s.id).order_by(Classroom.grade)).all()
    teachers = db.scalar(select(func.count(User.id)).where(User.school_id == s.id)) or 0
    children = sum(1 for c in classes for st in c.students if st.active)
    return {"id": s.id, "name": s.name, "upazila": s.upazila, "district": s.district, "teachers": teachers,
            "classes": [{"id": c.id, "name": c.name, "grade": c.grade} for c in classes], "children": children}


def _clean(v: str | None) -> str | None:
    return (v or "").strip() or None


@router.get("/schools")
def list_schools(db: Session = Depends(get_db)) -> dict:
    schools = db.scalars(select(School).order_by(School.district, School.upazila, School.name)).all()
    unassigned = db.scalars(select(Classroom).where(Classroom.school_id.is_(None)).order_by(Classroom.grade)).all()
    return {"schools": [_school_out(db, s) for s in schools],
            "unassigned_classes": [{"id": c.id, "name": c.name, "grade": c.grade} for c in unassigned]}


@router.post("/schools", status_code=201)
def create_school(body: SchoolIn, db: Session = Depends(get_db)) -> dict:
    name = body.name.strip()
    if db.scalar(select(School.id).where(School.name == name)) is not None:
        raise HTTPException(409, "A school with this name already exists")
    s = School(name=name, upazila=_clean(body.upazila), district=_clean(body.district))
    db.add(s)
    db.commit()
    return _school_out(db, s)


@router.put("/schools/{sid}")
def update_school(sid: int, body: SchoolIn, db: Session = Depends(get_db)) -> dict:
    s = _school(db, sid)
    name = body.name.strip()
    if name != s.name and db.scalar(select(School.id).where(School.name == name)) is not None:
        raise HTTPException(409, "A school with this name already exists")
    s.name, s.upazila, s.district = name, _clean(body.upazila), _clean(body.district)
    for c in db.scalars(select(Classroom).where(Classroom.school_id == s.id)):
        c.school = name
    db.commit()
    return _school_out(db, s)


@router.delete("/schools/{sid}", status_code=204)
def delete_school(sid: int, db: Session = Depends(get_db)) -> None:
    """Removes the school only: its classes and teachers stay, without a school."""
    s = _school(db, sid)
    for c in db.scalars(select(Classroom).where(Classroom.school_id == s.id)):
        c.school_id = None
    for u in db.scalars(select(User).where(User.school_id == s.id)):
        u.school_id = None
    db.delete(s)
    db.commit()


@router.put("/teachers/{uid}/school")
def set_teacher_school(uid: int, body: SchoolLink, db: Session = Depends(get_db)) -> dict:
    """Put a teacher in a school; their own classes move with them."""
    u = _teacher(db, uid)
    if u.role != TEACHER:
        raise HTTPException(422, "Only teachers belong to a school")
    s = _school(db, body.school_id) if body.school_id is not None else None
    u.school_id = s.id if s else None
    for c in db.scalars(select(Classroom).where(Classroom.teacher_id == u.id)):
        c.school_id = u.school_id
        if s:
            c.school = s.name
    db.commit()
    return _out(db, u)


@router.put("/classrooms/{cid}/school")
def set_class_school(cid: int, body: SchoolLink, db: Session = Depends(get_db)) -> dict:
    c = db.get(Classroom, cid)
    if c is None:
        raise HTTPException(404, "Class not found")
    s = _school(db, body.school_id) if body.school_id is not None else None
    c.school_id = s.id if s else None
    if s:
        c.school = s.name
    db.commit()
    return {"id": c.id, "name": c.name, "school_id": c.school_id}
