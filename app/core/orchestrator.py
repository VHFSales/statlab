"""Analysis orchestrator (design section 16, FR-19).

Ties the validated statistical core into a single, reproducible AnalysisResult with
a full audit record. This is the reusable engine consumed by the UI and exporters;
neither of those touches the statistics package directly.

Flow: validate -> describe -> diagnostics -> recommend -> omnibus -> (post-hoc) ->
significance matrix -> CLD -> effect sizes -> assemble result + audit.
"""

from __future__ import annotations

import hashlib
import json
import platform
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from statistics import (anova, assumptions, cld, descriptive, effect_sizes,
                        games_howell, nonparametric, paired as paired_mod, ttest,
                        tukey, two_way_anova as two_way_mod, welch)
from statistics import __version__ as CORE_VERSION
from statistics.decision_engine import DesignSpec as EngineDesign
from statistics.decision_engine import Diagnostics, recommend
from statistics.types import (AnovaTable, EffectSizes, RawGroup, SummaryGroup,
                              WelchResult)
from data.validator import has_errors, validate_raw, validate_summary
from reports import interpreter


PROGRAM_VERSION = "StatLab 0.1.0"


@dataclass
class AnalysisOptions:
    alpha: float = 0.05
    ci_level: float = 0.95
    mode: str = "quick"                 # "quick" | "advanced"
    method_override: Optional[str] = None      # advanced: "anova" | "welch"
    posthoc_override: Optional[str] = None      # advanced: "tukey" | "games_howell"
    force_posthoc: bool = False                 # advanced: run despite non-sig omnibus
    decimals: int = 4
    order: Optional[List[str]] = None           # visual order for CLD/summary
    nonparametric: bool = False                 # advanced opt-in: Kruskal-Wallis+Dunn
    dunn_adjust: str = "holm"                    # multiplicity adjust for Dunn


@dataclass
class AnalysisResult:
    analysis_id: str
    created_at: str
    program_version: str
    core_version: str
    python_version: str
    data_kind: str
    data_hash: str
    alpha: float
    issues: list
    descriptive: list
    diagnostics: dict
    recommendation: dict
    omnibus: Optional[dict]
    omnibus_kind: Optional[str]         # "anova" | "welch"
    effect_sizes: Optional[dict]
    posthoc: Optional[dict]
    significance_matrix: Optional[dict]
    cld: Optional[dict]
    interpretation: dict
    warnings: list
    refusals: list
    ttest: Optional[dict] = None        # two-group case
    summary_based: bool = False         # True when analysis used summary stats
    nonparametric_omnibus: Optional[dict] = None   # Kruskal-Wallis result
    mann_whitney: Optional[dict] = None            # two-group non-parametric
    stale: bool = False


def _hash_raw(raw: Dict[str, list]) -> str:
    canon = json.dumps({k: list(v) for k, v in raw.items()}, sort_keys=True,
                       default=str)
    return hashlib.sha256(canon.encode()).hexdigest()


def _clean(vals):
    return descriptive._clean(vals)


