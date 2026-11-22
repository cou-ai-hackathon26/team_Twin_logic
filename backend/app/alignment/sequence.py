"""Weighted sequence alignment (Levenshtein with arbitrary costs and backtrace)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence, TypeVar

A = TypeVar("A")
B = TypeVar("B")


@dataclass(frozen=True)
class Op:
    kind: str  # "match" | "sub" | "del" | "ins"
    i: int | None  # index in the reference (expected) sequence
    j: int | None  # index in the hypothesis (recognised) sequence
    cost: float = 0.0


def align(
    ref: Sequence[A],
    hyp: Sequence[B],
    sub_cost: Callable[[A, B], float],
    del_cost: float | Callable[[A], float] = 1.0,
    ins_cost: float | Callable[[B], float] = 1.0,
) -> tuple[list[Op], float]:
    """Minimum-cost alignment of ``ref`` to ``hyp``.

    Ties are broken in the order substitution/match, deletion, insertion, which
    keeps results deterministic.
    """
    n, m = len(ref), len(hyp)
    dc = del_cost if callable(del_cost) else (lambda _a, c=del_cost: c)
    ic = ins_cost if callable(ins_cost) else (lambda _b, c=ins_cost: c)
    INF = float("inf")
    D = [[INF] * (m + 1) for _ in range(n + 1)]
    back: list[list[int]] = [[0] * (m + 1) for _ in range(n + 1)]  # 1 diag, 2 up(del), 3 left(ins)
    D[0][0] = 0.0
    for i in range(1, n + 1):
        D[i][0] = D[i - 1][0] + dc(ref[i - 1])
        back[i][0] = 2
    for j in range(1, m + 1):
        D[0][j] = D[0][j - 1] + ic(hyp[j - 1])
        back[0][j] = 3
    subs: dict[tuple[int, int], float] = {}
    for i in range(1, n + 1):
        ri = ref[i - 1]
        di = dc(ri)
        for j in range(1, m + 1):
            s = sub_cost(ri, hyp[j - 1])
            subs[(i, j)] = s
            best, arg = D[i - 1][j - 1] + s, 1
            v = D[i - 1][j] + di
            if v < best - 1e-12:
                best, arg = v, 2
            v = D[i][j - 1] + ic(hyp[j - 1])
            if v < best - 1e-12:
                best, arg = v, 3
            D[i][j], back[i][j] = best, arg
    ops: list[Op] = []
    i, j = n, m
    while i > 0 or j > 0:
        b = back[i][j]
        if b == 1:
            s = subs[(i, j)]
            ops.append(Op("match" if s == 0 else "sub", i - 1, j - 1, s))
            i, j = i - 1, j - 1
        elif b == 2:
            ops.append(Op("del", i - 1, None, dc(ref[i - 1])))
            i -= 1
        else:
            ops.append(Op("ins", None, j - 1, ic(hyp[j - 1])))
            j -= 1
    ops.reverse()
    return ops, D[n][m]


def levenshtein(a: Sequence[object], b: Sequence[object]) -> int:
    """Plain edit distance (used for CER / WER)."""
    n, m = len(a), len(b)
    prev = list(range(m + 1))
    for i in range(1, n + 1):
        cur = [i] + [0] * m
        for j in range(1, m + 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] != b[j - 1]))
        prev = cur
    return prev[m]
