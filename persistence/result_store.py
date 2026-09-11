"""Persistence for AnalysisResult and reproducibility configs (FR-19, spec 66/95).

Pure stdlib, JSON only. An AnalysisResult is a dataclass of JSON-serializable
fields, so serialization is a direct round-trip. A ReproConfig captures everything
needed to re-run an analysis identically: the dataset, alpha/options, the declared
design, and the captured software versions.
"""

from __future__ import annotations

import json
from dataclasses import asdict, fields
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.core.orchestrator import AnalysisOptions, AnalysisResult
from statistics.decision_engine import DesignSpec


# --------------------------------------------------------------------------- #
# AnalysisResult <-> dict / JSON
# --------------------------------------------------------------------------- #
def result_to_dict(result: AnalysisResult) -> Dict[str, Any]:
    return asdict(result)


def result_from_dict(d: Dict[str, Any]) -> AnalysisResult:
    """Reconstruct an AnalysisResult, tolerant of missing optional fields."""
    field_names = {f.name for f in fields(AnalysisResult)}
    kwargs = {k: v for k, v in d.items() if k in field_names}
    return AnalysisResult(**kwargs)


def save_result(result: AnalysisResult, path: str) -> str:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result_to_dict(result), f, ensure_ascii=False, indent=2)
    return path


def load_result(path: str) -> AnalysisResult:
    with open(path, "r", encoding="utf-8") as f:
        return result_from_dict(json.load(f))


# --------------------------------------------------------------------------- #
# Reproducibility config (FR-19.2)
# --------------------------------------------------------------------------- #
def _design_to_dict(design: DesignSpec) -> Dict[str, Any]:
    return {
        "n_response_vars": design.n_response_vars,
        "n_factors": design.n_factors,
        "independent_groups": design.independent_groups,
        "repeated_measures": design.repeated_measures,
        "paired": design.paired,
        "blocks": design.blocks,
        "multiple_obs_per_unit": design.multiple_obs_per_unit,
        "independent_units_asserted": design.independent_units_asserted,
    }


def _design_from_dict(d: Dict[str, Any]) -> DesignSpec:
    return DesignSpec(**{k: v for k, v in d.items()
                         if k in DesignSpec.__dataclass_fields__})


def _options_to_dict(options: AnalysisOptions) -> Dict[str, Any]:
    return asdict(options)


def _options_from_dict(d: Dict[str, Any]) -> AnalysisOptions:
    field_names = set(AnalysisOptions.__dataclass_fields__)
    return AnalysisOptions(**{k: v for k, v in d.items() if k in field_names})


def build_repro_config(data: Dict[str, Any], data_kind: str, design: DesignSpec,
                       options: AnalysisOptions, result: AnalysisResult
                       ) -> Dict[str, Any]:
    """Assemble a self-contained reproduction config.

    ``data`` is the raw dict ({label: [values]}) for RAW, or the summary dict
    ({label: {mean, sd, n}}) for SUMMARY.
    """
    return {
        "statlab_repro_config": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "program_version": result.program_version,
        "core_version": result.core_version,
        "python_version": result.python_version,
        "data_kind": data_kind,
        "data": data,
        "data_hash": result.data_hash,
        "design": _design_to_dict(design),
        "options": _options_to_dict(options),
        "analysis_id": result.analysis_id,
    }


def save_repro_config(config: Dict[str, Any], path: str) -> str:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    return path


def load_repro_config(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