def analyze_raw(raw: Dict[str, list], design: EngineDesign,
                options: AnalysisOptions = None) -> AnalysisResult:
    options = options or AnalysisOptions()
    alpha = options.alpha
    labels = list(raw.keys())
    order = options.order or labels

    issues = validate_raw(raw, min_n_for_analysis=2)
    issue_dicts = [asdict(i) for i in issues]

    groups = [RawGroup(lab, raw[lab]) for lab in labels]
    desc = [asdict(d) for d in descriptive.describe(groups, options.ci_level)]

    result = AnalysisResult(
        analysis_id=uuid.uuid4().hex,
        created_at=datetime.now(timezone.utc).isoformat(),
        program_version=PROGRAM_VERSION,
        core_version=CORE_VERSION,
        python_version=platform.python_version(),
        data_kind="RAW",
        data_hash=_hash_raw(raw),
        alpha=alpha,
        issues=issue_dicts,
        descriptive=desc,
        diagnostics={},
        recommendation={},
        omnibus=None, omnibus_kind=None, effect_sizes=None,
        posthoc=None, significance_matrix=None, cld=None,
        interpretation={}, warnings=[], refusals=[],
    )

    if has_errors(issues):
        result.refusals.append("A análise não foi executada: há erros de dados "
                               "que impedem um cálculo válido (ver issues).")
        return result

    # --- diagnostics ---
    valid_groups = [g for g in groups if len(_clean(g.values)) >= 2]
    ns = [len(_clean(g.values)) for g in valid_groups]
    try:
        bf = assumptions.brown_forsythe(valid_groups)
        lev = assumptions.levene(valid_groups)
        vr = assumptions.variance_ratio(valid_groups)
    except Exception:
        bf = lev = None
        vr = float("nan")

    diag = Diagnostics(
        k_groups=len(valid_groups),
        n_per_group=ns,
        variance_ratio=vr,
        levene_p=lev.p if lev else float("nan"),
        brown_forsythe_p=bf.p if bf else float("nan"),
        balanced=(len(set(ns)) == 1) if ns else None,
    )
    result.diagnostics = {
        "levene": asdict(lev) if lev else None,
        "brown_forsythe": asdict(bf) if bf else None,
        "variance_ratio": vr,
        "independence_note": assumptions.independence_note(),
        "shapiro_residuals": asdict(assumptions.shapiro_wilk(
            assumptions.residuals(valid_groups))),
    }

    # --- recommendation ---
    rec = recommend(design, diag, alpha=alpha)
    result.recommendation = asdict(rec)
    result.warnings.extend(rec.warnings)
    if rec.is_refused:
        result.refusals.extend(rec.refusals)
        return result

    # a two-way design cannot be analysed by the one-way path; direct the user
    if rec.method == "two-way ANOVA":
        result.refusals.append(
            "Foi declarado um delineamento com dois fatores. Use a ANOVA de duas "
            "vias (analyze_two_way / seção FATORIAL na interface), que estima os "
            "dois efeitos principais e a interação. A análise de uma via não é "
            "apropriada aqui.")
        return result

    # --- non-parametric path (ADVANCED opt-in only; NEVER auto by Shapiro) ---
    if options.nonparametric:
        result.warnings.append(
            "Método não-paramétrico selecionado explicitamente pelo usuário. Esta "
            "escolha não foi feita automaticamente a partir de um teste de "
            "normalidade.")
        # rank-based tests admit n >= 1, so use a looser (non-empty) filter here
        # than the n >= 2 filter used for parametric diagnostics.
        np_groups = [g for g in groups if len(_clean(g.values)) >= 1]
        dropped = [g.label for g in groups if len(_clean(g.values)) == 0]
        if dropped:
            result.warnings.append(
                "ATENÇÃO: grupo(s) sem observações válidas removido(s) da análise: "
                + ", ".join(dropped) + ".")
        # two groups -> Mann-Whitney U; three or more -> Kruskal-Wallis (+ Dunn)
        if len(np_groups) == 2:
            mw = nonparametric.mann_whitney(np_groups[0], np_groups[1])
            result.mann_whitney = asdict(mw)
            result.omnibus_kind = "mann_whitney"
            result.interpretation["omnibus"] = (
                f"Mann-Whitney U = {mw.u_statistic:.{options.decimals}f} "
                f"(z = {mw.z:.{options.decimals}f}), p "
                + interpreter._p_rel(mw.p,
                                     interpreter.format_p(mw.p, options.decimals))
                + ".")
            result.interpretation["conclusion"] = (
                interpreter.omnibus_conclusion_rank(mw.p, alpha))
            if mw.note:
                result.warnings.append(mw.note)
            return result
        kw = nonparametric.kruskal_wallis(np_groups)
        result.nonparametric_omnibus = asdict(kw)
        result.omnibus_kind = "kruskal"
        result.interpretation["omnibus"] = (
            f"Kruskal-Wallis: H({kw.df}) = {kw.statistic:.{options.decimals}f}, "
            f"p " + interpreter._p_rel(kw.p,
                                       interpreter.format_p(kw.p, options.decimals))
            + f" (correção de empates = {kw.tie_correction:.{options.decimals}f}).")
        result.interpretation["conclusion"] = interpreter.omnibus_conclusion_rank(
            kw.p, alpha)
        run_posthoc = (kw.p < alpha)
        if options.mode == "advanced" and options.force_posthoc:
            run_posthoc = True
        if not run_posthoc:
            result.warnings.append(
                "O teste global (Kruskal-Wallis) não apresentou significância "
                "estatística. Comparações de Dunn não foram executadas "
                "automaticamente.")
            return result
        if len(np_groups) < 3:
            return result
        ph = nonparametric.dunn_test(np_groups, alpha=alpha,
                                     adjust=options.dunn_adjust, order=order)
        result.posthoc = asdict(ph)
        sig = ph.significance_matrix()
        result.significance_matrix = asdict(sig)
        means = {d["label"]: d["mean"] for d in desc}
        cld_order = sorted(sig.labels, key=lambda l: means.get(l, 0.0), reverse=True)
        cld_res = cld.compact_letter_display(sig, order=cld_order)
        result.cld = asdict(cld_res)
        result.interpretation["posthoc"] = interpreter.posthoc_sentence(
            ph, options.decimals)
        return result

    # --- two-group case: run a t-test instead of ANOVA/post-hoc ---
    if rec.method in ("Student's t-test", "Welch's t-test"):
        g1, g2 = valid_groups[0], valid_groups[1]
        if rec.method == "Welch's t-test":
            tt = ttest.welch_t(g1, g2, alpha=alpha, ci_level=options.ci_level)
        else:
            tt = ttest.student_t(g1, g2, alpha=alpha, ci_level=options.ci_level)
        result.ttest = asdict(tt)
        result.interpretation["omnibus"] = (
            f"{tt.method}: t({_fmt_df(tt.df)}) = "
            f"{tt.statistic:.{options.decimals}f}, p "
            + (interpreter._p_rel(tt.p, interpreter.format_p(tt.p, options.decimals)))
            + f", d de Cohen = {tt.cohens_d:.{options.decimals}f}.")
        result.interpretation["conclusion"] = interpreter.omnibus_conclusion(tt.p,
                                                                             alpha)
        return result

    # --- method selection (advanced override respected) ---
    method = rec.method
    if options.mode == "advanced" and options.method_override:
        method = {"anova": "one-way ANOVA",
                  "welch": "Welch's ANOVA"}.get(options.method_override, method)

    # --- omnibus ---
    if method == "Welch's ANOVA":
        wres = welch.welch_anova_raw(valid_groups)
        result.omnibus = asdict(wres)
        result.omnibus_kind = "welch"
        omnibus_p = wres.p
        eff = None
        result.interpretation["omnibus"] = interpreter.apa_welch(wres, alpha,
                                                                 options.decimals)
    else:
        table = anova.anova_oneway_raw(valid_groups)
        eff = effect_sizes.effect_sizes_from_anova(table)
        result.omnibus = asdict(table)
        result.omnibus_kind = "anova"
        result.effect_sizes = asdict(eff)
        omnibus_p = table.p
        result.interpretation["omnibus"] = interpreter.apa_anova(table, eff, alpha,
                                                                 options.decimals)

    result.interpretation["conclusion"] = interpreter.omnibus_conclusion(omnibus_p,
                                                                          alpha)

    # --- post-hoc decision ---
    run_posthoc = (omnibus_p < alpha)
    if options.mode == "advanced" and options.force_posthoc:
        run_posthoc = True
        result.warnings.append("Modo avançado: pós-teste executado por escolha "
                               "explícita do usuário (registrado).")
    if not run_posthoc:
        result.warnings.append(
            "O teste global não apresentou significância estatística. Comparações "
            "pós-hoc não foram executadas automaticamente.")
        return result

    posthoc_kind = "games_howell" if method == "Welch's ANOVA" else "tukey"
    if options.mode == "advanced" and options.posthoc_override:
        posthoc_kind = options.posthoc_override

    if posthoc_kind == "games_howell":
        ph = games_howell.games_howell_raw(valid_groups, alpha=alpha, order=order)
    else:
        ph = tukey.tukey_raw(valid_groups, alpha=alpha, order=order)

    result.posthoc = asdict(ph)
    sig = ph.significance_matrix()
    result.significance_matrix = asdict(sig)

    # order for CLD: descending mean (convention "a" at highest mean)
    means = {d["label"]: d["mean"] for d in desc}
    cld_order = sorted(sig.labels, key=lambda l: means.get(l, 0.0), reverse=True)
    cld_res = cld.compact_letter_display(sig, order=cld_order)
    problems = cld.verify_invariants(sig, cld_res)
    if problems:
        result.warnings.append("AVISO INTERNO: violação de invariante do CLD: "
                               + "; ".join(problems))
    result.cld = asdict(cld_res)
    result.interpretation["posthoc"] = interpreter.posthoc_sentence(ph,
                                                                    options.decimals)
    return result



