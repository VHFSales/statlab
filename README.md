# StatLab

[![CI](https://github.com/VHFSales/statlab/actions/workflows/ci.yml/badge.svg)](https://github.com/VHFSales/statlab/actions/workflows/ci.yml)

**A general-purpose scientific statistical platform for the comparison of
independent groups.** Domain-neutral: it works for engineering, chemistry, physics,
materials, biology, biomedicine, pharmacology, microbiology, polymers,
nanotechnology, environment, and any laboratory research. The statistical layer
never assigns physical/chemical/biological meaning to variables — that belongs to
the researcher.

First specialization (v1), implemented to a publication-grade correctness bar:

- Descriptive statistics
- One-way ANOVA (classical) and **Welch's ANOVA**
- **Tukey HSD** / **Tukey–Kramer** (unequal n) and **Games–Howell**
- **Compact Letter Display (CLD)** via the Piepho insert-and-absorb algorithm
- Assumption diagnostics (Levene, Brown–Forsythe, Shapiro–Wilk on residuals, Q–Q)
- Effect sizes (η², ω², partial η²)
- A decision engine that recommends the appropriate method and *refuses* invalid ones
- Scientific plots, Excel/CSV/HTML export, and a full reproducibility audit trail

## Design principle: correctness over convenience

Priority order (non-negotiable): statistical validity → precision → reproducibility
→ transparency → traceability → robustness → prevention of misuse → ease of use →
performance → appearance. When producing a number conflicts with the analysis being
inappropriate, StatLab **refuses with an explanation** instead of emitting a
precise-looking but invalid result.

## Architecture

```
statlab/
  statistics/     # PURE STDLIB statistical core (no third-party deps)
  data/           # model, validation, import, transform
  plots/          # matplotlib scientific plots (guarded)
  reports/        # interpreter text, Excel/CSV, HTML/PDF report
  persistence/    # JSON project save/load, hashing, snapshots
  app/core/       # orchestrator: end-to-end AnalysisResult + audit
  app/ui/         # Streamlit interface (Quick + Advanced modes)
  tests/          # unittest suite + reference values + oracle cross-checks
  specs/          # requirements.md, design.md, tasks.md, critical_review.md
  docs/           # methodology (ANOVA != Tukey != CLD)
```

The **statistical core depends only on the Python standard library.** This makes it
transparent (every formula is explicit — see `specs/design.md`), auditable, portable
to locked-down lab machines, and testable offline. The scientific stack
(numpy/pandas/scipy/statsmodels/matplotlib/openpyxl/streamlit) is used only in the
outer layers and, optionally, as a validation oracle.

## Quick start

```bash
# Core + tests need no installation (stdlib only):
python3 -m unittest discover -s tests

# Full application (import/plots/export/UI):
pip install -r requirements.txt
streamlit run streamlit_app.py          # or: streamlit run app/ui/streamlit_app.py
```

**Publish it as a public link (no install for end users):** deploy to Streamlit
Community Cloud — the repo is ready (root `streamlit_app.py`, `requirements.txt`,
`.streamlit/config.toml`). See [`docs/deploy_streamlit.md`](docs/deploy_streamlit.md).

Programmatic use of the validated engine:

```python
from app.core.orchestrator import analyze_raw, AnalysisOptions
from statistics.decision_engine import DesignSpec

raw = {"Controle": [10.2, 10.8, 11.1, 10.6, 10.4],
       "A": [13.5, 14.0, 13.8, 14.2, 13.9],
       "B": [12.1, 11.8, 12.5, 12.0, 11.9]}

result = analyze_raw(raw, DesignSpec(n_factors=1), AnalysisOptions(alpha=0.05))
print(result.interpretation["omnibus"])
print(result.cld["display"])          # e.g. {'A': 'a', 'B': 'b', 'Controle': 'c'}
```

## Validation status

232 automated tests pass on Python 3.9–3.13 (unittest; see `docs/validation.md` for
the full dossier). CI runs the suite on every push/PR, including an `oracle-tests`
job that installs SciPy/statsmodels and cross-validates the pure-Python core. The
numerical foundation is validated against closed-form identities and published
tables:

- F-distribution survival matches the exact form `(1 + 2F/n)^(-n/2)` to ~1e-19.
- Studentized-range critical values match Harter tables to ~1e-4.
- Shapiro–Wilk W matches the SciPy reference (~0.906 on the test sample).
- ANOVA SS decomposition, F=t² (k=2), summary=raw equivalence, Tukey–Kramer =
  Tukey HSD (balanced), Games–Howell per-pair Welch–Satterthwaite df.
- CLD: canonical `{A:a, B:ab, C:b}` case plus 400 random-matrix invariant checks
  (significant pair ⇒ disjoint letters; non-significant pair ⇒ shared letter),
  and >26-group letter symbols (a…z, aa, ab, …).

`tests/test_oracle.py` additionally cross-checks the core against SciPy/statsmodels
when those are installed (skipped with a notice otherwise).

Beyond the v1 core, the platform also includes: two-group t-tests (Student/Welch);
**non-parametric** tests — Mann–Whitney U (two groups) and Kruskal–Wallis → Dunn
(three or more), opt-in only and never auto-selected from a normality test;
**two-way (factorial) ANOVA** with interaction and partial η² (balanced designs);
**paired/dependent** comparison (paired t-test and Wilcoxon signed-rank);
**repeated-measures** (Friedman → Nemenyi → CLD); **correlation** (Pearson &
Spearman with Fisher-z CIs); **linear regression** (OLS, simple & multiple);
**unbalanced factorial ANOVA** with Type I/II/III sums of squares; summary-data and
batch analysis; opt-in multiplicity corrections (Bonferroni, Holm, Holm–Šidák,
Šidák, Hochberg, Benjamini–Hochberg); a registered outlier-exclusion flow with
original-vs-after comparison; Q–Q and residuals-vs-fitted plots; and full
persistence with deterministic reproduction configs, project save/reopen, and
snapshots.

## Documentation

- `specs/requirements.md` — functional & statistical requirements, data model, flows.
- `specs/design.md` — normative formulas and algorithms (the transparency contract).
- `specs/tasks.md` — incremental implementation plan.
- `specs/critical_review.md` — the statistical review that shaped the design.
- `docs/methodology.md` — what each test does, assumptions, when (not) to use it.
- `docs/manual_statlab.pdf` — end-user manual (PT-BR) for operating the app.
- `docs/deploy_streamlit.md` — how to publish the app as a public link.

## Not in v1 (architecture is prepared)

Parametric repeated-measures/mixed ANOVA, ANCOVA, MANOVA; generalized linear models
(logistic, Poisson); exact (non-approximate) small-sample non-parametric p-values;
multiuser server. Methods are added only when they can meet the same correctness bar.
