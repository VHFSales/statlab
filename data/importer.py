"""Data import (FR-4). Reads pasted text, CSV, Excel, PDF and Word into a table of
strings, then into the wide/long "raw" structure the engine uses.

Design goals:
- Never silently reinterpret columns: callers show a preview and confirm (FR-4.3).
- Handle the common Brazilian/European decimal comma (``50,1``) as well as the
  dot decimal (``50.1``) — this is auto-detected per column.
- Degrade gracefully: text/CSV work with the stdlib alone; Excel needs pandas/
  openpyxl, PDF needs pdfplumber (or a text fallback), Word needs python-docx.
  When a reader is missing, a clear message tells the user what to install.
"""

from __future__ import annotations

import csv
import io
import math
import os
import re
from typing import Dict, List, Optional, Tuple

try:
    import pandas as pd
    HAVE_PANDAS = True
except Exception:
    HAVE_PANDAS = False


# --------------------------------------------------------------------------- #
# Number parsing (dot / comma decimal aware)
# --------------------------------------------------------------------------- #
def _is_number_dot(s: str) -> bool:
    try:
        float(s)
        return True
    except (TypeError, ValueError):
        return False


def _clean_numeric_token(s: str) -> str:
    """Strip common noise from a cell before numeric parsing.

    Removes surrounding whitespace, thousands separators used as spaces, a trailing
    superscript/letter group (e.g. the CLD letters in ``61,4b``), and the ``± x``
    part of a ``mean ± sd`` cell (keeping only the mean). Returns the raw token to
    be interpreted by ``parse_number`` with the chosen decimal.
    """
    s = str(s).strip()
    # drop a "± sd" tail if present (keep the value before ±)
    for pm in ("±", "\u00b1", "+/-", "+-"):
        if pm in s:
            s = s.split(pm)[0].strip()
            break
    # drop trailing letters/superscripts attached to a number (e.g. 61,4b or 92,3ab)
    m = re.match(r"^[-+]?[\d\.,\s]+", s)
    if m:
        s = m.group(0).strip()
    return s


def parse_number(s: str, decimal: str = "auto") -> Optional[float]:
    """Parse a single cell to float, honoring the decimal convention.

    decimal: "dot", "comma", or "auto". Returns None if not numeric.
    """
    if s is None:
        return None
    tok = _clean_numeric_token(s)
    if tok == "":
        return None
    if decimal == "comma":
        tok = tok.replace(".", "").replace(",", ".")
    elif decimal == "dot":
        tok = tok.replace(",", "")
    else:  # auto: decide by which separator looks like the decimal
        has_comma = "," in tok
        has_dot = "." in tok
        if has_comma and has_dot:
            # the rightmost separator is the decimal; the other groups thousands
            if tok.rfind(",") > tok.rfind("."):
                tok = tok.replace(".", "").replace(",", ".")
            else:
                tok = tok.replace(",", "")
        elif has_comma:
            # comma-only: treat as decimal (Brazilian) unless it looks like a
            # thousands grouping (e.g. "1,000" with exactly 3 trailing digits AND
            # no other cue). We default to decimal, the common lab case.
            tok = tok.replace(",", ".")
        # dot-only or no separator: leave as-is
    try:
        return float(tok)
    except (TypeError, ValueError):
        return None


def detect_decimal(rows: List[List[str]]) -> str:
    """Guess whether the table uses comma or dot as the decimal separator.

    Looks at all cells: if commas appear as decimals more often than dots, returns
    "comma"; otherwise "dot". Defaults to "dot" when ambiguous.
    """
    comma_dec = 0
    dot_dec = 0
    for r in rows[1:] if len(rows) > 1 else rows:
        for cell in r:
            tok = _clean_numeric_token(cell)
            if not tok:
                continue
            has_c, has_d = "," in tok, "." in tok
            if has_c and has_d:
                if tok.rfind(",") > tok.rfind("."):
                    comma_dec += 1
                else:
                    dot_dec += 1
            elif has_c:
                # a lone comma with 1-2 trailing digits is almost surely a decimal
                if re.search(r",\d{1,2}\b", tok):
                    comma_dec += 1
            elif has_d:
                if re.search(r"\.\d{1,}\b", tok):
                    dot_dec += 1
    return "comma" if comma_dec > dot_dec else "dot"


