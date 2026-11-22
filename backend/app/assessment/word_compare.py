"""Baseline scorer: plain word comparison (systems 1 and 2 of the benchmark).

Any recognised word that differs from the passage word is an error; a missing
word is a skip. No grapheme engine, no confidence, no abstention.
"""

from __future__ import annotations

from ..alignment.sequence import align
from . import types as T


def word_compare(pw: list[T.PassageWord], rw: list[T.RecognizedWord]) -> list[T.WordMarkResult]:
    ops, _ = align([w.norm for w in pw], [r.text for r in rw], lambda a, b: 0.0 if a == b else 1.0)
    out: dict[int, T.WordMarkResult] = {}
    for op in ops:
        if op.i is None:
            continue
        w = pw[op.i]
        if op.kind == "match":
            r = rw[op.j]
            out[op.i] = T.WordMarkResult(op.i, w.display, w.norm, r.text, T.CORRECT, T.CORRECT,
                                         start=r.start, end=r.end, free_conf=r.confidence)
        elif op.kind == "sub":
            r = rw[op.j]
            out[op.i] = T.WordMarkResult(op.i, w.display, w.norm, r.text, T.MISREAD, T.MISREAD,
                                         start=r.start, end=r.end, free_conf=r.confidence)
        else:
            out[op.i] = T.WordMarkResult(op.i, w.display, w.norm, "", T.SKIPPED, T.SKIPPED)
    return [out[i] for i in range(len(pw))]
