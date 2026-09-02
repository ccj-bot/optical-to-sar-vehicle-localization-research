from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


SCRIPT = Path(__file__).resolve()
TASK = SCRIPT.parent
WORKSPACE = TASK.parents[1]
OUT = WORKSPACE / "output" / "person_r02_scene_depth_value_test_20260902"
PRE = OUT / "pre_reference"
MASK_OUT = PRE / "support_masks"

R2_PRE = (
    WORKSPACE
    / "output"
    / "person_terg_r2_runtime_grounding_and_full_stream_hypothesis_management_20260830"
    / "pre_reference"
)
REGISTRY = R2_PRE / "full_stream_frame_registry_pre_reference.parquet"
Q95_MASKS = R2_PRE / "full_stream_q95_masks"
FAMILY_MEMBERSHIP = R2_PRE / "runtime_candidate_family_membership_pre_reference.parquet"
ONE_CURB_BANDS = (
    WORKSPACE
    / "output"
    / "person_r02_curb_radial_anchor_pilot_20260831"
    / "pre_reference"
    / "sar_curb_candidate_frame_bands_pre_reference.parquet"
)

QUEUE = PRE / "OPTICAL_PERSON_SCENE_LAYER_QUEUE_PRE_REFERENCE.csv"
VISUAL_CASES = PRE / "OPTICAL_PERSON_SCENE_LAYER_VISUAL_CASES_PRE_REFERENCE.csv"
BOUNDARIES = PRE / "BOUNDARY_VALUE_ELIGIBLE_GEOMETRY_PRE_REFERENCE.parquet"
LABEL_SOURCE = TASK / "scene_layer_visual_labels_v1.csv"

CONDITIONS = (
    "ANGLE_ONLY",
    "ANGLE_PLUS_ONE_CURB_HALFSPACE",
    "ANGLE_PLUS_TWO_BOUNDARY_SCENE_LAYER",
)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def write_table(frame: pd.DataFrame, stem: Path) -> None:
    stem.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(stem.with_suffix(".csv"), index=False, encoding="utf-8-sig")
    frame.to_parquet(stem.with_suffix(".parquet"), index=False, compression="zstd")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().lower()


def sha256_array(array: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(array).view(np.uint8)).hexdigest().lower()


def parse_intervals(value: str) -> list[list[float]]:
    return [[float(low), float(high)] for low, high in json.loads(value)]


def angle_mask(theta: np.ndarray, intervals: list[list[float]]) -> np.ndarray:
    support = np.zeros(theta.shape, dtype=bool)
    for low, high in intervals:
        support |= (theta >= low) & (theta <= high)
    return support


def geometry_fields(frame: pd.Series) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    height = int(frame.sar_height_px)
    width = int(frame.sar_width_px)
    yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
    cx = float(frame.geometry_center_x_px)
    cy = float(frame.geometry_center_y_px)
    px_per_m = float(frame.geometry_radius_px) / float(frame.geometry_outer_range_m)
    theta = np.degrees(np.arctan2(xx - cx, cy - yy))
    radius_m = np.hypot(xx - cx, cy - yy) / px_per_m
    d_parallel_m = (cy - yy) / px_per_m
    return theta, radius_m, d_parallel_m, px_per_m


