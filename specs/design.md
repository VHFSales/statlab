# StatLab — Design Specification

**Document status:** v0.1 (FASE 2). Mathematical definitions here are normative: the
implementation must match these formulas, and tests validate against them.

Notation: `k` = number of groups; `n_i` = size of group i; `N = Σ n_i`; `x_ij` =
observation j in group i; `x̄_i` = mean of group i; `x̄` = grand mean;
`s_i²` = sample variance of group i (ddof=1); `s_p²` = pooled variance.

---

## 1. Architecture

```
statlab/
  statistics/          # PURE STDLIB. Deterministic, transparent, unit-tested.
    distributions.py   #   F, t, studentized-range CDFs/quantiles (numerical)
    descriptive.py     #   per-group & overall descriptive statistics
    assumptions.py     #   Levene, Brown-Forsythe, Shapiro-Wilk, residuals, Q-Q pts
    anova.py           #   one-way classical ANOVA (raw & summary)
    welch.py           #   Welch's ANOVA (raw & summary)
    tukey.py           #   Tukey HSD / Tukey-Kramer
    games_howell.py    #   Games-Howell
    effect_sizes.py    #   eta^2, omega^2, partial eta^2, Cohen's d (pairwise)
    cld.py             #   Compact Letter Display (Piepho insert-absorb)
    decision_engine.py #   design->method recommendation, guardrails, warnings
    outliers.py        #   IQR, Grubbs diagnostics (never auto-exclude)
    types.py           #   dataclasses: GroupData, DescriptiveRow, AnovaTable, ...
    formatting.py      #   display rounding, p-value formatting (p<0.001)
  data/
    model.py           #   Project/Experiment/Variable/Group dataclasses
    importer.py        #   xlsx/xls/csv/paste -> long/wide detection (numpy/pandas)
    validator.py       #   FR-9 checks -> structured issues
    transformer.py     #   wide<->long, missing handling, unit-structure mapping
  plots/
    scientific_plots.py# matplotlib figures + CLD overlay + export PNG/SVG/PDF
  reports/
    excel_export.py    # openpyxl workbook (mandated sheets)
    pdf_report.py      # scientific PDF (matplotlib PdfPages or reportlab)
    interpreter.py     # automatic report text + "why this test" text
  persistence/
    project_store.py   # save/load projects (JSON), snapshots, data hashing, staleness
  app/
    core/orchestrator.py  # ties layers; produces AnalysisResult; audit record
    ui/streamlit_app.py   # Quick + Advanced modes
  tests/                  # pytest, reference datasets, oracle cross-checks
  docs/                   # methodology docs (ANOVA != Tukey != CLD)
```

**Dependency direction:** `statistics/` depends on nothing but stdlib. `data`,
`plots`, `reports`, `persistence`, `app` may depend on `statistics` and on the
scientific stack. The UI depends on `app.core.orchestrator`, never on `statistics`
internals directly. This makes the statistical layer fully independent of the UI
(spec §4) and independently testable (spec §6/§68).

---

## 2. Numerical foundations

### 2.1 No intermediate rounding
All computations use float64 end-to-end. Rounding happens only in `formatting.py`
for display/export. `formatting.round_display(x, decimals)` and
`formatting.format_p(p, decimals)` (returns `"< 0.001"` etc.). (FR-7, SR-11)

### 2.2 Numerically stable sums of squares
Use the corrected two-pass algorithm (compute mean, then Σ(x−mean)²) rather than the
naive Σx² − (Σx)²/n form, to avoid catastrophic cancellation (TRK-4). For SS_total
decomposition we compute SS_within per group by the two-pass method and
SS_between = Σ n_i (x̄_i − x̄)²; we assert SS_between + SS_within ≈ SS_total
(within tolerance) as an internal invariant.

### 2.3 Special functions (pure Python)
- `lgamma`, `erf`, `erfc` from `math` (stdlib) — available and accurate.
- **Regularized incomplete beta** `I_x(a,b)` via Lentz's continued fraction
  (Numerical Recipes `betacf`), used for the Student-t and F CDFs. Tolerance 1e-12.
- **Student-t CDF**: for T~t(ν), `P(T ≤ t)` from `I` of the beta with
  `x = ν/(ν + t²)`, a=ν/2, b=1/2, using the symmetry relation. Two-sided p from tails.
- **F CDF**: `P(F ≤ f)` for F(d1,d2) = `I_{d1 f/(d1 f + d2)}(d1/2, d2/2)`.
  ANOVA/Welch p-value = 1 − CDF(F).
