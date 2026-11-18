# Independent native-DWG coordinate investigation — 2026-10-20

> Current update, 2026-10-20: the owner supplied EPSG:32638 and recognised the calculated map point as their field. [Location, point exports and preliminary environmental assessment](../epsg-32638-preview/REPORT.md) now supersede the unresolved-location status below. The CAD investigation remains historical evidence; formal site confirmation is pending.

## Earlier investigation record


## What was checked

The homeowner relayed that the survey creator can see point coordinates in GnaCAD on Android and identifies the survey as UTM. The full owner statement is retained in the project store. This report separates that statement from measurements of the supplied files.

GNU LibreDWG `dwgread 0.14` was installed as a standalone diagnostic utility and used to read both original DWGs directly into JSON, without passing through ODA/DXF. Both reads returned exit code 0 with SUCCESS logs. Original SHA-256 values were unchanged. No new application dependency or pipeline integration was added.

LibreDWG documents its JSON as a mapping of native DWG structures carrying information beyond DXF. This makes it an independent check against the previous converter path. [GNU JSON documentation](https://www.gnu.org/software/libredwg/manual/html_node/JSON.html).

## Verified coordinate extraction

| File | Native POINT entities | Same handles in ODA path | Largest coordinate component difference (source units) |
|---|---:|---|---:|
| seperated.dwg | 6 | True | 9.31322574615e-10 |
| elevation.dwg | 21 | True | 9.31322574615e-10 |

All 27 source-frame X/Y/Z point coordinates agree between the independent readers within 1e-8 source units. Both drawings declare metres through INSUNITS=6; the tool still awaits human unit confirmation. This numerical agreement validates extraction, not the survey accuracy or georeferencing.

Example directly from elevation.dwg POINT entity 69 (hexadecimal handle):

- X: 623841.289
- Y: 3870489.527
- Z: 1664.884

The complete point list is in `point-coordinates.csv`. Eleven LWPOLYLINE vertex records, including a repeated boundary-closing vertex, are separately in `polyline-vertices.csv`. Their stored polyline elevation is a CAD entity elevation, not a surveyed ground elevation at each vertex.

## Native metadata findings

- No GEODATA or GEOPOSITIONMARKER object was found; neither file declares such a class.
- All POINT entities have no extended entity data and no extension dictionary, so the native POINT records expose X/Y/Z without an attached second geographic-coordinate record.
- Native SummaryInfo has no title, subject, keywords or comments that identify a place or CRS.
- No UTM zone/datum/EPSG declaration was found in decoded headers, object/class records, dictionaries or summary data.
- Both original DWG headers also contain latitude 37.795, longitude -122.394 and timezone -8000. This independently establishes that the values pre-date the ODA conversion. The latitude/longitude values exactly match the software defaults already documented in `../default-location-comparison.json` and contradict the owner-reported Iranian region. They are not usable parcel geolocation evidence.

## How this relates to GnaCAD

The creator is correct that point coordinates are present. A CAD app displaying these X/Y/Z values is consistent with the supplied files. It has not been established that GnaCAD is displaying latitude/longitude, a full UTM zone designation, or a CRS stored in these files.

Autodesk documents drawing point coordinates as X/Y/Z, and separately documents geographic latitude/longitude retrieval. This distinction supports the interpretation question; it is not proof of GnaCAD-specific behavior. [Drawing coordinates](https://www.autodesk.com/support/technical/article/caas/sfdcarticles/sfdcarticles/Locating-the-current-coordinates-of-a-point.html), [geographic coordinates](https://www.autodesk.com/support/technical/article/caas/sfdcarticles/sfdcarticles/How-to-obtain-the-geographical-coordinates-of-a-point-in-AutoCAD.html).

The developer-site URL found in search returned a Firebase hosting placeholder; Google Play returned HTTP 404 and the Apple lookup returned no result. No authoritative current GnaCAD documentation establishing geographic conversion was obtained, and the app itself was not run. Third-party APK mirrors and online DWG viewers were not used for private survey data.

## Remaining evidence needed

A subsequent owner reply offered a Google Maps point known to lie inside the
parcel, without access to GnaCAD. This is a useful independent geographical
anchor: it can locate the area for regional environmental research and support
checking projection candidates against the survey. An approximate interior pin
does not identify a surveyed control point or certify the original datum, exact
boundary alignment or centimetre accuracy. A recognisable surveyed corner or
feature would provide a stronger correspondence. No pin/link has been supplied
yet; no projection candidate has been selected or applied.

A screenshot or copied field labels and values from the actual GnaCAD point panel would allow direct comparison with the exported records. If it shows X/Y/Z as above, ask the creator for the UTM zone and datum, or one independently identified geographic reference point. If it shows latitude/longitude or a full CRS label, preserve that as new evidence and check it against the drawing before assigning anything.

The [NGA coordinate-systems reference](https://earth-info.nga.mil/?action=coordsys&dir=coordsys) describes UTM as a family of zone/hemisphere projections. UTM eastings/northings without the necessary projection context do not establish an exact worldwide parcel location.

No CRS was guessed, no coordinate transformation was applied, no private survey data were uploaded, and no site or approval gate was confirmed. The earlier owner-interview confirmations remain unchanged.

## Reproduction

```sh
dwgread -O JSON -o <scratch>/seperated.json projects/my-house/surveys/seperated.dwg
dwgread -O JSON -o <scratch>/elevation.json projects/my-house/surveys/elevation.dwg
```

Local outputs: source DWG JSON, reader logs, `read-results.json`, `comparison.json`, `point-coordinates.csv`, `polyline-vertices.csv`. These are private derived inspection exports, not replacements for the canonical site model.
