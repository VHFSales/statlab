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
        "ANÁLISE", "PÓS-TESTES", "OUTLIERS", "GRÁFICOS", "FATORIAL", "PAREADO",
        "MEDIDAS REPETIDAS", "CORRELAÇÃO", "LOTE", "RELATÓRIO", "EXPORTAR"])

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
    elif section == "OUTLIERS":
        _section_outliers()
    elif section == "GRÁFICOS":
        _section_plots()
    elif section == "FATORIAL":
        _section_two_way()
    elif section == "PAREADO":
        _section_paired(mode)
    elif section == "MEDIDAS REPETIDAS":
        _section_repeated_measures()
    elif section == "CORRELAÇÃO":
        _section_correlation()
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

    st.subheader("Salvar / reabrir projeto")
    st.caption("O projeto é salvo como um arquivo JSON contendo os metadados, os "
               "dados atuais, o delineamento e o último resultado — suficiente para "
               "reabrir e continuar.")
    import json as _json
    from app.core.ui_session import (build_workspace_dict,
                                     restore_from_workspace_dict)

    data = (st.session_state.get("summary")
            if st.session_state.get("data_kind") == "SUMMARY"
            else st.session_state.get("raw"))
    ws_dict = build_workspace_dict(
        project=p, data_kind=st.session_state.get("data_kind", "RAW"),
        data=data, design=st.session_state.get("design", {}),
        result=st.session_state.get("result"))
    st.download_button("Baixar projeto (.json)",
                       _json.dumps(ws_dict, ensure_ascii=False, indent=2),
                       file_name="statlab_projeto.json",
                       mime="application/json")

    up = st.file_uploader("Reabrir projeto (.json)", type=["json"])
    if up is not None and st.button("Carregar projeto"):
        try:
            loaded = restore_from_workspace_dict(_json.loads(up.read()))
            st.session_state["project"] = loaded["project"] or p
            st.session_state["data_kind"] = loaded["data_kind"]
            if loaded["data_kind"] == "SUMMARY":
                st.session_state["summary"] = loaded["data"]
                st.session_state["raw"] = None
            else:
                st.session_state["raw"] = loaded["data"]
                st.session_state["summary"] = None
            st.session_state["design"] = loaded["design"] or {}
            st.session_state["result"] = loaded["result"]
            st.success("Projeto carregado. Verifique as seções DADOS e ANÁLISE.")
        except Exception as exc:
            st.error(f"Falha ao carregar o projeto: {exc}")


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
        opts.nonparametric = st.checkbox(
            "Usar teste NÃO-PARAMÉTRICO (Kruskal-Wallis → Dunn)", False)
        if opts.nonparametric:
            st.caption("A escolha do método não-paramétrico é sua e deliberada. O "
                       "sistema NUNCA a faz automaticamente a partir de um teste de "
                       "normalidade. Kruskal-Wallis compara distribuições/postos, "
                       "não médias.")
            adj = st.selectbox("Ajuste de multiplicidade (Dunn)",
                               ["Holm", "Benjamini-Hochberg", "Bonferroni", "Nenhum"])
            opts.dunn_adjust = {"Holm": "holm",
                                "Benjamini-Hochberg": "bh",
                                "Bonferroni": "bonferroni", "Nenhum": "none"}[adj]

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
    elif res.omnibus_kind == "mann_whitney" and res.mann_whitney:
        mw = res.mann_whitney
        st.markdown(f"**Método (2 grupos):** Mann-Whitney U (não-paramétrico)  \n"
                    f"U = {format_number(mw['u_statistic'], 4)} · "
                    f"z = {format_number(mw['z'], 4)} · p {_p(mw['p'])} · "
                    f"α = {res.alpha}")
        st.caption("Mann-Whitney compara distribuições/postos entre dois grupos, "
                   "não médias.")
    elif res.omnibus_kind == "kruskal" and res.nonparametric_omnibus:
        kw = res.nonparametric_omnibus
        st.markdown(f"**Método global:** Kruskal-Wallis (não-paramétrico)  \n"
                    f"H({kw['df']}) = {format_number(kw['statistic'], 4)} · "
                    f"p {_p(kw['p'])} · α = {res.alpha}  \n"
                    f"Correção de empates = {format_number(kw['tie_correction'], 4)}")
        st.caption("Kruskal-Wallis compara distribuições/postos, não médias.")
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
    is_dunn = res.omnibus_kind == "kruskal"
    diff_label = "Dif. posto médio" if is_dunn else "Diferença"
    if is_dunn:
        rows = [{"Grupo 1": c["group1"], "Grupo 2": c["group2"],
                 "Posto médio 1": c["mean1"], "Posto médio 2": c["mean2"],
                 diff_label: c["diff"], "z": c["statistic"],
                 "p ajustado": c["p_adjusted"],
                 "Signif.": "Sim" if c["significant"] else "Não"}
                for c in res.posthoc["comparisons"]]
        st.caption("Dunn compara postos médios (não médias); não há IC de diferença "
                   "de médias.")
    else:
        rows = [{"Grupo 1": c["group1"], "Grupo 2": c["group2"],
                 diff_label: c["diff"], "IC inf": c["ci_low"],
                 "IC sup": c["ci_high"], "p ajustado": c["p_adjusted"],
                 "Signif.": "Sim" if c["significant"] else "Não"}
                for c in res.posthoc["comparisons"]]
    st.dataframe(pd.DataFrame(rows))
    st.write(res.interpretation.get("posthoc", ""))


