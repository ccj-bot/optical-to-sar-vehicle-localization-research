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
POST = OUT / "post_reference_evaluation_only"

B0_POST = (
    WORKSPACE
    / "output"
    / "person_b0_end_to_end_capability_and_bottleneck_study_20260830"
    / "post_reference_oracle_diagnostic_only"
)
R02_REFERENCE = B0_POST / "r01_r02_r03_manual_range_reference_oracle_only.parquet"
RAW_TARGET_MAP = B0_POST / "raw_fragment_to_offline_target_mapping_oracle_only.csv"

BOUNDARIES = PRE / "BOUNDARY_VALUE_ELIGIBLE_GEOMETRY_PRE_REFERENCE.parquet"
QUEUE = PRE / "optical_person_scene_layer_pre_reference.parquet"
BURDEN = PRE / "runtime_support_burden_pre_reference.parquet"
FREEZE = PRE / "PRE_REFERENCE_FREEZE_MANIFEST.json"

CONDITIONS = (
    "ANGLE_ONLY",
    "ANGLE_PLUS_ONE_CURB_HALFSPACE",
    "ANGLE_PLUS_TWO_BOUNDARY_SCENE_LAYER",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().lower()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def write_table(frame: pd.DataFrame, stem: Path) -> None:
    stem.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(stem.with_suffix(".csv"), index=False, encoding="utf-8-sig")
    frame.to_parquet(stem.with_suffix(".parquet"), index=False, compression="zstd")


def verify_freeze() -> dict[str, Any]:
    if not FREEZE.exists():
        raise RuntimeError("Reference gate violation: pre-reference freeze manifest missing")
    manifest = json.loads(FREEZE.read_text(encoding="utf-8"))
    if manifest.get("manual_person_sar_reference_opened") is not False:
        raise RuntimeError("Reference gate violation: freeze state is not closed")
    root_lines = []
    for item in manifest["files"]:
        path = OUT / item["path"]
        if not path.exists():
            raise RuntimeError(f"Frozen file missing: {path}")
        digest = sha256_file(path)
        if digest != item["sha256"] or path.stat().st_size != int(item["bytes"]):
            raise RuntimeError(f"Frozen file changed: {path}")
        root_lines.append(f"{item['path']}|{item['bytes']}|{item['sha256']}")
    root = hashlib.sha256("\n".join(root_lines).encode("utf-8")).hexdigest().lower()
    if root != manifest["pre_reference_root_sha256"]:
        raise RuntimeError("Pre-reference root hash mismatch")
    return manifest


def parse_intervals(value: str) -> list[list[float]]:
    return [[float(low), float(high)] for low, high in json.loads(value)]


def theta_retained(theta: float, intervals: list[list[float]]) -> bool:
    return any(low <= theta <= high for low, high in intervals)


def interpolate_boundary(record: pd.Series, theta: float) -> float | None:
    nodes = np.asarray(json.loads(str(record.theta_nodes_json)), dtype=float)
    radii = np.asarray(json.loads(str(record.radius_nodes_m_json)), dtype=float)
    order = np.argsort(nodes)
    nodes = nodes[order]
    radii = radii[order]
    if theta < float(nodes[0]) or theta > float(nodes[-1]):
        return None
    return float(np.interp(theta, nodes, radii))


def range_stratum(value: float) -> str:
    if value < 6.0:
        return "LT6M"
    if value < 8.0:
        return "6_TO_8M"
    if value < 12.0:
        return "8_TO_12M"
    if value < 14.0:
        return "12_TO_14M"
    return "GE14M"


def main() -> None:
    if WORKSPACE.resolve() != Path(r"D:\profile\research\workspace").resolve():
        raise RuntimeError(WORKSPACE)
    for path in (TASK, OUT, R02_REFERENCE, RAW_TARGET_MAP):
        lowered = str(path).lower()
        if "old_work" in lowered or "r04" in lowered:
            raise RuntimeError(f"Forbidden path: {path}")
    manifest = verify_freeze()

    queue = pd.read_parquet(QUEUE)
    burden = pd.read_parquet(BURDEN)
    boundaries = pd.read_parquet(BOUNDARIES)
    boundary_index = {
        (int(row.sar_frame_index), str(row.object_type)): pd.Series(row._asdict())
        for row in boundaries.itertuples(index=False)
    }

    # Reference files are intentionally opened only after the full freeze validates above.
    reference = pd.read_parquet(R02_REFERENCE)
    reference = reference[reference.run_id.eq("R02ZF")].copy()
    mapping = pd.read_csv(RAW_TARGET_MAP, encoding="utf-8-sig")
    mapping = mapping[mapping.run_id.eq("R02ZF")].copy()
    entity_column = "entity_id" if "entity_id" in mapping.columns else "raw_track_fragment_id"
    mapping = mapping.rename(columns={entity_column: "person_hypothesis_id"})
    mapping = mapping[["run_id", "person_hypothesis_id", "target_id"]].drop_duplicates()

    matched = queue.merge(mapping, on=["run_id", "person_hypothesis_id"], how="left", validate="many_to_many")
    matched = matched.merge(
        reference[
            [
                "run_id",
                "frame_index",
                "target_id",
                "reference_range_m",
                "reference_theta_deg",
                "reference_support_status",
            ]
        ],
        left_on=["run_id", "sar_frame", "target_id"],
        right_on=["run_id", "frame_index", "target_id"],
        how="inner",
        validate="many_to_one",
    )

    rows: list[dict[str, Any]] = []
    for item in matched.itertuples(index=False):
        frame_index = int(item.sar_frame)
        theta = float(item.reference_theta_deg)
        radius = float(item.reference_range_m)
        intervals = parse_intervals(str(item.effective_intervals_json))
        angular = theta_retained(theta, intervals)
        contaminated = bool(
            frame_index == 472
            and str(item.person_hypothesis_id) == "R02ZF_REUSED_R02ZF_PERSON017"
        )
        condition_rows = burden[burden.shell_id.eq(str(item.shell_id))].set_index("condition")
        for condition in CONDITIONS:
            condition_row = condition_rows.loc[condition]
            applied = bool(condition_row.condition_applied)
            if condition == "ANGLE_ONLY":
                radial = True
                radial_state = "FULL_DEPTH_NO_RADIAL_PRUNE"
                near_radius = far_radius = math.nan
            elif condition == "ANGLE_PLUS_ONE_CURB_HALFSPACE":
                if applied:
                    d_ref = radius * math.cos(math.radians(theta))
                    threshold = float(condition_row.one_curb_d_parallel_threshold_m)
                    radial = d_ref >= threshold
                    radial_state = "ONE_CURB_D_PARALLEL_HALFSPACE_TESTED"
                else:
                    radial = True
                    radial_state = "FALLBACK_NO_RADIAL_PRUNE"
                near_radius = far_radius = math.nan
            else:
                if applied:
                    near_radius_value = interpolate_boundary(
                        boundary_index[(frame_index, "SAR_BOUNDARY_NEAR")], theta
                    )
                    far_radius_value = interpolate_boundary(
                        boundary_index[(frame_index, "SAR_BOUNDARY_FAR")], theta
                    )
                    if near_radius_value is None or far_radius_value is None:
                        raise RuntimeError(f"Applied boundary does not cover reference theta: {item.shell_id}")
                    near_radius = near_radius_value
                    far_radius = far_radius_value
                    layer = str(item.scene_layer)
                    if layer == "L0":
                        radial = radius <= near_radius
                    elif layer == "L1":
                        radial = near_radius <= radius <= far_radius
                    elif layer == "L2":
                        radial = radius >= far_radius
                    else:
                        raise RuntimeError(layer)
                    radial_state = f"TWO_BOUNDARY_{layer}_REFERENCE_POINT_TESTED"
                else:
                    radial = True
                    radial_state = "FALLBACK_NO_RADIAL_PRUNE"
                    near_radius = far_radius = math.nan
            support_2d = bool(angular and radial)
            rows.append(
                {
                    "run_id": "R02ZF",
                    "sar_frame": frame_index,
                    "shell_id": str(item.shell_id),
                    "person_hypothesis_id": str(item.person_hypothesis_id),
                    "optical_review_id": str(item.optical_review_id),
                    "optical_frame": int(item.optical_frame),
                    "scene_layer": str(item.scene_layer),
                    "target_id_oracle": str(item.target_id),
                    "reference_range_m": radius,
                    "reference_theta_deg": theta,
                    "reference_support_status": str(item.reference_support_status),
                    "reference_range_stratum": range_stratum(radius),
                    "condition": condition,
                    "condition_applied": applied,
                    "condition_state_pre_reference": str(condition_row.condition_state),
                    "radial_evaluation_state": radial_state,
                    "near_boundary_radius_at_reference_theta_m": near_radius,
                    "far_boundary_radius_at_reference_theta_m": far_radius,
                    "REFERENCE_THETA_SUPPORT_RETAINED": bool(angular),
                    "REFERENCE_RADIAL_SUPPORT_RETAINED": bool(radial),
                    "REFERENCE_2D_SUPPORT_RETAINED": support_2d,
                    "FALSE_SCENE_LAYER_PRUNE": bool(
                        condition == "ANGLE_PLUS_TWO_BOUNDARY_SCENE_LAYER"
                        and applied
                        and angular
                        and not radial
                    ),
                    "operator_contaminated_known_case": contaminated,
                    "confirmatory_uncontaminated": not contaminated,
                    "post_reference_only": True,
                }
            )
    retention = pd.DataFrame(rows)
    if not retention.empty and len(retention) != len(matched) * len(CONDITIONS):
        raise RuntimeError("Incomplete post-reference condition rows")
    write_table(retention, POST / "reference_support_retention_post_reference")

    summary_rows: list[dict[str, Any]] = []
    for condition in CONDITIONS:
        group = retention[retention.condition.eq(condition)]
        populations = [
            ("ALL_MATCHED_DISCLOSED", group),
            ("CONFIRMATORY_UNCONTAMINATED", group[group.confirmatory_uncontaminated]),
            (
                "CONFIRMATORY_UNCONTAMINATED_APPLIED_ONLY",
                group[group.confirmatory_uncontaminated & group.condition_applied],
            ),
        ]
        for population, subset in populations:
            summary_rows.append(
                {
                    "condition": condition,
                    "population": population,
                    "reference_rows": len(subset),
                    "unique_targets": int(subset.target_id_oracle.nunique()) if len(subset) else 0,
                    "condition_applied_rows": int(subset.condition_applied.sum()) if len(subset) else 0,
                    "theta_retention_fraction": float(subset.REFERENCE_THETA_SUPPORT_RETAINED.mean()) if len(subset) else math.nan,
                    "radial_retention_fraction": float(subset.REFERENCE_RADIAL_SUPPORT_RETAINED.mean()) if len(subset) else math.nan,
                    "support_2d_retention_fraction": float(subset.REFERENCE_2D_SUPPORT_RETAINED.mean()) if len(subset) else math.nan,
                    "false_scene_layer_prune_count": int(subset.FALSE_SCENE_LAYER_PRUNE.sum()) if len(subset) else 0,
                    "operator_contaminated_rows": int(subset.operator_contaminated_known_case.sum()) if len(subset) else 0,
                }
            )
    summary = pd.DataFrame(summary_rows)
    write_table(summary, POST / "reference_support_retention_summary_post_reference")

    layer = retention[
        retention.condition.eq("ANGLE_PLUS_TWO_BOUNDARY_SCENE_LAYER")
        & retention.confirmatory_uncontaminated
    ].copy()
    layer_summary = (
        layer.groupby(["scene_layer", "reference_range_stratum"], dropna=False)
        .agg(
            reference_rows=("shell_id", "size"),
            unique_targets=("target_id_oracle", "nunique"),
            reference_range_median=("reference_range_m", "median"),
            applied_rows=("condition_applied", "sum"),
            radial_retention_fraction=("REFERENCE_RADIAL_SUPPORT_RETAINED", "mean"),
            support_2d_retention_fraction=("REFERENCE_2D_SUPPORT_RETAINED", "mean"),
        )
        .reset_index()
    )
    write_table(layer_summary, POST / "scene_layer_vs_reference_range_strata_post_reference")

    audit = {
        "schema": "PERSON_R02_SCENE_DEPTH_POST_REFERENCE_GATE_AUDIT_V1",
        "pre_reference_root_sha256": manifest["pre_reference_root_sha256"],
        "reference_source": str(R02_REFERENCE),
        "mapping_source": str(RAW_TARGET_MAP),
        "reference_opened_only_after_freeze_validation": True,
        "matched_reference_rows": len(matched),
        "operator_contaminated_rows_disclosed": int(
            retention[retention.condition.eq("ANGLE_ONLY")].operator_contaminated_known_case.sum()
        ) if len(retention) else 0,
        "r04_accessed": False,
        "final_localization_run": False,
    }
    write_json(POST / "post_reference_gate_audit.json", audit)
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    print(summary.to_string(index=False))
    print(layer_summary.to_string(index=False))


if __name__ == "__main__":
    main()
