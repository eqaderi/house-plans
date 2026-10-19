"""S8 terrain quantities wired into the existing SiteEvaluator report."""

from house_ai.domain.epistemics import ClaimStatus
from house_ai.domain.program import Strength
from house_ai.geospatial.hillside import hillside_report


def terrain_metrics(ctx, out):
    report = hillside_report(ctx.model, ctx.site)
    works = report["earthworks"]
    if report["geometry_error"]:
        out.violation(
            "invalid_terrain_earthworks",
            Strength.HARD,
            report["geometry_error"],
            [],
            ClaimStatus.MEASURED,
        )
    inf, nc, measured = ClaimStatus.INFERRED, ClaimStatus.NOT_CHECKED, ClaimStatus.MEASURED
    method = works["method"]
    for name, unit in (
        ("excavation_volume_m3", "m3"),
        ("underfloor_void_volume_m3", "m3"),
        ("engineered_fill_volume_m3", "m3"),
        ("max_cut_m", "m"),
        ("max_underfloor_void_height_m", "m"),
    ):
        out.metric(name, works[name], method, inf if works[name] is not None else nc, unit=unit)
    out.metric(
        "terrain_coverage_pct", works["coverage_pct"], "triangle_union_intersection", unit="%"
    )
    out.metric(
        "unknown_terrain_footprint_m2",
        works["unknown_area_m2"],
        "footprint_minus_triangle_support",
        unit="m2",
    )
    for region in works["regions"]:
        subjects = [region["level_id"]]
        if region["floor_basis"].startswith("underside:"):
            subjects.append(region["floor_basis"].split(":", 1)[1])
        for metric, key, unit in (
            ("underfloor_area_void_m3", "underfloor_void_volume_m3", "m3"),
            ("underfloor_area_max_clear_height_m", "max_void_height_m", "m"),
        ):
            out.metric(
                metric,
                region[key],
                method,
                inf if region[key] is not None else nc,
                unit=unit,
                subjects=subjects,
            )
    if works["unknown_area_m2"] > 1e-8:
        out.violation(
            "terrain_coverage_incomplete",
            Strength.SOFT,
            f"Surveyed TIN covers {works['coverage_pct']:.1f}% of footprint. "
            "Quantities cover only known support; remaining terrain is unknown.",
            [],
            inf,
        )
    max_void = works["max_underfloor_void_height_m"]
    if max_void is not None and max_void > 0.6:
        out.violation(
            "elevated_floor_support_unresolved",
            Strength.SOFT,
            f"Underfloor void is {works['underfloor_void_volume_m3']:.1f} m³, "
            f"maximum {max_void:.2f} m. This is not specified engineered fill; "
            "supports, lateral stability, foundations and drainage unresolved.",
            [],
            inf,
        )
    if max_void is not None and max_void > report["settings"]["large_void_height_m"]:
        out.violation(
            "large_underfloor_void",
            Strength.SOFT,
            f"Void clear height {max_void:.2f} m exceeds configured "
            f"{report['settings']['large_void_height_m']:g} m concept-review trigger.",
            [],
            inf,
        )
    retaining = report["retaining_candidates"]
    total_area = sum(r["face_area_m2"] or 0 for r in retaining)
    retaining_complete = report["retaining_assessment_complete"]
    out.metric(
        "retaining_wall_length_m",
        sum(r["length_m"] for r in retaining),
        "earth_contact_candidate_wall_lengths",
        inf if retaining_complete else nc,
        unit="m",
    )
    out.metric(
        "retaining_wall_face_area_m2",
        total_area,
        method,
        inf if retaining_complete else nc,
        unit="m2",
    )
    for r in retaining:
        subjects = [r["wall_id"]]
        for key in (
            "length_m",
            "known_length_m",
            "max_retained_height_m",
            "mean_retained_height_m",
            "face_area_m2",
        ):
            out.metric(
                "retaining_" + key,
                r[key],
                "piecewise_linear_positive_height_integral",
                inf if r[key] is not None else nc,
                unit="m2" if "area" in key else "m",
                subjects=subjects,
            )
    for door in report["doors"]:
        for name, key in (
            ("exterior_door_ground_delta_m", "delta_m"),
            ("exterior_door_ground_z_m", "ground_z_m"),
        ):
            out.metric(
                name,
                door[key],
                "tin_0_5m_outside_door",
                inf if door[key] is not None else nc,
                unit="m",
                subjects=[door["door_id"]],
            )
        if door["outside_level_change_needed"]:
            out.violation(
                "exterior_access_level_unresolved",
                Strength.SOFT,
                f"Threshold differs from outside ground by {door['delta_m']:+.2f} m; "
                "steps, ramp or excavated approach need design.",
                [door["door_id"]],
                inf,
            )
    out.metric(
        "outdoor_level_changes_requiring_design",
        report["outdoor_level_changes_count"],
        "exterior_threshold_trigger_count",
        inf if report["outdoor_level_changes_count"] is not None else nc,
        unit="count",
    )
    out.metric(
        "known_outdoor_level_changes_requiring_design",
        report["known_outdoor_level_changes_count"],
        "known_threshold_trigger_count",
        inf,
        unit="count",
    )
    out.metric(
        "unchecked_exterior_doors_count",
        report["unchecked_exterior_doors_count"],
        "unknown_threshold_coverage_count",
        measured,
        unit="count",
    )
    out.metric(
        "indoor_stairs_count",
        report["indoor_stairs_count"],
        "canonical_stair_count",
        measured,
        unit="count",
    )
    for garage in report["garages"]:
        for name, key, unit in (
            ("garage_frontage_ground_z_m", "frontage_z_m", "m"),
            ("garage_frontage_delta_m", "delta_m", "m"),
            ("garage_candidate_ramp_run_m", "candidate_run_m", "m"),
            ("garage_candidate_ramp_grade_pct", "candidate_grade_pct", "%"),
        ):
            out.metric(
                name,
                garage[key],
                garage["method"],
                inf if garage[key] is not None else nc,
                unit=unit,
                subjects=[garage["garage_id"]],
            )
        grade = garage["candidate_grade_pct"]
        if grade is not None and abs(grade) > report["settings"]["vehicle_grade_trigger_pct"]:
            out.violation(
                "garage_ramp_grade_review",
                Strength.SOFT,
                f"Straight candidate grade {grade:+.1f}% exceeds configured concept "
                "trigger; no designed ramp or regulatory compliance established.",
                [garage["garage_id"]],
                inf,
            )
    for risk in report["risks"]:
        out.violation(
            "needs_professional_" + risk["discipline"],
            Strength.SOFT,
            risk["trigger"] + " — needs professional.",
            risk["subject_ids"],
            inf,
        )
    for face in report["buried_habitable_faces"]:
        out.violation(
            "buried_habitable_face",
            Strength.SOFT,
            "Buried face reduces daylight capability; waterproofing needs professional.",
            [face["wall_id"], *face["space_ids"]],
            inf,
        )
    for quality in report["terrain_quality"]:
        out.violation(
            "terrain_triangle_review",
            Strength.SOFT,
            f"Triangle {quality['triangle_index']} at {quality['xy']}: "
            f"{', '.join(quality['triggers'])}; survey review needed, no smoothing.",
            [],
            measured,
        )
    elevations = sorted({lv.elevation_m for lv in ctx.model.levels})
    out.metric("level_elevations_m", ", ".join(f"{z:.2f}" for z in elevations), "level_lookup")
    grounds = [r for r in works["regions"] if r["ground_min_m"] is not None]
    if grounds:
        low, high = min(r["ground_min_m"] for r in grounds), max(r["ground_max_m"] for r in grounds)
        out.metric("ground_relief_under_footprint_m", high - low, method, inf, unit="m")
        top = max(lv.elevation_m + (lv.floor_to_floor_m or 3) for lv in ctx.model.levels)
        out.metric("height_above_lowest_ground_m", top - low, method, inf, unit="m")
        env = ctx.site.buildable_envelope if ctx.site else None
        if env and env.max_height_m and top - low > env.max_height_m:
            out.violation(
                "height_limit_exceeded",
                Strength.HARD if env.status.value == "verified_fact" else Strength.SOFT,
                f"Height {top - low:.2f} m exceeds envelope {env.max_height_m:g} m.",
                [],
                inf,
            )
