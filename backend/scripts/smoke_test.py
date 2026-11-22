"""Run the full pipeline on one audio file and print the marks.

    python -m scripts.smoke_test data/smoke/p04_errors.mp3 P04
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import load_thresholds  # noqa: E402
from app.pipeline import run_porabondhu  # noqa: E402
from app.speech.audio import load_audio_file  # noqa: E402
from app.speech.registry import get_ctc  # noqa: E402

SEED = Path(__file__).resolve().parent.parent / "app" / "seed" / "passages.json"


def main() -> None:
    audio_path, code = sys.argv[1], sys.argv[2]
    passages = {p["code"]: p for p in json.loads(SEED.read_text(encoding="utf-8"))}
    text = passages[code]["text"]
    t0 = time.perf_counter()
    rec = get_ctc()
    print(f"model loaded in {time.perf_counter() - t0:.1f}s")
    audio = load_audio_file(audio_path)
    res = run_porabondhu(audio, text, rec, load_thresholds())
    print("quality:", res.quality.to_dict())
    print("transcript:", res.transcript)
    print(f"processing: {res.processing_ms} ms for {len(audio) / 16000:.1f}s audio; FA ok={res.forced_alignment_ok}")
    for m in res.marks:
        errs = "; ".join(e["description_en"] for u in m.units for e in u.errors)
        g = f"{m.gop:.2f}" if m.gop is not None else "-"
        c = f"{m.free_conf:.2f}" if m.free_conf is not None else "-"
        print(f"{m.index:3d} {m.status:11s} raw={m.raw_status:8s} exp={m.expected:14s} heard={m.heard:14s} "
              f"conf={c} gop={g} t={m.start}-{m.end} flags={m.flags} pats={m.patterns} {errs}")
    print("metrics:", res.metrics.to_dict() if res.metrics else None)


if __name__ == "__main__":
    main()