- **Normal CDF** Φ via `0.5*erfc(-z/√2)`; used by Shapiro and studentized range.

### 2.4 Studentized range distribution q(k, ν)
Needed for Tukey/Tukey-Kramer/Games-Howell p-values and simultaneous CIs.
CDF `P(Q ≤ q; k, ν)` (k = number of means, ν = error df):

Outer integral over the χ-scaled error term with density of s (s = √(χ²_ν/ν)),
inner is the probability that the range of k iid N(0,1) is ≤ q·s:

```
P_range(w; k) = k ∫_{-∞}^{∞} φ(u) [Φ(u) − Φ(u − w)]^{k−1} du      (range CDF of k std normals)
P(Q ≤ q; k, ν) = ∫_0^{∞} f_S(s; ν) · P_range(q·s; k) ds
where s ~ scaled-chi:  f_S(s;ν) = [ ν^{ν/2} / (Γ(ν/2) 2^{ν/2−1}) ] s^{ν−1} e^{−ν s²/2}
```

Both integrals evaluated by **adaptive Gauss–Legendre / Gauss–Hermite quadrature**
(or fixed high-order Gauss–Legendre on a truncated, transformed domain), targeting
absolute accuracy 1e-8 on the CDF. For ν → ∞, fall back to `P_range(q; k)` directly.
The quantile q_{α}(k,ν) (critical value) is obtained by bracketed root-finding
(Brent) on the CDF. Adjusted p for an observed range statistic
`q_obs` is `1 − P(Q ≤ q_obs; k, ν)`.

Validation: tabulated critical values (e.g. q_{0.05}) for representative (k, ν) and,
where available, `scipy.stats.studentized_range` (optional oracle). Tolerances in
`tests/reference/studentized_range.py`.

### 2.5 Optional oracle
`statistics/_oracle.py` (test-only) tries to import scipy/statsmodels; if present,
tests assert core ≈ oracle. If absent, those tests `pytest.skip` with a message.
The shipping core never imports scipy.

---

## 3. Descriptive statistics (`descriptive.py`)

For each group with valid values v (NaN removed, count reported):
- n = len(v); mean = Σv/n; median = standard median;
- variance = Σ(v−mean)²/(n−1) (ddof=1), sd = √variance;  (n≥2; n=1 → sd/var = NaN + warning)
- se = sd/√n;
- CI: mean ± t_{1−α/2, n−1} · se  (single-mean t interval; df=n−1). If n=1, CI undefined.
- min, max, range = max−min;
- quartiles Q1, Q3 via a **documented, fixed method**: linear interpolation on
  (n−1) positions — "type 7" (R default / numpy default). IQR = Q3−Q1.
- cv = sd/mean; flagged/NaN when |mean| < eps (SR-1). Report cv as percentage option.
- missing = n_informed − n_valid.

The quartile method is fixed and documented so results are reproducible and match
numpy's default (V-3/V-4).

---

## 4. One-way ANOVA (`anova.py`)

### 4.1 Raw data
```
x̄_i  = mean of group i
x̄    = (Σ_i Σ_j x_ij) / N          # grand mean over all observations
SS_between = Σ_i n_i (x̄_i − x̄)²
SS_within  = Σ_i Σ_j (x_ij − x̄_i)²   # two-pass per group
SS_total   = Σ_i Σ_j (x_ij − x̄)²
df_between = k − 1 ;  df_within = N − k ;  df_total = N − 1
MS_between = SS_between / df_between
MS_within  = SS_within  / df_within        # = pooled variance s_p²
F = MS_between / MS_within
p = 1 − F_CDF(F; df_between, df_within)
```
Guard: df_within ≥ 1 required; MS_within = 0 (all within-group variance zero) →
F undefined → refuse with explanation (zero-variance case, FR-9). Return an
`AnovaTable` (Between/Within/Total rows: SS, df, MS, F, p).

### 4.2 Summary data (mean_i, sd_i, n_i) — SR-13
Reconstructible exactly:
```
x̄  = Σ n_i x̄_i / N
SS_between = Σ n_i (x̄_i − x̄)²
SS_within  = Σ (n_i − 1) s_i²
```
then identical df/MS/F/p. A regression test asserts summary-mode == raw-mode on
equivalent data (V-3).

### 4.3 F = t² invariant (k=2)
Test asserts ANOVA F equals the square of the pooled two-sample t statistic (SR-8).

---

## 5. Welch's ANOVA (`welch.py`)  — Welch (1951)

