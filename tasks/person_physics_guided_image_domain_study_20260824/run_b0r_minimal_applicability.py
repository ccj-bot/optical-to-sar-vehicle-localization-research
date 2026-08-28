#!/usr/bin/env python3
"""Minimal B0R applicability audit using the frozen P0 implementation.

This script does not tune or replace P0. It runs the frozen representation,
anchor tracking, masks, selected model family, and display strata on R02/R03,
then asks a pointwise question at offline PERSON reference locations: is there
enough nearby held-out background support to attach a local compensation error
budget? The reference locations are used only for evaluation and never for
background fitting or model selection.
"""

from __future__ import annotations

import importlib.util
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pandas as pd


SCRIPT_PATH = Path(__file__).resolve()
TASK_DIR = SCRIPT_PATH.parent
WORKSPACE = TASK_DIR.parents[1]
STUDY_OUTPUT = (
    WORKSPACE / "output" / "person_physics_guided_image_domain_study_20260824"
)
P0_SCRIPT = TASK_DIR / "run_p0_common_apparent_motion.py"
P0_OUTPUT = STUDY_OUTPUT / "p0_common_apparent_motion"
OUTPUT_DIR = STUDY_OUTPUT / "p1e_sar_only_response_interface" / "b0r_minimal"
VIS_DIR = OUTPUT_DIR / "visualizations"
RUNS = ("R02ZF", "R03ZF")


