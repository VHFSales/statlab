"""Compact Letter Display (CLD) - SR-12, design section 10, spec 42-46, 73.

CRITICAL MODULE. Letters are derived from a GENERIC significance matrix (decoupled
from Tukey), NOT from mean ordering. Algorithm: insert-and-absorb (Piepho 2004).

Invariants (tested):
  INV-1  significant pair   => the two groups share NO letter.
  INV-2  non-significant pair => the two groups share >= 1 letter.
  INV-3  letters extend beyond 26: a..z, aa, ab, ...

Mean order (if provided) affects ONLY the left-to-right labelling of the already
computed columns (a purely visual convention: "a" at the highest mean).
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

from .types import CLDResult, SignificanceMatrix


def letter_symbol(index: int) -> str:
    """0->a, 1->b, ... 25->z, 26->aa, 27->ab, ... (bijective base-26)."""
    if index < 0:
        raise ValueError("index must be >= 0")
    result = ""
    index += 1  # bijective base-26
    while index > 0:
        index, rem = divmod(index - 1, 26)
        result = chr(ord("a") + rem) + result
    return result


def _absorb(columns: List[set]) -> List[set]:
    """Remove any column whose set is a subset of another column's set."""
    # drop empties
    cols = [c for c in columns if c]
    keep: List[set] = []
    for i, ci in enumerate(cols):
        subsumed = False
        for j, cj in enumerate(cols):
            if i == j:
                continue
            if ci < cj:  # proper subset
                subsumed = True
                break
            if ci == cj and j < i:  # duplicate: keep the first occurrence
                subsumed = True
                break
        if not subsumed:
            keep.append(ci)
    return keep


def compact_letter_display(matrix: SignificanceMatrix,
                           order: Optional[Sequence[str]] = None) -> CLDResult:
    """Compute a Compact Letter Display from a significance matrix.

    Parameters
    ----------
    matrix : SignificanceMatrix
        sig[i][j] == True means groups i and j differ significantly.
    order : sequence of labels, optional
        Visual order used to assign letter symbols left-to-right (e.g. by
        descending mean). Does NOT affect the grouping structure.
    """
    labels = list(matrix.labels)
    k = len(labels)
    sig = matrix.sig
    idx = {lab: i for i, lab in enumerate(labels)}

    # Determine the processing order of labels (for deterministic columns).
    if order is None:
        proc = list(labels)
    else:
        rank = {lab: r for r, lab in enumerate(order)}
        proc = sorted(labels, key=lambda l: rank.get(l, 1e9))

    # --- Insert-and-absorb (Piepho 2004) ---
    # Start with a single column containing all groups.
    columns: List[set] = [set(labels)]

    # For every significant pair, split any column containing both.
    for a in range(k):
        for b in range(a + 1, k):
            if not sig[a][b]:
                continue
            la, lb = labels[a], labels[b]
            new_cols: List[set] = []
            for col in columns:
                if la in col and lb in col:
                    c1 = col - {la}
                    c2 = col - {lb}
                    new_cols.append(c1)
                    new_cols.append(c2)
                else:
                    new_cols.append(col)
            columns = _absorb(new_cols)

    # Final absorb (safety) and drop empties.
    columns = _absorb(columns)
    columns = [c for c in columns if c]

    # --- Order the columns for stable, readable letter assignment ---
    # A column is placed by the best (earliest in proc) member it contains.
    proc_rank = {lab: r for r, lab in enumerate(proc)}

    def col_key(col: set):
        members = sorted(col, key=lambda l: proc_rank.get(l, 1e9))
        return [proc_rank.get(m, 1e9) for m in members]

    columns.sort(key=col_key)

    # --- Assign letter symbols ---
    letters: Dict[str, List[str]] = {lab: [] for lab in labels}
    for ci, col in enumerate(columns):
        sym = letter_symbol(ci)
        for lab in col:
            letters[lab].append(sym)

    # Each group ends up with at least one letter. A group significantly
    # different from every other becomes a singleton column here.
    for lab in labels:
        if not letters[lab]:
            # isolated group: give it its own trailing letter
            sym = letter_symbol(len(columns))
            columns.append({lab})
            letters[lab].append(sym)

    # sort each group's letters by their symbol order
    sym_order = {letter_symbol(i): i for i in range(len(columns) + 5)}
    for lab in labels:
        letters[lab].sort(key=lambda s: sym_order.get(s, 1e9))

    display = {lab: "".join(letters[lab]) for lab in labels}

    return CLDResult(
        letters=letters,
        display=display,
        n_letters=len(columns),
        source=matrix.source,
        order=proc,
    )


# --------------------------------------------------------------------------- #
# Invariant checks (used by tests and optionally at runtime)
# --------------------------------------------------------------------------- #
def verify_invariants(matrix: SignificanceMatrix, cld: CLDResult) -> List[str]:
    """Return a list of invariant-violation messages (empty if all hold)."""
    problems: List[str] = []
    labels = matrix.labels
    k = len(labels)
    for i in range(k):
        for j in range(i + 1, k):
            li, lj = labels[i], labels[j]
            shared = set(cld.letters[li]) & set(cld.letters[lj])
            if matrix.sig[i][j] and shared:
                problems.append(
                    f"INV-1 violated: {li} vs {lj} are significant but share {shared}."
                )
            if (not matrix.sig[i][j]) and not shared:
                problems.append(
                    f"INV-2 violated: {li} vs {lj} are not significant but share no letter."
                )
    return problems
