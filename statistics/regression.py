"""Ordinary least squares (OLS) linear regression — simple and multiple (spec 81).

Pure stdlib. Fits y = Xβ + e with an intercept by default. Because the core has no
numpy, the normal equations (XᵀX) β = Xᵀy are solved via Gauss-Jordan elimination
with partial pivoting; the same routine yields (XᵀX)⁻¹ for the coefficient standard
errors.

Reported quantities:
  - coefficient estimates β, their SE, t = β/SE, two-sided p (t, df = n - p), and
    Fisher/t confidence intervals;
  - R² and adjusted R²;
  - the global F test (model vs intercept-only) with its p-value;
  - residual standard error sigma = sqrt(SSE / (n - p)).

Guardrails: needs n > p (more observations than parameters); refuses a singular /
rank-deficient design (e.g. a constant predictor or exact collinearity) with an
explanation rather than emitting unstable numbers.
"""

from __future__ import annotations

import math
from typing import List, Sequence, Tuple

from .anova import InsufficientDataError
from .distributions import f_sf, t_two_sided_p, t_cdf
from .types import RegressionCoefficient, RegressionResult


def _t_ppf(p: float, df: float) -> float:
    lo, hi = -1e4, 1e4
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if t_cdf(mid, df) < p:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def _matmul_at_a(X: List[List[float]]) -> List[List[float]]:
    """Return XᵀX."""
    n = len(X)
    p = len(X[0])
    ata = [[0.0] * p for _ in range(p)]
    for i in range(p):
        for j in range(i, p):
            s = math.fsum(X[r][i] * X[r][j] for r in range(n))
            ata[i][j] = s
            ata[j][i] = s
    return ata


def _matvec_at_b(X: List[List[float]], y: Sequence[float]) -> List[float]:
    """Return Xᵀy."""
    n = len(X)
    p = len(X[0])
    return [math.fsum(X[r][i] * y[r] for r in range(n)) for i in range(p)]


def _invert(matrix: List[List[float]]) -> List[List[float]]:
    """Invert a square matrix via Gauss-Jordan with partial pivoting.

    Raises InsufficientDataError if the matrix is singular (rank-deficient design).
    """
    p = len(matrix)
    # augment with identity
    a = [list(row) + [1.0 if i == j else 0.0 for j in range(p)]
         for i, row in enumerate(matrix)]
    for col in range(p):
        # partial pivot
        pivot = max(range(col, p), key=lambda r: abs(a[r][col]))
        if abs(a[pivot][col]) < 1e-12:
            raise InsufficientDataError(
                "Matriz de delineamento singular (preditor constante ou "
                "colinearidade exata). A regressão não pode ser estimada de forma "
                "estável; verifique preditores redundantes.")
        a[col], a[pivot] = a[pivot], a[col]
        piv = a[col][col]
        a[col] = [v / piv for v in a[col]]
        for r in range(p):
            if r == col:
                continue
            factor = a[r][col]
            if factor != 0.0:
                a[r] = [ar - factor * ac for ar, ac in zip(a[r], a[col])]
    return [row[p:] for row in a]


def _clean_rows(predictors: List[Sequence[float]], y: Sequence[float]
                ) -> Tuple[List[List[float]], List[float], int]:
    """Align predictor columns and the response, dropping any row with a missing
    value anywhere. Never zero-fills."""
    ncols = len(predictors)
    n_in = len(y)
    for col in predictors:
        if len(col) != n_in:
            raise InsufficientDataError(
                "Todos os preditores e a resposta devem ter o mesmo número de "
                "observações.")

    def _missing(v):
        if v is None:
            return True
        try:
            return math.isnan(float(v))
        except (TypeError, ValueError):
            return True

    rows, ys, dropped = [], [], 0
    for i in range(n_in):
        vals = [predictors[c][i] for c in range(ncols)]
        if _missing(y[i]) or any(_missing(v) for v in vals):
            dropped += 1
            continue
        rows.append([float(v) for v in vals])
        ys.append(float(y[i]))
    return rows, ys, dropped


