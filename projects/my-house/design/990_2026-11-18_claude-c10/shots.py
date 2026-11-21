"""Still pictures of the 3D model, taken from 3d.html with headless Chrome."""

from __future__ import annotations

import subprocess
from pathlib import Path

CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
SHOTS = [
    ("house-se", "mode=house&view=se"),
    ("house-south", "mode=house&view=south&names=0"),
    ("house-east", "mode=house&view=east&names=0"),
    ("house-road", "mode=house&view=road&names=0"),
    ("field", "mode=field&view=se"),
    ("field-top", "mode=field&view=top"),
    ("dig", "mode=dig&view=high"),
    ("open-road", "mode=road&view=high"),
    ("open-main", "mode=main&view=high"),
    ("open-lower", "mode=lower&view=high"),
]


def write_page(here: Path, model: dict) -> None:
    """3d.html = the viewer template with the model inlined, so it opens offline from one file."""
    import json

    page = (here / "viewer_template.html").read_text().replace("/*MODEL*/", json.dumps(model, separators=(",", ":")))
    (here / "3d.html").write_text(page)


def take(here: Path, only: list[str] | None = None) -> list[str]:
    """Write views/<name>.png for every shot; returns the names written ([] without Chrome)."""
    if not CHROME.exists():
        return []
    out = here / "views"
    out.mkdir(exist_ok=True)
    done = []
    for name, args in SHOTS:
        if only and name not in only:
            continue
        png = out / f"{name}.png"
        subprocess.run([str(CHROME), "--headless=new", "--use-angle=swiftshader", "--enable-unsafe-swiftshader",
                        "--hide-scrollbars", "--window-size=1600,1000", "--virtual-time-budget=4000",
                        f"--screenshot={png}", f"file://{here / '3d.html'}#{args}&shot=1"],
                       check=False, capture_output=True, timeout=120)
        if png.exists():
            done.append(name)
    return done


if __name__ == "__main__":
    import sys

    print(take(Path(__file__).resolve().parent, sys.argv[1:] or None))
