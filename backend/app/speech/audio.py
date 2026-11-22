"""Audio loading and the recording quality check (Pipeline Step 1)."""

from __future__ import annotations

import io
import shutil
import subprocess
from dataclasses import asdict, dataclass, field

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

SR = 16_000


def _to_mono(x: np.ndarray) -> np.ndarray:
    return x.mean(axis=1) if x.ndim == 2 else x


def _resample(x: np.ndarray, sr: int) -> np.ndarray:
    if sr == SR:
        return x
    g = np.gcd(sr, SR)
    return resample_poly(x, SR // g, sr // g).astype(np.float32)


def _ffmpeg_decode(data: bytes) -> np.ndarray:
    exe = shutil.which("ffmpeg")
    if exe is None:
        raise ValueError("Unsupported audio format and ffmpeg is not installed")
    proc = subprocess.run(
        [exe, "-hide_banner", "-loglevel", "error", "-i", "pipe:0", "-ac", "1", "-ar", str(SR),
         "-f", "f32le", "pipe:1"],
        input=data, capture_output=True, check=False,
    )
    if proc.returncode != 0:
        raise ValueError(f"Could not decode audio: {proc.stderr.decode(errors='ignore')[:200]}")
    return np.frombuffer(proc.stdout, dtype=np.float32).copy()


def load_audio_bytes(data: bytes) -> np.ndarray:
    """Decode any audio to 16 kHz mono float32 in [-1, 1]."""
    try:
        x, sr = sf.read(io.BytesIO(data), dtype="float32", always_2d=False)
        x = _resample(_to_mono(np.asarray(x, dtype=np.float32)), int(sr))
    except Exception:  # noqa: BLE001 - fall back to ffmpeg for webm/ogg/m4a...
        x = _ffmpeg_decode(data)
    return np.clip(x, -1.0, 1.0).astype(np.float32)


def load_audio_file(path: str) -> np.ndarray:
    with open(path, "rb") as f:
        return load_audio_bytes(f.read())


def save_wav(path: str, x: np.ndarray) -> None:
    sf.write(path, x, SR, subtype="PCM_16")


@dataclass
class QualityReport:
    ok: bool
    duration_sec: float
    speech_level_db: float
    noise_floor_db: float
    snr_db: float
    clipping_ratio: float
    speech_ratio: float
    warnings: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)  # why it was rejected
    message_bn: str = ""
    message_en: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class QualityLimits:
    min_duration: float = 1.5
    max_duration: float = 300.0
    min_speech_db: float = -42.0
    min_snr_db: float = 8.0
    warn_snr_db: float = 15.0
    max_clipping: float = 0.01


def frame_db(x: np.ndarray, frame: int = 400, hop: int = 160) -> np.ndarray:
    if len(x) < frame:
        x = np.pad(x, (0, frame - len(x)))
    n = 1 + (len(x) - frame) // hop
    idx = np.arange(frame)[None, :] + hop * np.arange(n)[:, None]
    rms = np.sqrt(np.mean(x[idx] ** 2, axis=1) + 1e-12)
    return 20 * np.log10(rms + 1e-12)


def quality_check(x: np.ndarray, limits: QualityLimits | None = None) -> QualityReport:
    lim = limits or QualityLimits()
    dur = len(x) / SR
    db = frame_db(x)
    speech = float(np.percentile(db, 95))
    noise = float(np.percentile(db, 10))
    snr = speech - noise
    clip = float(np.mean(np.abs(x) > 0.99)) if len(x) else 0.0
    speech_ratio = float(np.mean(db > noise + 0.5 * max(snr, 0.0))) if len(db) else 0.0
    reasons: list[str] = []
    warnings: list[str] = []
    if dur < lim.min_duration:
        reasons.append("too_short")
    if dur > lim.max_duration:
        reasons.append("too_long")
    if speech < lim.min_speech_db:
        reasons.append("too_quiet")
    if clip > lim.max_clipping:
        reasons.append("clipping")
    if snr < lim.min_snr_db and "too_quiet" not in reasons:
        reasons.append("too_noisy")
    elif snr < lim.warn_snr_db:
        warnings.append("noisy")
    msgs = {
        "too_short": ("রেকর্ডিং খুব ছোট।", "The recording is too short."),
        "too_long": ("রেকর্ডিং খুব লম্বা।", "The recording is too long."),
        "too_quiet": ("আওয়াজ খুব কম, মাইক্রোফোনের কাছে এসে পড়ো।", "Too quiet: please read closer to the microphone."),
        "clipping": ("আওয়াজ খুব জোরে, একটু দূরে থেকে পড়ো।", "Too loud: please move a little away from the microphone."),
        "too_noisy": ("চারপাশে অনেক শব্দ, শান্ত জায়গায় আবার পড়ো।", "Too much background noise: please try again somewhere quieter."),
    }
    bn = " ".join(msgs[r][0] for r in reasons)
    en = " ".join(msgs[r][1] for r in reasons)
    return QualityReport(
        ok=not reasons, duration_sec=round(dur, 2), speech_level_db=round(speech, 1),
        noise_floor_db=round(noise, 1), snr_db=round(snr, 1), clipping_ratio=round(clip, 4),
        speech_ratio=round(speech_ratio, 3), warnings=warnings, reasons=reasons,
        message_bn=bn, message_en=en,
    )