# --------------------------------------------------------------------------- #
# Text / CSV parsing
# --------------------------------------------------------------------------- #
def _looks_comma_decimal(text: str) -> bool:
    """True if the text uses comma as the DECIMAL separator (so comma must NOT be
    used as the column delimiter).

    Only returns True when the evidence is strong AND there is no dot-decimal in
    play: if numbers already use a dot decimal (e.g. ``10.2``), any comma is a
    column separator, so we return False. We also require the comma-decimal pattern
    to appear on more than one line, to avoid misreading a single ``group,value``
    row as a decimal.
    """
    # dot used as a decimal anywhere? then commas are separators.
    if re.search(r"\d\.\d", text):
        return False
    lines = text.splitlines()
    if not lines:
        return False
    # Header cue: if the first line separates NON-numeric labels with commas
    # (e.g. "A,B,C" or "Grupo,Valor"), the comma is the column delimiter.
    header = lines[0]
    if "," in header:
        header_cells = [c.strip() for c in header.split(",")]
        non_numeric = [c for c in header_cells if c and parse_number(c) is None]
        if len(non_numeric) >= 2 or (len(header_cells) >= 2 and
                                     all(parse_number(c) is None
                                         for c in header_cells if c)):
            return False
    dec_commas = len(re.findall(r"\d,\d", text))
    if dec_commas == 0:
        return False
    # require the pattern on at least 2 body lines (a real numeric table)
    lines_with = sum(1 for ln in lines[1:] if re.search(r"\d,\d", ln))
    return lines_with >= 2


def parse_delimited_text(text: str) -> List[List[str]]:
    """Parse pasted text into rows of strings. Detects tab / semicolon / pipe /
    comma delimiters. When the decimal separator looks like a comma, the comma is
    NOT used as a column delimiter (ambiguity guard)."""
    text = text.strip("\n")
    if not text:
        return []
    first = text.splitlines()[0]
    comma_decimal = _looks_comma_decimal(text)
    if "\t" in first:
        delim = "\t"
    elif "|" in first:
        delim = "|"
    elif ";" in first:
        delim = ";"
    elif "," in first and not comma_decimal:
        delim = ","
    else:
        # only comma present but it is the decimal separator -> fall back to
        # whitespace as the column delimiter so we don't split "10,2" into "10","2"
        delim = None
    rows = []
    if delim is None:
        for line in text.splitlines():
            parts = re.split(r"\s{2,}|\t", line.strip())
            cleaned = [p.strip().strip("*").strip() for p in parts if p.strip()]
            if cleaned:
                rows.append(cleaned)
        return rows
    for row in csv.reader(io.StringIO(text), delimiter=delim):
        cleaned = [c.strip().strip("*").strip() for c in row]
        # Only for pipe-delimited tables (e.g. "| a | b |"): drop the empty leading/
        # trailing cells the surrounding pipes create. For other delimiters, an
        # empty cell is a real missing value and must be preserved.
        if delim == "|":
            while cleaned and cleaned[0] == "":
                cleaned.pop(0)
            while cleaned and cleaned[-1] == "":
                cleaned.pop()
        if any(c != "" for c in cleaned):
            rows.append(cleaned)
    return rows


def detect_format(rows: List[List[str]]) -> str:
    """Return 'long' or 'wide' (best-effort). 'long' = 2 cols, one non-numeric."""
    if not rows:
        return "unknown"
    header = rows[0]
    body = rows[1:]
    if len(header) == 2:
        non_num_first = sum(1 for r in body if r and parse_number(r[0]) is None)
        num_second = sum(1 for r in body
                         if len(r) > 1 and parse_number(r[1]) is not None)
        if body and non_num_first >= len(body) * 0.5 \
           and num_second >= len(body) * 0.5:
            return "long"
    return "wide"


