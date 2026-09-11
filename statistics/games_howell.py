"""Games-Howell all-pairs comparisons (SR-7, design section 8).

For heteroscedastic data (companion to Welch's ANOVA). Uses an UNPOOLED standard
error and a PER-PAIR Welch-Satterthwaite degrees of freedom (critical review
item 2). The studentized range is evaluated at that per-pair df.
"""

from __future__ import annotations

import itertools
import math
from typing import List, Sequence

from .anova import InsufficientDataError
from .descriptive import _clean
from .distributions import studentized_range_ppf, studentized_range_sf
from .types import PairwiseComparison, PostHocResult, RawGroup


def games_howell_from_moments(labels: Sequence[str], ns: Sequence[int],
                              means: Sequence[float], variances: Sequence[float],
                              alpha: float = 0.05,
                              order: Sequence[str] = None) -> PostHocResult:
    k = len(labels)
    if k < 2:
        raise InsufficientDataError("Post-hoc requires at least 2 groups.")
    for n, var in zip(ns, variances):
        if n < 2:
            raise InsufficientDataError("Games-Howell requires n >= 2 in every group.")
        if var <= 0:
            raise InsufficientDataError(
                "Games-Howell is undefined when a group has zero variance."
            )

    if order is None:
        order = list(labels)
    pos = {lab: i for i, lab in enumerate(order)}
    idx = {lab: i for i, lab in enumerate(labels)}
    lab_sorted = sorted(labels, key=lambda l: pos.get(l, 1e9))

    comparisons: List[PairwiseComparison] = []
    for a, b in itertools.combinations(lab_sorted, 2):
        ia, ib = idx[a], idx[b]
        na, nb = ns[ia], ns[ib]
        va, vb = variances[ia], variances[ib]
        ma, mb = means[ia], means[ib]

        va_na = va / na
        vb_nb = vb / nb
        se = math.sqrt(va_na + vb_nb)             # unpooled SE of the difference
        diff = ma - mb
        # studentized range statistic uses SE/sqrt(2)
        q = abs(diff) / (se / math.sqrt(2.0))
        # Welch-Satterthwaite per-pair df
        df = (va_na + vb_nb) ** 2 / (
            (va_na ** 2) / (na - 1) + (vb_nb ** 2) / (nb - 1)
        )
        p_adj = studentized_range_sf(q, k, df)
        q_crit = studentized_range_ppf(1.0 - alpha, k, df)
        margin = q_crit * se / math.sqrt(2.0)
        comparisons.append(PairwiseComparison(
            group1=a, group2=b, mean1=ma, mean2=mb, diff=diff, se=se,
            statistic=q, df=df, ci_low=diff - margin, ci_high=diff + margin,
            p_adjusted=p_adj, significant=(p_adj < alpha),
        ))

    return PostHocResult(method="Games-Howell", alpha=alpha,
                         comparisons=comparisons, labels=lab_sorted)


def games_howell_raw(groups: Sequence[RawGroup], alpha: float = 0.05,
                     order: Sequence[str] = None) -> PostHocResult:
    labels, ns, means, variances = [], [], [], []
    for g in groups:
        v = _clean(g.values)
        n = len(v)
        if n < 2:
            raise InsufficientDataError(
                f"Group '{g.label}': Games-Howell requires n >= 2."
            )
        m = math.fsum(v) / n
        var = math.fsum((x - m) ** 2 for x in v) / (n - 1)
        labels.append(g.label); ns.append(n); means.append(m); variances.append(var)
    return games_howell_from_moments(labels, ns, means, variances,
                                     alpha=alpha, order=order)
