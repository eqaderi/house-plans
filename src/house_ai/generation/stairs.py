"""Stair dimensions shared by the bar generator (S10-05)."""

from __future__ import annotations

import math

from house_ai.constants.evaluations import MIN_STAIR_LANDING_M

SLAB_M = 0.25
TREAD_M = 0.28
#: Depth (dm) kept for the landing where a U-shaped flight leaves and arrives: the
#: landing plus half a wall and tolerance (0.2 m).
LANDING_STRIP_DM = math.ceil((MIN_STAIR_LANDING_M + 0.2) * 10 - 1e-9)


def stair_risers(rise_m: float) -> tuple[int, float, float]:
    """(riser count, riser height m, run length m) for a straight flight, typical values."""
    n = max(2, math.ceil(abs(rise_m) / 0.18 - 1e-9))
    return n, abs(rise_m) / n, (n - 1) * TREAD_M


def u_layout(
    near: int, far: int, c0: int, c1: int, width_dm: float, riser_count: int
) -> tuple[list[tuple[float, float]], bool]:
    """A U-shaped flight as two lanes in the cross range ``c0..c1`` (ADR 0023).

    Both flights meet the ``near`` line: the first leaves it at the bottom, the second
    arrives at it on the upper floor, whose landing lies beyond ``near``. They turn on a
    level half landing towards ``far``. Each lane is as long as the longer flight. Returns
    the walking line as (run, cross) points, and whether the half landing is at least a
    flight's width deep; when it is not, the turn is clamped at ``far`` and the flights are
    too short.
    """
    sign = 1 if far > near else -1
    longer = math.ceil(riser_count / 2)
    run = math.ceil((longer - 1) * TREAD_M * 10 - 1e-9)
    turn = near + sign * run
    fits = sign * (far - turn) >= width_dm
    if sign * (turn - far) > 0:
        turn = far
    lane1, lane2 = c0 + width_dm / 2, c1 - width_dm / 2
    return [(near, lane1), (turn, lane1), (turn, lane2), (near, lane2)], fits


def u_core_fits(across_dm: int, along_dm: int, riser_count: int) -> bool:
    """Whether a rectangular core holds a U-shaped flight laid out by ``u_layout``.

    Lanes of at most 1.0 m (at least 0.9 m) keep 0.2 m from the walls; along the core,
    the landing strip, the longer flight and a half landing as deep as a lane fit.
    """
    width_dm = min(10.0, across_dm / 2 - 2)
    if width_dm < 9:
        return False
    longer = math.ceil(riser_count / 2)
    run = math.ceil((longer - 1) * TREAD_M * 10 - 1e-9)
    return along_dm >= 2 + LANDING_STRIP_DM + run + width_dm + 2
