from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd


WORKSPACE = Path(r"D:\profile\research\workspace")
TASK = WORKSPACE / "tasks" / "r02_local_boundary_observability_20260902"
OUT = WORKSPACE / "output" / "r02_local_boundary_observability_20260902"
PRE = OUT / "pre_reference"
SEEDS = PRE / "isolated_seed_inputs"
RUNS = PRE / "runs"
FROZEN_SCRIPT = (
    WORKSPACE
    / "tasks"
    / "r02_manual_seed_temporal_propagation_20260902"
    / "run_manual_seed_temporal_propagation.py"
)
MANUAL_SOURCES = [
    WORKSPACE
    / "output"
    / "r02_manual_static_scene_anchor_preparation_20260902"
    / "user_annotations"
    / "manual_static_scene_annotations.jsonl",
    WORKSPACE
    / "output"
    / "r02_boundary_multibracket_preparation_20260902"
    / "user_annotations"
    / "manual_static_scene_annotations.jsonl",
    WORKSPACE
    / "output"
    / "r02_boundary_multibracket_replication_20260902"
    / "repair_user_annotations"
    / "manual_static_scene_annotations.jsonl",
]
PRIMARY_SEEDS = [62, 150, 183, 264, 454]
BOUNDARIES = ["SAR_BOUNDARY_NEAR", "SAR_BOUNDARY_FAR"]
EXPECTED_FROZEN_SHA256 = "e80bd4ae8ff808c290340a1452c35f3fe72099051b7742178ad85ea902a90967"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def latest_sar_boundaries(path: Path) -> tuple[list[dict[str, object]], int]:
    raw = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    latest: dict[tuple[int, str], dict[str, object]] = {}
    for event in raw:
        if event.get("modality") == "SAR" and event.get("object_type") in BOUNDARIES:
            latest[(int(event["sar_frame_index"]), str(event["object_type"]))] = event
    active = [
        event
        for event in latest.values()
        if event.get("event_type") != "DELETE"
        and event.get("confidence_state") in {"CONFIDENT", "LIKELY"}
        and len(event.get("points", [])) >= 2
    ]
    return active, len(raw)


def prepare() -> None:
    if sha256(FROZEN_SCRIPT) != EXPECTED_FROZEN_SHA256:
        raise RuntimeError("Frozen source changed")
    SEEDS.mkdir(parents=True, exist_ok=True)
    all_active: dict[tuple[int, str], tuple[dict[str, object], Path]] = {}
    source_manifest = []
    for path in MANUAL_SOURCES:
        active, count = latest_sar_boundaries(path)
        source_manifest.append(
            {
                "path": str(path),
                "event_count": count,
                "sha256": sha256(path),
                "active_sar_boundary_record_count": len(active),
            }
        )
        for event in active:
            key = (int(event["sar_frame_index"]), str(event["object_type"]))
            if key in all_active:
                raise RuntimeError(f"Duplicate active checkpoint boundary: {key}")
            all_active[key] = (event, path)

    seed_manifest = []
    for frame_index in PRIMARY_SEEDS:
        rows = []
        for object_type in BOUNDARIES:
            event, source = all_active[(frame_index, object_type)]
            rows.append(
                {
                    "schema": "R02_ISOLATED_LOCAL_BOUNDARY_SEED_V1",
                    "run_id": "R02ZF",
                    "sar_frame_index": frame_index,
                    "sar_timestamp_ms": int(event["sar_timestamp_ms"]),
                    "object_type": object_type,
                    "points": event["points"],
                    "confidence_state": str(event["confidence_state"]),
                    "source_geometry_status": str(event["geometry_status"]),
                    "derived_geometry_status": "USER_CONFIRMED_SEMANTIC_CHECKPOINT",
                    "source_event_id": str(event["event_id"]),
                    "source_revision": int(event["revision"]),
                    "source_manual_path": str(source),
                    "source_manual_sha256": sha256(source),
                    "other_checkpoint_geometry_included": False,
                    "person_gt": False,
                    "final_localization": False,
                }
            )
        seed_path = SEEDS / f"F{frame_index:03d}.json"
        write_json(seed_path, {"seed_frame": frame_index, "boundaries": rows})
        seed_manifest.append(
            {
                "seed_frame": frame_index,
                "seed_file": str(seed_path),
                "seed_file_sha256": sha256(seed_path),
                "boundary_record_count": len(rows),
                "included_frame_ids": sorted({int(row["sar_frame_index"]) for row in rows}),
            }
        )
    write_json(
        PRE / "SEED_INPUT_MANIFEST.json",
        {
            "schema": "R02_LOCAL_OBSERVABILITY_SEED_INPUT_MANIFEST_V1",
            "primary_seed_frames": PRIMARY_SEEDS,
            "source_manual_files": source_manifest,
            "actual_active_manual_checkpoint_frames": sorted({frame for frame, _ in all_active}),
            "actual_active_manual_boundary_record_count": len(all_active),
            "isolated_seed_files": seed_manifest,
            "frozen_source_sha256": sha256(FROZEN_SCRIPT),
            "manual_files_modified": False,
            "r04_accessed": False,
            "person_experiment_run": False,
        },
    )
    print(json.dumps({"status": "PREPARED", "primary_seed_frames": PRIMARY_SEEDS}, ensure_ascii=False))


