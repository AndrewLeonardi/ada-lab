"""Small, dependency-free statistics for the hypothesis tests (checked against textbook values in tests)."""

from __future__ import annotations

import math


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float, float]:
    """Proportion k/n with its Wilson score interval (95% by default): (p, low, high)."""
    if n == 0:
        return float("nan"), 0.0, 1.0
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0.0, centre - half), min(1.0, centre + half)


def newcombe_diff(k1: int, n1: int, k2: int, n2: int) -> tuple[float, float, float]:
    """Difference p1 - p2 with Newcombe's hybrid score interval (from the two Wilson intervals)."""
    p1, l1, u1 = wilson(k1, n1)
    p2, l2, u2 = wilson(k2, n2)
    d = p1 - p2
    return d, d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2), d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)


def _logc(n: int, k: int) -> float:
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)


def fisher_exact(a: int, b: int, c: int, d: int, alternative: str = "two-sided") -> float:
    """Fisher's exact test for the 2x2 table [[a, b], [c, d]] (rows: groups; columns: event, no event).
    alternative: "two-sided", "less" (group 1 has the lower event odds) or "greater"."""
    r1, r2, c1, n = a + b, c + d, a + c, a + b + c + d
    lo, hi = max(0, c1 - r2), min(r1, c1)

    def pmf(x: int) -> float:
        return math.exp(_logc(r1, x) + _logc(r2, c1 - x) - _logc(n, c1))

    if alternative == "less":
        return min(1.0, sum(pmf(x) for x in range(lo, a + 1)))
    if alternative == "greater":
        return min(1.0, sum(pmf(x) for x in range(a, hi + 1)))
    p_obs = pmf(a)
    return min(1.0, sum(p for p in (pmf(x) for x in range(lo, hi + 1)) if p <= p_obs * (1 + 1e-7)))
