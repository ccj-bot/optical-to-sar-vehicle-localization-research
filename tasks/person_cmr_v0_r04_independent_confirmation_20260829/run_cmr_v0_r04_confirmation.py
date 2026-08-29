from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw


SCRIPT = Path(__file__).resolve()
TASK = SCRIPT.parent
WORKSPACE = TASK.parents[1]
STUDY = WORKSPACE / "output" / "person_physics_guided_image_domain_study_20260824"
OUTPUT = STUDY / "cmr_v0_r04_independent_confirmation"
PRE = OUTPUT / "pre_reference"
MECHANISM = PRE / "mechanism"
POST = OUTPUT / "post_reference"
FIGURES = POST / "figures" / "cases"
LOG = WORKSPACE / "logs" / "20260829_person_cmr_v0_r04_independent_confirmation.md"

DEV_TASK = WORKSPACE / "tasks" / "person_cmr_d0_common_residual_motion_mechanism_development_20260829"
DEV_RUNNER = DEV_TASK / "run_cmr_d0_development.py"
DEV_OUTPUT = STUDY / "cmr_d0_common_residual_motion_mechanism_development"
DEV_SPEC = DEV_OUTPUT / "CMR_V0_MECHANISM_SPECIFICATION_FROZEN.md"
DEV_MANIFEST = DEV_OUTPUT / "cmr_d0_output_manifest.json"
DEV_ATLAS = DEV_OUTPUT / "cmr_eligible_window_atlas.parquet"

PROTOCOL = TASK / "CMR_V0_R04_CONFIRMATION_PROTOCOL_FROZEN_BEFORE_REVEAL.md"
VALIDATOR = TASK / "validate_cmr_v0_r04_confirmation.py"
PROTOCOL_FREEZE = OUTPUT / "confirmation_protocol_and_evaluator_freeze.json"
CONTROL_FREEZE = PRE / "control_bank_freeze.json"
PRE_MANIFEST = PRE / "pre_reference_output_hash_freeze.json"
REVEAL_MARKER = POST / "REFERENCE_REVEAL_MARKER.json"
FINAL_SUMMARY = POST / "cmr_v0_r04_confirmation_summary.json"
FINAL_REPORT = POST / "CMR_V0_R04_FINAL_CONFIRMATION_REPORT.md"
FINAL_MANIFEST = OUTPUT / "cmr_v0_r04_final_manifest.json"

FROZEN_DEV_RUNNER_SHA256 = "038D7EE67A92483166791D4CCAFA15DB55DB1A3F33BC1FFC1F6DBCBF89877C99"
FROZEN_DEV_SPEC_SHA256 = "24B3CEA3552EF0C61062DAD9E97246922FE76C35A391B8C9242F6EC1968DF317"
FROZEN_DEV_MANIFEST_SHA256 = "0B103CE16AD516087572BBA49F5491AA7BB824371168B58B39894D2A4AD301CB"
FROZEN_ATLAS_SHA256 = "93A89BDFFA39E6480AEBB32F7D001F53C5888EF3087CB8BA34FE0E33C8F6CF79"
RUN_ID = "R04ZF"
CONTROL_COUNT = 5
TEMPORAL_BLOCK_SIZE = 25
NUMERICAL_TOL = 1e-12


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def stable_id(prefix: str, *parts: Any) -> str:
    payload = "||".join(str(value) for value in parts)
    return f"{prefix}_{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:20].upper()}"


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=WORKSPACE, text=True).strip()


