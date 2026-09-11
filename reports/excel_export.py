"""Excel export (FR-18.2). Uses openpyxl when available; otherwise falls back to a
multi-file CSV bundle so the feature degrades gracefully in minimal environments.

Mandated sheets: Projeto, Dados, Descritiva, Pressupostos, ANOVA, Pós-testes,
Resumo, Metadados, Auditoria. The Resumo sheet contains at least:
Grupo, n, Média, DP, EP, IC inferior, IC superior, Letras.
"""

from __future__ import annotations

import csv
import io
import os
from typing import Dict, List

try:
    import openpyxl  # noqa
    HAVE_OPENPYXL = True
except Exception:
    HAVE_OPENPYXL = False


def _summary_rows(result) -> List[list]:
    desc = {d["label"]: d for d in result.descriptive}
    letters = (result.cld or {}).get("display", {})
    rows = [["Grupo", "n", "Média", "DP", "EP", "IC inferior", "IC superior", "Letras"]]
    for lab, d in desc.items():
        rows.append([lab, d["n"], d["mean"], d["sd"], d["se"],
                     d["ci_low"], d["ci_high"], letters.get(lab, "")])
    return rows


def _descriptive_rows(result) -> List[list]:
    header = ["Grupo", "n", "n_ausente", "Média", "Mediana", "DP", "Variância",
              "EP", "IC inf", "IC sup", "Mín", "Máx", "Amplitude", "Q1", "Q3",
              "IQR", "CV"]
    rows = [header]
    for d in result.descriptive:
        rows.append([d["label"], d["n"], d["n_missing"], d["mean"], d["median"],
                     d["sd"], d["variance"], d["se"], d["ci_low"], d["ci_high"],
                     d["minimum"], d["maximum"], d["range"], d["q1"], d["q3"],
                     d["iqr"], d["cv"]])
    return rows


def _anova_rows(result) -> List[list]:
    o = result.omnibus
    if not o:
        return [["(sem teste global)"]]
    if result.omnibus_kind == "anova":
        return [
            ["Fonte", "SS", "df", "MS", "F", "p"],
            ["Entre grupos", o["ss_between"], o["df_between"], o["ms_between"],
             o["f"], o["p"]],
            ["Dentro (erro)", o["ss_within"], o["df_within"], o["ms_within"], "", ""],
            ["Total", o["ss_total"], o["df_total"], "", "", ""],
        ]
    return [
        ["Método", "Estatística", "df1", "df2", "p"],
        ["Welch's ANOVA", o["statistic"], o["df1"], o["df2"], o["p"]],
    ]


def _posthoc_rows(result) -> List[list]:
    ph = result.posthoc
    if not ph:
        return [["(sem pós-teste)"]]
    rows = [["Grupo 1", "Grupo 2", "Média 1", "Média 2", "Diferença",
             "IC inf", "IC sup", "p ajustado", "Significativo"]]
    for c in ph["comparisons"]:
        rows.append([c["group1"], c["group2"], c["mean1"], c["mean2"], c["diff"],
                     c["ci_low"], c["ci_high"], c["p_adjusted"],
                     "Sim" if c["significant"] else "Não"])
    return rows


def _assumptions_rows(result) -> List[list]:
    dg = result.diagnostics or {}
    rows = [["Diagnóstico", "Estatística", "df1", "df2", "p", "Observação"]]
    lev = dg.get("levene")
    if lev:
        rows.append(["Levene (média)", lev["statistic"], lev["df1"], lev["df2"],
                     lev["p"], ""])
    bf = dg.get("brown_forsythe")
    if bf:
        rows.append(["Brown-Forsythe (mediana)", bf["statistic"], bf["df1"],
                     bf["df2"], bf["p"], ""])
    sh = dg.get("shapiro_residuals")
    if sh:
        rows.append(["Shapiro-Wilk (resíduos)", sh["statistic"], "", "", sh["p"],
                     sh.get("note", "")])
    rows.append(["Razão de variâncias", dg.get("variance_ratio", ""), "", "", "", ""])
    rows.append(["Independência", "", "", "", "", dg.get("independence_note", "")])
    return rows


def _audit_rows(result) -> List[list]:
    return [
        ["Campo", "Valor"],
        ["ID da análise", result.analysis_id],
        ["Data/hora", result.created_at],
        ["Programa", result.program_version],
        ["Núcleo estatístico", result.core_version],
        ["Python", result.python_version],
        ["alpha", result.alpha],
        ["Tipo de dados", result.data_kind],
        ["Hash dos dados", result.data_hash],
        ["Método global", result.omnibus_kind or ""],
        ["Pós-teste", (result.posthoc or {}).get("method", "")],
        ["Fonte do CLD", (result.cld or {}).get("source", "")],
    ]


def _sheets(result, project_meta: Dict = None) -> Dict[str, List[list]]:
    project_meta = project_meta or {}
    return {
        "Projeto": [["Campo", "Valor"]] + [[k, v] for k, v in project_meta.items()],
        "Descritiva": _descriptive_rows(result),
        "Pressupostos": _assumptions_rows(result),
        "ANOVA": _anova_rows(result),
        "Pós-testes": _posthoc_rows(result),
        "Resumo": _summary_rows(result),
        "Auditoria": _audit_rows(result),
    }


def export_excel(result, path: str, project_meta: Dict = None) -> str:
    """Write an .xlsx (openpyxl) or a CSV bundle fallback. Returns the path used."""
    sheets = _sheets(result, project_meta)
    if HAVE_OPENPYXL:
        wb = openpyxl.Workbook()
        wb.remove(wb.active)
        for name, rows in sheets.items():
            ws = wb.create_sheet(title=name[:31])
            for row in rows:
                ws.append(row)
        wb.save(path)
        return path
    # Fallback: a directory of CSVs.
    base = os.path.splitext(path)[0] + "_csv"
    os.makedirs(base, exist_ok=True)
    for name, rows in sheets.items():
        with open(os.path.join(base, f"{name}.csv"), "w", newline="",
                  encoding="utf-8") as f:
            csv.writer(f).writerows(rows)
    return base


def summary_csv_string(result) -> str:
    buf = io.StringIO()
    csv.writer(buf).writerows(_summary_rows(result))
    return buf.getvalue()