def _section_outliers():
    st.header("Diagnóstico de outliers")
    raw = st.session_state.get("raw")
    if st.session_state.get("data_kind") == "SUMMARY" or not raw:
        st.info("O diagnóstico de outliers exige dados brutos (valores individuais). "
                "A partir de estatísticas resumidas não é possível.")
        return
    st.warning("Outliers NUNCA são excluídos automaticamente. O diagnóstico apenas "
               "sinaliza candidatos; a exclusão exige ação explícita e é registrada.")
    from app.core.outlier_flow import compare_with_exclusions, diagnose_outliers

    method = st.selectbox("Método de diagnóstico", ["IQR", "Grubbs"])
    method_arg = "grubbs" if method == "Grubbs" else "iqr"
    k = 1.5
    if method_arg == "iqr":
        k = st.slider("Fator k da cerca IQR", 1.0, 3.0, 1.5, 0.5)
    flagged = diagnose_outliers(raw, method=method_arg, k=k,
                                alpha=st.session_state.get("batch_alpha", 0.05))

    import pandas as pd
    rows = []
    for group, items in flagged.items():
        for it in items:
            rows.append({"Grupo": group, "Valor": it["value"],
                         "Critério": it["criterion"],
                         "Limite inf": it.get("low"), "Limite sup": it.get("high"),
                         "Estatística": it.get("statistic")})
    if not rows:
        st.success("Nenhum valor sinalizado como candidato a outlier.")
        return
    st.dataframe(pd.DataFrame(rows))

    st.subheader("Exclusão registrada (opcional)")
    st.caption("Selecione candidatos a excluir. A análise será refeita e comparada "
               "com a original; a exclusão fica registrada (valor/grupo/motivo/"
               "método/data).")
    choices = [f"{r['Grupo']} = {r['Valor']}" for r in rows]
    selected = st.multiselect("Candidatos a excluir", choices)
    reason = st.text_input("Motivo da exclusão (obrigatório)")
    if st.button("Excluir e comparar") and selected and reason.strip():
        targets = []
        for sel in selected:
            g, v = sel.split(" = ")
            targets.append({"group": g, "value": float(v)})
        comp = compare_with_exclusions(raw, _build_design(), targets, reason,
                                       method, st.session_state.get("last_options"))
        st.session_state["outlier_comparison"] = comp
        st.success(f"{len(comp.exclusions)} observação(ões) excluída(s) e registrada(s).")

    comp = st.session_state.get("outlier_comparison")
    if comp:
        st.subheader("Comparação: original vs. após exclusão")
        _show_comparison(comp)