def to_raw_wide(rows: List[List[str]], decimal: str = "auto"
                ) -> Dict[str, List[Optional[float]]]:
    header = rows[0]
    data: Dict[str, List[Optional[float]]] = {h.strip(): [] for h in header}
    for r in rows[1:]:
        for i, h in enumerate(header):
            cell = r[i] if i < len(r) else ""
            data[h.strip()].append(parse_number(cell, decimal))
    return data


def to_raw_long(rows: List[List[str]], decimal: str = "auto"
                ) -> Dict[str, List[Optional[float]]]:
    data: Dict[str, List[Optional[float]]] = {}
    for r in rows[1:]:
        if len(r) < 2:
            continue
        lab = r[0].strip()
        data.setdefault(lab, []).append(parse_number(r[1], decimal))
    return data


def rows_to_raw(rows: List[List[str]], fmt: Optional[str] = None,
                decimal: str = "auto"
                ) -> Tuple[Dict[str, List[Optional[float]]], str, str]:
    """Convert a table of strings into the raw dict. Returns (raw, format, decimal)."""
    if decimal == "auto":
        decimal = detect_decimal(rows)
    used = fmt or detect_format(rows)
    if used == "long":
        return to_raw_long(rows, decimal), "long", decimal
    return to_raw_wide(rows, decimal), "wide", decimal


def import_text(text: str, fmt: Optional[str] = None, decimal: str = "auto"
                ) -> Tuple[Dict[str, List[Optional[float]]], str]:
    """Import pasted/CSV text; returns (raw dict, detected/used format).

    Kept backward-compatible (2-tuple return). Decimal is auto-detected by default.
    """
    rows = parse_delimited_text(text)
    raw, used, _dec = rows_to_raw(rows, fmt, decimal)
    return raw, used


# --------------------------------------------------------------------------- #
# File readers -> table of strings
# --------------------------------------------------------------------------- #
class UnsupportedFile(RuntimeError):
    pass


class MissingReader(RuntimeError):
    pass


def _df_to_rows(df) -> List[List[str]]:
    header = [str(c) for c in df.columns]
    rows = [header]
    for _, r in df.iterrows():
        rows.append(["" if pd.isna(v) else str(v) for v in r.tolist()])
    return rows


def read_excel_bytes(data: bytes, filename: str = "") -> List[List[str]]:
    if not HAVE_PANDAS:
        raise MissingReader(
            "Leitura de Excel requer pandas + openpyxl. Instale com: "
            "pip install pandas openpyxl")
    bio = io.BytesIO(data)
    engine = "openpyxl" if filename.lower().endswith("xlsx") else None
    try:
        df = pd.read_excel(bio, engine=engine)
    except Exception as exc:
        raise MissingReader(
            "Não foi possível ler o Excel. Para .xlsx instale openpyxl; para .xls "
            "instale xlrd. Detalhe: " + str(exc))
    return _df_to_rows(df)


def read_csv_bytes(data: bytes, filename: str = "") -> List[List[str]]:
    text = data.decode("utf-8-sig", errors="replace")
    return parse_delimited_text(text)


def read_pdf_bytes(data: bytes, filename: str = "") -> List[List[str]]:
    """Extract the first usable table from a PDF.

    Prefers pdfplumber (real table extraction). Falls back to a whitespace/line
    heuristic on extracted text. Raises MissingReader if no PDF reader is available.
    """
    try:
        import pdfplumber
    except Exception:
        pdfplumber = None

    if pdfplumber is not None:
        rows: List[List[str]] = []
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for page in pdf.pages:
                for table in page.extract_tables() or []:
                    for row in table:
                        cleaned = [("" if c is None else str(c).strip())
                                   for c in row]
                        if any(cleaned):
                            rows.append(cleaned)
                    if rows:
                        return rows
                # if no ruled table, try text lines
                if not rows:
                    txt = page.extract_text() or ""
                    for line in txt.splitlines():
                        parts = re.split(r"\s{2,}|\t", line.strip())
                        if len(parts) >= 2:
                            rows.append([p.strip() for p in parts])
                    if rows:
                        return rows
        if rows:
            return rows
        raise UnsupportedFile(
            "Nenhuma tabela reconhecível foi encontrada no PDF. Copie os dados "
            "manualmente ou exporte a tabela como CSV/Excel.")
    raise MissingReader(
        "Leitura de PDF requer o pacote pdfplumber. Instale com: "
        "pip install pdfplumber — ou exporte a tabela como CSV/Excel.")


