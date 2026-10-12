"""Jurisdiction rules, loaded from rules/<ruleset>.yaml.

A rule names one of the evaluators below, the room uses it applies to, a
numeric limit and its source. How a failure is reported depends on how sure we
are of the limit itself:

- `verified`: checked against the official regulation text. Failure is an error.
- `transcribed`: taken from a transcription of the regulation text that has
  not yet been compared with the official edition. Failure is an error, and
  the message asks for that comparison.
- `unverified`: secondary sources only. Failure is a warning that a qualified
  person must confirm, because a number we could not trace to the regulation
  must never silently pass or fail a design.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Literal

import yaml
from pydantic import BaseModel, ConfigDict
from shapely.geometry import box

from .checks import Finding
from .geometry import LevelGeom, sides_of
from .model import Design, OpeningKind

RULES_DIR = Path(__file__).resolve().parents[2] / "rules"


class Rule(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    check: str
    title: str
    value: float
    value_max: float | None = None
    params: dict[str, float] = {}
    uses: list[str] | None = None
    source: str
    url: str | None = None
    status: Literal["verified", "transcribed", "unverified"] = "unverified"
    note: str | None = None


class Ruleset(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    ruleset: str
    jurisdiction: str
    title: str
    rules: list[Rule]


def load_ruleset(name: str) -> Ruleset:
    with open(RULES_DIR / f"{name}.yaml", encoding="utf-8") as fh:
        return Ruleset.model_validate(yaml.safe_load(fh))


def _rooms(design, geo, rule):
    for lg in geo.values():
        for rg in lg.rooms.values():
            if rg.outline is not None and (rule.uses is None or rg.room.use.value in rule.uses):
                yield lg, rg


def room_min_area(design, geo, rule):
    for _, rg in _rooms(design, geo, rule):
        a = rg.area_mm2 / 1e6
        yield rg.room.id, a >= rule.value, f"net area {a:.2f} m² (min {rule.value} m²)"


def room_min_width(design, geo, rule):
    for _, rg in _rooms(design, geo, rule):
        w, _ = sides_of(rg.outline)
        yield rg.room.id, w >= rule.value, f"narrowest side {w:.0f} mm (min {rule.value:.0f} mm); measured on the bounding rectangle, check L-shaped rooms by hand"


def clear_height_min(design, geo, rule):
    for lg, rg in _rooms(design, geo, rule):
        h = design.level(lg.level_id).clear_height
        yield rg.room.id, h >= rule.value, f"clear height {h} mm (min {rule.value:.0f} mm)"


def window_area_ratio(design, geo, rule):
    for lg, rg in _rooms(design, geo, rule):
        glazed = sum(
            og.opening.width * og.opening.height
            for og in lg.openings.values()
            if og.opening.kind is OpeningKind.window and rg.outline.distance(og.cut) < 1.0
        )
        ratio = glazed / rg.area_mm2 if rg.area_mm2 else 0
        yield rg.room.id, ratio >= rule.value, f"window rough-opening area / floor area = {ratio:.3f} (min {rule.value})"


def door_min_width(design, geo, rule):
    for lg in geo.values():
        for og in lg.openings.values():
            if og.opening.kind is OpeningKind.door:
                rooms = {rg.room.use.value for rg in lg.rooms.values() if rg.outline is not None and rg.outline.distance(og.cut) < 1.0}
                if rule.uses is None or rooms & set(rule.uses):
                    w = og.opening.leaf or og.opening.width
                    yield og.opening.id, w >= rule.value, f"door width {w} mm (min {rule.value:.0f} mm)"


def _stair_values(design):
    for s in design.stairs:
        climb = design.level(s.to_level).ffl - design.level(s.level).ffl
        yield s, climb / s.risers


def stair_rise_max(design, geo, rule):
    for s, rise in _stair_values(design):
        yield s.id, rise <= rule.value, f"rise {rise:.1f} mm (max {rule.value:.0f} mm)"


def stair_going_min(design, geo, rule):
    for s, _ in _stair_values(design):
        yield s.id, s.going >= rule.value, f"going {s.going} mm (min {rule.value:.0f} mm)"


def stair_width_min(design, geo, rule):
    for s, _ in _stair_values(design):
        yield s.id, s.width >= rule.value, f"clear width {s.width} mm (min {rule.value:.0f} mm)"


def stair_step_formula(design, geo, rule):
    for s, rise in _stair_values(design):
        v = 2 * rise + s.going
        yield s.id, rule.value <= v <= (rule.value_max or v), f"2R+G = {v:.1f} mm (allowed {rule.value:.0f}–{rule.value_max:.0f} mm)"


def stair_risers_per_flight_max(design, geo, rule):
    for s, _ in _stair_values(design):
        yield s.id, s.risers <= rule.value, f"{s.risers} risers in one flight (max {rule.value:.0f})"


def entrance_door_min_width(design, geo, rule):
    for lg in geo.values():
        for og in lg.openings.values():
            if og.opening.kind is OpeningKind.door and og.wall.kind.value == "exterior":
                w = og.opening.leaf or og.opening.width
                yield og.opening.id, w >= rule.value, f"entrance door width {w} mm (min {rule.value:.0f} mm)"


def main_room_min_area(design, geo, rule):
    """The largest room of the given uses must reach `value` m² once the
    dwelling's total net area reaches params.unit_area_from m²."""
    total = sum(rg.area_mm2 for lg in geo.values() for rg in lg.rooms.values()) / 1e6
    if total < rule.params.get("unit_area_from", 0):
        return
    rooms = list(_rooms(design, geo, rule))
    if not rooms:
        return
    _, best = max(rooms, key=lambda x: x[1].area_mm2)
    a = best.area_mm2 / 1e6
    yield best.room.id, a >= rule.value, f"largest main room {a:.2f} m² (min {rule.value} m² for a dwelling of {total:.1f} m² net)"


