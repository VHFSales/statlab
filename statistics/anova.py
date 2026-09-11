"""One-way ANOVA, classical (SR-2, design section 4).

Works from raw data or from summary statistics (mean, sd, n). Uses the stable
two-pass sum-of-squares. No intermediate rounding.
"""

from __future__ import annotations

import math
from typing import List, Sequence, Tuple

from .distributions import f_sf
from .descriptive import _clean
from .types import AnovaTable, RawGroup, SummaryGroup


class InsufficientDataError(ValueError):
    """Raised when the data cannot support a valid ANOVA."""


def _cells_from_raw(groups: Sequence[RawGroup]) -> List[Tuple[str, List[float]]]:
    cells = []
    for g in groups:
        vals = _clean(g.values)
        cells.append((g.label, vals))
    return cells


def anova_oneway_raw(groups: Sequence[RawGroup]) -> AnovaTable:
    cells = _cells_from_raw(groups)
    k = len(cells)
    if k < 2:
        raise InsufficientDataError("ANOVA requires at least 2 groups.")
    ns = [len(v) for _, v in cells]
    if any(n < 1 for n in ns):
        raise InsufficientDataError("Every group must have at least 1 valid observation.")
    N = sum(ns)
    if N - k < 1:
        raise InsufficientDataError(
            "Insufficient within-group degrees of freedom (need N - k >= 1)."
        )

    means = [math.fsum(v) / n for (_, v), n in zip(cells, ns)]
    grand = math.fsum(math.fsum(v) for _, v in cells) / N

    ss_between = math.fsum(n * (m - grand) ** 2 for m, n in zip(means, ns))
    ss_within = math.fsum(
        math.fsum((x - m) ** 2 for x in v) for (_, v), m in zip(cells, means)
    )
    ss_total = math.fsum(
        math.fsum((x - grand) ** 2 for x in v) for _, v in cells
    )

    df_between = k - 1
    df_within = N - k
    df_total = N - 1
    ms_between = ss_between / df_between
    ms_within = ss_within / df_within

    if ms_within == 0.0:
        raise InsufficientDataError(
            "Within-group variance is zero; the F statistic is undefined. "
            "Check for constant groups or data-entry errors."
        )

    f = ms_between / ms_within
    p = f_sf(f, df_between, df_within)

    return AnovaTable(
        ss_between=ss_between, ss_within=ss_within, ss_total=ss_total,
        df_between=df_between, df_within=df_within, df_total=df_total,
        ms_between=ms_between, ms_within=ms_within, f=f, p=p,
        k=k, n_total=N, method="one-way ANOVA (raw data)",
    )


def anova_oneway_summary(groups: Sequence[SummaryGroup]) -> AnovaTable:
    """ANOVA reconstructed exactly from (mean, sd, n) per group (SR-13)."""
    k = len(groups)
    if k < 2:
        raise InsufficientDataError("ANOVA requires at least 2 groups.")
    for g in groups:
        if g.n is None or g.n < 1 or int(g.n) != g.n:
            raise InsufficientDataError(
                f"Group '{g.label}': invalid sample size n={g.n}."
            )
        if g.sd is not None and g.sd < 0:
            raise InsufficientDataError(f"Group '{g.label}': negative SD.")
    ns = [int(g.n) for g in groups]
    N = sum(ns)
    if N - k < 1:
        raise InsufficientDataError("Insufficient within-group degrees of freedom.")

    means = [g.mean for g in groups]
    grand = math.fsum(n * m for n, m in zip(ns, means)) / N
    ss_between = math.fsum(n * (m - grand) ** 2 for n, m in zip(ns, means))
    ss_within = math.fsum((n - 1) * (g.sd ** 2) for g, n in zip(groups, ns))
    ss_total = ss_between + ss_within

    df_between = k - 1
    df_within = N - k
    df_total = N - 1
    ms_between = ss_between / df_between
    ms_within = ss_within / df_within
    if ms_within == 0.0:
        raise InsufficientDataError(
            "Within-group variance is zero; the F statistic is undefined."
        )
    f = ms_between / ms_within
    p = f_sf(f, df_between, df_within)

    return AnovaTable(
        ss_between=ss_between, ss_within=ss_within, ss_total=ss_total,
        df_between=df_between, df_within=df_within, df_total=df_total,
        ms_between=ms_between, ms_within=ms_within, f=f, p=p,
        k=k, n_total=N, method="one-way ANOVA (summary data)",
    )
