#!/usr/bin/env python
"""Phase5B source precheck and frozen config draft.

This precheck verifies inference-side source availability for a later Phase5B
diagnostic proposal run. It does not generate proposals or candidates.
"""

from __future__ import annotations

import csv
import json
import struct
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

PHASE4D_TARGET_PATH = ROOT / "output" / "gm17_phase4D_candidate_pool_ceiling_audit_20260629_001655" / "candidate_pool_ceiling_per_target.csv"
A005_PROXY_PATH = ROOT / "output" / "clean_no_gt_localizer_2026-05-31_boundary_tables" / "gm17_temporal_inference.csv"
GRAY_SAR_ROOT = Path(r"D:\profile\research\data\GM_RM017\GM_RM017_SARframes_gray")

TARGET_ALLOWED_FIELDS = [
    "target_identity",
    "scene",
    "sar_frame_num",
    "gm17_track_id",
]

A005_ALLOWED_FIELDS = [
    "target_identity",
    "scene",
    "sar_frame",
    "sar_frame_num",
    "sar_pseudocolor_path",
    "pred_cx",
    "pred_cy",
    "pred_w",
    "pred_h",
    "pred_r",
    "pred_az",
    "pred_cross",
    "gm17_track_id",
]

FORBIDDEN_A005_FIELDS = [
    "score",
    "lr_score",
    "sar_factor_score",
    "temporal_factor_score",
    "gm17_temporal_decision",
]

FORBIDDEN_TARGET_FIELDS = [
    "selection_limited",
    "oracle_usable",
    "oracle_high_quality",
    "pool_limited",
    "best_iou",
    "best_center_error",
    "c3_rank1_iou",
    "c3_rank1_center_error",
    "c4_rank1_iou",
    "c4_rank1_center_error",
    "failure_class",
    "diagnostic_label_boundary",
]


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def norm_text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def frame_stem(row: dict[str, str]) -> str:
    sar_frame = norm_text(row.get("sar_frame"))
    if sar_frame:
        return Path(sar_frame).stem
    frame_num = norm_text(row.get("sar_frame_num"))
    if not frame_num:
        return ""
    try:
        return f"{int(float(frame_num)):06d}"
    except ValueError:
        return frame_num


def png_dimensions(path: Path) -> tuple[int | None, int | None, str]:
    if not path.exists():
        return None, None, "missing"
    try:
        with path.open("rb") as f:
            header = f.read(24)
        if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
            return None, None, "not_png"
        width, height = struct.unpack(">II", header[16:24])
        return width, height, "ok"
    except OSError as exc:
        return None, None, f"read_error:{exc}"


def clean_path(value: str) -> Path | None:
    text = norm_text(value)
    if not text:
        return None
    return Path(text)


