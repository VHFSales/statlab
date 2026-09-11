"""Paired (dependent) two-sample tests (spec 81): paired t-test and Wilcoxon
signed-rank.

These are for DEPENDENT observations — the same experimental unit measured under two
conditions (before/after, matched pairs). Treating paired data as independent (a
two-sample t-test / Mann-Whitney) is a common error the decision engine guards
against (spec 22/35). The two inputs must be aligned pair-by-pair; pairs with a
missing value on either side are dropped (and reported), never zero-filled.

Formulas:
  Paired t-test: d_i = x1_i - x2_i over n pairs;
      t = mean(d) / (sd(d)/sqrt(n)),  df = n-1,  two-sided p from t.
      Effect size Cohen's dz = mean(d)/sd(d).
  Wilcoxon signed-rank: rank |d_i| (average ranks for ties), drop d_i = 0;
      W+ = sum of ranks where d_i > 0, W- = sum where d_i < 0;
      normal approximation with tie correction and continuity correction:
        mu = n(n+1)/4
        sigma^2 = n(n+1)(2n+1)/24  -  (Σ_t (t^3 - t))/48
        z = (min(W+,W-) - mu + 0.5) / sigma   (toward the mean)
        two-sided p from the standard normal.
"""

from __future__ import annotations

import math
from typing import List, Sequence, Tuple

from .anova import InsufficientDataError
from .descriptive import _clean  # noqa: F401 (kept for parity; not used directly)
from .distributions import norm_cdf, t_two_sided_p
from .nonparametric import _average_ranks
from .types import PairedTResult, WilcoxonResult


def _aligned_pairs(x1: Sequence[float], x2: Sequence[float]
                   ) -> Tuple[List[float], List[float], int]:
    """Return (paired x1, paired x2, n_dropped) dropping any pair with a missing
    value on either side. Never zero-fills (FR-8)."""
    if len(x1) != len(x2):
        raise InsufficientDataError(
            "As duas condições pareadas devem ter o mesmo número de observações "
            "(uma medição por unidade em cada condição).")

    def _missing(v):
        if v is None:
            return True
        try:
            return math.isnan(float(v))
        except (TypeError, ValueError):
            return True

    a, b, dropped = [], [], 0
    for u, v in zip(x1, x2):
        if _missing(u) or _missing(v):
            dropped += 1
            continue
        a.append(float(u))
        b.append(float(v))
    return a, b, dropped


def _t_ppf(p: float, df: float) -> float:
    from .distributions import t_cdf
    lo, hi = -1e4, 1e4
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if t_cdf(mid, df) < p:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def paired_t_test(x1: Sequence[float], x2: Sequence[float],
                  condition1: str = "Condição 1", condition2: str = "Condição 2",
                  alpha: float = 0.05, ci_level: float = 0.95) -> PairedTResult:
    a, b, _ = _aligned_pairs(x1, x2)
    n = len(a)
    if n < 2:
        raise InsufficientDataError("O teste t pareado requer pelo menos 2 pares.")
    d = [ai - bi for ai, bi in zip(a, b)]
    mean_d = math.fsum(d) / n
    var_d = math.fsum((di - mean_d) ** 2 for di in d) / (n - 1)
    sd_d = math.sqrt(var_d)
    if sd_d == 0:
        raise InsufficientDataError(
            "Todas as diferenças pareadas são iguais (variância nula); t indefinido.")
    se_d = sd_d / math.sqrt(n)
    t = mean_d / se_d
    df = n - 1
    p = t_two_sided_p(t, df)
    tcrit = _t_ppf(0.5 + ci_level / 2.0, df)
    dz = mean_d / sd_d
    return PairedTResult(
        method="Paired t-test", condition1=condition1, condition2=condition2,
        n_pairs=n, mean_diff=mean_d, sd_diff=sd_d, se_diff=se_d, statistic=t,
        df=df, p=p, ci_level=ci_level, ci_low=mean_d - tcrit * se_d,
        ci_high=mean_d + tcrit * se_d, cohens_dz=dz, alpha=alpha,
        significant=(p < alpha))


def wilcoxon_signed_rank(x1: Sequence[float], x2: Sequence[float],
                         condition1: str = "Condição 1",
                         condition2: str = "Condição 2",
                         alpha: float = 0.05) -> WilcoxonResult:
    a, b, _ = _aligned_pairs(x1, x2)
    diffs_all = [ai - bi for ai, bi in zip(a, b)]
    # drop zero differences (standard Wilcoxon)
    diffs = [d for d in diffs_all if d != 0.0]
    n_zeros = len(diffs_all) - len(diffs)
    n = len(diffs)
    if n < 1:
        raise InsufficientDataError(
            "Wilcoxon requer ao menos uma diferença não nula entre as condições.")

    abs_d = [abs(d) for d in diffs]
    ranks, tie_sizes = _average_ranks(abs_d)
    w_plus = math.fsum(r for r, d in zip(ranks, diffs) if d > 0)
    w_minus = math.fsum(r for r, d in zip(ranks, diffs) if d < 0)
    w = min(w_plus, w_minus)

    mu = n * (n + 1) / 4.0
    tie_sum = math.fsum(t ** 3 - t for t in tie_sizes)
    sigma2 = n * (n + 1) * (2 * n + 1) / 24.0 - tie_sum / 48.0
    sigma = math.sqrt(sigma2) if sigma2 > 0 else 0.0

    if sigma == 0:
        z, p = 0.0, 1.0
    else:
        # continuity correction toward the mean
        diff_stat = w - mu
        cc = 0.5 if diff_stat < 0 else (-0.5 if diff_stat > 0 else 0.0)
        z = (diff_stat + cc) / sigma
        p = 2.0 * (1.0 - norm_cdf(abs(z)))
        p = max(0.0, min(1.0, p))

    note = ""
    if n < 10:
        note = ("Poucos pares (n < 10): a aproximação normal é apenas aproximada; "
                "um teste exato seria preferível.")
    if n_zeros:
        note = (note + " " if note else "") + \
            f"{n_zeros} diferença(s) nula(s) foram descartadas (padrão de Wilcoxon)."

    return WilcoxonResult(
        method="Wilcoxon signed-rank", condition1=condition1, condition2=condition2,
        n_pairs=n, n_zeros=n_zeros, w_statistic=w, w_plus=w_plus, w_minus=w_minus,
        z=z, p=p, alpha=alpha, significant=(p < alpha), note=note.strip())
