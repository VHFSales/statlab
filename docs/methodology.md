# StatLab — Methodology

This document explains what each method does, its hypotheses and assumptions, when
to use it and when not to, and how to interpret it. The most important conceptual
distinction the software enforces:

> **ANOVA ≠ Tukey ≠ CLD.**
> - **ANOVA / Welch** is a *global* test: "Is there evidence that at least one mean
>   differs?" It does not say *which* groups differ.
> - **Tukey / Games–Howell** are *multiple comparisons*: "Which pairs differ?"
> - **CLD** is a *compact representation* of those pairwise results: "How do we show
>   the significance groupings?"

---

## Descriptive statistics
Per group: n, mean, median, sample SD (ddof=1), variance, SE = SD/√n, confidence
interval (t-distribution, df = n−1), min, max, range, Q1, Q3 (type-7/linear
interpolation, matching numpy/R), IQR, and CV = SD/mean (flagged when mean ≈ 0).
Missing values are counted and never coerced to zero.

## One-way ANOVA (classical)
- **H0:** μ₁ = μ₂ = … = μₖ. **H1:** at least one mean differs.
- **Assumptions:** independent observations (design-based), approximately normal
  residuals, homogeneous variances.
- **Statistic:** F = MS_between / MS_within, with SS_between = Σ nᵢ(x̄ᵢ − x̄)²,
  SS_within = ΣΣ(xᵢⱼ − x̄ᵢ)², df = (k−1, N−k). For k = 2, F = t² (pooled Student t).
- **Interpretation:** p < α ⇒ evidence *against* equality of all means. p ≥ α ⇒
  insufficient evidence to reject equality (this does **not** prove equality).

## Welch's ANOVA
- Use when variances are relevantly heterogeneous, especially with unequal n. Does
  **not** assume homogeneity of variance.
- Uses weights wᵢ = nᵢ/sᵢ², a weighted grand mean, and fractional denominator df
  (Welch 1951). Preferred companion post-hoc: Games–Howell.

## Choosing classical vs Welch
Not a rigid "Levene p < 0.05" switch. The decision is holistic: design, variance
ratio (max/min), a robust test (Brown–Forsythe by default, or Levene), balance, and
group sizes. In Quick mode StatLab recommends; in Advanced mode the researcher
chooses. The chosen method is always recorded.

## Assumptions & diagnostics
- **Independence** cannot be confirmed from the values; it depends on the design.
  StatLab states this explicitly and never "tests" it.
- **Normality** concerns the *residuals* (eᵢⱼ = xᵢⱼ − x̄ᵢ). StatLab provides Q–Q
  points and an optional Shapiro–Wilk on residuals, but **never** uses a normality
  test as an absolute gate — such tests have low power at small n and over-detect at
  large n. Judge together with Q–Q, outliers, balance, and design.
- **Homogeneity of variance:** Levene (mean-centered) and Brown–Forsythe
  (median-centered, robust default). Bartlett is not used as the default decision
  because it is sensitive to non-normality.

## Tukey HSD / Tukey–Kramer
- All-pairs comparisons controlling the family-wise error rate (FWER) via the
  studentized range distribution with df = df_within.
- SE = √(MS_within/2 · (1/nᵢ + 1/nⱼ)). Balanced n reduces exactly to Tukey HSD;
  unequal n is handled by Tukey–Kramer (never by substituting mean/min/max n).
- Each comparison reports: difference (mean_g1 − mean_g2), simultaneous CI, the
  **adjusted** p (studentized-range, not uncorrected t-tests), and significance.

## Games–Howell
- All-pairs comparisons for **heteroscedastic** data (companion to Welch). Uses an
  **unpooled** SE = √(sᵢ²/nᵢ + sⱼ²/nⱼ) and a **per-pair** Welch–Satterthwaite df.
  Do not run Tukey after Welch merely because Tukey is implemented.

## Two groups
Prefer Student's t (equal variance; F = t² with one-way ANOVA) or Welch's t (unequal
variance). A pairwise post-hoc like Tukey is unnecessary for two groups.