Works from group (n_i, x̄_i, s_i²), so it serves raw and summary alike.
```
w_i = n_i / s_i²
W   = Σ w_i
x̄*  = Σ w_i x̄_i / W                      # weighted grand mean
A   = Σ w_i (x̄_i − x̄*)² / (k − 1)
B   = [ 2(k−2) / (k²−1) ] · Σ [ (1 − w_i/W)² / (n_i − 1) ]
F*  = A / (1 + B)
df1 = k − 1
df2 = (k² − 1) / ( 3 · Σ [ (1 − w_i/W)² / (n_i − 1) ] )
p   = 1 − F_CDF(F*; df1, df2)
```
Guards: every n_i ≥ 2; s_i² > 0 for all i (a zero-variance group makes w_i infinite →
refuse-with-explanation). Does not require homogeneity (SR-3). Returns statistic,
df1, df2 (fractional), p.

---

## 6. Assumptions & diagnostics (`assumptions.py`)

### 6.1 Residuals (raw only)
e_ij = x_ij − x̄_i. Used for Q–Q points and Shapiro on residuals.

### 6.2 Levene (mean-based) & Brown–Forsythe (median-based)
Both are a one-way ANOVA on the absolute deviations z_ij:
- Levene: z_ij = |x_ij − x̄_i|
- Brown–Forsythe: z_ij = |x_ij − median_i|
Statistic W = ANOVA-F on z; p from F(k−1, N−k). BF is the robust default when
normality is doubtful; **Bartlett is NOT the default** (SR-5). (Bartlett may be
offered later, clearly labeled as normality-sensitive.)

### 6.3 Shapiro–Wilk (on residuals)
Implement Royston's (1992) algorithm (approximate expected order-statistic
coefficients + AS R94 polynomial p-value approximation), valid roughly 3 ≤ n ≤ 5000.
Presented as ONE diagnostic among many, never an absolute gate (SR-5). Q–Q plot
points always provided alongside.

### 6.4 Q–Q points
Theoretical quantiles Φ⁻¹((i − 0.375)/(n + 0.25)) (Blom) vs sorted residuals.
Φ⁻¹ via Acklam/Wichura AS241 rational approximation (accurate to ~1e-9).

### 6.5 Independence
No test computed. `assumptions.independence_note()` returns the mandated disclaimer
(SR-5): independence is design-based and cannot be confirmed from values.

---

## 7. Tukey HSD / Tukey–Kramer (`tukey.py`)  — SR-6

Requires classical-ANOVA context: MS_within (= s_p²) and df_within from §4.
For each unordered pair (i, j):
```
SE_ij = sqrt( MS_within / 2 · (1/n_i + 1/n_j) )      # Tukey–Kramer SE
diff  = x̄_i − x̄_j                                    # direction: mean_i − mean_j
q_ij  = |diff| / SE_ij
p_adj = 1 − P(Q ≤ q_ij; k, df_within)                # studentized range, k = #groups
q_crit = q_{1−α}(k, df_within)
CI    = diff ± q_crit · SE_ij                        # simultaneous CI
significant = p_adj < α   (equivalently |diff| > q_crit·SE_ij)
```
Balanced n → this reduces exactly to Tukey HSD (regression test asserts equality,
V-3). Unequal n → Tukey–Kramer automatically via the (1/n_i+1/n_j) term; we never
substitute mean/min/max n (SR-6). Report per comparison: g1, g2, mean1, mean2, diff,
CI_low, CI_high, p_adj, significant. Method label reported as "Tukey HSD" (balanced)
or "Tukey–Kramer" (unbalanced).

The reported p is the studentized-range-adjusted p — NOT uncorrected t-tests (SR-6).

---

## 8. Games–Howell (`games_howell.py`)  — SR-7

Per pair (i, j), does not pool variance:
```
SE_ij = sqrt( s_i²/n_i + s_j²/n_j )
diff  = x̄_i − x̄_j
q_ij  = |diff| / ( SE_ij / sqrt(2) )      # = |diff| * sqrt(2) / SE_ij
df_ij = ( s_i²/n_i + s_j²/n_j )² /
        [ (s_i²/n_i)²/(n_i−1) + (s_j²/n_j)²/(n_j−1) ]      # Welch–Satterthwaite
p_adj = 1 − P(Q ≤ q_ij; k, df_ij)
q_crit_ij = q_{1−α}(k, df_ij)
CI    = diff ± q_crit_ij · (SE_ij / sqrt(2))
significant = p_adj < α
```
Note the per-pair df (each comparison has its own df_ij), unlike Tukey's common
df_within. Admits unequal variances and unequal n (SR-7). Never used automatically
after classical-only contexts; it is the Welch companion.

