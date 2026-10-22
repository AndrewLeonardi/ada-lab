"""The statistics used by the hypothesis tests, against known values."""
import math

from ada.stats import fisher_exact, newcombe_diff, wilson


def close(a, b, tol=5e-4):
    return abs(a - b) <= tol


def test_wilson_interval():
    # Newcombe (1998), example 81/263: 0.3080 (0.2553 to 0.3662)
    p, lo, hi = wilson(81, 263)
    assert close(p, 0.3080) and close(lo, 0.2553) and close(hi, 0.3662)
    # 0 of 10: 0 to 0.2775
    assert wilson(0, 10)[1] == 0.0 and close(wilson(0, 10)[2], 0.2775)


def test_newcombe_difference():
    # Newcombe (1998) example 56/70 vs 48/80: difference 0.2000, 95% CI 0.0524 to 0.3339
    d, lo, hi = newcombe_diff(56, 70, 48, 80)
    assert close(d, 0.2) and close(lo, 0.0524, 1e-3) and close(hi, 0.3339, 1e-3)


def test_fisher_exact():
    # the classic tea-tasting table [[3, 1], [1, 3]]: two-sided p = 0.4857, one-sided (greater) 0.2429
    assert close(fisher_exact(3, 1, 1, 3), 0.4857)
    assert close(fisher_exact(3, 1, 1, 3, "greater"), 0.2429)
    assert close(fisher_exact(1, 3, 3, 1, "less"), 0.2429)
    # [[1, 9], [11, 3]]: two-sided p = 0.002759 (a standard textbook example)
    assert close(fisher_exact(1, 9, 11, 3), 0.002759, 1e-5)
    assert not math.isnan(fisher_exact(0, 0, 0, 5))
