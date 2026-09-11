"""Tukey HSD / Tukey-Kramer all-pairs comparisons (SR-6, design section 7).

Uses the studentized range distribution with df = df_within. Balanced designs
reduce exactly to Tukey HSD; unbalanced designs use the Tukey-Kramer SE with the
(1/n_i + 1/n_j) term (never mean/min/max n). The reported p is the
studentized-range-adjusted p (NOT uncorrected t-tests).
"""

from __future__ import annotations

import itertools
import math
from typing import List, Sequence, Tuple

from .anova import InsufficientDataError, anova_oneway_raw
from .descriptive import _clean
from .distributions import studentized_range_ppf, studentized_range_sf
from .types import AnovaTable, PairwiseComparison, PostHocResult, RawGroup


def tukey_from_moments(labels: Sequence[str], ns: Sequence[int],
                       means: Sequence[float], ms_within: float,
                       df_within: float, alpha: float = 0.05,
                       order: Sequence[str] = None) -> PostHocResult:
    k = len(labels)
    if k < 2:
        raise InsufficientDataError("Post-hoc requires at least 2 groups.")
    if ms_within <= 0:
        raise InsufficientDataError("MS_within must be positive for Tukey.")

    balanced = len(set(ns)) == 1
    method = "Tukey HSD" if balanced else "Tukey-Kramer"

    if order is None:
        order = list(labels)
    pos = {lab: i for i, lab in enumerate(order)}
    idx = {lab: i for i, lab in enumerate(labels)}

    q_crit = studentized_range_ppf(1.0 - alpha, k, df_within)

    comparisons: List[PairwiseComparison] = []
    # iterate pairs in canonical order (group1 = earlier in `order`)
    lab_sorted = sorted(labels, key=lambda l: pos.get(l, 1e9))
    for a, b in itertools.combinations(lab_sorted, 2):
        ia, ib = idx[a], idx[b]
        na, nb = ns[ia], ns[ib]
        ma, mb = means[ia], means[ib]
        se = math.sqrt(ms_within / 2.0 * (1.0 / na + 1.0 / nb))
        diff = ma - mb
        q = abs(diff) / se
        p_adj = studentized_range_sf(q, k, df_within)
        ci_low = diff - q_crit * se
        ci_high = diff + q_crit * se
        comparisons.append(PairwiseComparison(
            group1=a, group2=b, mean1=ma, mean2=mb, diff=diff, se=se,
            statistic=q, df=df_within, ci_low=ci_low, ci_high=ci_high,
            p_adjusted=p_adj, significant=(p_adj < alpha),
        ))

    return PostHocResult(method=method, alpha=alpha, comparisons=comparisons,
                         labels=lab_sorted)


def tukey_raw(groups: Sequence[RawGroup], alpha: float = 0.05,
              order: Sequence[str] = None, table: AnovaTable = None) -> PostHocResult:
    if table is None:
        table = anova_oneway_raw(groups)
    labels, ns, means = [], [], []
    for g in groups:
        v = _clean(g.values)
        labels.append(g.label)
        ns.append(len(v))
        means.append(math.fsum(v) / len(v))
    return tukey_from_moments(labels, ns, means, table.ms_within,
                              table.df_within, alpha=alpha, order=order)
