"""Multiplicity corrections across a set of p-values (spec 57, critical review 14).

Opt-in only. Never applied automatically. Used at the BATCH level (across many
response variables), NOT for the pairwise comparisons inside a single post-hoc
(those are already FWER-controlled by Tukey/Games-Howell).

Implemented:
  - Bonferroni (FWER)
  - Holm-Bonferroni step-down (FWER, uniformly more powerful than Bonferroni)
  - Benjamini-Hochberg (FDR, independence/positive dependence)

All return adjusted p-values in the ORIGINAL input order, plus boolean rejections
at level alpha. Adjusted p-values are clamped to [0, 1] and made monotone so that
"reject if p_adj <= alpha" reproduces the classic step procedures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Sequence


@dataclass
class MultiplicityResult:
    method: str
    alpha: float
    p_raw: List[float]
    p_adjusted: List[float]
    rejected: List[bool]
    labels: List[str] = field(default_factory=list)
    note: str = ""


def _order(p: Sequence[float]):
    return sorted(range(len(p)), key=lambda i: p[i])


def bonferroni(p: Sequence[float], alpha: float = 0.05,
               labels: Sequence[str] = None) -> MultiplicityResult:
    m = len(p)
    p_adj = [min(1.0, pi * m) for pi in p]
    rejected = [pa <= alpha for pa in p_adj]
    return MultiplicityResult("Bonferroni", alpha, list(p), p_adj, rejected,
                              list(labels or []),
                              note="Controla a FWER; conservador.")


def holm(p: Sequence[float], alpha: float = 0.05,
         labels: Sequence[str] = None) -> MultiplicityResult:
    """Holm-Bonferroni step-down (FWER)."""
    m = len(p)
    order = _order(p)
    p_adj = [0.0] * m
    running = 0.0
    for rank, idx in enumerate(order):
        val = (m - rank) * p[idx]
        running = max(running, val)          # enforce monotonicity
        p_adj[idx] = min(1.0, running)
    rejected = [p_adj[i] <= alpha for i in range(m)]
    return MultiplicityResult("Holm-Bonferroni", alpha, list(p), p_adj, rejected,
                              list(labels or []),
                              note="Controla a FWER; mais potente que Bonferroni.")


def benjamini_hochberg(p: Sequence[float], alpha: float = 0.05,
                       labels: Sequence[str] = None) -> MultiplicityResult:
    """Benjamini-Hochberg step-up (FDR)."""
    m = len(p)
    order = _order(p)
    p_adj = [0.0] * m
    # step-up: process from largest to smallest, enforce monotone non-increasing
    running = 1.0
    for rank in range(m - 1, -1, -1):
        idx = order[rank]
        val = p[idx] * m / (rank + 1)
        running = min(running, val)
        p_adj[idx] = min(1.0, running)
    rejected = [p_adj[i] <= alpha for i in range(m)]
    return MultiplicityResult("Benjamini-Hochberg (FDR)", alpha, list(p), p_adj,
                              rejected, list(labels or []),
                              note="Controla a FDR (taxa de falsas descobertas).")


def adjust(p: Sequence[float], method: str = "holm", alpha: float = 0.05,
           labels: Sequence[str] = None) -> MultiplicityResult:
    method = method.lower()
    if method in ("bonferroni", "bonf"):
        return bonferroni(p, alpha, labels)
    if method in ("holm", "holm-bonferroni"):
        return holm(p, alpha, labels)
    if method in ("bh", "fdr", "benjamini-hochberg"):
        return benjamini_hochberg(p, alpha, labels)
    raise ValueError(f"Método de correção desconhecido: {method}")
