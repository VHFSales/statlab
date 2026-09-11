"""Data transformation (FR-3, FR-8, FR-10; design section 13).

- wide <-> long conversions.
- missing handling: drop-with-log, NEVER zero-fill (FR-8).
- technical-replicate aggregation to the experimental-unit mean: the statistically
  correct remedy for pseudoreplication (critical review item 13). This is an
  OFFERED action, never applied silently.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional


def _is_missing(v) -> bool:
    if v is None:
        return True
    try:
        fv = float(v)
    except (TypeError, ValueError):
        return True
    return math.isnan(fv)


# --------------------------------------------------------------------------- #
# wide <-> long
# --------------------------------------------------------------------------- #
def wide_to_long(raw: Dict[str, List[Optional[float]]]):
    """Return list of (group_label, value) dropping missing (logged by caller)."""
    out = []
    for lab, vals in raw.items():
        for v in vals:
            if not _is_missing(v):
                out.append((lab, float(v)))
    return out


def long_to_wide(pairs) -> Dict[str, List[float]]:
    out: Dict[str, List[float]] = {}
    for lab, v in pairs:
        if not _is_missing(v):
            out.setdefault(str(lab), []).append(float(v))
    return out


# --------------------------------------------------------------------------- #
# missing handling
# --------------------------------------------------------------------------- #
@dataclass
class MissingReport:
    per_group_informed: Dict[str, int] = field(default_factory=dict)
    per_group_valid: Dict[str, int] = field(default_factory=dict)
    per_group_missing: Dict[str, int] = field(default_factory=dict)

    @property
    def total_missing(self) -> int:
        return sum(self.per_group_missing.values())


def drop_missing(raw: Dict[str, List]) -> "tuple[Dict[str, List[float]], MissingReport]":
    """Drop missing values (never zero-fill) and report counts per group."""
    clean: Dict[str, List[float]] = {}
    rep = MissingReport()
    for lab, vals in raw.items():
        informed = len(vals)
        kept = [float(v) for v in vals if not _is_missing(v)]
        rep.per_group_informed[lab] = informed
        rep.per_group_valid[lab] = len(kept)
        rep.per_group_missing[lab] = informed - len(kept)
        clean[lab] = kept
    return clean, rep


# --------------------------------------------------------------------------- #
# technical-replicate aggregation (pseudoreplication remedy)
# --------------------------------------------------------------------------- #
@dataclass
class AggregationReport:
    method: str
    units_per_group: Dict[str, int] = field(default_factory=dict)
    note: str = ""


def aggregate_technical_replicates(
        replicates: Dict[str, Dict[str, List[Optional[float]]]],
        agg: str = "mean") -> "tuple[Dict[str, List[float]], AggregationReport]":
    """Aggregate technical replicates to one value per experimental unit.

    Input structure:
        { group_label: { unit_id: [replicate values...] , ... }, ... }
    Output: { group_label: [unit-level aggregated value, ...] }  where each element
    is ONE independent experimental unit (correct n for inference).

    ``agg`` in {"mean", "median"}. Missing replicate values are dropped, never
    zero-filled. A unit with no valid replicate is skipped.
    """
    out: Dict[str, List[float]] = {}
    rep = AggregationReport(
        method=f"aggregate technical replicates by {agg}",
        note=("Replicatas técnicas foram agregadas à unidade experimental; o n de "
              "análise passa a ser o número de unidades independentes. Este é o "
              "tratamento correto para evitar pseudorreplicação."),
    )
    for group, units in replicates.items():
        vals: List[float] = []
        for unit_id, reps in units.items():
            valid = [float(v) for v in reps if not _is_missing(v)]
            if not valid:
                continue
            if agg == "median":
                s = sorted(valid)
                n = len(s)
                m = s[n // 2] if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2])
            else:
                m = math.fsum(valid) / len(valid)
            vals.append(m)
        out[group] = vals
        rep.units_per_group[group] = len(vals)
    return out, rep
