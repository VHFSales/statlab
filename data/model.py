"""Project / Experiment / Variable data model (FR-1, FR-2, FR-10).

Pure stdlib dataclasses. Domain-neutral: no hardcoded scientific fields. Metadata
is a generic list of (field, value) and never affects the analysis (FR-2.2).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional


def _uid() -> str:
    return uuid.uuid4().hex


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class MetadataField:
    field: str
    value: str


@dataclass
class DesignSpec:
    """User-declared design (mirrors decision_engine.DesignSpec, serializable)."""
    n_response_vars: int = 1
    n_factors: int = 1
    independent_groups: bool = True
    repeated_measures: bool = False
    paired: bool = False
    blocks: bool = False
    multiple_obs_per_unit: bool = False
    independent_units_asserted: bool = True


@dataclass
class Variable:
    """A single response variable within an experiment."""
    name: str
    unit: str = ""                       # free text, display only
    data_kind: str = "RAW"               # "RAW" | "SUMMARY"
    # RAW: mapping label -> list of values (float or None for missing)
    raw: Dict[str, List[Optional[float]]] = field(default_factory=dict)
    # SUMMARY: mapping label -> {"mean":..., "sd":..., "n":...}
    summary: Dict[str, Dict[str, float]] = field(default_factory=dict)
    id: str = field(default_factory=_uid)

    def group_labels(self) -> List[str]:
        return list(self.raw.keys()) if self.data_kind == "RAW" else list(self.summary.keys())


@dataclass
class Experiment:
    name: str
    notes: str = ""
    design: DesignSpec = field(default_factory=DesignSpec)
    variables: List[Variable] = field(default_factory=list)
    id: str = field(default_factory=_uid)


@dataclass
class Project:
    name: str
    description: str = ""
    researcher: str = ""
    lab: str = ""
    notes: str = ""
    created_at: str = field(default_factory=_now)
    metadata: List[MetadataField] = field(default_factory=list)
    experiments: List[Experiment] = field(default_factory=list)
    id: str = field(default_factory=_uid)