## Non-significant global test
In Quick mode, a non-significant omnibus suppresses automatic post-hoc (a
conservative workflow default), with a clear message. This is a **workflow choice,
not a mathematical rule**: Tukey/Games–Howell control their own error rate and
Advanced mode allows them regardless, with the decision recorded.

## Effect sizes
η² = SS_between/SS_total (upward biased); ω² = (SS_between − df_between·MS_within) /
(SS_total + MS_within), clamped to ≥ 0 for display; partial η². Report the numeric
value. Small/medium/large labels are context-dependent conventions — statistical
significance is **not** the same as importance or a large effect.

## Compact Letter Display (CLD)
Derived from a **generic significance matrix** (works with Tukey, Games–Howell, and
future methods like Dunn/Holm/Bonferroni/Šidák), NOT from mean ordering. Algorithm:
insert-and-absorb (Piepho 2004). Guarantees:
- Groups that differ significantly **share no letter**.
- Groups that do not differ significantly **share at least one letter**.
Letters are grouping symbols, not a ranking; "a" does not mean best/greatest. By
convention "a" is assigned starting at the highest-mean group (purely visual).
Supports more than 26 groups (a…z, aa, ab, …).

## Non-parametric: Kruskal–Wallis → Dunn
- **Opt-in only.** StatLab never switches to a non-parametric method automatically
  because a normality test rejected (spec §82). The researcher selects it deliberately
  (Advanced mode). The decision between parametric, robust, transformation, or
  non-parametric considers the full statistical context.
- **Kruskal–Wallis** tests whether ≥3 independent groups come from the same
  distribution / have the same rank location. It compares **ranks**, not means.
  Statistic H (with tie correction) ~ χ²(k−1). A significant KW says at least one
  group tends to differ in rank location.
- **Dunn's test** is the pairwise post-hoc: standardized differences of **mean ranks**
  using the shared ranking, with multiplicity adjustment (Holm/BH/Bonferroni) across
  the pairwise family. Reported as mean-rank differences and z statistics (no
  mean-difference CI). CLD is derived from Dunn's significance matrix like any other.
- Wording is rank-based: "at least one group tends to present different values
  (ranks)" — never "means differ".

## Linear regression (OLS): simple & multiple
- Fits y = Xβ + e by ordinary least squares (intercept by default). Reports each
  coefficient's estimate, SE, t = β/SE, two-sided p (df = n − p), and t confidence
  interval; R² and adjusted R²; the global F test (model vs intercept-only); and the
  residual standard error. For a simple regression, R² equals Pearson r² and the
  global F equals the slope's t².
- Assumes independent errors with constant variance, approximately normal. Regression
  is not causation. Needs n > p; a singular/rank-deficient design (constant predictor
  or exact collinearity) is refused with an explanation rather than emitting unstable
  estimates. The normal equations are solved by Gauss-Jordan elimination with partial
  pivoting (pure stdlib).

## Correlation: Pearson & Spearman
- Measures the strength/direction of association between two quantitative variables
  on the same units. **Correlation is not causation** and is not a mean comparison.
- **Pearson r** (linear); **Spearman ρ** (monotonic, computed on ranks). Significance
  via t = r√(n−2)/√(1−r²), df = n−2. Confidence interval via the Fisher z-transform
  (z = atanh r, SE = 1/√(n−3)); for Spearman the Fisher-z CI is an approximation
  (flagged). Requires ≥ 3 complete pairs; zero-variance refused.

## Repeated measures (non-parametric): Friedman → Nemenyi
- For 3+ related conditions measured on the same unit (complete block design).
  Friedman ranks WITHIN each block, so it is the repeated-measures analogue of
  Kruskal–Wallis. Opt-in; never auto-selected from a normality test.
- **Friedman Q** with tie correction ~ χ²(k−1); compares rank locations across
  conditions, not means. Requires complete blocks (no missing values).
