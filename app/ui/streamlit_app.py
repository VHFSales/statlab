"""StatLab Streamlit interface (FR-12, FR-14, spec 9, 84-87).

Sections: PROJETO, DADOS, DELINEAMENTO, DESCRITIVA, PRESSUPOSTOS, ANÁLISE,
PÓS-TESTES, GRÁFICOS, RELATÓRIO, EXPORTAR. Two modes: Quick (guided) and Advanced.

Run with:  streamlit run app/ui/streamlit_app.py

The statistical layer is fully independent of this UI; this module only renders the
results produced by app.core.orchestrator.
"""

from __future__ import annotations

import os
import sys

# make the project importable when run via `streamlit run`
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    import streamlit as st
except Exception as exc:  # pragma: no cover
    raise SystemExit(
        "streamlit não está instalado. Instale com `pip install streamlit` e "
        "execute `streamlit run app/ui/streamlit_app.py`.\n" + str(exc)
    )

from app.core.orchestrator import (AnalysisOptions, analyze_batch, analyze_raw,
                                   analyze_summary)
from data.importer import import_text
from statistics.decision_engine import DesignSpec
from statistics.formatting import format_number, format_p
from reports.excel_export import export_excel, summary_csv_string
from reports.pdf_report import build_html_report

HELP = {
    "Média": "Soma dos valores dividida por n.",
    "DP": "Desvio padrão amostral (ddof=1): dispersão em torno da média.",
    "EP": "Erro padrão da média = DP / √n.",
    "IC": "Intervalo de confiança para a média (distribuição t, df = n−1).",
    "F": "Razão entre variabilidade entre grupos e dentro dos grupos.",
    "ANOVA": "Teste GLOBAL: existe evidência de diferença entre as médias? "
             "Não diz quais grupos diferem.",
    "Welch": "ANOVA robusta que não assume variâncias iguais.",
    "Tukey": "Comparações par a par controlando o erro familiar (FWER).",
    "Games-Howell": "Comparações par a par para variâncias/tamanhos desiguais.",
    "η²": "Proporção da variância total explicada pelos grupos (viesado para cima).",
    "ω²": "Estimador menos viesado do tamanho de efeito.",
    "CLD": "Letras de agrupamento: grupos que compartilham uma letra não diferem "
           "significativamente. Não é um ranking.",
}


def _init_state():
    st.session_state.setdefault("raw", None)
    st.session_state.setdefault("summary", None)   # {label: {mean, sd, n}}
    st.session_state.setdefault("data_kind", "RAW")  # "RAW" | "SUMMARY"
    st.session_state.setdefault("result", None)
    st.session_state.setdefault("batch", None)       # {var: raw_dict}
    st.session_state.setdefault("batch_out", None)
    st.session_state.setdefault("project", {"Nome": "", "Pesquisador": "",
                                            "Laboratório": "", "Descrição": ""})


def main():
    st.set_page_config(page_title="StatLab", layout="wide")
    _init_state()
    st.title("StatLab — Plataforma de Análise Estatística Científica")
    st.caption("Comparação de grupos independentes: ANOVA · Welch · Tukey · "
               "Tukey-Kramer · Games-Howell · CLD")

    mode = st.sidebar.radio("Modo", ["Rápido", "Avançado"])
    section = st.sidebar.radio("Seção", [
        "PROJETO", "DADOS", "DELINEAMENTO", "DESCRITIVA", "PRESSUPOSTOS",
        "ANÁLISE", "PÓS-TESTES", "GRÁFICOS", "LOTE", "RELATÓRIO", "EXPORTAR"])

    with st.sidebar.expander("Glossário (?)"):
        for k, v in HELP.items():
            st.markdown(f"**{k}** — {v}")

    if section == "PROJETO":
        _section_project()
    elif section == "DADOS":
        _section_data()
    elif section == "DELINEAMENTO":
        _section_design(mode)
    elif section == "DESCRITIVA":
        _section_descriptive()
    elif section == "PRESSUPOSTOS":
        _section_assumptions()
    elif section == "ANÁLISE":
        _section_analysis(mode)
    elif section == "PÓS-TESTES":
        _section_posthoc()
    elif section == "GRÁFICOS":
        _section_plots()
    elif section == "LOTE":
        _section_batch(mode)
    elif section == "RELATÓRIO":
        _section_report()
    elif section == "EXPORTAR":
        _section_export()


