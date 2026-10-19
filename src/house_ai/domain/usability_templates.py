"""Versioned, cited conceptual furniture and fixture templates (ADR 0019).

Assumption data shared by the usability critics and the generator, which lays fixtures
out from the same bodies and clearances (S10-08). No jurisdictional authority.
"""

from house_ai.domain.usability import DimensionAssumption, FurnitureTemplate

VERSION = "1.0.0"
PROJECT = "docs/adr/0019-usability-geometry-and-assumptions.md (synthetic planning assumption)"
STAIRS = (
    "https://assets.publishing.service.gov.uk/government/uploads/"
    "system/uploads/attachment_data/file/996860/Approved_Document_K.pdf"
)
KITCHEN = "https://media.nkba.org/uploads/2022/05/Kitchen-Planning-Guidelines.pdf"
ACCESS = "https://www.access-board.gov/ada/guides/chapter-6-toilet-rooms/"
DINING = "https://www.ikea.com/gb/en/cat/6-seater-dining-tables-21827/"


def dimension(ident, value, source=PROJECT, rationale="Conceptual planning envelope"):
    return DimensionAssumption(id=ident, value=value, unit="m", source=source, rationale=rationale)


def template(ident, width, depth, *, left=0, right=0, front=0, back=0, source=PROJECT):
    def d(key, value):
        return dimension(f"{ident}-{key}", value, source)

    return FurnitureTemplate(
        id=ident,
        width=d("width", width),
        depth=d("depth", depth),
        left=d("left", left),
        right=d("right", right),
        front=d("front", front),
        back=d("back", back),
        description="Front is local negative Y; source is precedent, not code authority.",
    )


TEMPLATES = {
    t.id: t
    for t in [
        template("bed-double", 1.6, 2, left=0.6, right=0.6, front=0.75),
        template("bed-single", 0.9, 2, right=0.6, front=0.6),
        template("wardrobe", 1.2, 0.6, front=0.9),
        template("desk", 1.2, 0.6, front=0.9),
        template("chair", 0.5, 0.5, front=0.6),
        template(
            "dining",
            1.8,
            0.9,
            left=0.9,
            right=0.9,
            front=0.9,
            back=0.9,
            source=DINING + "; clearances: " + PROJECT,
        ),
        template("sofa-group", 2.4, 2.4, right=0.9),
        template("kitchen-run", 3, 0.6, front=1.219, source=KITCHEN + "; run/depth: " + PROJECT),
        template("appliance", 0.6, 0.6, front=0.9),
        template(
            "wc",
            0.4,
            0.7,
            front=0.75,
            left=0.2,
            right=0.2,
            source=ACCESS + "; non-accessible illustrative sizes: " + PROJECT,
        ),
        template("basin", 0.6, 0.5, front=0.7),
        template("shower", 0.9, 0.9, front=0.6),
        template("bath", 1.7, 0.75, front=0.6),
        template("vehicle", 1.8, 4.5, left=0.6, right=0.6, front=0.9, back=0.3),
        template("shelf", 1.2, 0.45, front=0.9),
        template("laundry", 1.8, 0.65, front=0.9),
    ]
}
