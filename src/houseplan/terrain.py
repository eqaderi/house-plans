"""Ground heights between the surveyed spot heights.

A linear TIN: Delaunay triangles over the site's ground spot heights, and
inside each triangle the plane through its three corners. No smoothing and no
extrapolation: outside the triangulated hull the ground is unknown. Every
height it returns is interpolated, not measured, and says from which points.
"""

from __future__ import annotations

from dataclasses import dataclass

import math

import numpy as np
from scipy.spatial import Delaunay

from .model import Site, SpotHeight

METHOD = "linear TIN (Delaunay triangles, plane per triangle, no extrapolation)"


@dataclass(frozen=True)
class GroundZ:
    z_mm: float  # survey Z, mm
    corners: tuple[str, str, str]  # spot heights of the triangle it lies in
    longest_edge_mm: float  # how far apart those points are: the support of the answer


class Terrain:
    def __init__(self, site: Site):
        self.points: list[SpotHeight] = [h for h in site.spot_heights if h.ground]
        self.source = site.source
        self.tri = Delaunay(np.array([h.at for h in self.points], dtype=float))

    def z_at(self, x: float, y: float) -> GroundZ | None:
        """Interpolated survey Z at a spec point, or None outside the hull."""
        s = int(self.tri.find_simplex(np.array([x, y], dtype=float)))
        if s < 0:
            return None
        t = self.tri.transform[s]
        b = t[:2] @ (np.array([x, y]) - t[2])
        w = (*b, 1 - b.sum())
        idx = self.tri.simplices[s]
        corners = [self.points[i] for i in idx]
        z = sum(wi * p.survey_z_mm for wi, p in zip(w, corners))
        longest = max(math.dist(a.at, b.at) for a in corners for b in corners)
        return GroundZ(float(z), tuple(p.name for p in corners), longest)

    def describe(self) -> str:
        return f"interpolated: {METHOD}, {len(self.points)} spot heights from {self.source}"
