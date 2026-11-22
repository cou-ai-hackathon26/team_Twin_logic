"""Phonetic helpers for alignment.

Two different ideas live here and must not be confused:

* **Homophone spellings.** Some Bangla letters are written differently but
  pronounced the same in standard reading (ই/ঈ-কার, শ/ষ/স, ন/ণ, জ/য ...).
  A speech model cannot tell them apart from audio, so a difference that is
  *only* between such letters is not evidence that the child misread.
  These are handled as "spelling-only" differences.

* **Phonetic similarity.** Letters that sound close but different (ক/খ,
  ড/ড় ...). This is used *only* to lower the alignment cost so the aligner
  pairs the right units; a similar-sounding substitution is still an error.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import chars as C
from .segment import Unit

# --- homophone classes: map each member to a class representative -------
_HOMOPHONE_GROUPS: list[str] = [
    "িী",  # ি ী
    "ুূ",  # ু ূ
    "ইঈ",  # ই ঈ
    "উঊ",  # উ ঊ
    "শষস",  # শ ষ স
    "নণ",  # ন ণ
    "জয",  # জ য
    "তৎ",  # ত ৎ
    "ড়ঢ়",  # ড় ঢ়
    "ংঙ",  # ং ঙ
]
HOMOPHONE_REP: dict[str, str] = {}
for _g in _HOMOPHONE_GROUPS:
    for _ch in _g:
        HOMOPHONE_REP[_ch] = _g[0]

# --- similar-sounding groups (alignment cost only) ------------------------
_SIMILAR_GROUPS: list[str] = [
    "কখ", "গঘ", "চছ", "জঝ", "টঠ", "ডঢ", "তথ", "দধ", "পফ", "বভ",
    "ডড়", "ঢঢ়", "রড়", "লন", "হঃ",
    "াঅ", "েৈ", "োৌ", "োু",
]
SIMILAR: set[frozenset[str]] = set()
for _g in _SIMILAR_GROUPS:
    for a in _g:
        for b in _g:
            if a != b:
                SIMILAR.add(frozenset((a, b)))


def homophone_key(text: str) -> str:
    return "".join(HOMOPHONE_REP.get(ch, ch) for ch in text)


def char_sub_cost(a: str | None, b: str | None) -> float:
    """Cost of replacing one component with another, in [0, 1]."""
    if a == b:
        return 0.0
    if a is None or b is None:
        return 1.0
    if HOMOPHONE_REP.get(a, a) == HOMOPHONE_REP.get(b, b):
        return 0.15
    if frozenset((a, b)) in SIMILAR:
        return 0.5
    return 1.0


def _seq_cost(a: tuple[str, ...], b: tuple[str, ...]) -> float:
    """Small edit distance between two short letter tuples (normalised to 0..1)."""
    if a == b:
        return 0.0
    n, m = len(a), len(b)
    d = [[0.0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        d[i][0] = float(i)
    for j in range(m + 1):
        d[0][j] = float(j)
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            d[i][j] = min(
                d[i - 1][j] + 1.0,
                d[i][j - 1] + 1.0,
                d[i - 1][j - 1] + char_sub_cost(a[i - 1], b[j - 1]),
            )
    return min(1.0, d[n][m] / max(n, m, 1))


# Component weights for a unit substitution. They sum to more than 1 so that a
# unit differing in everything costs the maximum of 1.0.
_W_CORE, _W_KAR, _W_REPH, _W_PHALA, _W_SIGN, _W_KIND = 0.65, 0.35, 0.3, 0.3, 0.15, 1.0


def unit_sub_cost(a: Unit, b: Unit) -> float:
    """Alignment cost of pairing expected unit ``a`` with recognised unit ``b``."""
    if a.text == b.text:
        return 0.0
    if a.kind != b.kind:
        # vowel letter vs consonant cluster etc. Allow a cheaper pairing for
        # vowel letter vs. kar-only differences (e.g. "এ" vs "ে" never occurs,
        # but অ/আ vs consonant does not sound alike).
        return _W_KIND
    cost = 0.0
    if a.kind == "vowel":
        cost += _W_CORE * char_sub_cost(a.vowel, b.vowel)
    elif a.kind == "consonant":
        cost += _W_CORE * _seq_cost(a.core, b.core)
        cost += _W_KAR * char_sub_cost(a.kar, b.kar) if (a.kar or b.kar) else 0.0
        cost += _W_REPH * (a.reph != b.reph)
        cost += _W_PHALA * _seq_cost(a.phalas, b.phalas) if (a.phalas or b.phalas) else 0.0
    else:
        cost += _W_CORE * (a.text != b.text)
    if a.signs != b.signs:
        cost += _W_SIGN * _seq_cost(a.signs, b.signs)
    return min(1.0, max(cost, 0.05))


def units_homophone_equal(a: Unit, b: Unit) -> bool:
    return homophone_key(a.text) == homophone_key(b.text)


@dataclass
class UnitError:
    pattern: str  # pattern key that this error is attributed to
    kind: str  # "dropped" | "substituted" | "added"
    expected: str | None
    heard: str | None
    description_bn: str
    description_en: str


def diff_units(exp: Unit, got: Unit | None) -> list[UnitError]:
    """Explain how ``got`` differs from ``exp`` in terms of teachable parts.

    Spelling-only (homophone) differences are not reported.
    """
    from .patterns import pattern_label  # local import to avoid a cycle

    errs: list[UnitError] = []

    def add(pattern: str, kind: str, e: str | None, h: str | None, bn: str, en: str) -> None:
        errs.append(UnitError(pattern, kind, e, h, bn, en))

    if got is None:
        # The whole unit is missing: attribute it to its most specific parts.
        keys = exp.patterns() or [f"letter:{exp.text}"]
        specific = [k for k in keys if not k.startswith("letter:")] or keys
        for k in specific:
            lab = pattern_label(k)
            add(k, "dropped", exp.text, None, f"{lab['bn']} বাদ পড়েছে", f"{lab['en']} dropped")
        return errs

    if units_homophone_equal(exp, got):
        return errs

    if exp.kind != got.kind or exp.kind == "other":
        keys = [k for k in exp.patterns() if not k.startswith(("kar:", "sign:"))] or exp.patterns()
        for k in keys or [f"letter:{exp.text}"]:
            lab = pattern_label(k)
            add(k, "substituted", exp.text, got.text,
                f"{exp.text} এর জায়গায় {got.text}", f"{lab['en']}: read {got.text} for {exp.text}")
        return errs

    if exp.kind == "vowel":
        if homophone_key(exp.vowel or "") != homophone_key(got.vowel or ""):
            k = f"vowel:{exp.vowel}"
            add(k, "substituted", exp.vowel, got.vowel,
                f"{exp.vowel} এর জায়গায় {got.vowel}", f"Vowel {exp.vowel} read as {got.vowel}")
    else:
        # reph
        if exp.reph and not got.reph:
            add("reph", "dropped", "র্", None, "রেফ বাদ পড়েছে", "Reph (র্) dropped")
        elif got.reph and not exp.reph:
            add(_main_key(exp), "added", None, "র্", "অতিরিক্ত রেফ", "Extra reph added")
        # phalas
        exp_ph, got_ph = list(exp.phalas), list(got.phalas)
        for p in exp.phalas:
            if p in got_ph:
                got_ph.remove(p)
                exp_ph.remove(p)
        for p in exp_ph:
            name = C.PHALA_NAMES.get(p, p)
            add(f"phala:{p}", "dropped", p, None, f"{name} বাদ পড়েছে", f"{name} dropped")
        for p in got_ph:
            name = C.PHALA_NAMES.get(p, p)
            add(_main_key(exp), "added", None, p, f"অতিরিক্ত {name}", f"Extra {name} added")
        # core consonant / conjunct
        if homophone_key("".join(exp.core)) != homophone_key("".join(got.core)):
            k = _main_key(exp)
            if exp.is_conjunct and len(got.core) < len(exp.core):
                bn = f"যুক্তাক্ষর {exp.core_text} ভেঙে {got.core_text or '—'} পড়েছে"
                en = f"Conjunct {exp.core_text} simplified to {got.core_text or '—'}"
            elif exp.is_conjunct:
                bn = f"যুক্তাক্ষর {exp.core_text} এর জায়গায় {got.core_text}"
                en = f"Conjunct {exp.core_text} read as {got.core_text}"
            else:
                bn = f"{exp.core_text} এর জায়গায় {got.core_text}"
                en = f"Letter {exp.core_text} read as {got.core_text}"
            add(k, "substituted", exp.core_text, got.core_text, bn, en)
        # kar
        ek, gk = exp.kar, got.kar
        if homophone_key(ek or "") != homophone_key(gk or ""):
            if ek and not gk:
                name = C.KAR_NAMES.get(ek, "কার")
                add(f"kar:{ek}", "dropped", ek, None, f"{name} বাদ পড়েছে", f"Vowel sign {name} dropped")
            elif ek and gk:
                n1, n2 = C.KAR_NAMES.get(ek, ek), C.KAR_NAMES.get(gk, gk)
                add(f"kar:{ek}", "substituted", ek, gk, f"{n1} এর জায়গায় {n2}", f"{n1} read as {n2}")
            else:
                name = C.KAR_NAMES.get(gk or "", "কার")
                add(_main_key(exp), "added", None, gk, f"অতিরিক্ত {name}", f"Extra vowel sign {name}")
        if exp.hasanta != got.hasanta and not errs:
            add("hasanta", "substituted", C.VIRAMA if exp.hasanta else None,
                C.VIRAMA if got.hasanta else None, "হসন্ত ভুল", "Hasanta read wrongly")
    # signs (both kinds)
    if homophone_key("".join(exp.signs)) != homophone_key("".join(got.signs)):
        for s in exp.signs:
            if s not in got.signs:
                name = C.SIGN_NAMES.get(s, s)
                add(f"sign:{s}", "dropped", s, None, f"{name} বাদ পড়েছে", f"{name} dropped")
        for s in got.signs:
            if s not in exp.signs:
                name = C.SIGN_NAMES.get(s, s)
                add(_main_key(exp), "added", None, s, f"অতিরিক্ত {name}", f"Extra {name}")
    if not errs and exp.text != got.text and homophone_key(exp.text) != homophone_key(got.text):
        k = _main_key(exp)
        add(k, "substituted", exp.text, got.text, f"{exp.text} এর জায়গায় {got.text}",
            f"Read {got.text} for {exp.text}")
    return errs


def _main_key(u: Unit) -> str:
    if u.kind == "vowel":
        return f"vowel:{u.vowel}"
    if u.is_conjunct:
        return f"conj:{u.core_text}"
    if u.core:
        return f"letter:{u.core[0]}"
    return f"letter:{u.text}"
