"""Live progress bar for the evaluation run (scripts/run_eval_100.ps1).

    python -m scripts.progress           # live, refreshes every 2 s
    python -m scripts.progress --once    # one snapshot

Stages: wide calibration (tuning speakers) -> benchmark on 100 test recordings (3 systems)
-> robustness sets (original, child-like, unseen errors, real skips). Ctrl+C to quit.
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

BAR = 30
STEP_RE = re.compile(r"\[(\d+)/(\d+)\]")
ROOT = Path(__file__).resolve().parent.parent / "data"


def read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return ""


def bar(frac: float) -> str:
    n = int(round(frac * BAR))
    return "█" * n + "░" * (BAR - n)


def frac_of(log: str, done_marker: str, total_hint: int) -> tuple[float, str]:
    if "Traceback" in log:
        return 0.0, "FAILED"
    if done_marker in log:
        return 1.0, "done"
    steps = STEP_RE.findall(log)
    if not steps:
        return 0.0, "waiting" if not log else "starting"
    k, n = int(steps[-1][0]), int(steps[-1][1])
    return k / max(n, total_hint, 1), f"{k}/{n}"


STAGES = [  # (label, log, done marker, weight)
    ("Wide calibration", ROOT / "eval_fleurs" / "calibrate_wide.log", "report:", 0.25),
    ("Benchmark (100, 3 systems)", ROOT / "eval_fleurs" / "benchmark.log", "report:", 0.45),
    ("Robust: original", ROOT / "eval_robust" / "original.log", "report:", 0.075),
    ("Robust: child-like", ROOT / "eval_robust" / "childlike.log", "report:", 0.075),
    ("Robust: unseen errors", ROOT / "eval_robust" / "unseen.log", "report:", 0.075),
    ("Robust: real skips", ROOT / "eval_robust" / "skipcut.log", "report:", 0.075),
]


def status() -> tuple[list[str], bool]:
    lines, total, failed = [], 0.0, None
    for label, log, marker, w in STAGES:
        text = read(log)
        f, note = frac_of(text, marker, 0)
        if label.startswith("Wide") and f < 1 and "fold" in text:
            f, note = 0.8, "cross-validation"
        elif label.startswith("Wide") and f < 1 and "wide-grid best" in text:
            f, note = 0.6, "cross-validation"
        elif label.startswith("Wide") and f < 1 and STEP_RE.search(text):
            f = 0.5 * f  # caching is about half the work, the search the rest
        total += w * f
        if note == "FAILED":
            failed = log
        lines.append(f" {label:<27} {bar(f)} {f * 100:5.1f}%  {note}")
    lines += ["", f" {'OVERALL':<27} {bar(total)} {total * 100:5.1f}%"]
    done = (ROOT / "eval_100_done.txt").exists()
    if failed:
        lines.append(f"\n !! failed - see {failed}")
    if done:
        lines.append(f"\n Done. Reports in {ROOT / 'reports'}")
    return lines, done or bool(failed)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    args = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    while True:
        lines, done = status()
        if not args.once:
            print("\033[2J\033[H", end="")
            print(" PoraBondhu evaluation (FLEURS, real adult Bangla speech)\n")
        print("\n".join(lines), flush=True)
        if args.once or done:
            break
        time.sleep(2)


if __name__ == "__main__":
    main()
