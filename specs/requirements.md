# StatLab — Requirements Specification

**Document status:** v0.1 (FASE 1). This is a living document; the critical review
(see `critical_review.md`) may amend individual clauses.

**Product one-liner:** A general-purpose scientific statistical platform for the
comparison of independent groups, whose first specialization — descriptive
statistics, one-way ANOVA, Welch ANOVA, Tukey HSD / Tukey–Kramer, Games–Howell,
and Compact Letter Display (CLD) — is implemented to a publication-grade level of
correctness, transparency, and reproducibility.

---

## 0. Guiding principles (priority order, non-negotiable)

1. Statistical validity
2. Mathematical precision
3. Reproducibility
4. Transparency
5. Traceability
6. Robustness
7. Prevention of statistically inappropriate use
8. Ease of use
9. Performance
10. Appearance

**Conflict rule:** when "produce a number" conflicts with "the analysis is not
appropriate", the software must refuse-with-explanation rather than emit a
precise-looking but invalid result.

**Domain neutrality:** the statistical engine never assigns physical, chemical,
biological, or clinical meaning to any variable. It sees only: *response variable*,
*factor*, *factor level / group / treatment / condition*, *experimental unit*,
*replicate*, *observation*. Scientific meaning belongs to the researcher.

---

## 1. Functional requirements

### FR-1 Projects & organization
- FR-1.1 Create/save/reopen **Projects** with: name, description, researcher,
  group/lab, date, notes, and one or more **Experiments**.
- FR-1.2 An Experiment contains one or more **Variables** (response variables).
- FR-1.3 Data from different Experiments are **never** merged automatically.
- FR-1.4 Reopening a project restores data, metadata, experiments, variables,
  groups, settings, results, plots, and statistical decisions.
- FR-1.5 (Nice-to-have v1) Snapshots / project versions for traceability
  (original → corrected → after justified exclusion).

### FR-2 Custom metadata
- FR-2.1 Generic `field | value` metadata; **no** hardcoded domain fields
  (no power/temperature/concentration/material/dose/etc. as required fields).
- FR-2.2 Metadata never affect the statistical analysis unless the user
  explicitly promotes a metadata field to an experimental factor.

### FR-3 Data entry
- FR-3.1 **Mode A — Raw data** (recommended default). From raw data compute:
  n, mean, median, sample SD, variance, SE, CI, min, max, range, Q1, Q3, IQR, CV.
- FR-3.2 **Mode B — Summary data** (`group | mean | sd | n`). Analyses that are
  mathematically reconstructible from `(mean, sd, n)` are permitted; diagnostics
  requiring raw values (Q–Q, residuals, Shapiro on residuals, individual outliers)
  are explicitly disabled and flagged.
- FR-3.3 With mean+SD but **no n**: refuse ANOVA/Tukey with the message
  "Os dados disponíveis são insuficientes para realizar ANOVA/Tukey. Informe o
  tamanho amostral de cada grupo ou forneça os dados brutos."
- FR-3.4 Summary-mode formulas are implemented explicitly and validated against
  results from equivalent raw data.

### FR-4 Import
- FR-4.1 Accept `.xlsx`, `.xls`, `.csv`, and paste-from-Excel.
- FR-4.2 Support **wide** (one column per group) and **long** (`group | value`)
  formats, with best-effort auto-detection.
- FR-4.3 Always show a preview before analysis. Never silently reinterpret columns.

### FR-5 Group count
- FR-5.1 Dynamic group count: 2, 3, 5, 8, 20, 50, 100, 150+ within reasonable
  computational limits. No fixed group count, no spreadsheet-cell references.

### FR-6 Spreadsheet-equivalent flow
- FR-6.1 The classic flow DATA → SUMMARY must exist: given data, return per-group
  n, mean, SD, SE, CI-lower, CI-upper, and CLD grouping letter.

### FR-7 Precision & decimals
- FR-7.1 Configurable display decimals (2, 3, 4, 5, or more).
- FR-7.2 **Never** round intermediate calculations; round only for display.
  Internal computations retain full floating-point (or exact) precision.

