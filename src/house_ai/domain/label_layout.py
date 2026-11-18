"""Room-label layout of the plan drawing, computed once (#34, ADR 0033).

The plan drawing (``render2d.plan_svg``) draws these labels, and the label-collision
Finding (``evaluation.drawing``) checks the same labels at the same scale, so the Finding
matches what the Owner sees. Every Level panel of the drawing shares one scale: the extent
of all Spaces, and of the Site boundary when one is drawn, plus a 2.5 m margin.

This is geometry only: where each label's text lines sit and how large they are. How a
line is styled (colour, weight) is the drawing's business. Label size on the page is
estimated from the text: the drawing has no font metrics.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import combinations

from shapely.geometry import box
from shapely.ops import unary_union

from house_ai.constants.reviewer import MARGIN, PANEL_W
from house_ai.domain.geometry import Point2, Polygon2D
from house_ai.domain.model import HouseModel
from house_ai.domain.site import Site

#: Margin around the drawn Spaces and Site boundary, metres.
DRAWING_MARGIN_M = 2.5
#: A Space drawn shorter than this (pixels) gets a short, smaller name.
SMALL_LABEL_PX = 70
#: Estimated glyph advance as a share of the font size (Helvetica, mixed case and digits).
GLYPH_ADVANCE_EM = 0.55
#: Estimated ascent and descent of a text line as a share of the font size.
ASCENT_EM, DESCENT_EM = 0.8, 0.2

Bounds = tuple[float, float, float, float]


def drawing_bounds(model: HouseModel, site: Site | None) -> Bounds:
    """The extent the drawing shows: every Space, and the Site boundary when there is one."""
    shapes = [s.boundary.to_shapely() for s in model.spaces]
    if site is not None and site.boundary is not None:
        shapes.append(site.boundary.to_shapely())
    return unary_union(shapes).buffer(DRAWING_MARGIN_M).bounds


def drawing_scale(bounds: Bounds) -> float:
    """Pixels per metre of every Level panel."""
    minx, miny, maxx, maxy = bounds
    return (PANEL_W - 2 * MARGIN) / max(maxx - minx, maxy - miny, 1.0)


def rect_dims(poly: Polygon2D) -> tuple[float, float]:
    """Length and width of the smallest rectangle around a Space."""
    r = poly.to_shapely().minimum_rotated_rectangle
    pts = list(r.exterior.coords)
    a, b = math.dist(pts[0], pts[1]), math.dist(pts[1], pts[2])
    return (max(a, b), min(a, b))


@dataclass(frozen=True)
class LabelLine:
    """One centred text line of a label; ``dy`` is its baseline below the anchor, pixels."""

    text: str
    dy: float
    size: float

    def box(self, x: float, y: float):
        """Estimated extent on the page of this line, anchored at pixel ``(x, y)``."""
        half = len(self.text) * self.size * GLYPH_ADVANCE_EM / 2
        base = y + self.dy
        return box(x - half, base - ASCENT_EM * self.size, x + half, base + DESCENT_EM * self.size)


@dataclass(frozen=True)
class SpaceLabel:
    """The name, area and dimensions drawn at a Space's representative point, in that order."""

    space_id: str
    level_id: str
    #: Anchor in the model's local frame, metres.
    anchor: Point2
    lines: tuple[LabelLine, ...]


@dataclass(frozen=True)
class LabelLayout:
    """Every room label of a drawing, and the scale they are drawn at."""

    bounds: Bounds
    scale: float
    labels: tuple[SpaceLabel, ...]

    def pixel(self, xy: Point2) -> tuple[float, float]:
        """Position in a Level panel, pixels from the panel's drawing origin."""
        minx, _, _, maxy = self.bounds
        return ((xy[0] - minx) * self.scale, (maxy - xy[1]) * self.scale)

    def collisions(self) -> list[tuple[SpaceLabel, SpaceLabel]]:
        """Pairs of labels on one Level whose text overlaps on the page."""
        boxes = {}
        for label in self.labels:
            x, y = self.pixel(label.anchor)
            boxes[label.space_id] = [line.box(x, y) for line in label.lines]
        return [
            (a, b)
            for a, b in combinations(self.labels, 2)
            if a.level_id == b.level_id
            and any(
                p.intersection(q).area > 0 for p in boxes[a.space_id] for q in boxes[b.space_id]
            )
        ]


def label_layout(model: HouseModel, site: Site | None) -> LabelLayout:
    """The room labels of the plan drawing of ``model`` (with ``site`` shown when given)."""
    bounds = drawing_bounds(model, site)
    scale = drawing_scale(bounds)
    labels = []
    for s in model.spaces:
        c = s.boundary.to_shapely().representative_point()
        length, width = rect_dims(s.boundary)
        small = length * scale < SMALL_LABEL_PX
        lines = (
            LabelLine(s.name if not small else s.name.split(" ")[0], -4, 9 if not small else 7),
            LabelLine(f"{s.area_m2:.1f} m²", 7, 8),
            LabelLine(f"{length:.2f} × {width:.2f}", 17, 7),
        )
        labels.append(SpaceLabel(s.id, s.level_id, (c.x, c.y), lines))
    return LabelLayout(bounds, scale, tuple(labels))
