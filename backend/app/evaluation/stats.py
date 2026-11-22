"""Small, dependency-light statistics for the benchmark report."""

from __future__ import annotations

import math
from collections import Counter
from typing import Sequence

from ..alignment.sequence import levenshtein


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float | None, float | None, float | None]:
    """Proportion with a Wilson 95% confidence interval: (p, low, high)."""
    if n == 0:
        return None, None, None
    if not 0 <= k <= n:
        raise ValueError(f"wilson interval needs 0 <= k <= n (got {k}/{n})")
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return p, max(0.0, centre - half), min(1.0, centre + half)


def rate(k: int, n: int) -> dict:
    """An error rate that can exceed 1 (CER/WER): no binomial interval."""
    return {"k": k, "n": n, "value": k / n if n else None, "ci_low": None, "ci_high": None}


def proportion(k: int, n: int) -> dict:
    p, lo, hi = wilson(k, n)
    return {"k": k, "n": n, "value": p, "ci_low": lo, "ci_high": hi}


def cohen_kappa(a: Sequence[str], b: Sequence[str]) -> float | None:
    if len(a) != len(b) or not a:
        return None
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb.get(k, 0) for k in ca) / (n * n)
    if pe == 1:
        return 1.0
    return (po - pe) / (1 - pe)


def _ranks(x: Sequence[float]) -> list[float]:
    order = sorted(range(len(x)), key=lambda i: x[i])
    ranks = [0.0] * len(x)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and x[order[j + 1]] == x[order[i]]:
            j += 1
        r = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = r
        i = j + 1
    return ranks


def spearman(x: Sequence[float], y: Sequence[float]) -> float | None:
    if len(x) != len(y) or len(x) < 3:
        return None
    rx, ry = _ranks(x), _ranks(y)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    vx = math.sqrt(sum((a - mx) ** 2 for a in rx))
    vy = math.sqrt(sum((b - my) ** 2 for b in ry))
    if vx == 0 or vy == 0:
        return None
    return cov / (vx * vy)


def error_rate(ref: Sequence[str], hyp: Sequence[str]) -> tuple[int, int]:
    """(edits, reference length) for CER (characters) or WER (words)."""
    return levenshtein(list(ref), list(hyp)), len(ref)
