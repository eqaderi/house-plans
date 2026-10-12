"""External tools: where they live, whether they work, and DWG conversion.

Paths come from config/tools.toml, then config/tools.local.toml (untracked,
per machine), then HP_<KEY> environment variables, so the same project runs on
both laptops.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import tempfile
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def tool_paths() -> dict[str, str]:
    with open(ROOT / "config" / "tools.toml", "rb") as fh:
        cfg = tomllib.load(fh)["tools"]
    local = ROOT / "config" / "tools.local.toml"
    if local.exists():
        with open(local, "rb") as fh:
            cfg |= tomllib.load(fh).get("tools", {})
    return {k: os.path.expanduser(os.environ.get(f"HP_{k.upper()}", v)) for k, v in cfg.items()}


def doctor() -> int:
    return subprocess.run([str(ROOT / "bin" / "doctor")]).returncode


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def dwg_to_dxf(dwg: Path, out_dir: Path) -> int:
    """Convert one DWG to DXF 2018 with the ODA File Converter.

    The original is copied to a scratch folder first so ODA never touches it,
    and its checksum is printed for sources/MANIFEST.sha256.
    """
    oda = tool_paths()["oda"]
    if not Path(oda).exists():
        print(f"ODA File Converter not found at {oda}; install it or set HP_ODA")
        return 1
    before = sha256(dwg)
    out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as src:
        shutil.copy2(dwg, Path(src) / dwg.name)
        cmd = [oda, src, str(out_dir), "ACAD2018", "DXF", "0", "1", dwg.name]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            print(res.stdout, res.stderr)
            return res.returncode
    if sha256(dwg) != before:
        print("ORIGINAL CHANGED during conversion; stop and restore it from backup")
        return 1
    print(f"{before}  {dwg}")
    print(f"wrote {out_dir / (dwg.stem + '.dxf')}")
    return 0
