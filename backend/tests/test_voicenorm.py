"""Test-time voice normalisation: gated, and chooses by the model's own confidence only."""

import numpy as np

from app.assessment import types as T
from app.speech.voicenorm import VoiceNorm, choose_logits, warp


class ConfRecognizer:
    """Confidence = 0.5 for the original audio, 0.9 for any warped copy (detected by its RMS change)."""

    def __init__(self, original):
        self.original = original
        self.calls = 0

    def logits(self, audio):
        self.calls += 1
        same = len(audio) == len(self.original) and np.allclose(audio, self.original)
        return np.full((5, 3), 0.5 if same else 0.9, dtype=np.float32)

    def log_probs(self, logits, temperature=1.0):
        return logits

    def greedy_decode(self, lp):
        return [T.RecognizedWord("ক", [], [float(lp[0, 0])] * 3, 0.0, 0.2)]


def _audio():
    t = np.arange(16000) / 16000
    return (0.3 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)


def test_warp_keeps_length_and_level():
    x = _audio()
    y = warp(x, 0.88, -3.0)
    assert len(y) == len(x) and 0 < np.max(np.abs(y)) <= 0.31


def test_low_confidence_picks_the_most_confident_warp():
    x = _audio()
    rec = ConfRecognizer(x)
    lg, info = choose_logits(x, rec, 1.0, VoiceNorm(gate=0.8, candidates=((0.88, -3.0),)))
    assert info["warp"] == {"alpha": 0.88, "semitones": -3.0} and float(lg[0, 0]) == np.float32(0.9)


def test_confident_original_is_kept_without_extra_work():
    x = _audio()
    rec = ConfRecognizer(x)
    lg, info = choose_logits(x, rec, 1.0, VoiceNorm(gate=0.4))
    assert info["warp"] is None and rec.calls == 1