def reentrant_corner_ratio_max(design, geo, rule):
    """A notch cut out of the plan's bounding box counts as a re-entrant
    corner when it is deeper than `value` of the plan size in both directions."""
    for lg in geo.values():
        fp = lg.footprint.simplify(0)
        if fp.is_empty:
            continue
        minx, miny, maxx, maxy = fp.bounds
        w, h = maxx - minx, maxy - miny
        notches = box(minx, miny, maxx, maxy).difference(fp)
        worst = 0.0
        for n in getattr(notches, "geoms", [notches]):
            if n.is_empty or n.area < 1.0:
                continue
            nx0, ny0, nx1, ny1 = n.bounds
            worst = max(worst, min((nx1 - nx0) / w, (ny1 - ny0) / h))
        yield lg.level_id, worst <= rule.value, f"deepest notch is {worst:.0%} of the plan in both directions (max {rule.value:.0%})"


def window_wall_ratio_max(design, geo, rule):
    """Window area over the area of exterior wall faces, per level."""
    for lg in geo.values():
        clear = design.level(lg.level_id).clear_height
        walls = sum(g.frame.length for g in lg.walls.values() if g.wall.kind.value == "exterior") * clear
        glass = sum(og.opening.width * og.opening.height for og in lg.openings.values() if og.opening.kind is OpeningKind.window and og.wall.kind.value == "exterior")
        if walls:
            yield lg.level_id, glass / walls <= rule.value, f"window-to-wall ratio {glass / walls:.0%} (max {rule.value:.0%}), measured on wall axes and clear height"


def lift_car_min(design, geo, rule):
    """Car inside size: width >= value, depth >= params.depth."""
    for lift in design.lifts:
        w, d = lift.car
        yield lift.id, w >= rule.value and d >= rule.params["depth"], f"car {w} x {d} mm (min {rule.value:.0f} x {rule.params['depth']:.0f} mm)"


