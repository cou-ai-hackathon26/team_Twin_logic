"""Lazy, thread-safe loading of the speech models (loaded once per process)."""

from __future__ import annotations

import logging
import threading
import time

from ..config import get_settings

log = logging.getLogger(__name__)

_lock = threading.Lock()
_ctc = None
_whisper = None
_status: dict[str, dict] = {
    "ctc": {"state": "not_loaded", "error": None, "load_sec": None},
    "whisper": {"state": "not_loaded", "error": None, "load_sec": None},
}


def get_ctc():
    global _ctc
    if _ctc is not None:
        return _ctc
    with _lock:
        if _ctc is None:
            from .ctc import CTCRecognizer

            s = get_settings()
            _status["ctc"]["state"] = "loading"
            t0 = time.perf_counter()
            try:
                _ctc = CTCRecognizer(s.ctc_model_id, threads=s.torch_threads or None,
                                     backend=s.resolved_ctc_backend(), onnx_dir=str(s.onnx_dir))
            except Exception as e:  # noqa: BLE001
                _status["ctc"].update(state="error", error=str(e))
                raise
            _status["ctc"].update(state="ready", error=None, load_sec=round(time.perf_counter() - t0, 1))
    return _ctc


def get_whisper():
    global _whisper
    s = get_settings()
    if not s.enable_whisper:
        raise RuntimeError("Whisper baseline is disabled (PB_ENABLE_WHISPER=false)")
    if _whisper is not None:
        return _whisper
    with _lock:
        if _whisper is None:
            from .whisper_baseline import WhisperBaseline

            _status["whisper"]["state"] = "loading"
            t0 = time.perf_counter()
            try:
                _whisper = WhisperBaseline(s.whisper_size, threads=s.torch_threads)
            except Exception as e:  # noqa: BLE001
                _status["whisper"].update(state="error", error=str(e))
                raise
            _status["whisper"].update(state="ready", error=None, load_sec=round(time.perf_counter() - t0, 1))
    return _whisper


def status() -> dict:
    s = get_settings()
    return {
        "ctc": {**_status["ctc"], "model_id": s.ctc_model_id, "backend": s.resolved_ctc_backend()},
        "whisper": {**_status["whisper"], "model": s.whisper_size, "enabled": s.enable_whisper},
        "device": "cpu",
    }
