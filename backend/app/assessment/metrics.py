"""Fluency measures (WCPM, accuracy) computed from final word marks.

Works on plain dicts so it can run both on fresh results and on database rows
after teacher corrections.
"""

from __future__ import annotations

from typing import Iterable, Mapping

from . import types as T


def final_status(mark: Mapping) -> str:
    return mark.get("teacher_status") or mark["status"]


SCORE_MAX = 10


def mark_out_of_10(correct: int | None, total_words: int | None) -> float | None:
    """Mark for one reading test: words read correctly out of all passage words, scaled to 10.

    Skipped, misread and not-reached words all earn nothing, so stopping early
    lowers the mark. Rounded to one decimal place.
    """
    if not total_words or correct is None:
        return None
    return round(SCORE_MAX * max(0, min(correct, total_words)) / total_words, 1)


def score_of(metrics: Mapping | None) -> float | None:
    """Mark from a stored metrics dict (older readings were saved before marks existed)."""
    if not metrics:
        return None
    if metrics.get("score") is not None:
        return metrics["score"]
    return mark_out_of_10(metrics.get("correct"), metrics.get("total_words"))


def compute_metrics(marks: Iterable[Mapping], audio_duration: float | None = None,
                    count_unsure_as_correct: bool = True) -> T.Metrics:
    marks = list(marks)
    statuses = [final_status(m) for m in marks]
    total = len(marks)
    not_reached = statuses.count(T.NOT_REACHED)
    attempted = total - not_reached
    misread = statuses.count(T.MISREAD)
    skipped = statuses.count(T.SKIPPED)
    unsure = statuses.count(T.UNSURE)
    correct = statuses.count(T.CORRECT) + (unsure if count_unsure_as_correct else 0)
    errors = misread + skipped
    reps = sum(1 for m in marks if T.FLAG_REPEATED in (m.get("flags") or []))
    hes = sum(1 for m in marks if T.FLAG_HESITATION in (m.get("flags") or []))

    starts = [m.get("start") for m, s in zip(marks, statuses) if s != T.NOT_REACHED and m.get("start") is not None]
    ends = [m.get("end") for m, s in zip(marks, statuses) if s != T.NOT_REACHED and m.get("end") is not None]
    reading_time: float | None = None
    if starts and ends:
        reading_time = max(ends) - min(starts)
    if (reading_time is None or reading_time < 1.0) and audio_duration:
        reading_time = audio_duration
    if reading_time is not None and reading_time < 1.0:
        reading_time = None

    accuracy = (correct / attempted) if attempted else None
    wcpm = (correct / reading_time * 60.0) if reading_time else None
    return T.Metrics(
        total_words=total, attempted_words=attempted, correct=correct, errors=errors, misread=misread,
        skipped=skipped, unsure=unsure, not_reached=not_reached, repetitions=reps, hesitations=hes,
        reading_time_sec=round(reading_time, 2) if reading_time else None,
        accuracy=round(accuracy, 4) if accuracy is not None else None,
        wcpm=round(wcpm, 1) if wcpm is not None else None,
        score=mark_out_of_10(correct, total),
    )