- **Nemenyi** post-hoc compares mean ranks using the studentized range at df = ∞;
  its significance matrix feeds the generic CLD. Two conditions → use a paired test
  instead.

## Paired (dependent) data: paired t-test & Wilcoxon signed-rank
- For two conditions measured on the SAME experimental unit (before/after, matched
  pairs). Treating paired data as two independent groups is a design error the
  decision engine guards against.
- **Paired t-test:** work on the within-pair differences d = x1 − x2; t = mean(d)/
  (sd(d)/√n), df = n−1, two-sided p; effect size Cohen's dz = mean(d)/sd(d).
- **Wilcoxon signed-rank** (non-parametric, opt-in): rank |d|, drop zero
  differences, W± = signed rank sums; normal approximation with tie + continuity
  correction. Small-n (< 10) flagged as approximate.
- Inputs must be aligned pair-by-pair; pairs missing on either side are dropped and
  reported, never zero-filled.

## Non-parametric: Mann-Whitney U (two groups)
- Opt-in only (same guardrail as above). The rank-sum test for two independent
  samples: tests whether one group tends to yield larger values than the other (a
  distribution/rank shift), NOT a mean difference.
- U1 = R1 − n1(n1+1)/2, U2 = n1·n2 − U1. Normal approximation with tie correction
  and a continuity correction; p is two-sided. For very small n (< 5 in a group) the
  approximation is flagged as only approximate (an exact test is a future item).

## Two-way (factorial) ANOVA
- Two crossed fixed factors A and B with replicates per cell. Estimates the two main
  effects and their **interaction**. Model
  `y_ijk = μ + α_i + β_j + (αβ)_ij + e_ijk`.
- **Balanced** designs: the SS decomposition is orthogonal and Type I = II = III —
  unambiguous (statistics/two_way_anova.py).
- **Unbalanced** designs: the effects are non-orthogonal, so the SS attributed to
  each effect depends on the **type** (statistics/factorial.py). StatLab computes all
  three explicitly by comparing nested OLS models' residual SS and requires the user
  to state the type — there is no single "correct" type (spec §99):
  - **Type I** (sequential): order-dependent partition; the effects sum to the model
    SS.
  - **Type II**: each main effect adjusted for the other main effect (not the
    interaction).
  - **Type III**: each effect adjusted for all others, via sum-to-zero (effect)
    coding so the contrasts are orthogonal.
  The error (full-model SSE) is identical across types; only the attribution changes.
- Report per effect: SS, df, MS, F, p, partial η² = SS_effect/(SS_effect+SS_error).
- **Interpretation:** if the interaction is significant, main effects must be read
  with caution (the effect of one factor depends on the level of the other).

## Causality & interpretation
A statistical difference does not imply causality; causal language depends on the
design. StatLab never fabricates mechanistic explanations, never displays p = 0
(uses "< 0.001"), and never rounds intermediate computations (only display values).

## Summary-data mode
From (mean, SD, n) StatLab can compute classical ANOVA, Welch, Tukey/Tukey–Kramer,
Games–Howell, and effect sizes via explicit summary formulas, validated against raw
data. Residual/Q–Q/Shapiro/individual-outlier diagnostics are impossible from
summaries and are disabled. StatLab never fabricates raw data from summaries and
tags the report accordingly. With mean + SD but no n, ANOVA/Tukey are refused.

## References (methodological)
- Welch, B.L. (1951). *On the comparison of several mean values.* Biometrika.
- Games, P.A. & Howell, J.F. (1976). *Pairwise multiple comparison procedures with
  unequal n and/or variances.* Journal of Educational Statistics.
- Tukey, J.W. (1949); Kramer, C.Y. (1956) — studentized-range multiple comparisons.
- Piepho, H.-P. (2004). *An algorithm for a letter-based representation of all
  pairwise comparisons.* Journal of Computational and Graphical Statistics.
- Royston, P. (1992). *Approximating the Shapiro–Wilk W-test for non-normality.*
- Brown, M.B. & Forsythe, A.B. (1974). *Robust tests for the equality of variances.*