### FR-8 Missing data
- FR-8.1 Empty cells are never coerced to zero.
- FR-8.2 Report per group: n informed, n valid, n missing.
- FR-8.3 Handle NaN explicitly; log which observations were dropped for missingness.

### FR-9 Data validation
- FR-9.1 Detect: text in numeric field, unexpected NaN, infinity, negative SD,
  invalid n, empty groups, zero variance, duplicate group labels, insufficient n,
  incompatible data, mathematically-detectable impossible values.
- FR-9.2 Never crash; always show comprehensible messages.

### FR-10 Experimental unit (critical)
- FR-10.1 Distinguish **independent experimental unit** from **technical replicate**.
  Five measurements of the same sample are NOT automatically n = 5 independent units.
- FR-10.2 Let the user declare experimental units, technical replicates,
  biological/experimental replicates, and repeated measures.
- FR-10.3 Design wizard asks: "As observações representam unidades experimentais
  independentes?" and explains that pseudoreplication can invalidate inference.

### FR-11 Design identification
- FR-11.1 Before choosing ANOVA, ask/infer-with-confirmation: number of response
  variables, number of factors, group independence, repeated measures, pairing,
  blocks, multiple observations per unit.
- FR-11.2 Never silently conclude one-way ANOVA. If ≥2 factors: inform that a
  factorial ANOVA may be more appropriate; if not implemented, do not force an
  inappropriate analysis.

### FR-12 Modes
- FR-12.1 **Quick mode:** guided; system validates, describes, diagnoses,
  recommends, runs, compares, generates CLD, plot, summary.
- FR-12.2 **Advanced mode:** manual control of alpha, method, post-hoc, assumption
  tests, ordering, interval type, plot, missing-data handling, decimals, export.
- FR-12.3 Any manual choice diverging from the recommendation can be recorded.

### FR-13 Multiple variables & batch
- FR-13.1 Analyze one variable or several in sequence, each with its own
  descriptive/global test/post-hoc/CLD/plot/conclusion.
- FR-13.2 Batch import `Group | Var1 | ... | VarN` and analyze automatically,
  producing a consolidated report.
- FR-13.3 When many global hypotheses are tested at once, warn about multiplicity
  across variables. Architecture ready for Holm and Benjamini–Hochberg/FDR;
  never applied automatically without informing the user.

### FR-14 Results UI
- FR-14.1 First result screen is simple: method, global result, p, effect size,
  summary table, letters, plot. Advanced/technical detail is expandable.
- FR-14.2 Buttons: Ver comparações, Ver pressupostos, Ver tamanho de efeito,
  Ver gráfico, Ver detalhes do cálculo, Exportar Excel, Gerar relatório.
- FR-14.3 "Por que este teste foi escolhido?" explanation button.
- FR-14.4 Automatic interpretation text suitable for a scientific report,
  without invented mechanistic explanations.
- FR-14.5 Help "?" affordances for all statistics/terms.

### FR-15 Plots
- FR-15.1 boxplot, violin, strip, individual-value scatter, mean±SD, mean±SE,
  mean+CI, individual+mean, Q–Q, residuals-vs-fitted.
- FR-15.2 Overlay CLD letters where applicable.
- FR-15.3 Configurable title, axes, unit, decimals, font, size, label rotation,
  group order, width, height, error-bar type. Never hide the distribution without
  offering an alternative view.
- FR-15.4 Export PNG, SVG, PDF at publication resolution.

### FR-16 Ordering
- FR-16.1 Order: original, alphabetical, ascending mean, descending mean.
- FR-16.2 Ordering is **purely visual**; it never changes p, comparisons, CLD, or
  conclusions.

### FR-17 Outliers
- FR-17.1 Never auto-exclude. Optional diagnostics: IQR, Grubbs, other justified.
- FR-17.2 Show value, group, criterion, diagnostic result.
- FR-17.3 Exclusion requires explicit user action; log value/group/reason/method/date.
- FR-17.4 Allow comparison of original vs post-exclusion analyses.