def ols(predictors: List[Sequence[float]], y: Sequence[float],
        predictor_names: Sequence[str] = None, response_name: str = "y",
        intercept: bool = True, ci_level: float = 0.95) -> RegressionResult:
    """Fit an OLS linear regression.

    ``predictors`` is a list of columns (each a sequence aligned with ``y``).
    A simple regression is just one predictor column.
    """
    Xcols, ys, dropped = _clean_rows(list(predictors), y)
    n = len(ys)
    k = len(predictors)  # number of predictors (excluding intercept)
    if predictor_names is None:
        predictor_names = [f"x{i+1}" for i in range(k)]
    predictor_names = list(predictor_names)

    # design matrix
    X = []
    for r in range(n):
        row = ([1.0] if intercept else []) + Xcols[r]
        X.append(row)
    p = len(X[0])  # number of parameters
    if n <= p:
        raise InsufficientDataError(
            f"São necessárias mais observações do que parâmetros (n = {n}, "
            f"parâmetros = {p}).")

    xtx = _matmul_at_a(X)
    xty = _matvec_at_b(X, ys)
    xtx_inv = _invert(xtx)
    beta = [math.fsum(xtx_inv[i][j] * xty[j] for j in range(p)) for i in range(p)]

    # fitted values and residuals
    fitted = [math.fsum(X[r][j] * beta[j] for j in range(p)) for r in range(n)]
    resid = [ys[r] - fitted[r] for r in range(n)]
    sse = math.fsum(e * e for e in resid)
    ybar = math.fsum(ys) / n
    sst = math.fsum((yi - ybar) ** 2 for yi in ys)

    df_resid = n - p
    df_model = p - 1 if intercept else p
    mse = sse / df_resid
    sigma = math.sqrt(mse)

    # coefficient SEs / t / p / CI
    names = (["(Intercepto)"] if intercept else []) + predictor_names
    tcrit = _t_ppf(0.5 + ci_level / 2.0, df_resid)
    coeffs: List[RegressionCoefficient] = []
    for i in range(p):
        var_i = mse * xtx_inv[i][i]
        se = math.sqrt(var_i) if var_i > 0 else 0.0
        t = beta[i] / se if se > 0 else math.inf
        pval = t_two_sided_p(t, df_resid) if se > 0 else 0.0
        coeffs.append(RegressionCoefficient(
            name=names[i], estimate=beta[i], se=se, t=t, p=pval,
            ci_low=beta[i] - tcrit * se, ci_high=beta[i] + tcrit * se))

    if sst > 0:
        r2 = 1.0 - sse / sst
    else:
        r2 = float("nan")
    # adjusted R^2
    if intercept and df_resid > 0 and sst > 0:
        adj_r2 = 1.0 - (1.0 - r2) * (n - 1) / df_resid
    else:
        adj_r2 = float("nan")

    # global F test (model vs intercept-only)
    if df_model >= 1 and sse > 0:
        ssr = sst - sse if intercept else (math.fsum(f * f for f in fitted) - 0.0)
        f_stat = (ssr / df_model) / mse
        f_p = f_sf(f_stat, df_model, df_resid)
    else:
        f_stat = float("nan")
        f_p = float("nan")

    notes = []
    if dropped:
        notes.append(f"{dropped} observação(ões) com valor ausente descartada(s).")
    notes.append("Regressão não implica causalidade; a inferência assume erros "
                 "independentes de variância constante e aproximadamente normais.")

    return RegressionResult(
        method="OLS linear regression", predictors=predictor_names,
        response=response_name, n=n, n_dropped=dropped, df_model=df_model,
        df_resid=df_resid, coefficients=coeffs, r_squared=r2, adj_r_squared=adj_r2,
        f_statistic=f_stat, f_p=f_p, sigma=sigma, ci_level=ci_level, notes=notes)


def simple_linear_regression(x: Sequence[float], y: Sequence[float],
                             x_name: str = "x", y_name: str = "y",
                             ci_level: float = 0.95) -> RegressionResult:
    """Convenience wrapper for one predictor."""
    return ols([x], y, [x_name], y_name, intercept=True, ci_level=ci_level)