def _section_project():
    st.header("Projeto")
    p = st.session_state["project"]
    p["Nome"] = st.text_input("Nome do projeto", p["Nome"])
    p["Pesquisador"] = st.text_input("Pesquisador", p["Pesquisador"])
    p["Laboratório"] = st.text_input("Grupo / Laboratório", p["Laboratório"])
    p["Descrição"] = st.text_area("Descrição / observações", p["Descrição"])
    st.info("Metadados são livres (campo | valor) e NÃO alteram a análise "
            "estatística, a menos que você os transforme explicitamente em fatores.")


def _parse_summary(text: str):
    """Parse 'Grupo | Média | DP | n' rows (comma or tab separated)."""
    out = {}
    for line in text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        parts = [p.strip() for p in (line.split("\t") if "\t" in line
                                     else line.split(","))]
        if len(parts) < 3:
            continue
        lab = parts[0]
        # skip a header row
        try:
            mean = float(parts[1]); sd = float(parts[2])
        except ValueError:
            continue
        n = int(float(parts[3])) if len(parts) >= 4 and parts[3] else None
        entry = {"mean": mean, "sd": sd}
        if n is not None:
            entry["n"] = n
        out[lab] = entry
    return out


def _section_data():
    st.header("Dados")
    kind = st.radio("Tipo de dados", ["Dados brutos (recomendado)",
                                      "Estatísticas resumidas (Média, DP, n)"])
    if kind.startswith("Dados brutos"):
        st.session_state["data_kind"] = "RAW"
        st.markdown("Cole os dados do Excel — formato **largo** (uma coluna por "
                    "grupo) ou **longo** (`Grupo | Valor`). Células vazias nunca "
                    "viram zero.")
        text = st.text_area("Colar dados", height=200,
                            placeholder="A\tB\tC\n10.2\t13.5\t14.9\n...")
        fmt = st.selectbox("Formato", ["auto-detectar", "largo", "longo"])
        if st.button("Carregar dados brutos") and text.strip():
            fmt_arg = {"auto-detectar": None, "largo": "wide", "longo": "long"}[fmt]
            raw, used = import_text(text, fmt_arg)
            st.session_state["raw"] = raw
            st.session_state["summary"] = None
            st.session_state["result"] = None
            st.success(f"Formato usado: {used}. Grupos: {', '.join(raw.keys())}")
        if st.session_state.get("raw"):
            st.subheader("Prévia")
            st.write({k: v for k, v in st.session_state["raw"].items()})
    else:
        st.session_state["data_kind"] = "SUMMARY"
        st.markdown("Uma linha por grupo: `Grupo, Média, DP, n`. **Sem o n, ANOVA/"
                    "Tukey não podem ser realizados.** Diagnósticos que exigem dados "
                    "brutos (resíduos, Q-Q, Shapiro, outliers) não são possíveis.")
        text = st.text_area("Colar estatísticas resumidas", height=160,
                            placeholder="A, 10.54, 1.21, 5\nB, 13.72, 0.84, 5\n"
                                        "C, 15.19, 1.03, 6")
        if st.button("Carregar dados resumidos") and text.strip():
            summ = _parse_summary(text)
            st.session_state["summary"] = summ
            st.session_state["raw"] = None
            st.session_state["result"] = None
            missing_n = [l for l, s in summ.items() if "n" not in s]
            if missing_n:
                st.error("Os dados disponíveis são insuficientes para realizar "
                         "ANOVA/Tukey. Informe o tamanho amostral (n) de cada "
                         f"grupo. Faltando n em: {', '.join(missing_n)}.")
            else:
                st.success(f"Grupos: {', '.join(summ.keys())}")
        if st.session_state.get("summary"):
            st.subheader("Prévia")
            st.write(st.session_state["summary"])


