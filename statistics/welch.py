"""Welch's ANOVA (SR-3, design section 5), Welch (1951).

Computed from per-group (n, mean, variance), so it serves both raw and summary
inputs. Does NOT assume homogeneity of variance. Refuses zero-variance groups
(critical review item 8).
"""

from __future__ import annotations

import math
from typing import List, Sequence, Tuple

from .anova import InsufficientDataError
from .descriptive import _clean
from .distributions import f_sf
from .types import RawGroup, SummaryGroup, WelchResult


def _welch_from_moments(ns: List[int], means: List[float],
                        variances: List[float]) -> WelchResult:
    k = len(ns)
    if k < 2:
        raise InsufficientDataError("Welch's ANOVA requires at least 2 groups.")
    for n, var in zip(ns, variances):
        if n < 2:
            raise InsufficientDataError(
                "Welch's ANOVA requires n >= 2 in every group."
            )
        if var <= 0.0:
            raise InsufficientDataError(
                "Welch's ANOVA is undefined when a group has zero variance "
                "(infinite weight). Inspect that group."
            )

    w = [n / var for n, var in zip(ns, variances)]
    W = math.fsum(w)
    xbar = math.fsum(wi * m for wi, m in zip(w, means)) / W

    A = math.fsum(wi * (m - xbar) ** 2 for wi, m in zip(w, means)) / (k - 1)
    # sum term used by both B and df2
    term = math.fsum((1.0 - wi / W) ** 2 / (n - 1) for wi, n in zip(w, ns))
    B = (2.0 * (k - 2) / (k * k - 1.0)) * term
    F = A / (1.0 + B)
    df1 = k - 1
    df2 = (k * k - 1.0) / (3.0 * term)
    p = f_sf(F, df1, df2)

    return WelchResult(statistic=F, df1=df1, df2=df2, p=p, k=k, n_total=sum(ns))


def welch_anova_raw(groups: Sequence[RawGroup]) -> WelchResult:
    ns, means, variances = [], [], []
    for g in groups:
        v = _clean(g.values)
        n = len(v)
        if n < 2:
            raise InsufficientDataError(
                f"Group '{g.label}': Welch's ANOVA requires n >= 2."
            )
        m = math.fsum(v) / n
        var = math.fsum((x - m) ** 2 for x in v) / (n - 1)
        ns.append(n); means.append(m); variances.append(var)
    return _welch_from_moments(ns, means, variances)


def welch_anova_summary(groups: Sequence[SummaryGroup]) -> WelchResult:
    ns = [int(g.n) for g in groups]
    means = [g.mean for g in groups]
    variances = [g.sd ** 2 for g in groups]
    return _welch_from_moments(ns, means, variances)