def boundary_curve(record: pd.Series, theta: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    nodes = np.asarray(json.loads(str(record.theta_nodes_json)), dtype=float)
    radii = np.asarray(json.loads(str(record.radius_nodes_m_json)), dtype=float)
    order = np.argsort(nodes)
    nodes = nodes[order]
    radii = radii[order]
    inside = (theta >= nodes[0]) & (theta <= nodes[-1])
    values = np.full(theta.shape, np.nan, dtype=np.float32)
    values[inside] = np.interp(theta[inside], nodes, radii).astype(np.float32)
    return values, inside


def family_count(
    membership_index: dict[tuple[int, str, str], str],
    frame_index: int,
    track_id: str,
    region_ids: list[str],
) -> tuple[int, int]:
    families: set[str] = set()
    unassigned = 0
    for region_id in region_ids:
        family = membership_index.get((frame_index, track_id, region_id))
        if family is None:
            family = f"UNASSIGNED::{region_id}"
            unassigned += 1
        families.add(family)
    return len(families), unassigned


def support_counts(
    labels: np.ndarray,
    support: np.ndarray,
    frame_index: int,
    track_id: str,
    px_per_m: float,
    membership_index: dict[tuple[int, str, str], str],
) -> dict[str, Any]:
    selected_labels = sorted(int(value) for value in np.unique(labels[support]) if int(value) > 0)
    region_ids = [f"R02ZF_SARF{frame_index:06d}__Q095__R{label:04d}" for label in selected_labels]
    family_n, unassigned = family_count(membership_index, frame_index, track_id, region_ids)
    pixel_count = int(np.count_nonzero((labels > 0) & support))
    return {
        "N_region": len(selected_labels),
        "N_family": family_n,
        "A_candidate_px": pixel_count,
        "A_candidate_m2": float(pixel_count / (px_per_m * px_per_m)),
        "region_ids_json": json.dumps(region_ids, ensure_ascii=False),
        "unassigned_family_count": unassigned,
    }


def freeze_visual_labels(queue: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    labels = pd.read_csv(LABEL_SOURCE)
    visual = pd.read_csv(VISUAL_CASES)
    if len(labels) != len(visual) or labels.optical_review_id.nunique() != len(visual):
        raise RuntimeError("Visual label source does not cover exactly the visual case denominator")
    if set(labels.optical_review_id) != set(visual.optical_review_id):
        raise RuntimeError("Visual label IDs differ from prepared visual cases")
    allowed = {"L0", "L1", "L2", "UNCERTAIN"}
    if not set(labels.scene_layer).issubset(allowed):
        raise RuntimeError(f"Unknown scene layer: {set(labels.scene_layer) - allowed}")
    if labels.manual_person_reference_used.astype(bool).any():
        raise RuntimeError("Manual PERSON reference entered visual labels")
    frozen_visual = visual.drop(columns=["scene_layer", "visual_state", "reason", "manual_person_reference_used"]).merge(
        labels, on=["review_number", "optical_review_id"], how="left", validate="one_to_one"
    )
    frozen_queue = queue.drop(columns=["scene_layer", "visual_state", "reason", "manual_person_reference_used"]).merge(
        labels.drop(columns=["review_number"]), on="optical_review_id", how="left", validate="many_to_one"
    )
    if frozen_queue.scene_layer.isna().any():
        raise RuntimeError("Queue contains unlabeled rows")
    frozen_queue["visual_development_only"] = True
    frozen_queue["manual_person_reference_used"] = False
    frozen_visual["visual_development_only"] = True
    frozen_visual["manual_person_reference_used"] = False
    return frozen_queue, frozen_visual


def summarize_burden(burden: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for condition, group in burden.groupby("condition", sort=False):
        applied = group[group.condition_applied]
        for population, subset in (("ALL_FALLBACK_AWARE", group), ("APPLIED_ONLY", applied)):
            if subset.empty:
                continue
            row: dict[str, Any] = {
                "condition": condition,
                "population": population,
                "denominator_rows": len(subset),
                "unique_frames": int(subset.sar_frame.nunique()),
                "condition_applied_rows": int(subset.condition_applied.sum()),
                "condition_applied_fraction": float(subset.condition_applied.mean()),
            }
            for metric in ("N_region", "N_family", "A_candidate_px", "A_candidate_m2"):
                values = subset[metric].astype(float)
                row[f"{metric}_median"] = float(values.median())
                row[f"{metric}_p75"] = float(values.quantile(0.75))
                row[f"{metric}_p90"] = float(values.quantile(0.90))
                row[f"{metric}_max"] = float(values.max())
            baseline = subset[["shell_id", "N_region", "N_family", "A_candidate_px"]].copy()
            if condition == "ANGLE_ONLY":
                reduction_region = np.zeros(len(subset), dtype=float)
                reduction_family = np.zeros(len(subset), dtype=float)
                reduction_area = np.zeros(len(subset), dtype=float)
            else:
                base = burden[burden.condition.eq("ANGLE_ONLY")][
                    ["shell_id", "N_region", "N_family", "A_candidate_px"]
                ].rename(columns={
                    "N_region": "N_region_base",
                    "N_family": "N_family_base",
                    "A_candidate_px": "A_candidate_px_base",
                })
                joined = subset.merge(base, on="shell_id", how="left", validate="one_to_one")
                reduction_region = (joined.N_region_base - joined.N_region).to_numpy(float)
                reduction_family = (joined.N_family_base - joined.N_family).to_numpy(float)
                reduction_area = np.where(
                    joined.A_candidate_px_base.to_numpy(float) > 0,
                    1.0 - joined.A_candidate_px.to_numpy(float) / joined.A_candidate_px_base.to_numpy(float),
                    0.0,
                )
            row["N_region_singleton_fraction"] = float((subset.N_region == 1).mean())
            row["N_region_le2_fraction"] = float((subset.N_region <= 2).mean())
            row["N_family_singleton_fraction"] = float((subset.N_family == 1).mean())
            row["N_family_le2_fraction"] = float((subset.N_family <= 2).mean())
            row["positive_region_contraction_fraction"] = float(np.mean(reduction_region > 0))
            row["positive_family_contraction_fraction"] = float(np.mean(reduction_family > 0))
            row["positive_area_contraction_fraction"] = float(np.mean(reduction_area > 0))
            row["zero_area_benefit_fraction"] = float(np.mean(reduction_area == 0))
            row["area_reduction_fraction_median"] = float(np.median(reduction_area))
            row["area_reduction_fraction_p75"] = float(np.quantile(reduction_area, 0.75))
            row["area_reduction_fraction_p90"] = float(np.quantile(reduction_area, 0.90))
            rows.append(row)
    return pd.DataFrame(rows)


def freeze_manifest(paths: list[Path], metadata: dict[str, Any]) -> dict[str, Any]:
    entries = []
    root_lines = []
    for path in sorted(paths, key=lambda item: str(item.relative_to(OUT)).replace("\\", "/")):
        relative = str(path.relative_to(OUT)).replace("\\", "/")
        digest = sha256_file(path)
        size = path.stat().st_size
        entries.append({"path": relative, "bytes": size, "sha256": digest})
        root_lines.append(f"{relative}|{size}|{digest}")
    root = hashlib.sha256("\n".join(root_lines).encode("utf-8")).hexdigest().lower()
    result = {
        "schema": "PERSON_R02_SCENE_DEPTH_PRE_REFERENCE_FREEZE_V1",
        "pre_reference_root_sha256": root,
        "files": entries,
        "manual_person_sar_reference_opened": False,
        "operator_contamination_disclosure": {
            "known_exposed_case": "R02ZF F472 / R02ZF_REUSED_R02ZF_PERSON017 / approximately 13.542 m",
            "policy": "Exclude from confirmatory reference statistics or report separately as operator-contaminated.",
            "new_case_level_reference_opened_before_freeze": False,
        },
        "r04_accessed": False,
        "boundary_propagation_modified": False,
        "f66_used": False,
        "final_localization_run": False,
        **metadata,
    }
    write_json(PRE / "PRE_REFERENCE_FREEZE_MANIFEST.json", result)
    return result


def main() -> None:
    if WORKSPACE.resolve() != Path(r"D:\profile\research\workspace").resolve():
        raise RuntimeError(f"Unexpected workspace: {WORKSPACE}")
    for path in (TASK, OUT, REGISTRY, Q95_MASKS, FAMILY_MEMBERSHIP, ONE_CURB_BANDS):
        lowered = str(path).lower()
        if "old_work" in lowered or "r04" in lowered:
            raise RuntimeError(f"Forbidden path: {path}")
    if (PRE / "PRE_REFERENCE_FREEZE_MANIFEST.json").exists():
        raise RuntimeError("Pre-reference freeze already exists; refuse silent overwrite")

    queue = pd.read_csv(QUEUE)
    frozen_queue, frozen_visual = freeze_visual_labels(queue)
    boundaries = pd.read_parquet(BOUNDARIES)
    registry = pd.read_parquet(REGISTRY)
    registry = registry[registry.run_id.eq("R02ZF")].set_index("sar_frame_index")
    membership = pd.read_parquet(FAMILY_MEMBERSHIP)
    membership = membership[membership.run_id.eq("R02ZF") & membership["mode"].eq("CAUSAL_REPLAY")]
    membership_index = {
        (int(row.frame_index), str(row.track_id), str(row.region_id)): str(row.family_id)
        for row in membership.itertuples(index=False)
    }
    one_curb = pd.read_parquet(ONE_CURB_BANDS)
    one_curb = one_curb[
        one_curb.run_id.eq("R02ZF")
        & one_curb.score_rank.eq(1)
        & one_curb.availability_state.eq("CURB_BAND_AVAILABLE_GT_BLIND")
    ].set_index("sar_frame_index")
    boundary_index = {
        (int(row.sar_frame_index), str(row.object_type)): pd.Series(row._asdict())
        for row in boundaries.itertuples(index=False)
    }

    MASK_OUT.mkdir(parents=True, exist_ok=True)
    burden_rows: list[dict[str, Any]] = []
    mask_paths: list[Path] = []
    geometry_cache: dict[int, tuple[np.ndarray, np.ndarray, np.ndarray, float, np.ndarray]] = {}
    for row in frozen_queue.sort_values(["sar_frame", "person_hypothesis_id"]).itertuples(index=False):
        frame_index = int(row.sar_frame)
        track_id = str(row.person_hypothesis_id)
        if frame_index not in geometry_cache:
            frame = registry.loc[frame_index]
            theta, radius_m, d_parallel_m, px_per_m = geometry_fields(frame)
            with np.load(Q95_MASKS / f"R02ZF_SARF{frame_index:06d}.npz", allow_pickle=False) as archive:
                labels = archive["Q095"].astype(np.int32)
            geometry_cache[frame_index] = (theta, radius_m, d_parallel_m, px_per_m, labels)
        theta, radius_m, d_parallel_m, px_per_m, labels = geometry_cache[frame_index]
        intervals = parse_intervals(str(row.effective_intervals_json))
        angle = angle_mask(theta, intervals)

        prior_known = str(row.prior_one_curb_visual_label) == "SIDEWALK_OR_PARKING_SIDE"
        one_applied = bool(prior_known and frame_index in one_curb.index)
        if one_applied:
            threshold = float(one_curb.loc[frame_index].d_band_low_m)
            one_mask = angle & (d_parallel_m >= threshold)
            one_state = "ONE_CURB_GT_BLIND_HALFSPACE_APPLIED"
        else:
            threshold = math.nan
            one_mask = angle.copy()
            one_state = "FALLBACK_ANGLE_ONLY_ONE_CURB_OR_LABEL_UNAVAILABLE"

        scene_layer = str(row.scene_layer)
        two_applied = bool(row.boundary_full_theta_coverage and scene_layer != "UNCERTAIN")
        near_record = boundary_index[(frame_index, "SAR_BOUNDARY_NEAR")]
        far_record = boundary_index[(frame_index, "SAR_BOUNDARY_FAR")]
        near_curve, near_inside = boundary_curve(near_record, theta)
        far_curve, far_inside = boundary_curve(far_record, theta)
        common = near_inside & far_inside
        angle_common = angle & common
        if bool(row.boundary_full_theta_coverage) and not np.array_equal(angle_common, angle):
            missing = int(np.count_nonzero(angle & ~common))
            if missing > 0:
                raise RuntimeError(f"Prepared full coverage disagrees with exact pixel support for {row.shell_id}: {missing}")
        if np.any(near_curve[common] >= far_curve[common]):
            raise RuntimeError(f"Near/far radial order invalid at F{frame_index}")
        if two_applied:
            if scene_layer == "L0":
                layer_mask = radius_m <= near_curve
            elif scene_layer == "L1":
                layer_mask = (radius_m >= near_curve) & (radius_m <= far_curve)
            elif scene_layer == "L2":
                layer_mask = radius_m >= far_curve
            else:
                raise RuntimeError(scene_layer)
            two_mask = angle & common & layer_mask
            two_state = f"TWO_BOUNDARY_{scene_layer}_EXACT_CURVE_APPLIED"
        else:
            two_mask = angle.copy()
            two_state = "FALLBACK_ANGLE_ONLY_PARTIAL_BOUNDARY_THETA_OR_UNCERTAIN_LAYER"

        masks = {
            "ANGLE_ONLY": angle,
            "ANGLE_PLUS_ONE_CURB_HALFSPACE": one_mask,
            "ANGLE_PLUS_TWO_BOUNDARY_SCENE_LAYER": two_mask,
        }
        key = hashlib.sha256(str(row.shell_id).encode("utf-8")).hexdigest()[:16]
        mask_path = MASK_OUT / f"R02ZF_F{frame_index:06d}_{key}.npz"
        np.savez_compressed(
            mask_path,
            shape=np.asarray(angle.shape, dtype=np.int32),
            angle_only_packbits=np.packbits(angle.reshape(-1)),
            one_curb_packbits=np.packbits(one_mask.reshape(-1)),
            two_boundary_packbits=np.packbits(two_mask.reshape(-1)),
        )
        mask_paths.append(mask_path)

        for condition in CONDITIONS:
            mask = masks[condition]
            if condition == "ANGLE_ONLY":
                applied = True
                state = "FROZEN_OPTICAL_ANGLE_CORRIDOR"
            elif condition == "ANGLE_PLUS_ONE_CURB_HALFSPACE":
                applied = one_applied
                state = one_state
            else:
                applied = two_applied
                state = two_state
            counts = support_counts(labels, mask, frame_index, track_id, px_per_m, membership_index)
            burden_rows.append(
                {
                    "run_id": "R02ZF",
                    "sar_frame": frame_index,
                    "sar_timestamp_ms": int(row.sar_timestamp_ms),
                    "shell_id": str(row.shell_id),
                    "person_hypothesis_id": track_id,
                    "optical_review_id": str(row.optical_review_id),
                    "optical_frame": int(row.optical_frame),
                    "optical_person_id": str(row.optical_person_id),
                    "scene_layer": scene_layer,
                    "visual_state": str(row.visual_state),
                    "boundary_full_theta_coverage": bool(row.boundary_full_theta_coverage),
                    "boundary_theta_overlap_fraction": float(row.boundary_theta_overlap_fraction),
                    "boundary_provenance": str(row.manual_or_propagated_boundary_provenance),
                    "condition": condition,
                    "condition_applied": applied,
                    "condition_state": state,
                    "one_curb_d_parallel_threshold_m": threshold,
                    "N_region": counts["N_region"],
                    "N_family": counts["N_family"],
                    "A_candidate_px": counts["A_candidate_px"],
                    "A_candidate_m2": counts["A_candidate_m2"],
                    "region_ids_json": counts["region_ids_json"],
                    "unassigned_family_count": counts["unassigned_family_count"],
                    "support_pixel_count": int(mask.sum()),
                    "support_mask_sha256": sha256_array(mask),
                    "support_mask_file": str(mask_path.relative_to(OUT)).replace("\\", "/"),
                    "exact_q95_pixel_intersection": True,
                    "manual_person_reference_used": False,
                    "visual_development_only": True,
                }
            )

    burden = pd.DataFrame(burden_rows)
    if len(burden) != len(frozen_queue) * len(CONDITIONS):
        raise RuntimeError("Incomplete burden table")
    if burden.unassigned_family_count.ne(0).any():
        bad = burden[burden.unassigned_family_count.ne(0)]
        raise RuntimeError(f"Unassigned candidate families: {len(bad)} rows")
    baseline = burden[burden.condition.eq("ANGLE_ONLY")].set_index("shell_id")
    for condition in CONDITIONS[1:]:
        current = burden[burden.condition.eq(condition)].set_index("shell_id")
        if (current.N_region > baseline.N_region).any() or (current.N_family > baseline.N_family).any():
            raise RuntimeError(f"Candidate counts increased under {condition}")
        if (current.A_candidate_px > baseline.A_candidate_px).any():
            raise RuntimeError(f"Candidate area increased under {condition}")

    write_table(frozen_visual, PRE / "optical_person_scene_layer_visual_cases_frozen_pre_reference")
    write_table(frozen_queue, PRE / "optical_person_scene_layer_pre_reference")
    write_table(burden, PRE / "runtime_support_burden_pre_reference")
    summary = summarize_burden(burden)
    write_table(summary, PRE / "runtime_support_burden_summary_pre_reference")
    case_selection = frozen_queue[
        [
            "run_id",
            "sar_frame",
            "shell_id",
            "person_hypothesis_id",
            "optical_review_id",
            "optical_frame",
            "scene_layer",
            "boundary_full_theta_coverage",
            "boundary_theta_overlap_fraction",
            "manual_or_propagated_boundary_provenance",
        ]
    ].copy()
    case_selection["confirmatory_two_boundary_eligible"] = (
        case_selection.boundary_full_theta_coverage & case_selection.scene_layer.ne("UNCERTAIN")
    )
    case_selection["operator_contaminated_known_case"] = (
        case_selection.sar_frame.eq(472)
        & case_selection.person_hypothesis_id.eq("R02ZF_REUSED_R02ZF_PERSON017")
    )
    write_table(case_selection, PRE / "case_selection_pre_reference")
    denominators = {
        "eligible_boundary_frames": int(boundaries.sar_frame_index.nunique()),
        "causal_shell_rows": len(frozen_queue),
        "unique_optical_visual_cases": len(frozen_visual),
        "scene_layer_distribution_visual_cases": {
            str(key): int(value) for key, value in frozen_visual.scene_layer.value_counts().sort_index().items()
        },
        "angle_only_rows": int((burden.condition.eq("ANGLE_ONLY")).sum()),
        "one_curb_applied_rows": int(
            (burden.condition.eq("ANGLE_PLUS_ONE_CURB_HALFSPACE") & burden.condition_applied).sum()
        ),
        "two_boundary_applied_rows": int(
            (burden.condition.eq("ANGLE_PLUS_TWO_BOUNDARY_SCENE_LAYER") & burden.condition_applied).sum()
        ),
        "two_boundary_fallback_rows": int(
            (burden.condition.eq("ANGLE_PLUS_TWO_BOUNDARY_SCENE_LAYER") & ~burden.condition_applied).sum()
        ),
        "known_operator_contaminated_cases": int(case_selection.operator_contaminated_known_case.sum()),
        "manual_person_sar_reference_opened": False,
    }
    write_json(PRE / "denominators_pre_reference.json", denominators)

    freeze_paths = [
        PRE / "BOUNDARY_VALUE_ELIGIBLE_GEOMETRY_PRE_REFERENCE.csv",
        PRE / "BOUNDARY_VALUE_ELIGIBLE_GEOMETRY_PRE_REFERENCE.parquet",
        PRE / "optical_person_scene_layer_visual_cases_frozen_pre_reference.csv",
        PRE / "optical_person_scene_layer_visual_cases_frozen_pre_reference.parquet",
        PRE / "optical_person_scene_layer_pre_reference.csv",
        PRE / "optical_person_scene_layer_pre_reference.parquet",
        PRE / "runtime_support_burden_pre_reference.csv",
        PRE / "runtime_support_burden_pre_reference.parquet",
        PRE / "runtime_support_burden_summary_pre_reference.csv",
        PRE / "runtime_support_burden_summary_pre_reference.parquet",
        PRE / "case_selection_pre_reference.csv",
        PRE / "case_selection_pre_reference.parquet",
        PRE / "denominators_pre_reference.json",
        *mask_paths,
    ]
    freeze = freeze_manifest(
        freeze_paths,
        {
            "condition_definitions": {
                "ANGLE_ONLY": "Frozen optical angular corridor times full SAR depth.",
                "ANGLE_PLUS_ONE_CURB_HALFSPACE": "Previous GT-blind 7.10 m curb band low edge with SIDEWALK_OR_PARKING_SIDE visual label; otherwise angle-only fallback.",
                "ANGLE_PLUS_TWO_BOUNDARY_SCENE_LAYER": "Exact per-pixel radial comparison with trusted near/far curves; only full theta coverage and non-UNCERTAIN visual layer apply.",
            },
            "denominators": denominators,
        },
    )
    print(json.dumps({"freeze_root": freeze["pre_reference_root_sha256"], **denominators}, indent=2))


if __name__ == "__main__":
    main()
