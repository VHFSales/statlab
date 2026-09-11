"""Unbalanced two-way factorial ANOVA with Type I / II / III sums of squares.

For UNBALANCED designs the factor effects are non-orthogonal, so the SS attributed
to each effect depends on the order/adjustment convention (the "type"). StatLab
computes all three explicitly by comparing nested OLS models' residual sums of
squares, and requires the user to state which type they want (there is no single
"correct" type — spec §99 / critical review). For BALANCED designs all three types
coincide (and equal statistics/two_way_anova.py).

Design encoding: effect (sum-to-zero) coding for both factors, so main effects and
the interaction are mutually orthogonal under balance and Type III contrasts are the
standard "each effect adjusted for all others" partition.

Type definitions (two factors A, B, interaction A:B; error from the full model):
  Type I  (sequential): SS_A = SSE(1) - SSE(A);
                        SS_B = SSE(A) - SSE(A,B);
                        SS_AB = SSE(A,B) - SSE(A,B,AB).
  Type II (each main effect adjusted for the other main effect, not the interaction):
                        SS_A = SSE(B) - SSE(A,B);
                        SS_B = SSE(A) - SSE(A,B);
                        SS_AB = SSE(A,B) - SSE(A,B,AB).
  Type III (each effect adjusted for all others, using orthogonal-contrast coding):
                        SS_A = SSE(B,AB) - SSE(A,B,AB);
                        SS_B = SSE(A,AB) - SSE(A,B,AB);
                        SS_AB = SSE(A,B) - SSE(A,B,AB).
All F tests use MS_effect / MS_error with the full-model error df.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

from .anova import InsufficientDataError
from .descriptive import _clean
from .distributions import f_sf
from .regression import sse_of_design
from .two_way_anova import EffectRow, TwoWayResult


def _levels(values: Sequence[str]) -> List[str]:
    seen: List[str] = []
    for v in values:
        if v not in seen:
            seen.append(v)
    return seen


def _effect_code(level: str, levels: List[str]) -> List[float]:
    """Sum-to-zero (effect) coding for a factor with the given levels.

    Returns a vector of length (#levels - 1). The last level is coded as all -1.
    """
    m = len(levels) - 1
    idx = levels.index(level)
    if idx == m:  # last (reference) level
        return [-1.0] * m
    v = [0.0] * m
    v[idx] = 1.0
    return v


def _build_columns(a_vals, b_vals, a_levels, b_levels):
    """Return per-observation coded columns for A, B, and A:B blocks."""
    a_cols = [_effect_code(a, a_levels) for a in a_vals]
    b_cols = [_effect_code(b, b_levels) for b in b_vals]
    # interaction columns = elementwise products of each A code with each B code
    ab_cols = []
    for ac, bc in zip(a_cols, b_cols):
        ab_cols.append([x * y for x in ac for y in bc])
    return a_cols, b_cols, ab_cols


def _design(intercept: List[float], parts: List[List[List[float]]]) -> List[List[float]]:
    """Assemble a design matrix from an intercept column and a list of coded blocks.

    ``intercept`` is a length-n list (all 1.0). Each part is a length-n list of
    row-vectors (the coded columns for that term).
    """
    n = len(intercept)
    X = []
    for r in range(n):
        row = [intercept[r]]
        for part in parts:
            row.extend(part[r])
        X.append(row)
    return X


def two_way_anova_typed(a_vals: Sequence[str], b_vals: Sequence[str],
                        y: Sequence[float], ss_type: int = 2,
                        factor_a: str = "A", factor_b: str = "B") -> TwoWayResult:
    """Unbalanced two-way ANOVA with the requested SS type (1, 2, or 3).

    ``a_vals``, ``b_vals``, ``y`` are aligned per-observation vectors.
    """
    if ss_type not in (1, 2, 3):
        raise ValueError("ss_type deve ser 1, 2 ou 3.")

    # clean/align (drop rows with a missing response)
    aa, bb, yy = [], [], []
    for a, b, v in zip(a_vals, b_vals, y):
        if v is None:
            continue
        try:
            fv = float(v)
        except (TypeError, ValueError):
            continue
        if math.isnan(fv):
            continue
        aa.append(str(a)); bb.append(str(b)); yy.append(fv)

    a_levels = _levels(aa)
    b_levels = _levels(bb)
    a, b = len(a_levels), len(b_levels)
    if a < 2 or b < 2:
        raise InsufficientDataError(
            "A ANOVA de duas vias requer pelo menos 2 níveis em cada fator.")
    n = len(yy)

    # every cell must have >= 1 observation (no empty cells)
    cells = {}
    for ai, bj in zip(aa, bb):
        cells[(ai, bj)] = cells.get((ai, bj), 0) + 1
    for ai in a_levels:
        for bj in b_levels:
            if cells.get((ai, bj), 0) == 0:
                raise InsufficientDataError(
                    f"Célula vazia: {factor_a}={ai}, {factor_b}={bj}. A ANOVA "
                    "fatorial exige todas as combinações preenchidas.")

    df_a, df_b = a - 1, b - 1
    df_ab = (a - 1) * (b - 1)
    n_params_full = 1 + df_a + df_b + df_ab
    df_err = n - n_params_full
    if df_err < 1:
        raise InsufficientDataError(
            "Graus de liberdade do erro insuficientes (n pequeno demais para o "
            "modelo completo).")

    ones = [1.0] * n
    A_cols, B_cols, AB_cols = _build_columns(aa, bb, a_levels, b_levels)

    def sse(*terms) -> float:
        parts = []
        if "A" in terms:
            parts.append(A_cols)
        if "B" in terms:
            parts.append(B_cols)
        if "AB" in terms:
            parts.append(AB_cols)
        X = _design(ones, parts)
        return sse_of_design(X, yy)

    sse_full = sse("A", "B", "AB")
    sse_1 = sse()  # intercept only

    if ss_type == 1:
        ss_a = sse_1 - sse("A")
        ss_b = sse("A") - sse("A", "B")
        ss_ab = sse("A", "B") - sse_full
    elif ss_type == 2:
        ss_a = sse("B") - sse("A", "B")
        ss_b = sse("A") - sse("A", "B")
        ss_ab = sse("A", "B") - sse_full
    else:  # type 3
        ss_a = sse("B", "AB") - sse_full
        ss_b = sse("A", "AB") - sse_full
        ss_ab = sse("A", "B") - sse_full

    ss_error = sse_full
    ss_total = math.fsum((v - math.fsum(yy) / n) ** 2 for v in yy)
    ms_err = ss_error / df_err

    def effect(name, ss, df):
        ss = max(0.0, ss)  # guard tiny negative from round-off
        ms = ss / df
        f = ms / ms_err if ms_err > 0 else float("nan")
        p = f_sf(f, df, df_err) if ms_err > 0 else float("nan")
        peta = ss / (ss + ss_error) if (ss + ss_error) > 0 else float("nan")
        return EffectRow(name=name, ss=ss, df=df, ms=ms, f=f, p=p,
                         partial_eta_sq=peta)

    effects = [
        effect(factor_a, ss_a, df_a),
        effect(factor_b, ss_b, df_b),
        effect(f"{factor_a}:{factor_b}", ss_ab, df_ab),
        EffectRow("Error", ss_error, df_err, ms_err, float("nan"), float("nan"),
                  float("nan")),
        EffectRow("Total", ss_total, n - 1, float("nan"), float("nan"),
                  float("nan"), float("nan")),
    ]
    balanced = len(set(cells.values())) == 1
    method = (f"Two-way ANOVA (Type {ss_type} SS"
              + (", balanced" if balanced else ", unbalanced") + ")")
    return TwoWayResult(factor_a=factor_a, factor_b=factor_b, a_levels=a_levels,
                        b_levels=b_levels, n_per_cell=(next(iter(cells.values()))
                                                       if balanced else -1),
                        effects=effects, method=method)
