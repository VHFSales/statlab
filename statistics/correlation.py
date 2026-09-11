"""Bivariate correlation: Pearson and Spearman (spec 81).

Measures the strength/direction of association between two quantitative variables
measured on the same units. Correlation is NOT causation and does not imply a
mean difference; the interpretation layer keeps this wording.

Formulas:
  Pearson r = Σ(x-x̄)(y-ȳ) / sqrt(Σ(x-x̄)^2 Σ(y-ȳ)^2).
  Spearman rho = Pearson r computed on the average ranks of x and y.
  Significance (both): t = r sqrt(n-2) / sqrt(1-r^2), df = n-2, two-sided p from t.
  Confidence interval (both, approximate): Fisher z-transform
    z = atanh(r),  SE_z = 1/sqrt(n-3),
    CI on z = z ± z_{1-α/2} SE_z,  back-transform with tanh.
  (The Fisher-z CI for Spearman is the common approximation; flagged as approximate.)
"""

from __future__ import annotations

import math
from typing import List, Sequence, Tuple

from .anova import InsufficientDataError
from .distributions import norm_ppf, t_two_sided_p
from .nonparametric import _average_ranks
from .types import CorrelationResult


def _aligned(x: Sequence[float], y: Sequence[float]) -> Tuple[List[float], List[float], int]:
    if len(x) != len(y):
        raise InsufficientDataError(
            "As duas variáveis devem ter o mesmo número de observações (uma medição "
            "de cada variável por unidade).")

    def _missing(v):
        if v is None:
            return True
        try:
            return math.isnan(float(v))
        except (TypeError, ValueError):
            return True

    xs, ys, dropped = [], [], 0
    for u, v in zip(x, y):
        if _missing(u) or _missing(v):
            dropped += 1
            continue
        xs.append(float(u))
        ys.append(float(v))
    return xs, ys, dropped


def _pearson_r(xs: Sequence[float], ys: Sequence[float]) -> float:
    n = len(xs)
    mx = math.fsum(xs) / n
    my = math.fsum(ys) / n
    sxy = math.fsum((a - mx) * (b - my) for a, b in zip(xs, ys))
    sxx = math.fsum((a - mx) ** 2 for a in xs)
    syy = math.fsum((b - my) ** 2 for b in ys)
    if sxx == 0 or syy == 0:
        raise InsufficientDataError(
            "Uma das variáveis tem variância nula; a correlação é indefinida.")
    r = sxy / math.sqrt(sxx * syy)
    # clamp tiny numerical overshoot
    return max(-1.0, min(1.0, r))


def _fisher_ci(r: float, n: int, ci_level: float) -> Tuple[float, float, str]:
    if n < 4 or abs(r) >= 1.0:
        return math.nan, math.nan, ("IC de Fisher indisponível (requer n >= 4 e "
                                    "|r| < 1).")
    z = math.atanh(r)
    se = 1.0 / math.sqrt(n - 3)
    zc = norm_ppf(0.5 + ci_level / 2.0)
    lo = math.tanh(z - zc * se)
    hi = math.tanh(z + zc * se)
    return lo, hi, ""


def _r_to_result(method: str, r: float, n: int, dropped: int, alpha: float,
                 ci_level: float, extra_note: str = "") -> CorrelationResult:
    df = n - 2
    if df < 1:
        raise InsufficientDataError("A correlação requer pelo menos 3 pares.")
    if abs(r) >= 1.0:
        t = math.inf
        p = 0.0
    else:
        t = r * math.sqrt(df) / math.sqrt(1.0 - r * r)
        p = t_two_sided_p(t, df)
    lo, hi, ci_note = _fisher_ci(r, n, ci_level)
    note = " ".join(s for s in (extra_note, ci_note) if s).strip()
    return CorrelationResult(
        method=method, r=r, n=n, n_dropped=dropped, df=df, statistic=t, p=p,
        ci_level=ci_level, ci_low=lo, ci_high=hi, alpha=alpha,
        significant=(p < alpha), note=note)


def pearson(x: Sequence[float], y: Sequence[float], alpha: float = 0.05,
            ci_level: float = 0.95) -> CorrelationResult:
    xs, ys, dropped = _aligned(x, y)
    n = len(xs)
    if n < 3:
        raise InsufficientDataError("A correlação de Pearson requer pelo menos 3 pares.")
    r = _pearson_r(xs, ys)
    return _r_to_result("Pearson", r, n, dropped, alpha, ci_level)


def spearman(x: Sequence[float], y: Sequence[float], alpha: float = 0.05,
             ci_level: float = 0.95) -> CorrelationResult:
    xs, ys, dropped = _aligned(x, y)
    n = len(xs)
    if n < 3:
        raise InsufficientDataError("A correlação de Spearman requer pelo menos 3 pares.")
    rx, _ = _average_ranks(xs)
    ry, _ = _average_ranks(ys)
    rho = _pearson_r(rx, ry)
    return _r_to_result(
        "Spearman", rho, n, dropped, alpha, ci_level,
        extra_note=("Spearman mede associação monotônica (sobre postos). O IC de "
                    "Fisher é uma aproximação."))
