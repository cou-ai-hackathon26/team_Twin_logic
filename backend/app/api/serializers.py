from __future__ import annotations

import os

from ..assessment.metrics import score_of
from ..bangla.patterns import pattern_label
from ..models import iso, Passage, Reading, WordMark
from ..services import progress
from ..services.analytics import passage_pattern_counts


def passage_out(p: Passage, with_patterns: bool = False) -> dict:
    d = {"id": p.id, "code": p.code, "title": p.title, "grade": p.grade, "language": p.language or "bn",
         "text": p.text, "active": p.active, "created_at": iso(p.created_at), "word_count": len(p.text.split())}
    if with_patterns and p.language == "en":
        d["patterns"] = []
    elif with_patterns:
        counts = passage_pattern_counts(p.text)
        focus = [k for k in counts if not k.startswith(("letter:", "vowel:"))]
        focus.sort(key=lambda k: -counts[k])
        d["patterns"] = [{**pattern_label(k), "count": counts[k]} for k in focus[:24]]
    return d


def mark_out(m: WordMark) -> dict:
    return {
        "id": m.id, "index": m.index, "display": m.display, "expected": m.expected, "heard": m.heard,
        "status": m.status, "raw_status": m.raw_status, "teacher_status": m.teacher_status,
        "final_status": m.final_status, "flags": m.flags or [], "inserted": m.inserted or [],
        "start": m.start, "end": m.end, "free_conf": m.free_conf, "gop": m.gop, "units": m.units or [],
        "patterns": [pattern_label(k) for k in (m.error_patterns or [])],
        "note_bn": m.note_bn, "note_en": m.note_en,
    }


def reading_out(r: Reading, with_marks: bool = True) -> dict:
    d = {
        "id": r.id, "student_id": r.student_id, "passage_id": r.passage_id, "status": r.status,
        "created_at": iso(r.created_at),
        "processed_at": iso(r.processed_at),
        "error": r.error, "quality": r.quality, "transcript": r.transcript,
        "metrics": {**r.metrics, "score": score_of(r.metrics)} if r.metrics else None,
        "score": score_of(r.metrics), "language": (r.passage.language if r.passage else None) or "bn",
        "duration_sec": r.duration_sec, "processing_ms": r.processing_ms, "model_id": r.model_id,
        "thresholds": r.thresholds, "forced_alignment_ok": r.forced_alignment_ok,
        "has_audio": bool(r.audio_path and os.path.exists(r.audio_path)), "keep_audio": r.keep_audio,
        "reviewed": r.reviewed, "reviewed_at": iso(r.reviewed_at),
        "comparison": r.comparison, "comparison_status": r.comparison_status,
        "passage": {"id": r.passage.id, "title": r.passage.title, "grade": r.passage.grade,
                    "language": r.passage.language} if r.passage else None,
        "student": {"id": r.student.id, "code": r.student.code, "nickname": r.student.nickname,
                    "classroom_id": r.student.classroom_id} if r.student else None,
    }
    if r.status in ("queued", "processing"):
        d["progress"] = progress.snapshot(r.id, d["language"], r.duration_sec)
    if with_marks:
        d["marks"] = [mark_out(m) for m in r.marks]
    return d