def _section_design(mode):
    st.header("Delineamento")
    st.markdown("Antes de qualquer teste, confirme a estrutura experimental.")
    st.session_state.setdefault("design", {})
    d = st.session_state["design"]
    d["n_factors"] = st.number_input("Quantos fatores?", 1, 10, 1)
    d["independent_groups"] = st.checkbox("Os grupos são independentes?", True)
    d["repeated_measures"] = st.checkbox("Há medidas repetidas?", False)
    d["paired"] = st.checkbox("Há dados pareados?", False)
    d["blocks"] = st.checkbox("Há blocos?", False)
    d["multiple_obs_per_unit"] = st.checkbox(
        "Há várias medições da mesma unidade (replicatas técnicas)?", False)
    d["independent_units_asserted"] = st.checkbox(
        "As observações representam unidades experimentais independentes?", True)
    st.warning("A independência depende do delineamento e não pode ser confirmada "
               "apenas pelos valores numéricos. Pseudorreplicação pode invalidar a "
               "inferência.")


def _build_design():
    d = st.session_state.get("design", {})
    return DesignSpec(
        n_factors=int(d.get("n_factors", 1)),
        independent_groups=d.get("independent_groups", True),
        repeated_measures=d.get("repeated_measures", False),
        paired=d.get("paired", False),
        blocks=d.get("blocks", False),
        multiple_obs_per_unit=d.get("multiple_obs_per_unit", False),
        independent_units_asserted=d.get("independent_units_asserted", True),
    )


def _run(mode, options):
    kind = st.session_state.get("data_kind", "RAW")
    design = _build_design()
    if kind == "SUMMARY":
        summ = st.session_state.get("summary")
        if not summ:
            st.error("Carregue os dados resumidos primeiro (seção DADOS).")
            return None
        res = analyze_summary(summ, design, options)
        st.session_state["last_data"] = summ
    else:
        raw = st.session_state.get("raw")
        if not raw:
            st.error("Carregue os dados primeiro (seção DADOS).")
            return None
        res = analyze_raw(raw, design, options)
        st.session_state["last_data"] = raw
    st.session_state["result"] = res
    st.session_state["last_options"] = options
    st.session_state["last_design"] = design
    st.session_state["last_kind"] = kind
    return res


def _section_descriptive():
    st.header("Descritiva")
    res = st.session_state.get("result")
    if not res:
        st.info("Execute a análise (seção ANÁLISE) para ver a descritiva completa.")
        return
    _show_descriptive(res)


def _show_descriptive(res):
    import pandas as pd  # streamlit ships pandas
    rows = [{"Grupo": d["label"], "n": d["n"], "Ausentes": d["n_missing"],
             "Média": d["mean"], "Mediana": d["median"], "DP": d["sd"],
             "EP": d["se"], "IC inf": d["ci_low"], "IC sup": d["ci_high"],
             "Mín": d["minimum"], "Máx": d["maximum"], "Q1": d["q1"],
             "Q3": d["q3"], "IQR": d["iqr"], "CV": d["cv"]}
            for d in res.descriptive]
    st.dataframe(pd.DataFrame(rows))


def _section_assumptions():
    st.header("Pressupostos / Diagnósticos")
    res = st.session_state.get("result")
    if not res or not res.diagnostics:
        st.info("Execute a análise para ver os diagnósticos.")
        return
    dg = res.diagnostics
    if dg.get("levene"):
        st.write("**Levene (centrado na média):** F =",
                 format_number(dg["levene"]["statistic"], 4),
                 " p =", format_p(dg["levene"]["p"]))
    if dg.get("brown_forsythe"):
        st.write("**Brown-Forsythe (centrado na mediana):** F =",
                 format_number(dg["brown_forsythe"]["statistic"], 4),
                 " p =", format_p(dg["brown_forsythe"]["p"]))
    st.write("**Razão de variâncias (máx/mín):**",
             format_number(dg.get("variance_ratio", float('nan')), 3))
    sh = dg.get("shapiro_residuals")
    if sh:
        st.write("**Shapiro-Wilk (resíduos):** W =",
                 format_number(sh["statistic"], 4), " p =", format_p(sh["p"]),
                 sh.get("note", ""))
    st.warning(dg.get("independence_note", ""))
    st.caption("Nenhum teste de pressuposto é usado como regra absoluta. Avalie em "
               "conjunto com Q-Q plot, outliers, balanceamento e delineamento.")