def seed_theta(frozen, boundaries: list[dict[str, object]], registry: pd.DataFrame) -> np.ndarray:
    row = registry.loc[int(boundaries[0]["sar_frame_index"])]
    extents = []
    for boundary in boundaries:
        theta_values = [frozen.point_to_theta_d(point, row)[0] for point in boundary["points"]]
        extents.append((min(theta_values), max(theta_values)))
    low = max(item[0] for item in extents) + 1.0
    high = min(item[1] for item in extents) - 1.0
    grid_low = math.ceil(low / frozen.THETA_STEP_DEG) * frozen.THETA_STEP_DEG
    grid_high = math.floor(high / frozen.THETA_STEP_DEG) * frozen.THETA_STEP_DEG
    theta = np.arange(grid_low, grid_high + 0.001, frozen.THETA_STEP_DEG, dtype=float)
    if len(theta) < 8:
        raise RuntimeError(f"Seed corridor too narrow: {low} to {high}")
    return theta


def curve_rows(
    frozen,
    seed_frame: int,
    path_kind: str,
    direction: str,
    curves: dict[int, dict[str, np.ndarray]],
    theta: np.ndarray,
    registry: pd.DataFrame,
) -> list[dict[str, object]]:
    rows = []
    for frame_index in sorted(curves):
        for object_type, curve in curves[frame_index].items():
            rows.append(
                {
                    "schema": "R02_LOCAL_BOUNDARY_PATH_V1",
                    "run_id": "R02ZF",
                    "seed_frame": seed_frame,
                    "path_kind": path_kind,
                    "direction": direction,
                    "sar_frame_index": frame_index,
                    "sar_timestamp_ms": int(registry.loc[frame_index].sar_timestamp_ms),
                    "object_type": object_type,
                    "theta_grid_deg": [float(value) for value in theta],
                    "d_curve_m": [round(float(value), 6) for value in curve],
                    "d_center_m": float(np.median(curve)),
                    "d_shape_span_m": float(np.ptp(curve)),
                    "points": frozen.curve_to_points(theta, curve, registry.loc[frame_index]),
                    "manual_seed_frame": frame_index == seed_frame,
                    "curve_update_semantics": "RIGID_WHOLE_CURVE_SCALAR_D_PERP_SHIFT",
                    "other_manual_checkpoint_geometry_read": False,
                    "person_gt": False,
                    "final_localization": False,
                }
            )
    return rows


def propagate_independent_boundary(
    frozen,
    object_type: str,
    seed_frame: int,
    end_frame: int,
    seed_curve: np.ndarray,
    theta: np.ndarray,
    registry: pd.DataFrame,
    transforms: dict[tuple[int, int], dict[str, object]],
    evidence,
    direction: str,
) -> tuple[dict[int, dict[str, np.ndarray]], list[dict[str, object]], dict[str, object] | None]:
    step = 1 if end_frame > seed_frame else -1
    curves = {seed_frame: {object_type: seed_curve.copy()}}
    current = seed_curve.copy()
    diagnostics = []
    stop = None
    for destination in range(seed_frame + step, end_frame + step, step):
        source = destination - step
        proposal = frozen.propose_curve(
            object_type,
            source,
            destination,
            current,
            theta,
            registry,
            transforms,
            evidence,
        )
        diagnostics.append(
            {
                "seed_frame": seed_frame,
                "path_kind": "BOUNDARY_INDEPENDENT_DIAGNOSTIC",
                "direction": direction,
                "source_frame": source,
                "destination_frame": destination,
                "object_type": object_type,
                "status": proposal.status,
                "reasons": "|".join(proposal.reasons),
                "best_score": proposal.best_score,
                "best_offset_m": proposal.best_offset_m,
                "second_score": proposal.second_score,
                "second_offset_m": proposal.second_offset_m,
                "second_ratio": proposal.second_ratio,
                "node_support_fraction": proposal.node_support_fraction,
                "p0_dx_px": proposal.p0_dx_px,
                "p0_dy_px": proposal.p0_dy_px,
            }
        )
        if proposal.status != "SUPPORTED":
            stop = {
                "seed_frame": seed_frame,
                "path_kind": "BOUNDARY_INDEPENDENT_DIAGNOSTIC",
                "direction": direction,
                "object_type": object_type,
                "source_frame": source,
                "destination_frame": destination,
                "status": proposal.status,
                "reasons": proposal.reasons,
            }
            break
        current = proposal.curve_m.copy()
        curves[destination] = {object_type: current.copy()}
    return curves, diagnostics, stop


