"""Semantic ID-map extraction and visual regression diff utilities (Stage S5, Task S5-08).

Extracts stable semantic element maps from canonical plan and site models or rendered SVGs,
computes structured regression diffs, and performs deterministic image diffing.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any

from house_ai.constants.reviewer import (
    ATTR_DATA_ID,
    ATTR_DATA_KIND,
    KIND_DOOR,
    KIND_ELEVATION_MARKER,
    KIND_ENVELOPE,
    KIND_PARCEL,
    KIND_SPACE,
    KIND_STAIR,
    KIND_WALL,
    KIND_WINDOW,
)
from house_ai.domain.plan import PlanVersion
from house_ai.domain.site import Site


@dataclass(frozen=True)
class SemanticElementRecord:
    """Canonical element record for semantic regression checking."""

    id: str
    kind: str
    label: str
    level_id: str | None = None
    bbox: tuple[float, float, float, float] | None = None
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class SemanticMapDiff:
    """Diff between baseline and current semantic ID maps."""

    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    modified: dict[str, dict[str, tuple[Any, Any]]] = field(default_factory=dict)

    @property
    def is_identical(self) -> bool:
        """True if there are zero added, removed, or modified elements."""
        return not self.added and not self.removed and not self.modified

    def summary(self) -> str:
        """Human-readable diff summary."""
        parts = []
        if self.added:
            parts.append(f"Added ({len(self.added)}): {', '.join(sorted(self.added))}")
        if self.removed:
            parts.append(f"Removed ({len(self.removed)}): {', '.join(sorted(self.removed))}")
        if self.modified:
            mod_keys = ', '.join(sorted(self.modified.keys()))
            parts.append(f"Modified ({len(self.modified)}): {mod_keys}")
        return "; ".join(parts) if parts else "No differences"


def build_semantic_id_map(
    plan: PlanVersion,
    site: Site | None = None,
) -> dict[str, SemanticElementRecord]:
    """Build a deterministic mapping of all canonical element IDs from plan and site."""
    elements: dict[str, SemanticElementRecord] = {}

    # Site overlays
    if site is not None:
        if site.boundary is not None:
            poly = site.boundary.to_shapely()
            elements["site-parcel-boundary"] = SemanticElementRecord(
                id="site-parcel-boundary",
                kind=KIND_PARCEL,
                label="Site parcel boundary",
                bbox=tuple(poly.bounds),  # type: ignore[arg-type]
                attributes={"area_m2": round(site.boundary.area_m2, 2)},
            )
        if site.buildable_envelope is not None:
            poly = site.buildable_envelope.polygon.to_shapely()
            elements["site-buildable-envelope"] = SemanticElementRecord(
                id="site-buildable-envelope",
                kind=KIND_ENVELOPE,
                label="Site buildable envelope",
                bbox=tuple(poly.bounds),  # type: ignore[arg-type]
                attributes={"area_m2": round(site.buildable_envelope.polygon.area_m2, 2)},
            )

    model = plan.model

    # Levels
    for lvl in model.levels:
        elements[f"level-elev-{lvl.id}"] = SemanticElementRecord(
            id=f"level-elev-{lvl.id}",
            kind=KIND_ELEVATION_MARKER,
            label=f"Level {lvl.name}",
            level_id=lvl.id,
            attributes={"elevation_m": lvl.elevation_m},
        )

    # Spaces
    for sp in model.spaces:
        poly = sp.boundary.to_shapely()
        elements[sp.id] = SemanticElementRecord(
            id=sp.id,
            kind=KIND_SPACE,
            label=sp.name,
            level_id=sp.level_id,
            bbox=tuple(poly.bounds),  # type: ignore[arg-type]
            attributes={
                "area_m2": round(sp.area_m2, 2),
                "program_item_id": sp.program_item_id,
                "zone_id": sp.zone_id,
            },
        )

    # Walls
    for w in model.walls:
        minx = min(w.start[0], w.end[0])
        miny = min(w.start[1], w.end[1])
        maxx = max(w.start[0], w.end[0])
        maxy = max(w.start[1], w.end[1])
        elements[w.id] = SemanticElementRecord(
            id=w.id,
            kind=KIND_WALL,
            label=f"Wall {w.id}",
            level_id=w.level_id,
            bbox=(minx, miny, maxx, maxy),
            attributes={
                "kind": w.kind.value,
                "thickness_m": round(w.thickness_m, 3),
            },
        )

    # Openings
    for o in model.openings:
        kind = KIND_DOOR if o.is_passable else KIND_WINDOW
        elements[o.id] = SemanticElementRecord(
            id=o.id,
            kind=kind,
            label=f"{kind.capitalize()} {o.id}",
            attributes={
                "host_wall_id": o.host_wall_id,
                "connects": list(o.connects),
                "width_m": round(o.width_m, 2),
            },
        )

    # Stairs
    for st in model.stairs:
        poly = st.footprint.to_shapely()
        elements[st.id] = SemanticElementRecord(
            id=st.id,
            kind=KIND_STAIR,
            label=f"Stair {st.id}",
            bbox=tuple(poly.bounds),  # type: ignore[arg-type]
            attributes={
                "from_level_id": st.from_level_id,
                "to_level_id": st.to_level_id,
                "riser_count": st.riser_count,
            },
        )

    return elements


def extract_svg_semantic_id_map(svg_text: str) -> dict[str, dict[str, str]]:
    """Parse SVG XML and extract all elements carrying semantic ID attributes."""
    root = ET.fromstring(svg_text)
    elements: dict[str, dict[str, str]] = {}

    for elem in root.iter():
        data_id = elem.attrib.get(ATTR_DATA_ID) or elem.attrib.get("id")
        if not data_id:
            continue

        data_kind = elem.attrib.get(ATTR_DATA_KIND, "element")
        role = elem.attrib.get("role", "")
        aria_label = elem.attrib.get("aria-label", "")

        elements[data_id] = {
            ATTR_DATA_ID: data_id,
            ATTR_DATA_KIND: data_kind,
            "role": role,
            "aria-label": aria_label,
            "tag": elem.tag.split("}")[-1],
        }

    return elements


def diff_semantic_id_maps(
    baseline: dict[str, SemanticElementRecord | dict[str, Any]],
    current: dict[str, SemanticElementRecord | dict[str, Any]],
) -> SemanticMapDiff:
    """Compute differences between baseline and current semantic ID maps."""
    diff = SemanticMapDiff()

    baseline_keys = set(baseline.keys())
    current_keys = set(current.keys())

    diff.added = sorted(list(current_keys - baseline_keys))
    diff.removed = sorted(list(baseline_keys - current_keys))

    common_keys = sorted(list(baseline_keys & current_keys))
    for k in common_keys:
        b_item = baseline[k]
        c_item = current[k]

        # Convert to dict representation for comparison
        b_dict = (
            {
                "kind": b_item.kind,
                "label": b_item.label,
                "level_id": b_item.level_id,
                "bbox": b_item.bbox,
                "attributes": b_item.attributes,
            }
            if isinstance(b_item, SemanticElementRecord)
            else b_item
        )
        c_dict = (
            {
                "kind": c_item.kind,
                "label": c_item.label,
                "level_id": c_item.level_id,
                "bbox": c_item.bbox,
                "attributes": c_item.attributes,
            }
            if isinstance(c_item, SemanticElementRecord)
            else c_item
        )

        modifications: dict[str, tuple[Any, Any]] = {}
        for prop in set(b_dict.keys()) | set(c_dict.keys()):
            b_val = b_dict.get(prop)
            c_val = c_dict.get(prop)
            if b_val != c_val:
                modifications[prop] = (b_val, c_val)

        if modifications:
            diff.modified[k] = modifications

    return diff


def compare_image_bytes(
    baseline_bytes: bytes,
    current_bytes: bytes,
    max_diff_ratio: float = 0.0,
) -> tuple[bool, float, str]:
    """Compare two image byte arrays.

    Returns (is_match, diff_ratio, reason).
    """
    if baseline_bytes == current_bytes:
        return True, 0.0, "Byte-exact match"

    # Verify PNG header
    png_hdr = b"\x89PNG\r\n\x1a\n"
    if not (baseline_bytes.startswith(png_hdr) and current_bytes.startswith(png_hdr)):
        return False, 1.0, "Invalid PNG header"

    len_base = len(baseline_bytes)
    len_curr = len(current_bytes)
    max_len = max(len_base, len_curr)
    min_len = min(len_base, len_curr)

    if max_len == 0:
        return True, 0.0, "Empty images match"

    # Count byte differences
    diff_count = abs(len_base - len_curr)
    for i in range(min_len):
        if baseline_bytes[i] != current_bytes[i]:
            diff_count += 1

    diff_ratio = diff_count / max_len

    if diff_ratio <= max_diff_ratio:
        return True, diff_ratio, f"Within tolerance ({diff_ratio:.4f} <= {max_diff_ratio:.4f})"

    return (
        False,
        diff_ratio,
        (
            f"Exceeded tolerance ({diff_ratio:.4f} > {max_diff_ratio:.4f}, "
            f"size {len_base} vs {len_curr})"
        ),
    )