def _section_analysis(mode):
    st.header("Análise")
    alpha = st.number_input("α", 0.0001, 0.5, 0.05, 0.01)
    ci = st.selectbox("Nível de IC", [0.90, 0.95, 0.99], index=1)
    decimals = st.slider("Casas decimais (exibição)", 2, 8, 4)
    opts = AnalysisOptions(alpha=alpha, ci_level=ci, decimals=decimals,
                           mode="advanced" if mode == "Avançado" else "quick")
    if mode == "Avançado":
        mo = st.selectbox("Método global (override)",
                          ["automático", "ANOVA clássica", "Welch"])
        opts.method_override = {"automático": None, "ANOVA clássica": "anova",
                                "Welch": "welch"}[mo]
        po = st.selectbox("Pós-teste (override)",
                          ["automático", "Tukey/Tukey-Kramer", "Games-Howell"])
        opts.posthoc_override = {"automático": None,
                                 "Tukey/Tukey-Kramer": "tukey",
                                 "Games-Howell": "games_howell"}[po]
        opts.force_posthoc = st.checkbox(
            "Executar pós-teste mesmo se o teste global não for significativo", False)

    if st.button("Analisar"):
        res = _run(mode, opts)
        if res:
            _show_result_summary(res)


def _show_result_summary(res):
    if res.refusals:
        for r in res.refusals:
            st.error(r)
        return
    st.subheader("RESULTADO")
    if res.omnibus_kind == "anova":
        o = res.omnibus
        st.markdown(f"**Método global:** ANOVA de uma via  \n"
                    f"F({int(o['df_between'])},{int(o['df_within'])}) = "
                    f"{format_number(o['f'], res.__dict__.get('decimals',4) if False else 4)}"
                    f"  ·  p {_p(o['p'])}  ·  α = {res.alpha}")
        if res.effect_sizes:
            st.markdown(f"ω² = {format_number(res.effect_sizes['omega_squared'],4)} "
                        f"· η² = {format_number(res.effect_sizes['eta_squared'],4)}")
    elif res.omnibus_kind == "welch":
        o = res.omnibus
        st.markdown(f"**Método global:** ANOVA de Welch  \n"
                    f"F({int(o['df1'])}, {format_number(o['df2'],2)}) = "
                    f"{format_number(o['statistic'],4)} · p {_p(o['p'])} · α = {res.alpha}")
    elif res.ttest:
        t = res.ttest
        st.markdown(f"**Método (2 grupos):** {t['method']}  \n"
                    f"t({format_number(t['df'], 2)}) = "
                    f"{format_number(t['statistic'], 4)} · p {_p(t['p'])} · "
                    f"α = {res.alpha}  \n"
                    f"Diferença ({t['group1']} − {t['group2']}) = "
                    f"{format_number(t['diff'], 4)} · "
                    f"IC{int(t['ci_level']*100)}% = "
                    f"[{format_number(t['ci_low'],4)}, {format_number(t['ci_high'],4)}] · "
                    f"d de Cohen = {format_number(t['cohens_d'], 4)}")
    if res.summary_based:
        st.caption("Análise realizada a partir de estatísticas resumidas.")
    st.info(res.interpretation.get("conclusion", ""))

    for w in res.warnings:
        st.warning(w)

    _show_descriptive_with_letters(res)

    with st.expander("Por que este teste foi escolhido?"):
        for r in res.recommendation.get("reasons", []):
            st.write("•", r)
    with st.expander("Detalhes do cálculo (auditoria)"):
        st.json({"analysis_id": res.analysis_id, "data_hash": res.data_hash,
                 "omnibus": res.omnibus, "effect_sizes": res.effect_sizes,
                 "diagnostics": res.diagnostics})


def _show_descriptive_with_letters(res):
    import pandas as pd
    letters = (res.cld or {}).get("display", {})
    rows = [{"Grupo": d["label"], "n": d["n"], "Média": d["mean"], "DP": d["sd"],
             "EP": d["se"], "IC inf": d["ci_low"], "IC sup": d["ci_high"],
             "Letras": letters.get(d["label"], "")} for d in res.descriptive]
    st.dataframe(pd.DataFrame(rows))
    if letters:
        st.caption("Letras são símbolos de agrupamento (não um ranking). Grupos que "
                   "compartilham uma letra não diferem significativamente.")


