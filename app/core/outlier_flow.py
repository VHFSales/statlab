"""Outlier diagnosis and REGISTERED exclusion flow (FR-17, spec 50).

Guardrails:
- Never auto-excludes. Diagnostics only flag candidates.
- Exclusion requires an explicit list of (group, value) targets and a reason.
- Every exclusion is logged with value, group, reason, method, and timestamp.
- Provides an original-vs-after-exclusion comparison so the researcher sees the
  impact of removing points (FR-17.4). The original analysis is never discarded.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from statistics import outliers
from statistics.decision_engine import DesignSpec as EngineDesign
from app.core.orchestrator import AnalysisOptions, analyze_raw


def _is_missing(v) -> bool:
    if v is None:
        return True
    try:
        return math.isnan(float(v))
    except (TypeError, ValueError):
        return True


@dataclass
class ExclusionRecord:
    group: str
    value: float
    reason: str
    method: str
    timestamp: str


def diagnose_outliers(raw: Dict[str, list], method: str = "iqr",
                      alpha: float = 0.05, k: float = 1.5) -> Dict[str, list]:
    """Return per-group flagged candidates. method in {"iqr", "grubbs"}.

    Nothing is excluded here — these are diagnostics only.
    """
    out: Dict[str, list] = {}
    for group, values in raw.items():
        clean = [float(v) for v in values if not _is_missing(v)]
        if method == "grubbs":
            res = outliers.grubbs_test(clean, alpha=alpha)
            flagged = []
            if res.get("is_outlier"):
                flagged.append({"value": res["value"], "criterion": res["criterion"],
                                "statistic": res.get("statistic"),
                                "critical": res.get("critical")})
            out[group] = flagged
        else:
            out[group] = outliers.iqr_outliers(clean, k=k)
    return out


def apply_exclusions(raw: Dict[str, list], targets: List[dict], reason: str,
                     method: str) -> "tuple[Dict[str, list], List[ExclusionRecord]]":
    """Remove specified (group, value) targets, logging each exclusion.

    ``targets`` = [{"group": g, "value": v}, ...]. Each matching value is removed
    ONCE (first match) so duplicates are handled predictably. Missing values are
    never touched. Returns (new_raw, log).
    """
    ts = datetime.now(timezone.utc).isoformat()
    new_raw = {g: list(vals) for g, vals in raw.items()}
    log: List[ExclusionRecord] = []
    for t in targets:
        g = t["group"]
        v = float(t["value"])
        if g not in new_raw:
            continue
        # remove one matching value (tolerant float compare)
        for i, cur in enumerate(new_raw[g]):
            if _is_missing(cur):
                continue
            if abs(float(cur) - v) <= 1e-12:
                del new_raw[g][i]
                log.append(ExclusionRecord(group=g, value=v, reason=reason,
                                           method=method, timestamp=ts))
                break
    return new_raw, log


@dataclass
class ComparisonResult:
    original: dict            # AnalysisResult as dict
    after_exclusion: dict     # AnalysisResult as dict
    exclusions: List[dict]    # ExclusionRecord dicts
    reason: str
    method: str


def compare_with_exclusions(raw: Dict[str, list], design: EngineDesign,
                            targets: List[dict], reason: str, method: str,
                            options: AnalysisOptions = None) -> ComparisonResult:
    """Run the analysis before and after registered exclusions (FR-17.4)."""
    from dataclasses import asdict as _asdict
    options = options or AnalysisOptions()
    original = analyze_raw(raw, design, options)
    new_raw, log = apply_exclusions(raw, targets, reason, method)
    after = analyze_raw(new_raw, design, options)
    # attach the exclusion audit to the after-result's warnings for traceability
    for rec in log:
        after.warnings.append(
            f"Observação excluída (registrada): grupo '{rec.group}', valor "
            f"{rec.value}, método {rec.method}, motivo: {rec.reason}.")
    return ComparisonResult(
        original=_asdict(original), after_exclusion=_asdict(after),
        exclusions=[asdict(r) for r in log], reason=reason, method=method)
