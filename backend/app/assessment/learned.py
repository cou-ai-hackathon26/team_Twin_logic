"""Trained word-level error classifier (see scripts/word_classifier.py for how it is trained and tested).

The rule-based decision compares two numbers with hand-set thresholds. This model combines more of the
evidence the speech model already gives for each flagged word. It only re-decides words the decoder
flagged (raw status misread / skipped); everything else is untouched. Uncertain words stay "unsure",
so the teacher still decides them.
"""

from __future__ import annotations

import json
import math
from functools import lru_cache

from ..config import RESULTS_DIR
from . import types as T

FEATURES = [
    "is_skip", "err_free", "err_free_missing", "word_gop", "word_gop_missing", "min_unit_gop", "mean_unit_gop",
    "frac_units_wrong", "n_units", "n_units_wrong", "spelling_only", "free_conf", "has_heard", "duration",
    "repeated_or_partial", "extra_word", "unit_del_frac", "unit_ins_count",
]


def _num(x, default: float) -> float:
    return default if x is None else float(x)


def features(m: dict) -> list[float]:
    """Numbers describing one marked word (a WordMarkResult as dict)."""
    units = m.get("units") or []
    wrong = [u for u in units if u.get("op") in ("sub", "del", "ins")]
    exp_units = [u for u in units if u.get("op") != "ins"]
    gops = [u["gop"] for u in wrong if u.get("gop") is not None]
    flags = m.get("flags") or []
    dur = (m["end"] - m["start"]) if m.get("start") is not None and m.get("end") is not None else 0.0
    return [
        1.0 if m.get("raw_status") == T.SKIPPED else 0.0,
        _num(m.get("err_free"), 0.5), 1.0 if m.get("err_free") is None else 0.0,
        max(-15.0, min(5.0, _num(m.get("gop"), -6.0))), 1.0 if m.get("gop") is None else 0.0,
        max(-15.0, min(5.0, min(gops))) if gops else 0.0,
        max(-15.0, min(5.0, sum(gops) / len(gops))) if gops else 0.0,
        len(wrong) / max(len(exp_units), 1), float(len(exp_units)), float(len(wrong)),
        1.0 if units and not wrong and any(u.get("op") == "spelling" for u in units) else 0.0,
        _num(m.get("free_conf"), 0.0), 1.0 if m.get("heard") else 0.0, min(dur, 5.0),
        1.0 if (T.FLAG_REPEATED in flags or T.FLAG_PARTIAL in flags) else 0.0,
        1.0 if T.FLAG_EXTRA in flags else 0.0,
        sum(1 for u in units if u.get("op") == "del") / max(len(exp_units), 1),
        float(sum(1 for u in units if u.get("op") == "ins")),
    ]


@lru_cache(maxsize=1)
def load_model() -> dict | None:
    """The trained model, only if its held-out test showed it is better than the rules."""
    path = RESULTS_DIR / "word_classifier.json"
    if not path.exists():
        return None
    rep = json.loads(path.read_text(encoding="utf-8"))
    if not rep.get("use_in_app") or rep.get("features") != FEATURES:
        return None
    return {**rep["model"], **rep["decision"]}


def probability(model: dict, m: dict) -> float:
    z = model["bias"]
    for x, mu, sd, w in zip(features(m), model["mean"], model["std"], model["weights"]):
        z += w * (x - mu) / sd
    return 1 / (1 + math.exp(-max(-30.0, min(30.0, z))))


def cutoffs(model: dict, th: T.Thresholds | None = None) -> tuple[float, float]:
    cut = th.word_model_cut if th is not None else None
    return (cut, cut) if cut is not None else (model["lo"], model["hi"])


def decide(model: dict, m: dict, lo: float, hi: float) -> str:
    """Decision for one flagged word (dict form), as used both live and when replaying reviews."""
    p = probability(model, m)
    if p >= hi:
        return m["raw_status"]
    return T.CORRECT if p <= lo else T.UNSURE


def apply(marks: list[T.WordMarkResult], model: dict | None = None,
          th: T.Thresholds | None = None) -> list[T.WordMarkResult]:
    """Re-decide flagged words with the trained model (in place). No model -> rules stay."""
    model = model or load_model()
    if model is None:
        return marks
    lo, hi = cutoffs(model, th)
    for m in marks:
        if m.status == T.NOT_REACHED or m.raw_status == T.CORRECT:
            continue
        new = decide(model, m.to_dict(), lo, hi)
        if new == m.status:
            continue
        m.status = new
        if new == T.CORRECT:
            m.patterns = []
            m.note_bn, m.note_en = "ঠিক পড়েছে (প্রশিক্ষিত মডেল)", "Read correctly (trained model)"
        elif new == T.UNSURE:
            m.patterns = []
            m.note_bn, m.note_en = "নিশ্চিত নয়, শুনে দেখুন", "Not sure; please listen"
        elif new == T.SKIPPED:
            m.patterns = ["skip"]
            m.note_bn, m.note_en = "শব্দটি পড়া হয়নি", "Word was not read"
        else:
            pats: list[str] = []
            for u in m.units:
                for er in u.errors:
                    if er.get("pattern") and er["pattern"] not in pats:
                        pats.append(er["pattern"])
            m.patterns = pats
            m.note_bn, m.note_en = "ভুল পড়েছে", "Misread"
    return marks
