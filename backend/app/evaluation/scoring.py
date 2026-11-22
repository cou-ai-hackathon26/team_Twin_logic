"""Compare system word marks with human labels (Proposal section 6)."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..assessment import types as T
from ..bangla.normalize import normalize_text
from .dataset import Recording
from .stats import error_rate, proportion, rate, spearman

ERR = (T.MISREAD, T.SKIPPED)

# Success criteria fixed in the proposal before any code was written.
TARGETS = {
    "adult": {"recall": (">=", 0.80), "precision": (">=", 0.80), "false_alarm": ("<=", 0.05),
              "grapheme_accuracy": (">=", 0.70), "wcpm_mae": ("<=", 5.0), "wcpm_spearman": (">=", 0.90),
              "uncertainty_coverage_noisy": (">=", 0.50), "kappa": (">=", 0.80), "sec_per_60s": ("<=", 15.0)},
    "child": {"recall": (">=", 0.65), "precision": (">=", 0.65), "false_alarm": ("<=", 0.10),
              "wcpm_mae": ("<=", 8.0), "wcpm_spearman": (">=", 0.80), "kappa": (">=", 0.80),
              "sec_per_60s": ("<=", 15.0)},
}


@dataclass
class SystemRun:
    recording: Recording
    system: str
    marks: list[dict]  # WordMarkResult.to_dict()
    wcpm: float | None
    transcript: str
    processing_ms: int
    duration_sec: float


@dataclass
class Tally:
    tp: int = 0
    fp: int = 0
    fn: int = 0
    tn: int = 0
    unsure: int = 0
    words: int = 0
    human_correct: int = 0
    raw_wrong: int = 0
    raw_wrong_unsure: int = 0
    unit_hits: int = 0
    unit_total: int = 0
    wcpm_pairs: list[tuple[float, float]] = field(default_factory=list)
    cer: list[int] = field(default_factory=lambda: [0, 0])
    wer: list[int] = field(default_factory=lambda: [0, 0])
    sec_per_60: list[float] = field(default_factory=list)
    recordings: int = 0


def tally_run(t: Tally, run: SystemRun) -> None:
    rec = run.recording
    t.recordings += 1
    for m, human in zip(run.marks, rec.labels):
        if human == T.NOT_REACHED:
            continue
        t.words += 1
        pred = m["status"]
        h_err = human in ERR
        p_err = pred in ERR
        if pred == T.UNSURE:
            t.unsure += 1
        if not h_err:
            t.human_correct += 1
        if h_err and p_err:
            t.tp += 1
            # grapheme accuracy: did the system blame the annotated unit?
            want = rec.error_units.get(m["index"])
            if want and human == T.MISREAD:
                t.unit_total += 1
                blamed = {u.get("exp_index") for u in m.get("units", []) if u.get("errors")}
                if blamed & set(want):
                    t.unit_hits += 1
        elif p_err:
            t.fp += 1
        elif h_err:
            t.fn += 1
        else:
            t.tn += 1
        raw = m.get("raw_status", pred)
        raw_err = raw in ERR
        if raw_err != h_err:
            t.raw_wrong += 1
            if pred == T.UNSURE:
                t.raw_wrong_unsure += 1
    if rec.human_wcpm is not None and run.wcpm is not None:
        t.wcpm_pairs.append((rec.human_wcpm, run.wcpm))
    if rec.human_transcript:
        ref = normalize_text(rec.human_transcript)
        hyp = normalize_text(run.transcript)
        e, n = error_rate(ref.replace(" ", ""), hyp.replace(" ", ""))
        t.cer[0] += e
        t.cer[1] += n
        e, n = error_rate(ref.split(), hyp.split())
        t.wer[0] += e
        t.wer[1] += n
    if run.duration_sec > 0:
        t.sec_per_60.append(run.processing_ms / 1000 * 60 / run.duration_sec)


def summarise(t: Tally) -> dict:
    out = {
        "recordings": t.recordings,
        "words": t.words,
        "recall": proportion(t.tp, t.tp + t.fn),
        "precision": proportion(t.tp, t.tp + t.fp),
        "false_alarm": proportion(t.fp, t.human_correct),
        "unsure_rate": proportion(t.unsure, t.words),
        "grapheme_accuracy": proportion(t.unit_hits, t.unit_total),
        "uncertainty_coverage": proportion(t.raw_wrong_unsure, t.raw_wrong),
        "confusion": {"tp": t.tp, "fp": t.fp, "fn": t.fn, "tn": t.tn},
        "cer": rate(t.cer[0], t.cer[1]) if t.cer[1] else None,
        "wer": rate(t.wer[0], t.wer[1]) if t.wer[1] else None,
    }
    if t.wcpm_pairs:
        hum = [a for a, _ in t.wcpm_pairs]
        sysv = [b for _, b in t.wcpm_pairs]
        out["wcpm_mae"] = round(sum(abs(a - b) for a, b in t.wcpm_pairs) / len(t.wcpm_pairs), 2)
        out["wcpm_spearman"] = spearman(hum, sysv)
        out["wcpm_n"] = len(t.wcpm_pairs)
    if t.sec_per_60:
        out["sec_per_60s"] = round(sum(t.sec_per_60) / len(t.sec_per_60), 2)
        out["sec_per_60s_max"] = round(max(t.sec_per_60), 2)
    return out


def check_targets(group: str, s: dict, kappa: float | None, coverage_noisy: dict | None) -> list[dict]:
    rows = []
    for name, (op, target) in TARGETS.get(group, {}).items():
        if name == "kappa":
            val = kappa
        elif name == "uncertainty_coverage_noisy":
            val = coverage_noisy["value"] if coverage_noisy else None
        else:
            v = s.get(name)
            val = v["value"] if isinstance(v, dict) else v
        met = None if val is None else (val >= target if op == ">=" else val <= target)
        rows.append({"measure": name, "target": f"{op} {target}", "value": val, "met": met})
    return rows
