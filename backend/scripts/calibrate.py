"""Tune the decision thresholds on the *tuning speakers only*, then freeze them.

    python -m scripts.calibrate --recordings eval/recordings.csv --annotations eval/annotations.csv

Searches the logit temperature and the three thresholds (free-decoding high,
expected-text high/low) for the best error-detection F1 with at most 5% false
alarms on correctly read words. Writes data/thresholds.json, which the app and
the benchmark load. Test speakers are never looked at.
"""

from __future__ import annotations

import argparse
import itertools
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.assessment import types as T  # noqa: E402
from app.assessment.marking import assess, passage_words  # noqa: E402
from app.config import save_thresholds  # noqa: E402
from app.evaluation.dataset import load_dataset, load_seed_passages  # noqa: E402
from app.speech.audio import load_audio_file  # noqa: E402
from app.speech.registry import get_ctc  # noqa: E402

TEMPS = (1.0, 1.5, 2.0)
FREE_HIGH = (0.5, 0.6, 0.7, 0.8, 0.9)
GOP_HIGH = (0.5, 1.0, 1.5, 2.0, 3.0)
GOP_LOW = (-3.0, -2.0, -1.0, -0.5, 0.0)
MAX_FALSE_ALARM = 0.05


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--recordings", required=True, type=Path)
    ap.add_argument("--annotations", required=True, type=Path)
    ap.add_argument("--dry-run", action="store_true", help="print the result without saving")
    args = ap.parse_args()

    data = [r for r in load_dataset(args.recordings, args.annotations, load_seed_passages()) if r.split == "tune"]
    if not data:
        sys.exit("No recordings with split=tune")
    ctc = get_ctc()
    cache = []  # (labels, passage words, {temp: (rw, ev)})
    for rec in data:
        audio = load_audio_file(str(rec.audio))
        logits = ctc.logits(audio)
        pw = passage_words(rec.passage_text)
        per_t = {}
        for t in TEMPS:
            lp = ctc.log_probs(logits, t)
            per_t[t] = (ctc.greedy_decode(lp), ctc.expected_evidence(lp, pw))
        cache.append((rec.labels, pw, per_t))
        print(f"cached {rec.id}")

    best = None
    for t, fh, gh, gl in itertools.product(TEMPS, FREE_HIGH, GOP_HIGH, GOP_LOW):
        if gl >= gh:
            continue
        th = T.Thresholds(free_high=fh, gop_high=gh, gop_low=gl, temperature=t)
        tp = fp = fn = correct_words = unsure = words = 0
        for labels, pw, per_t in cache:
            rw, ev = per_t[t]
            for m, h in zip(assess(pw, rw, ev, th), labels):
                if h == T.NOT_REACHED:
                    continue
                words += 1
                he, pe = h in (T.MISREAD, T.SKIPPED), m.status in (T.MISREAD, T.SKIPPED)
                unsure += m.status == T.UNSURE
                correct_words += not he
                tp += he and pe
                fp += pe and not he
                fn += he and not pe
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec_ = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * prec * rec_ / (prec + rec_) if prec + rec_ else 0.0
        fa = fp / correct_words if correct_words else 0.0
        ok = fa <= MAX_FALSE_ALARM
        key = (ok, f1 if ok else -fa, -unsure / max(words, 1))
        if best is None or key > best[0]:
            best = (key, th, {"precision": prec, "recall": rec_, "f1": f1, "false_alarm": fa,
                              "unsure_rate": unsure / max(words, 1), "words": words})
    assert best is not None
    _, th, stats = best
    print("best thresholds:", th.to_dict())
    print("tuning-set stats:", {k: round(v, 3) if isinstance(v, float) else v for k, v in stats.items()})
    if not args.dry_run:
        meta = {"tuned_at": datetime.now(timezone.utc).isoformat(), "speakers": sorted({r.speaker for r in data}),
                "recordings": len(data), "tuning_stats": stats}
        print("saved:", save_thresholds(th, meta))


if __name__ == "__main__":
    main()
