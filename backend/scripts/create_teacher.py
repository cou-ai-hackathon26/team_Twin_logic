"""Create (or reset) a teacher login for a real school installation.

    python -m scripts.create_teacher <username>          # asks for the password twice

Use this with PB_SEED_DEMO=false, so no public demo accounts exist.
"""

from __future__ import annotations

import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from app.auth import TEACHER, end_other_sessions, hash_password  # noqa: E402
from app.db import SessionLocal, init_db  # noqa: E402
from app.models import User  # noqa: E402


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("usage: python -m scripts.create_teacher <username>")
    username = sys.argv[1].strip().lower()
    pw = getpass.getpass("New password (8+ characters): ")
    if len(pw) < 8 or pw != getpass.getpass("Repeat it: "):
        sys.exit("Passwords must match and have at least 8 characters.")
    init_db()
    with SessionLocal() as db:
        u = db.scalar(select(User).where(User.username == username))
        if u is not None and u.role != TEACHER:
            sys.exit(f"{username} is a {u.role} account")
        if u is None:
            db.add(User(username=username, password_hash=hash_password(pw), role=TEACHER, display_name=username))
            print(f"created teacher {username}")
        else:
            u.password_hash = hash_password(pw)
            u.failed_logins, u.locked_until = 0, None
            end_other_sessions(db, u.id)
            print(f"reset password for {username} and logged it out everywhere")
        db.commit()


if __name__ == "__main__":
    main()