def load_p0_module() -> Any:
    spec = importlib.util.spec_from_file_location("frozen_person_p0", P0_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import frozen P0 script: {P0_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, float):
        return None if not math.isfinite(value) else value
    return value


def point_polar(point: np.ndarray, geometry: dict[str, Any]) -> tuple[float, float]:
    cx = float(geometry["center_x_px"])
    cy = float(geometry["center_y_px"])
    vx = float(point[0]) - cx
    vy = float(point[1]) - cy
    radial = math.hypot(vx, vy)
    theta = math.degrees(math.atan2(vx, cy - float(point[1])))
    return radial, theta


def make_frame_maps(explorer: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {frame["sar_frame_uid"]: frame for frame in explorer["frames"]}


def center_inside_frozen_base_mask(
    p0: Any,
    frame: dict[str, Any],
    point: np.ndarray,
    config: dict[str, Any],
) -> bool:
    image_path = p0.file_url_to_path(frame["sar_image_url"])
    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(image_path)
    mask, _ = p0.build_base_mask(frame, image, config)
    x = int(round(float(point[0])))
    y = int(round(float(point[1])))
    return 0 <= x < mask.shape[1] and 0 <= y < mask.shape[0] and bool(mask[y, x])


def summarize_run(
    run_id: str,
    pair_metrics: pd.DataFrame,
    comparability: pd.DataFrame,
    local_budget: pd.DataFrame,
) -> dict[str, Any]:
    selected_rows = pair_metrics[
        pair_metrics["is_selected_frozen_model"] & pair_metrics["model_available"]
    ]
    return {
        "run_id": run_id,
        "scheduled_frame_pairs": int(len(comparability)),
        "globally_comparable_frame_pairs": int(comparability["comparable"].sum()),
        "selected_model_available_frame_pairs": int(len(selected_rows)),
        "global_comparable_fraction": float(comparability["comparable"].mean()),
        "selected_model_improvement_fraction_vs_M0": (
            float(selected_rows["holdout_improved_vs_M0"].fillna(False).mean())
            if len(selected_rows)
            else 0.0
        ),
        "local_target_pair_count": int(len(local_budget)),
        "local_status_counts": dict(
            sorted(Counter(local_budget["local_compensation_status"]).items())
        ),
        "local_comparable_fraction": float(
            (local_budget["local_compensation_status"] == "P0_COMPENSATION_COMPARABLE").mean()
        ),
        "display_stratum_counts": dict(
            sorted(Counter(comparability["display_stratum"]).items())
        ),
        "comparability_reason_counts": dict(
            sorted(Counter(comparability["comparability_reason"]).items())
        ),
    }


def draw_case(
    p0: Any,
    frame: dict[str, Any],
    annotation: dict[str, Any],
    anchors: pd.DataFrame,
    row: pd.Series,
    config: dict[str, Any],
    path: Path,
) -> None:
    image_path = p0.file_url_to_path(frame["sar_image_url"])
    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(image_path)
    p0.draw_valid_boundaries(image, frame, config)
    p0.draw_rotated_box(image, annotation, (0, 0, 255), 2)
    center = (int(round(float(annotation["cx"]))), int(round(float(annotation["cy"]))))
    radius = int(round(float(row["local_support_radius_px"])))
    cv2.circle(image, center, radius, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.drawMarker(image, center, (0, 0, 255), cv2.MARKER_CROSS, 18, 2, cv2.LINE_AA)

    selected_model = str(row["selected_model"])
    residual_col = f"{selected_model}_residual_px"
    finite = anchors[anchors[residual_col].notna()].copy()
    vmax = float(np.percentile(finite[residual_col], 95)) if len(finite) else 1.0
    vmax = max(vmax, 1e-6)
    for anchor in finite.itertuples(index=False):
        value = float(getattr(anchor, residual_col))
        ratio = float(np.clip(value / vmax, 0.0, 1.0))
        color = (int(round(255 * (1.0 - ratio))), int(round(255 * (1.0 - ratio))), 255)
        point = (int(round(float(anchor.x_px))), int(round(float(anchor.y_px))))
        distance = math.hypot(point[0] - center[0], point[1] - center[1])
        thickness = -1 if distance <= radius else 1
        cv2.circle(image, point, 3, color, thickness, cv2.LINE_AA)

    lines = [
        f"{row['run_id']} {row['from_frame_uid']} -> {row['to_frame_uid']} lag={int(row['lag'])} {selected_model}",
        f"target={row['target_id']} status={row['local_compensation_status']} reason={row['local_reason']}",
        f"local holdout={int(row['local_holdout_count'])} bracket(r/theta)={bool(row['radial_bracket'])}/{bool(row['theta_bracket'])} epsilon={row['local_error_budget_px']:.3f}px",
        "red=offline PERSON reference; white circle=local support radius; dots=held-out background residuals",
    ]
    sheet = p0.put_title_band(image, lines)
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), sheet, [cv2.IMWRITE_JPEG_QUALITY, 94])


def main() -> None:
    if WORKSPACE.resolve() != Path(r"D:\profile\research\workspace").resolve():
        raise RuntimeError(f"workspace mismatch: {WORKSPACE}")
    if "old_work" in str(SCRIPT_PATH).lower() or "old_work" in str(OUTPUT_DIR).lower():
        raise RuntimeError("forbidden old_work dependency")

    p0 = load_p0_module()
    p0.assert_workspace_scope()
    contract, input_checks = p0.load_contract_and_verify()
    freeze = json.loads((P0_OUTPUT / "model_selection_R01.json").read_text(encoding="utf-8"))
    expected_script_hash = freeze["frozen"]["script_sha256"]
    actual_script_hash = p0.sha256_file(P0_SCRIPT)
    if actual_script_hash != expected_script_hash:
        raise RuntimeError(
            f"frozen P0 script hash mismatch: {actual_script_hash} != {expected_script_hash}"
        )

    config = freeze["frozen"]["algorithm_config"]
    selected = freeze["frozen"]["selected_model_by_lag"]
    display_thresholds = freeze["frozen"]["display_change_thresholds_by_lag"]
    p0_quantitative = json.loads(
        (P0_OUTPUT / "frozen_validation_R04_quantitative.json").read_text(encoding="utf-8")
    )
    p0_reference_short_axis_px = float(
        p0_quantitative["stationary_PERSON"]["short_axis_median_px_unique_R04_boxes"]
    )
    max_local_error_budget_px = 0.5 * p0_reference_short_axis_px
    local_radius_px = 3.0 * float(config["split_cell_px"])
    min_local_holdout = int(config["min_holdout_anchors"])
    explorer = p0.load_explorer()
    frame_map = make_frame_maps(explorer)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    VIS_DIR.mkdir(parents=True, exist_ok=True)
    all_pair: list[pd.DataFrame] = []
    all_anchor: list[pd.DataFrame] = []
    all_comp: list[pd.DataFrame] = []
    all_local: list[pd.DataFrame] = []
    all_parameters: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []

    for run_id in RUNS:
        result = p0.process_run(explorer, run_id, config)
        pair_metrics = p0.apply_display_strata(result["pair_metrics"], display_thresholds)
        pair_metrics = p0.add_selected_pair_fields(pair_metrics, selected)
        comparability = p0.apply_display_strata(result["comparability"], display_thresholds)
        person_rows = p0.apply_display_strata(result["person_residuals"], display_thresholds)
        anchors = result["anchor_metrics"].copy()

        local_rows: list[dict[str, Any]] = []
        selected_person = person_rows[
            person_rows.apply(
                lambda row: row["model"] == selected[str(int(row["lag"]))], axis=1
            )
        ].copy()
        comp_index = comparability.set_index(
            ["run_id", "from_frame_uid", "to_frame_uid", "lag"]
        )
        pair_index = pair_metrics[
            pair_metrics["is_selected_frozen_model"]
        ].set_index(["run_id", "from_frame_uid", "to_frame_uid", "lag"])

        for person in selected_person.itertuples(index=False):
            key = (
                person.run_id,
                person.from_frame_uid,
                person.to_frame_uid,
                int(person.lag),
            )
            comp = comp_index.loc[key]
            pair = pair_index.loc[key]
            model = selected[str(int(person.lag))]
            pair_anchors = anchors[
                (anchors["run_id"] == person.run_id)
                & (anchors["from_frame_uid"] == person.from_frame_uid)
                & (anchors["to_frame_uid"] == person.to_frame_uid)
                & (anchors["lag"] == int(person.lag))
                & (anchors["anchor_split"] == "HOLDOUT")
                & anchors[f"{model}_available"].astype(bool)
            ].copy()

            target = np.array([float(person.from_cx_px), float(person.from_cy_px)])
            frame = frame_map[person.from_frame_uid]
            geometry = frame["geometry"]
            target_radial, target_theta = point_polar(target, geometry)
            if len(pair_anchors):
                points = pair_anchors[["x_px", "y_px"]].to_numpy(dtype=float)
                distances = np.linalg.norm(points - target[None, :], axis=1)
                pair_anchors["distance_to_target_px"] = distances
                local = pair_anchors[distances <= local_radius_px].copy()
            else:
                local = pair_anchors.copy()
                local["distance_to_target_px"] = pd.Series(dtype=float)

            local_count = int(len(local))
            residual_col = f"{model}_residual_px"
            if local_count:
                local_residual = local[residual_col].to_numpy(dtype=float)
                local_median = float(np.median(local_residual))
                local_p90 = float(np.percentile(local_residual, 90))
                local_max_distance = float(local["distance_to_target_px"].max())
                radial_theta = np.asarray(
                    [point_polar(point, geometry) for point in local[["x_px", "y_px"]].to_numpy(dtype=float)]
                )
                radial_bracket = bool(
                    np.any(radial_theta[:, 0] < target_radial)
                    and np.any(radial_theta[:, 0] > target_radial)
                )
                theta_bracket = bool(
                    np.any(radial_theta[:, 1] < target_theta)
                    and np.any(radial_theta[:, 1] > target_theta)
                )
            else:
                local_median = math.nan
                local_p90 = math.nan
                local_max_distance = math.nan
                radial_bracket = False
                theta_bracket = False

            global_p90 = float(pair.holdout_residual_p90_px)
            local_budget = (
                max(local_p90, global_p90)
                if np.isfinite(local_p90) and np.isfinite(global_p90)
                else math.nan
            )
            center_valid = center_inside_frozen_base_mask(p0, frame, target, config)
            globally_available = bool(comp.comparable) and bool(pair.model_available)

            if not globally_available:
                status = "INSUFFICIENT_BACKGROUND_SUPPORT"
                reason = str(comp.comparability_reason)
            elif not center_valid:
                status = "P0_COMPENSATION_NOT_COMPARABLE"
                reason = "REFERENCE_POSITION_OUTSIDE_FROZEN_P0_VALID_MASK"
            elif local_count < min_local_holdout:
                status = "P0_COMPENSATION_NOT_COMPARABLE"
                reason = "INSUFFICIENT_LOCAL_HOLDOUT_ANCHORS"
            elif not radial_bracket or not theta_bracket:
                status = "P0_COMPENSATION_NOT_COMPARABLE"
                reason = "LOCAL_HOLDOUT_NOT_TWO_SIDED_IN_RANGE_AZIMUTH"
            elif not np.isfinite(local_budget) or local_budget > max_local_error_budget_px:
                status = "P0_COMPENSATION_NOT_COMPARABLE"
                reason = "LOCAL_ERROR_BUDGET_EXCEEDS_HALF_P0_REFERENCE_SHORT_AXIS"
            else:
                status = "P0_COMPENSATION_COMPARABLE"
                reason = "LOCAL_HELDOUT_SUPPORT_AVAILABLE"

            ann = next(
                item
                for item in frame["annotations"]
                if item["instance_id"] == person.target_id
            )
            local_rows.append(
                {
                    "run_id": person.run_id,
                    "from_frame": int(person.from_frame),
                    "to_frame": int(person.to_frame),
                    "from_frame_uid": person.from_frame_uid,
                    "to_frame_uid": person.to_frame_uid,
                    "lag": int(person.lag),
                    "target_id": person.target_id,
                    "from_source": person.from_source,
                    "to_source": person.to_source,
                    "both_manual_endpoints": bool(person.both_manual_endpoints),
                    "reference_cx_px": float(person.from_cx_px),
                    "reference_cy_px": float(person.from_cy_px),
                    "reference_range_m": float(ann["range_m"]),
                    "reference_theta_deg": float(ann["theta_deg"]),
                    "reference_outer_margin_m": float(ann["outer_radial_margin_m"]),
                    "reference_side_margin_deg": float(ann["angular_side_margin_deg"]),
                    "reference_local_valid_fraction": float(ann["local_valid_fraction"]),
                    "selected_model": model,
                    "global_pair_comparable": bool(comp.comparable),
                    "selected_model_available": bool(pair.model_available),
                    "selected_improved_vs_M0": (
                        bool(pair.holdout_improved_vs_M0)
                        if not pd.isna(pair.holdout_improved_vs_M0)
                        else False
                    ),
                    "global_holdout_median_px": float(pair.holdout_residual_median_px),
                    "global_holdout_p90_px": global_p90,
                    "display_js_divergence": float(comp.display_js_divergence),
                    "display_stratum": comp.display_stratum,
                    "reference_inside_frozen_P0_valid_mask": center_valid,
                    "local_support_radius_px": local_radius_px,
                    "local_min_required_holdout": min_local_holdout,
                    "local_holdout_count": local_count,
                    "local_holdout_median_px": local_median,
                    "local_holdout_p90_px": local_p90,
                    "local_holdout_max_distance_px": local_max_distance,
                    "radial_bracket": radial_bracket,
                    "theta_bracket": theta_bracket,
                    "local_error_budget_px": local_budget,
                    "max_usable_local_error_budget_px": max_local_error_budget_px,
                    "local_compensation_status": status,
                    "local_reason": reason,
                    "target_motion_used_for_budget": False,
                    "target_pixels_used_for_fitting": 0,
                }
            )

        local_budget = pd.DataFrame(local_rows)
        summaries.append(summarize_run(run_id, pair_metrics, comparability, local_budget))
        all_pair.append(pair_metrics)
        all_anchor.append(anchors)
        all_comp.append(comparability)
        all_local.append(local_budget)
        all_parameters.extend(result["model_parameters"])

    pair_all = pd.concat(all_pair, ignore_index=True)
    anchor_all = pd.concat(all_anchor, ignore_index=True)
    comp_all = pd.concat(all_comp, ignore_index=True)
    local_all = pd.concat(all_local, ignore_index=True)

    pair_all.to_csv(OUTPUT_DIR / "b0r_pair_metrics_R02_R03.csv", index=False, encoding="utf-8-sig")
    anchor_all.to_csv(OUTPUT_DIR / "b0r_background_anchor_metrics_R02_R03.csv", index=False, encoding="utf-8-sig")
    comp_all.to_csv(OUTPUT_DIR / "b0r_pair_comparability_R02_R03.csv", index=False, encoding="utf-8-sig")
    local_all.to_csv(OUTPUT_DIR / "b0r_local_error_budget_R02_R03.csv", index=False, encoding="utf-8-sig")
    p0.write_jsonl(OUTPUT_DIR / "b0r_model_parameters_R02_R03.jsonl", all_parameters)

    frame_pair_status = (
        local_all.groupby(["run_id", "from_frame_uid", "to_frame_uid", "lag"])[
            "local_compensation_status"
        ]
        .agg(list)
        .reset_index()
    )
    frame_pair_status["frame_pair_local_status"] = frame_pair_status[
        "local_compensation_status"
    ].apply(
        lambda values: (
            "ALL_REFERENCE_LOCATIONS_COMPARABLE"
            if all(value == "P0_COMPENSATION_COMPARABLE" for value in values)
            else "SOME_REFERENCE_LOCATIONS_COMPARABLE"
            if any(value == "P0_COMPENSATION_COMPARABLE" for value in values)
            else "NO_REFERENCE_LOCATION_COMPARABLE"
        )
    )
    frame_pair_status.drop(columns=["local_compensation_status"]).to_csv(
        OUTPUT_DIR / "b0r_frame_pair_local_status_R02_R03.csv",
        index=False,
        encoding="utf-8-sig",
    )

    case_rows: list[pd.Series] = []
    for run_id in RUNS:
        run_rows = local_all[local_all["run_id"] == run_id]
        comparable = run_rows[
            run_rows["local_compensation_status"] == "P0_COMPENSATION_COMPARABLE"
        ].sort_values("local_error_budget_px")
        noncomparable = run_rows[
            run_rows["local_compensation_status"] != "P0_COMPENSATION_COMPARABLE"
        ]
        if len(comparable):
            case_rows.append(comparable.iloc[0])
            case_rows.append(comparable.iloc[-1])
        for _, reason_rows in noncomparable.groupby("local_reason"):
            case_rows.append(reason_rows.iloc[0])

    unique_cases: list[pd.Series] = []
    seen: set[tuple[str, str, str, int, str]] = set()
    for row in case_rows:
        key = (
            str(row["run_id"]),
            str(row["from_frame_uid"]),
            str(row["to_frame_uid"]),
            int(row["lag"]),
            str(row["target_id"]),
        )
        if key not in seen:
            seen.add(key)
            unique_cases.append(row)
    unique_cases = unique_cases[:8]

    registry: list[dict[str, Any]] = []
    for rank, row in enumerate(unique_cases, start=1):
        frame = frame_map[str(row["from_frame_uid"])]
        annotation = next(
            item for item in frame["annotations"] if item["instance_id"] == row["target_id"]
        )
        model = str(row["selected_model"])
        anchors = anchor_all[
            (anchor_all["run_id"] == row["run_id"])
            & (anchor_all["from_frame_uid"] == row["from_frame_uid"])
            & (anchor_all["to_frame_uid"] == row["to_frame_uid"])
            & (anchor_all["lag"] == int(row["lag"]))
            & (anchor_all["anchor_split"] == "HOLDOUT")
            & anchor_all[f"{model}_available"].astype(bool)
        ]
        filename = (
            f"case_{rank:02d}_{row['run_id']}_{int(row['from_frame']):06d}_"
            f"{int(row['to_frame']):06d}_lag{int(row['lag'])}_{row['target_id']}.jpg"
        )
        path = VIS_DIR / filename
        draw_case(p0, frame, annotation, anchors, row, config, path)
        registry.append(
            {
                "rank": rank,
                "run_id": row["run_id"],
                "from_frame_uid": row["from_frame_uid"],
                "to_frame_uid": row["to_frame_uid"],
                "lag": int(row["lag"]),
                "target_id": row["target_id"],
                "status": row["local_compensation_status"],
                "reason": row["local_reason"],
                "local_error_budget_px": row["local_error_budget_px"],
                "visual_path": str(path),
            }
        )

    summary = {
        "schema": "PERSON_B0R_MINIMAL_FROZEN_P0_APPLICABILITY_V1",
        "created_at": p0.now_iso(),
        "status": "B0R_MINIMAL_COMPLETE_NO_P0_RETUNING",
        "runs": list(RUNS),
        "interpreter": r"D:\MINICONDA\envs\py311\python.exe",
        "frozen_P0_script_sha256": actual_script_hash,
        "frozen_P0_freeze_payload_sha256": freeze["freeze_payload_sha256"],
        "selected_model_by_lag": selected,
        "display_change_thresholds_by_lag": display_thresholds,
        "input_hash_checks": input_checks,
        "local_support_rule": {
            "radius_px": local_radius_px,
            "radius_source": "3_X_FROZEN_P0_SPLIT_CELL_PX",
            "minimum_local_holdout_anchors": min_local_holdout,
            "minimum_source": "FROZEN_P0_MIN_HOLDOUT_ANCHORS",
            "requires_radial_bracketing": True,
            "requires_azimuth_bracketing": True,
            "local_error_budget": "MAX(LOCAL_HOLDOUT_P90, GLOBAL_PAIR_HOLDOUT_P90)",
            "maximum_usable_local_error_budget_px": max_local_error_budget_px,
            "maximum_budget_source": "0.5_X_P0_R04_PERSON_SHORT_AXIS_MEDIAN",
            "P0_R04_PERSON_short_axis_median_px": p0_reference_short_axis_px,
            "target_motion_used": False,
        },
        "run_summaries": summaries,
        "overall_local_status_counts": dict(
            sorted(Counter(local_all["local_compensation_status"]).items())
        ),
        "overall_local_reason_counts": dict(sorted(Counter(local_all["local_reason"]).items())),
        "visual_case_registry": registry,
        "semantic_boundaries": {
            "P0_retuned": False,
            "target_regions_used_for_fitting_or_model_selection": False,
            "target_motion_used_to_set_temporal_tolerance": False,
            "SAR_boxes_created_or_moved": 0,
            "P1_PASS_claimed": False,
            "P2_started": False,
        },
    }
    p0.write_json(OUTPUT_DIR / "b0r_summary.json", json_safe(summary))
    print(json.dumps(json_safe(summary), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
