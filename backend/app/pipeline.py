"""End-to-end assessment of one recording (Pipeline Steps 1 to 6).

Pure orchestration: takes audio + passage text, returns marks and metrics.
Used by the web service and by the benchmark scripts, so both measure the
exact same code path.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np

from .assessment import learned
from .assessment import types as T
from .assessment.marking import assess, passage_words
from .assessment.metrics import compute_metrics
from .assessment.robust import GuardOptions, apply_guards
from .assessment.word_compare import word_compare
from .speech.audio import QualityReport, quality_check


@dataclass
class PipelineResult:
    system: str
    quality: QualityReport
    rejected: bool
    transcript: str = ""
    marks: list[T.WordMarkResult] = field(default_factory=list)
    metrics: T.Metrics | None = None
    forced_alignment_ok: bool = False
    processing_ms: int = 0
    model_id: str = ""

    def to_dict(self) -> dict:
        return {
            "system": self.system,
            "quality": self.quality.to_dict(),
            "rejected": self.rejected,
            "transcript": self.transcript,
            "marks": [m.to_dict() for m in self.marks],
            "metrics": self.metrics.to_dict() if self.metrics else None,
            "forced_alignment_ok": self.forced_alignment_ok,
            "processing_ms": self.processing_ms,
            "model_id": self.model_id,
        }


def run_porabondhu(audio: np.ndarray, passage_text: str, recognizer, th: T.Thresholds,
                   variant_pairs: set[tuple[str, str]] | None = None, skip_quality: bool = False,
                   count_unsure_as_correct: bool = True,
                   on_stage: Callable[[str], None] | None = None,
                   use_word_model: bool = True, guards: GuardOptions | None = None) -> PipelineResult:
    """``guards`` = None uses the default trust guards; pass GuardOptions(False, False, False) to switch
    them off (the published FLEURS benchmark was measured before the guards existed)."""
    stage = on_stage or (lambda _s: None)
    t0 = time.perf_counter()
    stage("quality")
    q = quality_check(audio)
    if not q.ok and not skip_quality:
        return PipelineResult("porabondhu", q, True, processing_ms=int((time.perf_counter() - t0) * 1000),
                              model_id=recognizer.model_id)
    pw = passage_words(passage_text)
    stage("listening")
    logits = recognizer.logits(audio)
    lp = recognizer.log_probs(logits, th.temperature)
    rw = recognizer.greedy_decode(lp)
    stage("aligning")
    ev = recognizer.expected_evidence(lp, pw)
    stage("diagnosing")
    marks = assess(pw, rw, ev, th, variant_pairs)
    if use_word_model:
        learned.apply(marks, th=th)  # trained word classifier, if its held-out test beat the rules
    apply_guards(marks, audio, pw, guards)  # regional accent, background noise, odd words
    metrics = compute_metrics([m.to_dict() for m in marks], q.duration_sec, count_unsure_as_correct)
    return PipelineResult(
        system="porabondhu", quality=q, rejected=False, transcript=" ".join(w.text for w in rw),
        marks=marks, metrics=metrics, forced_alignment_ok=ev is not None,
        processing_ms=int((time.perf_counter() - t0) * 1000), model_id=recognizer.model_id,
    )


def run_ctc_word_compare(audio: np.ndarray, passage_text: str, recognizer) -> PipelineResult:
    t0 = time.perf_counter()
    q = quality_check(audio)
    pw = passage_words(passage_text)
    lp = recognizer.log_probs(recognizer.logits(audio))
    rw = recognizer.greedy_decode(lp)
    marks = word_compare(pw, rw)
    metrics = compute_metrics([m.to_dict() for m in marks], q.duration_sec)
    return PipelineResult("ctc_word", q, False, " ".join(w.text for w in rw), marks, metrics, False,
                          int((time.perf_counter() - t0) * 1000), recognizer.model_id)


def run_whisper_word_compare(audio: np.ndarray, passage_text: str, whisper) -> PipelineResult:
    t0 = time.perf_counter()
    q = quality_check(audio)
    pw = passage_words(passage_text)
    text, rw = whisper.transcribe(audio)
    marks = word_compare(pw, rw)
    metrics = compute_metrics([m.to_dict() for m in marks], q.duration_sec)
    return PipelineResult("whisper_word", q, False, text, marks, metrics, False,
                          int((time.perf_counter() - t0) * 1000), f"whisper-{whisper.size}")
