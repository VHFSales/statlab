# Changelog

All notable changes to StatLab are documented here.

## [Unreleased] — post-v1 methods

Added, each in its own reviewed PR with numeric validation:
- **Paired (dependent) data:** paired t-test (Cohen's dz) and Wilcoxon signed-rank
  (tie + continuity correction). Decision engine routes paired 2-condition designs
  to the paired test.
- **Repeated measures (non-parametric):** Friedman test (tie correction) with the
  Nemenyi post-hoc feeding the CLD. Routed for repeated-measures 3+ conditions.
- **Correlation:** Pearson and Spearman with t-based p and Fisher-z confidence
  intervals; interpretation states that correlation is not causation.

Test suite grew from 169 to 204 tests. All remain validated against closed-form
identities and published references (e.g. Anscombe I for Pearson).

## [1.0.0] — 2026-09-11

First complete release: a domain-neutral scientific statistical platform for the
comparison of independent groups, with a pure-standard-library, validated core.

### Statistical methods
- Descriptive statistics (n, mean, median, SD, variance, SE, CI, min/max, range,
  Q1/Q3/IQR, CV; missing counts).
- One-way ANOVA (classical) and Welch's ANOVA (raw and summary data).
- Post-hoc: Tukey HSD / Tukey–Kramer (unequal n) and Games–Howell (unequal
  variances, per-pair Welch–Satterthwaite df).
- Compact Letter Display (CLD) via the Piepho insert-and-absorb algorithm, driven by
  a generic significance matrix (decoupled from any single post-hoc).
- Effect sizes: η², ω² (clamped ≥ 0), partial η²; Cohen's d for two groups.
- Two independent-sample t-tests (Student's and Welch's).
- Non-parametric: Mann–Whitney U (two groups) and Kruskal–Wallis → Dunn (three or
  more), with tie corrections; opt-in only, never auto-selected from a normality
  test.
- Two-way (factorial) ANOVA with interaction and partial η² (balanced designs;
  unbalanced/empty-cell/single-replicate designs refused with explanation).
- Assumption diagnostics: Levene, Brown–Forsythe, Shapiro–Wilk (Royston) on
  residuals, Q–Q points, variance ratio; independence disclaimer.
- Outlier diagnostics (IQR, Grubbs) with registered, logged exclusion and
  original-vs-after comparison — never automatic.
- Multiplicity corrections (Bonferroni, Holm, Benjamini–Hochberg) — opt-in, applied
  across batch variables only when requested.

### Engine & guardrails
- Decision engine routes designs to the appropriate method and refuses invalid ones
  (≥2 factors → two-way or refusal; repeated-measures/paired/blocked refused;
  two groups → t-test, not Tukey; pseudoreplication warning). Correctness is
  prioritized over producing a number (refuse-with-explanation).
- Orchestrator produces a single reproducible AnalysisResult with a full audit
  trail (ids, timestamps, versions, data hash), for raw, summary, and batch inputs.

### Interface, export, persistence
- Streamlit UI (Quick + Advanced modes) with sections for project, data, design,
  descriptive, assumptions, analysis, post-hoc, outliers, plots, factorial, batch,
  report, and export; a glossary and "why this test" explanations.
- Scientific plots (box/violin/strip, mean±SD/SE/CI, Q–Q, residuals-vs-fitted) with
  CLD overlay; export PNG/SVG/PDF.
- Excel/CSV/HTML export with the mandated sheets; deterministic reproduction config;
  project save/reopen; workspace snapshots and staleness detection.

### Numerical foundation
- Pure-Python distributions: incomplete beta (Lentz), Student-t and F CDFs, normal
  CDF/quantile (AS241), studentized-range CDF/quantile (double Gauss–Legendre
  quadrature + Brent), chi-square via regularized incomplete gamma. No hard
  dependency on SciPy.

### Quality
- 169 automated tests (unittest) validating numeric results against closed-form
  identities and published tables. CI (GitHub Actions) runs the suite on Python
  3.9–3.13 and cross-validates the core against SciPy/statsmodels in a dedicated job.
- Full documentation: requirements, design (normative formulas), critical review,
  methodology, and a validation dossier.

### Known limitations (v1)
- Two-way ANOVA is balanced-only. Small-sample non-parametric p-values use the
  normal approximation. See README "Not in v1" for the planned roadmap.
