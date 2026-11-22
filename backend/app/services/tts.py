"""Model reading ("listen first") for students: neural text-to-speech with word timings.

Audio is generated once per (text, voice, speed) with edge-tts and cached on disk
as MP3 + a JSON list of word boundaries, so a passage needs internet only the
first time it is played (or run ``python -m scripts.pregen_tts`` while online).
Only the passage text is sent to the TTS service, never a child's voice or data.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from pathlib import Path

from ..config import get_settings

log = logging.getLogger(__name__)

VOICES = {"bn": "bn-BD-NabanitaNeural", "en": "en-US-AnaNeural"}  # Ana is a child voice
RATES = {False: "-5%", True: "-35%"}
MAX_CHARS = 3000


class TTSUnavailable(RuntimeError):
    pass


def tts_dir() -> Path:
    d = get_settings().data_dir / "tts"
    d.mkdir(parents=True, exist_ok=True)
    return d


def cache_key(text: str, lang: str, slow: bool) -> str:
    raw = f"{VOICES[lang]}|{RATES[slow]}|{text.strip()}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:20]


def audio_path(key: str) -> Path:
    return tts_dir() / f"{key}.mp3"


def _meta_path(key: str) -> Path:
    return tts_dir() / f"{key}.json"


async def _synth(text: str, voice: str, rate: str) -> tuple[bytes, list[dict]]:
    import edge_tts

    com = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
    audio = bytearray()
    words: list[dict] = []
    async for chunk in com.stream():
        if chunk["type"] == "audio":
            audio.extend(chunk["data"])
        elif chunk["type"] == "WordBoundary":
            start = chunk["offset"] / 1e7  # 100-ns ticks -> seconds
            words.append({"text": chunk["text"], "start": round(start, 3), "end": round(start + chunk["duration"] / 1e7, 3)})
    if not audio:
        raise TTSUnavailable("No audio received")
    return bytes(audio), words


async def speak(text: str, lang: str, slow: bool = False) -> dict:
    """Return {key, words} for the passage, generating and caching it if needed."""
    text = text.strip()
    if not text:
        raise ValueError("Empty text")
    if len(text) > MAX_CHARS:
        raise ValueError("Text is too long to read aloud")
    if lang not in VOICES:
        lang = "bn"
    key = cache_key(text, lang, slow)
    mp3, meta = audio_path(key), _meta_path(key)
    if mp3.exists() and meta.exists():
        return {"key": key, "words": json.loads(meta.read_text(encoding="utf-8"))}
    last: Exception | None = None
    for attempt in range(3):
        try:
            data, words = await _synth(text, VOICES[lang], RATES[slow])
            mp3.write_bytes(data)
            meta.write_text(json.dumps(words, ensure_ascii=False), encoding="utf-8")
            return {"key": key, "words": words}
        except Exception as e:  # noqa: BLE001 - network errors of several kinds
            last = e
            await asyncio.sleep(0.8 * (attempt + 1))
    log.warning("TTS failed for %s: %s", key, last)
    raise TTSUnavailable("The model reading needs an internet connection the first time it is played.")