def _section_posthoc():
    st.header("Pós-testes")
    res = st.session_state.get("result")
    if res and res.ttest:
        t = res.ttest
        st.info("Com dois grupos, a comparação é o próprio teste t (não há "
                "pós-teste par a par como Tukey).")
        import pandas as pd
        st.dataframe(pd.DataFrame([{
            "Método": t["method"], "Grupo 1": t["group1"], "Grupo 2": t["group2"],
            "Diferença": t["diff"], "t": t["statistic"], "df": t["df"],
            "p": t["p"], "IC inf": t["ci_low"], "IC sup": t["ci_high"],
            "d de Cohen": t["cohens_d"],
            "Signif.": "Sim" if t["significant"] else "Não"}]))
        return
    if not res or not res.posthoc:
        st.info("Nenhum pós-teste disponível. Execute a análise; note que no modo "
                "rápido o pós-teste não roda se o teste global não for significativo.")
        return
    import pandas as pd
    st.write(f"**Método:** {res.posthoc['method']}")
    rows = [{"Grupo 1": c["group1"], "Grupo 2": c["group2"],
             "Diferença": c["diff"], "IC inf": c["ci_low"], "IC sup": c["ci_high"],
             "p ajustado": c["p_adjusted"], "Signif.": "Sim" if c["significant"]
             else "Não"} for c in res.posthoc["comparisons"]]
    st.dataframe(pd.DataFrame(rows))
    st.write(res.interpretation.get("posthoc", ""))


def _section_plots():
    st.header("Gráficos")
    res = st.session_state.get("result")
    if not res:
        st.info("Execute a análise primeiro.")
        return
    try:
        from plots import scientific_plots as sp
    except Exception:
        st.error("matplotlib indisponível neste ambiente.")
        return
    raw = st.session_state.get("raw")
    letters = (res.cld or {}).get("display", {})
    options = ["Média ± DP", "Média ± EP", "Média + IC"]
    if raw:  # boxplot needs individual values
        options = ["Boxplot"] + options
    else:
        st.caption("Boxplot indisponível: análise a partir de estatísticas "
                   "resumidas (sem valores individuais).")
    kind = st.selectbox("Tipo", options)
    try:
        if kind == "Boxplot":
            fig = sp.boxplot(raw, letters=letters)
        else:
            err = {"Média ± DP": "sd", "Média ± EP": "se", "Média + IC": "ci"}[kind]
            fig = sp.mean_error_plot(res.descriptive, error=err, letters=letters)
        st.pyplot(fig)
    except Exception as exc:
        st.error(str(exc))


def _section_batch(mode):
    st.header("Análise em lote (múltiplas variáveis)")
    st.markdown("Cole uma tabela com uma coluna de **Grupo** seguida de várias "
                "colunas de variáveis: `Grupo | Var1 | Var2 | ... | VarN`. Cada "
                "variável é analisada separadamente.")
    text = st.text_area("Colar tabela (largo, formato longo por grupo)", height=180,
                        placeholder="Grupo\tPeso\tAltura\tpH\nA\t10.2\t1.5\t7.1\n"
                                    "A\t10.5\t1.6\t7.0\nB\t13.1\t1.9\t6.8\n...")
    alpha = st.number_input("α (lote)", 0.0001, 0.5, 0.05, 0.01, key="batch_alpha")
    fdr = st.selectbox("Correção de multiplicidade entre variáveis (opcional)",
                       ["Nenhuma (não aplicar)", "Holm (FWER)",
                        "Benjamini-Hochberg (FDR)", "Bonferroni (FWER)"])
    fdr_arg = {"Nenhuma (não aplicar)": None, "Holm (FWER)": "holm",
               "Benjamini-Hochberg (FDR)": "bh", "Bonferroni (FWER)": "bonferroni"}[fdr]

    if st.button("Analisar em lote") and text.strip():
        variables = _parse_batch_table(text)
        if not variables:
            st.error("Não foi possível interpretar a tabela. Verifique o formato.")
            return
        opts = AnalysisOptions(alpha=alpha,
                               mode="advanced" if mode == "Avançado" else "quick")
        out = analyze_batch(variables, _build_design(), opts, fdr_method=fdr_arg)
        st.session_state["batch_out"] = out

    out = st.session_state.get("batch_out")
    if not out:
        return
    cons = out["consolidated"]
    st.write(f"Variáveis analisadas: **{cons['n_variables']}** · "
             f"com teste global: **{cons['n_tested']}**")
    for w in cons["warnings"]:
        st.warning(w)

    import pandas as pd
    rows = []
    fdr_adj = None
    if cons.get("fdr"):
        fdr_adj = dict(zip(cons["fdr"]["labels"], cons["fdr"]["p_adjusted"]))
    for name, res in out["results"].items():
        if res.refusals:
            rows.append({"Variável": name, "Método": "—",
                         "p (global)": None, "p ajustado": None,
                         "Situação": "recusada: " + res.refusals[0][:40]})
            continue
        p = (res.omnibus or {}).get("p") if res.omnibus else (
            res.ttest["p"] if res.ttest else None)
        method = (res.omnibus_kind or ("t-test" if res.ttest else "—"))
        rows.append({"Variável": name, "Método": method, "p (global)": p,
                     "p ajustado": (fdr_adj or {}).get(name),
                     "CLD": " ".join(f"{k}:{v}" for k, v in
                                     (res.cld or {}).get("display", {}).items())})
    st.dataframe(pd.DataFrame(rows))
    if fdr_adj is not None:
        st.caption(f"Correção aplicada: {cons['fdr']['method']}. As colunas 'p "
                   "ajustado' controlam a multiplicidade ENTRE variáveis.")


