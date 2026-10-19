"""Stair dimensions shared by the bar generator (S10-05)."""

from __future__ import annotations

import math

SLAB_M = 0.25
TREAD_M = 0.28


def stair_risers(rise_m: float) -> tuple[int, float, float]:
    """(riser count, riser height m, run length m) for a straight flight, typical values."""
    n = max(2, math.ceil(abs(rise_m) / 0.18 - 1e-9))
    return n, abs(rise_m) / n, (n - 1) * TREAD_M
