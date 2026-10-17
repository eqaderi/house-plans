"""Layer roles: which CAD layer holds the boundary, contours, spot heights, ...

Roles come only from an explicit mapping file written or approved by a human.
:func:`suggest_roles` offers guesses from layer names for the inspection
report, clearly labelled as suggestions; they are never applied to an import.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

import yaml
from pydantic import Field

from house_ai.domain.base import StrictModel
from house_ai.domain.site import SiteFeatureKind


class LayerRole(StrEnum):
    BOUNDARY = "boundary"
    CONTOUR = "contour"
    SPOT_ELEVATION = "spot_elevation"
    ROAD = "road"
    EASEMENT = "easement"
    EXISTING_STRUCTURE = "existing_structure"
    UTILITY = "utility"
    TREE = "tree"
    WATER = "water"
    ACCESS_POINT = "access_point"
    OTHER_FEATURE = "other_feature"
    #: Labels, dimensions, title blocks: read but deliberately not interpreted.
    ANNOTATION = "annotation"
    IGNORE = "ignore"


FEATURE_KINDS: dict[LayerRole, SiteFeatureKind] = {
    LayerRole.ROAD: SiteFeatureKind.ROAD,
    LayerRole.EASEMENT: SiteFeatureKind.EASEMENT,
    LayerRole.EXISTING_STRUCTURE: SiteFeatureKind.EXISTING_STRUCTURE,
    LayerRole.UTILITY: SiteFeatureKind.UTILITY,
    LayerRole.TREE: SiteFeatureKind.TREE,
    LayerRole.WATER: SiteFeatureKind.WATER,
    LayerRole.ACCESS_POINT: SiteFeatureKind.ACCESS_POINT,
    LayerRole.OTHER_FEATURE: SiteFeatureKind.OTHER,
}

UNCLASSIFIED = "unclassified"


class LayerMapping(StrictModel):
    """A human-authored layer mapping (YAML or JSON)."""

    #: Layer name -> role. Names match case-insensitively, as in AutoCAD.
    layers: dict[str, LayerRole] = Field(default_factory=dict)
    #: Elevation 0 often means "not set" in CAD. Only when a human says the
    #: site really lies at 0 are zero elevations used.
    zero_elevation_is_valid: bool = False
    #: Handle of the boundary polyline, when the boundary layer holds several.
    boundary_handle: str | None = None

    def role_of(self, layer: str) -> LayerRole | None:
        lowered = {k.lower(): v for k, v in self.layers.items()}
        return lowered.get(layer.lower())

    def as_dict(self) -> dict[str, str]:
        return {k: v.value for k, v in sorted(self.layers.items())}


def load_layer_mapping(path: Path) -> LayerMapping:
    """Read a mapping from YAML or JSON (JSON is valid YAML)."""
    return LayerMapping.model_validate(yaml.safe_load(Path(path).read_text(encoding="utf-8")))


#: Keywords in layer names (English, German, Persian transliterations) that
#: suggest a role. A match is a hint for the human, not evidence.
_KEYWORDS: list[tuple[LayerRole, tuple[str, ...]]] = [
    (LayerRole.BOUNDARY, ("boundary", "parcel", "plot", "property", "lot", "grenze", "flurst",
                          "cadast", "kataster", "hodud", "marz")),
    (LayerRole.CONTOUR, ("contour", "contr", "isohyps", "hoehenlin", "höhenlin", "cntr")),
    (LayerRole.SPOT_ELEVATION, ("spot", "elev", "height", "level", "hoehe", "höhe", "kote",
                                "pnt", "ertefa")),
    (LayerRole.ROAD, ("road", "street", "strasse", "straße", "weg", "kerb", "curb", "khiaban")),
    (LayerRole.EXISTING_STRUCTURE, ("build", "bldg", "house", "gebaeude", "gebäude", "struct",
                                    "sakhteman")),
    (LayerRole.TREE, ("tree", "baum", "vegetat", "derakht")),
    (LayerRole.WATER, ("water", "river", "wasser", "ab")),
    (LayerRole.UTILITY, ("util", "sewer", "power", "elec", "gas", "kanal", "leitung")),
    (LayerRole.ANNOTATION, ("text", "dim", "anno", "title", "frame", "label", "beschrift")),
]


def suggest_roles(layer_names: list[str]) -> dict[str, tuple[LayerRole, str]]:
    """Layer -> (suggested role, matched keyword). Layers with no match are absent."""
    out: dict[str, tuple[LayerRole, str]] = {}
    for name in layer_names:
        lowered = name.lower()
        for role, words in _KEYWORDS:
            hit = next((w for w in words if _matches(lowered, w)), None)
            if hit:
                out[name] = (role, hit)
                break
    return out


def _matches(name: str, word: str) -> bool:
    # Very short keywords must match a whole token, so "ab" does not hit "slab".
    if len(word) <= 3:
        tokens = name.replace("-", "_").replace(" ", "_").replace(".", "_").split("_")
        return word in tokens
    return word in name
