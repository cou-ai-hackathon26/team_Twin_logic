"""Whisper baseline (comparison system 1).

Whisper decodes with a strong internal language model, so it tends to output
the *intended* word. That is exactly the behaviour the benchmark measures.
Uses faster-whisper (CTranslate2, int8) for CPU speed.
"""

from __future__ import annotations

import threading

import numpy as np

from ..assessment import types as T
from ..bangla.normalize import normalize_text
from ..bangla.segment import segment_normalized


# Whisper (small/base) often writes Bangla speech in Devanagari script. The
# Unicode Indic blocks are laid out in parallel (ISCII order), so a fixed
# offset maps Devanagari to Bengali; a few letters have no Bengali slot.
_DEVA_EXCEPTIONS = {"व": "ব", "ऱ": "র", "ळ": "ল", "ऴ": "ল",
                    "ऩ": "ন", "ऑ": "ও", "ॉ": "ো", "ॅ": "ে",
                    "ॆ": "ে", "ॊ": "ো", "ऄ": "এ", "ऍ": "এ",
                    "ऎ": "এ", "ऒ": "ও", "।": "।", "॥": "॥"}


def devanagari_to_bengali(text: str) -> str:
    out = []
    for ch in text:
        o = ord(ch)
        if 0x0900 <= o <= 0x097F:
            out.append(_DEVA_EXCEPTIONS.get(ch, chr(o + 0x80)))
        else:
            out.append(ch)
    return "".join(out)


class WhisperBaseline:
    def __init__(self, size: str = "small", threads: int = 0) -> None:
        from faster_whisper import WhisperModel

        self.size = size
        self.model = WhisperModel(size, device="cpu", compute_type="int8", cpu_threads=threads)
        self._lock = threading.Lock()

    def transcribe(self, audio: np.ndarray) -> tuple[str, list[T.RecognizedWord]]:
        with self._lock:
            segments, _info = self.model.transcribe(
                audio, language="bn", beam_size=5, word_timestamps=True, vad_filter=False,
                condition_on_previous_text=False,
            )
            segments = list(segments)
        words: list[T.RecognizedWord] = []
        texts: list[str] = []
        for seg in segments:
            texts.append(devanagari_to_bengali(seg.text))
            for w in seg.words or []:
                norm = normalize_text(devanagari_to_bengali(w.word))
                for part in norm.split():
                    units = segment_normalized(part)
                    p = float(getattr(w, "probability", 1.0) or 1.0)
                    words.append(T.RecognizedWord(part, units, [p] * len(units), float(w.start), float(w.end)))
        return normalize_text(" ".join(texts)), words

    def transcribe_english(self, audio: np.ndarray) -> tuple[str, list[tuple[str, float, float, float]]]:
        """English reading: greedy decoding, no carried-over context, word timestamps.

        Returns (text, [(word, start, end, probability), ...]).
        """
        with self._lock:
            segments, _info = self.model.transcribe(
                audio, language="en", beam_size=1, word_timestamps=True, vad_filter=False,
                condition_on_previous_text=False, without_timestamps=False,
            )
            segments = list(segments)
        words = [(w.word, float(w.start), float(w.end), float(getattr(w, "probability", 1.0) or 1.0))
                 for seg in segments for w in (seg.words or [])]
        return " ".join(seg.text.strip() for seg in segments).strip(), words
