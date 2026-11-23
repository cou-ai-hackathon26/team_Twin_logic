"""Collect the evaluation reports into backend/results/ (tracked, shown by the app and the README).

    python -m scripts.publish_results

Reads from data/reports/: the newest fleurs_test100_*.json (main comparison), robust_*.json
(robustness families), calibration_wide.json (tuning + cross-validation). Writes:

* results/benchmark_latest.json   main three-system report (what the Benchmark page shows)
* results/robustness.json         compact robustness + paired comparisons + calibration summary
* results/EVALUATION.md           human-readable summary with every caveat

Paired differences (PoraBondhu minus Whisper, child-like minus original) use a recording-level
bootstrap (2,000 resamples, fixed seed) because the same recordings are scored by both arms.
"""

from __future__ import annotations

import csv
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import RESULTS_DIR, get_settings  # noqa: E402

ERR = {"misread", "skipped"}
B = 2000


def newest(pattern: str) -> Path | None:
    """Newest report whose name is exactly <prefix>_<YYYYmmdd>_<HHMMSS>.json (so robust_childlike_* does
    not also match robust_childlike_rs_*)."""
    import re

    prefix = pattern.split("*")[0]
    rx = re.compile(re.escape(prefix) + r"\d{8}_\d{6}\.json$")
    files = sorted(f for f in get_settings().reports_dir.glob(pattern) if rx.match(f.name))
    return files[-1] if files else None


