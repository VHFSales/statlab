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

    # capture a trailing grouping/CLD letter group (superscript, or LOWERCASE a-z).
    # Tukey/CLD letters are lowercase (a, b, ab, ...); an uppercase trailing token
    # is almost always a UNIT (e.g. "600 W", "15 mJ") and must NOT be read as a
    # grouping letter. We also require the letter to sit tight against the number
    # (optionally with a ± sd in between) rather than after a space+word.
    letter = ""
    m_letter = re.search(r"([" + _SUPERSCRIPT + r"]+|[a-z]{1,3})\s*$", pm_norm)
    # only treat as a letter if what precedes it is a number AND the trailing token
    # is not separated by whitespace from that number (units like " W" have a space)
    if m_letter and re.search(r"\d", pm_norm[:m_letter.start()]):
        preceding = pm_norm[:m_letter.start()]
        is_superscript = any(ch in _SUPERSCRIPT for ch in m_letter.group(1))
        # a plain a-z letter counts as grouping only if glued to the number
        # (no space): "61,4 ±1,3b" ok; "600 W" would have a space -> unit, reject.
        glued = is_superscript or (preceding and preceding[-1:] not in (" ", "\t"))
        if glued:
            letter = m_letter.group(1)
            core = preceding.strip()
        else:
            core = pm_norm
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


# --------------------------------------------------------------------------- #
# derived / non-data rows (e.g. "Variação (%)", "Δ", "Redução %")
# --------------------------------------------------------------------------- #
# words that mark a row as a DERIVED quantity (a computed delta), not raw data.
_DERIVED_HINTS = ("variacao", "variação", "delta", "reducao", "redução",
                   "aumento", "diferenca", "diferença", "ganho", "change",
                   "reduction", "increase", "difference")


def _looks_percent_token(cell: str) -> bool:
    """True if a cell is essentially a percentage value like '45,8%' or '53 %'."""
    s = str(cell).strip()
    return bool(re.match(r"^[-+]?[\d.,]+\s*%$", s))


def row_is_derived(row: List[str]) -> bool:
    """True if a row holds a DERIVED quantity (variation/delta) rather than data.

    Recognized two ways: (a) a label cell whose text matches a derived-quantity
    hint (Variação, Δ, Redução...), or (b) a row whose numeric cells are ALL
    written as percentages (e.g. '45,8%'), which in before/after tables marks the
    computed change line. Such rows must never be loaded as observations.
    """
    if not row:
        return False
    joined = " ".join(str(c) for c in row)
    norm = _norm(joined)
    if any(h in norm for h in (_norm(x) for x in _DERIVED_HINTS)):
        return True
    if "\u0394" in joined or "%" == joined.strip():
        return True
    # all non-empty numeric-looking cells are percentages -> a variation row
    numeric_cells = [c for c in row if str(c).strip() != ""
                     and parse_mean_sd(c) is not None]
    if numeric_cells and all(_looks_percent_token(c) for c in numeric_cells):
        return True
    return False


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


# condition-column hints: a column of "before/after"-style labels that pairs with
# a spanning factor column (e.g. Potência 600/750/900 × Condição Sem/Com plasma).
_CONDITION_HINTS = {"condicao", "condição", "condition", "estado", "status",
                    "etapa", "fase", "tratamento", "treatment"}
_BEFORE_AFTER_TOKENS = ("sem", "com", "antes", "apos", "após", "before", "after",
                        "controle", "control", "pre", "pré", "pos", "pós",
                        "tratado", "nao tratado", "não tratado", "untreated",
                        "treated", "referencia", "referência", "reference")


def _column_values(rows: List[List[str]], j: int, n_header: int) -> List[str]:
    return [str(r[j]).strip() for r in rows[n_header:] if j < len(r)]


