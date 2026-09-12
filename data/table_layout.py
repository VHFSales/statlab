"""Intelligent interpretation of scientific-table layouts after a document scan.

Real thesis/paper tables rarely arrive in the clean "one column per group, one
number per cell" shape the engine wants. This module recognizes the common patterns
and prepares the data, being explicit about what it inferred:

- ``mean ± sd`` cells (with optional grouping letters), e.g. ``61,4 ±1,3ᵇ`` or
  ``61.4(1.3)`` — recognized as SUMMARY data; mean and sd are separated, the
  grouping letter is captured for reference.
- multi-line headers (a spanning title over sub-columns like ``20° 60° 85°``) —
  merged into single, unique column labels.
- the label column (Amostra/Grupo) vs. measurement columns.
- overall table TYPE: raw-numeric, summary (mean±sd), or descriptive/text.

Nothing is fabricated: if a cell has no number, it stays missing; if ``n`` is not in
the table, the summary is returned without ``n`` (and the engine will ask for it).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from data.importer import parse_number, _norm, dedup_headers


# --------------------------------------------------------------------------- #
# 1) mean ± sd cell parsing
# --------------------------------------------------------------------------- #
# grouping letters that may trail a value (superscript unicode or plain a-z)
_SUPERSCRIPT = "\u1d43\u1d47\u1d9c\u1d48\u1d49"  # ᵃ ᵇ ᶜ ᵈ ᵉ (common ones)
_PM = ("\u00b1", "±", "+/-", "+-")


@dataclass
class MeanSD:
    mean: float
    sd: Optional[float] = None
    letter: str = ""          # grouping/CLD letter(s) found on the cell, if any


def parse_mean_sd(cell: str, decimal: str = "auto") -> Optional[MeanSD]:
    """Parse a 'mean ± sd' style cell. Returns None if no leading number is found.

    Accepts: '61,4 ± 1,3', '61.4±1.3', '61,4 (1,3)', '61,4 1,3b', '61,4ᵇ',
    plain '61,4'. Trailing grouping letters (ᵃᵇᶜ or a-z) are captured separately.
    """
    if cell is None:
        return None
    s = str(cell).strip()
    if s == "":
        return None

    # normalize the ± token
    pm_norm = s
    for pm in _PM:
        pm_norm = pm_norm.replace(pm, "±")

    # capture a trailing letter group (superscript or plain), e.g. "b", "ab", "ᵇ"
    letter = ""
    m_letter = re.search(r"([" + _SUPERSCRIPT + r"]+|[a-zA-Z]{1,3})\s*$", pm_norm)
    # only treat as a letter if what precedes it is a number (avoid words)
    if m_letter and re.search(r"\d", pm_norm[:m_letter.start()]):
        letter = m_letter.group(1)
        core = pm_norm[:m_letter.start()].strip()
    else:
        core = pm_norm

    mean = None
    sd = None
    if "±" in core:
        left, right = core.split("±", 1)
        mean = parse_number(left, decimal)
        sd = parse_number(right, decimal)
    else:
        # try "mean (sd)"
        mparen = re.match(r"^\s*([-+]?[\d.,]+)\s*\(\s*([-+]?[\d.,]+)\s*\)\s*$", core)
        if mparen:
            mean = parse_number(mparen.group(1), decimal)
            sd = parse_number(mparen.group(2), decimal)
        else:
            # try "mean sd" separated by whitespace (two numbers)
            nums = re.findall(r"[-+]?[\d.,]+", core)
            if len(nums) >= 2:
                mean = parse_number(nums[0], decimal)
                sd = parse_number(nums[1], decimal)
            elif len(nums) == 1:
                mean = parse_number(nums[0], decimal)

    if mean is None:
        return None
    # map superscript letters to plain a-z for readability
    if letter:
        table = {c: chr(ord('a') + i) for i, c in enumerate(_SUPERSCRIPT)}
        letter = "".join(table.get(ch, ch) for ch in letter).lower()
    return MeanSD(mean=mean, sd=sd, letter=letter)


def cell_looks_mean_sd(cell: str) -> bool:
    """True if the cell carries an explicit ± / (sd) / letter that marks it as a
    summary cell (not just a bare number)."""
    s = str(cell)
    if any(pm in s for pm in _PM):
        return True
    if re.search(r"\d\s*\(\s*[\d.,]+\s*\)", s):
        return True
    # a number immediately followed by a grouping superscript
    if re.search(r"\d\s*[" + _SUPERSCRIPT + r"]", s):
        return True
    return False



# --------------------------------------------------------------------------- #
# 2) multi-line headers and the label column
# --------------------------------------------------------------------------- #
def _row_numeric_fraction(row: List[str]) -> float:
    cells = [c for c in row if str(c).strip() != ""]
    if not cells:
        return 0.0
    num = sum(1 for c in cells if parse_mean_sd(c) is not None)
    return num / len(cells)


def _looks_data_row(row: List[str]) -> bool:
    """A data row: a non-empty first cell (the label) followed by mostly numeric
    cells. A sub-header row (e.g. ['', '20', '60', '85']) has an empty first cell
    and is NOT a data row even though the rest are numbers."""
    if not row:
        return False
    first = str(row[0]).strip()
    rest = row[1:]
    rest_frac = _row_numeric_fraction(rest) if rest else 0.0
    # an empty first cell signals a spanning sub-header (e.g. ['', '20', '60'])
    # rather than a data row, even if the rest are numbers.
    if first == "":
        return False
    # label present + numeric body -> data
    if parse_mean_sd(first) is None and rest_frac >= 0.5:
        return True
    # whole row numeric (no label column) -> data
    if _row_numeric_fraction(row) >= 0.6:
        return True
    return False


def detect_header_rows(rows: List[List[str]], max_header: int = 4) -> int:
    """Return how many leading rows are header (non-data) rows.

    Stops at the first row that looks like a data row (a label followed by numbers,
    or an all-numeric row). This correctly treats a numeric sub-header like
    ['', '20', '60', '85'] as header, not data. Capped for safety.
    """
    n = 0
    for r in rows[:max_header]:
        if _looks_data_row(r):
            break
        n += 1
    if n >= len(rows):
        n = 1
    return max(1, n)


def merge_header_rows(header_rows: List[List[str]]) -> List[str]:
    """Merge several header rows into one label per column.

    A spanning title in an upper row (a cell followed by blanks) is propagated
    across the columns it spans, then joined with the lower sub-labels:
    e.g. ["Brilho antes", "", ""] over ["20", "60", "85"] ->
    ["Brilho antes 20", "Brilho antes 60", "Brilho antes 85"].
    """
    if not header_rows:
        return []
    width = max(len(r) for r in header_rows)
    # forward-fill blanks in each header row (spanning titles)
    filled = []
    for r in header_rows:
        r = list(r) + [""] * (width - len(r))
        last = ""
        ff = []
        for c in r:
            c = str(c).strip()
            if c == "":
                ff.append(last)
            else:
                ff.append(c)
                last = c
        filled.append(ff)
    labels = []
    for j in range(width):
        parts = []
        for r in filled:
            piece = r[j].strip()
            if piece and (not parts or parts[-1] != piece):
                parts.append(piece)
        labels.append(" ".join(parts).strip())
    return dedup_headers(labels)


# label-column name hints (normalized)
_LABEL_HINTS = {"amostra", "amostras", "grupo", "grupos", "tratamento",
                "tratamentos", "sample", "samples", "group", "groups",
                "condicao", "material", "id", "codigo", "especime", "corpodeprova"}


def detect_label_column(rows: List[List[str]], n_header: int) -> Optional[int]:
    """Find the column of row labels (Amostra/Grupo): a column whose header matches
    a known hint, or (fallback) the first column if it is mostly non-numeric while
    the rest are numeric."""
    if not rows:
        return None
    header_labels = merge_header_rows(rows[:n_header])
    for i, h in enumerate(header_labels):
        if _norm(h) in _LABEL_HINTS:
            return i
    # fallback: first column mostly text, remaining columns mostly numeric
    body = rows[n_header:]
    if not body:
        return None
    def col_numeric_frac(j):
        vals = [r[j] for r in body if j < len(r) and str(r[j]).strip() != ""]
        if not vals:
            return 0.0
        return sum(1 for v in vals if parse_mean_sd(v) is not None) / len(vals)
    first_frac = col_numeric_frac(0)
    other_fracs = [col_numeric_frac(j) for j in range(1, len(header_labels))]
    if first_frac < 0.34 and other_fracs and \
       (sum(other_fracs) / len(other_fracs)) >= 0.5:
        return 0
    return None



# --------------------------------------------------------------------------- #
# 3) table-type classification and interpretation
# --------------------------------------------------------------------------- #
@dataclass
class InterpretedTable:
    kind: str                       # "summary" | "raw" | "descriptive"
    n_header_rows: int
    label_col: Optional[int]
    column_labels: List[str]        # merged, unique headers
    # For summary tables in the "sample x condition" layout, one summary dict per
    # measurement column: {column_label: {sample: {mean, sd[, letter]}}}
    summary_by_column: Dict[str, Dict[str, Dict[str, float]]] = field(
        default_factory=dict)
    grouping_letters: Dict[str, Dict[str, str]] = field(default_factory=dict)
    # For raw tables: {group_label: [values]}
    raw: Dict[str, List[Optional[float]]] = field(default_factory=dict)
    messages: List[str] = field(default_factory=list)
    measurement_columns: List[str] = field(default_factory=list)


def _cell_kind_stats(body: List[List[str]], label_col: Optional[int]):
    """Count, over the measurement cells, how many are mean±sd, plain-number, or
    non-numeric. Returns (n_meansd, n_number, n_text, total)."""
    n_meansd = n_number = n_text = 0
    for r in body:
        for j, c in enumerate(r):
            if label_col is not None and j == label_col:
                continue
            s = str(c).strip()
            if s == "":
                continue
            ms = parse_mean_sd(c)
            if ms is None:
                n_text += 1
            elif ms.sd is not None or cell_looks_mean_sd(c):
                n_meansd += 1
            else:
                n_number += 1
    total = n_meansd + n_number + n_text
    return n_meansd, n_number, n_text, total


def classify_table(rows: List[List[str]]) -> str:
    """Classify a table as 'summary' (mean±sd), 'raw' (plain numbers), or
    'descriptive' (mostly text)."""
    if not rows:
        return "descriptive"
    n_header = detect_header_rows(rows)
    label_col = detect_label_column(rows, n_header)
    body = rows[n_header:]
    n_meansd, n_number, n_text, total = _cell_kind_stats(body, label_col)
    if total == 0:
        return "descriptive"
    if n_text / total > 0.5:
        return "descriptive"
    if n_meansd >= max(1, 0.4 * (n_meansd + n_number)):
        return "summary"
    return "raw"


def interpret_table(rows: List[List[str]], decimal: str = "auto",
                    default_n: Optional[int] = None) -> InterpretedTable:
    """Interpret a scanned table: detect header/label layout, classify the type,
    and prepare the data. Nothing is fabricated (missing stays missing; ``n`` is
    only set if provided via ``default_n`` or present in a column)."""
    n_header = detect_header_rows(rows)
    labels = merge_header_rows(rows[:n_header])
    label_col = detect_label_column(rows, n_header)
    body = rows[n_header:]
    kind = classify_table(rows)

    result = InterpretedTable(kind=kind, n_header_rows=n_header,
                              label_col=label_col, column_labels=labels)

    if kind == "descriptive":
        result.messages.append(
            "Esta tabela parece descritiva (majoritariamente texto), não uma tabela "
            "de dados numéricos. Selecione outra tabela do documento.")
        return result

    meas_cols = [j for j in range(len(labels)) if j != label_col]
    result.measurement_columns = [labels[j] for j in meas_cols]

    if kind == "summary":
        # sample x condition layout: one summary per measurement column
        for j in meas_cols:
            col_label = labels[j]
            summ: Dict[str, Dict[str, float]] = {}
            letters: Dict[str, str] = {}
            for ri, r in enumerate(body):
                sample = (str(r[label_col]).strip() if label_col is not None
                          and label_col < len(r) else f"linha {ri+1}")
                if sample == "":
                    continue
                ms = parse_mean_sd(r[j]) if j < len(r) else None
                if ms is None:
                    continue
                entry: Dict[str, float] = {"mean": ms.mean}
                if ms.sd is not None:
                    entry["sd"] = ms.sd
                if default_n is not None:
                    entry["n"] = int(default_n)
                # de-dup sample labels within a column
                if sample in summ:
                    k = 2
                    while f"{sample} ({k})" in summ:
                        k += 1
                    sample = f"{sample} ({k})"
                summ[sample] = entry
                if ms.letter:
                    letters[sample] = ms.letter
            if summ:
                result.summary_by_column[col_label] = summ
                if letters:
                    result.grouping_letters[col_label] = letters
        msg = ("Tabela de estatísticas resumidas (média ± DP) no formato "
               "amostra × condição. Cada coluna de medida é uma comparação entre as "
               "amostras.")
        if default_n is None:
            msg += (" Informe o tamanho amostral (n) — não consta na tabela — para "
                    "habilitar ANOVA/Tukey.")
        result.messages.append(msg)
        if result.grouping_letters:
            result.messages.append(
                "Letras de agrupamento (ex.: teste de Tukey já realizado no trabalho "
                "original) foram detectadas e preservadas para conferência.")
        return result

    # kind == "raw": build {column_label: [values]} treating each measurement
    # column as a group. If there is a label column, values come from that column's
    # rows; otherwise the whole table is wide raw.
    if label_col is None:
        # wide: each column is a group
        raw: Dict[str, List[Optional[float]]] = {labels[j]: [] for j in meas_cols}
        for r in body:
            for j in meas_cols:
                ms = parse_mean_sd(r[j]) if j < len(r) else None
                raw[labels[j]].append(ms.mean if ms else None)
        result.raw = raw
        result.messages.append("Tabela de dados brutos (uma coluna por grupo).")
    else:
        # sample x condition of plain numbers -> each column is a comparison of
        # samples with a single value each (rarely enough for analysis); expose it
        # like the summary layout but as raw single values per sample.
        raw = {}
        for j in meas_cols:
            col_vals = []
            for r in body:
                ms = parse_mean_sd(r[j]) if j < len(r) else None
                col_vals.append(ms.mean if ms else None)
            raw[labels[j]] = col_vals
        result.raw = raw
        result.messages.append(
            "Tabela numérica no formato amostra × condição (um valor por célula). "
            "Cada coluna vira um grupo com um valor por amostra.")
    return result
