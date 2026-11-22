"""Reading lifecycle: upload -> queued -> processing -> done | rejected | failed.

Model inference runs in a single background worker thread so that the CPU is
never shared by two recordings at once and the API stays responsive.
"""

from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..assessment.english import run_english
from ..assessment.metrics import compute_metrics
from ..config import get_settings, load_thresholds
from ..db import SessionLocal
from ..models import AcceptedVariant, Reading, WordMark
from ..pipeline import run_ctc_word_compare, run_porabondhu, run_whisper_word_compare
from ..speech.audio import load_audio_bytes, load_audio_file, save_wav
from ..speech.registry import get_ctc, get_whisper
from ..speech.registry import status as model_status
from . import progress

log = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="pb-worker")


def variant_pairs(db: Session) -> set[tuple[str, str]]:
    return {(v.word, v.variant) for v in db.scalars(select(AcceptedVariant))}


def store_audio(reading: Reading, data: bytes) -> float:
    """Decode the upload once and keep a 16 kHz WAV copy for processing and review."""
    s = get_settings()
    audio = load_audio_bytes(data)
    path = s.audio_dir / f"reading_{reading.id}.wav"
    save_wav(str(path), audio)
    reading.audio_path = str(path)
    return len(audio) / 16000


def delete_audio(reading: Reading) -> None:
    if reading.audio_path and os.path.exists(reading.audio_path):
        try:
            os.remove(reading.audio_path)
        except OSError:
            log.warning("could not delete %s", reading.audio_path)
    reading.audio_path = None


def purge_old_audio(now: datetime | None = None) -> int:
    """Privacy: delete recordings older than PB_AUDIO_RETENTION_DAYS unless the teacher chose to keep
    them. Marks and metrics stay; only the voice is removed. Returns how many files were deleted."""
    days = get_settings().audio_retention_days
    if days <= 0:
        return 0
    cutoff = (now or datetime.now(timezone.utc)) - timedelta(days=days)
    db = SessionLocal()
    try:
        rows = db.scalars(select(Reading).where(Reading.audio_path.is_not(None), Reading.keep_audio.is_(False),
                                                Reading.status.not_in(["queued", "processing"]))).all()
        n = 0
        for r in rows:
            created = r.created_at if r.created_at.tzinfo else r.created_at.replace(tzinfo=timezone.utc)
            if created < cutoff:
                delete_audio(r)
                n += 1
        db.commit()
        return n
    finally:
        db.close()


def reading_language(r: Reading) -> str:
    return (r.passage.language if r.passage is not None else None) or "bn"


def submit(reading_id: int) -> None:
    _executor.submit(_process_reading, reading_id)


def submit_comparison(reading_id: int) -> None:
    _executor.submit(_process_comparison, reading_id)


def recompute_metrics(reading: Reading) -> None:
    s = get_settings()
    m = compute_metrics([w.as_metric_dict() for w in reading.marks], reading.duration_sec,
                        s.count_unsure_as_correct)
    reading.metrics = m.to_dict()


def store_marks(r: Reading, marks) -> None:
    """Replace the reading's word marks with fresh engine results (``WordMarkResult`` list)."""
    r.marks.clear()
    for m in marks:
        err_pats: list[str] = []
        for u in m.units:
            for e in u.errors:
                if e["pattern"] not in err_pats:
                    err_pats.append(e["pattern"])
        r.marks.append(WordMark(
            index=m.index, display=m.display, expected=m.expected, heard=m.heard, status=m.status,
            raw_status=m.raw_status, flags=m.flags, inserted=m.inserted, start=m.start, end=m.end,
            free_conf=m.free_conf, gop=m.gop, units=[u.__dict__ for u in m.units],
            patterns=m.patterns, error_patterns=err_pats, note_bn=m.note_bn, note_en=m.note_en))


def _process_reading(reading_id: int) -> None:
    db = SessionLocal()
    try:
        r = db.get(Reading, reading_id)
        if r is None:
            return
        r.status = "processing"
        r.error = None
        db.commit()
        try:
            if not r.audio_path or not os.path.exists(r.audio_path):
                raise RuntimeError("Audio file is missing")
            audio = load_audio_file(r.audio_path)
            th = load_thresholds()
            unsure_ok = get_settings().count_unsure_as_correct
            lang = reading_language(r)
            if lang == "en":
                progress.set_stage(reading_id, "listening")
                res = run_english(audio, r.passage_text, get_whisper, th, count_unsure_as_correct=unsure_ok)
            else:
                if model_status().get("ctc", {}).get("state") != "ready":
                    progress.set_stage(reading_id, "loading")
                ctc = get_ctc()
                res = run_porabondhu(audio, r.passage_text, ctc, th, variant_pairs(db),
                                     count_unsure_as_correct=unsure_ok,
                                     on_stage=lambda st: progress.set_stage(reading_id, st))
            progress.finish(reading_id, lang, res.quality.duration_sec, res.processing_ms)
            r.quality = res.quality.to_dict()
            r.duration_sec = res.quality.duration_sec
            r.processing_ms = res.processing_ms
            r.model_id = res.model_id
            r.thresholds = th.to_dict()
            r.processed_at = datetime.now(timezone.utc)
            if res.rejected:
                r.status = "rejected"
                delete_audio(r)
                db.commit()
                return
            r.transcript = res.transcript
            r.forced_alignment_ok = res.forced_alignment_ok
            store_marks(r, res.marks)
            r.metrics = res.metrics.to_dict() if res.metrics else None
            r.status = "done"
            db.commit()
        except Exception as e:  # noqa: BLE001
            log.exception("reading %s failed", reading_id)
            db.rollback()
            r = db.get(Reading, reading_id)
            if r is not None:
                r.status = "failed"
                r.error = str(e)[:2000]
                db.commit()
    finally:
        progress.clear(reading_id)
        db.close()


def _process_comparison(reading_id: int) -> None:
    db = SessionLocal()
    try:
        r = db.get(Reading, reading_id)
        if r is None:
            return
        r.comparison_status = "processing"
        db.commit()
        out: dict = {"systems": {}}
        try:
            if not r.audio_path or not os.path.exists(r.audio_path):
                raise RuntimeError("Audio was not kept for this reading, so it cannot be re-analysed")
            audio = load_audio_file(r.audio_path)
            runners = [("ctc_word", lambda: run_ctc_word_compare(audio, r.passage_text, get_ctc())),
                       ("whisper_word", lambda: run_whisper_word_compare(audio, r.passage_text, get_whisper()))]
            for name, fn in runners:
                try:
                    res = fn()
                    out["systems"][name] = {
                        "transcript": res.transcript, "processing_ms": res.processing_ms, "model_id": res.model_id,
                        "metrics": res.metrics.to_dict() if res.metrics else None,
                        "marks": [{"index": m.index, "status": m.status, "heard": m.heard} for m in res.marks],
                    }
                except Exception as e:  # noqa: BLE001
                    log.exception("comparison %s failed", name)
                    out["systems"][name] = {"error": str(e)[:500]}
            r.comparison = out
            r.comparison_status = "done"
        except Exception as e:  # noqa: BLE001
            r.comparison = {"error": str(e)}
            r.comparison_status = "failed"
        db.commit()
    finally:
        db.close()


def requeue_unfinished() -> int:
    """On start-up, put readings interrupted by a shutdown back in the queue."""
    db = SessionLocal()
    try:
        rows = db.scalars(select(Reading).where(Reading.status.in_(["queued", "processing"]))).all()
        for r in rows:
            r.status = "queued"
        db.commit()
        for r in rows:
            submit(r.id)
        return len(rows)
    finally:
        db.close()
