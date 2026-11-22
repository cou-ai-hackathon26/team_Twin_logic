"""Two-level alignment: passage words to recognised words, then units inside words.

Word level uses a weighted edit distance whose substitution cost is the
normalised *grapheme-unit* distance between the two words. It also allows
two extra moves that speech recognisers need:

* merge: two passage words recognised as one (a missing space),
* split: one passage word recognised as two (a pause inside a word).

Orthography is the primary basis. Phonetic similarity only lowers costs so
the right units are paired; it never turns a substitution into a match.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from ..bangla.phonetics import unit_sub_cost
from ..bangla.segment import Unit
from .sequence import Op, align

_unit_cost_cache: dict[tuple[str, str], float] = {}


def cached_unit_cost(a: Unit, b: Unit) -> float:
    key = (a.text, b.text)
    v = _unit_cost_cache.get(key)
    if v is None:
        v = unit_sub_cost(a, b)
        if len(_unit_cost_cache) > 200_000:
            _unit_cost_cache.clear()
        _unit_cost_cache[key] = v
    return v


def align_units(exp: list[Unit], rec: list[Unit]) -> tuple[list[Op], float]:
    return align(exp, rec, cached_unit_cost, 1.0, 1.0)


def word_distance(exp: list[Unit], rec: list[Unit]) -> float:
    """Normalised unit-level distance in [0, 1]."""
    if not exp and not rec:
        return 0.0
    if [u.text for u in exp] == [u.text for u in rec]:
        return 0.0
    _, cost = align_units(exp, rec)
    return min(1.0, cost / max(len(exp), len(rec), 1))


@dataclass
class AlignedGroup:
    kind: str  # match | sub | del | ins | merge | split
    exp: list[int]
    rec: list[int]
    cost: float


MERGE_PENALTY = 0.15
DEL_COST = 1.0
INS_COST = 1.0
# A substitution of two unrelated words (distance 1.0) costs a little less
# than deleting one and inserting the other, so real misreads stay misreads,
# but a cheap repetition plus a deletion can win (see REPEAT_INS_COST).
SUB_SCALE = 1.6
REPEAT_INS_COST = 0.4
MAX_GROUP = 3  # up to 3 words joined or split by the recogniser
MERGE_MAX_DIST = 0.4


def align_words(
    exp: list[list[Unit]],
    rec: list[list[Unit]],
    is_equivalent: Callable[[int, int], bool] | None = None,
    band: int | None = None,
) -> list[AlignedGroup]:
    """Align passage words ``exp`` with recognised words ``rec``.

    ``is_equivalent(i, j)`` may declare a pair identical (accepted variants).
    """
    n, m = len(exp), len(rec)
    if band is None:
        band = max(12, int(0.35 * max(n, m)) + abs(n - m))
    dist_cache: dict[tuple[int, int], float] = {}

    def in_band(i: int, j: int) -> bool:
        # i, j are 0-based word indices; compare relative position
        if n == 0 or m == 0:
            return True
        return abs(i * m / n - j) <= band

    def d(i: int, j: int) -> float:
        key = (i, j)
        v = dist_cache.get(key)
        if v is None:
            if is_equivalent is not None and is_equivalent(i, j):
                v = 0.0
            elif not in_band(i, j):
                v = 1.0
            else:
                v = word_distance(exp[i], rec[j])
            dist_cache[key] = v
        return v

    def d_group(i0: int, i1: int, j0: int, j1: int) -> float:
        """Distance between exp[i0:i1] joined and rec[j0:j1] joined."""
        if not in_band(i0, j0):
            return 1.0
        e = [u for w in exp[i0:i1] for u in w]
        r = [u for w in rec[j0:j1] for u in w]
        return word_distance(e, r)

    rec_text = ["".join(u.text for u in r) for r in rec]
    INF = float("inf")
    D = [[INF] * (m + 1) for _ in range(n + 1)]
    back: list[list[tuple | None]] = [[None] * (m + 1) for _ in range(n + 1)]
    D[0][0] = 0.0
    for i in range(0, n + 1):
        for j in range(0, m + 1):
            if i == 0 and j == 0:
                continue
            best, arg = INF, None
            if i > 0 and j > 0:
                c = SUB_SCALE * d(i - 1, j - 1)
                v = D[i - 1][j - 1] + c
                if v < best - 1e-12:
                    best, arg = v, ("sub" if c > 0 else "match", c)
            if i > 0:
                v = D[i - 1][j] + DEL_COST
                if v < best - 1e-12:
                    best, arg = v, ("del", DEL_COST)
            if j > 0:
                ic = INS_COST
                # repetition: same word recognised twice, or the word just read again
                if (j > 1 and rec_text[j - 1] == rec_text[j - 2]) or (i > 0 and d(i - 1, j - 1) == 0.0):
                    ic = REPEAT_INS_COST
                v = D[i][j - 1] + ic
                if v < best - 1e-12:
                    best, arg = v, ("ins", ic)
            for k in range(2, MAX_GROUP + 1):
                if i >= k and j > 0:  # k passage words recognised as one word
                    dd = d_group(i - k, i, j - 1, j)
                    if dd <= MERGE_MAX_DIST:
                        c = SUB_SCALE * dd + MERGE_PENALTY * (k - 1)
                        v = D[i - k][j - 1] + c
                        if v < best - 1e-12:
                            best, arg = v, ("merge", c, k, 1)
                if j >= k and i > 0:  # one passage word recognised as k words
                    dd = d_group(i - 1, i, j - k, j)
                    if dd <= MERGE_MAX_DIST:
                        c = SUB_SCALE * dd + MERGE_PENALTY * (k - 1)
                        v = D[i - 1][j - k] + c
                        if v < best - 1e-12:
                            best, arg = v, ("split", c, 1, k)
            D[i][j], back[i][j] = best, arg

    groups: list[AlignedGroup] = []
    i, j = n, m
    while i > 0 or j > 0:
        arg = back[i][j]
        assert arg is not None
        kind, c = arg[0], arg[1]
        if kind in ("match", "sub"):
            groups.append(AlignedGroup(kind, [i - 1], [j - 1], c))
            i, j = i - 1, j - 1
        elif kind == "del":
            groups.append(AlignedGroup("del", [i - 1], [], c))
            i -= 1
        elif kind == "ins":
            groups.append(AlignedGroup("ins", [], [j - 1], c))
            j -= 1
        else:  # merge / split
            _, c, ke, kr = arg
            groups.append(AlignedGroup(kind, list(range(i - ke, i)), list(range(j - kr, j)), c))
            i, j = i - ke, j - kr
    groups.reverse()
    return groups
