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


def sidak(p: Sequence[float], alpha: float = 0.05,
          labels: Sequence[str] = None) -> MultiplicityResult:
    """Šidák single-step correction (FWER).

    Adjusted p = 1 - (1 - p)^m. Slightly less conservative than Bonferroni; exact
    for independent tests.
    """
    m = len(p)
    p_adj = [min(1.0, 1.0 - (1.0 - pi) ** m) for pi in p]
    rejected = [pa <= alpha for pa in p_adj]
    return MultiplicityResult("Šidák", alpha, list(p), p_adj, rejected,
                              list(labels or []),
                              note="Controla a FWER; exato para testes "
                                   "independentes (menos conservador que Bonferroni).")


def holm_sidak(p: Sequence[float], alpha: float = 0.05,
               labels: Sequence[str] = None) -> MultiplicityResult:
    """Holm-Šidák step-down (FWER); uniformly at least as powerful as Holm."""
    m = len(p)
    order = _order(p)
    p_adj = [0.0] * m
    running = 0.0
    for rank, idx in enumerate(order):
        val = 1.0 - (1.0 - p[idx]) ** (m - rank)
        running = max(running, val)          # enforce monotonicity
        p_adj[idx] = min(1.0, running)
    rejected = [p_adj[i] <= alpha for i in range(m)]
    return MultiplicityResult("Holm-Šidák", alpha, list(p), p_adj, rejected,
                              list(labels or []),
                              note="Controla a FWER (step-down); ao menos tão "
                                   "potente quanto Holm.")


def hochberg(p: Sequence[float], alpha: float = 0.05,
             labels: Sequence[str] = None) -> MultiplicityResult:
    """Hochberg step-up (FWER under independence / positive dependence).

    Uses the same weights as Holm but a step-up procedure, so it is at least as
    powerful as Holm; valid under the same conditions as Benjamini-Hochberg.
    """
    m = len(p)
    order = _order(p)
    p_adj = [0.0] * m
    running = 1.0
    # step-up from the largest p to the smallest, enforcing monotone non-increasing
    for rank in range(m - 1, -1, -1):
        idx = order[rank]
        val = (m - rank) * p[idx]
        running = min(running, val)
        p_adj[idx] = min(1.0, running)
    rejected = [p_adj[i] <= alpha for i in range(m)]
    return MultiplicityResult("Hochberg", alpha, list(p), p_adj, rejected,
                              list(labels or []),
                              note="Controla a FWER (step-up) sob independência ou "
                                   "dependência positiva; mais potente que Holm.")


def adjust(p: Sequence[float], method: str = "holm", alpha: float = 0.05,
           labels: Sequence[str] = None) -> MultiplicityResult:
    method = method.lower()
    if method in ("bonferroni", "bonf"):
        return bonferroni(p, alpha, labels)
    if method in ("holm", "holm-bonferroni"):
        return holm(p, alpha, labels)
    if method in ("bh", "fdr", "benjamini-hochberg"):
        return benjamini_hochberg(p, alpha, labels)
    if method in ("sidak", "šidák", "sidak-single"):
        return sidak(p, alpha, labels)
    if method in ("holm-sidak", "holm-šidák", "holm_sidak"):
        return holm_sidak(p, alpha, labels)
    if method in ("hochberg",):
        return hochberg(p, alpha, labels)
    raise ValueError(f"Método de correção desconhecido: {method}")
