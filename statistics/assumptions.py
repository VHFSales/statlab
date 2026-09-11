"""Assumption diagnostics (SR-5, design section 6).

Levene (mean-centered) and Brown-Forsythe (median-centered) tests for homogeneity
of variance; residuals and Q-Q points; Shapiro-Wilk on residuals (Royston 1992);
and the independence disclaimer. None of these is used as an absolute gate.
"""

from __future__ import annotations

import math
from typing import List, Sequence, Tuple

from .descriptive import _clean, median as _median
from .distributions import f_sf, norm_ppf
from .types import LeveneResult, RawGroup, ShapiroResult


INDEPENDENCE_NOTE = (
    "A independência das observações depende do delineamento experimental e não "
    "pode ser confirmada somente a partir dos valores numéricos."
)


def independence_note() -> str:
    return INDEPENDENCE_NOTE


def _levene_like(groups: Sequence[RawGroup], center: str) -> LeveneResult:
    cells = [(_clean(g.values)) for g in groups]
    cells = [c for c in cells if len(c) > 0]
    k = len(cells)
    if k < 2:
        raise ValueError("Need at least 2 non-empty groups.")

    z_groups: List[List[float]] = []
    for c in cells:
        if center == "mean":
            ctr = math.fsum(c) / len(c)
        elif center == "median":
            ctr = _median(sorted(c))
        else:
            raise ValueError("center must be 'mean' or 'median'")
        z_groups.append([abs(x - ctr) for x in c])

    # One-way ANOVA F on the z deviations.
    ns = [len(z) for z in z_groups]
    N = sum(ns)
    means = [math.fsum(z) / n for z, n in zip(z_groups, ns)]
    grand = math.fsum(math.fsum(z) for z in z_groups) / N
    ss_b = math.fsum(n * (m - grand) ** 2 for m, n in zip(means, ns))
    ss_w = math.fsum(
        math.fsum((x - m) ** 2 for x in z) for z, m in zip(z_groups, means)
    )
    df1 = k - 1
    df2 = N - k
    if ss_w == 0.0:
        # all deviations identical within groups -> statistic undefined
        return LeveneResult(statistic=math.nan, df1=df1, df2=df2, p=math.nan,
                            center=center)
    W = (ss_b / df1) / (ss_w / df2)
    p = f_sf(W, df1, df2)
    return LeveneResult(statistic=W, df1=df1, df2=df2, p=p, center=center)


def levene(groups: Sequence[RawGroup]) -> LeveneResult:
    """Levene's test (mean-centered)."""
    return _levene_like(groups, "mean")


def brown_forsythe(groups: Sequence[RawGroup]) -> LeveneResult:
    """Brown-Forsythe test (median-centered) - robust default."""
    return _levene_like(groups, "median")


def residuals(groups: Sequence[RawGroup]) -> List[float]:
    """Model residuals e_ij = x_ij - mean_i (raw data only)."""
    out: List[float] = []
    for g in groups:
        c = _clean(g.values)
        if not c:
            continue
        m = math.fsum(c) / len(c)
        out.extend(x - m for x in c)
    return out


def qq_points(values: Sequence[float]) -> List[Tuple[float, float]]:
    """(theoretical normal quantile, sample value) using Blom plotting positions."""
    x = sorted(_clean(values))
    n = len(x)
    pts = []
    for i, v in enumerate(x, start=1):
        p = (i - 0.375) / (n + 0.25)
        pts.append((norm_ppf(p), v))
    return pts


def variance_ratio(groups: Sequence[RawGroup]) -> float:
    """max(variance)/min(variance) across groups - a holistic heteroscedasticity cue."""
    vs = []
    for g in groups:
        c = _clean(g.values)
        if len(c) < 2:
            continue
        m = math.fsum(c) / len(c)
        vs.append(math.fsum((x - m) ** 2 for x in c) / (len(c) - 1))
    vs = [v for v in vs if v > 0]
    if len(vs) < 2:
        return math.nan
    return max(vs) / min(vs)


