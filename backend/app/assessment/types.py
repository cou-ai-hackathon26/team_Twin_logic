"""Data types shared by the assessment engine (pure Python, no ML imports)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from ..bangla.segment import Unit

# Word status values
CORRECT = "correct"
MISREAD = "misread"
SKIPPED = "skipped"
UNSURE = "unsure"
NOT_REACHED = "not_reached"
STATUSES = (CORRECT, MISREAD, SKIPPED, UNSURE, NOT_REACHED)
ERROR_STATUSES = (MISREAD, SKIPPED)

# Word flags (do not change the status)
FLAG_REPEATED = "repeated"
FLAG_HESITATION = "hesitation"
FLAG_PARTIAL = "partial_attempt"
FLAG_EXTRA = "extra_word"
FLAG_SPELLING_ONLY = "spelling_only"
FLAG_VARIANT = "accepted_variant"


@dataclass
class Thresholds:
    """Decision thresholds. Tuned on tuning speakers only, then frozen."""

    free_high: float = 0.70  # free-decoding confidence counted as "high"
    gop_high: float = 1.0  # expected-text score counted as "high" (nats)
    gop_low: float = -0.5  # expected-text score counted as "low" (nats)
    temperature: float = 1.0  # logit temperature for calibration
    hesitation_sec: float = 3.0
    not_reached_min_run: int = 3

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Thresholds":
        known = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**known)


@dataclass
class PassageWord:
    index: int
    display: str
    norm: str
    units: list[Unit]


@dataclass
class RecognizedWord:
    text: str  # normalised
    units: list[Unit]
    unit_conf: list[float]
    start: float
    end: float

    @property
    def confidence(self) -> float:
        return min(self.unit_conf) if self.unit_conf else 0.0


@dataclass
class ExpectedEvidence:
    """Forced-alignment evidence for one passage word."""

    start: float | None = None
    end: float | None = None
    unit_gop: list[float | None] = field(default_factory=list)

    @property
    def word_gop(self) -> float | None:
        vals = [g for g in self.unit_gop if g is not None]
        return min(vals) if vals else None


@dataclass
class UnitResult:
    expected: str | None
    heard: str | None
    op: str  # match | sub | del | ins | spelling
    exp_index: int | None
    free_conf: float | None
    gop: float | None
    errors: list[dict] = field(default_factory=list)


@dataclass
class WordMarkResult:
    index: int
    display: str
    expected: str
    heard: str
    status: str
    raw_status: str  # what the decoder alone would say (before abstention)
    flags: list[str] = field(default_factory=list)
    inserted: list[str] = field(default_factory=list)
    start: float | None = None
    end: float | None = None
    free_conf: float | None = None
    gop: float | None = None
    units: list[UnitResult] = field(default_factory=list)
    patterns: list[str] = field(default_factory=list)
    note_bn: str = ""
    # free-decoding confidence of the units that differ (the value the misread rule compares with
    # free_high); stored so decisions can be replayed with new thresholds after teacher reviews
    err_free: float | None = None
    note_en: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Metrics:
    total_words: int
    attempted_words: int
    correct: int
    errors: int
    misread: int
    skipped: int
    unsure: int
    not_reached: int
    repetitions: int
    hesitations: int
    reading_time_sec: float | None
    accuracy: float | None
    wcpm: float | None
    score: float | None = None  # mark out of 10 for this reading test

    def to_dict(self) -> dict:
        return asdict(self)
