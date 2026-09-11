"""Workspace: a persistable bundle of a project, its analysis results, and
labelled snapshots, with staleness detection (FR-19.4, spec 94/95).

A Workspace ties each stored AnalysisResult to the data it was computed from (via
data_hash). When the current data hash differs, the stored result is stale and must
be recomputed before final export.

Pure stdlib, JSON. Snapshots capture the full workspace state under a label so a
researcher can compare "original", "após correção", "após exclusão justificada".
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.orchestrator import AnalysisResult
from persistence.result_store import result_from_dict, result_to_dict


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class StoredResult:
    """An AnalysisResult plus the key it is filed under and its staleness flag."""
    key: str                 # e.g. experiment/variable identifier
    result_dict: Dict[str, Any]
    stale: bool = False


@dataclass
class Snapshot:
    label: str
    timestamp: str
    project: Dict[str, Any]
    results: List[Dict[str, Any]] = field(default_factory=list)


class Workspace:
    """In-memory workspace with JSON persistence."""

    def __init__(self, project: Optional[Dict[str, Any]] = None):
        self.project: Dict[str, Any] = project or {}
        self.results: Dict[str, StoredResult] = {}
        self.snapshots: List[Snapshot] = []

    # --- results ---------------------------------------------------------- #
    def store_result(self, key: str, result: AnalysisResult) -> None:
        self.results[key] = StoredResult(key=key,
                                         result_dict=result_to_dict(result),
                                         stale=False)

    def get_result(self, key: str) -> Optional[AnalysisResult]:
        sr = self.results.get(key)
        return result_from_dict(sr.result_dict) if sr else None

    def mark_stale_by_data_hash(self, key: str, current_data_hash: str) -> bool:
        """If the stored result's data_hash != current hash, mark it stale.

        Returns the resulting staleness flag. Never keeps a silently outdated
        result: callers must recompute before final export (FR-19.4).
        """
        sr = self.results.get(key)
        if not sr:
            return False
        stored_hash = sr.result_dict.get("data_hash")
        sr.stale = (stored_hash != current_data_hash)
        return sr.stale

    def stale_keys(self) -> List[str]:
        return [k for k, sr in self.results.items() if sr.stale]

    # --- snapshots -------------------------------------------------------- #
    def take_snapshot(self, label: str) -> Snapshot:
        snap = Snapshot(
            label=label, timestamp=_now(),
            project=dict(self.project),
            results=[dict(sr.result_dict) for sr in self.results.values()],
        )
        self.snapshots.append(snap)
        return snap

    # --- persistence ------------------------------------------------------ #
    def to_dict(self) -> Dict[str, Any]:
        return {
            "statlab_workspace": 1,
            "saved_at": _now(),
            "project": self.project,
            "results": [asdict(sr) for sr in self.results.values()],
            "snapshots": [asdict(s) for s in self.snapshots],
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Workspace":
        ws = cls(project=d.get("project", {}))
        for sr in d.get("results", []):
            ws.results[sr["key"]] = StoredResult(
                key=sr["key"], result_dict=sr["result_dict"],
                stale=sr.get("stale", False))
        for s in d.get("snapshots", []):
            ws.snapshots.append(Snapshot(
                label=s["label"], timestamp=s["timestamp"],
                project=s.get("project", {}), results=s.get("results", [])))
        return ws

    def save(self, path: str) -> str:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
        return path

    @classmethod
    def load(cls, path: str) -> "Workspace":
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))