def read_docx_bytes(data: bytes, filename: str = "") -> List[List[str]]:
    """Extract the first table from a Word .docx. Requires python-docx."""
    try:
        import docx  # python-docx
    except Exception:
        raise MissingReader(
            "Leitura de Word (.docx) requer o pacote python-docx. Instale com: "
            "pip install python-docx — ou cole a tabela / exporte como CSV/Excel.")
    document = docx.Document(io.BytesIO(data))
    if not document.tables:
        # fall back to paragraphs as delimited text
        text = "\n".join(p.text for p in document.paragraphs if p.text.strip())
        rows = parse_delimited_text(text)
        if rows:
            return rows
        raise UnsupportedFile(
            "Nenhuma tabela encontrada no documento Word. Cole os dados ou exporte "
            "como CSV/Excel.")
    table = document.tables[0]
    rows = []
    for row in table.rows:
        cells = [c.text.strip() for c in row.cells]
        if any(cells):
            rows.append(cells)
    return rows


def read_uploaded_file(data: bytes, filename: str) -> List[List[str]]:
    """Dispatch by extension: returns a table of strings (header + body rows)."""
    name = (filename or "").lower()
    if name.endswith((".xlsx", ".xls")):
        return read_excel_bytes(data, name)
    if name.endswith(".csv") or name.endswith(".txt") or name.endswith(".tsv"):
        return read_csv_bytes(data, name)
    if name.endswith(".pdf"):
        return read_pdf_bytes(data, name)
    if name.endswith(".docx"):
        return read_docx_bytes(data, name)
    raise UnsupportedFile(
        f"Tipo de arquivo não suportado: {filename}. Use .xlsx, .xls, .csv, .pdf "
        "ou .docx.")


def import_file(data: bytes, filename: str, fmt: Optional[str] = None,
                decimal: str = "auto"
                ) -> Tuple[Dict[str, List[Optional[float]]], str, str, List[List[str]]]:
    """Read an uploaded file and convert to raw data.

    Returns (raw, format, decimal, rows) — ``rows`` is the parsed table (for preview).
    """
    rows = read_uploaded_file(data, filename)
    raw, used, dec = rows_to_raw(rows, fmt, decimal)
    return raw, used, dec, rows


# --------------------------------------------------------------------------- #
# Legacy helpers (kept for compatibility with existing callers/tests)
# --------------------------------------------------------------------------- #
def _is_number(s: str) -> bool:
    return _is_number_dot(s)


def _num(v):
    try:
        float(v)
        return True
    except (TypeError, ValueError):
        return False


def import_dataframe(df, fmt: str = "wide", group_col: str = None,
                     value_col: str = None) -> Dict[str, List[Optional[float]]]:
    if not HAVE_PANDAS:
        raise RuntimeError("pandas não está instalado neste ambiente.")
    if fmt == "long":
        gc = group_col or df.columns[0]
        vc = value_col or df.columns[1]
        out: Dict[str, List[Optional[float]]] = {}
        for _, row in df.iterrows():
            lab = str(row[gc])
            v = row[vc]
            out.setdefault(lab, []).append(None if pd.isna(v) else float(v))
        return out
    out = {}
    for col in df.columns:
        vals = []
        for v in df[col]:
            vals.append(None if pd.isna(v) else (float(v) if _num(v) else None))
        out[str(col)] = vals
    return out


def read_file(path: str) -> "pd.DataFrame":
    """Read .xlsx/.xls/.csv into a DataFrame (requires pandas; xls best-effort)."""
    if not HAVE_PANDAS:
        raise RuntimeError(
            "pandas não está instalado; use colar dados ou CSV via import_text.")
    if path.lower().endswith((".xlsx",)):
        return pd.read_excel(path, engine="openpyxl")
    if path.lower().endswith(".xls"):
        return pd.read_excel(path)
    return pd.read_csv(path)
