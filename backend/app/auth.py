"""Role-based login: ``admin``, ``teacher``, ``district`` (district officer) and ``student``.

Passwords are stored as salted PBKDF2-SHA256 hashes. A login creates a
server-side session; the browser holds only a random token in an HttpOnly
cookie (``Authorization: Bearer <token>`` also works for scripts).
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request
from sqlalchemy import delete
from sqlalchemy.orm import Session

from .config import get_settings
from .db import get_db
from .models import AuthSession, Student, User

COOKIE = "pb_session"
TEACHER, STUDENT, ADMIN, DISTRICT = "teacher", "student", "admin", "district"
ROLES = (TEACHER, STUDENT)
_ITER = 200_000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITER)
    return f"pbkdf2_sha256${_ITER}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters, salt_hex, hash_hex = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iters))
        return hmac.compare_digest(dk.hex(), hash_hex)
    except (ValueError, TypeError):
        return False


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("ascii", "ignore")).hexdigest()


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def create_session(db: Session, user: User) -> tuple[str, int]:
    """Returns (token, max_age_seconds)."""
    days = get_settings().session_days
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    db.execute(delete(AuthSession).where(AuthSession.expires_at < now))
    db.add(AuthSession(token_hash=_token_hash(token), user_id=user.id, expires_at=now + timedelta(days=days)))
    db.commit()
    return token, days * 86400


def _request_token(request: Request) -> str | None:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip() or None
    return request.cookies.get(COOKIE)


def end_other_sessions(db: Session, user_id: int, keep_token: str | None = None) -> None:
    """Log a user out everywhere (except the current browser), e.g. after a password change."""
    q = delete(AuthSession).where(AuthSession.user_id == user_id)
    if keep_token:
        q = q.where(AuthSession.token_hash != _token_hash(keep_token))
    db.execute(q)


def end_session(db: Session, request: Request) -> None:
    token = _request_token(request)
    if token:
        db.execute(delete(AuthSession).where(AuthSession.token_hash == _token_hash(token)))
        db.commit()


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = _request_token(request)
    if not token:
        raise HTTPException(401, "Please log in")
    sess = db.get(AuthSession, _token_hash(token))
    if sess is None or _aware(sess.expires_at) < datetime.now(timezone.utc):
        raise HTTPException(401, "Your session has expired. Please log in again")
    return sess.user


def require_teacher(user: User = Depends(current_user), db: Session = Depends(get_db)) -> User:
    """Teachers and admins. A teacher sees shared classes and their own; an admin sees every class."""
    if user.role not in (TEACHER, ADMIN):
        raise HTTPException(403, "Teacher account required")
    db.info["teacher_id"] = None if user.role == ADMIN else user.id  # read by can_see()
    return user


def require_admin(user: User = Depends(current_user), db: Session = Depends(get_db)) -> User:
    if user.role != ADMIN:
        raise HTTPException(403, "Admin account required")
    db.info["teacher_id"] = None
    return user


def require_district(user: User = Depends(current_user)) -> User:
    """District officers (counts per school only, never children or recordings) and admins."""
    if user.role not in (DISTRICT, ADMIN):
        raise HTTPException(403, "District account required")
    return user


def can_see(db: Session, classroom) -> bool:
    """Class-level access: shared classes (no owner) and the teacher's own classes."""
    tid = db.info.get("teacher_id")
    return tid is None or classroom is None or classroom.teacher_id in (None, tid)


def classroom_of(obj):
    from .models import Classroom, Reading, Student

    if isinstance(obj, Classroom):
        return obj
    if isinstance(obj, Student):
        return obj.classroom
    if isinstance(obj, Reading):
        return obj.student.classroom if obj.student else None
    return None


def require_student(user: User = Depends(current_user)) -> User:
    if user.role != STUDENT or user.student is None:
        raise HTTPException(403, "Student account required")
    return user


def user_out(u: User) -> dict:
    d = {"id": u.id, "username": u.username, "role": u.role, "display_name": u.display_name or u.username,
         "student": None}
    st: Student | None = u.student
    if st is not None:
        d["student"] = {"id": st.id, "code": st.code, "nickname": st.nickname, "classroom_id": st.classroom_id,
                        "classroom": st.classroom.name, "grade": st.classroom.grade}
    return d
