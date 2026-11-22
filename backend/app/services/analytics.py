"""Teacher-facing summaries: per child, per class, practice recommendations."""

from __future__ import annotations

from collections import defaultdict
from functools import lru_cache

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..assessment.weak_patterns import compute_patterns, word_opportunities
from ..bangla.normalize import tokenize_display
from ..assessment.metrics import score_of
from ..bangla.patterns import pattern_label
from ..config import get_settings
from ..models import SIMULATED_MODEL_ID, iso, Classroom, Passage, Reading, Student


def _reading_inputs(readings: list[Reading]):
    for r in readings:
        if r.status != "done" or (r.passage is not None and r.passage.language == "en"):
            continue  # grapheme patterns are Bangla-only
        yield r.id, iso(r.created_at), [m.as_metric_dict() for m in r.marks]


def student_patterns(student: Student) -> list[dict]:
    s = get_settings()
    return compute_patterns(_reading_inputs(student.readings), s.weak_min_errors, s.weak_min_readings)


def reading_summary(r: Reading) -> dict:
    m = r.metrics or {}
    return {
        "id": r.id, "created_at": iso(r.created_at), "status": r.status, "reviewed": r.reviewed,
        "passage_id": r.passage_id, "passage_title": r.passage.title if r.passage else "",
        "passage_grade": r.passage.grade if r.passage else None,
        "language": r.passage.language if r.passage else "bn",
        "score": score_of(m), "correct": m.get("correct"), "total_words": m.get("total_words"),
        "wcpm": m.get("wcpm"), "accuracy": m.get("accuracy"), "errors": m.get("errors"),
        "unsure": m.get("unsure"), "student_id": r.student_id,
        "simulated": r.model_id == SIMULATED_MODEL_ID,
    }


def student_card(st: Student) -> dict:
    done = [r for r in st.readings if r.status == "done"]
    latest = done[-1] if done else None
    pats = student_patterns(st) if done else []
    unreviewed = sum(1 for r in done if not r.reviewed)
    return {
        "id": st.id, "code": st.code, "nickname": st.nickname, "classroom_id": st.classroom_id,
        "readings": len(done),
        "latest": reading_summary(latest) if latest else None,
        "candidate_patterns": [p for p in pats if p["candidate"]][:5],
        "unreviewed": unreviewed,
        "mean_score": _mean([score_of(r.metrics) for r in done]),
        "username": st.account.username if st.account else None,
    }


def _mean(vals: list[float | None]) -> float | None:
    xs = [v for v in vals if v is not None]
    return round(sum(xs) / len(xs), 1) if xs else None


@lru_cache(maxsize=256)
def _passage_opportunities(text: str) -> tuple[tuple[str, tuple[str, ...]], ...]:
    out = []
    for _disp, norm in tokenize_display(text):
        out.append((norm, tuple(word_opportunities(norm))))
    return tuple(out)


def passage_pattern_counts(text: str) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for _w, keys in _passage_opportunities(text):
        for k in keys:
            counts[k] += 1
    return dict(counts)


def recommendations(db: Session, st: Student, pats: list[dict], limit_patterns: int = 3) -> list[dict]:
    """For each candidate weak pattern: passages that practise it and example words."""
    targets = [p for p in pats if p["candidate"]][:limit_patterns]
    if not targets:
        return []
    passages = db.scalars(select(Passage).where(Passage.active.is_(True), Passage.language == "bn")).all()
    recent = [r.passage_id for r in st.readings[-3:]]
    grade = st.classroom.grade if st.classroom else 1
    out = []
    for p in targets:
        key = p["key"]
        ranked = []
        words: dict[str, int] = {}
        for ps in passages:
            occ = 0
            for w, keys in _passage_opportunities(ps.text):
                if key in keys:
                    occ += 1
                    words[w] = words.get(w, 0) + 1
            if occ:
                # prefer passages near the class grade and not read recently
                # enough practice of the pattern matters, but reading level matters more
                score = min(occ, 6) - 3.0 * abs(ps.grade - grade) - (3 if ps.id in recent else 0)
                ranked.append((score, occ, ps))
        ranked.sort(key=lambda x: -x[0])
        practice_words = sorted(words, key=lambda w: (len(w), -words[w]))[:10]
        out.append({
            "pattern": pattern_label(key),
            "passages": [{"id": ps.id, "title": ps.title, "grade": ps.grade, "occurrences": occ}
                         for _s, occ, ps in ranked[:3]],
            "practice_words": practice_words,
        })
    return out


def student_detail(db: Session, st: Student) -> dict:
    pats = student_patterns(st)
    progress = [
        {"reading_id": r.id, "date": iso(r.created_at), "wcpm": (r.metrics or {}).get("wcpm"),
         "accuracy": (r.metrics or {}).get("accuracy"), "score": score_of(r.metrics),
         "passage": r.passage.title if r.passage else "", "language": r.passage.language if r.passage else "bn"}
        for r in st.readings if r.status == "done"
    ]
    return {
        **student_card(st),
        "classroom": {"id": st.classroom.id, "name": st.classroom.name, "grade": st.classroom.grade},
        "history": [reading_summary(r) for r in reversed(st.readings)],
        "patterns": pats,
        "progress": progress,
        "recommendations": recommendations(db, st, pats),
    }


def class_overview(db: Session, c: Classroom) -> dict:
    students = [st for st in c.students if st.active]
    cards = [student_card(st) for st in students]
    agg: dict[str, dict] = {}
    for st in students:
        for p in student_patterns(st):
            a = agg.setdefault(p["key"], {**pattern_label(p["key"]), "errors": 0, "opportunities": 0,
                                          "students_with_errors": 0, "students_candidate": 0,
                                          "students": []})
            a["errors"] += p["errors"]
            a["opportunities"] += p["opportunities"]
            a["students_with_errors"] += 1
            if p["candidate"]:
                a["students_candidate"] += 1
                a["students"].append(st.code)
    pattern_map = sorted(agg.values(), key=lambda a: (-a["students_candidate"], -a["errors"]))
    done = [r for st in students for r in st.readings if r.status == "done"]
    wcpms = [r.metrics.get("wcpm") for r in done if r.metrics and r.metrics.get("wcpm") is not None]
    accs = [r.metrics.get("accuracy") for r in done if r.metrics and r.metrics.get("accuracy") is not None]
    assessed = sum(1 for card in cards if card["readings"])
    return {
        "id": c.id, "name": c.name, "grade": c.grade, "school": c.school,
        "students": cards,
        "pattern_map": [p for p in pattern_map if p["key"] != "skip"][:30],
        "stats": {
            "students": len(students), "assessed": assessed, "readings": len(done),
            "mean_wcpm": round(sum(wcpms) / len(wcpms), 1) if wcpms else None,
            "mean_accuracy": round(sum(accs) / len(accs), 3) if accs else None,
            "mean_score": _mean([score_of(r.metrics) for r in done]),
            "unreviewed": sum(card["unreviewed"] for card in cards),
            "simulated": sum(1 for r in done if r.model_id == SIMULATED_MODEL_ID),
        },
    }