### FR-18 Reporting & export
- FR-18.1 Report includes: project id, experiment, variable, metadata, data used,
  descriptive stats, informed design, assumptions, chosen method + justification,
  ANOVA/Welch table, effect size, post-hoc, full comparison table, CLD, plots,
  statistical conclusion, warnings, excluded data, library versions, timestamp.
- FR-18.2 Excel `.xlsx` with sheets: Projeto, Dados, Descritiva, Pressupostos,
  ANOVA, Pós-testes, Resumo, Metadados, Auditoria. The Resumo sheet must contain at
  least: Grupo, n, Média, DP, EP, IC inferior, IC superior, Letras.
- FR-18.3 PDF report with organized scientific presentation — real tables and
  plots, not screenshots.

### FR-19 Reproducibility & audit
- FR-19.1 Every analysis records: program version, date, time, alpha, method,
  post-hoc, parameters, n, data used, missing data, excluded data, libraries,
  library versions. Assign a unique analysis id.
- FR-19.2 Export a configuration sufficient to fully reproduce the analysis.
- FR-19.3 "Detalhes da análise" audit view exposes all intermediates
  (means, SD, variances, residuals, SS, df, MS, statistic, p, adjusted p, CI,
  effect size, significance matrix, CLD method, library, version).
- FR-19.4 Results reference their source dataset; if data change, prior results are
  marked stale and recomputed before final export. Never keep stale statistics.

### FR-20 Performance
- FR-20.1 Handle 150+ groups, thousands of observations, many variables.
  Heavy operations report progress. Precision is never sacrificed for speed without
  explicit justification.

### FR-21 Future / architecture readiness (not implemented in v1)
- FR-21.1 Multiuser server operation (login, profiles, shared projects, ACL,
  history, backup, comments, peer review).
- FR-21.2 Additional methods: two-way/factorial/repeated-measures ANOVA, ANCOVA,
  MANOVA, mixed models; t / paired-t / Welch-t; Mann–Whitney, Wilcoxon,
  Kruskal–Wallis, Friedman; Dunn; linear/multiple regression, correlation, GLMs.

---

## 2. Statistical requirements

### SR-1 Descriptive statistics
Per group: n, mean, median, sample SD (ddof=1), sample variance, SE = SD/√n,
CI (default 95%, configurable 90/95/99/custom), min, max, range, Q1, Q3, IQR,
CV = SD/mean (flagged when mean≈0). Also missing count. CIs use the t-distribution
with n−1 df for a single group mean.

### SR-2 One-way ANOVA
- Applies when: one quantitative response, one categorical factor, ≥2 levels,
  independent observations, design compatible with mean comparison.
- Hypotheses: H0: μ1=μ2=…=μk ; H1: at least one mean differs. It is a **global**
  test and does not by itself identify which groups differ.
- Compute exactly: SS_between, SS_within, SS_total; df_between=k−1,
  df_within=N−k, df_total=N−1; MS_between, MS_within; F=MS_b/MS_w; p from
  F(df_b, df_w). Present the source table (Between / Within(Error) / Total).
- Relationship F = t² for k=2 must hold (regression test).

### SR-3 Welch's ANOVA
- For relevant variance heterogeneity, especially with unequal variances AND
  unequal n. Does not require homogeneity of variance.
- Implement the standard Welch (1951) statistic with weights w_i = n_i/s_i²,
  the Welch F* and its numerator (k−1) and denominator df (fractional),
  and p from the F distribution. Present statistic, df, p, alpha, conclusion.

### SR-4 Choice between classical ANOVA and Welch
- Not a rigid "Levene p<0.05" switch. Decision considers design, variances,
  variance ratio, group n, balance, residuals, outliers, diagnostics.
- Quick mode gives a recommendation; Advanced mode lets the researcher choose.
  The chosen method is always recorded.

### SR-5 Assumptions & diagnostics
- Assess independence (design-based, not provable from values alone — show the
  explicit disclaimer), residual structure/normality, homogeneity of variance.
- Normality pertains to **residuals**; when raw data exist: compute residuals,
  Q–Q plot, optional Shapiro–Wilk on residuals. Never use "Shapiro p>0.05 = normal /
  p<0.05 = ANOVA forbidden" as an absolute rule. Explain low power (small n) and
  over-sensitivity (large n); judge together with Q–Q, outliers, balance,
  heteroscedasticity, design.
