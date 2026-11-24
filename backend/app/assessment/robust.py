"""Trust guards applied after marking: regional accent, background noise and odd words.

The marking engine decides each word from two confidence signals. Three situations make those
signals unreliable for a classroom, so this pass re-checks the words the engine called misread
(or skipped) and never turns a correct word into an error:

* **Possible regional accent.** A heard word that differs only by a configured sound swap (for example,
  dropped aspiration or র/ড়) is flagged ``accent`` and sent to ``unsure``. These contrasts can change
  meaning in standard Bangla, so the teacher must confirm before accepting a pronunciation variant.
* **Background noise.** For every word we measure how far it stands above the local noise around it
  (dB) and how flat its spectrum is (hiss, fans and rain are flat; speech is not). In a recording that is
  noisy overall (below ``NOISY_RECORDING_DB``), a misread word below ``NOISY_WORD_DB`` becomes ``unsure``
  with the flag ``noisy``; so does a misread/skipped word drowned in flat noise. The teacher should
  listen, not trust the machine. (A soft word in a quiet room is not "noise".)
* **Odd words.** Words the speech model is known to struggle with (3-letter conjuncts, very long or
  foreign/rare words, words the teacher marked as tricky, and words where teachers have often
  overruled the AI) need stronger evidence: a misread there becomes ``unsure`` with the flag
  ``odd_word`` unless the recogniser was very confident.

Pure Python + numpy; used by the web service and by scripts/eval_noise_accent.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ..bangla.phonetics import HOMOPHONE_REP
from . import types as T

FLAG_ACCENT = "accent"
FLAG_NOISY = "noisy"
FLAG_ODD = "odd_word"

NOISY_WORD_DB = 10.0  # word level above local noise; below this the word is not trusted
NOISY_RECORDING_DB = 15.0  # the level rule applies only when the whole recording is this noisy
NOISY_FLATNESS = 0.30  # median spectral flatness of the word: speech ~0.01-0.15, broadband noise ~0.5
ODD_STRONG_CONF = 0.85  # free-decoding confidence needed to keep a misread on an odd word

# Regional sound swaps that are not reading errors. Each group is one sound for accent purposes.
ACCENT_GROUPS: list[tuple[str, str]] = [
    ("কখ", "aspiration (খ said as ক)"),
    ("গঘ", "aspiration (ঘ said as গ)"),
    ("চছ", "aspiration (ছ said as চ)"),
    ("জঝ", "aspiration (ঝ said as জ)"),
    ("টঠ", "aspiration (ঠ said as ট)"),
    ("ডঢ", "aspiration (ঢ said as ড)"),
    ("তথ", "aspiration (থ said as ত)"),
    ("দধ", "aspiration (ধ said as দ)"),
    ("পফ", "aspiration / Chattogram-Sylhet ফ"),
    ("বভ", "aspiration (ভ said as ব)"),
    ("রড়ঢ়", "র and ড় merged (east and north)"),
    ("চস", "চ said as স (Sylhet, Noakhali)"),
]


def _build_rep() -> dict[str, str]:
    parent: dict[str, str] = {}

    def find(a: str) -> str:
        parent.setdefault(a, a)
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for ch, rep in HOMOPHONE_REP.items():
        union(rep, ch)
    for letters, _ in ACCENT_GROUPS:
        for ch in letters[1:]:
            union(letters[0], ch)
    return {ch: find(ch) for ch in list(parent)}


ACCENT_REP = _build_rep()


def accent_key(text: str) -> str:
    return "".join(ACCENT_REP.get(ch, ch) for ch in text)


def accent_only(expected: str, heard: str) -> bool:
    """True when ``heard`` differs from ``expected`` only by regional sound swaps."""
    if not expected or not heard or " " in heard.strip() or expected == heard:
        return False
    return len(expected) == len(heard) and accent_key(expected) == accent_key(heard)


def accent_reason(expected: str, heard: str) -> str:
    """Name the regional swap behind the first differing letter."""
    for a, b in zip(expected, heard):
        if a == b:
            continue
        for letters, note in ACCENT_GROUPS:
            group = set(letters) | {ch for ch, rep in HOMOPHONE_REP.items() if rep in letters}
            if (a in group or HOMOPHONE_REP.get(a, a) in group) and (b in group or HOMOPHONE_REP.get(b, b) in group):
                return note
    return "regional pronunciation"


# ---------------------------------------------------------------- odd words
RARE_CHARS = set("ঞঋৠঌৡঐঔঃ")


def odd_word_reason(display: str, units) -> str | None:
    """Why the speech model may be unreliable on this passage word, or None."""
    if any(ch.isdigit() or ("a" <= ch.lower() <= "z") for ch in display):
        return "number or non-Bangla letters"
    if any(len(u.consonants) >= 3 for u in units):
        return "three-letter conjunct"
    if sum(1 for u in units if len(u.consonants) >= 2) >= 3:
        return "many conjuncts in one word"
    if len(units) >= 8:
        return "very long word"
    if any(ch in RARE_CHARS for ch in display):
        return "rare letter"
    return None


# -------------------------------------------------------------------- noise
def word_snr(audio: np.ndarray, start: float | None, end: float | None, frames_db: np.ndarray,
             global_floor: float, hop: float = 0.01) -> float | None:
    """dB the word stands above the local noise floor (None without timing)."""
    if start is None or end is None or end <= start or not len(frames_db):
        return None
    a, b = int(start / hop), max(int(end / hop), int(start / hop) + 1)
    seg = frames_db[a:b]
    if not len(seg):
        return None
    w0, w1 = max(0, a - 100), min(len(frames_db), b + 100)  # +-1 s around the word
    local_floor = max(global_floor, float(np.percentile(frames_db[w0:w1], 10)))
    return round(float(np.percentile(seg, 90)) - local_floor, 1)


def frame_flatness(x: np.ndarray, frame: int = 400, hop: int = 160) -> np.ndarray:
    """Spectral flatness per frame (geometric / arithmetic mean of the power spectrum, 0..1).
    Voiced speech is peaky (low); hiss, fans, rain and crowd bursts are flat (high)."""
    if len(x) < frame:
        x = np.pad(x, (0, frame - len(x)))
    n = 1 + (len(x) - frame) // hop
    idx = np.arange(frame)[None, :] + hop * np.arange(n)[:, None]
    p = np.abs(np.fft.rfft(x[idx] * np.hanning(frame), axis=1)) ** 2 + 1e-12
    return np.exp(np.mean(np.log(p), axis=1)) / np.mean(p, axis=1)


def word_flatness(start: float | None, end: float | None, flat: np.ndarray, frames_db: np.ndarray,
                  floor: float, hop: float = 0.01) -> float | None:
    """Median flatness of the word's *sounding* frames (6 dB+ above the floor). Silence is ignored, so a
    word the child skipped is not mistaken for noise. None when under 30% of the word is sounding."""
    if start is None or end is None or end <= start or not len(flat):
        return None
    a, b = int(start / hop), max(int(end / hop), int(start / hop) + 1)
    seg, lvl = flat[a:b], frames_db[a:b]
    active = seg[lvl > floor + 6.0]
    if not len(seg) or len(active) < 0.3 * len(seg):
        return None
    return float(np.median(active))


@dataclass
class GuardOptions:
    accent: bool = True
    noise: bool = True
    odd_words: bool = True
    tricky_words: set[str] = field(default_factory=set)  # teacher said: always let me decide
    unreliable_words: set[str] = field(default_factory=set)  # teachers often overruled the AI here


def apply_guards(marks: list[T.WordMarkResult], audio: np.ndarray | None, pw: list[T.PassageWord],
                 opts: GuardOptions | None = None) -> dict:
    """Re-check misread/skipped words in place. Returns counts of what each guard changed."""
    from ..speech.audio import frame_db

    opts = opts or GuardOptions()
    counts = {"accent": 0, "noisy": 0, "odd_word": 0}
    frames = frame_db(audio) if audio is not None and len(audio) else np.array([])
    floor = float(np.percentile(frames, 10)) if len(frames) else 0.0
    noisy_recording = bool(len(frames)) and float(np.percentile(frames, 95)) - floor < NOISY_RECORDING_DB
    flat = frame_flatness(audio) if len(frames) else np.array([])
    by_index = {w.index: w for w in pw}
    for m in marks:
        noisy = False
        if len(frames):
            m.snr_db = word_snr(audio, m.start, m.end, frames, floor)
            fl = word_flatness(m.start, m.end, flat, frames, floor)
            # a quiet word is evidence of a skip, so low level only counts as noise for words that were read
            # and a soft word in an otherwise quiet recording is not noise
            low = noisy_recording and m.status != T.SKIPPED and m.snr_db is not None and m.snr_db < NOISY_WORD_DB
            noisy = low or (fl is not None and fl > NOISY_FLATNESS)
        if m.status not in (T.MISREAD, T.SKIPPED, T.UNSURE):
            continue
        # 1. possible regional accent: do not call it an error, but keep the teacher in control.
        # These sound contrasts can be meaningful in standard Bangla; the teacher must confirm
        # before the pronunciation becomes an accepted variant for future readings.
        if opts.accent and m.status in (T.MISREAD, T.UNSURE) and accent_only(m.expected, m.heard):
            why = accent_reason(m.expected, m.heard)
            m.status = T.UNSURE
            m.patterns = []
            m.flags.append(FLAG_ACCENT)
            m.note_bn = "সম্ভাব্য আঞ্চলিক উচ্চারণ: শুনে শিক্ষক সিদ্ধান্ত নিন"
            m.note_en = f"Possible regional pronunciation ({why}); the teacher listens and decides"
            counts["accent"] += 1
            continue
        if m.status == T.UNSURE:
            continue
        # 2. background noise around the word
        if opts.noise and noisy:
            m.status = T.UNSURE
            m.patterns = []
            m.flags.append(FLAG_NOISY)
            m.note_bn = "চারপাশের শব্দে শব্দটি পরিষ্কার নয়: শুনে যাচাই করুন"
            m.note_en = "Background noise over this word: listen and decide"
            counts["noisy"] += 1
            continue
        # 3. odd words need strong evidence
        if opts.odd_words and m.status == T.MISREAD:
            w = by_index.get(m.index)
            if m.expected in opts.tricky_words:
                why = "the teacher marked this word as tricky"
            elif m.expected in opts.unreliable_words:
                why = "teachers often corrected the AI on this word"
            else:
                why = odd_word_reason(m.display, w.units) if w else None
                strong = m.err_free is not None and m.err_free >= ODD_STRONG_CONF
                if why and strong:
                    why = None
            if why:
                m.status = T.UNSURE
                m.patterns = []
                m.flags.append(FLAG_ODD)
                m.note_bn = "কঠিন বা অপরিচিত শব্দ: AI নিশ্চিত নয়, শুনে যাচাই করুন"
                m.note_en = f"Odd word ({why}): the AI is not reliable here, listen and decide"
                counts["odd_word"] += 1
    return counts
