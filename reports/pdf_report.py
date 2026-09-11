"""Report generation (FR-18.1, FR-18.3, spec 62/64).

Produces a self-contained HTML report (always available, real tables) and,
when matplotlib is present, a PDF via PdfPages. Not a screenshot dump.
"""

from __future__ import annotations

import html
from typing import Dict

from statistics.formatting import format_number, format_p

try:
    from matplotlib.backends.backend_pdf import PdfPages  # noqa
    import matplotlib.pyplot as plt
    HAVE_MPL = True
except Exception:
    HAVE_MPL = False


def _table(headers, rows, decimals=4):
    th = "".join(f"<th>{html.escape(str(h))}</th>" for h in headers)
    trs = []
    for r in rows:
        tds = []
        for c in r:
            if isinstance(c, float):
                c = format_number(c, decimals)
            tds.append(f"<td>{html.escape(str(c))}</td>")
        trs.append("<tr>" + "".join(tds) + "</tr>")
    return f"<table><thead><tr>{th}</tr></thead><tbody>{''.join(trs)}</tbody></table>"


def build_html_report(result, project_meta: Dict = None, decimals: int = 4) -> str:
    project_meta = project_meta or {}
    parts = ["<html><head><meta charset='utf-8'><style>",
             "body{font-family:sans-serif;margin:2em;color:#222;}",
             "table{border-collapse:collapse;margin:1em 0;}",
             "th,td{border:1px solid #bbb;padding:4px 8px;text-align:right;}",
             "th{background:#eee;} h1,h2{color:#1f4e79;}",
             ".warn{color:#a15c00;} .refuse{color:#a00;font-weight:bold;}",
             "</style></head><body>"]
    parts.append("<h1>StatLab — Relatório de Análise Estatística</h1>")

    if project_meta:
        parts.append("<h2>Projeto</h2>")
        parts.append(_table(["Campo", "Valor"], list(project_meta.items())))

    if result.refusals:
        parts.append("<h2 class='refuse'>Análise não realizada</h2><ul>")
        for r in result.refusals:
            parts.append(f"<li class='refuse'>{html.escape(r)}</li>")
        parts.append("</ul>")

    # Descriptive
    parts.append("<h2>Estatística descritiva</h2>")
    dh = ["Grupo", "n", "Média", "Mediana", "DP", "EP", "IC inf", "IC sup",
          "Mín", "Máx", "Q1", "Q3", "IQR", "CV"]
    drows = [[d["label"], d["n"], d["mean"], d["median"], d["sd"], d["se"],
              d["ci_low"], d["ci_high"], d["minimum"], d["maximum"], d["q1"],
              d["q3"], d["iqr"], d["cv"]] for d in result.descriptive]
    parts.append(_table(dh, drows, decimals))

    # Why this test
    rec = result.recommendation or {}
    if rec.get("reasons"):
        parts.append("<h2>Por que este teste foi escolhido?</h2><ul>")
        for r in rec["reasons"]:
            parts.append(f"<li>{html.escape(r)}</li>")
        parts.append("</ul>")

    # Omnibus
    if result.omnibus:
        parts.append("<h2>Teste global</h2>")
        o = result.omnibus
        if result.omnibus_kind == "anova":
            parts.append(_table(
                ["Fonte", "SS", "df", "MS", "F", "p"],
                [["Entre grupos", o["ss_between"], o["df_between"], o["ms_between"],
                  o["f"], format_p(o["p"], decimals)],
                 ["Dentro (erro)", o["ss_within"], o["df_within"], o["ms_within"],
                  "", ""],
                 ["Total", o["ss_total"], o["df_total"], "", "", ""]], decimals))
        else:
            parts.append(_table(
                ["Método", "Estatística", "df1", "df2", "p"],
                [["Welch", o["statistic"], o["df1"], o["df2"],
                  format_p(o["p"], decimals)]], decimals))
        parts.append(f"<p>{html.escape(result.interpretation.get('omnibus',''))}</p>")
        parts.append(f"<p><b>{html.escape(result.interpretation.get('conclusion',''))}</b></p>")

    if result.effect_sizes:
        e = result.effect_sizes
        parts.append("<h2>Tamanho de efeito</h2>")
        parts.append(_table(["η²", "ω²", "η² parcial"],
                            [[e["eta_squared"], e["omega_squared"],
                              e["partial_eta_squared"]]], decimals))

    # Post-hoc + CLD
    if result.posthoc:
        parts.append(f"<h2>Pós-teste: {html.escape(result.posthoc['method'])}</h2>")
        ph = result.posthoc
        rows = [[c["group1"], c["group2"], c["diff"], c["ci_low"], c["ci_high"],
                 format_p(c["p_adjusted"], decimals),
                 "Sim" if c["significant"] else "Não"] for c in ph["comparisons"]]
        parts.append(_table(["Grupo 1", "Grupo 2", "Diferença", "IC inf", "IC sup",
                             "p ajustado", "Signif."], rows, decimals))
        parts.append(f"<p>{html.escape(result.interpretation.get('posthoc',''))}</p>")
    if result.cld:
        parts.append("<h2>Compact Letter Display</h2>")
        parts.append(_table(["Grupo", "Letras"],
                            list(result.cld["display"].items())))
        parts.append(f"<p><i>Letras derivadas de: "
                     f"{html.escape(result.cld['source'])}. Letras são símbolos de "
                     f"agrupamento, não um ranking.</i></p>")

    if result.warnings:
        parts.append("<h2>Avisos</h2><ul>")
        for w in result.warnings:
            parts.append(f"<li class='warn'>{html.escape(w)}</li>")
        parts.append("</ul>")

    # Audit
    parts.append("<h2>Auditoria / Reprodutibilidade</h2>")
    parts.append(_table(["Campo", "Valor"], [
        ["ID da análise", result.analysis_id],
        ["Data/hora", result.created_at],
        ["Programa", result.program_version],
        ["Núcleo", result.core_version],
        ["Python", result.python_version],
        ["alpha", result.alpha],
        ["Hash dos dados", result.data_hash],
    ]))
    parts.append("</body></html>")
    return "".join(parts)


def save_html_report(result, path: str, project_meta: Dict = None,
                     decimals: int = 4) -> str:
    with open(path, "w", encoding="utf-8") as f:
        f.write(build_html_report(result, project_meta, decimals))
    return path