def _fmt_df(df) -> str:
    """Format degrees of freedom: integer if whole, else 2 decimals (Welch)."""
    if abs(df - round(df)) < 1e-9:
        return str(int(round(df)))
    return f"{df:.2f}"


def _hash_summary(summary: Dict[str, dict]) -> str:
    canon = json.dumps(summary, sort_keys=True, default=str)
    return hashlib.sha256(canon.encode()).hexdigest()


def analyze_summary(summary: Dict[str, dict], design: EngineDesign,
                    options: AnalysisOptions = None) -> AnalysisResult:
    """Analyze from summary statistics (mean, sd, n) per group (SR-13, spec 92).

    ``summary`` = { label: {"mean":.., "sd":.., "n":..}, ... }. Raw-only diagnostics
    (residuals, Q-Q, Shapiro, individual outliers) are impossible and flagged. Never
    fabricates raw data. Refuses when n is missing (FR-3.3).
    """
    options = options or AnalysisOptions()
    alpha = options.alpha
    labels = list(summary.keys())
    order = options.order or labels

    issues = validate_summary(summary)
    result = AnalysisResult(
        analysis_id=uuid.uuid4().hex,
        created_at=datetime.now(timezone.utc).isoformat(),
        program_version=PROGRAM_VERSION, core_version=CORE_VERSION,
        python_version=platform.python_version(),
        data_kind="SUMMARY", data_hash=_hash_summary(summary), alpha=alpha,
        issues=[asdict(i) for i in issues], descriptive=[], diagnostics={},
        recommendation={}, omnibus=None, omnibus_kind=None, effect_sizes=None,
        posthoc=None, significance_matrix=None, cld=None, interpretation={},
        warnings=[], refusals=[], summary_based=True,
    )
    result.warnings.append(
        "Análise realizada a partir de estatísticas resumidas. Diagnósticos que "
        "exigem dados brutos (resíduos, Q-Q plot, Shapiro-Wilk, outliers "
        "individuais) não são possíveis. Nenhum dado bruto foi fabricado.")

    if has_errors(issues):
        result.refusals.append("A análise não foi executada: dados resumidos "
                               "insuficientes ou inválidos (ver issues).")
        return result

    groups = [SummaryGroup(lab, float(summary[lab]["mean"]),
                           float(summary[lab]["sd"]), int(summary[lab]["n"]))
              for lab in labels]
    ns = [g.n for g in groups]
    means = [g.mean for g in groups]
    variances = [g.sd ** 2 for g in groups]

    # descriptive rows built from the provided summaries (SE, CI via t)
    from statistics.descriptive import t_ppf
    import math as _m
    desc = []
    for g in groups:
        se = g.sd / _m.sqrt(g.n) if g.n >= 1 else float("nan")
        if g.n >= 2:
            tcrit = t_ppf(0.5 + options.ci_level / 2.0, g.n - 1)
            ci_low, ci_high = g.mean - tcrit * se, g.mean + tcrit * se
        else:
            ci_low = ci_high = float("nan")
        cv = g.sd / abs(g.mean) if abs(g.mean) > 1e-15 else float("nan")
        desc.append({"label": g.label, "n": g.n, "n_missing": 0, "mean": g.mean,
                     "median": float("nan"), "sd": g.sd, "variance": g.sd ** 2,
                     "se": se, "ci_level": options.ci_level, "ci_low": ci_low,
                     "ci_high": ci_high, "minimum": float("nan"),
                     "maximum": float("nan"), "range": float("nan"),
                     "q1": float("nan"), "q3": float("nan"), "iqr": float("nan"),
                     "cv": cv})
    result.descriptive = desc

    # variance ratio only (no test on values available from summaries)
    valid_var = [v for v in variances if v > 0]
    vr = (max(valid_var) / min(valid_var)) if len(valid_var) >= 2 else float("nan")
    diag = Diagnostics(k_groups=len(groups), n_per_group=ns, variance_ratio=vr,
                       levene_p=float("nan"), brown_forsythe_p=float("nan"),
                       balanced=(len(set(ns)) == 1))
    result.diagnostics = {
        "variance_ratio": vr,
        "independence_note": assumptions.independence_note(),
        "note": ("Testes de homogeneidade (Levene/Brown-Forsythe) e de normalidade "
                 "não são possíveis a partir de estatísticas resumidas."),
    }

    rec = recommend(design, diag, alpha=alpha)
    result.recommendation = asdict(rec)
    result.warnings.extend(rec.warnings)
    if rec.is_refused:
        result.refusals.extend(rec.refusals)
        return result

    # a two-way design cannot be analysed by the one-way summary path either
    if rec.method == "two-way ANOVA":
        result.refusals.append(
            "Foi declarado um delineamento com dois fatores. A ANOVA de duas vias "
            "(fatorial) requer os dados por célula e não pode ser realizada a partir "
            "destas estatísticas resumidas de uma via. A análise de uma via não é "
            "apropriada aqui.")
        return result

    # two-group case not supported from summaries here (t-test needs the same
    # moments; can be added). For k==2 we still compute via ANOVA summary (F=t^2).
    method = rec.method
    if options.mode == "advanced" and options.method_override:
        method = {"anova": "one-way ANOVA",
                  "welch": "Welch's ANOVA"}.get(options.method_override, method)
    if method in ("Student's t-test", "Welch's t-test"):
        # equal-variance -> ANOVA summary (F=t^2); unequal -> Welch summary
        method = "one-way ANOVA" if method == "Student's t-test" else "Welch's ANOVA"

    if method == "Welch's ANOVA":
        wres = welch.welch_anova_summary(groups)
        result.omnibus = asdict(wres); result.omnibus_kind = "welch"
        omnibus_p = wres.p
        result.interpretation["omnibus"] = interpreter.apa_welch(wres, alpha,
                                                                 options.decimals)
    else:
        table = anova.anova_oneway_summary(groups)
        eff = effect_sizes.effect_sizes_from_anova(table)
        result.omnibus = asdict(table); result.omnibus_kind = "anova"
        result.effect_sizes = asdict(eff); omnibus_p = table.p
        result.interpretation["omnibus"] = interpreter.apa_anova(table, eff, alpha,
                                                                 options.decimals)
    result.interpretation["conclusion"] = interpreter.omnibus_conclusion(omnibus_p,
                                                                          alpha)

    run_posthoc = (omnibus_p < alpha)
    if options.mode == "advanced" and options.force_posthoc:
        run_posthoc = True
    if not run_posthoc:
        result.warnings.append(
            "O teste global não apresentou significância estatística. Comparações "
            "pós-hoc não foram executadas automaticamente.")
        return result

    if len(groups) < 3:
        return result  # 2 groups: omnibus is enough

    posthoc_kind = "games_howell" if method == "Welch's ANOVA" else "tukey"
    if options.mode == "advanced" and options.posthoc_override:
        posthoc_kind = options.posthoc_override

    if posthoc_kind == "games_howell":
        ph = games_howell.games_howell_from_moments(labels, ns, means, variances,
                                                    alpha=alpha, order=order)
    else:
        table = anova.anova_oneway_summary(groups)
        ph = tukey.tukey_from_moments(labels, ns, means, table.ms_within,
                                      table.df_within, alpha=alpha, order=order)
    result.posthoc = asdict(ph)
    sig = ph.significance_matrix()
    result.significance_matrix = asdict(sig)
    mean_map = {g.label: g.mean for g in groups}
    cld_order = sorted(sig.labels, key=lambda l: mean_map.get(l, 0.0), reverse=True)
    cld_res = cld.compact_letter_display(sig, order=cld_order)
    result.cld = asdict(cld_res)
    result.interpretation["posthoc"] = interpreter.posthoc_sentence(ph,
                                                                    options.decimals)
    return result


