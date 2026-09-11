"""Two independent-sample t-tests (SR-8, spec 38).

Student's t (pooled variance, assumes equal variances) and Welch's t (does not
assume equal variances, Welch-Satterthwaite df). Two-sided p-values. Reports the
difference (mean1 - mean2), a confidence interval for the difference, and Cohen's d.

Relationship (SR-8, critical review item 12): Student's t satisfies F = t^2 with
the classical one-way ANOVA on the same two groups. Welch's t relates to Welch's
ANOVA but with generally different degrees of freedom.
"""

from __future__ import annotations

import math
from typing import Sequence

from .anova import InsufficientDataError
from .descriptive import _clean
from .distributions import t_two_sided_p
from .types import RawGroup, TTestResult


def _t_ppf(p: float, df: float) -> float:
    """Quantile of Student's t via bisection on the two-sided tail relation."""
    # find t such that P(T <= t) = p, using the two-sided helper by symmetry
    from .distributions import t_cdf
    lo, hi = -1e4, 1e4
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if t_cdf(mid, df) < p:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def _moments(values: Sequence[float]):
    v = _clean(values)
    n = len(v)
    if n < 2:
        raise InsufficientDataError("O teste t requer n >= 2 em cada grupo.")
    m = math.fsum(v) / n
    var = math.fsum((x - m) ** 2 for x in v) / (n - 1)
    return n, m, var


def student_t(group1: RawGroup, group2: RawGroup, alpha: float = 0.05,
              ci_level: float = 0.95) -> TTestResult:
    """Student's two-sample t-test (pooled variance)."""
    n1, m1, v1 = _moments(group1.values)
    n2, m2, v2 = _moments(group2.values)
    df = n1 + n2 - 2
    sp2 = ((n1 - 1) * v1 + (n2 - 1) * v2) / df           # pooled variance
    se = math.sqrt(sp2 * (1.0 / n1 + 1.0 / n2))
    if se == 0:
        raise InsufficientDataError("Variância nula; teste t indefinido.")
    diff = m1 - m2
    t = diff / se
    p = t_two_sided_p(t, df)
    tcrit = _t_ppf(0.5 + ci_level / 2.0, df)
    d = diff / math.sqrt(sp2) if sp2 > 0 else float("nan")   # Cohen's d (pooled)
    return TTestResult(
        method="Student's t-test", group1=group1.label, group2=group2.label,
        mean1=m1, mean2=m2, diff=diff, se=se, statistic=t, df=df, p=p,
        ci_level=ci_level, ci_low=diff - tcrit * se, ci_high=diff + tcrit * se,
        cohens_d=d, alpha=alpha, significant=(p < alpha),
    )


def welch_t(group1: RawGroup, group2: RawGroup, alpha: float = 0.05,
            ci_level: float = 0.95) -> TTestResult:
    """Welch's two-sample t-test (unequal variances, Satterthwaite df)."""
    n1, m1, v1 = _moments(group1.values)
    n2, m2, v2 = _moments(group2.values)
    a, b = v1 / n1, v2 / n2
    se = math.sqrt(a + b)
    if se == 0:
        raise InsufficientDataError("Variância nula; teste t indefinido.")
    df = (a + b) ** 2 / ((a ** 2) / (n1 - 1) + (b ** 2) / (n2 - 1))
    diff = m1 - m2
    t = diff / se
    p = t_two_sided_p(t, df)
    tcrit = _t_ppf(0.5 + ci_level / 2.0, df)
    # Cohen's d with pooled SD as a comparable effect size
    sp2 = ((n1 - 1) * v1 + (n2 - 1) * v2) / (n1 + n2 - 2)
    d = diff / math.sqrt(sp2) if sp2 > 0 else float("nan")
    return TTestResult(
        method="Welch's t-test", group1=group1.label, group2=group2.label,
        mean1=m1, mean2=m2, diff=diff, se=se, statistic=t, df=df, p=p,
        ci_level=ci_level, ci_low=diff - tcrit * se, ci_high=diff + tcrit * se,
        cohens_d=d, alpha=alpha, significant=(p < alpha),
    )
