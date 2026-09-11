"""Project persistence (FR-1.4, FR-19). JSON only - no Excel dependency (spec 98).

Saves/loads Project objects to human-readable JSON, computes data hashes for
staleness detection, and supports labelled snapshots (FR-1.5).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Dict

from data.model import (DesignSpec, Experiment, MetadataField, Project, Variable)


def project_to_dict(p: Project) -> Dict[str, Any]:
    return asdict(p)


def project_from_dict(d: Dict[str, Any]) -> Project:
    experiments = []
    for e in d.get("experiments", []):
        variables = [Variable(**v) for v in e.get("variables", [])]
        design = DesignSpec(**e.get("design", {})) if e.get("design") else DesignSpec()
        experiments.append(Experiment(
            name=e["name"], notes=e.get("notes", ""), design=design,
            variables=variables, id=e.get("id"),
        ))
    metadata = [MetadataField(**m) for m in d.get("metadata", [])]
    return Project(
        name=d["name"], description=d.get("description", ""),
        researcher=d.get("researcher", ""), lab=d.get("lab", ""),
        notes=d.get("notes", ""), created_at=d.get("created_at"),
        metadata=metadata, experiments=experiments, id=d.get("id"),
    )


def save_project(p: Project, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(project_to_dict(p), f, ensure_ascii=False, indent=2)


def load_project(path: str) -> Project:
    with open(path, "r", encoding="utf-8") as f:
        return project_from_dict(json.load(f))


def data_hash_of_variable(var: Variable) -> str:
    if var.data_kind == "RAW":
        canon = json.dumps({k: list(v) for k, v in var.raw.items()},
                           sort_keys=True, default=str)
    else:
        canon = json.dumps(var.summary, sort_keys=True, default=str)
    return hashlib.sha256(canon.encode()).hexdigest()


def make_snapshot(p: Project, label: str) -> Dict[str, Any]:
    return {
        "label": label,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "project": project_to_dict(p),
    }
