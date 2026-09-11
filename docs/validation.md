# StatLab — Validation Dossier

Per spec §68–75 and §89, no analysis is considered validated because results merely
"look close". This dossier records the reference datasets, the independently-known
expected values, the explicit numeric tolerances, and the current validation status.

All reference values are hand-computed, derived from closed-form identities, or taken
from published statistical tables — **not** from a library (the development sandbox
has no scientific stack). Where SciPy/statsmodels are installed, `tests/test_oracle.py`
additionally cross-checks the pure-Python core against them.

Run the whole suite: `python3 -m unittest discover -s tests`.

---

## 1. Tolerance policy

| Quantity | Tolerance | Rationale |
|---|---|---|
| Incomplete beta / t-CDF / F-CDF | abs 1e-9…1e-12 | continued fraction converges to ~1e-12 |
| F-distribution survival (df1=2) | abs 1e-10 | validated against exact `(1+2F/n)^(-n/2)` |
| Studentized-range critical values | abs 2e-3 | table values are rounded to 4 decimals |
| SS / MS / F (exact/hand cases) | abs 1e-9 | integer/decimal arithmetic |
| Effect sizes (η², ω²) | abs 1e-9 | direct from SS |
| Tukey/Games-Howell adjusted p | abs 1e-4 | depends on studentized-range quadrature |
| Shapiro–Wilk W | abs 0.03 | Royston approximation vs SciPy reference |
| Reproduction (config → re-run) | exact / 1e-9 | deterministic engine |

---

## 2. Distribution foundation (`tests/test_distributions.py`)

- **Normal quantile (AS241):** `norm_ppf(0.975)=1.959963985`, `norm_ppf(0.995)=
  2.575829304` — matched to 1e-7. Round-trip `cdf(ppf(p))=p` to 1e-9.
- **Student t:** Cauchy `t_cdf(1,1)=0.75` (1e-8); `t_0.975(10)=2.228138852` gives
  CDF 0.975 and two-sided p 0.05 (1e-6); approaches normal as df→∞.
- **F:** `F_0.95(3,16)=3.238871523` gives survival 0.05 (1e-6); survival for df1=2
  matches the exact closed form `(1+2F/n)^(-n/2)` to **1e-10**; `F(1,ν)` at `t²`
  equals the two-sided t p.
- **Studentized range q_{0.05}(k,ν)** vs Harter tables (delta 2e-3):
  (2,10)=3.1511, (3,10)=3.8768, (3,16)=3.6493, (4,20)=3.9583, (5,30)=4.1021,
  (3,∞)=3.3145. CDF is monotone in q and bounded in [0,1].

## 3. Descriptive (`tests/test_descriptive.py`)

Dataset `[2,4,4,4,5,5,7,9]`: mean 5, variance (ddof=1) 32/7, median 4.5, Q1 4.0,
Q3 5.5 (type-7), IQR 1.5. SE and t-CI verified. Missing values dropped (not zeroed):
`[1, NaN, 3]` → n=2, mean 2.0. n=1 → SD/CI NaN. CV NaN when mean≈0.

## 4. One-way ANOVA (`tests/test_anova.py`)

Balanced 3-group dataset A=[6,8,4,5,3,4], B=[8,12,9,11,6,8], C=[13,9,11,8,7,12]:
SS_between=84, SS_within=68, SS_total=152, df=(2,15), F=9.264705882,
p=0.0023987773 (p verified via the exact df1=2 closed form). Invariants:
SS_b+SS_w=SS_t; summary-mode == raw-mode; F=t² (pooled Student t) for k=2.
Edge cases: zero within-variance refused; single group refused; NaN dropped;
unequal n handled.

## 5. Welch ANOVA (`tests/test_welch.py`)

Heteroscedastic dataset (A n=8, B n=6, C n=7 well-separated): df1=2, p<1e-4,
fractional df2. Zero-variance group refused; n<2 refused.

## 6. Effect sizes (`tests/test_effect_sizes.py`)

η²=84/152; ω²=(84−2·MS_w)/(152+MS_w). ω² clamped ≥0 for near-null effects. Labels
carry the "context-dependent convention" note.

## 7. Tukey / Tukey–Kramer (`tests/test_tukey.py`)

Balanced → "Tukey HSD"; unequal n → "Tukey–Kramer". 3 pairwise comparisons for
k=3; difference direction mean1−mean2; simultaneous CI contains the difference;
significance iff CI excludes 0; adjusted p in [0,1]. Balanced SE equals
√(MS_w/2·(1/n+1/n)).

## 8. Games–Howell (`tests/test_games_howell.py`)

Per-pair Welch–Satterthwaite df are distinct across pairs; unpooled SE equals
√(s_i²/n_i + s_j²/n_j); separated groups flagged significant; CI contains diff;
n<2 refused.

## 9. t-tests (`tests/test_ttest.py`)

Student's t satisfies F=t² and its two-sided p equals the k=2 ANOVA p (1e-9).
Welch's t uses the Satterthwaite df (verified against the explicit formula).
CI contains the difference; n<2 refused.

## 10. Compact Letter Display (`tests/test_cld.py`) — critical

- Canonical case A×B=NS, B×C=NS, A×C=S ⇒ {A:a, B:ab, C:b}.
- Boundary: all-different ⇒ 4 distinct letters; all-same ⇒ 1 letter.
- >26 groups ⇒ letters extend a…z, aa, ab, … (bijective base-26; 701→zz, 702→aaa).
- **Property test:** 400 random significance matrices (k=2..8, shuffled orders) all
  satisfy INV-1 (significant pair ⇒ disjoint letters) and INV-2 (non-significant
  pair ⇒ shared letter). Decoupled from Tukey (accepts arbitrary source).

