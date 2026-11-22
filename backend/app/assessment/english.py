"""English reading assessment (for English-learning passages).

The Bangla grapheme engine does not apply to English, so English readings use
a simpler, transparent path:

1. quality check (same as Bangla),
2. Whisper in English, greedy decoding with no carried-over context,
3. word alignment where the substitution cost is the letter edit distance, so
   a near-miss ("cat" -> "cats") pairs up as a misread instead of a skip,
4. word marks: correct / misread / skipped / unsure / not reached, plus the
   same hesitation flag the Bangla path uses.

A misread that Whisper itself was not confident about is marked *unsure*
(never counted as an error) for the teacher to check.
"""

from __future__ import annotations

import re
import time
import unicodedata
from typing import Callable

import numpy as np

from ..alignment.sequence import align
from . import types as T
from .metrics import compute_metrics

_WORD_RE = re.compile(r"[^a-z0-9']+")
UNSURE_PROB = 0.45  # Whisper word probability below this -> unsure instead of misread
_NUMBERS = {"0": "zero", "1": "one", "2": "two", "3": "three", "4": "four", "5": "five", "6": "six",
            "7": "seven", "8": "eight", "9": "nine", "10": "ten", "11": "eleven", "12": "twelve"}


def normalize_english_word(word: str) -> str:
    w = unicodedata.normalize("NFKC", word).lower().replace("’", "'").replace("‘", "'")
    w = _WORD_RE.sub("", w).strip("'")
    return _NUMBERS.get(w, w)


def english_words(text: str) -> list[T.PassageWord]:
    """Passage words with punctuation attached to the previous word for display."""
    out: list[T.PassageWord] = []
    for raw in text.split():
        norm = normalize_english_word(raw)
        if not norm:
            if out:
                out[-1].display += " " + raw
            continue
        out.append(T.PassageWord(index=len(out), display=raw, norm=norm, units=[]))
    return out


def _edit_distance(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i] + [0] * len(b)
        for j, cb in enumerate(b, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb))
        prev = cur
    return prev[-1]


def word_distance(a: str, b: str) -> float:
    """Normalised letter distance in [0, 1]; apostrophes ignored."""
    a, b = a.replace("'", ""), b.replace("'", "")
    if a == b:
        return 0.0
    return _edit_distance(a, b) / max(len(a), len(b), 1)


def _sub_cost(a: str, b: str) -> float:
    d = word_distance(a, b)
    # unrelated words cost more than a delete + insert, so they do not pair up
    return d * 1.6 if d < 0.75 else 2.5


def assess_english(pw: list[T.PassageWord], heard: list[tuple[str, float, float, float]],
                   th: T.Thresholds) -> list[T.WordMarkResult]:
    rw = [(normalize_english_word(w), s, e, p) for w, s, e, p in heard]
    rw = [x for x in rw if x[0]]
    ops, _ = align([w.norm for w in pw], [r[0] for r in rw], _sub_cost)

    marks: dict[int, T.WordMarkResult] = {}
    pending_insert: list[str] = []
    for op in ops:
        if op.i is None:  # extra word the child said
            pending_insert.append(rw[op.j][0])
            continue
        w = pw[op.i]
        if op.j is None:
            m = T.WordMarkResult(op.i, w.display, w.norm, "", T.SKIPPED, T.SKIPPED,
                                 note_en="Not heard in the reading")
        else:
            text, start, end, prob = rw[op.j]
            if word_distance(w.norm, text) == 0.0:
                m = T.WordMarkResult(op.i, w.display, w.norm, text, T.CORRECT, T.CORRECT,
                                     start=start, end=end, free_conf=round(prob, 3))
            else:
                status = T.UNSURE if prob < UNSURE_PROB else T.MISREAD
                m = T.WordMarkResult(op.i, w.display, w.norm, text, status, T.MISREAD, start=start, end=end,
                                     free_conf=round(prob, 3), note_en=f'Read "{w.norm}" as "{text}"')
        if pending_insert:
            m.inserted = pending_insert
            m.flags.append(T.FLAG_EXTRA)
            pending_insert = []
        marks[op.i] = m
    out = [marks[i] for i in range(len(pw))]

    # trailing run of skipped words = the child stopped: not reached, not errors
    run = 0
    for m in reversed(out):
        if m.status != T.SKIPPED:
            break
        run += 1
    if run >= th.not_reached_min_run:
        for m in out[len(out) - run:]:
            m.status = m.raw_status = T.NOT_REACHED
            m.note_en = "Not reached"

    # hesitation: long pause before a word
    last_end: float | None = None
    for m in out:
        if m.start is not None:
            if last_end is not None and m.start - last_end >= th.hesitation_sec:
                m.flags.append(T.FLAG_HESITATION)
            last_end = m.end
    return out


def run_english(audio: np.ndarray, passage_text: str, load_whisper: Callable, th: T.Thresholds,
                skip_quality: bool = False, count_unsure_as_correct: bool = True):
    """Same contract as ``pipeline.run_porabondhu``; the model loads only if the audio passes the check."""
    from ..pipeline import PipelineResult
    from ..speech.audio import quality_check

    t0 = time.perf_counter()
    q = quality_check(audio)
    if not q.ok and not skip_quality:
        return PipelineResult("english", q, True, processing_ms=int((time.perf_counter() - t0) * 1000),
                              model_id="whisper")
    whisper = load_whisper()
    text, heard = whisper.transcribe_english(audio)
    marks = assess_english(english_words(passage_text), heard, th)
    metrics = compute_metrics([m.to_dict() for m in marks], q.duration_sec, count_unsure_as_correct)
    return PipelineResult(system="english", quality=q, rejected=False, transcript=text, marks=marks,
                          metrics=metrics, forced_alignment_ok=False,
                          processing_ms=int((time.perf_counter() - t0) * 1000),
                          model_id=f"whisper-{getattr(whisper, 'size', '')} (en)")
