from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd


WORKSPACE = Path(r"D:\profile\research\workspace")
OUT = WORKSPACE / "output" / "person_r02_curb_radial_anchor_pilot_20260831"
PRE = OUT / "pre_reference"
INVENTORY = PRE / "visual_review_frame_inventory.csv"
OPTICAL_HYP = (
    WORKSPACE
    / "output"
    / "person_optical_guided_sar_annotation_full_20260823"
    / "optical_person_frame_hypotheses.parquet"
)

PRIMARY_LOW = 421
PRIMARY_HIGH = 474
NEGATIVE_CONTROLS = {
    "PASSING_VEHICLE_OCCLUSION_AND_NEAR_RANGE_FALSE_CURB": [375, 390, 405, 414],
    "DISPLAY_INTENSITY_SHIFT_AND_MULTIPLE_RANGE_ARCS": [480, 486, 488],
    "EARLY_CURVED_OR_BRANCHING_OPTICAL_CURB": [0, 30, 60],
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def visual_assessment(frame: int) -> dict[str, object]:
    assessment: dict[str, object] = {
        "optical_curb_visible": True,
        "sar_curb_visible": True,
        "sar_curb_candidate_count": 2,
        "visual_confidence": "MEDIUM",
        "ambiguity_reason": "FARTHER_PARALLEL_STATIC_RESPONSE_BANDS",
        "notes": (
            "Near road/sidewalk boundary is visually clear in optical. SAR contains a persistent "
            "lower-middle near-horizontal band plus at least one farther parallel band; physical "
            "identity is not yet assigned."
        ),
        "visual_verdict": "VISUAL_STATIC_BOUNDARY_PLAUSIBLE_SET_VALUED",
    }
    if frame in {0, 30, 60}:
        assessment.update(
            visual_confidence="LOW",
            sar_curb_candidate_count=3,
            ambiguity_reason="OPTICAL_DRIVEWAY_CURVATURE_AND_MULTIPLE_SAR_BANDS",
            notes=(
                "Optical curb bends/branches at the driveway; SAR still has several line-like bands. "
                "This is frozen as an early-run negative control, not a detector-development case."
            ),
            visual_verdict="VISUAL_CURB_AMBIGUOUS_BRANCHING_SCENE_BOUNDARY",
        )
    elif frame in {375, 390, 405, 414}:
        assessment.update(
            optical_curb_visible=frame in {375, 414},
            sar_curb_candidate_count=3,
            visual_confidence="LOW",
            ambiguity_reason="PASSING_VEHICLE_OCCLUSION_AND_STRONG_NEAR_RANGE_REFLECTION",
            notes=(
                "A passing white vehicle occludes the optical curb and creates strong near-range "
                "SAR arcs/ridges that can be mistaken for the static boundary."
            ),
            visual_verdict="VISUAL_CURB_AMBIGUOUS_DYNAMIC_VEHICLE_CONFOUNDER",
        )
    elif frame == 480:
        assessment.update(
            sar_curb_visible=False,
            sar_curb_candidate_count=0,
            visual_confidence="LOW",
            ambiguity_reason="FRAME_LEVEL_DISPLAY_RESPONSE_COLLAPSE",
            notes="Optical curb is clear, but the SAR pseudocolor response is globally weak/dark.",
            visual_verdict="VISUAL_CURB_UNAVAILABLE_WEAK_SAR_FRAME",
        )
    elif frame in {486, 488}:
        assessment.update(
            sar_curb_candidate_count=3,
            visual_confidence="LOW",
            ambiguity_reason="MULTIPLE_STRONG_NEAR_CONCENTRIC_OR_PARALLEL_ARCS",
            notes=(
                "Several strong near-range arcs coexist with the expected horizontal static band; "
                "single-line selection would be unsafe."
            ),
            visual_verdict="VISUAL_CURB_AMBIGUOUS_MULTIPLE_STRONG_ARCS",
        )
    elif PRIMARY_LOW <= frame <= PRIMARY_HIGH:
        assessment.update(
            visual_confidence="MEDIUM_HIGH",
            notes=(
                "Primary stable-window case. Optical near roadside curb is clear. SAR lower-middle "
                "near-horizontal static band is persistent, but farther parallel structures remain "
                "a physical-identity confounder."
            ),
            visual_verdict="VISUAL_PRIMARY_WINDOW_STATIC_BOUNDARY_PLAUSIBLE_SET_VALUED",
        )
    return assessment


def main() -> None:
    inventory = pd.read_csv(INVENTORY)
    inventory = inventory.sort_values("sar_frame_index").drop_duplicates("sar_frame_index")
    rows: list[dict[str, object]] = []
    for item in inventory.itertuples(index=False):
        assessment = visual_assessment(int(item.sar_frame_index))
        rows.append(
            {
                "run_id": "R02ZF",
                "sar_frame_index": int(item.sar_frame_index),
                "optical_frame_index": int(item.optical_frame_index),
                "sar_timestamp_ms": int(item.sar_timestamp_ms),
                "optical_timestamp_ms": int(item.optical_timestamp_ms),
                "timestamp_delta_ms": int(item.timestamp_delta_ms),
                **assessment,
                "computed_verdict": "NOT_RUN_AT_VISUAL_FREEZE",
                "provenance": "DIRECT_MULTIFRAME_VISUAL_REVIEW_20260831",
            }
        )
    ledger = pd.DataFrame(rows)
    ledger.to_csv(PRE / "CURB_VISUAL_HYPOTHESIS_LEDGER.csv", index=False, encoding="utf-8-sig")

    optical = pd.read_parquet(OPTICAL_HYP)
    optical = optical[
        optical.run_id.eq("R02ZF")
        & optical.frame_index.between(251, 284)
    ].copy()
    optical["topology_label"] = "SIDEWALK_OR_PARKING_SIDE"
    optical["topology_definition"] = (
        "PERSON candidate is visually beyond the near roadside curb, on the sidewalk/planting/parking side; "
        "therefore only the farther-than-curb SAR half-space is provisionally legal."
    )
    optical["topology_confidence"] = optical.apply(
        lambda row: "MEDIUM" if row.box_source == "INTERPOLATED_SHORT_GAP" or row.confidence < 0.30 else "HIGH",
        axis=1,
    )
    optical["topology_semantics"] = "VISUAL_DEVELOPMENT_ONLY_NOT_RUNTIME_CLASSIFIER"
    optical["curb_direction_basis"] = (
        "Camera/radar platform is on the foreground road side; the reviewed near curb separates that road "
        "from the farther sidewalk/planting/parking side. Direction is established from images, not image-up/down alone."
    )
    optical["manual_reference_used"] = False
    topology_columns = [
        "run_id",
        "frame_index",
        "timestamp_ms",
        "raw_track_fragment_id",
        "optical_person_id",
        "box_source",
        "confidence",
        "bbox_x1",
        "bbox_y1",
        "bbox_x2",
        "bbox_y2",
        "topology_label",
        "topology_confidence",
        "topology_definition",
        "topology_semantics",
        "curb_direction_basis",
        "manual_reference_used",
    ]
    optical[topology_columns].to_csv(
        PRE / "optical_person_curb_topology_visual_development_only.csv",
        index=False,
        encoding="utf-8-sig",
    )

    selection = {
        "run_id": "R02ZF",
        "primary_analysis_window_sar_frames_inclusive": [PRIMARY_LOW, PRIMARY_HIGH],
        "primary_window_reason": (
            "Visually stable SAR/optical interval after the passing-vehicle disturbance and before the "
            "F480 display-response collapse; it also contains the dense optical PERSON interval."
        ),
        "negative_controls": NEGATIVE_CONTROLS,
        "additional_context_frames": [95, 110, 120, 150, 155, 180, 210, 240, 260, 270, 300, 330, 345, 360],
        "selection_semantics": "GT_BLIND_VISUAL_PRE_REFERENCE_FIXED_BEFORE_AUTOMATIC_CURB_EXTRACTION",
        "pairing_semantics": "NOMINAL_INDEX_FPS_ZERO_OFFSET_UNVERIFIED",
        "manual_sar_reference_opened": False,
        "r04_accessed": False,
    }
    (PRE / "case_control_selection_pre_reference.json").write_text(
        json.dumps(selection, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    freeze_files = [
        PRE / "CURB_VISUAL_HYPOTHESIS_LEDGER.csv",
        PRE / "optical_person_curb_topology_visual_development_only.csv",
        PRE / "case_control_selection_pre_reference.json",
        PRE / "visual_review_frame_inventory.csv",
        PRE / "visual_review_generation_summary.json",
    ]
    hashes = [
        {"path": str(path.relative_to(OUT)).replace("\\", "/"), "sha256": sha256(path), "bytes": path.stat().st_size}
        for path in freeze_files
    ]
    (PRE / "visual_hypothesis_freeze_manifest.json").write_text(
        json.dumps(
            {
                "freeze_semantics": "VISUAL_HYPOTHESES_AND_CASE_SELECTION_FROZEN_BEFORE_AUTOMATIC_CURB_EXTRACTION",
                "manual_sar_reference_opened": False,
                "r04_accessed": False,
                "files": hashes,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"visual rows={len(ledger)} topology rows={len(optical)}")


if __name__ == "__main__":
    main()