---

## 9. Effect sizes (`effect_sizes.py`)  — SR-10

```
eta²        = SS_between / SS_total
omega²      = (SS_between − (k−1)·MS_within) / (SS_total + MS_within)   # clamp ≥ 0
partial_eta² = SS_between / (SS_between + SS_within)   # = eta² in one-way, provided for API symmetry
```
Cohen's d (pairwise, optional, pooled sd) for two-group context. Values returned
numeric; any small/medium/large label is annotated "convention, context-dependent"
(SR-10, spec §47/§48). omega² can be slightly negative in noise → clamped to 0 with a
note.

---

## 10. Compact Letter Display (`cld.py`)  — SR-12, spec §42–46, §73  (CRITICAL)

### 10.1 Input / output
Input: `k` group labels + a symmetric boolean matrix `sig[i][j]` where `True` means
"groups i and j differ significantly" (from ANY post-hoc — decoupled, SR-12/§44).
Output: `dict label -> list of letter-strings`, plus the ordered letter columns.

### 10.2 Algorithm — insert-and-absorb (Piepho 2004)
We work with the complement "connected" relation: `same[i][j] = not sig[i][j]`
(groups may share a letter). A **letter** is a set of groups that is fully connected
(a clique in the `same` graph). The display is a set of columns (letters) covering
all groups such that:
- (Correctness / disjointness) if `sig[i][j]` then i and j share NO column;
- (Coverage) if `not sig[i][j]` then some column contains both i and j;
- (Minimality) no column's group-set is a subset of another's (absorb step).

Procedure:
1. Order groups deterministically (by descending mean by default → "a" at top mean,
   a purely visual convention, SR-12/§46; ties broken by label).
2. Start with one column = {all groups}.
3. For each significant pair (i, j) in order: for every current column C that
   contains both i and j, **split**: replace C by C\{i} and C\{j} (insert step),
   because a column may not contain a significant pair.
4. After processing all pairs, **absorb**: remove any column whose set ⊆ another
   column's set. Also drop empty/singleton-redundant columns appropriately.
5. Assign letter symbols to the remaining columns left-to-right (a, b, …, z, aa, …).
   Each group's letters = the symbols of columns containing it.