def detect_grouped_before_after(rows: List[List[str]], n_header: int
                                ) -> Optional[Tuple[int, int]]:
    """Detect the 'factor × condition (before/after)' layout.

    Returns ``(factor_col, condition_col)`` when the table has:
      - a FACTOR column that labels blocks (e.g. Potência: 600 W / 750 W / 900 W,
        often written once per block with blank cells under it), and
      - a CONDITION column of before/after-style labels (Sem plasma / Com plasma,
        Antes / Após, Controle / Tratado), whose values repeat across blocks.
    Otherwise returns None. This is the layout in many materials/engineering
    results tables, where each measurement cell is one paired observation.
    """
    if not rows:
        return None
    header = merge_header_rows(rows[:n_header])
    body = [r for r in rows[n_header:] if not row_is_derived(r)]
    if len(body) < 2:
        return None

    # find a condition column: header hint OR values dominated by before/after tokens
    cond_col = None
    for j in range(len(header)):
        if _norm(header[j]) in _CONDITION_HINTS:
            cond_col = j
            break
    if cond_col is None:
        for j in range(min(len(header), 3)):  # condition is an early column
            # values from body rows only, excluding derived (variation) rows
            vals = [str(r[j]).strip() for r in body if j < len(r)
                    and str(r[j]).strip() != ""]
            if not vals:
                continue
            hits = sum(1 for v in vals
                       if any(tok in _norm(v) for tok in
                              (_norm(t) for t in _BEFORE_AFTER_TOKENS)))
            if hits >= max(2, 0.6 * len(vals)):
                cond_col = j
                break
    if cond_col is None:
        return None

    # find the factor column: a different early, mostly-non-numeric column whose
    # values label blocks (may be sparse / forward-filled). Prefer a header hint.
    factor_col = None
    for j in range(len(header)):
        if j == cond_col:
            continue
        h = _norm(header[j])
        if h in {"potencia", "potência", "power", "fator", "factor", "nivel",
                 "nível", "grupo", "tratamento", "condicao_experimental"}:
            factor_col = j
            break
    if factor_col is None:
        # fallback: the first non-condition column that is mostly non-mean±sd text
        for j in range(min(len(header), 3)):
            if j == cond_col:
                continue
            vals = [str(r[j]).strip() for r in body if j < len(r)]
            nonempty = [v for v in vals if v != ""]
            if not nonempty:
                continue
            numeric = sum(1 for v in nonempty if cell_looks_mean_sd(v))
            if numeric == 0:  # labels/units like "600 W", "N/A" — not summary cells
                factor_col = j
                break
    if factor_col is None or factor_col == cond_col:
        return None
    return (factor_col, cond_col)


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
    # layout tag: "sample_by_condition" | "grouped_before_after" | "wide_raw" | ...
    layout: str = ""
    # rows recognized as DERIVED (variation/delta) and deliberately NOT loaded
    dropped_derived_rows: int = 0


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