def _show_comparison(comp):
    import pandas as pd

    def summarize(res_dict):
        o = res_dict.get("omnibus") or {}
        kind = res_dict.get("omnibus_kind")
        if kind == "anova":
            stat = f"F = {format_number(o.get('f'), 4)}"
        elif kind == "welch":
            stat = f"F* = {format_number(o.get('statistic'), 4)}"
        elif res_dict.get("ttest"):
            stat = f"t = {format_number(res_dict['ttest']['statistic'], 4)}"
            o = res_dict["ttest"]
        else:
            stat = "—"
        cld = (res_dict.get("cld") or {}).get("display", {})
        return {"Método": kind or ("t-test" if res_dict.get("ttest") else "—"),
                "Estatística": stat, "p": format_p(o.get("p", float("nan"))),
                "CLD": " ".join(f"{k}:{v}" for k, v in cld.items())}

    st.dataframe(pd.DataFrame([
        {"Análise": "Original", **summarize(comp.original)},
        {"Análise": "Após exclusão", **summarize(comp.after_exclusion)},
    ]))
    st.markdown("**Exclusões registradas:**")
    st.dataframe(pd.DataFrame(comp.exclusions))
    st.caption("A comparação é informativa. A decisão de excluir observações é do "
               "pesquisador e deve ser justificada cientificamente.")


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
    if raw:  # these need individual values
        options = ["Boxplot"] + options + ["Q-Q (resíduos)",
                                           "Resíduos vs. ajustados"]
    else:
        st.caption("Boxplot, Q-Q e resíduos indisponíveis: análise a partir de "
                   "estatísticas resumidas (sem valores individuais).")
    kind = st.selectbox("Tipo", options)
    try:
        if kind == "Boxplot":
            fig = sp.boxplot(raw, letters=letters)
        elif kind == "Q-Q (resíduos)":
            from statistics import assumptions
            from statistics.types import RawGroup
            groups = [RawGroup(g, v) for g, v in raw.items()]
            fig = sp.qq_plot(assumptions.qq_points(assumptions.residuals(groups)))
        elif kind == "Resíduos vs. ajustados":
            fig = sp.residuals_vs_fitted(raw)
        else:
            err = {"Média ± DP": "sd", "Média ± EP": "se", "Média + IC": "ci"}[kind]
            fig = sp.mean_error_plot(res.descriptive, error=err, letters=letters)
        st.pyplot(fig)
    except Exception as exc:
        st.error(str(exc))


def _section_correlation():
    st.header("Correlação (associação entre duas variáveis)")
    st.markdown("Cole **duas colunas alinhadas** (`Variável X | Variável Y`), uma "
                "medição de cada variável por unidade. **Correlação não implica "
                "causalidade.**")
    vx = st.text_input("Nome da Variável X", "X")
    vy = st.text_input("Nome da Variável Y", "Y")
    method = st.selectbox("Método", ["Pearson (linear)",
                                     "Spearman (monotônica, postos)"])
    method_arg = "spearman" if method.startswith("Spearman") else "pearson"
    text = st.text_area("Colar dados (X, Y)", height=200,
                        placeholder="X, Y\n10, 8.04\n8, 6.95\n13, 7.58\n...")
    alpha = st.number_input("α (correlação)", 0.0001, 0.5, 0.05, 0.01,
                            key="corr_alpha")
    if st.button("Calcular correlação") and text.strip():
        x, y = _parse_two_columns(text)
        if not x:
            st.error("Não foi possível interpretar os dados (esperado 2 colunas).")
            return
        from app.core.orchestrator import AnalysisOptions, analyze_correlation
        res = analyze_correlation(x, y, vx, vy, method_arg,
                                  AnalysisOptions(alpha=alpha))
        st.session_state["corr_result"] = res

    res = st.session_state.get("corr_result")
    if not res:
        return
    if res.refusals:
        for r in res.refusals:
            st.error(r)
        return
    for w in res.warnings:
        st.warning(w)
    st.subheader("RESULTADO")
    st.markdown(res.interpretation.get("primary", ""))
    st.info(res.interpretation.get("conclusion", ""))
    import pandas as pd
    c = res.result
    st.dataframe(pd.DataFrame([{
        "Método": c["method"], "r": c["r"], "n": c["n"], "t": c["statistic"],
        "df": c["df"], "p": c["p"], "IC inf": c["ci_low"], "IC sup": c["ci_high"],
        "Significativo": "Sim" if c["significant"] else "Não"}]))