def analyze_batch(variables: Dict[str, Dict[str, list]], design: EngineDesign,
                  options: AnalysisOptions = None,
                  fdr_method: Optional[str] = None) -> dict:
    """Analyze many response variables (FR-13.2, spec 57).

    ``variables`` = { variable_name: raw_dict }. Returns per-variable results plus a
    consolidated view. Warns about multiplicity ACROSS variables. When ``fdr_method``
    is given ("holm" | "bh" | "bonferroni"), an OPT-IN correction is applied to the
    vector of omnibus p-values (never automatic).
    """
    options = options or AnalysisOptions()
    from statistics import multiplicity

    results = {name: analyze_raw(raw, design, options)
               for name, raw in variables.items()}

    # collect omnibus p-values where available
    names, pvals = [], []
    for name, r in results.items():
        p = None
        if r.omnibus and r.omnibus_kind in ("anova", "welch"):
            p = r.omnibus["p"]
        elif r.omnibus_kind == "kruskal" and r.nonparametric_omnibus:
            p = r.nonparametric_omnibus["p"]
        elif r.omnibus_kind == "mann_whitney" and r.mann_whitney:
            p = r.mann_whitney["p"]
        elif r.ttest:
            p = r.ttest["p"]
        if p is not None:
            names.append(name); pvals.append(p)

    consolidated = {
        "n_variables": len(variables),
        "n_tested": len(pvals),
        "warnings": [],
        "omnibus_p": dict(zip(names, pvals)),
        "fdr": None,
    }
    if len(pvals) > 1:
        consolidated["warnings"].append(
            f"ATENÇÃO: {len(pvals)} hipóteses globais foram avaliadas "
            f"simultaneamente. Isso aumenta a probabilidade de falso positivo entre "
            f"variáveis. Considere uma correção de multiplicidade (Holm ou "
            f"Benjamini-Hochberg/FDR) — não aplicada automaticamente.")
    if fdr_method and len(pvals) >= 1:
        adj = multiplicity.adjust(pvals, method=fdr_method, alpha=options.alpha,
                                  labels=names)
        consolidated["fdr"] = asdict(adj)

    return {"results": results, "consolidated": consolidated}



