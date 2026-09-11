"""Non-parametric group comparison: Kruskal-Wallis and Dunn (spec 81/82).

GUARDRAIL (SR, spec 82): the choice of a non-parametric method is a holistic
decision made by the researcher / decision engine. This module NEVER decides to use
Kruskal-Wallis just because a normality test rejected. It only computes the tests
when explicitly requested.

Formulas (explicit, validated):

Kruskal-Wallis H (with tie correction):
  Rank all N observations together (average ranks for ties). With R_i the rank sum
  of group i and n_i its size:
      H = [ 12 / (N (N+1)) ] * Σ_i R_i^2 / n_i  -  3 (N + 1)
  Tie correction divides H by:
      C = 1 - ( Σ_t (t^3 - t) ) / (N^3 - N)
  where the sum is over groups of tied values of size t. H/C ~ chi-square(k-1).

Dunn's test (post-hoc for KW), pairwise z on mean ranks:
      z_ij = ( R̄_i - R̄_j ) / SE_ij
      SE_ij = sqrt( [ (N(N+1)/12) - tieTerm ] * (1/n_i + 1/n_j) )
      tieTerm = ( Σ_t (t^3 - t) ) / (12 (N - 1))
  two-sided p from the standard normal, then adjusted (Holm or BH) across the
  set of pairwise comparisons.
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass, field
from typing import Dict, List, Sequence, Tuple

from .anova import InsufficientDataError
from .descriptive import _clean
from .distributions import betai, norm_cdf
from .multiplicity import adjust as _padjust
from .types import PairwiseComparison, PostHocResult, RawGroup


@dataclass
class KruskalResult:
    statistic: float        # H (tie-corrected)
    df: int                 # k - 1
    p: float
    k: int
    n_total: int
    tie_correction: float
    method: str = "Kruskal-Wallis"


# --------------------------------------------------------------------------- #
# Ranking with average ranks for ties
# --------------------------------------------------------------------------- #
def _average_ranks(values: Sequence[float]) -> Tuple[List[float], List[int]]:
    """Return (ranks aligned to input order, tie group sizes).

    Ties receive the average of the ranks they span (standard mid-rank method).
    """
    indexed = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    tie_sizes: List[int] = []
    i = 0
    n = len(values)
    while i < n:
        j = i
        while j + 1 < n and values[indexed[j + 1]] == values[indexed[i]]:
            j += 1
        # positions i..j (0-based) -> ranks (i+1)..(j+1); average
        avg = (i + 1 + j + 1) / 2.0
        for k in range(i, j + 1):
            ranks[indexed[k]] = avg
        if j > i:
            tie_sizes.append(j - i + 1)
        i = j + 1
    return ranks, tie_sizes


def _chi2_sf(x: float, df: int) -> float:
    """Survival function of chi-square via the regularized incomplete beta-free
    relation using the regularized lower incomplete gamma (series/continued frac).
    We use the identity P(X<=x)=gammainc(df/2, x/2); implement gammainc directly."""
    if x <= 0:
        return 1.0
    return 1.0 - _gammainc_lower(df / 2.0, x / 2.0)


def _gammainc_lower(a: float, x: float) -> float:
    """Regularized lower incomplete gamma P(a, x) (Numerical Recipes)."""
    if x < 0 or a <= 0:
        raise ValueError("invalid args to gammainc")
    if x == 0:
        return 0.0
    if x < a + 1.0:
        # series expansion
        ap = a
        summ = 1.0 / a
        delta = summ
        for _ in range(1000):
            ap += 1.0
            delta *= x / ap
            summ += delta
            if abs(delta) < abs(summ) * 1e-15:
                break
        return summ * math.exp(-x + a * math.log(x) - math.lgamma(a))
    # continued fraction for the upper incomplete, then complement
    tiny = 1e-300
    b = x + 1.0 - a
    c = 1.0 / tiny
    d = 1.0 / b
    h = d
    for i in range(1, 1000):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < tiny:
            d = tiny
        c = b + an / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-15:
            break
    q = math.exp(-x + a * math.log(x) - math.lgamma(a)) * h
    return 1.0 - q


def kruskal_wallis(groups: Sequence[RawGroup]) -> KruskalResult:
    cells = [(g.label, _clean(g.values)) for g in groups]
    cells = [(lab, v) for lab, v in cells if len(v) > 0]
    k = len(cells)
    if k < 2:
        raise InsufficientDataError("Kruskal-Wallis requer pelo menos 2 grupos.")
    all_vals: List[float] = []
    sizes: List[int] = []
    for _, v in cells:
        all_vals.extend(v)
        sizes.append(len(v))
    N = len(all_vals)
    if N - k < 1:
        raise InsufficientDataError("Graus de liberdade insuficientes.")

    ranks, tie_sizes = _average_ranks(all_vals)
    # rank sums per group (walk in the same order we appended)
    rank_sums = []
    pos = 0
    for _, v in cells:
        rank_sums.append(math.fsum(ranks[pos:pos + len(v)]))
        pos += len(v)

    H = (12.0 / (N * (N + 1))) * math.fsum(
        (R * R) / n for R, n in zip(rank_sums, sizes)) - 3.0 * (N + 1)

    tie_sum = math.fsum(t ** 3 - t for t in tie_sizes)
    C = 1.0 - tie_sum / (N ** 3 - N) if (N ** 3 - N) > 0 else 1.0
    H_corr = H / C if C > 0 else H
    df = k - 1
    p = _chi2_sf(H_corr, df)
    return KruskalResult(statistic=H_corr, df=df, p=p, k=k, n_total=N,
                         tie_correction=C)


def dunn_test(groups: Sequence[RawGroup], alpha: float = 0.05,
              adjust: str = "holm", order: Sequence[str] = None) -> PostHocResult:
    """Dunn's post-hoc test with multiplicity adjustment across pairs.

    ``adjust`` in {"holm", "bh", "bonferroni", "none"}.
    """
    cells = [(g.label, _clean(g.values)) for g in groups]
    cells = [(lab, v) for lab, v in cells if len(v) > 0]
    k = len(cells)
    if k < 2:
        raise InsufficientDataError("Dunn requer pelo menos 2 grupos.")

    labels = [lab for lab, _ in cells]
    all_vals: List[float] = []
    for _, v in cells:
        all_vals.extend(v)
    N = len(all_vals)
    ranks, tie_sizes = _average_ranks(all_vals)

    sizes, mean_ranks = {}, {}
    pos = 0
    for lab, v in cells:
        n = len(v)
        sizes[lab] = n
        mean_ranks[lab] = math.fsum(ranks[pos:pos + n]) / n
        pos += n

    tie_sum = math.fsum(t ** 3 - t for t in tie_sizes)
    tie_term = tie_sum / (12.0 * (N - 1)) if N > 1 else 0.0
    base = (N * (N + 1)) / 12.0 - tie_term

    if order is None:
        order = labels
    pos_rank = {lab: i for i, lab in enumerate(order)}
    lab_sorted = sorted(labels, key=lambda l: pos_rank.get(l, 1e9))

    raw_pairs = []
    raw_p = []
    for a, b in itertools.combinations(lab_sorted, 2):
        se = math.sqrt(base * (1.0 / sizes[a] + 1.0 / sizes[b]))
        diff_ranks = mean_ranks[a] - mean_ranks[b]
        z = diff_ranks / se if se > 0 else 0.0
        p_two = 2.0 * (1.0 - norm_cdf(abs(z)))
        raw_pairs.append((a, b, mean_ranks[a], mean_ranks[b], se, z))
        raw_p.append(max(0.0, min(1.0, p_two)))

    if adjust and adjust.lower() != "none":
        adj = _padjust(raw_p, method=adjust, alpha=alpha)
        p_adj_list = adj.p_adjusted
        method_label = f"Dunn ({adj.method})"
    else:
        p_adj_list = list(raw_p)
        method_label = "Dunn (sem ajuste)"

    comparisons: List[PairwiseComparison] = []
    for (a, b, ra, rb, se, z), p_adj in zip(raw_pairs, p_adj_list):
        comparisons.append(PairwiseComparison(
            group1=a, group2=b, mean1=ra, mean2=rb, diff=ra - rb, se=se,
            statistic=z, df=float("nan"),  # z-based; no df
            ci_low=float("nan"), ci_high=float("nan"),
            p_adjusted=p_adj, significant=(p_adj < alpha),
        ))
    # mean1/mean2 here are MEAN RANKS (documented); diff is the mean-rank difference
    return PostHocResult(method=method_label, alpha=alpha,
                         comparisons=comparisons, labels=lab_sorted)