def _parse_batch_table(text: str):
    """Parse 'Grupo, Var1, Var2, ...' rows into {var_name: {group: [values]}}."""
    lines = [l for l in text.strip().splitlines() if l.strip()]
    if len(lines) < 2:
        return {}
    def split(line):
        return [c.strip() for c in (line.split("\t") if "\t" in line
                                    else line.split(","))]
    header = split(lines[0])
    var_names = header[1:]
    variables = {v: {} for v in var_names}
    for line in lines[1:]:
        parts = split(line)
        if len(parts) < 2:
            continue
        group = parts[0]
        for i, v in enumerate(var_names, start=1):
            cell = parts[i] if i < len(parts) else ""
            try:
                val = float(cell) if cell != "" else None
            except ValueError:
                val = None
            variables[v].setdefault(group, []).append(val)
    return variables


def _section_report():
    st.header("Relatório")
    res = st.session_state.get("result")
    if not res:
        st.info("Execute a análise primeiro.")
        return
    html = build_html_report(res, project_meta=st.session_state["project"])
    st.download_button("Baixar relatório HTML", html, file_name="statlab_report.html",
                       mime="text/html")
    st.components.v1.html(html, height=600, scrolling=True)


def _section_export():
    st.header("Exportar")
    res = st.session_state.get("result")
    if not res:
        st.info("Execute a análise primeiro.")
        return
    st.download_button("Baixar Resumo (CSV)", summary_csv_string(res),
                       file_name="resumo.csv", mime="text/csv")
    if st.button("Gerar Excel (.xlsx)"):
        path = export_excel(res, "statlab_export.xlsx",
                            project_meta=st.session_state["project"])
        st.success(f"Exportado para: {path}")

    st.subheader("Reprodutibilidade")
    st.caption("A configuração de reprodução contém os dados, α, método, "
               "delineamento e versões — suficiente para refazer a análise de forma "
               "idêntica.")
    import json as _json
    from persistence.result_store import build_repro_config, result_to_dict
    cfg = build_repro_config(
        st.session_state.get("last_data", {}),
        st.session_state.get("last_kind", res.data_kind),
        st.session_state.get("last_design", _build_design()),
        st.session_state.get("last_options", AnalysisOptions(alpha=res.alpha)),
        res)
    st.download_button("Baixar configuração de reprodução (JSON)",
                       _json.dumps(cfg, ensure_ascii=False, indent=2),
                       file_name="statlab_repro.json", mime="application/json")
    st.download_button("Baixar resultado completo (JSON)",
                       _json.dumps(result_to_dict(res), ensure_ascii=False,
                                   indent=2),
                       file_name="statlab_result.json", mime="application/json")


def _p(p):
    s = format_p(p)
    return s if s.startswith("<") else f"= {s}"


if __name__ == "__main__":
    main()
