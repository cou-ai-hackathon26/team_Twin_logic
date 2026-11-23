"""Learning from teacher reviews: PoraBondhu adapts to each school without retraining a model.

Every finalised review is a labelled example: the teacher's final decision for each word. Two things
are learned from them, both transparent and reversible:

1. **Accepted pronunciations.** When teachers mark the same heard form of a word as correct in at
   least ``VARIANT_MIN_READINGS`` different readings (e.g. a regional pronunciation), that form is
   added as an accepted variant and is no longer flagged.
2. **Decision thresholds.** Each word's decision depends on three thresholds (free_high, gop_high,
   gop_low). The evidence behind every decision is stored, so the decisions can be *replayed* with
   other thresholds. After enough reviews we search for thresholds that agree better with the
   teachers' final marks while keeping false alarms (against the teacher) at or below 5%. A change is
   adopted only if it improves agreement; the previous thresholds are kept for one-click undo.

Only real recordings count (simulated demo readings are excluded), and an "unsure" word the teacher
left unsure gives no label.
"""

from __future__ import annotations

import itertools
import json
import logging
import threading
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..assessment import types as T
from ..config import get_settings, load_thresholds, save_thresholds
from ..models import SIMULATED_MODEL_ID, AcceptedVariant, Reading, WordMark

log = logging.getLogger(__name__)
LEARNED_NOTE = "learned from teacher reviews"
VARIANT_MIN_READINGS = 3
MIN_READINGS, MIN_WORDS = 10, 200
MAX_FALSE_ALARM = 0.05
FREE_HIGH = (0.2, 0.3, 0.4, 0.5, 0.6, 0.7)
GOP_HIGH = (0.1, 0.25, 0.5, 1.0, 1.5)
GOP_LOW = (-6.0, -5.0, -4.0, -3.0, -2.0, -1.0)
_lock = threading.Lock()


def replay(m: WordMark, th: T.Thresholds) -> str:
    """The decision the marking rules would make for this word with thresholds ``th``."""
    if m.raw_status == T.MISREAD:
        free = m.err_free if m.err_free is not None else m.free_conf
        if m.gop is not None and m.gop >= th.gop_high:
            return T.CORRECT
        if free is not None and m.gop is not None and free >= th.free_high and m.gop <= th.gop_low:
            return T.MISREAD
        return T.UNSURE
    if m.raw_status == T.SKIPPED and not m.heard:
        return T.SKIPPED if m.gop is not None and m.gop <= th.gop_low else T.UNSURE
    return m.status


def _reviewed_marks(db: Session) -> tuple[list[WordMark], int]:
    readings = db.scalars(select(Reading).where(Reading.reviewed.is_(True), Reading.status == "done",
                                                Reading.model_id.is_distinct_from(SIMULATED_MODEL_ID))).all()
    marks = [m for r in readings if (r.passage is None or r.passage.language != "en") for m in r.marks
             if m.final_status in (T.CORRECT, T.MISREAD, T.SKIPPED)  # unsure left unsure = no label
             and not (m.raw_status == T.MISREAD and m.err_free is None)]  # older marks can't be replayed exactly
    return marks, len(readings)


def score(marks: list[WordMark], th: T.Thresholds) -> dict:
    tp = fp = fn = hc = un = 0
    for m in marks:
        sys_s, teacher = replay(m, th), m.final_status
        te, pe = teacher in (T.MISREAD, T.SKIPPED), sys_s in (T.MISREAD, T.SKIPPED)
        tp += te and pe
        fp += pe and not te
        fn += te and not pe
        hc += not te
        un += sys_s == T.UNSURE
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    return {"words": len(marks), "precision": round(prec, 4), "recall": round(rec, 4),
            "f1": round(2 * prec * rec / (prec + rec), 4) if prec + rec else 0.0,
            "false_alarm": round(fp / hc, 4) if hc else 0.0, "unsure_rate": round(un / max(len(marks), 1), 4)}


def _key(s: dict) -> tuple:
    ok = s["false_alarm"] <= MAX_FALSE_ALARM
    return (ok, s["f1"] if ok else -s["false_alarm"], -s["unsure_rate"])


def search(marks: list[WordMark], current: T.Thresholds) -> tuple[T.Thresholds, dict]:
    """Thresholds that agree best with the teachers' final marks (false alarms at most 5%)."""
    best, best_s = current, score(marks, current)
    for fh, gh, gl in itertools.product(FREE_HIGH, GOP_HIGH, GOP_LOW):
        if gl >= gh:
            continue
        th = T.Thresholds(**{**current.to_dict(), "free_high": fh, "gop_high": gh, "gop_low": gl})
        s = score(marks, th)
        if _key(s) > _key(best_s):
            best, best_s = th, s
    return best, best_s


