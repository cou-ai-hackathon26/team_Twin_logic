"""Live processing progress for readings (in memory, one worker thread).

The worker reports the real pipeline stage; the speed estimate (seconds of
processing per second of audio) is learned from the readings this server has
actually processed, so the progress bar adapts to the machine it runs on.
"""

from __future__ import annotations

import threading
import time

STAGES = ("queued", "loading", "quality", "listening", "aligning", "diagnosing")

_lock = threading.Lock()
_live: dict[int, dict] = {}
_rtf = {"bn": 0.35, "en": 0.6}  # starting guesses, replaced by measured values
_load_sec = 20.0


def set_stage(reading_id: int, stage: str) -> None:
    with _lock:
        d = _live.setdefault(reading_id, {"started": time.monotonic()})
        d["stage"] = stage
        d["stage_started"] = time.monotonic()


def finish(reading_id: int, language: str, audio_sec: float | None, processing_ms: int | None) -> None:
    with _lock:
        _live.pop(reading_id, None)
        if audio_sec and processing_ms and audio_sec > 1:
            rtf = processing_ms / 1000 / audio_sec
            _rtf[language] = 0.7 * _rtf.get(language, rtf) + 0.3 * rtf  # smoothed


def clear(reading_id: int) -> None:
    with _lock:
        _live.pop(reading_id, None)


def snapshot(reading_id: int, language: str, audio_sec: float | None) -> dict:
    """What the UI needs to draw an honest progress bar."""
    with _lock:
        d = dict(_live.get(reading_id) or {})
        rtf = _rtf.get(language, 0.5)
    now = time.monotonic()
    est = (audio_sec or 30.0) * rtf + 1.5
    return {
        "stage": d.get("stage", "queued"),
        "elapsed_sec": round(now - d["started"], 1) if "started" in d else 0.0,
        "stage_elapsed_sec": round(now - d["stage_started"], 1) if "stage_started" in d else 0.0,
        "estimated_sec": round(est + (_load_sec if d.get("stage") == "loading" else 0), 1),
        "audio_sec": audio_sec,
    }
