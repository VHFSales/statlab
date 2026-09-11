"""Data import (FR-4). Wide/long detection, paste-from-Excel, xlsx/csv.

Uses pandas when available (xlsx/robust parsing); always supports pasted/CSV text
via the stdlib. Never silently reinterprets columns: callers must show a preview
and confirm (FR-4.3).
"""

from __future__ import annotations

import csv
import io
import math
from typing import Dict, List, Optional, Tuple

try:
    import pandas as pd
    HAVE_PANDAS = True
except Exception:
    HAVE_PANDAS = False


def _is_number(s: str) -> bool:
    try:
        float(s)
        return True
    except (TypeError, ValueError):
        return False


def parse_delimited_text(text: str) -> List[List[str]]:
    """Parse pasted text (tab or comma delimited) into rows of strings."""
    text = text.strip("\n")
    if not text:
        return []
    delim = "\t" if "\t" in text.splitlines()[0] else ","
    return [row for row in csv.reader(io.StringIO(text), delimiter=delim)]


def detect_format(rows: List[List[str]]) -> str:
    """Return 'long' or 'wide' (best-effort). 'long' = 2 cols, one non-numeric."""
    if not rows:
        return "unknown"
    header = rows[0]
    body = rows[1:]
    if len(header) == 2:
        # long if first column mostly non-numeric labels, second numeric
        non_num_first = sum(1 for r in body if r and not _is_number(r[0]))
        num_second = sum(1 for r in body if len(r) > 1 and _is_number(r[1]))
        if non_num_first >= len(body) * 0.5 and num_second >= len(body) * 0.5:
            return "long"
    return "wide"


def to_raw_wide(rows: List[List[str]]) -> Dict[str, List[Optional[float]]]:
    header = rows[0]
    data: Dict[str, List[Optional[float]]] = {h.strip(): [] for h in header}
    for r in rows[1:]:
        for i, h in enumerate(header):
            cell = r[i].strip() if i < len(r) else ""
            data[h.strip()].append(float(cell) if _is_number(cell) else None)
    return data


def to_raw_long(rows: List[List[str]]) -> Dict[str, List[Optional[float]]]:
    data: Dict[str, List[Optional[float]]] = {}
    for r in rows[1:]:
        if len(r) < 2:
            continue
        lab = r[0].strip()
        val = r[1].strip()
        data.setdefault(lab, []).append(float(val) if _is_number(val) else None)
    return data


def import_text(text: str, fmt: Optional[str] = None
                ) -> Tuple[Dict[str, List[Optional[float]]], str]:
    """Import pasted/CSV text; returns (raw dict, detected/used format)."""
    rows = parse_delimited_text(text)
    used = fmt or detect_format(rows)
    if used == "long":
        return to_raw_long(rows), "long"
    return to_raw_wide(rows), "wide"


def import_dataframe(df, fmt: str = "wide", group_col: str = None,
                     value_col: str = None) -> Dict[str, List[Optional[float]]]:
    """Import a pandas DataFrame (requires pandas)."""
    if not HAVE_PANDAS:
        raise RuntimeError("pandas não está instalado neste ambiente.")
    if fmt == "long":
        gc = group_col or df.columns[0]
        vc = value_col or df.columns[1]
        out: Dict[str, List[Optional[float]]] = {}
        for _, row in df.iterrows():
            lab = str(row[gc])
            v = row[vc]
            out.setdefault(lab, []).append(
                None if pd.isna(v) else float(v))
        return out
    out = {}
    for col in df.columns:
        vals = []
        for v in df[col]:
            vals.append(None if pd.isna(v) else (float(v) if _num(v) else None))
        out[str(col)] = vals
    return out


def _num(v):
    try:
        float(v)
        return True
    except (TypeError, ValueError):
        return False


def read_file(path: str) -> "pd.DataFrame":
    """Read .xlsx/.xls/.csv into a DataFrame (requires pandas; xls best-effort)."""
    if not HAVE_PANDAS:
        raise RuntimeError(
            "pandas não está instalado; use colar dados ou CSV via import_text.")
    if path.lower().endswith((".xlsx",)):
        return pd.read_excel(path, engine="openpyxl")
    if path.lower().endswith(".xls"):
        return pd.read_excel(path)  # best-effort (xlrd if present)
    return pd.read_csv(path)
