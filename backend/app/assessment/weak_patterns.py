"""Candidate weak patterns: transparent repeated-error counts.

For one child, every passage word read gives *opportunities* for the patterns
its units contain, and every word finally marked "misread" gives *errors* for
the patterns its unit diff blamed. A pattern becomes a *candidate weak
pattern* only after repeated errors across more than one reading, never after
a single slip.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Iterable, Mapping

from ..bangla.patterns import TEACHING_PRIORITY, pattern_category, pattern_label
from ..bangla.segment import segment_normalized
from . import types as T


@dataclass
class PatternStat:
    key: str
    errors: int = 0
    opportunities: int = 0
    readings: set[int] = field(default_factory=set)
    examples: list[dict] = field(default_factory=list)
    last_seen: str | None = None

    @property
    def error_rate(self) -> float | None:
        return self.errors / self.opportunities if self.opportunities else None

    def to_dict(self, candidate: bool) -> dict:
        return {
            **pattern_label(self.key),
            "errors": self.errors,
            "opportunities": self.opportunities,
            "error_rate": round(self.error_rate, 3) if self.error_rate is not None else None,
            "readings_with_error": len(self.readings),
            "candidate": candidate,
            "examples": self.examples[:6],
            "last_seen": self.last_seen,
        }


def word_opportunities(norm_word: str) -> list[str]:
    keys: list[str] = []
    for u in segment_normalized(norm_word):
        keys.extend(u.patterns())
    return keys


def compute_patterns(
    readings: Iterable[tuple[int, str, list[Mapping]]],
    min_errors: int = 3,
    min_readings: int = 2,
) -> list[dict]:
    """``readings`` yields (reading_id, created_at_iso, marks)."""
    stats: dict[str, PatternStat] = defaultdict(lambda: PatternStat(""))
    for reading_id, created, marks in readings:
        for m in marks:
            status = m.get("teacher_status") or m["status"]
            if status == T.NOT_REACHED:
                continue
            for k in set(word_opportunities(m["expected"])):
                s = stats[k]
                s.key = k
                s.opportunities += 1
            if status == T.MISREAD:
                pats = m.get("patterns") or []
                for k in set(pats):
                    s = stats[k]
                    s.key = k
                    s.errors += 1
                    s.readings.add(reading_id)
                    s.last_seen = max(s.last_seen or "", created)
                    if len(s.examples) < 12:
                        s.examples.append({"reading_id": reading_id, "expected": m["expected"],
                                           "heard": m.get("heard") or ""})
            elif status == T.SKIPPED:
                s = stats["skip"]
                s.key = "skip"
                s.errors += 1
                s.readings.add(reading_id)
                s.last_seen = max(s.last_seen or "", created)
    out = []
    for s in stats.values():
        if s.errors == 0:
            continue
        candidate = s.key != "skip" and s.errors >= min_errors and len(s.readings) >= min_readings
        out.append(s.to_dict(candidate))
    out.sort(key=lambda d: (not d["candidate"], TEACHING_PRIORITY.get(pattern_category(d["key"]), 9),
                            -d["errors"], -(d["error_rate"] or 0)))
    return out
