"""DWG support through the ODA File Converter (DWG -> DXF), then ezdxf.

The converter is an external, optional program. It is found through the
``HOUSE_AI_ODA_CONVERTER`` environment variable, ``ODAFileConverter`` on
``PATH``, or the default macOS application path. When it is missing,
:func:`find_oda_converter` returns None and DWG files are reported as
unreadable instead of being guessed at.

The original file is never handed to the converter: it is copied, under an
ASCII name, into a fresh temporary directory, and the converter only ever
sees that copy. (QGIS's bundled GDAL has no DWG driver, so it is not used.)
"""

from __future__ import annotations

import hashlib
import os
import plistlib
import shutil
import subprocess
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, replace
from pathlib import Path

from .base import CadExtraction, CadInspection
from .dxf_ezdxf import EzdxfAdapter
from .formats import FileFormat, detect_format

ENV_VAR = "HOUSE_AI_ODA_CONVERTER"
MACOS_APP = Path("/Applications/ODAFileConverter.app/Contents/MacOS/ODAFileConverter")
#: DXF release written by the converter.
OUTPUT_VERSION = "ACAD2018"
TIMEOUT_S = 300


class DwgConversionError(RuntimeError):
    pass


@dataclass(frozen=True)
class OdaConverter:
    executable: Path
    version: str | None

    name = "ODA File Converter"

    @contextmanager
    def converted(self, dwg: Path) -> Iterator[Path]:
        """Yield a DXF converted from a private copy of ``dwg``; cleaned up afterwards."""
        with tempfile.TemporaryDirectory(prefix="house-ai-dwg-") as tmp:
            src_dir, out_dir = Path(tmp) / "in", Path(tmp) / "out"
            src_dir.mkdir()
            out_dir.mkdir()
            shutil.copyfile(dwg, src_dir / "input.dwg")
            cmd = [
                str(self.executable),
                str(src_dir),
                str(out_dir),
                OUTPUT_VERSION,
                "DXF",
                "0",  # do not recurse
                "1",  # audit
                "*.DWG",
            ]
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT_S)
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise DwgConversionError(f"ODA File Converter failed to run: {exc}") from exc
            out = out_dir / "input.dxf"
            if proc.returncode != 0 or not out.is_file():
                detail = (proc.stderr or proc.stdout).strip()[:500]
                errlog = next(out_dir.glob("*.err"), None)
                if errlog is not None:
                    detail += " " + errlog.read_text(errors="replace")[:500]
                raise DwgConversionError(
                    f"ODA File Converter produced no DXF for {dwg.name} "
                    f"(exit {proc.returncode}): {detail}".strip()
                )
            yield out


def find_oda_converter() -> OdaConverter | None:
    candidates = [os.environ.get(ENV_VAR), shutil.which("ODAFileConverter"), str(MACOS_APP)]
    for c in candidates:
        if c and Path(c).is_file() and os.access(c, os.X_OK):
            return OdaConverter(Path(c), _app_version(Path(c)))
    return None


def _app_version(executable: Path) -> str | None:
    """Version from the macOS bundle's Info.plist, when it is an app bundle."""
    plist = executable.parent.parent / "Info.plist"
    try:
        with plist.open("rb") as fh:
            return str(plistlib.load(fh).get("CFBundleShortVersionString")) or None
    except (OSError, plistlib.InvalidFileException):
        return None


class OdaDwgAdapter:
    """Reads DWG by converting a copy to DXF and parsing that with ezdxf."""

    name = "oda+ezdxf"

    def __init__(self, converter: OdaConverter, dxf: EzdxfAdapter | None = None) -> None:
        self.converter = converter
        self.dxf = dxf or EzdxfAdapter()

    def can_read(self, path: Path) -> bool:
        return detect_format(path).format is FileFormat.DWG

    def _annotate(self, path: Path, dxf_path: Path, inspection: CadInspection) -> CadInspection:
        version = detect_format(path).version
        # $ACADVER of the converted DXF is the converter's output release, not the DWG's.
        header = {**inspection.header, "$ACADVER": version}
        return replace(
            inspection,
            header=header,
            source_format=f"dwg {version}",
            converter=self.converter.name,
            converter_version=self.converter.version,
            converted_sha256=hashlib.sha256(dxf_path.read_bytes()).hexdigest(),
        )

    def inspect_cad(self, path: Path) -> CadInspection:
        with self.converter.converted(path) as dxf_path:
            return self._annotate(path, dxf_path, self.dxf.inspect_cad(dxf_path))

    def extract_cad(self, path: Path, layer_roles: dict[str, str]) -> CadExtraction:
        with self.converter.converted(path) as dxf_path:
            ext = self.dxf.extract_cad(dxf_path, layer_roles)
            assert ext.inspection is not None
            inspection = self._annotate(path, dxf_path, ext.inspection)
        return CadExtraction(
            points=ext.points,
            polylines=ext.polylines,
            layer_roles=ext.layer_roles,
            inspection=inspection,
            unsupported_entities=ext.unsupported_entities,
        )


def adapter_for(path: Path) -> EzdxfAdapter | OdaDwgAdapter:
    """The adapter that can read this file, chosen by its detected format."""
    fmt = detect_format(path)
    if fmt.format in (FileFormat.DXF_ASCII, FileFormat.DXF_BINARY):
        return EzdxfAdapter()
    if fmt.format is FileFormat.DWG:
        converter = find_oda_converter()
        if converter is None:
            raise DwgConversionError(
                f"{path.name} is DWG ({fmt.label}) but no DWG reader is available. Install the "
                f"ODA File Converter or set {ENV_VAR} to its executable."
            )
        return OdaDwgAdapter(converter)
    raise ValueError(f"{path.name} is {fmt.label} ({fmt.evidence}); no CAD adapter reads it")
