"""Automatic interpretation text (FR-14.4, SR-11, spec 58-60).

All wording obeys the guardrails: never "means are equal"; never causal or
importance claims from p; p formatted as "< 0.001"; no invented mechanism.
"""

from __future__ import annotations

from typing import Optional

from statistics.formatting import format_p, format_number
from statistics.types import AnovaTable, EffectSizes, PostHocResult, WelchResult


def omnibus_conclusion(p: float, alpha: float) -> str:
    if p < alpha:
        return ("Há evidência estatística contra a hipótese de igualdade de todas "
                "as médias.")
    return ("Não há evidência estatística suficiente para rejeitar a hipótese de "
            "igualdade das médias. (A ausência de significância não comprova "
            "igualdade.)")


def omnibus_conclusion_rank(p: float, alpha: float) -> str:
    """Conclusion wording for rank-based (non-parametric) omnibus tests.

    Kruskal-Wallis compares distributions/rank locations, NOT means.
    """
    if p < alpha:
        return ("Há evidência estatística de que pelo menos um grupo tende a "
                "apresentar valores (postos) diferentes dos demais.")
    return ("Não há evidência estatística suficiente para afirmar que os grupos "
            "diferem quanto à distribuição/posição (postos). A ausência de "
            "significância não comprova igualdade das distribuições.")


def apa_anova(table: AnovaTable, effects: Optional[EffectSizes],
              alpha: float = 0.05, decimals: int = 3) -> str:
    df1 = int(table.df_between)
    df2 = int(table.df_within)
    f = format_number(table.f, decimals)
    p = format_p(table.p, decimals)
    txt = (f"A análise de variância de uma via indicou "
           + ("diferença estatisticamente significativa"
              if table.p < alpha else "ausência de diferença estatisticamente "
              "significativa")
           + f" entre os grupos, F({df1},{df2}) = {f}, p {_p_rel(table.p, p)}")
    if effects is not None and effects.omega_squared == effects.omega_squared:
        txt += f", \u03c9\u00b2 = {format_number(effects.omega_squared, decimals)}"
    txt += "."
    return txt


def apa_welch(res: WelchResult, alpha: float = 0.05, decimals: int = 3) -> str:
    p = format_p(res.p, decimals)
    return (f"A ANOVA de Welch (não assume homogeneidade de variâncias) indicou "
            + ("diferença estatisticamente significativa"
               if res.p < alpha else "ausência de diferença estatisticamente "
               "significativa")
            + f" entre os grupos, F({int(res.df1)}, "
            f"{format_number(res.df2, 2)}) = {format_number(res.statistic, decimals)}, "
            f"p {_p_rel(res.p, p)}.")


def posthoc_sentence(res: PostHocResult, decimals: int = 3) -> str:
    total = len(res.comparisons)
    sig = sum(1 for c in res.comparisons if c.significant)
    return (f"O teste post hoc de {res.method} identificou diferenças "
            f"estatisticamente significativas em {sig} de {total} comparações "
            f"par a par (\u03b1 = {res.alpha}).")


def _p_rel(p_value: float, p_display: str) -> str:
    """Return '< 0.001' style or '= 0.023'."""
    return p_display if p_display.startswith("<") else f"= {p_display}"


def why_this_test(reasons) -> str:
    return "Método escolhido.\n\nMotivo:\n- " + "\n- ".join(reasons)
