# StatLab — Critical Statistical Review (FASE 4)

Per spec §101/§103, I reviewed the requirements critically and did **not** rubber-stamp
them. Below are genuine statistical/technical issues found in the specification, each
with severity, the problem, and the recommended resolution. Items marked **[BLOCKER]**
would produce incorrect science if implemented literally; **[AMBIGUITY]** needs a
decision; **[REFINEMENT]** improves correctness/clarity.

---

## 1. [BLOCKER → resolved] "Tukey after a significant ANOVA" coupling

**Spec:** §33/§80 present the flow ANOVA-significant → Tukey, and §37 says in Quick
mode a non-significant omnibus suppresses post-hoc.

**Issue.** Tukey HSD is a *self-contained* simultaneous procedure that controls FWER
on its own; it does **not** require a prior significant ANOVA, and gating Tukey on the
ANOVA (the "Fisher LSD-style" two-stage logic) is statistically unnecessary for Tukey
and can even distort error rates. Conversely, an ANOVA can be significant while Tukey
finds no significant pair (and vice-versa), because they test different things.

**Resolution (adopted).** Keep the Quick-mode *UX* default of not auto-running
post-hoc after a non-significant omnibus (this is a reasonable, conservative default
and the spec's explicit wish), BUT document clearly that this is a **workflow choice,
not a mathematical requirement**, and Advanced mode allows Tukey/Games–Howell
regardless of the omnibus (spec §37 already permits this). The engine must never state
that a non-significant ANOVA *forbids* comparisons. Implemented in
`decision_engine`: `run_posthoc` is a recommendation flag, not a hard gate.

---

## 2. [BLOCKER → resolved] Games–Howell must NOT reuse ANOVA/Welch df or pooled SE

**Spec:** §36 lists Welch→Games–Howell but doesn't pin the df/SE.

**Issue.** A common implementation error is to feed Games–Howell the pooled MS_within
or a single df. Games–Howell is defined with a **per-pair** Welch–Satterthwaite df and
an **unpooled** SE. Using pooled quantities silently turns it into something else.

**Resolution (adopted).** `games_howell.py` uses, for each pair, its own
`df_ij = (s_i²/n_i + s_j²/n_j)² / [ (s_i²/n_i)²/(n_i−1) + (s_j²/n_j)²/(n_j−1) ]` and
`SE_ij = sqrt(s_i²/n_i + s_j²/n_j)`, with the studentized-range q evaluated at that
per-pair df. Pinned in design §8 and covered by test A7.

---

## 3. [BLOCKER → resolved] CLD must be built from the significance matrix, never mean order

**Spec:** §42/§43 correctly demand a matrix-based algorithm; §46 offers "a at highest
mean" as a *visual* convention.

**Issue (guardrail).** The single most common CLD bug is generating letters by sorting
means and thresholding gaps. That is wrong and can violate the disjointness invariant.

**Resolution (adopted).** `cld.py` consumes only the boolean significance matrix
(Piepho insert-absorb, design §10). Mean order affects **only** the left-to-right
labeling of already-computed columns (cosmetic). Property tests (A8) assert INV-1
(significant ⇒ disjoint letters) and INV-2 (non-significant ⇒ shared letter) on random
matrices, so a regression to mean-order logic would fail loudly.

**Sub-note [REFINEMENT].** INV-2 ("non-significant ⇒ shared letter") is only always
satisfiable when the "not-significant" relation is such that a valid covering exists;
with intransitive significance (A≠C, A=B, B=C) the correct CLD gives B two letters.
This is expected (documented SRK-4). The invariant as tested is: *for the produced
display*, every non-significant pair shares ≥1 letter — which the algorithm guarantees
by construction (it never splits a column unless the pair is significant).

---

## 4. [AMBIGUITY → resolved] Direction/sign convention of the pairwise difference

**Spec:** §39 says `Diferença = Média Grupo 1 − Média Grupo 2`.

**Issue.** "Group 1/Group 2" is undefined until an ordering is fixed; the sign of the
difference and the CI depends on it. Different orderings flip signs and confuse users.

**Resolution (adopted).** For every unordered pair, define Group 1 = the group listed
first in the **canonical group order** (default: original input order; or the chosen
visual order, but recorded explicitly per comparison). `diff = mean_1 − mean_2`,
CI symmetric around diff. The report states the convention. The *significance* and
*adjusted p* are order-invariant.

---

## 5. [REFINEMENT] "IC" for descriptive stats vs simultaneous CIs are different objects

**Spec:** §51/§52 ask for a per-group CI (descriptive); §39 asks for the Tukey
*simultaneous* CI.

**Clarification (adopted).** These are distinct and must be labeled distinctly:
- Descriptive per-group CI: `mean ± t_{1−α/2, n_i−1} · SE_i` (marginal, one group).
- Tukey/Games–Howell CI on a *difference*: `diff ± q_crit · SE` (simultaneous, family).
Mixing them (e.g. plotting per-group t-CIs and reading pairwise significance off
overlap) is a known fallacy; the UI will not imply that non-overlap of per-group CIs
equals a significant pairwise difference. Documented in methodology.

---

## 6. [AMBIGUITY → resolved] Quartile / percentile method unspecified

**Spec:** §51 asks for Q1/Q3/IQR but not the estimator.

**Issue.** There are ≥9 quartile definitions; Excel's `QUARTILE.INC`, R type 7, and
others disagree, especially for small n. Reproducibility (priority #3) demands a fixed,
documented choice.

**Resolution (adopted).** Use the **type-7 / linear-interpolation** method (numpy &
R default) for Q1/Q3/median-consistency, documented in design §3, and note that this
matches numpy but may differ slightly from Excel's default. This is a *display/summary*
statistic and does not enter ANOVA.

---

## 7. [REFINEMENT] omega² can be negative; effect-size labels are conventions

**Spec:** §47 asks for η²/ω².

**Resolution (adopted).** ω² and partial ω² can be negative for small/near-null
effects; we **clamp to 0 for display** and note it. η² is upward-biased; we report both
and prefer ω² for reporting. Small/medium/large labels are shown only with an explicit
"convention, context-dependent" caveat (spec §47/§48 already require this).

---

## 8. [AMBIGUITY → resolved] Welch summary-mode edge cases

**Spec:** §28/§92 permit Welch from (mean, SD, n).

**Issue.** Welch needs `s_i² > 0` and `n_i ≥ 2`. A group with `sd = 0` gives an
infinite weight `w_i = n_i/s_i²`. Silent handling would corrupt the result.

**Resolution (adopted).** Refuse-with-explanation when any group has `sd = 0`
(or `n_i < 2`) for Welch; suggest inspecting that group (possibly a constant / a data
error / true zero variance). Same guard for classical ANOVA when *all* within-group
variance is 0 (MS_within = 0 ⇒ F undefined). Encoded in `anova`/`welch` guards
(design §4.1, §5).

---

## 9. [REFINEMENT] "Detect impossible values / negative SD" — scope

**Spec:** §16 lists "DP negativo", "valores impossíveis".

**Clarification (adopted).** For raw data, negative SD is not an input (it's computed).
The negative-SD / invalid-n checks apply to **summary-mode input** (`group|mean|sd|n`):
sd < 0 → ERROR; n < 1 or non-integer → ERROR; n = 1 → sd/CI undefined (WARNING).
"Impossible values" is intentionally scoped to mathematically detectable cases
(non-finite, negative variance) — the tool cannot know domain bounds (e.g. a
concentration can't be negative) because it is domain-neutral by design; such
domain limits are the researcher's responsibility (§2 of requirements).

---

## 10. [REFINEMENT] Normality is about residuals, not raw group values — and Shapiro scope

**Spec:** §25 correctly emphasizes residuals and warns against absolute Shapiro rules.

**Clarification (adopted).** For one-way ANOVA the residual e_ij = x_ij − x̄_i, so the
"residual normality" test is equivalent to a within-group normality assessment pooled
across groups after centering. We run Shapiro on the pooled residuals (Royston, valid
~3 ≤ n ≤ 5000), and ALSO offer per-group Q–Q. We never gate ANOVA on Shapiro (SR-5).
For n < 3 total-per-context, Shapiro is not computed (reported as N/A).

---

## 11. [BLOCKER → resolved] "Kruskal–Wallis if Shapiro p<0.05" temptation

**Spec:** §82 explicitly forbids auto-switching to non-parametric on Shapiro alone.

**Confirmation.** Adopted as written. The decision engine will NOT branch to a
non-parametric method (not implemented in v1 anyway) based on a normality test.
Recorded so a future contributor doesn't add this anti-pattern.

---

## 12. [REFINEMENT] Two-group case: which t-test, and the F=t² claim

**Spec:** §38 says prefer t / Welch-t for two groups; F = t².

**Clarification (adopted).** The identity F = t² holds specifically for **classical
one-way ANOVA vs the pooled (equal-variance) Student t** with the same data.
It does **not** hold for Welch-ANOVA vs Welch-t in general (different df), though they
are closely related. The engine recommends: equal-variance ⇒ Student t (F=t² exact);
unequal-variance ⇒ Welch t. The F=t² regression test uses the pooled t. Documented so
the equivalence claim is not overstated.

---

## 13. [REFINEMENT] Pseudoreplication: warn, and offer the correct fix

**Spec:** §17/§74/§85 require detecting/ warning technical replicates.

**Clarification (adopted).** The tool cannot *detect* pseudoreplication from numbers
alone (it's a design fact). It (a) asks in the wizard, (b) warns when the user declares
technical replicates but still requests independent-group analysis, and (c) offers the
statistically correct remedy: **aggregate technical replicates to the experimental-unit
mean** and analyze those unit means (n = number of independent units). This is
implemented in `transformer.py`. We do not silently do this; it's an offered action.

---

## 14. [REFINEMENT] Multiplicity across batch variables

**Spec:** §57 wants FDR/Holm readiness, not auto-applied.

**Clarification (adopted).** Two multiplicity layers exist and must not be conflated:
(a) *within* one analysis across pairwise comparisons — handled by Tukey/Games–Howell
FWER control; (b) *across* many response variables in batch — NOT corrected by the
per-variable post-hoc. We surface a batch-level warning and provide an *optional*
Holm/BH adjustment over the vector of omnibus p-values, clearly labeled, never on by
default. Architecture placed in `effect_sizes`/a new `multiplicity.py` later.

---

## 15. [REFINEMENT] Studentized-range accuracy is the main numerical risk

**Spec:** §41 asks for a reliable library or validated formula.

**Clarification (adopted).** Since the sandbox has no scipy, we implement q(k,ν) by
quadrature (design §2.4) and pin accuracy with tabulated critical values (Harter tables
/ standard q-tables) and, where the stack exists, `scipy.stats.studentized_range` as an
oracle (tol documented). This is the top technical risk (TRK-1) and gets the densest
test coverage. If in implementation the quadrature cannot hit tolerance for extreme
(k, ν), we will STOP and surface the limitation rather than ship an inaccurate p
(priority #1/#2, spec §77/§103).

---

## 16. [REFINEMENT] "Never display p = 0" and precision

Adopted: internal value kept full precision; display uses `format_p` → `"< 0.001"`
(threshold configurable). For extremely small p from the F/beta tails, the incomplete
beta returns a tiny but positive value; we never coerce to exactly 0 for storage.

---

## 17. [AMBIGUITY → decision] `.xls` legacy support

**Spec:** §11 lists `.xls`.

**Decision.** First-class support for `.xlsx` and `.csv` (and paste). `.xls` (BIFF) is
best-effort via `xlrd` if installed; if not, we show a clear message asking the user to
re-save as `.xlsx`/`.csv`. Rationale: `xlrd` dropped `.xlsx` and `.xls` support has
become fragile; forcing it would add a shaky dependency for a legacy format (TRK-3).

---

## Summary of adopted deviations from a literal reading

| # | Spec clause | Adopted resolution |
|---|-------------|--------------------|
| 1 | §33/§37 ANOVA-gates-Tukey | Quick-mode UX default only; not a math gate; Advanced overrides |
| 2 | §36 Welch→GH | Per-pair Welch–Satterthwaite df + unpooled SE (pinned) |
| 3 | §42–46 CLD | Matrix-only Piepho; mean order is cosmetic; invariants tested |
| 4 | §39 diff sign | Canonical order fixes Group1/Group2; sign convention recorded |
| 5 | §39/§51 CIs | Descriptive t-CI ≠ simultaneous CI; UI won't imply overlap⇒sig |
| 6 | §51 quartiles | Type-7 (numpy/R) fixed & documented |
| 7 | §47 effect size | ω² clamp ≥0; labels flagged as conventions |
| 8 | §28/§92 Welch summary | Refuse if sd=0 or n<2 |
| 9 | §16 validation | Negative-SD/invalid-n scoped to summary input; domain bounds = user's |
| 12 | §38 F=t² | Holds for pooled Student t only; Welch-t is separate |
| 13 | §17 pseudoreplication | Cannot auto-detect; warn + offer unit-mean aggregation |
| 14 | §57 multiplicity | Two layers; batch FDR optional, never automatic |
| 17 | §11 `.xls` | `.xlsx`/`.csv` first-class; `.xls` best-effort |

None of these deviations reduce statistical correctness; each increases it or resolves
an ambiguity in favor of the stricter, more defensible choice (priority order §0).

**Open questions for the user (do not block core implementation):**
- Q1: Confirm dependency strategy (A) pure-stdlib core (recommended). Proceeding with (A).
- Q2: PDF backend preference — matplotlib PdfPages (zero extra dep) vs reportlab
  (richer layout, extra dep). Proceeding with PdfPages unless you prefer reportlab.
- Q3: Default "a"-at-highest-mean CLD convention vs "a"-at-lowest — cosmetic only.
  Proceeding with highest-mean = "a".
