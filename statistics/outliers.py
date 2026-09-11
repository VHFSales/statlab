"""Outlier DIAGNOSTICS (FR-17). Never auto-excludes.

Provides IQR-fence and Grubbs diagnostics that flag candidate values. Exclusion is
always an explicit, logged user action handled elsewhere.
"""

from __future__ import annotations

import math
from typing import List, Sequence

from .descriptive import _clean, quantile_type7
from .distributions import t_cdf


def iqr_outliers(values: Sequence[float], k: float = 1.5) -> List[dict]:
    """Flag values outside [Q1 - k*IQR, Q3 + k*IQR]."""
    x = sorted(_clean(values))
    if len(x) < 4:
        return []
    q1 = quantile_type7(x, 0.25)
    q3 = quantile_type7(x, 0.75)
    iqr = q3 - q1
    lo = q1 - k * iqr
    hi = q3 + k * iqr
    return [
        {"value": v, "criterion": f"IQR fence (k={k})", "low": lo, "high": hi}
        for v in x if v < lo or v > hi
    ]


def _t_ppf(p: float, df: float) -> float:
    lo, hi = -1e4, 1e4
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if t_cdf(mid, df) < p:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def grubbs_test(values: Sequence[float], alpha: float = 0.05) -> dict:
    """Two-sided Grubbs test for a single outlier (the most extreme value)."""
    x = _clean(values)
    n = len(x)
    if n < 3:
        return {"n": n, "note": "Grubbs requires n >= 3."}
    mean = math.fsum(x) / n
    sd = math.sqrt(math.fsum((v - mean) ** 2 for v in x) / (n - 1))
    if sd == 0:
        return {"n": n, "note": "Zero variance; Grubbs undefined."}
    devs = [abs(v - mean) for v in x]
    idx = max(range(n), key=lambda i: devs[i])
    G = devs[idx] / sd
    # two-sided critical value
    tcrit = _t_ppf(1.0 - alpha / (2.0 * n), n - 2)
    Gcrit = ((n - 1) / math.sqrt(n)) * math.sqrt(tcrit ** 2 / (n - 2 + tcrit ** 2))
    return {
        "n": n, "statistic": G, "critical": Gcrit,
        "value": x[idx], "is_outlier": G > Gcrit, "alpha": alpha,
        "criterion": "Grubbs (two-sided, single outlier)",
    }