def lift_shaft_min(design, geo, rule):
    """Clear shaft, free on every served level: short side >= value, long
    side >= params.depth."""
    from .geometry import lift_shafts

    for lid, common in lift_shafts(design, geo).items():
        short, long = sides_of(common) if not common.is_empty else (0, 0)
        yield lid, short >= rule.value and long >= rule.params["depth"], f"clear shaft {short:.0f} x {long:.0f} mm (min {rule.value:.0f} x {rule.params['depth']:.0f} mm); measured on the bounding rectangle"


def lift_entrance_min_width(design, geo, rule):
    """The widest door or opening from each shaft room to its landing."""
    shafts = {r for lift in design.lifts for r in lift.shafts}
    for lg in geo.values():
        for rid in shafts & set(lg.rooms):
            widths = [og.opening.leaf or og.opening.width for og in lg.openings.values()
                      if og.opening.kind is not OpeningKind.window and lg.rooms[rid].outline is not None and lg.rooms[rid].outline.distance(og.cut) < 1.0]
            if widths:
                yield rid, max(widths) >= rule.value, f"landing entrance {max(widths)} mm (min {rule.value:.0f} mm)"


def garage_stalls_min(design, geo, rule):
    """One stall per car in program.vehicles, side by side in the largest
    garage: stalls `value` mm wide and params.length mm long. Measured on the
    bounding rectangle."""
    cars = design.program.vehicles
    garages = [rg for _, rg in _rooms(design, geo, rule) if rg.room.use.value == "garage"]
    if not cars or not garages:
        return
    g = max(garages, key=lambda rg: rg.area_mm2)
    short, long = sides_of(g.outline)
    across, deep = len(cars) * rule.value, rule.params["length"]
    ok = (across <= long and deep <= short) or (across <= short and deep <= long)
    yield g.room.id, ok, f"{len(cars)} stalls side by side need {across:.0f} x {deep:.0f} mm; garage is {short:.0f} x {long:.0f} mm"


EVALUATORS: dict[str, Callable] = {
    f.__name__: f
    for f in (
        room_min_area,
        room_min_width,
        clear_height_min,
        window_area_ratio,
        door_min_width,
        stair_rise_max,
        stair_going_min,
        stair_width_min,
        stair_risers_per_flight_max,
        stair_step_formula,
        entrance_door_min_width,
        main_room_min_area,
        reentrant_corner_ratio_max,
        window_wall_ratio_max,
        lift_car_min,
        lift_shaft_min,
        lift_entrance_min_width,
        garage_stalls_min,
    )
}


def run_rules(design: Design, geo: dict[str, LevelGeom]) -> list[Finding]:
    if not design.project.ruleset:
        return [Finding("NO_RULESET", "warning", design.project.name, "no ruleset set; only geometry was checked")]
    rs = load_ruleset(design.project.ruleset)
    out: list[Finding] = []
    idle: list[str] = []
    for rule in rs.rules:
        fn = EVALUATORS.get(rule.check)
        if fn is None:
            out.append(Finding("RULE_UNKNOWN_CHECK", "error", rule.id, f"no evaluator named {rule.check!r}"))
            continue
        results = list(fn(design, geo, rule))
        if not results:
            idle.append(rule.id)
        for subject, ok, detail in results:
            if ok:
                continue
            tag = {
                "verified": "",
                "transcribed": "(limit from a transcription; compare with the official edition) ",
                "unverified": "UNVERIFIED RULE — confirm with the regulation: ",
            }[rule.status]
            severity = "warning" if rule.status == "unverified" else "error"
            out.append(Finding(rule.id, severity, subject, f"{tag}{rule.title}: {detail} [{rule.source}]"))
    if idle:
        out.append(Finding("RULES_NOT_APPLICABLE", "info", rs.ruleset, f"nothing in the plan to test, so not checked (not passed): {', '.join(idle)}"))
    return out