- Homogeneity: **Levene** (mean-centered) and **Brown–Forsythe** (median-centered)
  available. Do not use Bartlett as the default decision when normality is doubtful.

### SR-6 Post-hoc: Tukey HSD / Tukey–Kramer
- After appropriate classical ANOVA with >2 groups and all-pairs comparisons.
- Equal n → Tukey HSD; unequal n → **Tukey–Kramer** with the statistically correct
  formulation (never fake it with mean/min/max n). Uses the studentized range
  distribution with df = df_within. Report per comparison: g1, g2, mean1, mean2,
  difference (= mean_g1 − mean_g2), simultaneous CI lower/upper, adjusted p,
  significant?. The reported p is the **Tukey-adjusted** p, not uncorrected t-tests.
- Controls family-wise error rate (FWER) for the set of pairwise comparisons.

### SR-7 Post-hoc: Games–Howell
- Preferred after Welch ANOVA (heteroscedasticity). Admits unequal variances and
  unequal n, all-pairs. Uses studentized range with Welch–Satterthwaite df per pair
  and SE = √((s_i²/n_i + s_j²/n_j)/... ) per the standard Games–Howell formulation.
- Do **not** run Tukey after Welch merely because Tukey is implemented.

### SR-8 Two groups
- With exactly two independent groups, prefer Student's t or Welch's t as
  appropriate; do not run Tukey unnecessarily. Explain F = t² equivalence.

### SR-9 Non-significant global test
- Quick mode: do not auto-run post-hoc; show "O teste global não apresentou
  significância estatística. Comparações pós-hoc não foram executadas
  automaticamente." Advanced mode: allow with recorded justification. The omnibus
  result is not treated as an absolute mathematical prohibition of all comparisons.

### SR-10 Effect sizes
- ANOVA: η² and ω² (and partial η² where pertinent). Show numeric value.
  Any small/medium/large labels are context-dependent conventions, stated as such.

### SR-11 Interpretation guardrails
- α default 0.05, configurable. If p<α: "Há evidência estatística contra a hipótese
  de igualdade de todas as médias." If p≥α: "Não há evidência estatística suficiente
  para rejeitar a hipótese de igualdade das médias." Never "as médias são iguais".
- Never display p = 0; show p < 0.001 (or configurable precision); keep the true
  value internally. Never equate p<0.05 with importance/large effect. Never assert
  causality from a group difference. Never invent mechanistic explanations.

### SR-12 Compact Letter Display (CLD) — critical
- Generate grouping letters from a **generic significance matrix**, decoupled from
  Tukey (must also accept Games–Howell, Dunn, Holm, Bonferroni, Sidak, …).
  The report records which post-hoc produced the letters.
- Algorithm: a validated CLD algorithm (insert-and-absorb / Piepho 2004),
  NOT mean ordering. Invariant: two groups that differ significantly must NOT share
  any letter; two groups that do not differ significantly must be representable as
  sharing at least one letter per the algorithm. Support >26 groups
  (a…z, aa, ab, …). Provide alternative visualizations when CLD becomes too complex.
- Letters are grouping symbols, not a ranking; "a" does not mean best/greatest.
  Optional convention: assign "a" starting at the highest-mean group (visual only,
  never alters structure).

### SR-13 Summary-data limitations
- With (mean, SD, n): classical ANOVA, Welch, Tukey/Tukey–Kramer, Games–Howell,
  and effect sizes are computable via explicit summary formulas; residual/Q–Q/
  Shapiro/individual outliers are impossible and must be flagged. Never fabricate
  raw data from summaries. Report tags "Análise a partir de estatísticas resumidas".

### SR-14 Raw-data preference
- When raw data exist they are preferred; report tags "Análise a partir de dados
  brutos" and full diagnostics are available.

---

## 3. Data model (conceptual)