def bool_series(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series
    return series.astype(str).str.lower().map({"true": True, "false": False}).fillna(False)


def load_dev() -> Any:
    spec = importlib.util.spec_from_file_location("frozen_cmr_v0_development", DEV_RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load frozen CMR-v0 runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_frozen_sources() -> None:
    expected = {
        DEV_RUNNER: FROZEN_DEV_RUNNER_SHA256,
        DEV_SPEC: FROZEN_DEV_SPEC_SHA256,
        DEV_MANIFEST: FROZEN_DEV_MANIFEST_SHA256,
        DEV_ATLAS: FROZEN_ATLAS_SHA256,
    }
    failures = {str(path): sha256_file(path) for path, digest in expected.items() if sha256_file(path) != digest}
    if failures:
        raise RuntimeError(f"frozen CMR-v0 source mismatch: {failures}")


def freeze_protocol() -> None:
    if REVEAL_MARKER.exists():
        raise RuntimeError("reference was already revealed; protocol cannot be re-frozen")
    verify_frozen_sources()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    shutil.copy2(PROTOCOL, OUTPUT / PROTOCOL.name)
    payload = {
        "schema": "PERSON_CMR_V0_R04_PROTOCOL_EVALUATOR_FREEZE_V1",
        "status": "FROZEN_BEFORE_R04_MECHANISM_AND_REFERENCE_REVEAL",
        "created_at": now_iso(),
        "head": git_head(),
        "run_id": RUN_ID,
        "reference_loaded": False,
        "outcome_accessed": False,
        "mechanism_modified": False,
        "files": {
            "protocol": {"path": str(PROTOCOL.relative_to(WORKSPACE)), "sha256": sha256_file(PROTOCOL)},
            "evaluator": {"path": str(SCRIPT.relative_to(WORKSPACE)), "sha256": sha256_file(SCRIPT)},
            "validator": {"path": str(VALIDATOR.relative_to(WORKSPACE)), "sha256": sha256_file(VALIDATOR)},
            "frozen_mechanism_runner": {"path": str(DEV_RUNNER.relative_to(WORKSPACE)), "sha256": sha256_file(DEV_RUNNER)},
            "frozen_mechanism_spec": {"path": str(DEV_SPEC.relative_to(WORKSPACE)), "sha256": sha256_file(DEV_SPEC)},
            "frozen_development_manifest": {"path": str(DEV_MANIFEST.relative_to(WORKSPACE)), "sha256": sha256_file(DEV_MANIFEST)},
            "frozen_eligible_atlas": {"path": str(DEV_ATLAS.relative_to(WORKSPACE)), "sha256": sha256_file(DEV_ATLAS)},
        },
        "frozen_evaluation_semantics": {
            "control_count": CONTROL_COUNT,
            "temporal_block_size_frames": TEMPORAL_BLOCK_SIZE,
            "sar_only_ranking": "STATIC_FEASIBILITY_ONLY_NO_PREFERENCE",
            "scene_common_preference": "NON_WEIGHTED_PARETO_OVER_SOFT_IOU_RETENTION_DESTINATION_EXPLAINED",
            "candidate_separation": [
                "STRONG_SEPARATION",
                "ASYMMETRIC_SEPARATION",
                "TENDENCY_SEPARATION",
                "NO_SEPARATION",
                "REVERSED_SEPARATION",
            ],
            "strict_outcomes": ["SAR_EDGE_RESCUE", "CONFIRMATION", "HARM", "CONFLICT", "NO_INFORMATION"],
        },
    }
    write_json(PROTOCOL_FREEZE, payload)


def verify_protocol_freeze() -> dict[str, Any]:
    if not PROTOCOL_FREEZE.exists():
        raise RuntimeError("protocol/evaluator freeze is missing")
    payload = json.loads(PROTOCOL_FREEZE.read_text(encoding="utf-8"))
    if payload.get("status") != "FROZEN_BEFORE_R04_MECHANISM_AND_REFERENCE_REVEAL":
        raise RuntimeError("invalid protocol freeze status")
    for item in payload["files"].values():
        path = WORKSPACE / item["path"]
        if sha256_file(path) != item["sha256"]:
            raise RuntimeError(f"frozen file changed: {path}")
    verify_frozen_sources()
    return payload


def r04_atlas() -> pd.DataFrame:
    atlas = pd.read_parquet(DEV_ATLAS)
    atlas = atlas[(atlas["run_id"] == RUN_ID) & atlas["cross_modal_eligible"]].copy()
    if len(atlas) != 98 or int(atlas["runtime_common_fragment_count"].sum()) != 166:
        raise RuntimeError("R04 frozen eligibility accounting changed")
    return atlas.sort_values(["source_sar_frame", "destination_sar_frame"]).reset_index(drop=True)


def enumerate_static_hypotheses(atlas: pd.DataFrame, data: dict[str, Any]) -> pd.DataFrame:
    topology = data["topology"]
    rows: list[dict[str, Any]] = []
    for window in atlas.itertuples(index=False):
        for fragment in str(window.runtime_common_fragments).split(";"):
            source_regions = sorted(
                topology[
                    (topology["run_id"] == RUN_ID)
                    & (topology["frame_index"] == int(window.source_sar_frame))
                    & (topology["track_id"].astype(str) == fragment)
                ]["region_id"].astype(str).unique()
            )
            destination_regions = sorted(
                topology[
                    (topology["run_id"] == RUN_ID)
                    & (topology["frame_index"] == int(window.destination_sar_frame))
                    & (topology["track_id"].astype(str) == fragment)
                ]["region_id"].astype(str).unique()
            )
            for source_region in source_regions:
                for destination_region in destination_regions:
                    rows.append(
                        {
                            "hypothesis_id": stable_id("CMRH", window.window_id, fragment, source_region, destination_region),
                            "window_id": window.window_id,
                            "run_id": RUN_ID,
                            "source_sar_frame": int(window.source_sar_frame),
                            "destination_sar_frame": int(window.destination_sar_frame),
                            "source_optical_frame": int(window.source_optical_frame),
                            "destination_optical_frame": int(window.destination_optical_frame),
                            "raw_track_fragment_id": fragment,
                            "source_region_id": source_region,
                            "destination_region_id": destination_region,
                            "static_pixel_shell_region_feasible": True,
                            "reference_used": False,
                        }
                    )
    return pd.DataFrame(rows)


def add_structural_fields(hypotheses: pd.DataFrame, data: dict[str, Any]) -> pd.DataFrame:
    regions = data["regions"].set_index("region_id", drop=False)
    topology = data["topology"]
    region_degree = topology.groupby(["run_id", "frame_index", "region_id"])["track_id"].nunique().to_dict()
    track_degree = topology.groupby(["run_id", "frame_index", "track_id"])["region_id"].nunique().to_dict()
    rows: list[dict[str, Any]] = []
    for row in hypotheses.itertuples(index=False):
        source = regions.loc[str(row.source_region_id)]
        destination = regions.loc[str(row.destination_region_id)]
        rows.append(
            {
                **row._asdict(),
                "source_pixel_count": int(source.pixel_count),
                "destination_pixel_count": int(destination.pixel_count),
                "source_theta_mid_deg": 0.5 * (float(source.theta_min_deg) + float(source.theta_max_deg)),
                "destination_theta_mid_deg": 0.5 * (float(destination.theta_min_deg) + float(destination.theta_max_deg)),
                "source_theta_width_deg": float(source.theta_max_deg) - float(source.theta_min_deg),
                "destination_theta_width_deg": float(destination.theta_max_deg) - float(destination.theta_min_deg),
                "destination_boundary": bool(source.touches_observable_boundary) or bool(destination.touches_observable_boundary),
                "destination_truncated": bool(source.has_truncated_support) or bool(destination.has_truncated_support),
                "destination_region_degree": int(region_degree.get((RUN_ID, int(row.destination_sar_frame), str(row.destination_region_id)), 0)),
                "destination_track_degree": int(track_degree.get((RUN_ID, int(row.destination_sar_frame), str(row.raw_track_fragment_id)), 0)),
                "absolute_angular_transition_deg": abs(
                    0.5 * (float(destination.theta_min_deg) + float(destination.theta_max_deg))
                    - 0.5 * (float(source.theta_min_deg) + float(source.theta_max_deg))
                ),
            }
        )
    return pd.DataFrame(rows)


def build_control_bank(structural: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    keys = ["window_id", "raw_track_fragment_id", "source_region_id"]
    for _, group in structural.groupby(keys, sort=True):
        records = group.sort_values("hypothesis_id").to_dict("records")
        for primary in records:
            alternatives = []
            for control in records:
                if control["hypothesis_id"] == primary["hypothesis_id"]:
                    continue
                vector = (
                    int(bool(primary["destination_boundary"]) != bool(control["destination_boundary"])),
                    int(bool(primary["destination_truncated"]) != bool(control["destination_truncated"])),
                    abs(int(primary["destination_region_degree"]) - int(control["destination_region_degree"])),
                    abs(math.log1p(float(primary["destination_pixel_count"])) - math.log1p(float(control["destination_pixel_count"]))),
                    abs(float(primary["destination_theta_width_deg"]) - float(control["destination_theta_width_deg"])),
                    abs(float(primary["destination_theta_mid_deg"]) - float(control["destination_theta_mid_deg"])),
                    str(control["hypothesis_id"]),
                )
                alternatives.append((vector, control))
            for rank, (vector, control) in enumerate(sorted(alternatives, key=lambda item: item[0])[:CONTROL_COUNT], start=1):
                rows.append(
                    {
                        "control_pair_id": stable_id("CMRC", primary["hypothesis_id"], control["hypothesis_id"]),
                        "primary_hypothesis_id": primary["hypothesis_id"],
                        "control_hypothesis_id": control["hypothesis_id"],
                        "window_id": primary["window_id"],
                        "run_id": RUN_ID,
                        "source_sar_frame": primary["source_sar_frame"],
                        "destination_sar_frame": primary["destination_sar_frame"],
                        "raw_track_fragment_id": primary["raw_track_fragment_id"],
                        "source_region_id": primary["source_region_id"],
                        "primary_destination_region_id": primary["destination_region_id"],
                        "control_destination_region_id": control["destination_region_id"],
                        "control_rank": rank,
                        "boundary_mismatch": vector[0],
                        "truncation_mismatch": vector[1],
                        "region_degree_difference": vector[2],
                        "log_area_difference": vector[3],
                        "theta_width_difference_deg": vector[4],
                        "theta_mid_difference_deg": vector[5],
                        "selection_used_reference": False,
                        "selection_used_cmr_outcome": False,
                    }
                )
    return pd.DataFrame(rows)


def tendency(state: str, midpoint: float) -> str:
    if "ABOVE_COMMON" in state:
        return "DEFINITE_POSITIVE"
    if "BELOW_COMMON" in state:
        return "DEFINITE_NEGATIVE"
    if not np.isfinite(midpoint):
        return "SIGN_UNAVAILABLE"
    if midpoint > 0:
        return "POSITIVE_LEANING_UNRESOLVED"
    if midpoint < 0:
        return "NEGATIVE_LEANING_UNRESOLVED"
    return "NEAR_COMMON_SIGN_UNRESOLVED"


def tendency_sign(value: str) -> int:
    if "POSITIVE" in value:
        return 1
    if "NEGATIVE" in value:
        return -1
    return 0


def add_confirmation_diagnostics(cross: pd.DataFrame) -> pd.DataFrame:
    frame = cross.copy()
    frame["optical_tendency_state"] = [
        tendency(str(state), float(mid) if pd.notna(mid) else math.nan)
        for state, mid in zip(frame["optical_residual_state"], frame["residual_mid_descriptor_deg"])
    ]
    frame["sar_tendency_state"] = [
        tendency(str(state), float(mid) if pd.notna(mid) else math.nan)
        for state, mid in zip(frame["sar_p0_residual_state"], frame["sar_residual_mid_descriptor_deg"])
    ]
    leaning = []
    for optical_state, sar_state in zip(frame["optical_tendency_state"], frame["sar_tendency_state"]):
        optical_sign = tendency_sign(str(optical_state))
        sar_sign = tendency_sign(str(sar_state))
        if optical_sign == 0 or sar_sign == 0:
            leaning.append("LEANING_RELATION_UNRESOLVED")
        elif optical_sign == sar_sign:
            leaning.append("LEANING_RELATION_SUPPORTIVE")
        else:
            leaning.append("LEANING_RELATION_OPPOSING")
    frame["cross_modal_leaning_relation"] = leaning
    frame["confirmation_diagnostic_only"] = True
    return frame


def pre_reference_phase() -> None:
    protocol = verify_protocol_freeze()
    if REVEAL_MARKER.exists():
        raise RuntimeError("reference already revealed; pre-reference mechanism cannot run")
    if PRE_MANIFEST.exists():
        raise RuntimeError("pre-reference outputs are already frozen; one-shot rerun refused")
    dev = load_dev()
    data = dev.load_authorities()
    atlas = r04_atlas()

    PRE.mkdir(parents=True, exist_ok=True)
    static = add_structural_fields(enumerate_static_hypotheses(atlas, data), data)
    controls = build_control_bank(static)
    static.to_parquet(PRE / "r04_static_hypothesis_bank_pre_reference.parquet", index=False, compression="zstd")
    controls.to_parquet(PRE / "r04_structurally_matched_control_bank_pre_reference.parquet", index=False, compression="zstd")
    controls.to_csv(PRE / "r04_structurally_matched_control_bank_pre_reference.csv", index=False, encoding="utf-8-sig")
    forbidden = {
        "target_id",
        "physical_target_id",
        "reference_supported",
        "cross_modal_residual_relation",
        "soft_iou",
        "source_total_retention",
        "destination_explained_fraction",
    }
    present = sorted(forbidden & set(controls.columns))
    if present:
        raise RuntimeError(f"control bank contains forbidden fields: {present}")
    control_payload = {
        "schema": "PERSON_CMR_V0_R04_CONTROL_BANK_FREEZE_V1",
        "status": "FROZEN_BEFORE_CMR_MECHANISM_OUTPUT_AND_REFERENCE_REVEAL",
        "created_at": now_iso(),
        "reference_loaded": False,
        "cmr_outcome_used": False,
        "static_hypothesis_count": len(static),
        "control_pair_count": len(controls),
        "control_count_per_primary_max": CONTROL_COUNT,
        "static_bank_sha256": sha256_file(PRE / "r04_static_hypothesis_bank_pre_reference.parquet"),
        "control_bank_sha256": sha256_file(PRE / "r04_structurally_matched_control_bank_pre_reference.parquet"),
        "selection_fields": [
            "destination_boundary",
            "destination_truncated",
            "destination_region_degree",
            "destination_pixel_count",
            "destination_theta_width_deg",
            "destination_theta_mid_deg",
            "hypothesis_id",
        ],
    }
    write_json(CONTROL_FREEZE, control_payload)

    execution_atlas = atlas.copy()
    execution_atlas["pool"] = "DEVELOPMENT_POOL"
    MECHANISM.mkdir(parents=True, exist_ok=True)
    dev.OUTPUT = MECHANISM
    common, optical = dev.develop_optical_common_and_residual(execution_atlas, data)
    hypotheses = dev.build_static_hypotheses(execution_atlas, data, optical)
    if set(hypotheses["hypothesis_id"]) != set(static["hypothesis_id"]):
        raise RuntimeError("frozen mechanism hypothesis enumeration differs from frozen control bank")
    sar = dev.develop_sar_p0_residual(hypotheses, data)
    cross = dev.develop_cross_modal(hypotheses, sar)
    profiles = add_confirmation_diagnostics(cross)
    profiles.to_parquet(PRE / "r04_cmr_v0_evidence_profiles_pre_reference.parquet", index=False, compression="zstd")
    profiles[
        [
            "window_id",
            "raw_track_fragment_id",
            "hypothesis_id",
            "optical_residual_state",
            "optical_tendency_state",
            "sar_p0_residual_state",
            "sar_tendency_state",
            "cross_modal_residual_relation",
            "cross_modal_leaning_relation",
        ]
    ].to_csv(PRE / "r04_cmr_v0_evidence_state_index_pre_reference.csv", index=False, encoding="utf-8-sig")
    window_summary = (
        profiles.groupby("window_id")
        .agg(
            run_id=("run_id", "first"),
            source_sar_frame=("source_sar_frame", "first"),
            destination_sar_frame=("destination_sar_frame", "first"),
            branch_count=("raw_track_fragment_id", "nunique"),
            hypothesis_count=("hypothesis_id", "nunique"),
            optical_state_count=("optical_residual_state", "nunique"),
            sar_state_count=("sar_p0_residual_state", "nunique"),
            relation_state_count=("cross_modal_residual_relation", "nunique"),
        )
        .reset_index()
    )
    window_summary.to_csv(PRE / "r04_pre_reference_observability_by_window.csv", index=False, encoding="utf-8-sig")

    files = [path for path in PRE.rglob("*") if path.is_file() and path != PRE_MANIFEST]
    manifest = {
        "schema": "PERSON_CMR_V0_R04_PRE_REFERENCE_FREEZE_V1",
        "status": "R04_PRE_REFERENCE_CMR_OUTPUTS_HASH_FROZEN",
        "created_at": now_iso(),
        "protocol_freeze_sha256": sha256_file(PROTOCOL_FREEZE),
        "control_freeze_sha256": sha256_file(CONTROL_FREEZE),
        "reference_loaded": False,
        "outcome_accessed": False,
        "mechanism_modified": False,
        "frozen_mechanism_runner_sha256": sha256_file(DEV_RUNNER),
        "eligible_windows": len(atlas),
        "eligible_branch_instances": int(atlas["runtime_common_fragment_count"].sum()),
        "common_window_count": len(common),
        "optical_branch_count": len(optical),
        "sar_unique_edge_count": len(sar),
        "cross_modal_hypothesis_count": len(cross),
        "files": [
            {"path": str(path.relative_to(WORKSPACE)), "bytes": path.stat().st_size, "sha256": sha256_file(path)}
            for path in sorted(files)
        ],
        "execution_order": [
            "PROTOCOL_AND_EVALUATOR_HASH_VERIFIED",
            "STATIC_HYPOTHESES_ENUMERATED_WITHOUT_REFERENCE",
            "MATCHED_CONTROLS_FROZEN_WITHOUT_CMR_OUTCOME",
            "FROZEN_CMR_V0_EXECUTED_ON_R04",
            "CONTINUOUS_AND_CATEGORICAL_PROFILES_MATERIALIZED",
            "REFERENCE_NOT_LOADED_PRE_REFERENCE_PHASE_CLOSED",
        ],
        "protocol_record": protocol["files"],
    }
    write_json(PRE_MANIFEST, manifest)


def verify_pre_reference_freeze() -> dict[str, Any]:
    verify_protocol_freeze()
    if not PRE_MANIFEST.exists():
        raise RuntimeError("pre-reference output freeze is missing")
    manifest = json.loads(PRE_MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("status") != "R04_PRE_REFERENCE_CMR_OUTPUTS_HASH_FROZEN":
        raise RuntimeError("invalid pre-reference freeze status")
    for item in manifest["files"]:
        path = WORKSPACE / item["path"]
        if not path.exists() or path.stat().st_size != int(item["bytes"]) or sha256_file(path) != item["sha256"]:
            raise RuntimeError(f"pre-reference output changed: {path}")
    return manifest


def strict_relation_level(state: str) -> str:
    if state == "RESIDUAL_DIRECTION_CONCORDANT":
        return "SUPPORTIVE"
    if state == "RESIDUAL_DIRECTION_CONTRADICTORY":
        return "OPPOSING"
    return "UNRESOLVED"


def leaning_level(state: str) -> str:
    if state == "LEANING_RELATION_SUPPORTIVE":
        return "SUPPORTIVE"
    if state == "LEANING_RELATION_OPPOSING":
        return "OPPOSING"
    return "UNRESOLVED"


def scene_common_preference(primary: pd.Series, control: pd.Series) -> str:
    columns = ["soft_iou", "source_total_retention", "destination_explained_fraction"]
    p = np.asarray([float(primary[column]) for column in columns], dtype=float)
    c = np.asarray([float(control[column]) for column in columns], dtype=float)
    if not np.isfinite(p).all() or not np.isfinite(c).all():
        return "SCENE_COMMON_NO_PREFERENCE"
    primary_dominates = bool(np.all(p >= c - NUMERICAL_TOL) and np.any(p > c + NUMERICAL_TOL))
    control_dominates = bool(np.all(c >= p - NUMERICAL_TOL) and np.any(c > p + NUMERICAL_TOL))
    if primary_dominates:
        return "SCENE_COMMON_PRIMARY_PREFERRED"
    if control_dominates:
        return "SCENE_COMMON_CONTROL_PREFERRED"
    return "SCENE_COMMON_NO_PREFERENCE"


def candidate_separation(primary: pd.Series, control: pd.Series) -> str:
    order = {"OPPOSING": -1, "UNRESOLVED": 0, "SUPPORTIVE": 1}
    p_strict = strict_relation_level(str(primary.cross_modal_residual_relation))
    c_strict = strict_relation_level(str(control.cross_modal_residual_relation))
    strict_difference = order[p_strict] - order[c_strict]
    if strict_difference == 2:
        return "STRONG_SEPARATION"
    if strict_difference == 1:
        return "ASYMMETRIC_SEPARATION"
    if strict_difference < 0:
        return "REVERSED_SEPARATION"
    p_lean = leaning_level(str(primary.cross_modal_leaning_relation))
    c_lean = leaning_level(str(control.cross_modal_leaning_relation))
    leaning_difference = order[p_lean] - order[c_lean]
    if leaning_difference > 0:
        return "TENDENCY_SEPARATION"
    if leaning_difference < 0:
        return "REVERSED_SEPARATION"
    return "NO_SEPARATION"


def strict_outcome(scene: str, separation: str) -> str:
    if separation == "STRONG_SEPARATION":
        if scene in {"SCENE_COMMON_NO_PREFERENCE", "SCENE_COMMON_CONTROL_PREFERRED"}:
            return "SAR_EDGE_RESCUE"
        return "CONFIRMATION"
    if separation == "REVERSED_SEPARATION":
        return "HARM"
    if scene == "SCENE_COMMON_PRIMARY_PREFERRED":
        return "CONFIRMATION"
    if scene == "SCENE_COMMON_CONTROL_PREFERRED" and separation == "ASYMMETRIC_SEPARATION":
        return "CONFLICT"
    if scene == "SCENE_COMMON_CONTROL_PREFERRED":
        return "HARM"
    return "NO_INFORMATION"


def reference_maps(dev: Any) -> tuple[dict[tuple[str, str], str], pd.DataFrame, pd.DataFrame, dict[str, str]]:
    reference_path = dev.REGION_ROOT / "offline_reference_response_region_evaluation.csv"
    center_path = (
        dev.STUDY
        / "p1e_sar_only_response_interface"
        / "candidate_recall_semantic_split_v1"
        / "single_frame_candidate_recall"
        / "manual_reference_candidate_interpretation_v2.csv"
    )
    assignment_path = dev.OFFLINE_ASSIGNMENT
    references = pd.read_csv(reference_path)
    near = bool_series(references["region_near_reference_0p30m"])
    references = references[
        references["run_id"].eq(RUN_ID)
        & references["percentile_tag"].eq("Q095")
        & near
        & references["nearest_region_id"].notna()
    ].copy()
    mapping = {
        (str(row.frame_uid), str(row.target_id)): str(row.nearest_region_id)
        for row in references.itertuples(index=False)
    }
    centers = pd.read_csv(center_path)
    centers = centers[centers["run_id"].eq(RUN_ID)].copy()
    assignments = pd.read_csv(assignment_path)
    assignments = assignments[
        assignments["run_id"].eq(RUN_ID)
        & assignments["interface_kind"].eq("RAW_DETECTED_FRAGMENT_ALL")
        & (pd.to_numeric(assignments["time_window_half_width_ms"], errors="coerce") == 0)
        & assignments["assigned_track_id_offline"].notna()
    ].copy()
    hashes = {
        "reference_region_evaluation": sha256_file(reference_path),
        "manual_reference_centers": sha256_file(center_path),
        "offline_branch_assignment": sha256_file(assignment_path),
    }
    return mapping, centers, assignments, hashes


def supported_edge_map(atlas: pd.DataFrame, mapping: dict[tuple[str, str], str]) -> dict[tuple[int, int, str, str], list[str]]:
    result: dict[tuple[int, int, str, str], list[str]] = {}
    for window in atlas.itertuples(index=False):
        source_uid = f"{RUN_ID}_SARF{int(window.source_sar_frame):06d}"
        destination_uid = f"{RUN_ID}_SARF{int(window.destination_sar_frame):06d}"
        source_targets = {target: region for (uid, target), region in mapping.items() if uid == source_uid}
        destination_targets = {target: region for (uid, target), region in mapping.items() if uid == destination_uid}
        for target in sorted(set(source_targets) & set(destination_targets)):
            key = (
                int(window.source_sar_frame),
                int(window.destination_sar_frame),
                source_targets[target],
                destination_targets[target],
            )
            result.setdefault(key, []).append(target)
    return result


def branch_grounding_state(
    assignments: pd.DataFrame,
    fragment: str,
    target: str,
    source_frame: int,
    destination_frame: int,
) -> str:
    subset = assignments[
        assignments["assigned_track_id_offline"].astype(str).eq(fragment)
        & pd.to_numeric(assignments["frame_index"], errors="coerce").isin([source_frame, destination_frame])
    ]
    if subset.empty:
        return "UNRESOLVED_NO_OFFLINE_ASSIGNMENT"
    by_frame = {
        int(frame): set(group["target_id"].astype(str))
        for frame, group in subset.groupby(pd.to_numeric(subset["frame_index"], errors="coerce").astype(int))
    }
    source_targets = by_frame.get(source_frame, set())
    destination_targets = by_frame.get(destination_frame, set())
    if target in source_targets and target in destination_targets:
        return "LIKELY_PAIR_CONSISTENT_OFFLINE"
    if target in source_targets or target in destination_targets:
        return "LIKELY_SINGLE_ENDPOINT_OFFLINE"
    if source_targets or destination_targets:
        return "UNRESOLVED_CONFLICTING_OFFLINE_ASSIGNMENT"
    return "UNRESOLVED_NO_OFFLINE_ASSIGNMENT"


def merge_profile_rows(controls: pd.DataFrame, profiles: pd.DataFrame) -> pd.DataFrame:
    primary = profiles.add_prefix("primary_")
    control = profiles.add_prefix("control_")
    frame = controls.merge(
        primary,
        left_on="primary_hypothesis_id",
        right_on="primary_hypothesis_id",
        how="left",
        validate="many_to_one",
    )
    frame = frame.merge(
        control,
        left_on="control_hypothesis_id",
        right_on="control_hypothesis_id",
        how="left",
        validate="many_to_one",
    )
    return frame


def render_pair_case(
    case_name: str,
    evaluation: pd.Series,
    profiles: pd.DataFrame,
    common: pd.DataFrame,
    data: dict[str, Any],
    dev: Any,
    output: Path,
) -> None:
    primary = profiles[profiles["hypothesis_id"].eq(str(evaluation.primary_hypothesis_id))].iloc[0]
    control = profiles[profiles["hypothesis_id"].eq(str(evaluation.control_hypothesis_id))].iloc[0]
    temp_dir = POST / "figures" / "_temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    dev.OUTPUT = temp_dir
    primary_path = temp_dir / f"{case_name}_primary.png"
    control_path = temp_dir / f"{case_name}_control.png"
    optical = data["optical"]
    dev.render_cross_modal_case(primary, optical, common, data, primary_path)
    dev.render_cross_modal_case(control, optical, common, data, control_path)
    if not primary_path.exists() or not control_path.exists():
        return
    images = [Image.open(primary_path).convert("RGB"), Image.open(control_path).convert("RGB")]
    resized = []
    for image in images:
        width = 1050
        ratio = width / image.width
        resized.append(image.resize((width, int(image.height * ratio))))
    header_height = 180
    canvas = Image.new("RGB", (sum(image.width for image in resized), header_height + max(image.height for image in resized)), "white")
    draw = ImageDraw.Draw(canvas)
    header = (
        f"{case_name} | target={evaluation.supported_target_id} | separation={evaluation.candidate_separation} | "
        f"strict={evaluation.strict_outcome} | scene={evaluation.scene_common_preference}\n"
        f"PRIMARY reference-supported: {evaluation.primary_hypothesis_id} | CONTROL reference-unsupported: {evaluation.control_hypothesis_id}\n"
        f"grounding={evaluation.branch_grounding_state} | primary relation={evaluation.primary_cross_modal_residual_relation} | "
        f"control relation={evaluation.control_cross_modal_residual_relation}"
    )
    draw.multiline_text((15, 15), header, fill="black", spacing=7)
    x = 0
    for image in resized:
        canvas.paste(image, (x, header_height))
        x += image.width
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output)
    primary_path.unlink(missing_ok=True)
    control_path.unlink(missing_ok=True)


def select_visual_cases(evaluation: pd.DataFrame) -> list[tuple[str, pd.DataFrame, list[str], list[bool]]]:
    p_rel = evaluation["primary_cross_modal_residual_relation"]
    c_rel = evaluation["control_cross_modal_residual_relation"]
    p_sar = evaluation["primary_sar_p0_residual_state"]
    c_sar = evaluation["control_sar_p0_residual_state"]
    p_opt = evaluation["primary_optical_residual_state"]
    rules = [
        ("01_sar_only_ambiguous_cmr_separates", evaluation[evaluation["candidate_separation"].isin(["STRONG_SEPARATION", "ASYMMETRIC_SEPARATION"])]),
        ("02_scene_common_wrong_cmr_rescues", evaluation[(evaluation["scene_common_preference"] == "SCENE_COMMON_CONTROL_PREFERRED") & (evaluation["strict_outcome"] == "SAR_EDGE_RESCUE")]),
        ("03_scene_common_correct_cmr_confirms", evaluation[(evaluation["scene_common_preference"] == "SCENE_COMMON_PRIMARY_PREFERRED") & (evaluation["strict_outcome"] == "CONFIRMATION")]),
        ("04_scene_common_correct_cmr_conflicts", evaluation[(evaluation["scene_common_preference"] == "SCENE_COMMON_PRIMARY_PREFERRED") & evaluation["strict_outcome"].isin(["HARM", "CONFLICT"])]),
        ("05_concordant_high_overlap_wrong_alternative", evaluation[c_rel == "RESIDUAL_DIRECTION_CONCORDANT"]),
        ("06_contradictory_high_overlap_wrong_alternative", evaluation[c_rel == "RESIDUAL_DIRECTION_CONTRADICTORY"]),
        ("07_weak_unresolved_visually_plausible", evaluation[c_rel == "RESIDUAL_RELATION_WEAK_OR_UNRESOLVED"]),
        ("08_deformation_case", evaluation[p_sar.str.contains("DEFORMATION") | c_sar.str.contains("DEFORMATION") | p_opt.str.contains("DEFORMATION")]),
        ("09_boundary_censored_case", evaluation[p_sar.str.contains("BOUNDARY_CENSORED") | c_sar.str.contains("BOUNDARY_CENSORED")]),
        ("10_large_common_estimator_uncertainty", evaluation),
        ("11_optical_strong_sar_weak", evaluation[p_opt.isin(["OPTICAL_RESIDUAL_ABOVE_COMMON", "OPTICAL_RESIDUAL_BELOW_COMMON"]) & p_sar.eq("SAR_P0_RESIDUAL_COMMON_COMPATIBLE")]),
        ("12_sar_clear_optical_uncertain", evaluation[p_sar.isin(["SAR_P0_RESIDUAL_ABOVE_COMMON", "SAR_P0_RESIDUAL_BELOW_COMMON"]) & ~p_opt.isin(["OPTICAL_RESIDUAL_ABOVE_COMMON", "OPTICAL_RESIDUAL_BELOW_COMMON"])]),
        ("13_likely_grounded_branch", evaluation[evaluation["branch_grounding_state"].str.startswith("LIKELY")]),
        ("14_unresolved_grounding_branch", evaluation[evaluation["branch_grounding_state"].str.startswith("UNRESOLVED")]),
        ("15_best_apparent_candidate_separation", evaluation[evaluation["candidate_separation"] == "STRONG_SEPARATION"]),
        ("16_worst_apparent_cmr_harm", evaluation[evaluation["strict_outcome"] == "HARM"]),
    ]
    return [(name, frame, ["visual_priority", "primary_soft_iou", "control_soft_iou", "pair_evaluation_id"], [True, False, False, True]) for name, frame in rules]


def post_reference_phase() -> None:
    pre_manifest = verify_pre_reference_freeze()
    if FINAL_SUMMARY.exists():
        raise RuntimeError("post-reference confirmation already completed; one-shot rerun refused")
    dev = load_dev()
    POST.mkdir(parents=True, exist_ok=True)
    write_json(
        REVEAL_MARKER,
        {
            "schema": "PERSON_CMR_V0_R04_REFERENCE_REVEAL_MARKER_V1",
            "status": "REFERENCE_REVEAL_STARTED_AFTER_PRE_REFERENCE_HASH_FREEZE",
            "created_at": now_iso(),
            "pre_reference_manifest_sha256": sha256_file(PRE_MANIFEST),
            "mechanism_modified_after_pre_reference": False,
        },
    )

    mapping, centers, assignments, reference_hashes = reference_maps(dev)
    atlas = r04_atlas()
    supported_map = supported_edge_map(atlas, mapping)
    profiles = pd.read_parquet(PRE / "r04_cmr_v0_evidence_profiles_pre_reference.parquet")
    controls = pd.read_parquet(PRE / "r04_structurally_matched_control_bank_pre_reference.parquet")
    merged = merge_profile_rows(controls, profiles)

    profile_index = profiles.set_index("hypothesis_id", drop=False)
    supported_by_hypothesis: dict[str, list[str]] = {}
    for row in profiles.itertuples(index=False):
        key = (int(row.source_sar_frame), int(row.destination_sar_frame), str(row.source_region_id), str(row.destination_region_id))
        if key in supported_map:
            supported_by_hypothesis[str(row.hypothesis_id)] = sorted(supported_map[key])

    evaluation_rows: list[dict[str, Any]] = []
    for control_row in merged.itertuples(index=False):
        primary_id = str(control_row.primary_hypothesis_id)
        if primary_id not in supported_by_hypothesis:
            continue
        control_id = str(control_row.control_hypothesis_id)
        control_targets = supported_by_hypothesis.get(control_id, [])
        if control_targets:
            continue
        primary = profile_index.loc[primary_id]
        control = profile_index.loc[control_id]
        for target in supported_by_hypothesis[primary_id]:
            scene = scene_common_preference(primary, control)
            separation = candidate_separation(primary, control)
            outcome = strict_outcome(scene, separation)
            grounding = branch_grounding_state(
                assignments,
                str(primary.raw_track_fragment_id),
                target,
                int(primary.source_sar_frame),
                int(primary.destination_sar_frame),
            )
            visual_priority = {
                "STRONG_SEPARATION": 0,
                "ASYMMETRIC_SEPARATION": 1,
                "TENDENCY_SEPARATION": 2,
                "REVERSED_SEPARATION": 3,
                "NO_SEPARATION": 4,
            }[separation]
            evaluation_rows.append(
                {
                    "pair_evaluation_id": stable_id("CMRE", primary_id, control_id, target),
                    "control_pair_id": str(control_row.control_pair_id),
                    "window_id": str(primary.window_id),
                    "run_id": RUN_ID,
                    "source_sar_frame": int(primary.source_sar_frame),
                    "destination_sar_frame": int(primary.destination_sar_frame),
                    "temporal_block_id": f"R04_BLOCK_{int(primary.source_sar_frame) // TEMPORAL_BLOCK_SIZE:02d}",
                    "raw_track_fragment_id": str(primary.raw_track_fragment_id),
                    "supported_target_id": target,
                    "primary_hypothesis_id": primary_id,
                    "control_hypothesis_id": control_id,
                    "primary_source_region_id": str(primary.source_region_id),
                    "primary_destination_region_id": str(primary.destination_region_id),
                    "control_destination_region_id": str(control.destination_region_id),
                    "sar_only_preference": "SAR_ONLY_NO_PREFERENCE_STATIC_FEASIBLE",
                    "scene_common_preference": scene,
                    "candidate_separation": separation,
                    "strict_outcome": outcome,
                    "primary_strict_relation_level": strict_relation_level(str(primary.cross_modal_residual_relation)),
                    "control_strict_relation_level": strict_relation_level(str(control.cross_modal_residual_relation)),
                    "primary_leaning_level": leaning_level(str(primary.cross_modal_leaning_relation)),
                    "control_leaning_level": leaning_level(str(control.cross_modal_leaning_relation)),
                    "branch_grounding_state": grounding,
                    "strict_branch_specific_evaluation": "STRICT_BRANCH_SPECIFIC_EVALUATION_UNAVAILABLE",
                    "primary_optical_residual_state": str(primary.optical_residual_state),
                    "control_optical_residual_state": str(control.optical_residual_state),
                    "primary_sar_p0_residual_state": str(primary.sar_p0_residual_state),
                    "control_sar_p0_residual_state": str(control.sar_p0_residual_state),
                    "primary_cross_modal_residual_relation": str(primary.cross_modal_residual_relation),
                    "control_cross_modal_residual_relation": str(control.cross_modal_residual_relation),
                    "primary_optical_mid_residual_deg": float(primary.residual_mid_descriptor_deg),
                    "control_optical_mid_residual_deg": float(control.residual_mid_descriptor_deg),
                    "primary_sar_mid_residual_deg": float(primary.sar_residual_mid_descriptor_deg),
                    "control_sar_mid_residual_deg": float(control.sar_residual_mid_descriptor_deg),
                    "primary_common_uncertainty_deg": float(primary.common_uncertainty_deg),
                    "control_common_uncertainty_deg": float(control.common_uncertainty_deg),
                    "primary_p0_uncertainty_deg": float(primary.p0_angular_uncertainty_deg),
                    "control_p0_uncertainty_deg": float(control.p0_angular_uncertainty_deg),
                    "primary_soft_iou": float(primary.soft_iou),
                    "control_soft_iou": float(control.soft_iou),
                    "primary_source_retention": float(primary.source_total_retention),
                    "control_source_retention": float(control.source_total_retention),
                    "primary_destination_explained": float(primary.destination_explained_fraction),
                    "control_destination_explained": float(control.destination_explained_fraction),
                    "primary_topology_state": str(primary.sar_topology_state),
                    "control_topology_state": str(control.sar_topology_state),
                    "visual_priority": visual_priority,
                    "reference_used_for_evaluation": True,
                    "mechanism_recomputed_after_reveal": False,
                }
            )
    evaluation = pd.DataFrame(evaluation_rows)
    evaluation.to_parquet(POST / "r04_supported_vs_matched_wrong_pairwise_evaluation.parquet", index=False, compression="zstd")
    evaluation.to_csv(POST / "r04_supported_vs_matched_wrong_pairwise_evaluation.csv", index=False, encoding="utf-8-sig")

    supported_edges = []
    for key, targets in supported_map.items():
        supported_edges.append(
            {
                "run_id": RUN_ID,
                "source_sar_frame": key[0],
                "destination_sar_frame": key[1],
                "source_region_id": key[2],
                "destination_region_id": key[3],
                "supported_target_ids": ";".join(sorted(targets)),
                "supported_target_count": len(targets),
                "shared_or_unresolved": len(targets) > 1,
            }
        )
    pd.DataFrame(supported_edges).to_csv(POST / "r04_reference_supported_sar_edges.csv", index=False, encoding="utf-8-sig")

    # Reference-free structurally matched controls: neither endpoint becomes supported.
    unsupported = merged[
        ~merged["primary_hypothesis_id"].isin(supported_by_hypothesis)
        & ~merged["control_hypothesis_id"].isin(supported_by_hypothesis)
    ].copy()
    unsupported["strict_profile_different"] = (
        unsupported["primary_cross_modal_residual_relation"] != unsupported["control_cross_modal_residual_relation"]
    )
    unsupported["leaning_profile_different"] = (
        unsupported["primary_cross_modal_leaning_relation"] != unsupported["control_cross_modal_leaning_relation"]
    )
    unsupported.to_parquet(POST / "r04_reference_free_structurally_matched_controls.parquet", index=False, compression="zstd")

    separation_counts = evaluation["candidate_separation"].value_counts().to_dict()
    strict_counts = evaluation["strict_outcome"].value_counts().to_dict()
    window_separation = (
        evaluation.groupby("window_id")
        .agg(
            source_sar_frame=("source_sar_frame", "first"),
            destination_sar_frame=("destination_sar_frame", "first"),
            target_count=("supported_target_id", "nunique"),
            pair_count=("pair_evaluation_id", "size"),
            strong=("candidate_separation", lambda values: int((values == "STRONG_SEPARATION").sum())),
            asymmetric=("candidate_separation", lambda values: int((values == "ASYMMETRIC_SEPARATION").sum())),
            tendency=("candidate_separation", lambda values: int((values == "TENDENCY_SEPARATION").sum())),
            reversed=("candidate_separation", lambda values: int((values == "REVERSED_SEPARATION").sum())),
        )
        .reset_index()
    )
    window_separation["has_candidate_separation"] = (window_separation[["strong", "asymmetric", "tendency"]].sum(axis=1) > 0)
    window_separation.to_csv(POST / "r04_candidate_separation_by_window.csv", index=False, encoding="utf-8-sig")

    cluster_summary = (
        evaluation.groupby(["temporal_block_id", "supported_target_id"])
        .agg(
            windows=("window_id", "nunique"),
            branches=("raw_track_fragment_id", "nunique"),
            comparisons=("pair_evaluation_id", "size"),
            separation_pairs=("candidate_separation", lambda values: int(values.isin(["STRONG_SEPARATION", "ASYMMETRIC_SEPARATION", "TENDENCY_SEPARATION"]).sum())),
            rescue=("strict_outcome", lambda values: int((values == "SAR_EDGE_RESCUE").sum())),
            harm=("strict_outcome", lambda values: int((values == "HARM").sum())),
        )
        .reset_index()
    )
    cluster_summary.to_csv(POST / "r04_cluster_aware_summary.csv", index=False, encoding="utf-8-sig")

    likely = evaluation[evaluation["branch_grounding_state"].str.startswith("LIKELY")].copy()
    unresolved = evaluation[evaluation["branch_grounding_state"].str.startswith("UNRESOLVED")].copy()
    likely.to_csv(POST / "r04_offline_likely_supported_branch_evaluation.csv", index=False, encoding="utf-8-sig")
    unresolved.to_csv(POST / "r04_unresolved_branch_evidence_profiles.csv", index=False, encoding="utf-8-sig")

    leave_one_out = {
        "by_target": {
            target: {
                "remaining_comparisons": int(len(evaluation[evaluation["supported_target_id"] != target])),
                "remaining_separation_counts": evaluation[evaluation["supported_target_id"] != target]["candidate_separation"].value_counts().to_dict(),
                "remaining_strict_outcomes": evaluation[evaluation["supported_target_id"] != target]["strict_outcome"].value_counts().to_dict(),
            }
            for target in sorted(evaluation["supported_target_id"].unique())
        },
        "by_temporal_block": {
            block: {
                "remaining_comparisons": int(len(evaluation[evaluation["temporal_block_id"] != block])),
                "remaining_separation_counts": evaluation[evaluation["temporal_block_id"] != block]["candidate_separation"].value_counts().to_dict(),
                "remaining_strict_outcomes": evaluation[evaluation["temporal_block_id"] != block]["strict_outcome"].value_counts().to_dict(),
            }
            for block in sorted(evaluation["temporal_block_id"].unique())
        },
    }
    write_json(POST / "r04_leave_one_cluster_out_descriptive.json", leave_one_out)

    common = pd.read_parquet(MECHANISM / "optical_common_motion_development.parquet")
    data = dev.load_authorities()
    case_rows = []
    FIGURES.mkdir(parents=True, exist_ok=True)
    for case_name, candidates, sort_columns, ascending in select_visual_cases(evaluation):
        if candidates.empty:
            case_rows.append({"case_name": case_name, "status": "CATEGORY_NOT_OBSERVED", "path": ""})
            continue
        row = candidates.sort_values(sort_columns, ascending=ascending).iloc[0]
        path = FIGURES / f"{case_name}.png"
        render_pair_case(case_name, row, profiles, common, data, dev, path)
        status = "OBSERVED" if path.exists() else "RENDER_FAILED"
        case_rows.append(
            {
                "case_name": case_name,
                "status": status,
                "path": str(path.relative_to(WORKSPACE)) if path.exists() else "",
                "pair_evaluation_id": row.pair_evaluation_id,
                "window_id": row.window_id,
                "supported_target_id": row.supported_target_id,
                "candidate_separation": row.candidate_separation,
                "strict_outcome": row.strict_outcome,
            }
        )
    case_registry = pd.DataFrame(case_rows)
    case_registry.to_csv(POST / "r04_visual_case_registry.csv", index=False, encoding="utf-8-sig")
    images = [Image.open(WORKSPACE / path).convert("RGB") for path in case_registry.loc[case_registry["status"] == "OBSERVED", "path"]]
    if images:
        width = 1200
        thumbs = []
        for image in images:
            ratio = width / image.width
            thumbs.append(image.resize((width, max(1, int(image.height * ratio)))))
        sheet = Image.new("RGB", (width, sum(image.height for image in thumbs)), "white")
        y = 0
        for image in thumbs:
            sheet.paste(image, (0, y))
            y += image.height
        sheet.save(POST / "R04_CONFIRMATION_CASE_CONTACT_SHEET.jpg", quality=88)

    scene_counts = evaluation["scene_common_preference"].value_counts().to_dict()
    grounding_counts = evaluation["branch_grounding_state"].value_counts().to_dict()
    summary = {
        "schema": "PERSON_CMR_V0_R04_CONFIRMATION_SUMMARY_V1",
        "created_at": now_iso(),
        "run_id": RUN_ID,
        "stage": "CMR_V0_R04_INDEPENDENT_CONFIRMATION",
        "one_shot_confirmation": True,
        "mechanism_modified_after_reveal": False,
        "eligible_windows": pre_manifest["eligible_windows"],
        "eligible_branch_instances": pre_manifest["eligible_branch_instances"],
        "common_window_count": pre_manifest["common_window_count"],
        "optical_branch_count": pre_manifest["optical_branch_count"],
        "sar_unique_edge_count": pre_manifest["sar_unique_edge_count"],
        "cross_modal_hypothesis_count": pre_manifest["cross_modal_hypothesis_count"],
        "reference_supported_sar_edge_count": len(supported_map),
        "supported_vs_matched_wrong_comparison_count": len(evaluation),
        "windows_with_candidate_separation": int(window_separation["has_candidate_separation"].sum()),
        "candidate_separation_counts": separation_counts,
        "strict_outcome_counts": strict_counts,
        "scene_common_preference_counts": scene_counts,
        "grounding_counts": grounding_counts,
        "strict_branch_specific_evaluation": "STRICT_BRANCH_SPECIFIC_EVALUATION_UNAVAILABLE",
        "likely_supported_exploratory_comparison_count": len(likely),
        "unresolved_grounding_comparison_count": len(unresolved),
        "reference_free_control_pair_count": len(unsupported),
        "reference_free_strict_profile_difference_fraction": float(unsupported["strict_profile_different"].mean()) if len(unsupported) else None,
        "reference_free_leaning_profile_difference_fraction": float(unsupported["leaning_profile_different"].mean()) if len(unsupported) else None,
        "strict_unresolved_but_tendency_count": int((evaluation["candidate_separation"] == "TENDENCY_SEPARATION").sum()),
        "visual_cases_observed": int((case_registry["status"] == "OBSERVED").sum()),
        "visual_cases_not_observed": int((case_registry["status"] == "CATEGORY_NOT_OBSERVED").sum()),
        "visual_review_status": "PENDING_DIRECT_HUMAN_MULTIMODAL_REVIEW_LEDGER",
        "reference_hashes": reference_hashes,
        "prohibited_outputs": {
            "weighted_score": False,
            "pruning": False,
            "identity_assignment": False,
            "tracker": False,
            "factor_graph": False,
            "p2": False,
            "final_sar_center": False,
            "final_sar_box": False,
        },
    }
    write_json(FINAL_SUMMARY, summary)

    report = f"""# CMR-v0 R04 independent confirmation report

- Run: `R04ZF`, one held-out run.
- Mechanism changed after reveal: `NO`.
- Eligible windows / branches: `{summary['eligible_windows']} / {summary['eligible_branch_instances']}`.
- Reference-supported SAR edges: `{summary['reference_supported_sar_edge_count']}`.
- Supported-vs-matched-wrong comparisons: `{len(evaluation)}`.

## Observability

CMR produced `{summary['common_window_count']}` common-motion windows, `{summary['optical_branch_count']}` optical branch residuals, `{summary['sar_unique_edge_count']}` unique SAR P0-relative edges, and `{summary['cross_modal_hypothesis_count']}` cross-modal evidence profiles.  Weak, deformation, censored, ambiguous, and high-uncertainty observations remain represented.

## Candidate separation

- Windows with at least one strong/asymmetric/tendency separation: `{summary['windows_with_candidate_separation']}`.
- Pair counts: `{separation_counts}`.
- Strict unresolved but meaningful tendency pairs: `{summary['strict_unresolved_but_tendency_count']}`.

## Incremental SAR-edge information

- Strict outcomes: `{strict_counts}`.
- Scene-common preferences: `{scene_counts}`.
- SAR-only remains static-feasibility ambiguous by design; it does not use a hidden morphology ranker.

## Branch specificity

- Strict result: `STRICT_BRANCH_SPECIFIC_EVALUATION_UNAVAILABLE` because no authoritative confirmed raw-fragment identity exists.
- Offline likely-supported exploratory comparisons: `{len(likely)}`.
- Unresolved/conflicting grounding comparisons retained: `{len(unresolved)}`.

## Reference-free controls

- Structurally matched reference-free pairs: `{len(unsupported)}`.
- Strict relation-profile difference fraction: `{summary['reference_free_strict_profile_difference_fraction']}`.
- Leaning-profile difference fraction: `{summary['reference_free_leaning_profile_difference_fraction']}`.

## Visual review

Deterministic cases are materialized in `r04_visual_case_registry.csv` and `R04_CONFIRMATION_CASE_CONTACT_SHEET.jpg`.  Direct multimodal review and the final method-reality discrepancy ledger are completed after this quantitative materialization without changing or rerunning CMR-v0.

## Non-claims

No weighted score, pruning, tracker, assignment, runtime identity, factor graph, P2, final SAR center, final SAR box, physical PERSON velocity, platform trajectory, or synchronization calibration is produced.
"""
    FINAL_REPORT.write_text(report, encoding="utf-8")


def freeze_final_manifest() -> None:
    verify_pre_reference_freeze()
    if not FINAL_SUMMARY.exists() or not (POST / "CMR_V0_R04_MULTIMODAL_VISUAL_REVIEW_LEDGER.md").exists():
        raise RuntimeError("final summary and visual review ledger are required")
    files = [
        path
        for path in OUTPUT.rglob("*")
        if path.is_file()
        and path not in {FINAL_MANIFEST, OUTPUT / "cmr_v0_r04_independent_validation.json"}
        and "_temp" not in path.parts
    ]
    payload = {
        "schema": "PERSON_CMR_V0_R04_FINAL_MANIFEST_V1",
        "created_at": now_iso(),
        "head": git_head(),
        "one_shot_confirmation": True,
        "mechanism_modified_after_reveal": False,
        "files": [
            {"path": str(path.relative_to(WORKSPACE)), "bytes": path.stat().st_size, "sha256": sha256_file(path)}
            for path in sorted(files)
        ],
    }
    write_json(FINAL_MANIFEST, payload)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "phase",
        choices=["freeze-protocol", "pre-reference", "post-reference", "freeze-final"],
    )
    return parser.parse_args()


def main() -> None:
    phase = parse_args().phase
    if phase == "freeze-protocol":
        freeze_protocol()
    elif phase == "pre-reference":
        pre_reference_phase()
    elif phase == "post-reference":
        post_reference_phase()
    elif phase == "freeze-final":
        freeze_final_manifest()


if __name__ == "__main__":
    main()
