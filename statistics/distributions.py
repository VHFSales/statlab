"""Probability distributions implemented in pure Python (stdlib only).

Provides the special functions and CDFs/quantiles required by the statistical
core, so that the engine has NO hard dependency on SciPy (see specs/design.md
sections 2.3 and 2.4). Where SciPy is available it is used only as a test oracle.

Implemented:
  - regularized incomplete beta  I_x(a, b)   via Lentz's continued fraction
  - Student's t CDF / survival function
  - F CDF / survival function
  - standard normal CDF (Phi) and quantile (AS241 / Acklam)
  - studentized range CDF  P(Q <= q; k, nu)  and quantile q_{p}(k, nu)
    via Gauss-Legendre quadrature (double integral) + Brent root finding

References:
  - Press et al., Numerical Recipes (betacf / betai).
  - Wichura (1988) AS 241 for the normal quantile.
  - Standard studentized-range integral (e.g. Gleason 1999; Copenhaver & Holland
    1988) for the double-integral formulation.
"""

from __future__ import annotations

import math

_EPS = 3.0e-16
_FPMIN = 1e-300


# --------------------------------------------------------------------------- #
# Regularized incomplete beta  I_x(a, b)
# --------------------------------------------------------------------------- #
def _betacf(a: float, b: float, x: float) -> float:
    """Continued fraction for the incomplete beta function (Lentz's method)."""
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < _FPMIN:
        d = _FPMIN
    d = 1.0 / d
    h = d
    for m in range(1, 300):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < _FPMIN:
            d = _FPMIN
        c = 1.0 + aa / c
        if abs(c) < _FPMIN:
            c = _FPMIN
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < _FPMIN:
            d = _FPMIN
        c = 1.0 + aa / c
        if abs(c) < _FPMIN:
            c = _FPMIN
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < _EPS:
            break
    return h