def main() -> None:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    freeze_timestamp = datetime.now().isoformat(timespec="seconds")
    out_dir = ROOT / "output" / f"phase5B_precheck_sources_and_config_{timestamp}"
    out_dir.mkdir(parents=True, exist_ok=False)

    target_rows_raw = read_csv_rows(PHASE4D_TARGET_PATH)
    a005_rows_raw = read_csv_rows(A005_PROXY_PATH)

    target_rows = [{field: norm_text(row.get(field)) for field in TARGET_ALLOWED_FIELDS} for row in target_rows_raw]
    a005_rows = [{field: norm_text(row.get(field)) for field in A005_ALLOWED_FIELDS} for row in a005_rows_raw]

    a005_by_target: dict[str, list[dict[str, str]]] = {}
    for row in a005_rows:
        a005_by_target.setdefault(row["target_identity"], []).append(row)

    duplicate_targets = sorted([target for target, rows in a005_by_target.items() if len(rows) > 1])
    duplicate_count = len(duplicate_targets)

    missing_rows: list[dict[str, str]] = []
    shell_rows: list[dict[str, Any]] = []
    target_freeze_rows: list[dict[str, Any]] = []
    dimension_counter: Counter[tuple[int | None, int | None]] = Counter()
    grayscale_available_count = 0
    pseudocolor_available_count = 0
    selected_gray_count = 0
    selected_pseudocolor_count = 0
    image_problem_rows: list[dict[str, Any]] = []

    for target in target_rows:
        target_identity = target["target_identity"]
        matches = a005_by_target.get(target_identity, [])
        if not matches:
            missing_rows.append(target)
            continue
        a005 = matches[0]

        stem = frame_stem(a005)
        grayscale_path = GRAY_SAR_ROOT / f"{stem}.png" if stem else Path("")
        pseudocolor_path = clean_path(a005.get("sar_pseudocolor_path"))

        gray_w, gray_h, gray_status = png_dimensions(grayscale_path) if stem else (None, None, "missing_frame_stem")
        pseudo_w, pseudo_h, pseudo_status = png_dimensions(pseudocolor_path) if pseudocolor_path else (None, None, "missing_path")

        gray_exists = gray_status == "ok"
        pseudo_exists = pseudo_status == "ok"
        if gray_exists:
            grayscale_available_count += 1
        if pseudo_exists:
            pseudocolor_available_count += 1

        if gray_exists:
            selected_image_source_id = "gm17_sarframes_gray_display_png"
            image_width, image_height = gray_w, gray_h
            selected_gray_count += 1
        elif pseudo_exists:
            selected_image_source_id = "gm17_sarframes_pseudocolor_display_png"
            image_width, image_height = pseudo_w, pseudo_h
            selected_pseudocolor_count += 1
        else:
            selected_image_source_id = "missing_sar_image_source"
            image_width, image_height = None, None

        dimension_counter[(image_width, image_height)] += 1
        if selected_image_source_id == "missing_sar_image_source" or (gray_exists and pseudo_exists and (gray_w, gray_h) != (pseudo_w, pseudo_h)):
            image_problem_rows.append(
                {
                    "target_identity": target_identity,
                    "scene": a005["scene"],
                    "sar_frame_num": a005["sar_frame_num"],
                    "grayscale_path": str(grayscale_path) if stem else "",
                    "grayscale_status": gray_status,
                    "pseudocolor_path": str(pseudocolor_path) if pseudocolor_path else "",
                    "pseudocolor_status": pseudo_status,
                    "selected_image_source_id": selected_image_source_id,
                    "gray_width": gray_w,
                    "gray_height": gray_h,
                    "pseudocolor_width": pseudo_w,
                    "pseudocolor_height": pseudo_h,
                }
            )

        target_freeze_rows.append(
            {
                "target_set_id": "phase4D_gm_rm017_205_target_set",
                "target_identity": target_identity,
                "scene": target["scene"],
                "sar_frame_num": target["sar_frame_num"],
                "gm17_track_id": target["gm17_track_id"],
                "source_phase": "Phase4D_candidate_pool_ceiling_audit",
                "source_path": str(PHASE4D_TARGET_PATH.relative_to(ROOT)),
                "include_flag": "true",
                "freeze_timestamp": freeze_timestamp,
                "leakage_boundary_note": "identity_frame_track_only_no_oracle_iou_center_error_failure_labels",
            }
        )

        shell_rows.append(
            {
                "shell_source_id": "gm17_temporal_inference_proxy",
                "target_identity": target_identity,
                "scene": a005["scene"],
                "sar_frame_num": a005["sar_frame_num"],
                "gm17_track_id": a005["gm17_track_id"],
                "shell_cx": a005["pred_cx"],
                "shell_cy": a005["pred_cy"],
                "shell_w_prior": a005["pred_w"],
                "shell_h_prior": a005["pred_h"],
                "pred_r": a005["pred_r"],
                "pred_az": a005["pred_az"],
                "pred_cross": a005["pred_cross"],
                "sar_pseudocolor_path": a005["sar_pseudocolor_path"],
                "grayscale_path": str(grayscale_path) if stem else "",
                "selected_image_source_id": selected_image_source_id,
                "image_width": image_width if image_width is not None else "",
                "image_height": image_height if image_height is not None else "",
                "leakage_audit_status": "pre_inference_allowed_fields_only_scores_decisions_eval_labels_excluded",
                "diagnostic_only_flag": "true",
            }
        )

    target_count = len(target_rows)
    join_success_count = len(shell_rows)
    missing_count = len(missing_rows)
    consistent_dims = 0
    if dimension_counter:
        consistent_dims = dimension_counter.most_common(1)[0][1]
    consistent_image_dimension_rate = consistent_dims / target_count if target_count else 0.0

    blockers: list[str] = []
    if missing_count:
        blockers.append("A005 proxy rows are missing for some targets")
    if duplicate_count:
        blockers.append("A005 proxy table has duplicate target_identity rows")
    if join_success_count != target_count:
        blockers.append("target set cannot be fully joined to A005 proxy")
    if grayscale_available_count != target_count:
        blockers.append("preferred grayscale display PNG is not available for every target")
    if pseudocolor_available_count != target_count:
        blockers.append("fallback pseudocolor PNG is not available for every target")
    if consistent_image_dimension_rate < 1.0:
        blockers.append("selected image dimensions are not fully consistent")

    # This precheck intentionally leaves route parameter values as TBD, so the
    # later implementation remains PARTIAL until a reviewed config fills them.
    blockers.extend(
        [
            "crop_policy_id remains TBD_before_implementation",
            "shell_margin_or_crop_size remains TBD_before_implementation",
            "scale_set remains TBD_before_implementation",
            "offset_grid remains TBD_before_implementation",
            "energy_peak_count remains TBD_before_implementation",
            "component_threshold_family remains TBD_before_implementation",
        ]
    )

    core_sources_ready = (
        target_count > 0
        and missing_count == 0
        and duplicate_count == 0
        and join_success_count == target_count
        and (grayscale_available_count == target_count or pseudocolor_available_count == target_count)
        and consistent_image_dimension_rate == 1.0
    )
    implementation_readiness = "PARTIAL" if core_sources_ready else "BLOCKED"

    target_fields = [
        "target_set_id",
        "target_identity",
        "scene",
        "sar_frame_num",
        "gm17_track_id",
        "source_phase",
        "source_path",
        "include_flag",
        "freeze_timestamp",
        "leakage_boundary_note",
    ]
    shell_fields = [
        "shell_source_id",
        "target_identity",
        "scene",
        "sar_frame_num",
        "gm17_track_id",
        "shell_cx",
        "shell_cy",
        "shell_w_prior",
        "shell_h_prior",
        "pred_r",
        "pred_az",
        "pred_cross",
        "sar_pseudocolor_path",
        "grayscale_path",
        "selected_image_source_id",
        "image_width",
        "image_height",
        "leakage_audit_status",
        "diagnostic_only_flag",
    ]

    write_csv(out_dir / "target_set_freeze.csv", target_freeze_rows, target_fields)
    write_csv(out_dir / "shell_proxy_inventory.csv", shell_rows, shell_fields)
    write_csv(out_dir / "a005_missing_rows.csv", missing_rows, TARGET_ALLOWED_FIELDS)
    write_csv(
        out_dir / "image_source_precheck_issues.csv",
        image_problem_rows,
        [
            "target_identity",
            "scene",
            "sar_frame_num",
            "grayscale_path",
            "grayscale_status",
            "pseudocolor_path",
            "pseudocolor_status",
            "selected_image_source_id",
            "gray_width",
            "gray_height",
            "pseudocolor_width",
            "pseudocolor_height",
        ],
    )

    source_inventory_rows = [
        {
            "source_id": "phase4D_gm_rm017_205_target_set",
            "source_path": str(PHASE4D_TARGET_PATH.relative_to(ROOT)),
            "role": "target set identity/frame/track source",
            "allowed_fields": "|".join(TARGET_ALLOWED_FIELDS),
            "forbidden_fields": "|".join(FORBIDDEN_TARGET_FIELDS),
            "status": "ready" if target_count else "blocked",
            "diagnostic_only_note": "Phase4D metrics and failure labels are not read into config",
        },
        {
            "source_id": "gm17_temporal_inference_proxy",
            "source_path": str(A005_PROXY_PATH.relative_to(ROOT)),
            "role": "preferred proxy shell source",
            "allowed_fields": "|".join(A005_ALLOWED_FIELDS),
            "forbidden_fields": "|".join(FORBIDDEN_A005_FIELDS),
            "status": "ready" if missing_count == 0 and duplicate_count == 0 else "blocked",
            "diagnostic_only_note": "A005 score and decision fields are excluded",
        },
        {
            "source_id": "gm17_sarframes_gray_display_png",
            "source_path": str(GRAY_SAR_ROOT),
            "role": "preferred SAR display image source",
            "allowed_fields": "frame-stem-derived path only",
            "forbidden_fields": "image-derived energy|component|threshold outputs",
            "status": "ready" if grayscale_available_count == target_count else "partial",
            "diagnostic_only_note": "only PNG existence and dimensions are checked",
        },
        {
            "source_id": "gm17_sarframes_pseudocolor_display_png",
            "source_path": "A005 sar_pseudocolor_path",
            "role": "fallback SAR display image source",
            "allowed_fields": "sar_pseudocolor_path",
            "forbidden_fields": "image-derived energy|component|threshold outputs",
            "status": "ready" if pseudocolor_available_count == target_count else "partial",
            "diagnostic_only_note": "only PNG existence and dimensions are checked",
        },
    ]
    write_csv(
        out_dir / "source_inventory_readiness_summary.csv",
        source_inventory_rows,
        ["source_id", "source_path", "role", "allowed_fields", "forbidden_fields", "status", "diagnostic_only_note"],
    )

    config_draft = {
        "experiment_id": "TBD_before_implementation",
        "target_set_id": "phase4D_gm_rm017_205_target_set",
        "shell_source_id": "gm17_temporal_inference_proxy",
        "shell_source_path": str(A005_PROXY_PATH.relative_to(ROOT)),
        "sar_image_source_id": "gm17_sarframes_gray_display_png" if grayscale_available_count == target_count else "gm17_sarframes_pseudocolor_display_png",
        "sar_image_source_path_policy": str(GRAY_SAR_ROOT / "<sar_frame>.png"),
        "sar_image_fallback_source_id": "gm17_sarframes_pseudocolor_display_png",
        "sar_image_fallback_path_field": "sar_pseudocolor_path",
        "valid_support_source_id": "image_bounds_only_display_png",
        "coordinate_convention_id": "full_image_xy_display_png_v1",
        "route_list": ["shell_grid", "energy_contrast_peak", "connected_component"],
        "route_config_id": "TBD_before_implementation",
        "crop_policy_id": "TBD_before_implementation",
        "max_proposals_per_target": "TBD_before_implementation",
        "shell_margin_or_crop_size": "TBD_before_implementation",
        "scale_set": "TBD_before_implementation",
        "offset_grid": "TBD_before_implementation",
        "energy_peak_count": "TBD_before_implementation",
        "local_background_policy": "TBD_before_implementation",
        "component_threshold_family": "TBD_before_implementation",
        "component_size_filter": "TBD_before_implementation",
        "duplicate_merge_policy": "TBD_before_implementation",
        "output_bundle_id": "TBD_before_implementation",
        "leakage_audit_policy": "pre_inference_fields_only_no_A019_A021_GT_oracle_panel",
        "draft_boundary_note": "precheck_only_no_proposal_no_candidate_no_A019_A021_join_no_metrics",
    }
    write_json(out_dir / "proposal_config_draft.json", config_draft)

    leakage_checklist = {
        "allowed_fields": {
            "phase4D_target_source": TARGET_ALLOWED_FIELDS,
            "a005_temporal_proxy": A005_ALLOWED_FIELDS,
            "image_source": ["path_exists", "png_width", "png_height"],
        },
        "forbidden_fields": sorted(set(FORBIDDEN_A005_FIELDS + FORBIDDEN_TARGET_FIELDS)),
        "forbidden_tables": [
            "output/hermes_annotation_consolidation_2026-05-20/00_tables/final_gt_working.csv",
            "output/hermes_annotation_consolidation_2026-05-20/00_tables/visibility_condition_working.csv",
            "candidate_oracle_eval.csv",
            "any A019/A021/GT/oracle/panel review table",
        ],
        "post_hoc_only_tables": [
            "A019 final boxes",
            "A021 condition labels",
            "Phase4D oracle and metric columns",
        ],
        "generation_boundary": "This precheck does not generate proposals or candidates. Future generation may read only pre-inference fields declared in proposal_config_draft.json.",
        "phase5C_join_boundary": "A019/A021/GT/oracle metrics may be joined only after an approved proposal output is frozen. They cannot modify Phase5B route config or thresholds for the same run.",
    }
    write_json(out_dir / "leakage_audit_checklist.json", leakage_checklist)

    readiness_summary = {
        "run_timestamp": timestamp,
        "target_count": target_count,
        "a005_join_success_count": join_success_count,
        "a005_missing_count": missing_count,
        "a005_duplicate_target_identity_count": duplicate_count,
        "grayscale_available_count": grayscale_available_count,
        "pseudocolor_available_count": pseudocolor_available_count,
        "selected_gray_count": selected_gray_count,
        "selected_pseudocolor_count": selected_pseudocolor_count,
        "consistent_image_dimension_rate": consistent_image_dimension_rate,
        "common_selected_image_dimensions": [
            {"width": width, "height": height, "count": count}
            for (width, height), count in dimension_counter.most_common()
        ],
        "implementation_readiness": implementation_readiness,
        "blockers": blockers,
        "route_A_readiness": "PARTIAL" if core_sources_ready else "BLOCKED",
        "route_B_readiness": "PARTIAL" if core_sources_ready else "BLOCKED",
        "route_C_readiness": "PARTIAL" if core_sources_ready else "BLOCKED",
        "route_D_readiness": "BLOCKED",
        "boundary_assertions": {
            "proposal_generated": False,
            "candidate_generated": False,
            "a019_a021_joined": False,
            "gt_oracle_metrics_computed": False,
            "c3_c4_changed": False,
            "threshold_tuned": False,
            "model_trained": False,
            "calibration_performed": False,
        },
    }
    write_json(out_dir / "readiness_summary.json", readiness_summary)

    docs_path = ROOT / "docs" / f"phase5B_precheck_sources_and_config_summary_{timestamp}.md"
    docs_text = f"""# Phase5B Precheck Sources And Config Summary

Date: {timestamp}

## Purpose

This is a source precheck and frozen config draft for a later Phase5B first diagnostic run. It is not Phase5B proposal implementation.

No proposal was generated. No candidate was generated. No A019/A021 table was read or joined. No GT/oracle metrics were computed.

## Inputs Checked

- Target identity/frame/track source: `{PHASE4D_TARGET_PATH.relative_to(ROOT)}`
- A005 proxy source: `{A005_PROXY_PATH.relative_to(ROOT)}`
- Preferred SAR image source: `{GRAY_SAR_ROOT}`
- Fallback SAR image source: A005 `sar_pseudocolor_path`

Only allowed identity, frame, proxy-shell, and image-path/dimension fields were used.

## Join Result

- Target count: {target_count}
- A005 join success count: {join_success_count}
- A005 missing count: {missing_count}
- A005 duplicate target-identity count: {duplicate_count}

Missing rows, if any, are written to `{(out_dir / 'a005_missing_rows.csv').relative_to(ROOT)}`.

## SAR Image Source Check

- Preferred grayscale available count: {grayscale_available_count}
- Fallback pseudocolor available count: {pseudocolor_available_count}
- Selected grayscale count: {selected_gray_count}
- Selected pseudocolor count: {selected_pseudocolor_count}
- Consistent selected image dimension rate: {consistent_image_dimension_rate:.4f}

The precheck only reads PNG headers for dimensions. It does not compute image energy, contrast, components, or thresholds.

## Readiness

- Implementation readiness: {implementation_readiness}
- Route A readiness: {readiness_summary['route_A_readiness']}
- Route B readiness: {readiness_summary['route_B_readiness']}
- Route C readiness: {readiness_summary['route_C_readiness']}
- Route D readiness: {readiness_summary['route_D_readiness']}

Blockers:

{chr(10).join(f'- {item}' for item in blockers)}

Interpretation:

- Core source availability is {'sufficient for pre-implementation review' if core_sources_ready else 'not sufficient'}.
- Implementation is still not fully approved because route parameters remain predeclared placeholders.
- Route D remains blocked because fan/range convention and valid support mapping are not frozen.

## Outputs

- `{(out_dir / 'target_set_freeze.csv').relative_to(ROOT)}`
- `{(out_dir / 'shell_proxy_inventory.csv').relative_to(ROOT)}`
- `{(out_dir / 'source_inventory_readiness_summary.csv').relative_to(ROOT)}`
- `{(out_dir / 'proposal_config_draft.json').relative_to(ROOT)}`
- `{(out_dir / 'leakage_audit_checklist.json').relative_to(ROOT)}`
- `{(out_dir / 'readiness_summary.json').relative_to(ROOT)}`

## Boundary

- No proposal generated.
- No candidate generated.
- No proposal_candidates.csv generated.
- No A019/A021 joined.
- No GT/oracle metric computed.
- No C3/C4 changed.
- No A001/A005/A019/A021 source file changed.
- No threshold tuning.
- No training.
- No calibration.
- No push.
"""
    docs_path.write_text(docs_text, encoding="utf-8")

    print(json.dumps({"output_dir": str(out_dir), "docs_summary": str(docs_path), **readiness_summary}, indent=2))


if __name__ == "__main__":
    main()
