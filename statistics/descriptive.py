"""Descriptive statistics (SR-1, design section 3).

Pure stdlib. No intermediate rounding. Quartiles use the type-7 (linear
interpolation) method to match numpy/R defaults (critical review item 6).
"""

from __future__ import annotations

import math
from typing import List, Sequence

from .distributions import t_cdf
from .types import DescriptiveRow, RawGroup


def _clean(values: Sequence[float]) -> List[float]:
    """Drop NaN / non-finite; never coerce empties to zero (FR-8)."""
    out = []
    for v in values:
        if v is None:
            continue
        try:
            fv = float(v)
        except (TypeError, ValueError):
            continue
        if math.isnan(fv) or math.isinf(fv):
            continue
        out.append(fv)
    return out


def quantile_type7(sorted_vals: List[float], q: float) -> float:
    """Type-7 quantile (numpy/R default) on already-sorted values."""
    n = len(sorted_vals)
    if n == 0:
        return math.nan
    if n == 1:
        return sorted_vals[0]
    h = (n - 1) * q
    lo = math.floor(h)
    hi = math.ceil(h)
    if lo == hi:
        return sorted_vals[int(h)]
    return sorted_vals[lo] + (h - lo) * (sorted_vals[hi] - sorted_vals[lo])


def median(sorted_vals: List[float]) -> float:
    return quantile_type7(sorted_vals, 0.5)


def t_ppf(p: float, df: float) -> float:
    """Quantile of Student's t (delegates to the canonical, robust implementation
    in ``distributions.t_ppf``, which expands its bracket instead of truncating)."""
    from .distributions import t_ppf as _canonical_t_ppf
    return _canonical_t_ppf(p, df)


def describe_group(label: str, values: Sequence[float],
                   ci_level: float = 0.95) -> DescriptiveRow:
    n_informed = len(list(values))
    clean = _clean(values)
    n = len(clean)
    n_missing = n_informed - n

    if n == 0:
        nan = math.nan
        return DescriptiveRow(
            label=label, n=0, n_missing=n_missing, mean=nan, median=nan, sd=nan,
            variance=nan, se=nan, ci_level=ci_level, ci_low=nan, ci_high=nan,
            minimum=nan, maximum=nan, range=nan, q1=nan, q3=nan, iqr=nan, cv=nan)

    s = sorted(clean)
    total = math.fsum(clean)
    mean = total / n
    med = median(s)
    mn, mx = s[0], s[-1]
    rng = mx - mn
    q1 = quantile_type7(s, 0.25)
    q3 = quantile_type7(s, 0.75)
    iqr = q3 - q1

    if n >= 2:
        # two-pass variance (numerically stable), ddof=1
        ss = math.fsum((x - mean) ** 2 for x in clean)
        variance = ss / (n - 1)
        sd = math.sqrt(variance)
        se = sd / math.sqrt(n)
        tcrit = t_ppf(0.5 + ci_level / 2.0, n - 1)
        ci_low = mean - tcrit * se
        ci_high = mean + tcrit * se
    else:
        variance = sd = se = math.nan
        ci_low = ci_high = math.nan

    # CV is conventionally non-negative (uses |mean|); NaN when mean ~ 0 or n < 2.
    cv = sd / abs(mean) if (n >= 2 and abs(mean) > 1e-15) else math.nan

    return DescriptiveRow(
        label=label, n=n, n_missing=n_missing, mean=mean, median=med,
        sd=sd, variance=variance, se=se, ci_level=ci_level,
        ci_low=ci_low, ci_high=ci_high, minimum=mn, maximum=mx, range=rng,
        q1=q1, q3=q3, iqr=iqr, cv=cv,
    )


def describe(groups: Sequence[RawGroup], ci_level: float = 0.95) -> List[DescriptiveRow]:
    return [describe_group(g.label, g.values, ci_level) for g in groups]
