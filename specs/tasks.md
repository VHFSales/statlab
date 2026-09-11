# StatLab — Implementation Plan (tasks.md)

**Status:** v0.1 (FASE 3). Order follows spec §102. Each task lists its deliverable
and its validation gate. A task is "done" only when its tests pass at the specified
tolerances. Statistical correctness gates everything (priority #1).

Legend: [ ] todo · [~] in progress · [x] done · (v) has a numeric validation gate

---

## Milestone A — Statistical core (pure stdlib)  ← v1 critical path

- [ ] A0. `types.py`, `formatting.py` — dataclasses; display rounding; `format_p`
      (`p<0.001`); never round intermediates. (FR-7, SR-11)
- [ ] A1. (v) `distributions.py` — incomplete beta (Lentz), Student-t CDF, F CDF,
      normal CDF/quantile (AS241), studentized-range CDF & quantile (quadrature +
      Brent). Gate: match tabulated t/F/q critical values and, if available, scipy
      (tol: 1e-6 on CDF, 1e-5 on quantiles). (design §2.3, §2.4)
- [ ] A2. (v) `descriptive.py` — full per-group table + missing counts. Gate: match
      hand-computed values and numpy defaults (quartile type 7). (SR-1, design §3)
- [ ] A3. (v) `anova.py` — raw + summary one-way ANOVA. Gates: SS_b+SS_w=SS_t;
      raw==summary on equivalent data; F=t² for k=2; reference datasets. (SR-2, §4)
- [ ] A4. (v) `welch.py` — Welch ANOVA (raw/summary). Gate: known heteroscedastic
      datasets; statistic/df1/df2/p vs reference (and scipy if present). (SR-3, §5)
- [ ] A5. (v) `effect_sizes.py` — eta², omega², partial eta², Cohen's d. Gate:
      reference values; omega² clamp behavior. (SR-10, §9)
- [ ] A6. (v) `tukey.py` — Tukey HSD / Tukey–Kramer. Gates: balanced==HSD; unbalanced
      Tukey–Kramer vs reference/statsmodels; simultaneous CI & adjusted p; direction
      of diff. (SR-6, §7)
- [ ] A7. (v) `games_howell.py` — Games–Howell. Gate: unequal var & n vs reference
      (e.g. R `PMCMRplus`/`rstatix` published values). (SR-7, §8)
- [ ] A8. (v) `cld.py` — Piepho insert-absorb. Gates: {A:a,B:ab,C:b} canonical case;
      INV-1/INV-2/INV-3; property tests on random matrices; >26 groups. (SR-12, §10, §73)
- [ ] A9. `assumptions.py` — residuals, Q–Q points, Levene, Brown–Forsythe,
      Shapiro–Wilk (Royston), independence note. Gate: Levene/BF as F-on-deviations
      vs reference; Shapiro W & p vs reference tables/scipy. (SR-5, §6)
- [ ] A10. `outliers.py` — IQR & Grubbs diagnostics (never auto-exclude). (FR-17)
- [ ] A11. (v) `decision_engine.py` — recommend()+guardrails+reasons. Gate: the §74
      decision matrix (classical→Tukey; unbalanced→Tukey–Kramer; Welch→Games–Howell;
      Welch⇏Tukey; 2 groups⇏Tukey; ≥2 factors⇏silent one-way; repeated/paired⇏
      independent; tech-replicates⇒pseudoreplication warning). (SR-4/§11)

## Milestone B — Data layer
- [ ] B1. `data/model.py` — Project/Experiment/Variable/Group + DesignSpec + unit
      structure. (FR-1, FR-2, FR-10)
- [ ] B2. `data/validator.py` — FR-9 checks → typed issues. (FR-9)
- [ ] B3. `data/transformer.py` — wide↔long, missing handling (no zero-fill),
      technical-replicate aggregation. (FR-3, FR-8, FR-10)
- [ ] B4. `data/importer.py` — xlsx/csv/paste + wide/long detection + preview.
      (FR-4) [needs pandas → guarded import + graceful message if absent]

## Milestone C — Orchestration & persistence
- [ ] C1. `app/core/orchestrator.py` — end-to-end analyze(); AnalysisResult + audit;
      staleness on data change; batch mode + cross-variable multiplicity warning.
      (FR-13, FR-19, §16)
- [ ] C2. `persistence/project_store.py` — JSON save/load, data hashing, snapshots.
      (FR-1.4, FR-1.5, FR-19)

## Milestone D — Interface (Streamlit)  ← only after A/B/C validated
- [ ] D1. App shell + sections PROJETO/DADOS/DELINEAMENTO/DESCRITIVA/PRESSUPOSTOS/
      ANÁLISE/PÓS-TESTES/GRÁFICOS/RELATÓRIO/EXPORTAR. (FR-14, spec §9)
- [ ] D2. Quick mode wizard (§86) + Advanced mode controls (§87). (FR-12)
- [ ] D3. Results screen (§58): method, global, p, effect size, summary+letters, plot;
      expandable detail; "why this test"; help "?"; ordering (visual only). (FR-14, FR-16)

## Milestone E — Plots & export
- [ ] E1. `plots/scientific_plots.py` — box/violin/strip/scatter/mean±SD/±SE/+CI/
      individual+mean/Q–Q/resid-vs-fitted + CLD overlay; PNG/SVG/PDF export. (FR-15)
- [ ] E2. `reports/interpreter.py` — RESULTADO block, APA sentence, why-this-test;
      SR-11 guardrails. (FR-14.4, spec §58–60)
- [ ] E3. `reports/excel_export.py` — mandated sheets incl. Resumo & Auditoria. (FR-18.2)
- [ ] E4. `reports/pdf_report.py` — scientific PDF. (FR-18.3)

## Milestone F — Validation & docs
- [ ] F1. (v) Reference dataset battery + tolerances (§89); consolidate all gates.
- [ ] F2. Oracle cross-validation harness (scipy/statsmodels), skip-with-notice offline.
- [ ] F3. `docs/methodology.md` — what/when/assumptions/interpretation/formulas/refs;
      "ANOVA ≠ Tukey ≠ CLD". (spec §90–91)
- [ ] F4. Regression-test policy wired into CI (spec §75).

---

## Execution notes
- Milestone A is implemented and validated **before** any UI work (spec FASE 5→7).
- Every statistical bug ⇒ a reproducing regression test first (spec §75).
- No new dependency without a justification recorded in `design.md` §1/§6.
- Offline sandbox: A0–A11 + CLD/decision tests run fully on stdlib; oracle (F2) and
  pandas/matplotlib/openpyxl tasks (B4, E*, reports) are implemented but their
  live-run validation is deferred to an environment with the stack installed (TRK-2).
