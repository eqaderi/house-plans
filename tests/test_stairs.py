"""Stairs with a landing: two flights, straight on, turning a quarter (L) or
back on themselves (U). The footprint is flights plus landing; the walking
line ends where the last flight ends."""

from __future__ import annotations

import pytest

from houseplan.geometry import stair_footprint, stair_ends
from houseplan.model import Stair


def stair(**kw):
    base = dict(id="S", level="A", to_level="B", origin=[0, 0], direction="+x", width=1000, risers=18, going=280)
    return Stair.model_validate({**base, **kw})


def test_straight_single_flight_unchanged():
    fp = stair_footprint(stair())
    assert fp.bounds == (0, -500, 17 * 280, 500)


def test_u_turn_left_with_gap():
    s = stair(flights=[9, 9], turn="U-left", gap=100)
    fp = stair_footprint(s)
    assert fp.bounds == (0, -500, 2240 + 1000, 1600)
    assert fp.area == pytest.approx(2 * 2240 * 1000 + 1000 * 2100)
    bottom, top = stair_ends(s)
    assert bottom == (-400, 0) and top == (-400, 1100)


def test_l_turn_right_going_north():
    s = stair(direction="+y", flights=[10, 8], turn="L-right")
    fp = stair_footprint(s)
    assert fp.bounds == (-500, 0, 500 + 7 * 280, 9 * 280 + 1000)
    assert fp.area == pytest.approx(9 * 280 * 1000 + 1000 * 1000 + 7 * 280 * 1000)
    assert stair_ends(s)[1] == (500 + 7 * 280 + 400, 9 * 280 + 500)


def test_straight_with_mid_landing():
    s = stair(flights=[9, 9], turn="straight", landing=1200)
    assert stair_footprint(s).bounds == (0, -500, 8 * 280 + 1200 + 8 * 280, 500)


def test_flights_must_add_up():
    with pytest.raises(ValueError):
        stair(flights=[9, 8])


def test_turn_needs_two_flights():
    with pytest.raises(ValueError):
        stair(turn="U-left")
