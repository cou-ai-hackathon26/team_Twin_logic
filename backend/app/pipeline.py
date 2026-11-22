"""End-to-end assessment of one recording (Pipeline Steps 1 to 6).

Pure orchestration: takes audio + passage text, returns marks and metrics.
Used by the web service and by the benchmark scripts, so both measure the
exact same code path.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np

from .assessment import types as T
from .assessment.marking import assess, passage_words
from .assessment.metrics import compute_metrics
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
                   count_unsure_as_correct: bool = True) -> PipelineResult:
    t0 = time.perf_counter()
    q = quality_check(audio)
    if not q.ok and not skip_quality:
        return PipelineResult("porabondhu", q, True, processing_ms=int((time.perf_counter() - t0) * 1000),
                              model_id=recognizer.model_id)
    pw = passage_words(passage_text)
    logits = recognizer.logits(audio)
    lp = recognizer.log_probs(logits, th.temperature)
    rw = recognizer.greedy_decode(lp)
    ev = recognizer.expected_evidence(lp, pw)
    marks = assess(pw, rw, ev, th, variant_pairs)
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
