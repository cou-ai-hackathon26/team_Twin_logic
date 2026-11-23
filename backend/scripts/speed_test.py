"""Time one 60-second Bangla reading through the full PoraBondhu pipeline, for several settings.

    python -m scripts.speed_test [--threads 0 4 8] [--chunk 15 30 60] [--repeats 3]

Audio: the first FLEURS test recordings joined to exactly 60 s (real adult speech). Reports the
median of `repeats` runs after one warm-up, per setting. Writes results/speed_test.json.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import statistics
import time
from datetime import datetime

import numpy as np

from app.config import BACKEND_DIR, RESULTS_DIR, get_settings, load_thresholds
from app.pipeline import run_porabondhu
from app.speech.audio import load_audio_file
from app.speech.ctc import CTCRecognizer


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--threads", type=int, nargs="+", default=[0, 4, 8])
    ap.add_argument("--chunk", type=float, nargs="+", default=[15.0, 30.0])
    ap.add_argument("--repeats", type=int, default=3)
    a = ap.parse_args()
    rows = [r for r in csv.DictReader(open(BACKEND_DIR / "data/eval_fleurs/recordings.csv", encoding="utf-8"))
            if r["split"] == "test"][:8]
    audio = np.concatenate([load_audio_file(r["audio"]) for r in rows])[: 16000 * 60]
    text = " ".join(r["human_transcript"] for r in rows)
    s, th = get_settings(), load_thresholds()
    out = []
    for t in a.threads:
        for ch in a.chunk:
            ctc = CTCRecognizer(s.ctc_model_id, threads=t or None, chunk_sec=ch, backend=s.resolved_ctc_backend(),
                                onnx_dir=str(s.onnx_dir))
            run_porabondhu(audio, text, ctc, th, skip_quality=True)  # warm-up
            times = []
            for _ in range(a.repeats):
                t0 = time.perf_counter()
                run_porabondhu(audio, text, ctc, th, skip_quality=True)
                times.append(time.perf_counter() - t0)
            row = {"threads": t or "default", "chunk_sec": ch, "median_s_per_60s": round(statistics.median(times), 2),
                   "runs": [round(x, 2) for x in times]}
            print(row, flush=True)
            out.append(row)
            del ctc
    rep = {"generated": datetime.now().isoformat(timespec="seconds"), "audio_sec": 60.0,
           "machine": f"author's laptop, {os.cpu_count()} logical cores, Windows 10, nothing else heavy running",
           "backend": s.resolved_ctc_backend(), "results": out,
           "best": min(out, key=lambda r: r["median_s_per_60s"])}
    (RESULTS_DIR / "speed_test.json").write_text(json.dumps(rep, indent=2), encoding="utf-8")
    print("best", rep["best"])


if __name__ == "__main__":
    main()
