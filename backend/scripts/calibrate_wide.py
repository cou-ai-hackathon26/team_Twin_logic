"""Wider threshold search, cross-validated, plus the precision / unsure trade-off.

    python -m scripts.calibrate_wide --recordings data/eval_fleurs/recordings.csv \
        --annotations data/eval_fleurs/annotations.csv [--save]

Why: scripts/calibrate.py picked thresholds on the edge of its grid (free_high 0.5, gop_high 0.5,
gop_low -3.0, temperature 2.0), so the best setting may lie outside it. This script

1. searches a wider grid on the tuning split only (coordinate search from the current thresholds),
2. estimates how well tuning generalises with 3-fold cross-validation over tuning recordings
   (FLEURS has no speaker ids, so folds are by recording),
3. writes the precision / recall / unsure-rate trade-off for every evaluated setting.

Test speakers are never used. Thresholds are saved only with --save.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.assessment import types as T  # noqa: E402
from app.assessment.marking import assess, passage_words  # noqa: E402
from app.config import get_settings, load_thresholds, save_thresholds  # noqa: E402
from app.evaluation.dataset import load_dataset, load_seed_passages  # noqa: E402
from app.speech.audio import load_audio_file  # noqa: E402
from app.speech.registry import get_ctc  # noqa: E402

TEMPS = (1.5, 2.0, 3.0, 4.0)
FREE_HIGH = (0.2, 0.3, 0.4, 0.5, 0.6, 0.7)
GOP_HIGH = (0.1, 0.25, 0.5, 1.0, 1.5)
GOP_LOW = (-8.0, -6.0, -5.0, -4.0, -3.0, -2.0, -1.0)
MAX_FALSE_ALARM = 0.05


def evaluate(cache, idx, th: T.Thresholds) -> dict:
    tp = fp = fn = correct_words = unsure = words = 0
    for i in idx:
        labels, pw, per_t = cache[i]
        rw, ev = per_t[th.temperature]
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
    rec = tp / (tp + fn) if tp + fn else 0.0
    return {"precision": prec, "recall": rec, "f1": 2 * prec * rec / (prec + rec) if prec + rec else 0.0,
            "false_alarm": fp / correct_words if correct_words else 0.0,
            "unsure_rate": unsure / max(words, 1), "words": words}


def key(s: dict) -> tuple:
    ok = s["false_alarm"] <= MAX_FALSE_ALARM
    return (ok, s["f1"] if ok else -s["false_alarm"], -s["unsure_rate"])


def search(cache, idx, start: T.Thresholds, seen: dict, max_passes: int = 3) -> tuple[T.Thresholds, dict]:
    """Coordinate search over the wide grid, starting from `start`; records every point in `seen`."""
    grids = {"temperature": TEMPS, "free_high": FREE_HIGH, "gop_high": GOP_HIGH, "gop_low": GOP_LOW}
    best = start
    best_s = evaluate(cache, idx, best)
    improved, passes = True, 0
    while improved and passes < max_passes:
        improved, passes = False, passes + 1
        for name, values in grids.items():
            for v in values:
                cand = T.Thresholds(**{**best.to_dict(), name: v})
                if cand.gop_low >= cand.gop_high:
                    continue
                k = tuple(sorted(cand.to_dict().items()))
                s = seen.get(k) or evaluate(cache, idx, cand)
                seen[k] = s
                if key(s) > key(best_s):
                    best, best_s, improved = cand, s, True
    return best, best_s


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--recordings", required=True, type=Path)
    ap.add_argument("--annotations", required=True, type=Path)
    ap.add_argument("--folds", type=int, default=3)
    ap.add_argument("--save", action="store_true")
    args = ap.parse_args()

    data = [r for r in load_dataset(args.recordings, args.annotations, load_seed_passages()) if r.split == "tune"]
    ctc = get_ctc()
    cache = []
    for k, rec in enumerate(data, 1):
        logits = ctc.logits(load_audio_file(str(rec.audio)))
        pw = passage_words(rec.passage_text)
        per_t = {}
        for t in TEMPS:
            lp = ctc.log_probs(logits, t)
            per_t[t] = (ctc.greedy_decode(lp), ctc.expected_evidence(lp, pw))
        cache.append((rec.labels, pw, per_t))
        print(f"[{k}/{len(data)}] cached {rec.id}", flush=True)

    current = load_thresholds()
    start = T.Thresholds(**{**current.to_dict(), "temperature": 2.0})
    all_idx = list(range(len(cache)))
    seen: dict = {}
    best, best_s = search(cache, all_idx, start, seen)
    print("wide-grid best:", best.to_dict(), {k: round(v, 3) for k, v in best_s.items() if k != "words"}, flush=True)

    # cross-validation: tune on k-1 folds, measure on the held-out fold
    rng = random.Random(5)
    order = all_idx[:]
    rng.shuffle(order)
    folds = [order[i:: args.folds] for i in range(args.folds)]
    cv = []
    for f, held in enumerate(folds):
        train = [i for i in all_idx if i not in held]
        th_f, _ = search(cache, train, start, {}, max_passes=2)
        s = evaluate(cache, held, th_f)
        cv.append({"fold": f, "thresholds": th_f.to_dict(), **{k: round(v, 4) for k, v in s.items()}})
        print(f"fold {f}: precision {s['precision']:.3f} recall {s['recall']:.3f} "
              f"false_alarm {s['false_alarm']:.3f} unsure {s['unsure_rate']:.3f}", flush=True)

    def mean_sd(k):
        xs = [c[k] for c in cv]
        m = sum(xs) / len(xs)
        return {"mean": round(m, 4), "sd": round((sum((x - m) ** 2 for x in xs) / max(len(xs) - 1, 1)) ** 0.5, 4)}

    trade = sorted(({"thresholds": dict(k), **{m: round(v, 4) for m, v in s.items()}} for k, s in seen.items()),
                   key=lambda r: r["unsure_rate"])
    # Pareto front: best precision for each unsure-rate level with false alarms within target
    front, best_p = [], -1.0
    for r in trade:
        if r["false_alarm"] <= MAX_FALSE_ALARM and r["precision"] > best_p:
            front.append(r)
            best_p = r["precision"]
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "label": "FLEURS bn_in tuning speakers only (real adult speech, simulated errors)",
        "recordings": len(cache), "previous_thresholds": current.to_dict(),
        "wide_grid_best": {"thresholds": best.to_dict(), **{k: round(v, 4) for k, v in best_s.items()}},
        "on_grid_edge": {n: getattr(best, n) in (g[0], g[-1]) for n, g in
                         (("temperature", TEMPS), ("free_high", FREE_HIGH), ("gop_high", GOP_HIGH),
                          ("gop_low", GOP_LOW))},
        "cross_validation": {"folds": cv, **{k: mean_sd(k) for k in ("precision", "recall", "false_alarm",
                                                                       "unsure_rate")}},
        "tradeoff_front": front, "points_evaluated": len(seen),
    }
    out = get_settings().reports_dir / "calibration_wide.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), "utf-8")
    print("report:", out, flush=True)
    if args.save:
        meta = {"tuned_at": report["generated_at"], "recordings": len(cache), "search": "wide coordinate",
                "tuning_stats": report["wide_grid_best"], "cv": {k: report["cross_validation"][k] for k in
                                                                  ("precision", "recall", "false_alarm",
                                                                   "unsure_rate")}}
        print("saved:", save_thresholds(best, meta))


if __name__ == "__main__":
    main()
