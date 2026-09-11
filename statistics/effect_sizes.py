"""Effect sizes for one-way ANOVA (SR-10, design section 9).

eta^2, omega^2, partial eta^2. omega^2 is clamped to >= 0 for display with a note
(critical review item 7). Small/medium/large labels are conventions only.
"""

from __future__ import annotations

from .types import AnovaTable, EffectSizes


def effect_sizes_from_anova(table: AnovaTable) -> EffectSizes:
    ss_b = table.ss_between
    ss_w = table.ss_within
    ss_t = table.ss_total
    ms_w = table.ms_within
    df_b = table.df_between

    eta2 = ss_b / ss_t if ss_t > 0 else float("nan")
    partial_eta2 = ss_b / (ss_b + ss_w) if (ss_b + ss_w) > 0 else float("nan")

    notes = []
    denom = ss_t + ms_w
    omega2_raw = (ss_b - df_b * ms_w) / denom if denom > 0 else float("nan")
    omega2 = omega2_raw
    if omega2_raw == omega2_raw and omega2_raw < 0:  # not NaN and negative
        omega2 = 0.0
        notes.append(
            "omega^2 estimate was negative (consistent with a very small/near-null "
            "effect) and has been clamped to 0 for display."
        )
    notes.append(
        "Effect-size magnitude labels (small/medium/large) are context-dependent "
        "conventions, not statements of scientific importance."
    )
    return EffectSizes(eta_squared=eta2, omega_squared=omega2,
                       partial_eta_squared=partial_eta2, notes=notes)


def cohens_d_pooled(mean1: float, mean2: float, sd_pooled: float) -> float:
    """Cohen's d using a pooled SD (for the two-group context)."""
    if sd_pooled <= 0:
        return float("nan")
    return (mean1 - mean2) / sd_pooled
