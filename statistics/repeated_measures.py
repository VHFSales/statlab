"""Repeated-measures / dependent-samples non-parametric analysis (spec 81/82):
Friedman test and the Nemenyi post-hoc.

Design: n blocks (subjects) each measured under k related conditions/treatments —
a complete block design. Friedman ranks WITHIN each block, so it is the repeated-
measures analogue of Kruskal-Wallis.

GUARDRAIL (spec 82): opt-in only; never auto-selected from a normality test.

Formulas:
  For each block, rank its k values (average ranks for ties). Let R_j be the sum of
  ranks for condition j across the n blocks.
    Friedman Q = [ 12 / (n k (k+1)) ] * Σ_j R_j^2  -  3 n (k+1)
  Tie correction (per block ties) divides Q by:
    C = 1 - ( Σ_blocks Σ_t (t^3 - t) ) / ( n (k^3 - k) )
  Q/C ~ chi-square(k-1).

  Nemenyi post-hoc (all pairs), on MEAN ranks R̄_j = R_j / n:
    critical difference uses the studentized range q at df = infinity:
    q_ij = |R̄_i - R̄_j| / sqrt( k (k+1) / (6 n) )
    p_adj = P(Q_studentized_range > q_ij ; k, inf)
  The Nemenyi significance matrix feeds the generic CLD.
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass
from typing import Dict, List, Sequence

from .anova import InsufficientDataError
from .distributions import studentized_range_sf
from .nonparametric import _average_ranks, _chi2_sf
from .types import PairwiseComparison, PostHocResult


@dataclass
class FriedmanResult:
    statistic: float        # Q (tie-corrected)
    df: int                 # k - 1
    p: float
    k: int                  # conditions
    n_blocks: int
    tie_correction: float
    mean_ranks: Dict[str, float]
    method: str = "Friedman"


def _clean_matrix(blocks: Sequence[Sequence[float]], labels: Sequence[str]):
    """Validate a complete block matrix (n blocks x k conditions).

    Every block must have exactly k finite values (no missing) — Friedman requires
    complete blocks. Returns the list of rows as floats.
    """
    k = len(labels)
    rows: List[List[float]] = []
    for i, row in enumerate(blocks):
        if len(row) != k:
            raise InsufficientDataError(
                f"Bloco {i + 1} tem {len(row)} valores; esperado {k} (uma medição "
                "por condição). Friedman exige blocos completos.")
        clean = []
        for v in row:
            if v is None:
                raise InsufficientDataError(
                    f"Valor ausente no bloco {i + 1}. Friedman exige blocos "
                    "completos (sem ausentes).")
            fv = float(v)
            if math.isnan(fv) or math.isinf(fv):
                raise InsufficientDataError(
                    f"Valor inválido (NaN/inf) no bloco {i + 1}.")
            clean.append(fv)
        rows.append(clean)
    return rows


def friedman(blocks: Sequence[Sequence[float]],
             labels: Sequence[str]) -> FriedmanResult:
    """Friedman test. ``blocks`` is a list of rows; each row has k values, one per
    condition in ``labels`` order."""
    k = len(labels)
    if k < 3:
        raise InsufficientDataError(
            "Friedman requer pelo menos 3 condições relacionadas.")
    rows = _clean_matrix(blocks, labels)
    n = len(rows)
    if n < 2:
        raise InsufficientDataError("Friedman requer pelo menos 2 blocos.")

    rank_sums = [0.0] * k
    tie_term = 0.0
    for row in rows:
        ranks, tie_sizes = _average_ranks(row)
        for j in range(k):
            rank_sums[j] += ranks[j]
        tie_term += math.fsum(t ** 3 - t for t in tie_sizes)

    Q = (12.0 / (n * k * (k + 1))) * math.fsum(r * r for r in rank_sums) \
        - 3.0 * n * (k + 1)
    denom = n * (k ** 3 - k)
    C = 1.0 - tie_term / denom if denom > 0 else 1.0
    Q_corr = Q / C if C > 0 else Q
    df = k - 1
    p = _chi2_sf(Q_corr, df)
    mean_ranks = {labels[j]: rank_sums[j] / n for j in range(k)}
    return FriedmanResult(statistic=Q_corr, df=df, p=p, k=k, n_blocks=n,
                          tie_correction=C, mean_ranks=mean_ranks)


def nemenyi_test(blocks: Sequence[Sequence[float]], labels: Sequence[str],
                 alpha: float = 0.05,
                 order: Sequence[str] = None) -> PostHocResult:
    """Nemenyi all-pairs post-hoc following a Friedman test.

    Uses the studentized range distribution at df = infinity on mean ranks.
    """
    k = len(labels)
    if k < 3:
        raise InsufficientDataError("Nemenyi requer pelo menos 3 condições.")
    rows = _clean_matrix(blocks, labels)
    n = len(rows)

    rank_sums = [0.0] * k
    for row in rows:
        ranks, _ = _average_ranks(row)
        for j in range(k):
            rank_sums[j] += ranks[j]
    mean_ranks = {labels[j]: rank_sums[j] / n for j in range(k)}

    se = math.sqrt(k * (k + 1) / (6.0 * n))

    if order is None:
        order = list(labels)
    pos = {lab: i for i, lab in enumerate(order)}
    lab_sorted = sorted(labels, key=lambda l: pos.get(l, 1e9))

    comparisons: List[PairwiseComparison] = []
    for a, b in itertools.combinations(lab_sorted, 2):
        diff = mean_ranks[a] - mean_ranks[b]
        q = abs(diff) / se
        # Nemenyi uses the studentized range with df -> infinity
        p_adj = studentized_range_sf(q, k, float("inf"))
        p_adj = max(0.0, min(1.0, p_adj))
        comparisons.append(PairwiseComparison(
            group1=a, group2=b, mean1=mean_ranks[a], mean2=mean_ranks[b],
            diff=diff, se=se, statistic=q, df=float("inf"),
            ci_low=float("nan"), ci_high=float("nan"),
            p_adjusted=p_adj, significant=(p_adj < alpha)))

    return PostHocResult(method="Nemenyi", alpha=alpha, comparisons=comparisons,
                         labels=lab_sorted)
