"""Three-system benchmark on human-annotated recordings (Proposal 6.2).

    python -m scripts.benchmark --recordings eval/recordings.csv --annotations eval/annotations.csv
    python -m scripts.benchmark ... --no-whisper        # skip the slow baseline
    python -m scripts.benchmark ... --split tune        # look at tuning speakers (never reported)

Systems:
  whisper_word  Whisper transcription + plain word comparison
  ctc_word      Bangla CTC + plain word comparison
  porabondhu    Bangla CTC + grapheme alignment + two confidence signals

Writes data/reports/benchmark_<time>.json/.md and benchmark_latest.json (shown in the app).
Every percentage is reported with counts and a 95% Wilson interval.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings, load_thresholds  # noqa: E402
from app.evaluation.dataset import load_dataset, load_seed_passages  # noqa: E402
from app.evaluation.scoring import SystemRun, Tally, check_targets, summarise, tally_run  # noqa: E402
from app.evaluation.stats import cohen_kappa  # noqa: E402
from app.pipeline import run_ctc_word_compare, run_porabondhu, run_whisper_word_compare  # noqa: E402
from app.speech.audio import load_audio_file  # noqa: E402
from app.speech.registry import get_ctc, get_whisper  # noqa: E402

SYSTEMS = ("whisper_word", "ctc_word", "porabondhu")


def bucket(rec) -> str:
    if rec.condition == "noisy":
        return f"{rec.group}_noisy"
    return rec.group


def fmt(p: dict | None) -> str:
    if not p or p.get("value") is None:
        return "n/a"
    return f"{p['value'] * 100:.1f}% ({p['k']}/{p['n']}; 95% CI {p['ci_low'] * 100:.1f}-{p['ci_high'] * 100:.1f})"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--recordings", required=True, type=Path)
    ap.add_argument("--annotations", required=True, type=Path)
    ap.add_argument("--split", default="test")
    ap.add_argument("--no-whisper", action="store_true")
    ap.add_argument("--label", default="")
    args = ap.parse_args()

    data = [r for r in load_dataset(args.recordings, args.annotations, load_seed_passages()) if r.split == args.split]
    if not data:
        sys.exit(f"No recordings with split={args.split}")
    th = load_thresholds()
    ctc = get_ctc()
    whisper = None if args.no_whisper else get_whisper()
    systems = [s for s in SYSTEMS if not (s == "whisper_word" and whisper is None)]

    tallies: dict[str, dict[str, Tally]] = {s: {} for s in systems}
    per_recording = []
    t_start = time.perf_counter()
    for k, rec in enumerate(data, 1):
        audio = load_audio_file(str(rec.audio))
        dur = len(audio) / 16000
        row = {"id": rec.id, "group": rec.group, "condition": rec.condition, "speaker": rec.speaker, "systems": {}}
        for s in systems:
            if s == "porabondhu":
                res = run_porabondhu(audio, rec.passage_text, ctc, th, skip_quality=True)
            elif s == "ctc_word":
                res = run_ctc_word_compare(audio, rec.passage_text, ctc)
            else:
                res = run_whisper_word_compare(audio, rec.passage_text, whisper)
            marks = [m.to_dict() for m in res.marks]
            if len(marks) != len(rec.labels):
                sys.exit(f"{rec.id}: passage has {len(marks)} words but annotation has {len(rec.labels)}")
            run = SystemRun(rec, s, marks, res.metrics.wcpm if res.metrics else None, res.transcript,
                            res.processing_ms, dur)
            tally_run(tallies[s].setdefault(bucket(rec), Tally()), run)
            tally_run(tallies[s].setdefault("all", Tally()), run)
            row["systems"][s] = {"wcpm": run.wcpm, "transcript": res.transcript,
                                 "statuses": [m["status"] for m in marks]}
        per_recording.append(row)
        print(f"[{k}/{len(data)}] {rec.id} ({dur:.1f}s) done")

    # inter-annotator agreement (Cohen's kappa) per group
    kappa: dict[str, float | None] = {}
    for g in {r.group for r in data}:
        a = [x for r in data if r.group == g and r.labels_a and r.labels_b for x in r.labels_a]
        b = [x for r in data if r.group == g and r.labels_a and r.labels_b for x in r.labels_b]
        kappa[g] = cohen_kappa(a, b) if a else None

    results = {s: {b: summarise(t) for b, t in tallies[s].items()} for s in systems}
    targets = {}
    for g in ("adult", "child"):
        if g in results["porabondhu"]:
            noisy = results["porabondhu"].get(f"{g}_noisy", {}).get("uncertainty_coverage")
            targets[g] = check_targets(g, results["porabondhu"][g], kappa.get(g), noisy)

    hypothesis = None
    if "whisper_word" in results:
        pb, wh = results["porabondhu"]["all"], results["whisper_word"]["all"]
        if pb["recall"]["value"] is not None and wh["recall"]["value"] is not None:
            diff = pb["recall"]["value"] - wh["recall"]["value"]
            prec_ok = (pb["precision"]["value"] or 0) >= (wh["precision"]["value"] or 0)
            hypothesis = {"recall_gain_pp": round(diff * 100, 1), "precision_not_worse": prec_ok,
                          "supported": diff >= 0.10 and prec_ok}

    now = datetime.now(timezone.utc)
    report = {
        "generated_at": now.isoformat(), "label": args.label, "split": args.split,
        "recordings": len(data), "speakers": sorted({r.speaker for r in data}),
        "groups": sorted({bucket(r) for r in data}), "thresholds": th.to_dict(),
        "model": {"ctc": ctc.model_id, "ctc_backend": ctc.backend,
                  "whisper": whisper.size if whisper else None},
        "results": results, "kappa": kappa, "targets": targets, "hypothesis": hypothesis,
        "per_recording": per_recording, "wall_time_sec": round(time.perf_counter() - t_start, 1),
    }
    out_dir = get_settings().reports_dir
    stamp = now.strftime("%Y%m%d_%H%M%S")
    (out_dir / f"benchmark_{stamp}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), "utf-8")
    (out_dir / "benchmark_latest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), "utf-8")

    md = [f"# PoraBondhu benchmark ({args.split} split)", "", f"Generated {now:%Y-%m-%d %H:%M} UTC. "
          f"{len(data)} recordings, speakers: {', '.join(report['speakers'])}.", ""]
    for b in ["all"] + sorted(k for k in results["porabondhu"] if k != "all"):
        md += [f"## {b}", "", "| System | Recall | Precision | False alarms | Unsure | WCPM MAE |",
               "|---|---|---|---|---|---|"]
        for s in systems:
            r = results[s].get(b)
            if not r:
                continue
            md.append(f"| {s} | {fmt(r['recall'])} | {fmt(r['precision'])} | {fmt(r['false_alarm'])} | "
                      f"{fmt(r['unsure_rate'])} | {r.get('wcpm_mae', 'n/a')} |")
        md.append("")
    if hypothesis:
        md += ["## Hypothesis", "", f"Recall gain over Whisper: {hypothesis['recall_gain_pp']} pp; "
               f"precision not worse: {hypothesis['precision_not_worse']}; "
               f"supported: **{hypothesis['supported']}**", ""]
    for g, rows in targets.items():
        md += [f"## Targets ({g})", "", "| Measure | Target | Value | Met |", "|---|---|---|---|"]
        for r in rows:
            v = r["value"]
            md.append(f"| {r['measure']} | {r['target']} | {'n/a' if v is None else round(v, 3)} | "
                      f"{'n/a' if r['met'] is None else ('yes' if r['met'] else 'no')} |")
        md.append("")
    (out_dir / f"benchmark_{stamp}.md").write_text("\n".join(md), "utf-8")
    print("\n".join(md))
    print(f"\nreport: {out_dir / f'benchmark_{stamp}.json'}")


if __name__ == "__main__":
    main()
