# Location evidence and environmental research — 2026-10-20

> Current update, 2026-10-20: the owner supplied EPSG:32638 and recognised the calculated map point as their field. [Location, point exports and preliminary environmental assessment](epsg-32638-preview/REPORT.md) now supersede the unresolved-location status below. The CAD investigation remains historical evidence; formal site confirmation is pending.

## Earlier investigation record


Status: exact location unresolved. This is a read-only evidence review and research-source register, not a confirmed site, climate analysis or approved design.

Follow-up after the creator's reported GnaCAD use: an independent native DWG
reader recovered all 27 POINT coordinates directly, matching the ODA extraction.
It also found the default latitude/longitude values in the original DWGs and no
declared UTM zone/datum. See [native-reader findings and coordinate exports](native-dwg/REPORT.md).
The creator is correct that point coordinates exist; their global CRS context
remains unresolved. The software-specific limits below describe the earlier pass.

## Result of the closer inspection

Both current survey originals, `seperated.dwg` and `elevation.dwg`, were inspected through local ODA conversion and ezdxf. Original SHA-256 values were unchanged. The inspection covered all entity-database text, model and paper spaces, blocks, external-reference records, custom header variables, XRECORDs, dictionary variables, and string tags. A native DWG printable-string scan was also performed.

- No GEODATA object or declared coordinate-system/EPSG record was found in the readable CAD data.
- Neither drawing exposed a UTM zone or datum, town/village name, surveyor address, location-bearing external reference or title block.
- `seperated.dwg` contains six point labels. `elevation.dwg` contains 21 labels, including the Persian label `نقطه مبنا` (reference/benchmark point). That label names a survey reference point, not a geographical place.
- The converted drawings expose `$LATITUDE = 37.795` and `$LONGITUDE = -122.394`. Both exactly match the installed ezdxf header defaults. They contradict the owner-reported Iranian region and are not usable site-location evidence. See `default-location-comparison.json`.
- Earlier project notes mention WGS 84 / UTM 38N without a traced source. It remains an unsupported historical assumption and was not assigned or used to retrieve point climate data.

The owner has reported northwestern Iran, in the Zagros Mountains. This provides regional context but does not confirm a survey CRS, datum, parcel pin or true-north alignment. No town was inferred from it.

These conclusions describe what the local CAD reader exposed; the native printable-string scan is not a complete decoder of every compressed DWG record.

## Why grid coordinates alone are insufficient

UTM uses separate six-degree zones, with eastings and northings measured within each zone. A coordinate pair without its zone is not a unique global location. A survey datum is also needed for a defensible survey transformation. [USGS explanation](https://www.usgs.gov/faqs/how-are-utm-coordinates-measured-usgs-topographic-maps).

A map pin would independently locate the parcel for environmental screening. The nearest village could support regional screening and a consistency check, while survey-grade transformation would still require CRS confirmation. Neither would silently approve a gate.

## Sources checked for the environmental assessment

No point climate values, prevailing wind direction or parcel sunlight hours have been calculated or downloaded, because the parcel location is unresolved. The following source capabilities were checked online on 2026-10-20.

| Topic | Source and intended output | Evidence status and limits |
|---|---|---|
| Solar position | [Solar Position Algorithm](https://midcdmz.nlr.gov/spa/) — sun azimuth and altitude through the year | Calculated after a defensible latitude/longitude is available. Relating it to house faces also needs the drawing's true-north alignment. Solar geometry is different from actual sunshine under cloud and obstruction. |
| Solar radiation and mountain horizon | [European Commission PVGIS manual](https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/using-pvgis-5/pvgis-5-user-manual_en) — seasonal radiation and a terrain-horizon screening | PVGIS can account for hills/mountains through horizon data. Nearby buildings, trees, walls and the proposed design require additional obstruction geometry. No parcel-specific horizon has been obtained. |
| Temperature, humidity, precipitation and solar climate | [NASA POWER data documentation](https://power.larc.nasa.gov/docs/faqs/data/) and [parameter documentation](https://power.larc.nasa.gov/docs/tutorials/parameters/) | Satellite/model-derived environmental data; assess the source grid, period and elevation representativeness before using it. These are not observations at the house. |
| Seasonal wind and weather distributions | [Copernicus ERA5 single-level dataset](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels?tab=overview) — wind components and weather time series | Reanalysis atmosphere grid is 0.25 degrees. It provides regional context; a mountain parcel's sheltering, channels and gust exposure cannot be certified from one grid cell. |
| Local observations and design conditions | Appropriate nearby weather-station records and jurisdictional sources, to be identified after location is established | No station has been selected. Historical means are not design wind, snow or structural loads. |

The final assessment should distinguish measured station observations, gridded/reanalysis estimates, calculated solar geometry and assumptions. It should cover seasonal temperatures, precipitation, snow/frost screening, solar access and shading, wind exposure and ventilation opportunity, overheating risk and outdoor comfort. Retaining-wall design, soil/rock, groundwater and slope stability require project-specific evidence; they do not follow from weather lookup alone.

## Minimum next evidence

One useful geographical anchor: a parcel map link/pin, the nearest village/town, or a surveyor's CRS declaration (UTM zone plus datum, ideally EPSG). A nearest-village name supports regional screening; it does not alone establish an exact parcel or legal boundary.

The project remains `SITE_NEEDS_VERIFICATION`. No site facts or approval gates were confirmed by the agent. Original survey files were unchanged; no survey coordinates were sent to external services during this investigation.

## Local evidence files

- `raw-survey-metadata.json`: initial metadata and readable drawing text.
- `deep-survey-metadata.json`: custom records, all string tags, block/xref records and native printable-string scan.
- `default-location-comparison.json`: actual converted header values against library defaults.
- Existing survey audit: `../survey-audit/REPORT.md` and `../../site/inspection/inspection.md`.
