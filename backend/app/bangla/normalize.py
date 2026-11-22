"""Unicode normalisation for Bangla text.

The same visible Bangla word can be stored with different code point sequences
(for example ড় as one code point or as ড + nukta, ো as one code point or as
ে + া). Comparison is only meaningful after both sides use one canonical form.

Canonical form used throughout PoraBondhu:
  * Unicode NFC,
  * ড় ঢ় য় as single precomposed code points,
  * খণ্ড ত as U+09CE,
  * no ZWJ / ZWNJ (they change rendering, not the letters),
  * no punctuation, single spaces between words.
"""

from __future__ import annotations

import re
import unicodedata

from . import chars as C

_NUKTA_COMPOSE = {
    "ড" + C.NUKTA: C.RRA,  # ড + ় -> ড়
    "ঢ" + C.NUKTA: C.RHA,  # ঢ + ় -> ঢ়
    "য" + C.NUKTA: C.YYA,  # য + ় -> য়
}

# Vowel letter written as অ + kar (a common typing error) -> the real vowel.
_A_PLUS_KAR = {
    "অা": "আ",  # অা -> আ
}

_SPACE_RE = re.compile(r"\s+")


def _compose_nukta(text: str) -> str:
    for seq, composed in _NUKTA_COMPOSE.items():
        text = text.replace(seq, composed)
    return text


def normalize_text(text: str, *, strip_punctuation: bool = True) -> str:
    """Return the canonical form of a Bangla string."""
    if not text:
        return ""
    t = unicodedata.normalize("NFC", text)
    # Khanda ta is sometimes typed as ত + ্ + ZWJ.
    t = t.replace(C.TA + C.VIRAMA + C.ZWJ, C.KHANDA_TA)
    t = t.replace(C.ZWJ, "").replace(C.ZWNJ, "")
    t = _compose_nukta(t)
    for seq, repl in _A_PLUS_KAR.items():
        t = t.replace(seq, repl)
    # ে + ৗ -> ৌ can survive NFC when separated by a stray mark; fix it.
    t = t.replace("ৌ", "ৌ").replace("ো", "ো")
    if strip_punctuation:
        t = "".join(" " if ch in C.PUNCTUATION else ch for ch in t)
    t = _SPACE_RE.sub(" ", t).strip()
    return t


def normalize_word(word: str) -> str:
    """Canonical form of a single word (no spaces)."""
    return normalize_text(word).replace(" ", "")


def tokenize_display(text: str) -> list[tuple[str, str]]:
    """Split a passage into words.

    Returns a list of ``(display, normalised)`` pairs. ``display`` keeps the
    original spelling and punctuation for showing to the teacher; tokens that
    are only punctuation are attached to the previous word.
    """
    out: list[tuple[str, str]] = []
    for raw in unicodedata.normalize("NFC", text).split():
        norm = normalize_word(raw)
        if not norm:
            if out:
                disp, n = out[-1]
                out[-1] = (disp + " " + raw, n)
            continue
        out.append((raw, norm))
    return out