def reproduce_from_config(config: Dict) -> AnalysisResult:
    """Re-run an analysis from a reproduction config (FR-19.2).

    ``config`` is the dict produced by persistence.result_store.build_repro_config.
    Rebuilds the design and options and dispatches to analyze_raw/analyze_summary.
    """
    design = EngineDesign(**{k: v for k, v in config.get("design", {}).items()
                             if k in EngineDesign.__dataclass_fields__})
    opt_fields = set(AnalysisOptions.__dataclass_fields__)
    options = AnalysisOptions(**{k: v for k, v in config.get("options", {}).items()
                                 if k in opt_fields})
    data = config["data"]
    if config.get("data_kind") == "SUMMARY":
        return analyze_summary(data, design, options)
    return analyze_raw(data, design, options)


def results_match(a: AnalysisResult, b: AnalysisResult, tol: float = 1e-9) -> bool:
    """Compare two results for statistical equivalence (ignores ids/timestamps).

    Checks omnibus statistic/p, effect sizes, t-test, post-hoc adjusted p, and the
    CLD display. Returns True if all present numeric quantities agree within tol.
    """
    def close(x, y):
        if x is None and y is None:
            return True
        if x is None or y is None:
            return False
        try:
            return abs(float(x) - float(y)) <= tol
        except (TypeError, ValueError):
            return x == y

    if a.omnibus_kind != b.omnibus_kind:
        return False
    if a.omnibus and b.omnibus:
        key = "f" if a.omnibus_kind == "anova" else "statistic"
        if not close(a.omnibus.get(key), b.omnibus.get(key)):
            return False
        if not close(a.omnibus.get("p"), b.omnibus.get("p")):
            return False
    if a.ttest and b.ttest:
        if not (close(a.ttest["statistic"], b.ttest["statistic"])
                and close(a.ttest["p"], b.ttest["p"])):
            return False
    if a.effect_sizes and b.effect_sizes:
        for k in ("eta_squared", "omega_squared"):
            if not close(a.effect_sizes.get(k), b.effect_sizes.get(k)):
                return False
    if a.posthoc and b.posthoc:
        ca = {(c["group1"], c["group2"]): c["p_adjusted"]
              for c in a.posthoc["comparisons"]}
        cb = {(c["group1"], c["group2"]): c["p_adjusted"]
              for c in b.posthoc["comparisons"]}
        if set(ca) != set(cb):
            return False
        for key in ca:
            if not close(ca[key], cb[key]):
                return False
    if (a.cld or {}).get("display") != (b.cld or {}).get("display"):
        return False
    return True



