"""Joint horizontal/vertical CP-SAT decisions for bar massings.

Terrain lookup indices depend on each bar's solved start AND length. Elevations
and burial/daylight are therefore decisions in the same solve as room layout.
Only the sectional intent restricts terrain contact; there is no cut/fill,
excavation depth or void-volume objective. Lookup uses a 5 cm horizontal grid
and centimetre Z; exact TIN quantities are evaluated after assembly.
"""

from __future__ import annotations

import math

SECTIONAL_STRATEGIES = ("walkout", "split_level", "stepped", "elevated", "hybrid")


def configure_section(m, mode):
    """Set link topology before room/stair eligibility is compiled."""
    if mode is None:
        return
    if mode not in SECTIONAL_STRATEGIES:
        raise ValueError(f"unknown sectional strategy {mode}")
    entry = m.entry_elevation_m
    stacked = {link.b for link in m.links if link.kind == "stacked"}
    for b in m.bars:
        if b.entry:
            continue
        if b.id in stacked:
            sign = 1 if mode == "elevated" else -1
            b.elevation_m = entry + sign * 3
        elif mode == "elevated":
            b.elevation_m = entry
        elif mode == "walkout" and stacked:
            b.elevation_m = entry - 3
        elif mode == "stepped":
            b.elevation_m = entry + round((b.elevation_m - entry) / 3) * 3
    m.params["sectional_strategy"] = mode


def joint_level_variables(md, m, start, length, ctx, mode=None):
    """Return elevation and buried-face variables, constrained by survey lookup."""
    if ctx is None or ctx.ground.surface is None:
        return {}, {}, []
    points = ctx.ground.surface.vertices
    low = math.floor(min(p[2] for p in points) * 100) - 600
    high = math.ceil(max(p[2] for p in points) * 100) + 600
    levels, ground, faces, objective = {}, {}, {}, []
    entry_bar = next(b for b in m.bars if b.entry)

    def terrain_at_center(bar, cross, name):
        lo, hi = 2 * bar.start_lo_dm, 2 * bar.start_hi_dm
        # midpoint along bar = (2*start + length) / 20 metres.
        center = md.NewIntVar(lo, hi, f"terrain_center2_{name}")
        md.Add(center == 2 * start[bar.id] + length[bar.id])
        values, known = [], []
        for c in range(lo, hi + 1):
            s = c / 20
            z = ctx.ground.at(s, cross) if bar.axis == "u" else ctx.ground.at(cross, s)
            values.append(round(z * 100) if z is not None else low)
            known.append(int(z is not None))
        if not any(known):
            return None
        z = md.NewIntVar(low, high, f"ground_{name}")
        index = md.NewIntVar(0, hi - lo, f"ground_index_{name}")
        md.Add(index == center - lo)
        md.AddElement(index, values, z)
        if not all(known):
            md.AddElement(index, known, 1)
        return z

    for b in m.bars:
        ground[b.id] = terrain_at_center(b, (b.cross0_dm + b.cross1_dm) / 20, f"{b.id}-center")
        faces[b.id, "front"] = terrain_at_center(b, b.cross0_dm / 10 - 0.5, f"{b.id}-front")
        faces[b.id, "back"] = terrain_at_center(b, b.cross1_dm / 10 + 0.5, f"{b.id}-back")
        levels[b.id] = md.NewIntVar(low, high, f"floor_z_cm_{b.id}")
    entry = levels[entry_bar.id]
    road = faces[entry_bar.id, "front"]
    if road is None:
        road = ground[entry_bar.id]
    if road is None:
        md.Add(entry == round(m.entry_elevation_m * 100))
    else:
        md.Add(entry == road)
    mode = mode or (
        "hybrid"
        if m.strategy == "split_walkout"
        else "walkout"
        if m.strategy == "compact"
        else "split_level"
    )
    stacked = set()
    for link in m.links:
        if link.kind == "stacked":
            a, b = m.bar(link.a), m.bar(link.b)
            sign = 1 if b.elevation_m > a.elevation_m else -1
            md.Add(levels[b.id] == levels[a.id] + sign * 300)
            stacked.add(b.id)
    step = 300 if mode == "stepped" else 150
    for b in m.bars:
        if b.entry or b.id in stacked:
            continue
        target = ground[b.id]
        base_ground = ground[entry_bar.id]
        if mode == "walkout" and stacked:
            md.Add(levels[b.id] == entry - 300)
        elif mode == "elevated" or abs(b.elevation_m - m.entry_elevation_m) < 1e-6:
            md.Add(levels[b.id] == entry)
        elif target is None or base_ground is None:
            md.Add(levels[b.id] == entry + round((b.elevation_m - m.entry_elevation_m) * 100))
        else:
            q = md.NewIntVar(-(high - low) // step, (high - low) // step, f"level_steps_{b.id}")
            md.Add(levels[b.id] == entry + q * step)
            # Sectional contact band: nearest half/full-storey to local terrain
            # change. It is symmetric in cut/void and has no +/-3 m clamp.
            band = step if mode == "stepped" else step//2
            md.Add(q * step >= target - base_ground - band)
            md.Add(q * step <= target - base_ground + band)
            md.Add(q <= -1 if b.elevation_m < m.entry_elevation_m else q >= 1)
    # Stair/link topology compiled above this seam must stay valid as Z moves.
    # Equal-level links stay equal, flights retain their direction and minimum
    # rise; an optimiser may not collapse a stair into a dangling same-level link.
    for link in m.links:
        if link.kind == "stacked":
            continue
        delta = m.bar(link.b).elevation_m-m.bar(link.a).elevation_m
        if abs(delta)<1e-6:
            md.Add(levels[link.b] == levels[link.a])
        elif delta>0:
            md.Add(levels[link.b]>=levels[link.a]+step)
        else:
            md.Add(levels[link.b]<=levels[link.a]-step)
    buried = {}
    for b in m.bars:
        for row in b.room_rows:
            terrain = faces[b.id, row.side]
            if terrain is None:
                continue
            flag = md.NewBoolVar(f"buried_{row.id}")
            md.Add(terrain - levels[b.id] >= 101).OnlyEnforceIf(flag)
            md.Add(terrain - levels[b.id] <= 100).OnlyEnforceIf(flag.Not())
            buried[row.id] = flag
    for link in m.links:
        rise = md.NewIntVar(0, high - low, f"section_rise_{link.a}_{link.b}")
        md.AddAbsEquality(rise, levels[link.a] - levels[link.b])
        objective.append(rise)  # circulation effort; no excavation or elevation score
    return levels, buried, objective
