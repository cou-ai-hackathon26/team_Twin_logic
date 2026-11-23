"""Artifact-free child-like proxy: resample the same FLEURS test recordings to play 10-20% faster.

    python -m scripts.make_childlike_resample

Why a second proxy: the first child-like set used librosa's phase-vocoder pitch shifting. A control
showed that shifting pitch up and back down again (a net-zero change) already drops recall from
88% to 23% on dev recordings, so that proxy mostly measured processing artifacts, not voices.
Plain resampling raises pitch AND formants by the same factor (like a shorter vocal tract) with no
vocoder artifacts; it also makes speech 10-20% faster. Labels are copied from the paired original.
"""

from __future__ import annotations

import csv
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402

from app.speech.audio import load_audio_file, save_wav  # noqa: E402

SRC = Path("data/eval_robust/original")
OUT = Path("data/eval_robust/childlike_rs")


def speed_up(x: np.ndarray, factor: float) -> np.ndarray:
    """Read the signal `factor` times faster (linear interpolation = resampling, no phase vocoder)."""
    n = int(len(x) / factor)
    return np.interp(np.arange(n) * factor, np.arange(len(x)), x).astype(np.float32)


def main() -> None:
    rng = random.Random(53)
    (OUT / "audio").mkdir(parents=True, exist_ok=True)
    with open(SRC / "recordings.csv", encoding="utf-8") as f:
        recs = list(csv.DictReader(f))
    rows = []
    for r in recs:
        rid = r["id"].replace("original_", "childrs_")
        y = speed_up(load_audio_file(r["audio"]), rng.uniform(1.10, 1.20))
        save_wav(str(OUT / "audio" / f"{rid}.wav"), y)
        rows.append({**r, "id": rid, "audio": f"audio/{rid}.wav"})
    with open(OUT / "recordings.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    with open(SRC / "annotations.csv", encoding="utf-8") as f:
        ann = list(csv.DictReader(f))
    with open(OUT / "annotations.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(ann[0].keys()))
        w.writeheader()
        w.writerows({**a, "recording_id": a["recording_id"].replace("original_", "childrs_")} for a in ann)
    print(f"wrote {len(rows)} recordings to {OUT}")


if __name__ == "__main__":
    main()
