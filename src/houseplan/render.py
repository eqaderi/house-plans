"""Render a plan DXF to PDF and PNG at true scale on its sheet.

The render limits are the sheet frame in modelspace, and the figure size is
the paper size, so 1 mm on paper is exactly `scale` mm in the model. Nothing
is fitted to the page.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from ezdxf.addons.drawing import Frontend, RenderContext
from ezdxf.addons.drawing.config import BackgroundPolicy, ColorPolicy, Configuration, LineweightPolicy
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend

from .drawing import PAPERS, Sheet

MM_PER_INCH = 25.4


def render(doc, sheet: Sheet, pdf_path: str | None, png_path: str | None, dpi: int = 200) -> None:
    w_mm, h_mm = PAPERS[sheet.paper]
    fig = plt.figure(figsize=(w_mm / MM_PER_INCH, h_mm / MM_PER_INCH), dpi=dpi)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_axis_off()
    ax.margins(0)
    x0, y0, x1, y1 = sheet.frame
    config = Configuration(
        background_policy=BackgroundPolicy.WHITE,
        color_policy=ColorPolicy.BLACK,
        lineweight_policy=LineweightPolicy.ABSOLUTE,
        min_lineweight=0.13,
    )
    Frontend(RenderContext(doc), MatplotlibBackend(ax), config=config).draw_layout(doc.modelspace(), finalize=False)
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect("equal")
    fig.set_size_inches(w_mm / MM_PER_INCH, h_mm / MM_PER_INCH, forward=True)
    if pdf_path:
        fig.savefig(pdf_path)
    if png_path:
        fig.savefig(png_path, dpi=dpi)
    plt.close(fig)