This yields the canonical `{A:a, B:ab, C:b}` for the A×B=NS, B×C=NS, A×C=S case
(spec §42/§73). Determinism (fixed group order + fixed pair order + stable absorb)
guarantees reproducibility (priority #3).

### 10.3 Invariants (asserted in code and tested — §73)
- INV-1 significant pair ⇒ letter-set intersection is empty.
- INV-2 non-significant pair ⇒ letter-set intersection is non-empty.
- INV-3 letters extend beyond 26 (a…z, aa, ab, …).
Note (SRK-4): with intransitive patterns (A≠C, A=B, B=C) INV-2 for (A,B) and (B,C)
and INV-1 for (A,C) can force B to carry two letters (`ab`), which is exactly the
intended behavior; CLD represents pairwise relations, not a partition.

### 10.4 Many groups
When columns become numerous, the UI offers alternative views (significance heatmap,
network) instead of unreadable letters (spec §45). CLD generation still succeeds.

---

## 11. Decision engine (`decision_engine.py`)  — SR-2..SR-9, spec §74/§80

Pure function: `recommend(design: DesignSpec, diagnostics: Diagnostics) -> Recommendation`.
`Recommendation` = {method, posthoc, run_posthoc, alpha, reasons[], warnings[],
refusals[]}. It NEVER executes tests; it only recommends + explains ("why this test",
FR-14.3). The orchestrator honors it in Quick mode; Advanced mode may override
(override recorded, FR-12.3).

Rules (holistic, not a single rigid gate — SR-4):
- ≥2 factors declared ⇒ refuse silent one-way; message "Foi identificado um possível
  delineamento fatorial…" (spec §22). No forced analysis.
- repeated measures / paired / blocks / multiple obs per unit declared ⇒ refuse
  one-way-as-independent; explain (spec §22, §74).
- technical replicates without independent-unit assertion ⇒ pseudoreplication
  WARNING (does not hard-block a mathematically valid computation, but is recorded —
  FR-10, §85).
- exactly 2 independent groups ⇒ recommend Student's t or Welch's t (not Tukey),
  explain F=t² (SR-8).
- ≥3 independent groups, one factor:
  - assess heteroscedasticity holistically: Brown–Forsythe/Levene p, variance ratio
    max(s²)/min(s²), balance (n spread), n sizes. Provide a recommendation with the
    reasons enumerated; do not decide solely on "Levene p<0.05" (SR-4).
  - homoscedastic & appropriate ⇒ classical ANOVA → (if significant or user-forced)
    Tukey HSD / Tukey–Kramer (by balance).
  - relevant heteroscedasticity ⇒ Welch ANOVA → Games–Howell. Never Tukey after
    Welch automatically (SR-7).
- global test non-significant (Quick mode) ⇒ run_posthoc=False + message (SR-9);
  Advanced mode may set run_posthoc=True with recorded justification.

Every recommendation carries human-readable `reasons` used verbatim by
"Por que este teste foi escolhido?" (FR-14.3, spec §59).

---

## 12. Data model & persistence (`data/model.py`, `persistence/project_store.py`)

Dataclasses per requirements §3. Persistence format: JSON (human-readable,
diff-able, no Excel dependency — spec §98). `AnalysisResult` stores a `data_hash`
(SHA-256 of the canonicalized dataset). On load, if the current data hash ≠ stored
hash, the result is marked `stale` and must be recomputed before export (FR-19.4).
Snapshots (FR-1.5) are copies of the dataset+results with a label and timestamp.
Every `AnalysisResult` has a UUID `analysis_id`, `program_version`, and captured
`library_versions` (FR-19.1).

---

## 13. Import / validation / transform (`data/`)

- `importer.py`: pandas-backed read of xlsx/csv (+ paste via clipboard text →
  `pandas.read_csv(StringIO)`); wide/long auto-detection heuristic (a single
  non-numeric column + one numeric ⇒ long; multiple numeric columns with a header ⇒
  wide) with a preview and an explicit user confirmation before committing
  (FR-4.3). `.xls` via `xlrd` best-effort (TRK-3).
- `validator.py`: returns a list of typed `Issue(severity, code, message, location)`
  covering FR-9.1; severities: ERROR (blocks), WARNING (proceeds), INFO.
- `transformer.py`: wide↔long, missing handling (drop-with-log, never zero-fill —
  FR-8), mapping of the experimental-unit structure (aggregate technical replicates
  to unit means when the user requests it — the correct fix for pseudoreplication).

---

## 14. Plots (`plots/scientific_plots.py`)  — FR-15

matplotlib. Figure builders return a `Figure`; a thin export helper writes PNG/SVG/PDF
at configurable dpi. CLD letters overlaid above each group at a configurable y-offset.
Group order parameter is visual only and must not touch the statistics (FR-16.2).
Never emit a bar-only mean plot without offering a distribution view (FR-15.3).

---

## 15. Reports & interpreter (`reports/`)  — FR-18, FR-14.4, spec §58–62

- `interpreter.py`: templated, guarded text. Produces the "RESULTADO" summary block
  (spec §58), the APA-style sentence (spec §60), and the "why this test" text. All
  wording obeys SR-11 guardrails (no "means are equal", no causal/importance claims,
  p<0.001 formatting). Templates never fabricate mechanism.
- `excel_export.py`: openpyxl workbook with sheets Projeto, Dados, Descritiva,
  Pressupostos, ANOVA, Pós-testes, Resumo, Metadados, Auditoria (FR-18.2); Resumo has
  Grupo/n/Média/DP/EP/IC inf/IC sup/Letras.
- `pdf_report.py`: matplotlib `PdfPages` (no extra dep) or reportlab (if richer
  layout needed — justified then). Real tables/plots, not screenshots (FR-18.3).

---

## 16. Orchestrator (`app/core/orchestrator.py`)

`analyze(variable, design, options) -> AnalysisResult`:
validate → describe → diagnostics → decision_engine.recommend → run omnibus
(classical/Welch) → (if run_posthoc) run post-hoc → significance matrix → CLD →
effect sizes → assemble AnalysisResult (with audit record, warnings, refusals,
timestamps, versions, data_hash). Batch mode maps this over variables and adds the
cross-variable multiplicity warning (FR-13.3).

---

## 17. Testing & tolerances (`tests/`)  — spec §68–75, §89

Reference values in `tests/reference/`. Default tolerances: relative 1e-9 for
SS/MS/F on exact/hand-computed cases; 1e-6 for p-values and studentized-range
quantities; documented per file. Oracle tests (scipy/statsmodels) skip-with-notice
when the stack is absent (TRK-2). CLD invariant tests are property-style over random
significance matrices.