@dataclass
class TwoWayAnalysisResult:
    analysis_id: str
    created_at: str
    program_version: str
    core_version: str
    python_version: str
    alpha: float
    factor_a: str
    factor_b: str
    a_levels: list
    b_levels: list
    n_per_cell: int
    effects: list                 # list of EffectRow dicts
    cell_descriptive: list        # per-cell n/mean/sd
    interpretation: dict
    warnings: list
    refusals: list
    method: str = "Two-way ANOVA (balanced)"


def analyze_two_way(cells: Dict, factor_a: str = "Fator A",
                    factor_b: str = "Fator B",
                    options: AnalysisOptions = None) -> TwoWayAnalysisResult:
    """Balanced two-way ANOVA orchestration.

    ``cells`` maps (a_level, b_level) -> list of observations.
    """
    options = options or AnalysisOptions()
    alpha = options.alpha
    res = TwoWayAnalysisResult(
        analysis_id=uuid.uuid4().hex,
        created_at=datetime.now(timezone.utc).isoformat(),
        program_version=PROGRAM_VERSION, core_version=CORE_VERSION,
        python_version=platform.python_version(), alpha=alpha,
        factor_a=factor_a, factor_b=factor_b, a_levels=[], b_levels=[],
        n_per_cell=0, effects=[], cell_descriptive=[], interpretation={},
        warnings=[], refusals=[])

    try:
        tw = two_way_mod.two_way_anova(cells, factor_a, factor_b)
    except two_way_mod.InsufficientDataError as exc:
        res.refusals.append(str(exc))
        return res

    res.a_levels = tw.a_levels
    res.b_levels = tw.b_levels
    res.n_per_cell = tw.n_per_cell
    res.effects = [asdict(e) for e in tw.effects]

    # per-cell descriptive
    for (ai, bj), vals in cells.items():
        clean = descriptive._clean(vals)
        if not clean:
            continue
        d = descriptive.describe_group(f"{ai}|{bj}", vals, options.ci_level)
        res.cell_descriptive.append({
            "a_level": ai, "b_level": bj, "n": d.n, "mean": d.mean, "sd": d.sd})

    # interpretation for each effect
    def eff_text(e):
        sig = e["p"] < alpha
        verdict = ("efeito estatisticamente significativo" if sig
                   else "sem efeito estatisticamente significativo")
        return (f"{e['name']}: F({int(e['df'])}, "
                f"{int(tw.by_name('Error').df)}) = "
                f"{e['f']:.{options.decimals}f}, p "
                + interpreter._p_rel(e["p"],
                                     interpreter.format_p(e["p"], options.decimals))
                + f", \u03b7\u00b2 parcial = {e['partial_eta_sq']:.{options.decimals}f}"
                + f" ({verdict}).")

    lines = [eff_text(e) for e in res.effects if e["name"] in
             (factor_a, factor_b, f"{factor_a}:{factor_b}")]
    res.interpretation["effects"] = lines
    inter = tw.by_name(f"{factor_a}:{factor_b}")
    if inter.p < alpha:
        res.interpretation["note"] = (
            "A interação é significativa: os efeitos de um fator dependem do nível "
            "do outro. Interprete os efeitos principais com cautela.")
    else:
        res.interpretation["note"] = (
            "A interação não foi significativa; os efeitos principais podem ser "
            "interpretados de forma mais direta (a ausência de significância não "
            "prova ausência de interação).")
    return res



