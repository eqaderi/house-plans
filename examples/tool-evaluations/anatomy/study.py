"""Reproduce the bounded Anatomy source/build study without installing its skill."""

from __future__ import annotations

import argparse
import json
import subprocess
from html.parser import HTMLParser
from pathlib import Path

PIN = "e9488296a44211c42701ff71705b7901470ec78f"


class Tags(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.counts: dict[str, int] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.counts[tag] = self.counts.get(tag, 0) + 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    args = parser.parse_args()
    source = args.source.resolve()
    pin = subprocess.check_output(
        ["git", "-C", str(source), "rev-parse", "HEAD"], text=True
    ).strip()
    assert pin == PIN, pin
    assert "MIT License" in (source / "LICENSE").read_text()
    subprocess.run(
        ["node", "examples/dial-indicator/build.mjs", "--light"],
        cwd=source,
        check=True,
        timeout=30,
        capture_output=True,
    )
    generated = source / "examples/dial-indicator/index-light.html"
    if not generated.exists():
        generated = source / "examples/dial-indicator/dial-indicator-light.html"
    assert generated.exists(), list((source / "examples/dial-indicator").glob("*.html"))
    tags = Tags()
    html = generated.read_text()
    tags.feed(html)
    assert tags.counts.get("svg", 0) > 0
    assert tags.counts.get("path", 0) > 40
    study = {
        "pin": pin,
        "licence": "MIT",
        "method": "measured source/build study",
        "build": "node examples/dial-indicator/build.mjs --light",
        "generated_file": generated.name,
        "tags": tags.counts,
        "observed_patterns": [
            "one SKILL.md with task-specific references and executable examples",
            "geometry kit separated from runtime and pure numeric behaviour",
            "live readout shares state with geometry/motion",
            "keyboard and reduced-motion instructions in references/motion.md",
            "desktop/mobile/zoomed screenshot verification in references/verify.md",
        ],
        "decision": "ADAPT patterns; do not install skill or use it as an architecture engine",
    }
    print(json.dumps(study, indent=2))


if __name__ == "__main__":
    main()