def _interpret_grouped_before_after(
        result: "InterpretedTable", data_rows: List[List[str]],
        labels: List[str], grouped: Tuple[int, int],
        default_n: Optional[int]) -> bool:
    """Fill ``result`` for the factor × condition (before/after) layout.

    Each measurement column becomes a summary comparing every {factor · condition}
    cell (e.g. '600 W · Sem plasma', '600 W · Com plasma', '750 W · Sem plasma'...).
    The factor label is forward-filled across its block (it is often written once,
    with blank cells beneath). Returns True on success, False if nothing usable was
    built (so the caller can fall back to the generic handler).
    """
    factor_col, cond_col = grouped
    meas_cols = [j for j in range(len(labels))
                 if j not in (factor_col, cond_col)]
    if not meas_cols:
        return False
    result.measurement_columns = [labels[j] for j in meas_cols]
    result.layout = "grouped_before_after"

    built_any = False

    # Assign a factor label to every data row. The factor (e.g. '600 W') is written
    # once per BLOCK but may sit on any row of that block (top, middle, ...), with
    # 'N/A'/blank on the block's other rows. So we segment rows into blocks and give
    # each block the single real factor value found anywhere inside it. A new block
    # starts when the condition value repeats (e.g. a second 'Sem plasma').
    def _is_placeholder(v: str) -> bool:
        return _norm(v) in {"", "na", "n/a", "-", "--"}

    factor_per_row: List[str] = [""] * len(data_rows)
    block_start = 0
    seen_conds: set = set()
    blocks: List[Tuple[int, int]] = []
    for ri, r in enumerate(data_rows):
        cond = _norm(str(r[cond_col]).strip()) if cond_col < len(r) else ""
        if cond and cond in seen_conds:
            blocks.append((block_start, ri))
            block_start = ri
            seen_conds = set()
        if cond:
            seen_conds.add(cond)
    blocks.append((block_start, len(data_rows)))
    for (a, b) in blocks:
        block_factor = ""
        for ri in range(a, b):
            r = data_rows[ri]
            fac = str(r[factor_col]).strip() if factor_col < len(r) else ""
            if not _is_placeholder(fac):
                block_factor = fac
                break
        for ri in range(a, b):
            factor_per_row[ri] = block_factor

    for j in meas_cols:
        col_label = labels[j]
        summ: Dict[str, Dict[str, float]] = {}
        for ri, r in enumerate(data_rows):
            cond = str(r[cond_col]).strip() if cond_col < len(r) else ""
            fac = factor_per_row[ri]
            ms = parse_mean_sd(r[j]) if j < len(r) else None
            if ms is None:
                continue
            key = " · ".join([p for p in (fac, cond) if p]) or f"linha {ri+1}"
            entry: Dict[str, float] = {"mean": ms.mean}
            if ms.sd is not None:
                entry["sd"] = ms.sd
            if default_n is not None:
                entry["n"] = int(default_n)
            if key in summ:
                k = 2
                while f"{key} ({k})" in summ:
                    k += 1
                key = f"{key} ({k})"
            summ[key] = entry
        if summ:
            result.summary_by_column[col_label] = summ
            built_any = True

    if not built_any:
        return False

    msg = ("Tabela no formato fator × condição (antes/depois) — ex.: '"
           + labels[factor_col] + "' × '" + labels[cond_col] + "'. Cada célula é "
           "uma observação pareada; as colunas de medida ("
           + ", ".join(result.measurement_columns) + ") foram carregadas como "
           "grupos '{fator · condição}'.")
    if default_n is None:
        msg += (" Informe o tamanho amostral (n) — não consta na tabela — para "
                "habilitar os testes.")
    result.messages.append(msg)
    if result.dropped_derived_rows:
        result.messages.append(
            f"{result.dropped_derived_rows} linha(s) de variação/percentual foram "
            "identificadas como valores derivados e NÃO carregadas como dados "
            "(elas são cálculos, não observações).")
    return True


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

    # count and drop DERIVED rows (variation/delta) up front — they are never data
    result.dropped_derived_rows = sum(1 for r in body if row_is_derived(r))
    data_rows = [r for r in body if not row_is_derived(r)]

    # The 'factor × condition (before/after)' layout applies whether or not the
    # cells carry a ± sd (materials tables often report a bare mean). Try it first
    # for BOTH summary and raw kinds, so 'Potência' is never mistaken for a measure.
    grouped = detect_grouped_before_after(rows, n_header)
    if grouped is not None:
        if _interpret_grouped_before_after(
                result, data_rows, labels, grouped, default_n):
            # if none of the loaded cells carried a sd, tell the user plainly
            has_sd = any("sd" in e for col in result.summary_by_column.values()
                         for e in col.values())
            if not has_sd:
                result.messages.append(
                    "Atenção: esta tabela traz apenas valores pontuais (sem desvio "
                    "padrão). Sem DP e sem n não é possível testar significância — "
                    "o StatLab não fabrica incerteza. Os valores foram carregados "
                    "apenas para referência/visualização.")
            return result

    if kind == "summary":
        # sample x condition layout: one summary per measurement column
        meas_cols = [j for j in range(len(labels)) if j != label_col]
        result.measurement_columns = [labels[j] for j in meas_cols]
        result.layout = "sample_by_condition"
        for j in meas_cols:
            col_label = labels[j]
            summ: Dict[str, Dict[str, float]] = {}
            letters: Dict[str, str] = {}
            for ri, r in enumerate(data_rows):
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
        if result.dropped_derived_rows:
            result.messages.append(
                f"{result.dropped_derived_rows} linha(s) de variação/percentual "
                "foram identificadas como valores derivados e NÃO carregadas como "
                "dados.")
        if result.grouping_letters:
            result.messages.append(
                "Letras de agrupamento (ex.: teste de Tukey já realizado no trabalho "
                "original) foram detectadas e preservadas para conferência.")
        return result

    meas_cols = [j for j in range(len(labels)) if j != label_col]
    result.measurement_columns = [labels[j] for j in meas_cols]

    # kind == "raw": build {column_label: [values]} treating each measurement
    # column as a group. If there is a label column, values come from that column's
    # rows; otherwise the whole table is wide raw.
    if label_col is None:
        # wide: each column is a group
        result.layout = "wide_raw"
        raw: Dict[str, List[Optional[float]]] = {labels[j]: [] for j in meas_cols}
        for r in data_rows:
            for j in meas_cols:
                ms = parse_mean_sd(r[j]) if j < len(r) else None
                raw[labels[j]].append(ms.mean if ms else None)
        result.raw = raw
        result.messages.append("Tabela de dados brutos (uma coluna por grupo).")
    else:
        # sample x condition of plain numbers -> each column is a comparison of
        # samples with a single value each (rarely enough for analysis); expose it
        # like the summary layout but as raw single values per sample.
        result.layout = "sample_by_condition_raw"
        raw = {}
        for j in meas_cols:
            col_vals = []
            for r in data_rows:
                ms = parse_mean_sd(r[j]) if j < len(r) else None
                col_vals.append(ms.mean if ms else None)
            raw[labels[j]] = col_vals
        result.raw = raw
        result.messages.append(
            "Tabela numérica no formato amostra × condição (um valor por célula). "
            "Cada coluna vira um grupo com um valor por amostra.")
    if result.dropped_derived_rows:
        result.messages.append(
            f"{result.dropped_derived_rows} linha(s) de variação/percentual foram "
            "identificadas como valores derivados e NÃO carregadas como dados.")
    return result
