"""Demo data: a teacher, one class per grade, student logins and practice results.

Versioned, so an install that already has older demo data gets topped up
once, and nothing is re-created after a teacher deletes it. Real (non-demo)
classes are never touched. Disable with PB_SEED_DEMO=false.

    teacher  / teacher123          (role: teacher)
    c1r01 .. c5r10 / student123    (role: student; class N, roll NN)

The practice results are *simulated* readings (marked ``model_id =
"demo-seed (simulated)"``, no audio): each demo child gets an ability level,
reads a few passages with realistic slips (dropped conjuncts, wrong vowel
signs, skipped words, stopping early), and the real marking engine turns
those slips into word marks, weak patterns and a mark out of 10.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..assessment import types as T
from ..assessment.english import assess_english, english_words
from ..assessment.marking import assess, passage_words
from ..assessment.metrics import compute_metrics
from ..auth import ADMIN, STUDENT, TEACHER, hash_password, verify_password
from ..bangla.normalize import normalize_word
from ..bangla.segment import segment_normalized
from ..db import SessionLocal
from ..models import SIMULATED_MODEL_ID, AppMeta, Classroom, Passage, Reading, Student, User

DEMO_VERSION = 4  # v4: grades 1-3 practise the NCTB-aligned passages T01-T12 first (v3: richer history)
META_KEY = "demo_seed_version"
TEACHER_LOGIN = ("teacher", "teacher123")
ADMIN_LOGIN = ("admin", "admin123")  # demo only: creates and removes teacher accounts
STUDENT_PASSWORD = "student123"
STUDENTS_PER_CLASS = 10
SCHOOL = "PoraBondhu Demo School"
SIM_MODEL = SIMULATED_MODEL_ID
NICKNAMES = ["Rafi", "Mitu", "Tanvir", "Nusrat", "Shuvo", "Riya", "Arif", "Lima", "Sakib", "Tania"]


def student_username(grade: int, roll: int) -> str:
    return f"c{grade}r{roll:02d}"


# ------------------------------------------------------------ simulated slips
_KAR_SWAP = {"া": "", "ি": "ী", "ী": "ি", "ু": "ূ", "ূ": "ু", "ে": "ি", "ো": "া", "ৈ": "ে", "ৌ": "ো"}
_CONS_SWAP = {"ব": "ভ", "ভ": "ব", "দ": "ধ", "ধ": "দ", "ত": "থ", "থ": "ত", "ক": "খ", "খ": "ক", "গ": "ঘ",
              "ঘ": "গ", "প": "ফ", "ফ": "প", "জ": "ঝ", "স": "শ", "শ": "স", "ড": "ঢ", "চ": "ছ", "ছ": "চ"}


def bangla_slip(word: str, rng: random.Random, conj_bias: float = 0.75) -> str | None:
    """A typical child misreading: conjunct simplified, vowel sign changed, or aspirate swapped.

    ``conj_bias`` gives each child a consistent tendency, so weak patterns repeat like real ones."""
    w = list(word)
    if "্" in w and rng.random() < conj_bias:  # প্রথম -> পথম
        i = w.index("্")
        del w[i:i + 2]
    else:
        kars = [i for i, ch in enumerate(w) if ch in _KAR_SWAP]
        cons = [i for i, ch in enumerate(w) if ch in _CONS_SWAP]
        if kars and (not cons or rng.random() < 0.6):
            i = rng.choice(kars)
            w[i] = _KAR_SWAP[w[i]]
        elif cons:
            i = rng.choice(cons)
            w[i] = _CONS_SWAP[w[i]]
        else:
            return None
    out = normalize_word("".join(w))
    return out if out and out != word else None


_VOWEL_SWAP = {"a": "e", "e": "i", "i": "e", "o": "u", "u": "o"}


def english_slip(word: str, rng: random.Random) -> str | None:
    if len(word) > 3 and rng.random() < 0.5:
        return word[:-1]  # dropped ending: "runs" -> "run"
    idx = [i for i, ch in enumerate(word) if ch in _VOWEL_SWAP]
    if not idx:
        return None
    i = rng.choice(idx)
    return word[:i] + _VOWEL_SWAP[word[i]] + word[i + 1:]


def simulate_reading(passage: Passage, ability: float, rng: random.Random, th: T.Thresholds,
                     conj_bias: float = 0.75):
    """Returns (marks, metrics, transcript, duration) for one simulated reading."""
    english = passage.language == "en"
    pw = english_words(passage.text) if english else passage_words(passage.text)
    n = len(pw)
    stop = n
    if n > 8 and rng.random() < (1 - ability) * 0.7:  # weaker readers sometimes stop early
        stop = n - rng.randint(3, min(8, n // 3))
    err_rate = max(0.01, (1 - ability) * 0.7)
    sec_per_word = 60.0 / rng.uniform(25 + 70 * ability, 35 + 85 * ability)

    t = 0.6
    heard_en: list[tuple[str, float, float, float]] = []
    rw: list[T.RecognizedWord] = []
    ev: list[T.ExpectedEvidence] = []
    for i, w in enumerate(pw):
        if i >= stop:
            ev.append(T.ExpectedEvidence(None, None, [-6.0] * len(w.units)))
            continue
        if rng.random() < (1 - ability) * 0.12:
            t += rng.uniform(3.2, 4.5)  # hesitation
        dur = sec_per_word * rng.uniform(0.7, 1.3)
        said: str | None = w.norm
        if rng.random() < err_rate:
            said = None if rng.random() < 0.25 else (english_slip(w.norm, rng) if english else bangla_slip(w.norm, rng, conj_bias))
        if said is None:  # skipped
            ev.append(T.ExpectedEvidence(t, t + 0.1, [-5.0] * len(w.units)))
            t += 0.3
            continue
        if english:
            prob = 0.92 if said == w.norm else rng.choice([0.85, 0.8, 0.35])
            heard_en.append((said, t, t + dur, prob))
        else:
            units = segment_normalized(said)
            good = said == w.norm
            rw.append(T.RecognizedWord(said, units, [0.95 if good else 0.9] * len(units), t, t + dur))
            ev.append(T.ExpectedEvidence(t, t + dur, [3.0 if good else -4.0] * len(w.units)))
        t += dur + rng.uniform(0.1, 0.35)

    if english:
        marks = assess_english(pw, heard_en, th)
        transcript = " ".join(h[0] for h in heard_en)
    else:
        marks = assess(pw, rw, ev, th)
        transcript = " ".join(r.text for r in rw)
    duration = round(t + 0.8, 2)
    metrics = compute_metrics([m.to_dict() for m in marks], duration)
    return marks, metrics, transcript, duration


# ------------------------------------------------------------------ seeding
def _ensure_class(db: Session, grade: int, student_hash: str) -> Classroom:
    name = f"Class {grade}"
    c = db.scalar(select(Classroom).where(Classroom.name == name, Classroom.grade == grade))
    if c is None:
        c = Classroom(name=name, grade=grade, school=SCHOOL)
        db.add(c)
        db.flush()
    existing = {s.code: s for s in c.students}
    taken = set(db.scalars(select(User.username)))
    for roll in range(1, STUDENTS_PER_CLASS + 1):
        code = f"Roll {roll:02d}"
        st = existing.get(code)
        if st is None:
            st = Student(classroom_id=c.id, code=code)
            db.add(st)
            db.flush()
        if not st.nickname:
            st.nickname = NICKNAMES[(roll - 1 + grade) % len(NICKNAMES)]
        uname = student_username(grade, roll)
        if st.account is None and uname not in taken:
            db.add(User(username=uname, password_hash=student_hash, role=STUDENT,
                        display_name=f"{name} · {code}", student_id=st.id))
    db.flush()
    db.refresh(c)
    return c


def _is_simulated_only(st: Student) -> bool:
    return all(r.model_id == SIM_MODEL for r in st.readings)


def _seed_results(db: Session, c: Classroom, refresh: bool = False) -> int:
    """Simulated reading history for demo students.

    Students with no readings get a history. With ``refresh`` (demo upgrade), students whose
    readings are *all* simulated get a fresh, richer history; real readings are never touched.
    Each child: up to 8 tests over ~10 weeks, ability that improves over time, a personal
    tendency (conjuncts vs vowel signs) so weak patterns repeat, and the newest test or two
    still waiting for the teacher's review.
    """
    from ..services.readings import store_marks  # avoid importing the worker at module load

    th = T.Thresholds()
    passages = db.scalars(select(Passage).where(Passage.active.is_(True), Passage.grade == c.grade)).all()
    bn = sorted((p for p in passages if p.language == "bn"), key=lambda p: p.code or "")
    en = sorted((p for p in passages if p.language == "en"), key=lambda p: p.code or "")
    if not bn and not en:
        return 0
    now = datetime.now(timezone.utc)
    added = 0
    for st in c.students:
        if st.readings:
            if not (refresh and _is_simulated_only(st)):
                continue
            for r in list(st.readings):
                db.delete(r)
            db.flush()
            db.refresh(st)
        rng = random.Random(f"porabondhu-demo-v3-{c.grade}-{st.code}")
        roll = int(st.code.split()[-1]) if st.code.split()[-1].isdigit() else 0
        if roll == STUDENTS_PER_CLASS and c.grade in (2, 4):
            continue  # a couple of children not heard yet, so coverage isn't a perfect 100%
        ability = rng.uniform(0.32, 0.9)
        conj_bias = rng.choice([0.9, 0.8, 0.55, 0.3])
        n_bn, n_en = (5, 3) if rng.random() > 0.15 else (3, 1)
        # textbook-aligned passages (T01-T12, docs/CURRICULUM_ALIGNMENT.md) first, then the rest
        tb = [p for p in bn if (p.code or "").startswith("T")]
        rest = [p for p in bn if p not in tb]
        pick = rng.sample(tb, min(n_bn, len(tb)))
        pick += rng.sample(rest, min(n_bn - len(pick), len(rest)))
        plan = pick + rng.sample(en, min(n_en, len(en)))
        rng.shuffle(plan)
        day = rng.randint(66, 74)
        step = day / max(1, len(plan))
        unreviewed = 1 if rng.random() < 0.6 else (2 if rng.random() < 0.5 else 0)
        for k, p in enumerate(plan):
            when = now - timedelta(days=max(0.2, day), hours=rng.randint(0, 5), minutes=rng.randint(0, 59))
            day -= step * rng.uniform(0.75, 1.15)
            growth = 0.045 * k + rng.uniform(-0.04, 0.04)
            marks, metrics, transcript, duration = simulate_reading(p, min(0.98, ability + growth), rng, th, conj_bias)
            pending = k >= len(plan) - unreviewed
            r = Reading(student_id=st.id, passage_id=p.id, passage_text=p.text, status="done", created_at=when,
                        processed_at=when + timedelta(seconds=20), transcript=transcript, duration_sec=duration,
                        processing_ms=0, model_id=SIM_MODEL, thresholds=th.to_dict(), forced_alignment_ok=True,
                        reviewed=not pending)
            if r.reviewed:
                r.reviewed_at = when + timedelta(hours=2)
            db.add(r)
            store_marks(r, marks)
            r.metrics = metrics.to_dict()
            added += 1
    return added


def ensure_demo_admin(db: Session) -> bool:
    """The demo admin login (added after the first demo seeds, so it is checked on every start)."""
    if db.scalar(select(User.id).where(User.username == ADMIN_LOGIN[0])) is not None:
        return False
    if db.scalar(select(User.id).where(User.username == TEACHER_LOGIN[0])) is None:
        return False  # not a demo database
    db.add(User(username=ADMIN_LOGIN[0], password_hash=hash_password(ADMIN_LOGIN[1]), role=ADMIN,
                display_name="Demo Admin"))
    db.commit()
    return True


def seed_demo() -> str | None:
    db = SessionLocal()
    try:
        ensure_demo_admin(db)
        meta = db.get(AppMeta, META_KEY)
        version = int(meta.value) if meta else 0
        if version >= DEMO_VERSION:
            return None
        users = db.scalar(select(func.count(User.id)))
        has_demo_teacher = db.scalar(select(User.id).where(User.username == TEACHER_LOGIN[0])) is not None
        if version == 0 and users and not has_demo_teacher:
            # someone set up their own accounts before demo seeding existed: leave their data alone
            db.add(AppMeta(key=META_KEY, value=str(DEMO_VERSION)))
            db.commit()
            return None
        if not has_demo_teacher:
            db.add(User(username=TEACHER_LOGIN[0], password_hash=hash_password(TEACHER_LOGIN[1]), role=TEACHER,
                        display_name="Demo Teacher"))
        student_hash = hash_password(STUDENT_PASSWORD)  # one hash is fine for a shared demo password
        readings = 0
        for grade in range(1, 6):
            c = _ensure_class(db, grade, student_hash)
            if c.school == SCHOOL:  # only demo classes get simulated results
                readings += _seed_results(db, c, refresh=version < DEMO_VERSION)
        if meta is None:
            db.add(AppMeta(key=META_KEY, value=str(DEMO_VERSION)))
        else:
            meta.value = str(DEMO_VERSION)
        db.commit()
        ensure_demo_admin(db)
        return (f"v{DEMO_VERSION}: teacher={TEACHER_LOGIN[0]}, students={student_username(1, 1)}..."
                f"{student_username(5, STUDENTS_PER_CLASS)}, {readings} simulated readings")
    finally:
        db.close()


def is_demo_login(username: str | None) -> bool:
    """The published demo logins (teacher, c1r01 … c5r10) that the README tells visitors to use."""
    if not username:
        return False
    if username in (TEACHER_LOGIN[0], ADMIN_LOGIN[0]):
        return True
    return any(username == student_username(g, r) for g in range(1, 6) for r in range(1, STUDENTS_PER_CLASS + 1))


def restore_demo(db: Session) -> dict:
    """Demo reset: put back what a visitor may have changed, so the README instructions work again.

    Restores the published passwords and clears lockouts of the demo logins, re-creates any deleted
    demo class, student or simulated history. Real readings are removed by the caller."""
    restored = 0
    teacher = db.scalar(select(User).where(User.username == TEACHER_LOGIN[0]))
    if teacher is None:
        db.add(User(username=TEACHER_LOGIN[0], password_hash=hash_password(TEACHER_LOGIN[1]), role=TEACHER,
                    display_name="Demo Teacher"))
        restored += 1
    db.flush()
    if ensure_demo_admin(db):
        restored += 1
    # teacher accounts visitors created through the admin page are removed (their classes stay, shared)
    for u in db.scalars(select(User).where(User.role == TEACHER, User.username != TEACHER_LOGIN[0])):
        db.delete(u)
        restored += 1
    student_hash = hash_password(STUDENT_PASSWORD)
    for grade in range(1, 6):
        c = _ensure_class(db, grade, student_hash)
        if c.school == SCHOOL:
            _seed_results(db, c)  # only children with no readings get their simulated history back
    for u in db.scalars(select(User)):
        if not is_demo_login(u.username):
            continue
        want = {TEACHER_LOGIN[0]: TEACHER_LOGIN[1], ADMIN_LOGIN[0]: ADMIN_LOGIN[1]}.get(u.username, STUDENT_PASSWORD)
        if not verify_password(want, u.password_hash) or u.failed_logins or u.locked_until:
            u.password_hash = hash_password(want) if not verify_password(want, u.password_hash) else u.password_hash
            u.failed_logins, u.locked_until = 0, None
            restored += 1
    db.commit()
    return {"logins_restored": restored}