def sanitize(value: object) -> object:
    if isinstance(value, dict):
        return {key: sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def propagate(seed_file: Path) -> None:
    if sha256(FROZEN_SCRIPT) != EXPECTED_FROZEN_SHA256:
        raise RuntimeError("Frozen source changed")
    seed_payload = json.loads(seed_file.read_text(encoding="utf-8"))
    seed_frame = int(seed_payload["seed_frame"])
    included_frames = sorted({int(row["sar_frame_index"]) for row in seed_payload["boundaries"]})
    if included_frames != [seed_frame] or len(seed_payload["boundaries"]) != 2:
        raise RuntimeError("Seed isolation violated")
    frozen = load_module(f"r02_frozen_local_observability_f{seed_frame}", FROZEN_SCRIPT)
    registry = frozen.load_registry()
    transforms = frozen.load_p0_transforms()
    p1e = frozen.load_module(f"r02_local_observability_p1e_f{seed_frame}", frozen.P1E_SCRIPT)
    evidence = frozen.EvidenceCache(registry, p1e)
    theta = seed_theta(frozen, seed_payload["boundaries"], registry)
    seed_curves = {
        str(row["object_type"]): frozen.manual_curve(row["points"], registry.loc[seed_frame], theta)
        for row in seed_payload["boundaries"]
    }
    expected_separation = float(
        np.median(seed_curves["SAR_BOUNDARY_FAR"] - seed_curves["SAR_BOUNDARY_NEAR"])
    )
    result_dir = RUNS / f"F{seed_frame:03d}"
    result_dir.mkdir(parents=True, exist_ok=True)
    pair_rows: list[dict[str, object]] = []
    individual_rows: list[dict[str, object]] = []
    diagnostics: list[dict[str, object]] = []
    stops = []
    segment_summary = []
    for direction, end_frame in (("BACKWARD", 0), ("FORWARD", int(registry.index.max()))):
        pair_curves, pair_diag, pair_stop = frozen.propagate_direction(
            seed_frame,
            end_frame,
            seed_curves,
            expected_separation,
            theta,
            registry,
            transforms,
            evidence,
            f"F{seed_frame:03d}_{direction}_PAIR_SAFE",
        )
        pair_rows.extend(curve_rows(frozen, seed_frame, "PAIR_SAFE_FROZEN", direction, pair_curves, theta, registry))
        for row in pair_diag:
            diagnostics.append(sanitize({"seed_frame": seed_frame, "path_kind": "PAIR_SAFE_FROZEN", **row}))
        if pair_stop:
            stops.append(sanitize({"seed_frame": seed_frame, "path_kind": "PAIR_SAFE_FROZEN", **pair_stop}))
        frames = sorted(pair_curves)
        segment_summary.append(
            {
                "seed_frame": seed_frame,
                "path_kind": "PAIR_SAFE_FROZEN",
                "direction": direction,
                "object_type": "NEAR_AND_FAR",
                "start_frame": min(frames),
                "end_frame": max(frames),
                "frame_count": len(frames),
                "natural_stop": sanitize(pair_stop),
            }
        )
        for object_type in BOUNDARIES:
            curves, diag, stop = propagate_independent_boundary(
                frozen,
                object_type,
                seed_frame,
                end_frame,
                seed_curves[object_type],
                theta,
                registry,
                transforms,
                evidence,
                direction,
            )
            individual_rows.extend(
                curve_rows(
                    frozen,
                    seed_frame,
                    "BOUNDARY_INDEPENDENT_DIAGNOSTIC",
                    direction,
                    curves,
                    theta,
                    registry,
                )
            )
            diagnostics.extend(sanitize(diag))
            if stop:
                stops.append(sanitize(stop))
            frames = sorted(curves)
            segment_summary.append(
                {
                    "seed_frame": seed_frame,
                    "path_kind": "BOUNDARY_INDEPENDENT_DIAGNOSTIC",
                    "direction": direction,
                    "object_type": object_type,
                    "start_frame": min(frames),
                    "end_frame": max(frames),
                    "frame_count": len(frames),
                    "natural_stop": sanitize(stop),
                }
            )
    write_jsonl(result_dir / "pair_safe_paths.jsonl", pair_rows)
    write_jsonl(result_dir / "boundary_independent_paths.jsonl", individual_rows)
    pd.DataFrame(diagnostics).to_csv(result_dir / "frame_diagnostics.csv", index=False, encoding="utf-8-sig")
    write_json(result_dir / "stop_events.json", stops)
    write_json(
        result_dir / "RUN_SUMMARY.json",
        {
            "schema": "R02_ISOLATED_SEED_LOCAL_OBSERVABILITY_RUN_V1",
            "seed_frame": seed_frame,
            "seed_file": str(seed_file),
            "seed_file_sha256": sha256(seed_file),
            "input_disclosure": {
                "manual_geometry_files_read": [str(seed_file)],
                "manual_frame_ids_available_to_process": [seed_frame],
                "other_checkpoint_geometry_read": False,
                "runtime_inputs": [str(FROZEN_SCRIPT), str(frozen.REGISTRY), str(frozen.P0_EDGES), str(frozen.P1E_SCRIPT)],
            },
            "theta_corridor_deg": [float(theta.min()), float(theta.max())],
            "theta_node_count": len(theta),
            "expected_seed_pair_separation_m": expected_separation,
            "segments": segment_summary,
            "frozen_source_sha256": sha256(FROZEN_SCRIPT),
            "parameter_tuning": False,
            "curve_shape_update": "NONE_RIGID_SCALAR_SHIFT_ONLY",
            "pair_safe_geometry_accepted_for_optional_context": True,
            "boundary_independent_geometry_is_diagnostic_only": True,
            "r04_accessed": False,
            "person_experiment_run": False,
            "tree_experiment_run": False,
            "final_localization_run": False,
        },
    )
    print(json.dumps({"status": "PROPAGATED", "seed_frame": seed_frame}, ensure_ascii=False))


def contiguous_components(frames: set[int]) -> list[list[int]]:
    components: list[list[int]] = []
    for frame in sorted(frames):
        if not components or frame != components[-1][-1] + 1:
            components.append([frame])
        else:
            components[-1].append(frame)
    return components


def consolidate() -> None:
    pair_rows = []
    individual_rows = []
    segment_rows = []
    stop_rows = []
    run_summaries = []
    for seed_frame in PRIMARY_SEEDS:
        run_dir = RUNS / f"F{seed_frame:03d}"
        pair_rows.extend(
            json.loads(line)
            for line in (run_dir / "pair_safe_paths.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
        individual_rows.extend(
            json.loads(line)
            for line in (run_dir / "boundary_independent_paths.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
        summary = json.loads((run_dir / "RUN_SUMMARY.json").read_text(encoding="utf-8"))
        run_summaries.append(summary)
        segment_rows.extend(summary["segments"])
        stop_rows.extend(json.loads((run_dir / "stop_events.json").read_text(encoding="utf-8")))
    write_jsonl(PRE / "ALL_PAIR_SAFE_PATHS.jsonl", pair_rows)
    write_jsonl(PRE / "ALL_BOUNDARY_INDEPENDENT_PATHS.jsonl", individual_rows)
    pd.DataFrame(segment_rows).to_csv(PRE / "LOCAL_SEGMENTS.csv", index=False, encoding="utf-8-sig")
    write_json(PRE / "STOP_EVENTS.json", stop_rows)

    pair_frames = {int(row["sar_frame_index"]) for row in pair_rows}
    individual_by_type = {
        object_type: {int(row["sar_frame_index"]) for row in individual_rows if row["object_type"] == object_type}
        for object_type in BOUNDARIES
    }
    timeline = []
    for frame_index in range(495):
        near = frame_index in individual_by_type["SAR_BOUNDARY_NEAR"]
        far = frame_index in individual_by_type["SAR_BOUNDARY_FAR"]
        pair = frame_index in pair_frames
        scene_state = "BOTH_SUPPORTED" if pair else "PARTIAL" if near or far else "UNKNOWN"
        timeline.append(
            {
                "sar_frame_index": frame_index,
                "near_state": "SUPPORTED" if near else "UNKNOWN",
                "far_state": "SUPPORTED" if far else "UNKNOWN",
                "pair_safe_state": "SUPPORTED" if pair else "UNKNOWN",
                "scene_boundary_state": scene_state,
                "accepted_as_optional_scene_context": pair,
            }
        )
    pd.DataFrame(timeline).to_csv(PRE / "FULL_R02_LOCAL_OBSERVABILITY_TIMELINE.csv", index=False, encoding="utf-8-sig")
    pair_components = contiguous_components(pair_frames)
    component_rows = [
        {
            "component_index": index,
            "start_frame": component[0],
            "end_frame": component[-1],
            "frame_count": len(component),
            "state": "BOTH_SUPPORTED_PAIR_SAFE",
        }
        for index, component in enumerate(pair_components, start=1)
    ]
    pd.DataFrame(component_rows).to_csv(PRE / "PAIR_SAFE_SUPPORTED_COMPONENTS.csv", index=False, encoding="utf-8-sig")
    state_counts = pd.DataFrame(timeline).scene_boundary_state.value_counts().to_dict()
    boundary_state_counts = {
        "near_supported": len(individual_by_type["SAR_BOUNDARY_NEAR"]),
        "far_supported": len(individual_by_type["SAR_BOUNDARY_FAR"]),
        "both_pair_safe_supported": len(pair_frames),
        "partial": int(state_counts.get("PARTIAL", 0)),
        "unknown": int(state_counts.get("UNKNOWN", 0)),
    }
    write_json(
        PRE / "PRE_REFERENCE_SUMMARY.json",
        {
            "schema": "R02_LOCAL_BOUNDARY_OBSERVABILITY_PRE_REFERENCE_SUMMARY_V1",
            "primary_seed_frames": PRIMARY_SEEDS,
            "run_count": len(run_summaries),
            "pair_safe_directional_segment_count": sum(
                1 for row in segment_rows if row["path_kind"] == "PAIR_SAFE_FROZEN"
            ),
            "supported_component_count": len(pair_components),
            "supported_components": component_rows,
            "total_frame_count": 495,
            "pair_safe_supported_frame_count": len(pair_frames),
            "pair_safe_supported_frame_fraction": len(pair_frames) / 495,
            "unknown_for_optional_context_frame_count": 495 - len(pair_frames),
            "unknown_for_optional_context_frame_fraction": (495 - len(pair_frames)) / 495,
            "boundary_independent_state_counts": boundary_state_counts,
            "full_stream_closure_rate_is_kpi": False,
            "unknown_gaps_are_legal": True,
            "parameter_tuning": False,
            "manual_checkpoint_geometry_used_for_stop_or_selection": False,
            "r04_accessed": False,
            "person_experiment_run": False,
            "tree_experiment_run": False,
            "final_localization_run": False,
        },
    )
    print(json.dumps({"status": "CONSOLIDATED", **boundary_state_counts}, ensure_ascii=False))


def freeze() -> None:
    manifest_path = OUT / "PRE_REFERENCE_FREEZE_MANIFEST.json"
    rows = []
    for path in sorted(PRE.rglob("*")):
        if path.is_file():
            rows.append(
                {
                    "workspace_relative_path": path.relative_to(WORKSPACE).as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": sha256(path),
                }
            )
    write_json(
        manifest_path,
        {
            "schema": "R02_LOCAL_BOUNDARY_OBSERVABILITY_PRE_REFERENCE_FREEZE_V1",
            "file_count": len(rows),
            "files": rows,
            "manual_checkpoints_revealed_for_audit": False,
            "frozen_source_sha256": sha256(FROZEN_SCRIPT),
            "parameter_tuning": False,
        },
    )
    print(json.dumps({"status": "FROZEN", "file_count": len(rows), "manifest_sha256": sha256(manifest_path)}, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["prepare", "propagate", "consolidate", "freeze"])
    parser.add_argument("--seed-file", type=Path)
    args = parser.parse_args()
    if args.phase == "prepare":
        prepare()
    elif args.phase == "propagate":
        if args.seed_file is None:
            raise SystemExit("--seed-file required")
        propagate(args.seed_file)
    elif args.phase == "consolidate":
        consolidate()
    else:
        freeze()


if __name__ == "__main__":
    main()
