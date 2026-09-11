"""Core dataclasses for the statistical engine (stdlib only)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple


# --------------------------------------------------------------------------- #
# Inputs
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class RawGroup:
    """A group of raw observations (NaN allowed; filtered on use)."""
    label: str
    values: Sequence[float]


@dataclass(frozen=True)
class SummaryGroup:
    """A group described by summary statistics (mean, sd, n)."""
    label: str
    mean: float
    sd: float
    n: int


# --------------------------------------------------------------------------- #
# Descriptive
# --------------------------------------------------------------------------- #
@dataclass
class DescriptiveRow:
    label: str
    n: int
    n_missing: int
    mean: float
    median: float
    sd: float
    variance: float
    se: float
    ci_level: float
    ci_low: float
    ci_high: float
    minimum: float
    maximum: float
    range: float
    q1: float
    q3: float
    iqr: float
    cv: float  # coefficient of variation (sd/mean); NaN if mean ~ 0


# --------------------------------------------------------------------------- #
# ANOVA / Welch
# --------------------------------------------------------------------------- #
@dataclass
class AnovaTable:
    """One-way ANOVA source table."""
    ss_between: float
    ss_within: float
    ss_total: float
    df_between: float
    df_within: float
    df_total: float
    ms_between: float
    ms_within: float
    f: float
    p: float
    k: int
    n_total: int
    method: str = "one-way ANOVA"


@dataclass
class WelchResult:
    statistic: float
    df1: float
    df2: float
    p: float
    k: int
    n_total: int
    method: str = "Welch's ANOVA"


@dataclass
class EffectSizes:
    eta_squared: float
    omega_squared: float
    partial_eta_squared: float
    notes: List[str] = field(default_factory=list)


@dataclass
class TTestResult:
    """Two independent-sample t-test (Student's or Welch's)."""
    method: str          # "Student's t-test" | "Welch's t-test"
    group1: str
    group2: str
    mean1: float
    mean2: float
    diff: float          # mean1 - mean2
    se: float
    statistic: float     # t
    df: float
    p: float             # two-sided
    ci_level: float
    ci_low: float
    ci_high: float
    cohens_d: float
    alpha: float
    significant: bool


# --------------------------------------------------------------------------- #
# Post-hoc comparisons
# --------------------------------------------------------------------------- #
@dataclass
class PairwiseComparison:
    group1: str
    group2: str
    mean1: float
    mean2: float
    diff: float          # mean1 - mean2
    se: float
    statistic: float     # q statistic
    df: float
    ci_low: float
    ci_high: float
    p_adjusted: float
    significant: bool


@dataclass
class PostHocResult:
    method: str          # "Tukey HSD" | "Tukey-Kramer" | "Games-Howell"
    alpha: float
    comparisons: List[PairwiseComparison]
    labels: List[str]    # canonical group order used

    def significance_matrix(self) -> "SignificanceMatrix":
        idx = {lab: i for i, lab in enumerate(self.labels)}
        k = len(self.labels)
        sig = [[False] * k for _ in range(k)]
        for c in self.comparisons:
            i, j = idx[c.group1], idx[c.group2]
            sig[i][j] = sig[j][i] = c.significant
        return SignificanceMatrix(labels=list(self.labels), sig=sig,
                                  source=self.method)


@dataclass
class SignificanceMatrix:
    """Generic significance matrix. sig[i][j] == True => pair differs."""
    labels: List[str]
    sig: List[List[bool]]
    source: str = "unspecified post-hoc"


@dataclass
class CLDResult:
    """Compact Letter Display output."""
    letters: dict          # label -> sorted list of letter symbols
    display: dict          # label -> concatenated string, e.g. "ab"
    n_letters: int
    source: str
    order: List[str]       # order in which labels/letters were assigned


# --------------------------------------------------------------------------- #
# Diagnostics
# --------------------------------------------------------------------------- #
@dataclass
class LeveneResult:
    statistic: float
    df1: float
    df2: float
    p: float
    center: str  # "mean" (Levene) | "median" (Brown-Forsythe)


@dataclass
class ShapiroResult:
    statistic: float
    p: float
    n: int
    note: str = ""


@dataclass
class Issue:
    severity: str  # "ERROR" | "WARNING" | "INFO"
    code: str
    message: str
    location: Optional[str] = None
