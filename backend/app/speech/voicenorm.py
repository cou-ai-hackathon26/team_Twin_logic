"""Test-time voice normalisation for higher, child-like voices (no training, no child data).

Children have shorter vocal tracts (higher formants) and higher pitch than the adults the Bangla
speech model was trained on. On a child-like proxy (FLEURS with formant and pitch raised) recall
fell from 82% to 13%. Here we try a few *inverse* warps (lower formants, lower pitch) and keep the
version the model is most confident about. Confidence is the model's own free-decoding confidence;
the expected passage text is never used, so choosing a warp cannot hide a real misreading.

Gated: if the original audio already decodes confidently (typical adult voice) nothing changes and
no extra time is spent.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .audio import SR


def warp(x: np.ndarray, alpha: float, semitones: float) -> np.ndarray:
    """Scale formants by ``alpha`` (<1 = longer vocal tract) and shift pitch, keeping duration."""
    import librosa

    y = x
    if alpha != 1.0:
        y = librosa.resample(y, orig_sr=SR, target_sr=int(SR / alpha))
        y = librosa.effects.time_stretch(y, rate=len(y) / len(x))
        y = librosa.effects.pitch_shift(y, sr=SR, n_steps=-12 * np.log2(alpha))  # keep pitch, move formants
    if semitones:
        y = librosa.effects.pitch_shift(y, sr=SR, n_steps=semitones)
    n = len(x)
    y = y[:n] if len(y) >= n else np.pad(y, (0, n - len(y)))
    peak = float(np.max(np.abs(y))) + 1e-9
    return (y / peak * min(0.95, float(np.max(np.abs(x))) + 1e-9)).astype(np.float32)


@dataclass(frozen=True)
class VoiceNorm:
    gate: float = 0.80  # mean free-decoding confidence above which the original audio is kept
    candidates: tuple[tuple[float, float], ...] = ((0.92, -2.0), (0.88, -3.0), (0.84, -4.0), (0.80, -5.0), (0.88, 0.0))


def decode_confidence(recognizer, logits, temperature: float) -> float:
    words = recognizer.greedy_decode(recognizer.log_probs(logits, temperature))
    conf = [c for w in words for c in w.unit_conf]
    return float(np.mean(conf)) if conf else 0.0


def choose_logits(x: np.ndarray, recognizer, temperature: float, vn: VoiceNorm) -> tuple[np.ndarray, dict]:
    """Logits of the original audio, or of the most confidently decoded inverse warp."""
    logits = recognizer.logits(x)
    best = (decode_confidence(recognizer, logits, temperature), logits, (1.0, 0.0))
    info = {"original_conf": round(best[0], 4), "warp": None}
    if best[0] >= vn.gate:
        return logits, info
    for alpha, st in vn.candidates:
        lg = recognizer.logits(warp(x, alpha, st))
        c = decode_confidence(recognizer, lg, temperature)
        if c > best[0]:
            best = (c, lg, (alpha, st))
    if best[2] != (1.0, 0.0):
        info.update(warp={"alpha": best[2][0], "semitones": best[2][1]}, conf=round(best[0], 4))
    return best[1], info
