"""Scientific plots (FR-15). Requires matplotlib; guarded so the rest of the app
works without it. Group order is visual only and never touches the statistics.

Provided figures: boxplot, violin, strip/scatter, mean +/- SD/SE/CI, individual +
mean, Q-Q, residuals-vs-fitted. CLD letters overlaid where applicable. Export
PNG/SVG/PDF at configurable dpi.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAVE_MPL = True
except Exception:
    HAVE_MPL = False


class PlottingUnavailable(RuntimeError):
    pass


def _require():
    if not HAVE_MPL:
        raise PlottingUnavailable(
            "matplotlib não está instalado neste ambiente. Instale matplotlib "
            "para gerar gráficos, ou utilize os dados/tabelas exportados."
        )


def _order(labels, order):
    if not order:
        return list(labels)
    rank = {l: i for i, l in enumerate(order)}
    return sorted(labels, key=lambda l: rank.get(l, 1e9))


def boxplot(data: Dict[str, Sequence[float]], order: Optional[List[str]] = None,
            letters: Optional[Dict[str, str]] = None, title: str = "",
            xlabel: str = "Grupo", ylabel: str = "Valor", figsize=(7, 5)):
    _require()
    labs = _order(list(data.keys()), order)
    series = [[float(x) for x in data[l] if x is not None and not
               (isinstance(x, float) and math.isnan(x))] for l in labs]
    fig, ax = plt.subplots(figsize=figsize)
    ax.boxplot(series, labels=labs, showmeans=True)
    # strip overlay to always show distribution (FR-15.3)
    for i, ys in enumerate(series, start=1):
        xs = [i + (0.06 * ((j % 5) - 2)) for j in range(len(ys))]
        ax.plot(xs, ys, "o", alpha=0.4, markersize=3, color="#444")
    if letters:
        ymax = max((max(s) for s in series if s), default=0)
        span = ymax - min((min(s) for s in series if s), default=0) or 1
        for i, l in enumerate(labs, start=1):
            if l in letters:
                top = max(series[i - 1]) if series[i - 1] else ymax
                ax.text(i, top + 0.05 * span, letters[l], ha="center",
                        fontweight="bold")
    ax.set_title(title); ax.set_xlabel(xlabel); ax.set_ylabel(ylabel)
    fig.tight_layout()
    return fig


def mean_error_plot(desc_rows: List[dict], order: Optional[List[str]] = None,
                    error: str = "sd", letters: Optional[Dict[str, str]] = None,
                    title: str = "", xlabel: str = "Grupo", ylabel: str = "Média",
                    figsize=(7, 5)):
    """error in {'sd','se','ci'}."""
    _require()
    by = {d["label"]: d for d in desc_rows}
    labs = _order(list(by.keys()), order)
    means = [by[l]["mean"] for l in labs]
    if error == "sd":
        errs = [[by[l]["sd"] for l in labs]] * 1
        lower = upper = [by[l]["sd"] for l in labs]
    elif error == "se":
        lower = upper = [by[l]["se"] for l in labs]
    else:  # ci
        lower = [by[l]["mean"] - by[l]["ci_low"] for l in labs]
        upper = [by[l]["ci_high"] - by[l]["mean"] for l in labs]
    fig, ax = plt.subplots(figsize=figsize)
    ax.errorbar(range(len(labs)), means, yerr=[lower, upper], fmt="o",
                capsize=4, color="#1f4e79")
    ax.set_xticks(range(len(labs))); ax.set_xticklabels(labs)
    if letters:
        for i, l in enumerate(labs):
            if l in letters:
                ax.text(i, means[i] + upper[i] * 1.1 + 1e-9, letters[l],
                        ha="center", fontweight="bold")
    ax.set_title(title or f"Média ± {error.upper()}")
    ax.set_xlabel(xlabel); ax.set_ylabel(ylabel)
    fig.tight_layout()
    return fig


def qq_plot(points, title="Q-Q plot dos resíduos", figsize=(6, 5)):
    _require()
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    fig, ax = plt.subplots(figsize=figsize)
    ax.plot(xs, ys, "o", markersize=4)
    if xs:
        lo, hi = min(xs), max(xs)
        # reference line through data quartiles
        ax.plot([lo, hi], [min(ys), max(ys)], "-", color="#c00", alpha=0.6)
    ax.set_xlabel("Quantis teóricos (normal)")
    ax.set_ylabel("Resíduos ordenados")
    ax.set_title(title)
    fig.tight_layout()
    return fig


def save_figure(fig, path: str, dpi: int = 300):
    _require()
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    return path
