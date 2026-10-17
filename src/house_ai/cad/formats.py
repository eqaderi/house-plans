"""Detect what a survey file really is, from its bytes rather than its name.

A ``.dwg`` extension does not prove a DWG, and a survey can arrive as DXF,
PDF, LandXML, a point list or a GIS file. Detection reads only the first
bytes of the file and never modifies it.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

#: DWG/DXF version strings (AutoCAD release codes).
ACAD_RELEASES: dict[str, str] = {
    "AC1009": "R11/R12",
    "AC1012": "R13",
    "AC1014": "R14",
    "AC1015": "2000",
    "AC1018": "2004",
    "AC1021": "2007",
    "AC1024": "2010",
    "AC1027": "2013",
    "AC1032": "2018",
}

_SNIFF_BYTES = 4096


class FileFormat(StrEnum):
    DWG = "dwg"
    DXF_ASCII = "dxf"
    DXF_BINARY = "dxf_binary"
    PDF = "pdf"
    LANDXML = "landxml"
    KML = "kml"
    XML = "xml"
    ZIP = "zip"
    SQLITE = "sqlite"
    SHAPEFILE = "shapefile"
    LAS = "las"
    TIFF = "tiff"
    PNG = "png"
    JPEG = "jpeg"
    TEXT = "text"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class DetectedFormat:
    format: FileFormat
    #: e.g. "AC1032" for DWG; None when the format has no version marker here.
    version: str | None = None
    #: How the format was recognised.
    evidence: str = ""

    @property
    def is_cad(self) -> bool:
        return self.format in (FileFormat.DWG, FileFormat.DXF_ASCII, FileFormat.DXF_BINARY)

    @property
    def label(self) -> str:
        if self.version:
            release = ACAD_RELEASES.get(self.version)
            suffix = f" (AutoCAD {release})" if release else ""
            return f"{self.format.value} {self.version}{suffix}"
        return self.format.value


def detect_format(path: Path) -> DetectedFormat:
    with Path(path).open("rb") as fh:
        head = fh.read(_SNIFF_BYTES)
    if head[:4] == b"AC10" and head[4:6].isdigit():
        version = head[:6].decode("ascii")
        return DetectedFormat(FileFormat.DWG, version, f"file starts with {version!r}")
    if head.startswith(b"AutoCAD Binary DXF"):
        return DetectedFormat(FileFormat.DXF_BINARY, None, "binary DXF sentinel")
    if head.startswith(b"%PDF-"):
        return DetectedFormat(FileFormat.PDF, head[5:8].decode("ascii", "replace"), "%PDF header")
    if head.startswith(b"PK\x03\x04"):
        return DetectedFormat(FileFormat.ZIP, None, "zip signature (e.g. KMZ, DOCX)")
    if head.startswith(b"SQLite format 3\x00"):
        return DetectedFormat(FileFormat.SQLITE, None, "SQLite header (e.g. GeoPackage)")
    if head[:4] == b"\x00\x00\x27\x0a":
        return DetectedFormat(FileFormat.SHAPEFILE, None, "shapefile magic number")
    if head.startswith(b"LASF"):
        return DetectedFormat(FileFormat.LAS, None, "LAS point cloud signature")
    if head[:4] in (b"II*\x00", b"MM\x00*"):
        return DetectedFormat(FileFormat.TIFF, None, "TIFF byte order mark")
    if head.startswith(b"\x89PNG"):
        return DetectedFormat(FileFormat.PNG, None, "PNG signature")
    if head.startswith(b"\xff\xd8\xff"):
        return DetectedFormat(FileFormat.JPEG, None, "JPEG signature")
    text = _as_text(head)
    if text is None:
        return DetectedFormat(FileFormat.UNKNOWN, None, "binary, no known signature")
    stripped = text.lstrip("﻿ \t\r\n")
    lines = [ln.strip() for ln in stripped.splitlines()[:2]]
    if lines[:2] == ["0", "SECTION"]:
        version = _dxf_version(text)
        return DetectedFormat(FileFormat.DXF_ASCII, version, "DXF group code 0 SECTION")
    if stripped.startswith("<"):
        if "<LandXML" in text:
            return DetectedFormat(FileFormat.LANDXML, None, "LandXML root element")
        if "<kml" in text:
            return DetectedFormat(FileFormat.KML, None, "KML root element")
        return DetectedFormat(FileFormat.XML, None, "XML text")
    return DetectedFormat(FileFormat.TEXT, None, "plain text (e.g. CSV point list)")


def _as_text(head: bytes) -> str | None:
    if b"\x00" in head:
        return None
    for encoding in ("utf-8", "cp1252"):
        try:
            return head.decode(encoding)
        except UnicodeDecodeError:
            continue
    return None


def _dxf_version(text: str) -> str | None:
    lines = [ln.strip() for ln in text.splitlines()]
    for i, line in enumerate(lines[:-2]):
        if line == "$ACADVER" and lines[i + 1] == "1":
            return lines[i + 2]
    return None
