"""Admin: create and manage teacher accounts. Teachers then create their students' logins.

Roles: admin (manages teachers, sees every class) -> teacher (own and shared classes, creates student
logins on each student's page) -> student (own readings only).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import ADMIN, TEACHER, end_other_sessions, hash_password, require_admin
from ..config import get_settings
from ..db import get_db
from ..models import Classroom, User, iso

router = APIRouter(prefix="/api/admin", dependencies=[Depends(require_admin)])


class TeacherIn(BaseModel):
    username: str = Field(min_length=3, max_length=60, pattern=r"^[A-Za-z0-9_.-]+$")
    display_name: str | None = Field(default=None, max_length=120)
    password: str = Field(min_length=8, max_length=200)


class PasswordReset(BaseModel):
    password: str = Field(min_length=8, max_length=200)


def _out(db: Session, u: User) -> dict:
    classes = db.scalar(select(func.count(Classroom.id)).where(Classroom.teacher_id == u.id)) or 0
    return {"id": u.id, "username": u.username, "display_name": u.display_name or u.username, "role": u.role,
            "classes": classes, "created_at": iso(u.created_at),
            "locked": bool(u.locked_until)}


def _teacher(db: Session, uid: int) -> User:
    u = db.get(User, uid)
    if u is None or u.role != TEACHER:
        raise HTTPException(404, "Teacher not found")
    return u


@router.get("/teachers")
def list_teachers(db: Session = Depends(get_db)) -> list[dict]:
    users = db.scalars(select(User).where(User.role.in_([TEACHER, ADMIN])).order_by(User.role, User.username))
    return [_out(db, u) for u in users]


@router.post("/teachers", status_code=201)
def create_teacher(body: TeacherIn, db: Session = Depends(get_db)) -> dict:
    username = body.username.strip().lower()
    if db.scalar(select(User.id).where(User.username == username)) is not None:
        raise HTTPException(409, "This username is already taken")
    u = User(username=username, password_hash=hash_password(body.password), role=TEACHER,
             display_name=(body.display_name or "").strip() or username)
    db.add(u)
    db.commit()
    return _out(db, u)


@router.put("/teachers/{uid}/password", status_code=204)
def reset_teacher_password(uid: int, body: PasswordReset, db: Session = Depends(get_db)) -> None:
    u = _teacher(db, uid)
    if get_settings().seed_demo:
        from ..seed.demo import is_demo_login

        if is_demo_login(u.username):
            raise HTTPException(403, "The shared demo teacher keeps its published password on the public demo")
    u.password_hash = hash_password(body.password)
    u.failed_logins, u.locked_until = 0, None
    end_other_sessions(db, u.id)
    db.commit()


@router.delete("/teachers/{uid}", status_code=204)
def delete_teacher(uid: int, db: Session = Depends(get_db)) -> None:
    """Removes the login only. The teacher's classes stay and become shared (visible to all teachers)."""
    u = _teacher(db, uid)
    if get_settings().seed_demo:
        from ..seed.demo import is_demo_login

        if is_demo_login(u.username):
            raise HTTPException(403, "The shared demo teacher cannot be removed on the public demo")
    for c in db.scalars(select(Classroom).where(Classroom.teacher_id == u.id)):
        c.teacher_id = None
    end_other_sessions(db, u.id)
    db.delete(u)
    db.commit()