def _section_repeated_measures():
    st.header("Medidas repetidas (Friedman → Nemenyi)")
    st.markdown("Para **3+ condições relacionadas medidas na mesma unidade** "
                "(delineamento de blocos completos). Cole uma tabela onde **cada "
                "linha é um sujeito/bloco** e **cada coluna é uma condição** "
                "(`Cond1 | Cond2 | Cond3 | ...`). Teste não-paramétrico deliberado.")
    text = st.text_area("Colar tabela (uma linha por bloco)", height=200,
                        placeholder="C1\tC2\tC3\n1\t2\t3\n2\t3\t4\n1\t3\t5\n...")
    alpha = st.number_input("α (Friedman)", 0.0001, 0.5, 0.05, 0.01, key="rm_alpha")
    if st.button("Analisar medidas repetidas") and text.strip():
        labels, blocks = _parse_block_matrix(text)
        if not blocks:
            st.error("Não foi possível interpretar a matriz de blocos.")
            return
        from app.core.orchestrator import (AnalysisOptions,
                                           analyze_repeated_measures)
        res = analyze_repeated_measures(blocks, labels, AnalysisOptions(alpha=alpha))
        st.session_state["rm_result"] = res

    res = st.session_state.get("rm_result")
    if not res:
        return
    if res.refusals:
        for r in res.refusals:
            st.error(r)
        return
    for w in res.warnings:
        st.warning(w)
    st.subheader("RESULTADO")
    st.markdown(res.interpretation.get("omnibus", ""))
    st.info(res.interpretation.get("conclusion", ""))
    import pandas as pd
    if res.omnibus:
        mr = res.omnibus["mean_ranks"]
        letters = (res.cld or {}).get("display", {})
        st.dataframe(pd.DataFrame([
            {"Condição": k, "Posto médio": v, "Letras": letters.get(k, "")}
            for k, v in mr.items()]))
    if res.posthoc:
        st.write(f"**Pós-teste:** {res.posthoc['method']}")
        st.dataframe(pd.DataFrame([
            {"Cond. 1": c["group1"], "Cond. 2": c["group2"],
             "Dif. posto médio": c["diff"], "q": c["statistic"],
             "p ajustado": c["p_adjusted"],
             "Signif.": "Sim" if c["significant"] else "Não"}
            for c in res.posthoc["comparisons"]]))
        st.write(res.interpretation.get("posthoc", ""))


def _parse_block_matrix(text: str):
    """Parse a block x condition matrix; returns (labels, list-of-rows)."""
    lines = [l for l in text.strip().splitlines() if l.strip()]
    if len(lines) < 2:
        return [], []

    def split(line):
        return [c.strip() for c in (line.split("\t") if "\t" in line
                                    else line.split(","))]

    first = split(lines[0])
    # header if the first row is non-numeric
    header_is_labels = False
    try:
        [float(x) for x in first]
    except ValueError:
        header_is_labels = True
    if header_is_labels:
        labels = first
        data_lines = lines[1:]
    else:
        labels = [f"C{i+1}" for i in range(len(first))]
        data_lines = lines
    blocks = []
    for line in data_lines:
        parts = split(line)
        row = []
        ok = True
        for p in parts:
            try:
                row.append(float(p))
            except ValueError:
                ok = False
                break
        if ok and row:
            blocks.append(row)
    return labels, blocks


def _section_paired(mode):
    st.header("Comparação pareada (dados dependentes)")
    st.markdown("Para **duas condições medidas na mesma unidade** (antes/depois, "
                "pares). Cole **duas colunas alinhadas par a par** "
                "(`Condição 1 | Condição 2`). Não trate dados pareados como grupos "
                "independentes.")
    c1 = st.text_input("Nome da Condição 1", "Antes")
    c2 = st.text_input("Nome da Condição 2", "Depois")
    text = st.text_area("Colar dois valores por linha (C1, C2)", height=200,
                        placeholder="Antes, Depois\n210, 200\n180, 170\n195, 188\n...")
    alpha = st.number_input("α (pareado)", 0.0001, 0.5, 0.05, 0.01, key="pair_alpha")
    nonparam = False
    if mode == "Avançado":
        nonparam = st.checkbox("Usar Wilcoxon signed-rank (não-paramétrico)", False)
        if nonparam:
            st.caption("Escolha não-paramétrica deliberada; o sistema não a faz "
                       "automaticamente a partir de um teste de normalidade.")
    if st.button("Analisar pareado") and text.strip():
        x1, x2 = _parse_two_columns(text)
        if not x1:
            st.error("Não foi possível interpretar os dados (esperado 2 colunas).")
            return
        from app.core.orchestrator import AnalysisOptions, analyze_paired
        opts = AnalysisOptions(alpha=alpha,
                               mode="advanced" if mode == "Avançado" else "quick",
                               nonparametric=nonparam)
        st.session_state["paired_result"] = analyze_paired(x1, x2, c1, c2, opts)

    res = st.session_state.get("paired_result")
    if not res:
        return
    if res.refusals:
        for r in res.refusals:
            st.error(r)
        return
    for w in res.warnings:
        st.warning(w)
    st.subheader("RESULTADO")
    st.markdown(res.interpretation.get("primary", ""))
    st.info(res.interpretation.get("conclusion", ""))
    import pandas as pd
    if res.parametric:
        p = res.parametric
        st.dataframe(pd.DataFrame([{
            "Pares (n)": p["n_pairs"], "Média das diferenças": p["mean_diff"],
            "DP dif.": p["sd_diff"], "t": p["statistic"], "df": p["df"],
            "p": p["p"], "IC inf": p["ci_low"], "IC sup": p["ci_high"],
            "Cohen dz": p["cohens_dz"]}]))
    if res.nonparametric:
        w = res.nonparametric
        st.dataframe(pd.DataFrame([{
            "Pares (n)": w["n_pairs"], "W": w["w_statistic"], "W+": w["w_plus"],
            "W-": w["w_minus"], "z": w["z"], "p": w["p"], "Zeros descartados":
            w["n_zeros"]}]))


