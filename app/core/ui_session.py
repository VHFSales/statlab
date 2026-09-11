"""UI session <-> workspace serialization (FR-1.4, FR-65 save/reopen).

Pure functions (no Streamlit) so they are unit-testable. They convert the pieces of
UI state that must persist — project metadata, the current dataset (raw or summary),
the declared design, and the last AnalysisResult — into a single JSON-serializable
workspace, and back. Built on persistence.workspace.Workspace.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.core.orchestrator import AnalysisResult
from persistence.result_store import result_from_dict, result_to_dict
from persistence.workspace import Workspace


WORKSPACE_KIND = "statlab_ui_workspace_v1"


def build_workspace_dict(project: Dict[str, Any], data_kind: str,
                         data: Optional[Dict], design: Dict[str, Any],
                         result: Optional[AnalysisResult]) -> Dict[str, Any]:
    """Serialize the UI session into a workspace dict (for download)."""
    ws = Workspace(project=project)
    if result is not None:
        ws.store_result("current", result)
    d = ws.to_dict()
    d["ui"] = {
        "kind": WORKSPACE_KIND,
        "data_kind": data_kind,
        "data": data,
        "design": design,
    }
    return d


def restore_from_workspace_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    """Restore UI session pieces from a workspace dict (from upload).

    Returns a dict with keys: project, data_kind, data, design, result
    (result is an AnalysisResult or None). Tolerant of missing sections.
    """
    ui = d.get("ui", {})
    project = d.get("project", {}) or {}
    result = None
    for sr in d.get("results", []):
        if sr.get("key") == "current" and sr.get("result_dict"):
            result = result_from_dict(sr["result_dict"])
            break
    return {
        "project": project,
        "data_kind": ui.get("data_kind", "RAW"),
        "data": ui.get("data"),
        "design": ui.get("design", {}),
        "result": result,
    }
