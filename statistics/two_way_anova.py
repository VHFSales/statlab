"""Two-way (factorial) ANOVA with interaction (spec 81).

Design: two crossed fixed factors A (a levels) and B (b levels), with replicates in
each cell. Model:  y_ijk = mu + alpha_i + beta_j + (alpha*beta)_ij + e_ijk.

SCOPE / GUARDRAIL (spec 99): this implementation handles the BALANCED case (equal
cell counts n per cell), where the sum-of-squares decomposition is orthogonal and
Type I = Type II = Type III (unambiguous). For UNBALANCED designs the SS types
diverge and the "correct" answer depends on the chosen type and contrasts; rather
than silently pick one, we refuse with an explanation and point the user to the
balanced requirement (a typed unbalanced implementation is a future item).

Formulas (balanced, N = a*b*n):
  Cell means m_ij, row means mA_i, col means mB_j, grand mean g.
  SS_A     = b*n * Σ_i (mA_i - g)^2                 df_A   = a-1
  SS_B     = a*n * Σ_j (mB_j - g)^2                 df_B   = b-1
  SS_AB    = n * Σ_ij (m_ij - mA_i - mB_j + g)^2    df_AB  = (a-1)(b-1)
  SS_error = Σ_ijk (y_ijk - m_ij)^2                 df_err = a*b*(n-1)
  SS_total = Σ (y - g)^2                            df_tot = N-1
  MS = SS/df ; F_effect = MS_effect / MS_error ; p from F.
  partial eta^2 = SS_effect / (SS_effect + SS_error).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from .anova import InsufficientDataError
from .descriptive import _clean
from .distributions import f_sf


@dataclass
class EffectRow:
    name: str            # "A", "B", "A:B", "Error", "Total"
    ss: float
    df: float
    ms: float
    f: float
    p: float
    partial_eta_sq: float


@dataclass
class TwoWayResult:
    factor_a: str
    factor_b: str
    a_levels: List[str]
    b_levels: List[str]
    n_per_cell: int
    effects: List[EffectRow]        # A, B, A:B, Error, Total
    method: str = "Two-way ANOVA (balanced)"

    def by_name(self, name: str) -> EffectRow:
        for e in self.effects:
            if e.name == name:
                return e
        raise KeyError(name)


def two_way_anova(cells: Dict[Tuple[str, str], list],
                  factor_a: str = "A", factor_b: str = "B") -> TwoWayResult:
    """Balanced two-way ANOVA.

    ``cells`` maps (a_level, b_level) -> list of observations. Every combination of
    the observed A and B levels must be present with the SAME number of valid
    observations (balanced). Missing values are dropped before the balance check.
    """
    # collect levels in first-seen order
    a_levels: List[str] = []
    b_levels: List[str] = []
    clean: Dict[Tuple[str, str], List[float]] = {}
    for (ai, bj), vals in cells.items():
        if ai not in a_levels:
            a_levels.append(ai)
        if bj not in b_levels:
            b_levels.append(bj)
        clean[(ai, bj)] = _clean(vals)

    a, b = len(a_levels), len(b_levels)
    if a < 2 or b < 2:
        raise InsufficientDataError(
            "A ANOVA de duas vias requer pelo menos 2 níveis em cada fator.")

    # every cell present?
    counts = {}
    for ai in a_levels:
        for bj in b_levels:
            if (ai, bj) not in clean or len(clean[(ai, bj)]) == 0:
                raise InsufficientDataError(
                    f"Célula ausente ou vazia: {factor_a}={ai}, {factor_b}={bj}. "
                    "A ANOVA de duas vias exige todas as combinações preenchidas.")
            counts[(ai, bj)] = len(clean[(ai, bj)])

    ns = set(counts.values())
    if len(ns) != 1:
        raise InsufficientDataError(
            "Delineamento desbalanceado (nº de repetições difere entre células). "
            "Esta versão implementa apenas o caso balanceado, onde a decomposição "
            "de somas de quadrados é não ambígua (Tipo I = II = III). Para dados "
            "desbalanceados, iguale as repetições por célula ou aguarde o suporte a "
            "tipos de SS. Contagens: " + str(dict(counts)))
    n = ns.pop()
    if n < 2:
        raise InsufficientDataError(
            "São necessárias pelo menos 2 repetições por célula para estimar o erro.")

    N = a * b * n
    all_vals = [v for cell in clean.values() for v in cell]
    grand = math.fsum(all_vals) / N

    cell_mean = {k: math.fsum(v) / len(v) for k, v in clean.items()}
    mA = {ai: math.fsum(cell_mean[(ai, bj)] for bj in b_levels) / b
          for ai in a_levels}
    mB = {bj: math.fsum(cell_mean[(ai, bj)] for ai in a_levels) / a
          for bj in b_levels}

    ss_a = b * n * math.fsum((mA[ai] - grand) ** 2 for ai in a_levels)
    ss_b = a * n * math.fsum((mB[bj] - grand) ** 2 for bj in b_levels)
    ss_ab = n * math.fsum(
        (cell_mean[(ai, bj)] - mA[ai] - mB[bj] + grand) ** 2
        for ai in a_levels for bj in b_levels)
    ss_error = math.fsum(
        math.fsum((y - cell_mean[k]) ** 2 for y in clean[k]) for k in clean)
    ss_total = math.fsum((y - grand) ** 2 for y in all_vals)

    df_a, df_b = a - 1, b - 1
    df_ab = (a - 1) * (b - 1)
    df_err = a * b * (n - 1)

    if df_err < 1 or ss_error == 0:
        raise InsufficientDataError(
            "Graus de liberdade do erro insuficientes ou erro nulo; F indefinido.")

    ms_err = ss_error / df_err

    def effect(name, ss, df):
        ms = ss / df
        f = ms / ms_err
        p = f_sf(f, df, df_err)
        peta = ss / (ss + ss_error) if (ss + ss_error) > 0 else float("nan")
        return EffectRow(name=name, ss=ss, df=df, ms=ms, f=f, p=p,
                         partial_eta_sq=peta)

    effects = [
        effect(factor_a, ss_a, df_a),
        effect(factor_b, ss_b, df_b),
        effect(f"{factor_a}:{factor_b}", ss_ab, df_ab),
        EffectRow("Error", ss_error, df_err, ms_err, float("nan"), float("nan"),
                  float("nan")),
        EffectRow("Total", ss_total, N - 1, float("nan"), float("nan"),
                  float("nan"), float("nan")),
    ]
    return TwoWayResult(factor_a=factor_a, factor_b=factor_b, a_levels=a_levels,
                        b_levels=b_levels, n_per_cell=n, effects=effects)
