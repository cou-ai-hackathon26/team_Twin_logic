"""Live progress bar for the evaluation run (calibrate -> benchmark).

    python -m scripts.progress                # watch data/eval_fleurs/*.log
    python -m scripts.progress --dir data/eval_fleurs --once

Reads the logs written by run_public_eval.ps1: calibrate prints "cached <id>"
per tuning recording, benchmark prints "[k/N] <id> ... done". Ctrl+C to quit.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import time
from pathlib import Path

BAR = 36
STEP_RE = re.compile(r"\[(\d+)/(\d+)\]")


def count_split(rec_csv: Path, split: str) -> int:
    if not rec_csv.exists():
        return 0
    with open(rec_csv, encoding="utf-8-sig", newline="") as f:
        return sum(1 for r in csv.DictReader(f) if (r.get("split") or "").strip() == split)


def read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return ""


def bar(frac: float) -> str:
    n = int(round(frac * BAR))
    return "█" * n + "░" * (BAR - n)


def fmt_eta(sec: float | None) -> str:
    if sec is None or sec < 0:
        return "--:--"
    m, s = divmod(int(sec), 60)
    h, m = divmod(m, 60)
    return f"{h}h{m:02d}m" if h else f"{m:02d}m{s:02d}s"


def status(d: Path, started: dict) -> tuple[list[str], bool]:
    n_tune = count_split(d / "recordings.csv", "tune")
    cal, bench = read(d / "calibrate.log"), read(d / "benchmark.log")
    lines = []

    # stage 1: calibration (caching ~ 95%, threshold search ~ 5%)
    done_c = cal.count("cached ")
    if "saved:" in cal or "best thresholds" in cal:
        f_cal = 1.0
    else:
        f_cal = 0.95 * done_c / n_tune if n_tune else 0.0
    lines.append(f" 1. Calibrate  {bar(f_cal)} {f_cal * 100:5.1f}%  ({done_c}/{n_tune} recordings)")

    # stage 2: benchmark
    steps = STEP_RE.findall(bench)
    k, n = (int(steps[-1][0]), int(steps[-1][1])) if steps else (0, count_split(d / "recordings.csv", "test"))
    finished = "report" in bench.lower() and k == n and n > 0 or "Traceback" in bench
    f_b = 1.0 if finished else (k / n if n else 0.0)
    eta = None
    if 0 < k < n:
        started.setdefault("bench", (time.time(), k))
        t0, k0 = started["bench"]
        if k > k0:
            eta = (time.time() - t0) / (k - k0) * (n - k)
    lines.append(f" 2. Benchmark  {bar(f_b)} {f_b * 100:5.1f}%  ({k}/{n} recordings, ETA {fmt_eta(eta)})")

    total = 0.3 * f_cal + 0.7 * f_b
    lines.append("")
    lines.append(f"    OVERALL    {bar(total)} {total * 100:5.1f}%")
    for log, name in ((cal, "calibrate"), (bench, "benchmark")):
        if "Traceback" in log:
            lines.append(f"\n !! {name} failed - see {d / (name + '.log')}")
            return lines, True
    if "saved:" in cal:
        m = re.search(r"tuning-set stats: (.*)", cal)
        if m:
            lines.append(f"\n tuning stats: {m.group(1)}")
    done = f_b >= 1.0
    if done:
        lines.append(f"\n Done. Report: {d.parent / 'reports' / 'benchmark_latest.json'} (and the .md next to it)")
    return lines, done


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", type=Path, default=Path(__file__).resolve().parent.parent / "data" / "eval_fleurs")
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--every", type=float, default=2.0)
    args = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    started: dict = {}
    while True:
        lines, done = status(args.dir, started)
        if not args.once:
            print("\033[2J\033[H", end="")
            print(" PoraBondhu evaluation on FLEURS (real human Bangla speech)\n")
        print("\n".join(lines), flush=True)
        if args.once or done:
            break
        time.sleep(args.every)


if __name__ == "__main__":
    main()