```
Project
  id, name, description, researcher, lab, created_at, notes
  metadata: [ {field, value} ]        # generic, non-statistical
  experiments: [ Experiment ]

Experiment
  id, name, notes
  design: DesignSpec                  # factors, independence, repeated/paired/blocks
  variables: [ Variable ]

Variable                              # one response variable
  id, name, unit (free text, display only)
  data_kind: RAW | SUMMARY
  groups: [ Group ]                   # factor levels
  unit_structure: {                   # experimental-unit declaration
     independent_units: bool,
     technical_replicates: bool, ...
  }

Group (raw)     : label, values: [float | NaN]
Group (summary) : label, mean, sd, n

AnalysisResult                        # immutable snapshot, references dataset hash
  id (unique), created_at, program_version, library_versions
  alpha, chosen_method, chosen_posthoc, parameters
  descriptive, assumptions, omnibus, posthoc, effect_sizes, cld, warnings,
  excluded, data_hash, stale: bool
```

Numeric storage: raw values as IEEE-754 float64; where feasible, intermediate SS
computed with numerically stable algorithms (see design.md). No rounding until
display.

---

## 4. User flow (Quick mode)

DATA → confirm DESIGN → VALIDATION → DESCRIPTIVE → DIAGNOSTICS → METHOD
RECOMMENDATION → GLOBAL TEST → (if appropriate) POST-HOC → SIGNIFICANCE MATRIX →
CLD → SUMMARY TABLE → PLOT → REPORT → EXPORT. Achievable with no programming.

## 5. Statistical flow (engine)

See design.md §Decision engine and §Statistical flow (mirrors spec §80).

---

## 6. Libraries & dependency strategy

