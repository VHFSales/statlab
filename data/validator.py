"""Data validation (FR-9). Returns typed Issues; never crashes.

Covers: text in numeric field, unexpected NaN, infinity, negative SD, invalid n,
empty groups, zero variance, duplicate labels, insufficient n, insufficient data
for the requested method. Domain bounds (e.g. concentration >= 0) are intentionally
NOT enforced: the tool is domain-neutral (critical review item 9).
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional

from statistics.types import Issue


def _coerce_float(x) -> Optional[float]:
    if x is None or x == "":
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return "TEXT"  # sentinel for non-numeric text


def validate_raw(raw: Dict[str, List], min_n_for_analysis: int = 2) -> List[Issue]:
    issues: List[Issue] = []
    labels = list(raw.keys())

    seen = set()
    for lab in labels:
        if lab in seen:
            issues.append(Issue("ERROR", "DUP_LABEL",
                                f"Rótulo de grupo duplicado: '{lab}'.", lab))
        seen.add(lab)

    if len(labels) < 2:
        issues.append(Issue("ERROR", "TOO_FEW_GROUPS",
                            "São necessários pelo menos 2 grupos.", None))

    for lab, vals in raw.items():
        clean, n_missing, n_text = [], 0, 0
        for v in vals:
            fv = _coerce_float(v)
            if fv == "TEXT":
                n_text += 1
            elif fv is None:
                n_missing += 1
            elif math.isnan(fv):
                n_missing += 1
            elif math.isinf(fv):
                issues.append(Issue("ERROR", "INFINITE",
                                    f"Grupo '{lab}': valor infinito encontrado.", lab))
            else:
                clean.append(fv)

        if n_text:
            issues.append(Issue("ERROR", "NON_NUMERIC",
                                f"Grupo '{lab}': {n_text} valor(es) não numérico(s) "
                                f"em campo numérico.", lab))
        if len(clean) == 0:
            issues.append(Issue("ERROR", "EMPTY_GROUP",
                                f"Grupo '{lab}': nenhum valor válido.", lab))
            continue
        if len(clean) < min_n_for_analysis:
            issues.append(Issue("WARNING", "SMALL_N",
                                f"ATENÇÃO: o grupo '{lab}' possui apenas "
                                f"{len(clean)} observação(ões) válida(s).", lab))
        if len(clean) >= 2:
            m = math.fsum(clean) / len(clean)
            var = math.fsum((x - m) ** 2 for x in clean) / (len(clean) - 1)
            if var == 0.0:
                issues.append(Issue("WARNING", "ZERO_VARIANCE",
                                    f"ATENÇÃO: o grupo '{lab}' tem variância zero "
                                    f"(todos os valores iguais).", lab))
        if n_missing:
            issues.append(Issue("INFO", "MISSING",
                                f"Grupo '{lab}': {n_missing} valor(es) ausente(s) "
                                f"(não convertidos em zero).", lab))
    return issues


def validate_summary(summary: Dict[str, Dict]) -> List[Issue]:
    issues: List[Issue] = []
    if len(summary) < 2:
        issues.append(Issue("ERROR", "TOO_FEW_GROUPS",
                            "São necessários pelo menos 2 grupos.", None))
    for lab, s in summary.items():
        n = s.get("n")
        sd = s.get("sd")
        mean = s.get("mean")
        if mean is None:
            issues.append(Issue("ERROR", "NO_MEAN", f"Grupo '{lab}': média ausente.", lab))
        if n is None:
            issues.append(Issue("ERROR", "NO_N",
                                "Os dados disponíveis são insuficientes para realizar "
                                "ANOVA/Tukey. Informe o tamanho amostral de cada grupo "
                                "ou forneça os dados brutos.", lab))
        else:
            try:
                if int(n) != n or n < 1:
                    issues.append(Issue("ERROR", "BAD_N",
                                        f"Grupo '{lab}': tamanho amostral inválido "
                                        f"(n={n}).", lab))
                elif n == 1:
                    issues.append(Issue("WARNING", "N_ONE",
                                        f"ATENÇÃO: grupo '{lab}' com n=1; DP/IC "
                                        f"indefinidos.", lab))
            except (TypeError, ValueError):
                issues.append(Issue("ERROR", "BAD_N",
                                    f"Grupo '{lab}': n inválido.", lab))
        if sd is None:
            issues.append(Issue("ERROR", "NO_SD",
                                f"Grupo '{lab}': desvio padrão (DP) ausente. Sem o DP "
                                "não é possível realizar ANOVA/teste t a partir de "
                                "estatísticas resumidas. Informe o DP de cada grupo "
                                "ou forneça os dados brutos.", lab))
        elif sd < 0:
            issues.append(Issue("ERROR", "NEG_SD",
                                f"Grupo '{lab}': desvio padrão negativo.", lab))
    return issues


def has_errors(issues: List[Issue]) -> bool:
    return any(i.severity == "ERROR" for i in issues)
