"""Display formatting helpers.

Rule (FR-7, SR-11): NEVER round intermediate calculations. Rounding happens only
here, for presentation. p-values are never displayed as exactly 0.
"""

from __future__ import annotations

import math


def round_display(value: float, decimals: int = 4) -> float:
    """Round a value for display only. Passes through NaN/inf unchanged."""
    if value is None:
        return value
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return value
    return round(value, decimals)


def format_number(value: float, decimals: int = 4) -> str:
    """Format a number for display with a fixed number of decimals."""
    if value is None:
        return "—"
    if isinstance(value, float):
        if math.isnan(value):
            return "NaN"
        if math.isinf(value):
            return "∞" if value > 0 else "−∞"
    return f"{value:.{decimals}f}"


def format_p(p: float, decimals: int = 3, tiny_threshold: float | None = None) -> str:
    """Format a p-value for display.

    Never shows ``p = 0``. Values below the threshold (default 10**-decimals) are
    shown as ``< threshold``. The true value is kept elsewhere at full precision.
    """
    if p is None or (isinstance(p, float) and math.isnan(p)):
        return "NaN"
    if tiny_threshold is None:
        tiny_threshold = 10.0 ** (-decimals)
    if p < tiny_threshold:
        return f"< {tiny_threshold:.{decimals}f}"
    if p > 1.0:  # numerical noise guard
        p = 1.0
    return f"{p:.{decimals}f}"