def betai(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta function I_x(a, b), 0 <= x <= 1."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    ln_beta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
    bt = math.exp(ln_beta + a * math.log(x) + b * math.log1p(-x))
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


# --------------------------------------------------------------------------- #
# Student's t
# --------------------------------------------------------------------------- #
def t_cdf(t: float, df: float) -> float:
    """CDF of Student's t distribution with ``df`` degrees of freedom."""
    if df <= 0:
        raise ValueError("df must be positive")
    if t == 0.0:
        return 0.5
    x = df / (df + t * t)
    ib = betai(df / 2.0, 0.5, x)  # = P(|T| > |t|) ... regularized
    # betai(df/2, 1/2, df/(df+t^2)) equals 2*P(T > |t|) = P(|T|>|t|)
    tail = 0.5 * ib
    return 1.0 - tail if t > 0 else tail


def t_sf(t: float, df: float) -> float:
    """Survival function P(T > t)."""
    return 1.0 - t_cdf(t, df)


def t_two_sided_p(t: float, df: float) -> float:
    """Two-sided p-value P(|T| >= |t|)."""
    x = df / (df + t * t)
    return betai(df / 2.0, 0.5, x)


# --------------------------------------------------------------------------- #
# F distribution
# --------------------------------------------------------------------------- #
def f_cdf(f: float, df1: float, df2: float) -> float:
    """CDF of the F distribution with (df1, df2) degrees of freedom."""
    if f <= 0.0:
        return 0.0
    if df1 <= 0 or df2 <= 0:
        raise ValueError("degrees of freedom must be positive")
    x = df1 * f / (df1 * f + df2)
    return betai(df1 / 2.0, df2 / 2.0, x)


def f_sf(f: float, df1: float, df2: float) -> float:
    """Survival function P(F > f) = ANOVA/Welch p-value."""
    if f <= 0.0:
        return 1.0
    x = df2 / (df1 * f + df2)
    return betai(df2 / 2.0, df1 / 2.0, x)


# --------------------------------------------------------------------------- #
# Standard normal
# --------------------------------------------------------------------------- #
def norm_pdf(z: float) -> float:
    return math.exp(-0.5 * z * z) / math.sqrt(2.0 * math.pi)


def norm_cdf(z: float) -> float:
    """Standard normal CDF via erfc."""
    return 0.5 * math.erfc(-z / math.sqrt(2.0))


# Wichura (1988) AS 241 rational approximation for the normal quantile.
def norm_ppf(p: float) -> float:
    """Inverse standard normal CDF (quantile). Accurate to ~1e-9."""
    if p <= 0.0:
        return -math.inf
    if p >= 1.0:
        return math.inf
    q = p - 0.5
    if abs(q) <= 0.425:
        r = 0.180625 - q * q
        num = (
            (((((((2509.0809287301226727 * r + 33430.575583588128105) * r
              + 67265.770927008700853) * r + 45921.953931549871457) * r
              + 13731.693765509461125) * r + 1971.5909503065514427) * r
              + 133.14166789178437745) * r + 3.387132872796366608)
        )
        den = (
            (((((((5226.495278852854561 * r + 28729.085735721942674) * r
              + 39307.89580009271061) * r + 21213.794301586595867) * r
              + 5394.1960214247511077) * r + 687.1870074920579083) * r
              + 42.313330701600911252) * r + 1.0)
        )
        return q * num / den
    r = p if q < 0 else 1.0 - p
    r = math.sqrt(-math.log(r))
    if r <= 5.0:
        r -= 1.6
        num = (
            (((((((7.7454501427834140764e-4 * r + 0.0227238449892691845833) * r
              + 0.24178072517745061177) * r + 1.27045825245236838258) * r
              + 3.64784832476320460504) * r + 5.7694972214606914055) * r
              + 4.6303378461565452959) * r + 1.42343711074968357734)
        )
        den = (
            (((((((1.05075007164441684324e-9 * r + 5.475938084995344946e-4) * r
              + 0.0151986665636164571966) * r + 0.14810397642748007459) * r
              + 0.68976733498510000455) * r + 1.6763848301838038494) * r
              + 2.05319162663775882187) * r + 1.0)
        )
    else:
        r -= 5.0
        num = (
            (((((((2.01033439929228813265e-7 * r + 2.71155556874348757815e-5) * r
              + 0.0012426609473880784386) * r + 0.026532189526576123093) * r
              + 0.29656057182850489123) * r + 1.7848265399172913358) * r
              + 5.4637849111641143699) * r + 6.6579046435011037772)
        )
        den = (
            (((((((2.04426310338993978564e-15 * r + 1.4215117583164458887e-7) * r
              + 1.8463183175100546818e-5) * r + 7.868691311456132591e-4) * r
              + 0.0148753612908506148525) * r + 0.13692988092273580531) * r
              + 0.59983220655588793769) * r + 1.0)
        )
    val = num / den
    return -val if q < 0 else val


# --------------------------------------------------------------------------- #
# Gauss-Legendre quadrature nodes/weights (fixed high order)
# --------------------------------------------------------------------------- #
def _gauss_legendre(n: int):
    """Return (nodes, weights) for n-point Gauss-Legendre on [-1, 1]."""
    nodes = [0.0] * n
    weights = [0.0] * n
    m = (n + 1) // 2
    for i in range(m):
        z = math.cos(math.pi * (i + 0.75) / (n + 0.5))
        for _ in range(100):
            p1, p2 = 1.0, 0.0
            for j in range(n):
                p3 = p2
                p2 = p1
                p1 = ((2.0 * j + 1.0) * z * p2 - j * p3) / (j + 1.0)
            pp = n * (z * p1 - p2) / (z * z - 1.0)
            z1 = z
            z = z1 - p1 / pp
            if abs(z - z1) < 1e-15:
                break
        nodes[i] = -z
        nodes[n - 1 - i] = z
        weights[i] = 2.0 / ((1.0 - z * z) * pp * pp)
        weights[n - 1 - i] = weights[i]
    return nodes, weights


_GL64 = _gauss_legendre(64)


def _integrate(func, a: float, b: float, nodes_weights=_GL64) -> float:
    """Integrate func on [a, b] with Gauss-Legendre quadrature."""
    nodes, weights = nodes_weights
    half = 0.5 * (b - a)
    mid = 0.5 * (b + a)
    total = 0.0
    for x, w in zip(nodes, weights):
        total += w * func(mid + half * x)
    return total * half


# --------------------------------------------------------------------------- #
# Studentized range distribution q(k, nu)
# --------------------------------------------------------------------------- #
def _range_cdf_normal(w: float, k: int) -> float:
    """P(range of k iid N(0,1) <= w).

    P = k * integral_{-inf}^{inf} phi(u) [Phi(u) - Phi(u - w)]^{k-1} du
    """
    if w <= 0.0:
        return 0.0

    def integrand(u: float) -> float:
        d = norm_cdf(u) - norm_cdf(u - w)
        if d <= 0.0:
            return 0.0
        return norm_pdf(u) * d ** (k - 1)

    # phi(u) is negligible beyond |u| ~ 8; integrate on a generous window,
    # split at 0 for accuracy of the peaked integrand.
    lo, hi = -8.5, 8.5 + w
    total = _integrate(integrand, lo, 0.0)
    total += _integrate(integrand, 0.0, hi)
    return k * total


def studentized_range_cdf(q: float, k: int, nu: float) -> float:
    """CDF P(Q <= q) of the studentized range for k means and nu error df."""
    if q <= 0.0:
        return 0.0
    if k < 2:
        raise ValueError("k must be >= 2")
    if nu is None or nu == math.inf or nu > 1e7:
        return _range_cdf_normal(q, k)

    # Outer integral over s where s = sqrt(chi^2_nu / nu); density:
    #   f(s) = [nu^(nu/2) / (Gamma(nu/2) 2^(nu/2 - 1))] s^(nu-1) exp(-nu s^2 / 2)
    ln_c = (nu / 2.0) * math.log(nu) - math.lgamma(nu / 2.0) - (nu / 2.0 - 1.0) * math.log(2.0)

    def outer(s: float) -> float:
        if s <= 0.0:
            return 0.0
        ln_fs = ln_c + (nu - 1.0) * math.log(s) - nu * s * s / 2.0
        fs = math.exp(ln_fs)
        return fs * _range_cdf_normal(q * s, k)

    # s concentrates around 1; density negligible beyond a few sd. Use a wide,
    # split window with dense quadrature.
    hi = 1.0 + 8.0 / math.sqrt(nu) + 6.0 / nu + 1.0
    total = _integrate(outer, 1e-6, 1.0)
    total += _integrate(outer, 1.0, hi)
    return min(1.0, max(0.0, total))


def studentized_range_sf(q: float, k: int, nu: float) -> float:
    """Survival function = studentized-range-adjusted upper tail (p-value)."""
    return 1.0 - studentized_range_cdf(q, k, nu)


def studentized_range_ppf(p: float, k: int, nu: float) -> float:
    """Quantile q such that P(Q <= q; k, nu) = p, via Brent root finding."""
    if not (0.0 < p < 1.0):
        raise ValueError("p must be in (0, 1)")

    def g(q: float) -> float:
        return studentized_range_cdf(q, k, nu) - p

    lo, hi = 1e-6, 2.0
    # expand the upper bracket until g(hi) > 0
    while g(hi) < 0.0 and hi < 1e4:
        hi *= 2.0
    return _brentq(g, lo, hi)


# --------------------------------------------------------------------------- #
# Brent's root-finding method
# --------------------------------------------------------------------------- #
def _brentq(f, a: float, b: float, tol: float = 1e-12, maxiter: int = 200) -> float:
    fa, fb = f(a), f(b)
    if fa * fb > 0:
        raise ValueError("root not bracketed")
    if abs(fa) < abs(fb):
        a, b = b, a
        fa, fb = fb, fa
    c, fc = a, fa
    d = e = b - a
    for _ in range(maxiter):
        if fb * fc > 0:
            c, fc = a, fa
            d = e = b - a
        if abs(fc) < abs(fb):
            a, b, c = b, c, b
            fa, fb, fc = fb, fc, fb
        tol1 = 2.0 * _EPS * abs(b) + 0.5 * tol
        xm = 0.5 * (c - b)
        if abs(xm) <= tol1 or fb == 0.0:
            return b
        if abs(e) >= tol1 and abs(fa) > abs(fb):
            s = fb / fa
            if a == c:
                p = 2.0 * xm * s
                qd = 1.0 - s
            else:
                qd = fa / fc
                r = fb / fc
                p = s * (2.0 * xm * qd * (qd - r) - (b - a) * (r - 1.0))
                qd = (qd - 1.0) * (r - 1.0) * (s - 1.0)
            if p > 0:
                qd = -qd
            p = abs(p)
            if 2.0 * p < min(3.0 * xm * qd - abs(tol1 * qd), abs(e * qd)):
                e = d
                d = p / qd
            else:
                d = xm
                e = d
        else:
            d = xm
            e = d
        a, fa = b, fb
        if abs(d) > tol1:
            b += d
        else:
            b += tol1 if xm > 0 else -tol1
        fb = f(b)
    return b