def _parse_two_columns(text: str):
    """Parse two aligned numeric columns; returns (x1, x2) with None for blanks."""
    lines = [l for l in text.strip().splitlines() if l.strip()]

    def split(line):
        return [c.strip() for c in (line.split("\t") if "\t" in line
                                    else line.split(","))]

    start = 0
    if lines:
        first = split(lines[0])
        if len(first) >= 2:
            try:
                float(first[0]); float(first[1])
            except ValueError:
                start = 1  # header
    x1, x2 = [], []
    for line in lines[start:]:
        parts = split(line)
        if len(parts) < 2:
            continue

        def num(s):
            try:
                return float(s)
            except ValueError:
                return None
        x1.append(num(parts[0]))
        x2.append(num(parts[1]))
    return x1, x2


def _section_two_way():
    st.header("ANOVA de duas vias (fatorial)")
    st.markdown("Cole os dados no formato longo com **três colunas**: "
                "`Fator A | Fator B | Valor`. Delineamento **balanceado** "
                "(mesmo nº de repetições por célula) é exigido nesta versão.")
    fa = st.text_input("Nome do Fator A", "Fator A")
    fb = st.text_input("Nome do Fator B", "Fator B")
    text = st.text_area("Colar dados (A, B, Valor)", height=200,
                        placeholder="Dose, Material, Valor\n"
                                    "Baixa, X, 10.2\nBaixa, X, 10.5\n"
                                    "Baixa, Y, 12.1\nAlta, X, 9.8\n...")
    alpha = st.number_input("α (fatorial)", 0.0001, 0.5, 0.05, 0.01,
                            key="tw_alpha")
    if st.button("Analisar fatorial") and text.strip():
        cells = _parse_two_way(text)
        if not cells:
            st.error("Não foi possível interpretar a tabela (esperado A, B, Valor).")
            return
        from app.core.orchestrator import AnalysisOptions, analyze_two_way
        res = analyze_two_way(cells, fa, fb, AnalysisOptions(alpha=alpha))
        st.session_state["tw_result"] = res

    res = st.session_state.get("tw_result")
    if not res:
        return
    if res.refusals:
        for r in res.refusals:
            st.error(r)
        return
    import pandas as pd
    st.subheader("Tabela ANOVA (duas vias)")
    rows = []
    for e in res.effects:
        rows.append({
            "Fonte": e["name"], "SS": e["ss"], "df": e["df"],
            "MS": e["ms"] if e["ms"] == e["ms"] else None,
            "F": e["f"] if e["f"] == e["f"] else None,
            "p": format_p(e["p"]) if e["p"] == e["p"] else "",
            "η² parcial": e["partial_eta_sq"] if e["partial_eta_sq"] ==
            e["partial_eta_sq"] else None})
    st.dataframe(pd.DataFrame(rows))
    for line in res.interpretation.get("effects", []):
        st.write("•", line)
    st.info(res.interpretation.get("note", ""))
    st.caption(f"Delineamento balanceado com n = {res.n_per_cell} por célula.")


def _parse_two_way(text: str):
    """Parse 'A, B, Valor' rows into {(a_level, b_level): [values]}."""
    lines = [l for l in text.strip().splitlines() if l.strip()]
    if len(lines) < 2:
        return {}

    def split(line):
        return [c.strip() for c in (line.split("\t") if "\t" in line
                                    else line.split(","))]

    cells = {}
    start = 0
    # skip a header row if the third column is not numeric
    first = split(lines[0])
    if len(first) >= 3:
        try:
            float(first[2])
        except ValueError:
            start = 1
    for line in lines[start:]:
        parts = split(line)
        if len(parts) < 3:
            continue
        a, b, v = parts[0], parts[1], parts[2]
        try:
            val = float(v)
        except ValueError:
            continue
        cells.setdefault((a, b), []).append(val)
    return cells


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