# --------------------------------------------------------------------------- #
# Shapiro-Wilk (Royston 1992 approximation)
# --------------------------------------------------------------------------- #
def shapiro_wilk(values: Sequence[float]) -> ShapiroResult:
    """Shapiro-Wilk test using Royston's (1992) approximation.

    Valid roughly for 3 <= n <= 5000. Returned as ONE diagnostic among several;
    never used as an absolute gate for ANOVA (SR-5).
    """
    x = sorted(_clean(values))
    n = len(x)
    if n < 3:
        return ShapiroResult(statistic=math.nan, p=math.nan, n=n,
                             note="Shapiro-Wilk requires n >= 3.")

    # Expected values of standard normal order statistics (Blom) and their norm.
    m = [norm_ppf((i - 0.375) / (n + 0.25)) for i in range(1, n + 1)]
    m2 = math.fsum(v * v for v in m)
    rsn = 1.0 / math.sqrt(n)

    a = [0.0] * n
    # Royston polynomial corrections for the two extreme weights.
    c1 = [0.0, 0.221157, -0.147981, -2.071190, 4.434685, -2.706056]
    c2 = [0.0, 0.042981, -0.293762, -1.752461, 5.682633, -3.582633]

    def poly(c, x_):
        return math.fsum(c[i] * x_ ** i for i in range(len(c)))

    if n == 3:
        a[0] = math.sqrt(0.5)
        a[-1] = -a[0]
    else:
        an = m[-1] / math.sqrt(m2)
        a_n = poly(c1, rsn) + an
        if n > 5:
            an1 = m[-2] / math.sqrt(m2)
            a_n1 = poly(c2, rsn) + an1
            phi = (m2 - 2.0 * m[-1] ** 2 - 2.0 * m[-2] ** 2) / (
                1.0 - 2.0 * a_n ** 2 - 2.0 * a_n1 ** 2
            )
            a[-1] = a_n
            a[0] = -a_n
            a[-2] = a_n1
            a[1] = -a_n1
            start = 2
            end = n - 2
        else:
            phi = (m2 - 2.0 * m[-1] ** 2) / (1.0 - 2.0 * a_n ** 2)
            a[-1] = a_n
            a[0] = -a_n
            start = 1
            end = n - 1
        for i in range(start, end):
            a[i] = m[i] / math.sqrt(phi)

    # W statistic
    xbar = math.fsum(x) / n
    num = math.fsum(a[i] * x[i] for i in range(n)) ** 2
    den = math.fsum((xi - xbar) ** 2 for xi in x)
    if den == 0:
        return ShapiroResult(statistic=math.nan, p=math.nan, n=n,
                             note="Zero variance; Shapiro-Wilk undefined.")
    W = num / den

    # p-value (Royston 1992)
    if n == 3:
        pi6 = 6.0 / math.pi
        stqr = math.asin(math.sqrt(0.75))
        p = pi6 * (math.asin(math.sqrt(W)) - stqr)
        p = max(0.0, min(1.0, 1.0 - p))
        return ShapiroResult(statistic=W, p=p, n=n)

    lnn = math.log(n)
    if n <= 11:
        gamma = -2.273 + 0.459 * n
        w1 = -math.log(gamma - math.log(1.0 - W))
        mu = 0.5440 - 0.39978 * n + 0.025054 * n * n - 0.0006714 * n ** 3
        sigma = math.exp(1.3822 - 0.77857 * n + 0.062767 * n * n - 0.0020322 * n ** 3)
    else:
        w1 = math.log(1.0 - W)
        mu = -1.5861 - 0.31082 * lnn - 0.083751 * lnn ** 2 + 0.0038915 * lnn ** 3
        sigma = math.exp(-0.4803 - 0.082676 * lnn + 0.0030302 * lnn ** 2)
    z = (w1 - mu) / sigma
    from .distributions import norm_cdf
    p = 1.0 - norm_cdf(z)
    return ShapiroResult(statistic=W, p=max(0.0, min(1.0, p)), n=n)