def learn_thresholds(db: Session, force: bool = False) -> dict:
    marks, n_readings = _reviewed_marks(db)
    current = load_thresholds()
    if not force and (n_readings < MIN_READINGS or len(marks) < MIN_WORDS):
        return {"changed": False, "reason": f"needs {MIN_READINGS} reviewed readings and {MIN_WORDS} decided words "
                                            f"(have {n_readings} and {len(marks)})"}
    before = score(marks, current)
    best, best_s = search(marks, current)
    if best == current:
        return {"changed": False, "reason": "current thresholds already agree best with the teachers", "stats": before}
    history = _history_path()
    hist = json.loads(history.read_text(encoding="utf-8")) if history.exists() else []
    hist.append({"at": datetime.now(timezone.utc).isoformat(), "previous": current.to_dict()})
    history.write_text(json.dumps(hist[-20:], indent=2), encoding="utf-8")
    save_thresholds(best, {"tuned_at": datetime.now(timezone.utc).isoformat(), "source": LEARNED_NOTE,
                           "reviewed_readings": n_readings, "words": len(marks), "before": before, "after": best_s})
    log.info("thresholds learned from %d reviewed readings: %s -> %s", n_readings, before, best_s)
    return {"changed": True, "before": before, "after": best_s, "thresholds": best.to_dict()}


def learn_variants(db: Session) -> list[dict]:
    """Add heard forms that teachers repeatedly accepted as correct for a word."""
    seen: dict[tuple[str, str], set[int]] = defaultdict(set)
    for m in db.scalars(select(WordMark).join(Reading).where(
            WordMark.teacher_status == T.CORRECT, WordMark.status == T.MISREAD, Reading.reviewed.is_(True),
            Reading.model_id.is_distinct_from(SIMULATED_MODEL_ID))):
        if m.heard and m.heard != m.expected and " " not in m.heard:
            seen[(m.expected, m.heard)].add(m.reading_id)
    have = {(v.word, v.variant) for v in db.scalars(select(AcceptedVariant))}
    added = []
    for (word, heard), rids in seen.items():
        if len(rids) >= VARIANT_MIN_READINGS and (word, heard) not in have:
            db.add(AcceptedVariant(word=word, variant=heard, note=f"{LEARNED_NOTE} ({len(rids)} readings)"))
            added.append({"word": word, "variant": heard, "readings": len(rids)})
    if added:
        db.commit()
    return added


def learn(db: Session, force: bool = False) -> dict:
    with _lock:
        return {"variants_added": learn_variants(db), "thresholds": learn_thresholds(db, force)}


def learn_in_background(force: bool = False) -> None:
    from ..db import SessionLocal

    def run():
        db = SessionLocal()
        try:
            learn(db, force)
        except Exception:  # noqa: BLE001
            log.exception("learning from reviews failed")
        finally:
            db.close()

    threading.Thread(target=run, daemon=True, name="pb-learning").start()


def undo_thresholds() -> dict:
    history = _history_path()
    hist = json.loads(history.read_text(encoding="utf-8")) if history.exists() else []
    if not hist:
        return {"undone": False}
    last = hist.pop()
    save_thresholds(T.Thresholds.from_dict(last["previous"]), {"restored_at": datetime.now(timezone.utc).isoformat(),
                                                                "source": "undo of a learned change"})
    history.write_text(json.dumps(hist, indent=2), encoding="utf-8")
    return {"undone": True, "thresholds": last["previous"]}


def reset_learning(db: Session) -> dict:
    """Demo reset: forget learned variants and go back to the published thresholds."""
    n = 0
    for v in db.scalars(select(AcceptedVariant).where(AcceptedVariant.note.like(f"{LEARNED_NOTE}%"))):
        db.delete(v)
        n += 1
    db.commit()
    s = get_settings()
    meta = {}
    if s.thresholds_path.exists():
        meta = json.loads(s.thresholds_path.read_text(encoding="utf-8")).get("_meta", {}) or {}
        if meta.get("source") in (LEARNED_NOTE, "undo of a learned change"):
            s.thresholds_path.unlink()  # falls back to results/thresholds.json (the evaluated settings)
    _history_path().unlink(missing_ok=True)
    return {"learned_variants_removed": n}


def status(db: Session) -> dict:
    marks, n_readings = _reviewed_marks(db)
    th = load_thresholds()
    s = get_settings()
    meta = {}
    if s.thresholds_path.exists():
        meta = json.loads(s.thresholds_path.read_text(encoding="utf-8")).get("_meta", {}) or {}
    learned = [{"word": v.word, "variant": v.variant, "note": v.note}
               for v in db.scalars(select(AcceptedVariant).where(AcceptedVariant.note.like(f"{LEARNED_NOTE}%")))]
    hist = json.loads(_history_path().read_text(encoding="utf-8")) if _history_path().exists() else []
    return {"reviewed_readings": n_readings, "decided_words": len(marks), "needs": {"readings": MIN_READINGS,
                                                                                      "words": MIN_WORDS},
            "agreement_now": score(marks, th) if marks else None, "thresholds": th.to_dict(),
            "thresholds_source": meta.get("source", "published evaluation (results/thresholds.json)"),
            "last_learned": meta if meta.get("source") == LEARNED_NOTE else None,
            "learned_variants": learned, "can_undo": bool(hist)}


def _history_path():
    return get_settings().data_dir / "thresholds_history.json"