## 11. Multiplicity (`tests/test_multiplicity.py`)

Bonferroni scaling+clamp; Holm step-down with monotonicity (`[0.01,0.04,0.03]` →
`[0.03,0.06,0.06]`); Benjamini–Hochberg (`[0.01..0.05]` → all 0.05) and BH ≤
Bonferroni elementwise.

## 12. Decision engine (`tests/test_decision_engine.py`) — guardrails

classical→Tukey; unequal-n→Tukey–Kramer; Welch→Games–Howell; Welch ⇏ Tukey;
2 groups ⇏ Tukey (→ t-test); ≥2 factors ⇏ silent one-way (refused);
repeated-measures/paired/blocks refused; technical replicates ⇒ pseudoreplication
warning; non-significant omnibus suppresses auto post-hoc (Quick mode).

## 13. Transformer (`tests/test_transformer.py`)

wide↔long round-trip drops missing (never zero-fills); technical-replicate
aggregation reduces n from observations to independent units
(mean(10,12,11)=11, etc.); missing replicate dropped, not zeroed.

## 14. Orchestrator + summary + batch (`tests/test_orchestrator.py`,
`tests/test_summary_and_batch.py`)

End-to-end raw flow produces descriptive/omnibus/effect sizes/post-hoc/CLD/audit;
heteroscedastic → Welch→Games–Howell; ≥2 factors refused; data error refused;
data_hash changes with data. Summary-mode F matches raw F; summary flags its
limitations; refuses without n. Two-group raw routes to Student/Welch t. Batch warns
about cross-variable multiplicity and applies an optional FDR correction.

## 15. Outlier flow (`tests/test_outlier_flow.py`)

IQR/Grubbs flag candidates without excluding; exclusion removes one matching value,
leaves the original untouched, and logs value/group/reason/method/timestamp; the
before/after comparison carries the registered-exclusion audit.

## 16. Persistence & reproducibility (`tests/test_persistence.py`)

AnalysisResult JSON round-trip; reproduction config re-runs **identically** (raw and
summary), preserving the data hash; Workspace staleness detection via data_hash;
snapshot save/load.

## 17. Export (`tests/test_export.py`)

Summary CSV carries the letters column; Excel bundle has the mandated sheets incl.
Resumo & Auditoria; HTML report contains all sections; the two-group t-test appears
in HTML and the Excel post-hoc sheet; batch CSV carries adjusted p.

---

## 17b. Non-parametric: Kruskal–Wallis / Dunn (`tests/test_nonparametric.py`)

- **χ² survival** via regularized incomplete gamma matches tabulated critical values:
  χ²_{0.05}(2)=5.9915, χ²_{0.05}(3)=7.8147, χ²_{0.01}(2)=9.2103 (delta 1e-4).
- **Kruskal–Wallis** matches the SciPy reference (H=0.7714, p=0.6799 to 3 places on
  the Hollander–Wolfe-style dataset); separated groups [1..5]/[6..10]/[11..15] give
  H=12.5; tie correction C<1 applied when ties are present.
- **Dunn:** SE=√(N(N+1)/12·(1/n_i+1/n_j)) and z verified against hand computation
  (SE=2.8284, z(A,B)=−1.7678); Holm adjustment verified (raw 0.00041 → 0.00122).
  Mean ranks recorded (3/8/13). CLD from Dunn's matrix satisfies the invariants.
- **Mann-Whitney U** (two groups): U1=0, U2=25, z=−2.5067, p=0.01219 on
  [1..5]/[6..10] verified against hand computation (with continuity + tie
  correction); U1+U2=n1·n2 invariant; tie-correction flag; small-n note. Routed by
  the orchestrator for the two-group non-parametric case.
- **Guardrail (spec §82):** the non-parametric path runs ONLY when explicitly
  requested (Advanced mode `nonparametric=True`); it is never triggered by a
  normality test. Verified in `tests/test_orchestrator.py::TestNonParametricFlow`.

## 17c. Two-way (factorial) ANOVA (`tests/test_two_way_anova.py`)

Balanced 2×2, n=3 dataset: SS_A=108, SS_B=27, SS_AB=0, SS_error=8, SS_total=143
(matches hand computation; decomposition identity holds); df=(1,1,1,8); F_A=108,
F_B=27. A crossover dataset yields a dominant, highly significant interaction with
weak main effects. Guards: unbalanced cells refused; missing cell refused; a single
replicate per cell refused (no error df). Orchestration (`analyze_two_way`) produces
the effect table, per-cell descriptives, and interaction-aware interpretation; the
decision engine routes n_factors==2 to two-way and refuses 3+ factors.

## 18. Oracle cross-validation (`tests/test_oracle.py`) — lab environment

When SciPy/statsmodels are installed, the core is cross-checked:
`f_oneway` (F,p to 1e-9), `studentized_range.ppf` (to 1e-4), `pairwise_tukeyhsd`
adjusted p (to 1e-3). These tests **skip with a notice** in the offline sandbox.

**Action item for the lab:** run the suite with `pip install scipy statsmodels numpy`
present so the oracle tests execute; record any deviations here.

---

## 19. Current status

- **Total automated tests:** 169 (165 run + 4 oracle tests skipped when the
  scientific stack is absent locally).
- **All offline tests pass** on Python 3.9–3.13 (CI matrix).
- **Oracle cross-validation now runs in CI** (`.github/workflows/ci.yml`,
  `oracle-tests` job): SciPy/statsmodels/numpy are installed and the
  `tests/test_oracle.py` checks execute — closing the previously-outstanding
  technical risk TRK-2. The pure-Python core is cross-validated against SciPy
  (`f_oneway`, `studentized_range`) and statsmodels (`pairwise_tukeyhsd`) on every
  push and pull request.
- **No known numerical defect.**
