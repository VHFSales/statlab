"""Decision engine (SR-4..SR-9, spec 74/80, design section 11).

Pure recommendation logic. It NEVER executes tests; it inspects a declared design
and computed diagnostics and returns a Recommendation with method, post-hoc,
whether to auto-run post-hoc, human-readable reasons, warnings, and refusals.

Guardrails (critical review items 1, 2, 11): a non-significant omnibus is NOT a
mathematical prohibition on comparisons; the decision is holistic (not a rigid
Levene gate); it never switches to non-parametric based on a normality test.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class DesignSpec:
    """User-declared experimental design."""
    n_response_vars: int = 1
    n_factors: int = 1
    independent_groups: bool = True
    repeated_measures: bool = False
    paired: bool = False
    blocks: bool = False
    multiple_obs_per_unit: bool = False   # technical replicates present
    independent_units_asserted: bool = True  # user says obs = independent units


@dataclass
class Diagnostics:
    """Computed cues feeding the recommendation (all optional)."""
    k_groups: int = 0
    n_per_group: Optional[List[int]] = None
    variance_ratio: float = math.nan       # max/min group variance
    levene_p: float = math.nan
    brown_forsythe_p: float = math.nan
    balanced: Optional[bool] = None


@dataclass
class Recommendation:
    method: Optional[str]         # "one-way ANOVA" | "Welch's ANOVA" | "t-test..." | None
    posthoc: Optional[str]        # "Tukey HSD" | "Tukey-Kramer" | "Games-Howell" | None
    run_posthoc: bool
    alpha: float
    reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    refusals: List[str] = field(default_factory=list)

    @property
    def is_refused(self) -> bool:
        return self.method is None and bool(self.refusals)


def recommend(design: DesignSpec, diag: Diagnostics, alpha: float = 0.05,
              omnibus_p: Optional[float] = None,
              heteroscedastic_threshold_ratio: float = 3.0) -> Recommendation:
    rec = Recommendation(method=None, posthoc=None, run_posthoc=False, alpha=alpha)

    # --- Design-level routing / refusals --------------------------------- #
    if design.n_factors == 2:
        rec.method = "two-way ANOVA"
        rec.posthoc = None
        rec.reasons.append(
            "Foram declarados dois fatores cruzados: uma ANOVA de duas vias "
            "(fatorial), que estima os dois efeitos principais e a interação, é o "
            "método apropriado — não a ANOVA de uma via."
        )
        rec.warnings.append(
            "A ANOVA de duas vias exige delineamento balanceado (mesmo nº de "
            "repetições por célula) nesta versão."
        )
        return rec
    if design.n_factors is not None and design.n_factors >= 3:
        rec.refusals.append(
            "Foram declarados 3 ou mais fatores. ANOVA fatorial de ordem superior "
            "não está implementada nesta versão; a ANOVA de uma via não será "
            "aplicada automaticamente."
        )
        return rec

    if design.repeated_measures:
        if diag.k_groups is not None and diag.k_groups >= 3:
            rec.method = "Friedman"
            rec.posthoc = "Nemenyi"
            rec.reasons.append(
                "Foram declaradas medidas repetidas (3+ condições relacionadas). "
                "O teste de Friedman (não-paramétrico) com pós-teste de Nemenyi é a "
                "abordagem disponível nesta versão. A ANOVA de medidas repetidas "
                "paramétrica ainda não foi implementada."
            )
            rec.warnings.append(
                "Friedman exige delineamento de blocos completos (cada sujeito "
                "medido em todas as condições, sem ausentes)."
            )
            return rec
        rec.refusals.append(
            "Foram declaradas medidas repetidas com menos de 3 condições. Para 2 "
            "condições dependentes, use um teste pareado (t pareado ou Wilcoxon)."
        )
        return rec

    if design.paired:
        if diag.k_groups == 2:
            rec.method = "paired test"
            rec.reasons.append(
                "Foram declaradas duas condições pareadas (dependentes). O teste "
                "apropriado é o teste t pareado (ou Wilcoxon signed-rank, na versão "
                "não-paramétrica) — não um teste para grupos independentes."
            )
            return rec
        rec.refusals.append(
            "Foram declarados dados pareados com um número de condições diferente "
            "de 2. Um teste pareado de duas condições ou uma ANOVA de medidas "
            "repetidas (para 3+ condições) é apropriado; a análise de grupos "
            "independentes não será aplicada."
        )
        return rec

    if design.blocks:
        rec.refusals.append(
            "Foi declarada estrutura de blocos; um modelo com blocos é mais "
            "apropriado do que a ANOVA de uma via."
        )
        return rec

    # --- Pseudoreplication warning (does not hard-block) ----------------- #
    if design.multiple_obs_per_unit and not design.independent_units_asserted:
        rec.warnings.append(
            "ATENÇÃO: possíveis replicatas técnicas foram identificadas. Tratar "
            "medições da mesma unidade como observações independentes pode causar "
            "pseudorreplicação e invalidar a inferência. Considere agregar as "
            "replicatas técnicas à média da unidade experimental."
        )

    if not design.independent_groups:
        rec.refusals.append(
            "Os grupos foram declarados como não independentes; a ANOVA de uma via "
            "assume independência entre grupos."
        )
        return rec

    k = diag.k_groups
    if k is None or k < 2:
        rec.refusals.append("São necessários pelo menos 2 grupos.")
        return rec

    # --- Two groups: prefer a t-test ------------------------------------- #
    if k == 2:
        # heteroscedasticity cue chooses Student vs Welch t
        het = _is_heteroscedastic(diag, heteroscedastic_threshold_ratio)
        if het:
            rec.method = "Welch's t-test"
            rec.reasons.append(
                "Há apenas dois grupos independentes e há indícios de variâncias "
                "diferentes; o teste t de Welch é preferível."
            )
        else:
            rec.method = "Student's t-test"
            rec.reasons.append(
                "Há apenas dois grupos independentes com variâncias semelhantes; "
                "o teste t de Student é preferível (equivalente à ANOVA de uma via, "
                "com F = t²)."
            )
        rec.posthoc = None
        rec.run_posthoc = False
        rec.warnings.append(
            "Com dois grupos não é necessário um pós-teste como Tukey."
        )
        return rec

    # --- >= 3 groups: classical vs Welch (holistic, not a rigid gate) ---- #
    het = _is_heteroscedastic(diag, heteroscedastic_threshold_ratio)
    balanced = diag.balanced
    if balanced is None and diag.n_per_group:
        balanced = len(set(diag.n_per_group)) == 1

    if het:
        rec.method = "Welch's ANOVA"
        rec.posthoc = "Games-Howell"
        reason = ["Há um fator com grupos independentes e >= 3 níveis."]
        cues = []
        if not math.isnan(diag.variance_ratio):
            cues.append(f"razão de variâncias ≈ {diag.variance_ratio:.2f}")
        if not math.isnan(diag.brown_forsythe_p):
            cues.append(f"Brown-Forsythe p = {diag.brown_forsythe_p:.4f}")
        elif not math.isnan(diag.levene_p):
            cues.append(f"Levene p = {diag.levene_p:.4f}")
        if diag.n_per_group and len(set(diag.n_per_group)) > 1:
            cues.append("tamanhos amostrais desiguais")
        reason.append(
            "Foram observados indícios relevantes de heterogeneidade de variâncias"
            + (f" ({'; '.join(cues)})" if cues else "")
            + ", portanto a ANOVA de Welch é recomendada, seguida de Games-Howell."
        )
        rec.reasons.extend(reason)
    else:
        rec.method = "one-way ANOVA"
        rec.posthoc = "Tukey HSD" if balanced else "Tukey-Kramer"
        reason = [
            "Existe uma variável resposta quantitativa, um fator categórico e "
            "grupos independentes, e os diagnósticos não indicaram heterogeneidade "
            "relevante das variâncias.",
        ]
        if balanced:
            reason.append("Tamanhos amostrais iguais: Tukey HSD.")
        else:
            reason.append("Tamanhos amostrais desiguais: Tukey-Kramer.")
        rec.reasons.extend(reason)

    # --- Post-hoc auto-run policy (Quick mode) --------------------------- #
    if omnibus_p is None:
        rec.run_posthoc = True  # caller will run omnibus first
    elif omnibus_p < alpha:
        rec.run_posthoc = True
    else:
        rec.run_posthoc = False
        rec.warnings.append(
            "O teste global não apresentou significância estatística. Comparações "
            "pós-hoc não foram executadas automaticamente (modo rápido). No modo "
            "avançado é possível executá-las com justificativa registrada."
        )
    return rec


def _is_heteroscedastic(diag: Diagnostics, ratio_threshold: float) -> bool:
    """Holistic heteroscedasticity cue (NOT a single rigid rule).

    Flags heteroscedasticity if EITHER a robust test (Brown-Forsythe, else Levene)
    is significant OR the variance ratio is large. Deliberately conservative;
    the researcher can override in Advanced mode.
    """
    signals = 0
    p = diag.brown_forsythe_p
    if math.isnan(p):
        p = diag.levene_p
    if not math.isnan(p) and p < 0.05:
        signals += 1
    if not math.isnan(diag.variance_ratio) and diag.variance_ratio >= ratio_threshold:
        signals += 1
    return signals >= 1