**Core statistics package (`statlab/statistics/`): standard library only**
(`math`, `statistics`, `fractions`, `dataclasses`, `typing`). Rationale
(priorities #1–#7): maximum transparency, auditability, portability, and testability;
runs in locked-down lab environments; the studentized-range distribution is
implemented by numerical integration so no hard SciPy dependency exists in the core.

**Outer layers** may use, when available and justified:
- `numpy`, `pandas` — data import/wrangling and vectorized descriptive stats.
- `scipy` — OPTIONAL cross-validation oracle (F, t, studentized_range) and speed.
- `statsmodels` — OPTIONAL cross-validation oracle (ANOVA, Tukey, Levene).
- `matplotlib` — plotting.
- `openpyxl` — Excel export; `xlrd` for legacy `.xls` read if needed.
- `streamlit` — UI.
- `reportlab` or `matplotlib`-backed PDF — report export (choice justified in design).

Every added dependency is justified in design.md. The core never requires them.

**Known environment constraint:** the current development sandbox has NO internet
access to PyPI and none of numpy/scipy/statsmodels/matplotlib/openpyxl installed.
Therefore: (a) the core is pure-stdlib and fully runnable/testable here;
(b) SciPy/statsmodels cross-validation (SR/FR references to comparing against SciPy)
is a documented validation step to be executed in the lab's real environment where
the stack is installed. This is recorded as a technical risk (§10).

---

## 7. Validation strategy

- V-1 Reference datasets with independently-known numeric answers (textbook and
  hand-computed), stored under `tests/reference/`.
- V-2 Explicit numeric tolerances (absolute/relative) per quantity; "looks close"
  is not acceptable (spec §89).
- V-3 Internal consistency checks: F=t² (k=2); Tukey–Kramer = Tukey HSD in the
  balanced case; summary-mode results = raw-mode results on equivalent data;
  SS_between + SS_within = SS_total; CLD invariants (§SR-12).
- V-4 Oracle cross-validation against SciPy/statsmodels — runs where installed
  (CI / lab machine); skipped-with-notice where the stack is absent.
- V-5 Regression tests: any statistical bug gets a reproducing test before/with the
  fix (spec §75).

## 8. Testing strategy

- pytest suite mirroring modules: descriptive, assumptions, anova, welch, tukey,
  games_howell, cld, effect_sizes, decision_engine.
- Test numeric results, not just "it runs" (spec §68).
- ANOVA tests (§69): balanced, unequal n, equal means, large differences, zero
  variance, small n, many groups, missing data, negatives, decimals, large magnitudes;
  compare SS/df/MS/F/p.
- Welch tests (§70): known heteroscedastic datasets; statistic/df/p.
- Tukey tests (§71): mean diffs, simultaneous CIs, adjusted p, decision; equal &
  unequal n.
- Games–Howell tests (§72): unequal variances & n vs reference.
- CLD tests (§73): the A×B=NS, B×C=NS, A×C=S ⇒ {A:a, B:ab, C:b} case; larger
  structures; the significant⇒disjoint-letters and non-significant⇒shared-letter
  invariants; >26 groups.
- Decision-engine tests (§74): classical→Tukey; unequal-n→Tukey–Kramer;
  Welch→Games–Howell; Welch⇏Tukey; 2 groups⇏Tukey; ≥2 factors⇏silent one-way;
  repeated measures ⇏ independent; paired ⇏ independent; technical replicates ⇒
  pseudoreplication warning.

## 9. CLD implementation (summary; full algorithm in design.md)

Insert-and-absorb (Piepho 2004). Input: symmetric boolean "significant?" matrix
over k groups (True = the pair differs significantly). Output: for each group a set
of letters such that (i) every non-significant pair shares ≥1 letter and (ii) no
significant pair shares any letter; columns (letters) are then minimized by absorbing
any letter-set that is a subset of another. Letter symbols extend past 26
(a…z, aa, ab, …). Deterministic ordering for reproducibility.

## 10. Statistical risks
- SRK-1 Users treating η²/ω² labels as importance — mitigated by explicit wording.
- SRK-2 Pseudoreplication silently inflating n — mitigated by FR-10 wizard + warnings.
- SRK-3 Misreading a non-significant omnibus as "means equal" — SR-11 wording.
- SRK-4 CLD ambiguity with intransitive significance patterns (A≠C but A=B=C via
  overlaps): documented; CLD represents pairwise relations, not a partition.
- SRK-5 Choosing Welch vs classical by a rigid rule — SR-4 holistic guidance.
- SRK-6 Multiplicity across many batch variables — FR-13.3 warning + FDR readiness.

## 11. Technical risks
- TRK-1 Studentized-range numerical integration accuracy/edge cases (very large k,
  tiny df) — mitigated by tolerance-tested reference values and optional SciPy oracle.
- TRK-2 Sandbox lacks scientific stack / PyPI (see §6) — core is stdlib-only; oracle
  validation deferred to a networked environment; documented explicitly.
- TRK-3 `.xls` legacy parsing fragility — restrict to `.xlsx`/`.csv` first-class;
  `.xls` best-effort.
- TRK-4 Floating-point catastrophic cancellation in SS — use stable one-pass /
  two-pass algorithms.
- TRK-5 Streamlit state management for multi-experiment projects — explicit
  session/state model in design.

## 12. First-version limitations
- One-way, independent-groups comparisons only. No factorial/repeated/paired/blocked
  models, no non-parametric tests, no regression (architecture is prepared, not built).
- Independence is user-asserted via the design wizard; the tool cannot verify it.
- Summary mode disables all raw-only diagnostics.
- Oracle cross-validation not executed in the offline sandbox.

## 13. Expansion plan
Follow spec §81/§82 readiness: add methods only when they can be implemented to the
same correctness bar. Order of future work: two-way/factorial ANOVA → repeated
measures/mixed → t-family → non-parametric (Kruskal–Wallis→Dunn, Mann–Whitney,
Wilcoxon, Friedman) → regression/correlation/GLM → multiuser server.

---

## 14. Acceptance criteria (v1)

A researcher can: create a project → experiment → variable → import/enter data →
identify groups → declare experimental structure → analyze, and automatically
receive: full descriptive stats; assumption diagnostics; classical or Welch ANOVA as
appropriate; F/equivalent statistic, df, p; η²/ω² where applicable; Tukey/Tukey–Kramer
or Games–Howell; all comparisons with adjusted p and simultaneous CIs; the
significance matrix; CLD; summary table; plot; report; Excel file. All numeric
outputs validated against reference values within defined tolerances (V-1..V-3),
with oracle cross-validation (V-4) documented for the lab environment.