@dataclass
class PairedAnalysisResult:
    analysis_id: str
    created_at: str
    program_version: str
    core_version: str
    python_version: str
    alpha: float
    condition1: str
    condition2: str
    n_pairs: int
    n_dropped: int
    parametric: Optional[dict]        # PairedTResult dict
    nonparametric: Optional[dict]     # WilcoxonResult dict
    descriptive_diff: Optional[dict]  # descriptive of the paired differences
    interpretation: dict
    warnings: list
    refusals: list
    method: str = "Paired comparison"


def analyze_paired(x1: list, x2: list, condition1: str = "Condição 1",
                   condition2: str = "Condição 2", options: AnalysisOptions = None
                   ) -> PairedAnalysisResult:
    """Paired (dependent) two-condition comparison.

    Runs the paired t-test and, in advanced/non-parametric mode, the Wilcoxon
    signed-rank test. Inputs must be aligned pair-by-pair (same length); pairs with
    a missing value on either side are dropped and reported (never zero-filled).
    """
    options = options or AnalysisOptions()
    alpha = options.alpha
    res = PairedAnalysisResult(
        analysis_id=uuid.uuid4().hex,
        created_at=datetime.now(timezone.utc).isoformat(),
        program_version=PROGRAM_VERSION, core_version=CORE_VERSION,
        python_version=platform.python_version(), alpha=alpha,
        condition1=condition1, condition2=condition2, n_pairs=0, n_dropped=0,
        parametric=None, nonparametric=None, descriptive_diff=None,
        interpretation={}, warnings=[], refusals=[])

    try:
        a, b, dropped = paired_mod._aligned_pairs(x1, x2)
    except paired_mod.InsufficientDataError as exc:
        res.refusals.append(str(exc))
        return res
    res.n_pairs = len(a)
    res.n_dropped = dropped
    if dropped:
        res.warnings.append(
            f"{dropped} par(es) com valor ausente em uma das condições foram "
            f"descartados (nunca convertidos em zero).")
    if len(a) < 2:
        res.refusals.append("São necessários pelo menos 2 pares completos.")
        return res

    # descriptive of the within-pair differences
    diffs = [ai - bi for ai, bi in zip(a, b)]
    dd = descriptive.describe_group(f"{condition1}-{condition2}", diffs,
                                    options.ci_level)
    res.descriptive_diff = asdict(dd)

    use_nonparam = options.nonparametric
    try:
        if not use_nonparam:
            pt = paired_mod.paired_t_test(x1, x2, condition1, condition2, alpha,
                                          options.ci_level)
            res.parametric = asdict(pt)
            res.interpretation["primary"] = (
                f"Teste t pareado: t({int(pt.df)}) = "
                f"{pt.statistic:.{options.decimals}f}, p "
                + interpreter._p_rel(pt.p,
                                     interpreter.format_p(pt.p, options.decimals))
                + f", d de Cohen (dz) = {pt.cohens_dz:.{options.decimals}f}.")
            res.interpretation["conclusion"] = interpreter.omnibus_conclusion(pt.p,
                                                                              alpha)
        else:
            res.warnings.append(
                "Teste não-paramétrico selecionado explicitamente (Wilcoxon "
                "signed-rank). Esta escolha não foi feita automaticamente a partir "
                "de um teste de normalidade.")
            wx = paired_mod.wilcoxon_signed_rank(x1, x2, condition1, condition2,
                                                 alpha)
            res.nonparametric = asdict(wx)
            res.interpretation["primary"] = (
                f"Wilcoxon signed-rank: W = {wx.w_statistic:.{options.decimals}f} "
                f"(z = {wx.z:.{options.decimals}f}), p "
                + interpreter._p_rel(wx.p,
                                     interpreter.format_p(wx.p, options.decimals))
                + ".")
            res.interpretation["conclusion"] = (
                interpreter.omnibus_conclusion_rank(wx.p, alpha))
            if wx.note:
                res.warnings.append(wx.note)
    except paired_mod.InsufficientDataError as exc:
        res.refusals.append(str(exc))
    return res
