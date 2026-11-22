"""Bangla orthographic grapheme segmentation.

A written Bangla word is split into *units* (akshara-like clusters). Each unit
keeps its parts separately, so that the alignment engine can say *which part*
of a unit was misread:

    প্রথম  ->  [প্র] [থ] [ম]
    প্র     ->  consonants=(প, র)  core=(প,)  phalas=(র,)  -> র-ফলা
    কার্য   ->  [কা] [র্য]  -> reph over য
    ক্ষেত্র  ->  [ক্ষে] [ত্র]  -> conjunct ক্ষ with এ-কার; ত with র-ফলা

The segmenter works on canonical text (see ``normalize``).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import chars as C
from .normalize import normalize_word


@dataclass(frozen=True)
class Unit:
    text: str
    kind: str  # "consonant" | "vowel" | "other"
    consonants: tuple[str, ...] = ()  # full cluster without reph, in order
    reph: bool = False
    kar: str | None = None
    signs: tuple[str, ...] = ()
    hasanta: bool = False
    vowel: str | None = None  # independent vowel for kind == "vowel"
    start: int = 0  # char offset in the normalised word
    end: int = 0

    # --- derived parts -------------------------------------------------
    @property
    def phalas(self) -> tuple[str, ...]:
        """Phala letters (র য ব) that follow the first consonant of the cluster."""
        out = []
        for i, c in enumerate(self.consonants):
            if i == 0:
                continue
            if c in C.PHALA_LETTERS:
                # ম্ব is read as a conjunct (mb), not as ব-ফলা.
                if c == C.BA and self.consonants[i - 1] == C.MA:
                    continue
                out.append(c)
        return tuple(out)

    @property
    def core(self) -> tuple[str, ...]:
        """Cluster with phala letters removed (the conjunct proper)."""
        ph = list(self.phalas)
        out = []
        for i, c in enumerate(self.consonants):
            if i > 0 and c in ph:
                ph.remove(c)
                continue
            out.append(c)
        return tuple(out)

    @property
    def is_conjunct(self) -> bool:
        return len(self.core) >= 2

    @property
    def core_text(self) -> str:
        return C.VIRAMA.join(self.core)

    def patterns(self) -> list[str]:
        """Stable pattern keys this unit contains (used for weak-pattern counts)."""
        keys: list[str] = []
        if self.kind == "vowel" and self.vowel:
            keys.append(f"vowel:{self.vowel}")
        if self.kind == "consonant":
            if self.is_conjunct:
                keys.append(f"conj:{self.core_text}")
            elif self.core:
                keys.append(f"letter:{self.core[0]}")
            if self.reph:
                keys.append("reph")
            for p in self.phalas:
                keys.append(f"phala:{p}")
            if self.kar:
                keys.append(f"kar:{self.kar}")
            if self.hasanta:
                keys.append("hasanta")
        for s in self.signs:
            keys.append(f"sign:{s}")
        return keys


def _consume_signs(chars: str, j: int) -> tuple[tuple[str, ...], int]:
    signs: list[str] = []
    while j < len(chars) and chars[j] in C.SIGNS:
        signs.append(chars[j])
        j += 1
    return tuple(signs), j


def segment_normalized(word: str) -> list[Unit]:
    """Segment an already-normalised word into units."""
    units: list[Unit] = []
    i, n = 0, len(word)
    while i < n:
        ch = word[i]
        start = i
        if ch in C.CONSONANTS:
            cluster = [ch]
            j = i + 1
            if j < n and word[j] == C.NUKTA:  # stray nukta on a consonant
                j += 1
            while j + 1 < n and word[j] == C.VIRAMA and word[j + 1] in C.CONSONANTS:
                cluster.append(word[j + 1])
                j += 2
                if j < n and word[j] == C.NUKTA:
                    j += 1
            hasanta = False
            if j < n and word[j] == C.VIRAMA:
                hasanta = True
                j += 1
            reph = False
            if len(cluster) >= 2 and cluster[0] == C.RA:
                reph = True
                cluster = cluster[1:]
            kar = None
            if j < n and word[j] in C.VOWEL_SIGNS:
                kar = word[j]
                j += 1
            signs, j = _consume_signs(word, j)
            units.append(
                Unit(
                    text=word[start:j],
                    kind="consonant",
                    consonants=tuple(cluster),
                    reph=reph,
                    kar=kar,
                    signs=signs,
                    hasanta=hasanta,
                    start=start,
                    end=j,
                )
            )
            i = j
        elif ch in C.INDEPENDENT_VOWELS:
            signs, j = _consume_signs(word, i + 1)
            units.append(
                Unit(text=word[start:j], kind="vowel", vowel=ch, signs=signs, start=start, end=j)
            )
            i = j
        elif ch == C.KHANDA_TA:
            signs, j = _consume_signs(word, i + 1)
            units.append(
                Unit(
                    text=word[start:j],
                    kind="consonant",
                    consonants=(C.KHANDA_TA,),
                    signs=signs,
                    start=start,
                    end=j,
                )
            )
            i = j
        else:
            # Digits, stray signs or non-Bangla characters: one unit each,
            # with any following signs attached.
            signs, j = _consume_signs(word, i + 1)
            units.append(Unit(text=word[start:j], kind="other", signs=signs, start=start, end=j))
            i = j
    return units


def segment_word(word: str) -> list[Unit]:
    """Normalise and segment a single word."""
    return segment_normalized(normalize_word(word))


@dataclass
class WordUnits:
    norm: str
    units: list[Unit] = field(default_factory=list)

    @property
    def texts(self) -> list[str]:
        return [u.text for u in self.units]


def analyze_word(word: str) -> WordUnits:
    norm = normalize_word(word)
    return WordUnits(norm=norm, units=segment_normalized(norm))