def labels_for(ann_csv: Path) -> dict[str, list[str]]:
    full = {"c": "correct", "m": "misread", "s": "skipped", "n": "not_reached"}
    out: dict[str, list[tuple[int, str]]] = {}
    with open(ann_csv, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            out.setdefault(r["recording_id"], []).append((int(r["word_index"]), full.get(r["label"], r["label"])))
    return {k: [lab for _, lab in sorted(v)] for k, v in out.items()}


def counts(statuses: list[str], labels: list[str]) -> tuple[int, int, int, int, int, int]:
    """tp, fp, fn, human_correct, unsure, words (not-reached words skipped, as in scoring.py)."""
    tp = fp = fn = hc = un = w = 0
    for s, h in zip(statuses, labels):
        if h == "not_reached":
            continue
        w += 1
        he, pe = h in ERR, s in ERR
        tp += he and pe
        fp += pe and not he
        fn += he and not pe
        hc += not he
        un += s == "unsure"
    return tp, fp, fn, hc, un, w


def metrics(rows: list[tuple]) -> dict[str, float]:
    tp, fp, fn, hc, un, w = (sum(r[i] for r in rows) for i in range(6))
    return {"recall": tp / (tp + fn) if tp + fn else float("nan"),
            "precision": tp / (tp + fp) if tp + fp else float("nan"),
            "false_alarm": fp / hc if hc else float("nan"), "unsure_rate": un / w if w else float("nan")}


def paired(a: list[tuple], b: list[tuple]) -> dict:
    """Bootstrap CI of metric(a) - metric(b) over recordings (a[i] and b[i] are the same recording)."""
    rng = random.Random(7)
    n = len(a)
    point = {k: metrics(a)[k] - metrics(b)[k] for k in metrics(a)}
    draws = {k: [] for k in point}
    for _ in range(B):
        idx = [rng.randrange(n) for _ in range(n)]
        ma, mb = metrics([a[i] for i in idx]), metrics([b[i] for i in idx])
        for k in draws:
            d = ma[k] - mb[k]
            if d == d:  # not NaN
                draws[k].append(d)
    out = {}
    for k, xs in draws.items():
        xs.sort()
        lo, hi = xs[int(0.025 * len(xs))], xs[int(0.975 * len(xs)) - 1]
        out[k] = {"diff": round(point[k], 4), "ci_low": round(lo, 4), "ci_high": round(hi, 4),
                  "excludes_zero": lo > 0 or hi < 0}
    return out


def per_rec(report: dict, labels: dict[str, list[str]], system: str, strip: str = "") -> dict[str, tuple]:
    out = {}
    for r in report["per_recording"]:
        sysr = r["systems"].get(system)
        rid = r["id"]
        if sysr is None or rid not in labels:
            continue
        out[rid.replace(strip, "") if strip else rid] = counts(sysr["statuses"], labels[rid])
    return out


def pct(p: dict | None) -> str:
    if not p or p.get("value") is None:
        return "n/a"
    return f"{p['value'] * 100:.1f}% ({p['k']}/{p['n']}; 95% CI {p['ci_low'] * 100:.0f}-{p['ci_high'] * 100:.0f}%)"


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    RESULTS_DIR.mkdir(exist_ok=True)
    main_p = newest("fleurs_test100_*.json")
    if main_p is None:
        sys.exit("no fleurs_test100 report yet")
    main_r = json.loads(main_p.read_text(encoding="utf-8"))
    (RESULTS_DIR / "benchmark_latest.json").write_text(json.dumps(main_r, ensure_ascii=False, indent=2), "utf-8")
    md_src = main_p.with_suffix(".md")
    if md_src.exists():
        (RESULTS_DIR / "benchmark_latest.md").write_text(md_src.read_text(encoding="utf-8"), "utf-8")

    lab_main = labels_for(root / "data/eval_fleurs/annotations.csv")
    pb = per_rec(main_r, lab_main, "porabondhu")
    comparisons = {}
    for other in ("whisper_word", "ctc_word"):
        ot = per_rec(main_r, lab_main, other)
        ids = sorted(set(pb) & set(ot))
        if ids:
            comparisons[f"porabondhu_minus_{other}"] = {"recordings": len(ids),
                                                        **paired([pb[i] for i in ids], [ot[i] for i in ids])}

    robust = {}
    for fam in ("original", "childlike_rs", "unseen", "skipcut", "childlike"):
        p = newest(f"robust_{fam}_*.json")
        if p:
            r = json.loads(p.read_text(encoding="utf-8"))
            robust[fam] = {"recordings": r["recordings"], "label": r["label"],
                           "porabondhu": {k: r["results"]["porabondhu"]["all"].get(k)
                                          for k in ("recall", "precision", "false_alarm", "unsure_rate",
                                                    "grapheme_accuracy", "words", "sec_per_60s")}}
    if "original" in robust and "childlike" in robust:
        po = json.loads(newest("robust_original_*.json").read_text(encoding="utf-8"))
        pc = json.loads(newest("robust_childlike_*.json").read_text(encoding="utf-8"))
        lo = labels_for(root / "data/eval_robust/original/annotations.csv")
        lc = labels_for(root / "data/eval_robust/childlike/annotations.csv")
        a, b = per_rec(pc, lc, "porabondhu", "childlike_"), per_rec(po, lo, "porabondhu", "original_")
        ids = sorted(set(a) & set(b))
        comparisons["childlike_minus_original"] = {"recordings": len(ids), **paired([a[i] for i in ids],
                                                                                     [b[i] for i in ids])}
    prs = newest("robust_childlike_rs_*.json")
    if prs and "original" in robust:
        po = json.loads(newest("robust_original_*.json").read_text(encoding="utf-8"))
        lrs = labels_for(root / "data/eval_robust/childlike_rs/annotations.csv")
        lo = labels_for(root / "data/eval_robust/original/annotations.csv")
        a = per_rec(json.loads(prs.read_text(encoding="utf-8")), lrs, "porabondhu", "childrs_")
        b = per_rec(po, lo, "porabondhu", "original_")
        ids = sorted(set(a) & set(b))
        comparisons["childlike_rs_minus_original"] = {"recordings": len(ids), **paired([a[i] for i in ids],
                                                                                      [b[i] for i in ids])}

    cal_p = get_settings().reports_dir / "calibration_wide.json"
    cal = json.loads(cal_p.read_text(encoding="utf-8")) if cal_p.exists() else None
    notes = [
        "The first child-like set ('childlike') used phase-vocoder pitch shifting. Control on 20 dev "
        "recordings: shifting pitch +4 then -4 semitones (no net change) already dropped recall from 87.5% "
        "to 22.9%, so that set mostly measures processing artifacts. 'childlike_rs' (plain resampling, "
        "pitch and formants x1.10-1.20, 10-20% faster) is the better proxy. Neither is child speech.",
        "Test-time voice normalisation by inverse phase-vocoder warps (app/speech/voicenorm.py, tuned on "
        "dev only, scripts/voicenorm_experiment.py) did not help (child-like recall 13.5% -> 14.9%, adult "
        "unchanged) and is not used by the app.",
    ]
    summary = {"generated_at": datetime.now(timezone.utc).isoformat(), "main_report": main_p.name, "notes": notes,
               "comparisons": comparisons, "robustness": robust,
               "calibration": {k: cal[k] for k in ("recordings", "previous_thresholds", "wide_grid_best",
                                                   "on_grid_edge", "cross_validation", "tradeoff_front")}
               if cal else None}
    (RESULTS_DIR / "robustness.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), "utf-8")
    if cal:
        (RESULTS_DIR / "calibration_wide.json").write_text(json.dumps(cal, ensure_ascii=False, indent=2), "utf-8")

    # ------------------------------------------------------------- markdown
    res = main_r["results"]
    L = ["# PoraBondhu evaluation (FLEURS Bengali, real adult speech, simulated reading errors)", "",
         f"Generated {summary['generated_at'][:16]} UTC from `{main_p.name}`.", "",
         "**What this is:** native adult speakers reading Wikipedia sentences correctly (Google FLEURS bn_in, "
         "CC BY 4.0). Reading errors are simulated by changing the expected text the system is given "
         "(`scripts/make_public_set.py`). Thresholds were tuned on FLEURS **dev** recordings only; results below "
         "are on the first 100 FLEURS **test** recordings. FLEURS has no speaker IDs, so speaker separation "
         "between dev and test cannot be verified; dev and test use different sentences.", "",
         "**What this is not:** not children, not authentic misreadings, not classroom audio. Labels are generated, "
         "so there is no inter-annotator agreement.", "",
         f"## Main comparison ({main_r['recordings']} test recordings)", "",
         "| System | Recall | Precision | False alarms | Unsure | s per 60 s |", "|---|---|---|---|---|---|"]
    for s in ("porabondhu", "whisper_word", "ctc_word"):
        if s in res:
            a = res[s]["all"]
            L.append(f"| {s} | {pct(a['recall'])} | {pct(a['precision'])} | {pct(a['false_alarm'])} | "
                     f"{pct(a['unsure_rate'])} | {a.get('sec_per_60s', 'n/a')} |")
    L += ["", "Paired differences (bootstrap over recordings, 95% CI; percentage points):", ""]
    for name, c in comparisons.items():
        parts = [f"{k} {v['diff'] * 100:+.1f} ({v['ci_low'] * 100:+.1f} to {v['ci_high'] * 100:+.1f})"
                 + (" *" if v["excludes_zero"] else "") for k, v in c.items() if isinstance(v, dict)]
        L.append(f"* **{name}** (n={c['recordings']}): " + "; ".join(parts))
    L += ["", "\\* = interval excludes zero.", ""]
    if robust:
        L += ["## Robustness (PoraBondhu only, 100 FLEURS test recordings each)", "",
              "| Set | What changes | Recall | Precision | False alarms | Unsure |", "|---|---|---|---|---|---|"]
        what = {"original": "nothing (paired reference)", "childlike": "phase-vocoder child-like voice (confounded by processing artifacts, see notes)",
                "unseen": "error types the detector was not designed around", "skipcut": "real skips: word audio cut out",
                "childlike_rs": "child-like voice by resampling x1.10-1.20 (pitch + formants up, no vocoder artifacts)"}
        for fam, r in robust.items():
            p = r["porabondhu"]
            L.append(f"| {fam} | {what[fam]} | {pct(p['recall'])} | {pct(p['precision'])} | "
                     f"{pct(p['false_alarm'])} | {pct(p['unsure_rate'])} |")
        L += ["", "Child-like sets are signal-processing proxies, **not** child speech.", ""] + [f"* {n}" for n in notes] + [""]
    if cal:
        cv = cal["cross_validation"]
        w = cal["wide_grid_best"]
        L += ["## Threshold tuning (dev recordings only)", "",
              f"* Wide search best: {w['thresholds']} (precision {w['precision']:.3f}, recall {w['recall']:.3f}, "
              f"false alarms {w['false_alarm']:.3f}, unsure {w['unsure_rate']:.3f}).",
              f"* Parameters at the edge of the searched grid: "
              f"{[k for k, v in cal['on_grid_edge'].items() if v] or 'none'}.",
              f"* 3-fold cross-validation (tune on 2/3, test on 1/3): precision {cv['precision']['mean']:.3f} "
              f"± {cv['precision']['sd']:.3f}, recall {cv['recall']['mean']:.3f} ± {cv['recall']['sd']:.3f}, "
              f"false alarms {cv['false_alarm']['mean']:.3f} ± {cv['false_alarm']['sd']:.3f}, unsure "
              f"{cv['unsure_rate']['mean']:.3f} ± {cv['unsure_rate']['sd']:.3f}.", ""]
    (RESULTS_DIR / "EVALUATION.md").write_text("\n".join(L), "utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
