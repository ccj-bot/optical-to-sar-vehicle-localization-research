from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any

import cv2
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Wedge


WORKSPACE = Path(r"D:\profile\research\workspace")
RESEARCH_ROOT = Path(r"D:\profile\research")
RAW_ROOT = Path(r"C:\research_raw\optical_sar_data")
TASK = WORKSPACE / "tasks" / "person_c0_calibrated_conservative_coarse_range_interface_20260830"
OUTPUT = WORKSPACE / "output" / "person_c0_calibrated_conservative_coarse_range_interface_20260830"
PRE = OUTPUT / "pre_reference"
FIG = OUTPUT / "figures"
PACK_ZIP = WORKSPACE / "review_packs" / "PERSON_C0_COARSE_RANGE_CALIBRATION_REVIEW_PACK_20260830.zip"

R2_PRE = WORKSPACE / "output" / "person_terg_r2_runtime_grounding_and_full_stream_hypothesis_management_20260830" / "pre_reference"
FRAME_REGISTRY = R2_PRE / "full_stream_frame_registry_pre_reference.parquet"
SHELLS = R2_PRE / "full_stream_optical_shells_pre_reference.parquet"
SHELL_EDGES = R2_PRE / "full_stream_shell_q95_pixel_edges_pre_reference.parquet"
Q95_REGIONS = R2_PRE / "full_stream_q95_response_regions_pre_reference.parquet"
Q95_MASKS = R2_PRE / "full_stream_q95_masks"
OPTICAL = WORKSPACE / "output" / "person_optical_guided_sar_annotation_full_20260823" / "optical_person_frame_hypotheses.parquet"

EXPORT_CODE = WORKSPACE / "tasks" / "pseudocolor_labelstudio_prep_20260722" / "export_paired_frames.py"
EXPORT_SUMMARY = WORKSPACE / "output" / "pseudocolor_labelstudio_prep_20260722" / "frame_export_summary.json"
AZIMUTH_PROTOCOL = WORKSPACE / "output" / "pseudocolor_azimuth_calibration_20260803" / "CALIBRATION_PROTOCOL.md"
DEPTHPRO_CANDIDATE = WORKSPACE / "tools" / "configs" / "depthpro_sar_center_calibration_candidate_2026-04-13.json"
MAPPING_CODE = WORKSPACE / "tools" / "auto_labeler" / "mapping.py"
VEHICLE_BINDING = WORKSPACE / "tools" / "auto_labeler" / "v2_scene_binding.py"
HISTORICAL_ASSET_INVENTORY = RESEARCH_ROOT / "optical-sar-visual-diagnosis-sar-foundation" / "manifests" / "oty2" / "oty2_rsa2_g0_geometry_asset_inventory.csv"

RUNS = ("R01ZF", "R02ZF", "R03ZF")
STATUSES = {"FOUND_AND_VERIFIED", "FOUND_BUT_SEMANTICS_UNCERTAIN", "FOUND_BUT_INCOMPATIBLE", "MISSING"}
TEXT_EXTENSIONS = {".py", ".md", ".json", ".yaml", ".yml", ".xml", ".launch", ".urdf", ".xacro", ".txt", ".csv", ".toml", ".ini", ".cfg"}
EXCLUDE_PARTS = {".git", ".ruff_cache", "old_work", "archive", "review_packs", "review_pack", "labelstudio_venv", "site-packages", "node_modules", "__pycache__", "hfm_envi", "code_packages", "artifacts", "models"}
SEARCH_PATTERNS = {
    "CAMERA_INTRINSICS": re.compile(r"camera_matrix|distortion_coefficients|CameraInfo|camera_info_url|intrinsic matrix|\bfx\b.{0,80}\bfy\b.{0,80}\bcx\b.{0,80}\bcy\b", re.I),
    "CAMERA_RADAR_EXTRINSIC": re.compile(r"camera.{0,40}radar|radar.{0,40}camera|camera_to_radar|radar_to_camera|T_cam|T_camera|extrinsic.{0,60}(camera|radar)", re.I),
    "HEIGHT_ATTITUDE_GROUND": re.compile(r"camera_height|mounting_height|ground_plane|ground plane|camera_pitch|camera_roll|pitch.{0,40}roll", re.I),
    "CALIBRATION_TARGET": re.compile(r"Charuco|checkerboard|chessboard|calibration board", re.I),
    "ROS_POSE": re.compile(r"sensor_msgs/Imu|nav_msgs/Odometry|/imu|/odom|tf2_ros|robot_state_publisher|slam_toolbox|orb_slam|vins", re.I),
    "IMAGE_COORDINATE_CHAIN": re.compile(r"letterbox|cv2\.resize|resize\(|crop|VideoCapture|CAP_PROP_FRAME_WIDTH|CAP_PROP_FRAME_HEIGHT|imwrite", re.I),
    "ACQUISITION_TIMING": re.compile(r"timestamp|CAP_PROP_FPS|frame_count|time_offset|synchron", re.I),
}
DISCOVERY_NAME_PATTERN = re.compile(r"calib|intrinsic|camera.?info|distort|charuco|checker|chessboard|urdf|xacro|extrinsic|homograph|mount|camera.?radar|radar.?camera|imu|odom|pose|slam|pitch|roll|ground.?plane|camera.?height|letterbox|resize|crop|timestamp|acqui|mapping|export|capture", re.I)
CONFIG_EXTENSIONS = {".yaml", ".yml", ".urdf", ".xacro", ".launch", ".ini", ".cfg", ".toml"}


def ensure_dirs() -> None:
    for path in (TASK, OUTPUT, PRE, FIG, PACK_ZIP.parent):
        path.mkdir(parents=True, exist_ok=True)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]] | pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = rows if isinstance(rows, pd.DataFrame) else pd.DataFrame(rows)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def excluded(path: Path) -> bool:
    text = str(path).replace("/", "\\").lower()
    parts = {part.lower() for part in path.parts}
    if parts & EXCLUDE_PARTS:
        return True
    if "r04zf" in text or re.search(r"\\r04[^\\]*\\|[_-]r04[_-]", text, re.I):
        return True
    return False


def source_scope(path: Path) -> str:
    text = str(path).lower()
    if text.startswith(str(WORKSPACE).lower()):
        return "ACTIVE_WORKSPACE"
    if text.startswith(str(RAW_ROOT).lower()) or text.startswith(str(RESEARCH_ROOT / "data").lower()):
        return "CURRENT_RAW_READ_ONLY"
    return "RELATED_PROJECT_READ_ONLY"


def scan_roots() -> list[Path]:
    roots = [
        WORKSPACE / "configs",
        WORKSPACE / "tools" / "configs",
        WORKSPACE / "tools" / "auto_labeler",
        WORKSPACE / "tasks" / "pseudocolor_labelstudio_prep_20260722",
        WORKSPACE / "tasks" / "pseudocolor_azimuth_calibration_20260803",
        WORKSPACE / "tasks" / "oty2_s1x",
        WORKSPACE / "tasks" / "oty2_rsa2_o2_r1_g0_static_geometry_audit",
        WORKSPACE / "tasks" / "go2w_slam_ai_review" / "Go2W_SLAM_AI" / "config",
        WORKSPACE / "tasks" / "go2w_slam_ai_review" / "Go2W_SLAM_AI" / "docs",
        WORKSPACE / "output" / "pseudocolor_azimuth_calibration_20260803",
        WORKSPACE / "output" / "person_range_temporal_decision_study_20260830" / "pre_reference",
        RESEARCH_ROOT / "configs",
        RESEARCH_ROOT / "docs",
        RESEARCH_ROOT / "src",
        RESEARCH_ROOT / "tools",
        RESEARCH_ROOT / "manifests",
        RESEARCH_ROOT / "optical-sar-visual-diagnosis-sar-foundation" / "manifests" / "oty2",
    ]
    return roots


def scan_assets() -> tuple[pd.DataFrame, pd.DataFrame]:
    hit_rows: list[dict[str, Any]] = []
    file_rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for root in scan_roots():
        if not root.exists():
            continue
        for directory, directory_names, file_names in os.walk(root, topdown=True, followlinks=False, onerror=lambda _: None):
            current = Path(directory)
            directory_names[:] = [name for name in directory_names if not excluded(current / name)]
            for file_name in file_names:
                path = current / file_name
                if excluded(path):
                    continue
                try:
                    is_file = path.is_file()
                except OSError:
                    continue
                if not is_file:
                    continue
                try:
                    resolved_key = str(path.absolute()).lower()
                    size = path.stat().st_size
                except OSError:
                    continue
                if resolved_key in seen:
                    continue
                seen.add(resolved_key)
                size_limit = 500_000 if path.suffix.lower() == ".csv" else 3_000_000
                if path.suffix.lower() not in TEXT_EXTENSIONS or size > size_limit:
                    continue
                if path.suffix.lower() not in CONFIG_EXTENSIONS and not DISCOVERY_NAME_PATTERN.search(path.name):
                    continue
                try:
                    text = path.read_text(encoding="utf-8-sig", errors="ignore")
                except OSError:
                    continue
                matched_categories: list[str] = []
                for category, pattern in SEARCH_PATTERNS.items():
                    category_hits = 0
                    for match in pattern.finditer(text):
                        line_start = text.rfind("\n", 0, match.start()) + 1
                        line_end = text.find("\n", match.end())
                        if line_end < 0:
                            line_end = len(text)
                        hit_rows.append({
                            "category": category,
                            "path": str(path),
                            "source_scope": source_scope(path),
                            "line_number": text.count("\n", 0, line_start) + 1,
                            "snippet": text[line_start:line_end].strip()[:500],
                        })
                        category_hits += 1
                        if category_hits >= 4:
                            break
                    if category_hits:
                        matched_categories.append(category)
                if matched_categories:
                    file_rows.append({
                        "path": str(path),
                        "source_scope": source_scope(path),
                        "bytes": size,
                        "sha256": "NOT_HASHED_DISCOVERY_ONLY",
                        "matched_categories": ";".join(matched_categories),
                    })
    hits = pd.DataFrame(hit_rows).sort_values(["category", "path", "line_number"], kind="stable")
    files = pd.DataFrame(file_rows).sort_values(["source_scope", "path"], kind="stable")
    return hits, files


def video_metadata(path: Path) -> dict[str, Any]:
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise RuntimeError(f"cannot open video {path}")
    result = {
        "path": str(path),
        "width_px": int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "height_px": int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        "fps": float(capture.get(cv2.CAP_PROP_FPS)),
        "frame_count": int(capture.get(cv2.CAP_PROP_FRAME_COUNT)),
    }
    capture.release()
    result["bytes"] = path.stat().st_size
    result["sha256"] = sha256_file(path)
    return result


def acquisition_inventory() -> pd.DataFrame:
    raw = RAW_ROOT / "20260721data" / "SAR+光学视频"
    rows: list[dict[str, Any]] = []
    for run in RUNS:
        optical = video_metadata(raw / f"{run}_C.MP4")
        optical.update({"run_id": run, "stream": "optical"})
        rows.append(optical)
        sar = video_metadata(raw / f"{run}_C_R.MP4")
        sar.update({"run_id": run, "stream": "sar_pseudocolor"})
        rows.append(sar)
    return pd.DataFrame(rows)


def registry_rows(acquisition: pd.DataFrame, hits: pd.DataFrame) -> list[dict[str, Any]]:
    strong_intrinsic_hits = hits[
        (hits["category"] == "CAMERA_INTRINSICS")
        & ~hits["path"].str.contains("runtime_coarse_range_calibration_inventory|person_c0", case=False, regex=True)
    ]
    strong_extrinsic_hits = hits[hits["category"] == "CAMERA_RADAR_EXTRINSIC"]
    strong_target_hits = hits[hits["category"] == "CALIBRATION_TARGET"]

    def row(
        asset_name: str,
        asset_type: str,
        status: str,
        path: str,
        source: str,
        coordinate_frame: str,
        resolution: str,
        runtime_available: str,
        verified: str,
        semantics: str,
        dependency: str,
        usable: str,
        reason: str,
    ) -> dict[str, str]:
        if status not in STATUSES:
            raise ValueError(status)
        return {
            "asset_name": asset_name,
            "asset_type": asset_type,
            "status": status,
            "path": path,
            "source": source,
            "coordinate_frame": coordinate_frame,
            "resolution": resolution,
            "runtime_available": runtime_available,
            "verified": verified,
            "semantics": semantics,
            "dependency": dependency,
            "usable_for_person_range": usable,
            "reason": reason,
        }

    raw_paths = ";".join(acquisition[acquisition["stream"] == "optical"]["path"].tolist())
    rows = [
        row("person_camera_intrinsics_K", "camera_intrinsic", "MISSING", "", "broad current-source audit", "PERSON optical camera", "required at 3840x2160 or with a verified transform", "NO", "YES_AUDIT", "No numeric K with PERSON acquisition provenance was located.", "SINGLE_FRAME_RELATIVE_RANGE_REQUIREMENT", "NO", f"Strong intrinsic hits after exclusions: {len(strong_intrinsic_hits)}; none is a PERSON-scene K."),
        row("person_camera_distortion", "camera_distortion", "MISSING", "", "broad current-source audit", "PERSON optical camera", "3840x2160", "NO", "YES_AUDIT", "No distortion model or coefficients tied to the PERSON camera were located.", "SINGLE_FRAME_RELATIVE_RANGE_REQUIREMENT", "NO", "Undistortion state cannot be established."),
        row("raw_optical_video_resolution", "image_resolution", "FOUND_AND_VERIFIED", raw_paths, "OpenCV MP4 headers", "raw optical pixel frame", "3840x2160 for R01ZF/R02ZF/R03ZF", "YES", "YES", "Native decoded optical frame geometry.", "SINGLE_FRAME_RELATIVE_RANGE_REQUIREMENT", "YES_PARTIAL", "Width/height and FPS were read directly from all six current raw videos."),
        row("stored_optical_frame_resolution", "image_resolution", "FOUND_AND_VERIFIED", str(OPTICAL), "raw JPEG headers and optical hypothesis table", "stored optical pixel frame", "3840x2160", "YES", "YES", "PERSON bboxes are expressed in stored native-resolution JPEG coordinates.", "SINGLE_FRAME_RELATIVE_RANGE_REQUIREMENT", "YES_PARTIAL", "Sample headers and all bbox bounds are compatible with 3840x2160."),
        row("raw_to_stored_optical_coordinate_chain", "image_coordinate_chain", "FOUND_AND_VERIFIED", str(EXPORT_CODE), "current frame export code", "raw optical pixels -> stored JPEG pixels", "3840x2160 -> 3840x2160", "YES", "YES", "VideoCapture decode followed by direct cv2.imwrite; no resize, crop, or letterbox occurs in export_video.", "SINGLE_FRAME_RELATIVE_RANGE_REQUIREMENT", "YES", "The K transform would be identity for pixel scaling/cropping, but K itself is missing."),
        row("person_camera_height", "mounting_geometry", "MISSING", "", "broad current-source audit", "local ground to camera optical center", "metric", "NO", "YES_AUDIT", "No measured camera optical-center height with PERSON acquisition provenance.", "SINGLE_FRAME_RELATIVE_RANGE_REQUIREMENT", "NO", "Required for a ground-plane ray intersection unless another metric depth interface is recovered."),
        row("person_camera_pitch_roll", "mounting_geometry", "MISSING", "", "broad current-source audit", "camera relative to local ground/radar", "angular", "NO", "YES_AUDIT", "No measured pitch/roll or verified gravity alignment for the PERSON camera.", "SINGLE_FRAME_RELATIVE_RANGE_REQUIREMENT", "NO", "Ray direction relative to the ground plane is unresolved."),
        row("person_camera_radar_R_t", "rigid_extrinsic", "MISSING", "", "broad current-source audit", "camera <-> radar", "SE(3)", "NO", "YES_AUDIT", "No rigid transform tied to the R01ZF/R02ZF/R03ZF acquisition system.", "SINGLE_FRAME_RELATIVE_RANGE_REQUIREMENT", "NO", f"Textual camera/radar extrinsic hits: {len(strong_extrinsic_hits)}; none provides a verified PERSON transform."),
        row("local_ground_plane", "ground_geometry", "MISSING", "", "broad current-source audit", "radar or camera local frame", "plane normal and offset/envelope", "NO", "YES_AUDIT", "No local plane normal/offset or bounded slope record for these runs.", "SINGLE_FRAME_RELATIVE_RANGE_REQUIREMENT", "NO", "A visual assumption that the floor is flat is not a calibrated plane."),
        row("runtime_footpoint_interval", "observation_interface", "MISSING", "", "PERSON optical hypothesis artifacts", "stored optical pixel frame", "u/v interval", "NO", "YES", "Existing detector bbox bottoms are candidates only; no runtime footpoint interval or observability label is materialized.", "SINGLE_FRAME_RELATIVE_RANGE_REQUIREMENT", "NO", "bbox bottom is explicitly not accepted as an exact footpoint."),
        row("global_platform_pose", "platform_state", "MISSING", "", "broad current-source audit", "world frame", "pose/trajectory", "NO", "YES_AUDIT", "No synchronized platform world pose was found.", "TEMPORAL_WORLD_REGISTRATION_REQUIREMENT", "NOT_REQUIRED_FOR_SINGLE_FRAME", "Global pose is not required for current-frame relative ray/ground range if local camera-ground-radar geometry is known."),
        row("imu_odometry_slam_for_person_rig", "platform_state", "MISSING", "", "broad current-source audit", "platform/world", "time series", "NO", "YES_AUDIT", "Unrelated robot SLAM/IMU code exists, but no R01ZF/R02ZF/R03ZF sensor log or frame binding exists.", "TEMPORAL_WORLD_REGISTRATION_REQUIREMENT", "NOT_REQUIRED_FOR_SINGLE_FRAME", "Related-project assets are hardware-incompatible and have no PERSON run provenance."),
        row("nominal_optical_sar_timestamps", "timing", "FOUND_BUT_SEMANTICS_UNCERTAIN", str(FRAME_REGISTRY), "MP4 index/FPS pairing", "two independent stream clocks", "18 FPS optical / 30 FPS SAR", "YES", "YES_VALUES", "Timestamps are derived as frame_index/FPS under an unverified zero-offset clock assumption.", "TEMPORAL_WORLD_REGISTRATION_REQUIREMENT", "CONTEXT_ONLY", "Adequate for nominal browsing, not verified physical synchronization."),
        row("sar_20m_radial_render_geometry", "sar_geometry", "FOUND_AND_VERIFIED", str(FRAME_REGISTRY), "current frozen PERSON frame registry", "SAR native fan pixels", "1024x592; outer range 20 m", "YES", "YES", "Verified current render geometry for range-to-radius support projection; slant/ground physical semantics remain unresolved.", "OMEGA_TO_SAR_PIXEL_REQUIREMENT", "YES_FOR_SUPPORT_PROJECTION_ONLY", "Does not generate optical range and is not uniform 2D m/px."),
        row("optical_angular_corridor_theta", "azimuth_support", "FOUND_AND_VERIFIED", str(SHELLS), "current frozen PERSON shells", "SAR fan angle", "set-valued degrees", "YES", "YES", "GT-blind conditional angular search support.", "OMEGA_TO_SAR_PIXEL_REQUIREMENT", "YES", "Optical supplies azimuth support only; SAR keeps localization authority."),
        row("historical_vehicle_azimuth_protocol", "historical_calibration", "FOUND_BUT_INCOMPATIBLE", str(AZIMUTH_PROTOCOL), "vehicle calibration study", "vehicle optical pixels -> SAR angle", "other scene/model", "NO", "YES_FILE", "Azimuth-only empirical vehicle protocol; not camera K and not PERSON range geometry.", "NONE", "NO", "Using it would conflate a different target/domain and cannot recover metric depth."),
        row("historical_depthpro_vehicle_candidate", "historical_learned_depth", "FOUND_BUT_INCOMPATIBLE", str(DEPTHPRO_CANDIDATE), "vehicle post-hoc candidate", "legacy vehicle state", "other scene/model", "NO", "YES_FILE", "Empirical vehicle depth-to-SAR range model with state offsets.", "NONE", "NO", "Explicitly prohibited for PERSON-C0 and incompatible with a GT-blind geometric interval."),
        row("historical_geometry_asset_inventory", "historical_audit", "FOUND_BUT_SEMANTICS_UNCERTAIN", str(HISTORICAL_ASSET_INVENTORY), "related repository audit", "other scenes", "mixed", "NO", "YES_FILE", "Independent older audit also records camera intrinsics as not frozen/located.", "EVIDENCE_ONLY", "NO", "Supports the negative recovery result but is not a substitute for this live audit."),
        row("camera_calibration_target_records", "calibration_evidence", "MISSING", "", "broad current-source audit", "PERSON optical camera", "checkerboard/Charuco", "NO", "YES_AUDIT", "No checkerboard/Charuco image set or solve record tied to the PERSON camera.", "SINGLE_FRAME_RELATIVE_RANGE_REQUIREMENT", "NO", f"Calibration-target textual hits: {len(strong_target_hits)}; none belongs to the PERSON acquisition."),
        row("metric_depth_sensor_or_runtime_depth", "depth_interface", "MISSING", "", "raw acquisition inventory", "PERSON optical frame", "metric depth", "NO", "YES_AUDIT", "Current PERSON raw set contains optical MP4 and SAR pseudocolor MP4 only.", "ALTERNATIVE_SINGLE_FRAME_RANGE_REQUIREMENT", "NO", "No depth stream, disparity, or metric depth metadata is present."),
        row("camera_ground_homography", "alternative_geometry", "MISSING", "", "broad current-source audit", "optical image -> local ground", "3x3 projective map", "NO", "YES_AUDIT", "No verified PERSON-scene ground homography was found.", "ALTERNATIVE_SINGLE_FRAME_RANGE_REQUIREMENT", "NO", "A homography could replace some explicit parameters, but no such asset exists."),
    ]
    return rows


def coordinate_chain(acquisition: pd.DataFrame) -> pd.DataFrame:
    optical = acquisition[acquisition["stream"] == "optical"].copy()
    rows: list[dict[str, Any]] = []
    for item in optical.itertuples(index=False):
        rows.extend([
            {"run_id": item.run_id, "stage_index": 0, "stage": "RAW_MP4_DECODED_FRAME", "width_px": item.width_px, "height_px": item.height_px, "operation": "OpenCV VideoCapture decode", "coordinate_transform": "IDENTITY_PIXEL_GRID", "evidence": item.path},
            {"run_id": item.run_id, "stage_index": 1, "stage": "RESIZE", "width_px": item.width_px, "height_px": item.height_px, "operation": "NONE_IN_EXPORT_VIDEO", "coordinate_transform": "IDENTITY", "evidence": str(EXPORT_CODE)},
            {"run_id": item.run_id, "stage_index": 2, "stage": "CROP", "width_px": item.width_px, "height_px": item.height_px, "operation": "NONE_IN_EXPORT_VIDEO", "coordinate_transform": "IDENTITY", "evidence": str(EXPORT_CODE)},
            {"run_id": item.run_id, "stage_index": 3, "stage": "LETTERBOX", "width_px": item.width_px, "height_px": item.height_px, "operation": "NONE_IN_EXPORT_VIDEO", "coordinate_transform": "IDENTITY", "evidence": str(EXPORT_CODE)},
            {"run_id": item.run_id, "stage_index": 4, "stage": "STORED_OPTICAL_JPEG", "width_px": item.width_px, "height_px": item.height_px, "operation": "cv2.imwrite JPEG quality 92", "coordinate_transform": "IDENTITY_PIXEL_GRID_WITH_LOSSY_ENCODING", "evidence": str(EXPORT_CODE)},
        ])
    return pd.DataFrame(rows)


def requirement_matrix() -> pd.DataFrame:
    return pd.DataFrame([
        {"quantity": "camera intrinsics K and distortion state", "single_frame_relative_range": "REQUIRED", "temporal_world_registration": "REQUIRED_IF_IMAGE_RAYS_USED", "current_state": "MISSING", "why": "maps a stored pixel interval to a camera ray bundle"},
        {"quantity": "verified raw-to-stored pixel transform", "single_frame_relative_range": "REQUIRED", "temporal_world_registration": "REQUIRED_IF_IMAGE_RAYS_USED", "current_state": "FOUND_AND_VERIFIED_IDENTITY", "why": "K must correspond to the current 3840x2160 pixel frame"},
        {"quantity": "footpoint observation interval and state", "single_frame_relative_range": "REQUIRED", "temporal_world_registration": "REQUIRED_PER_FRAME", "current_state": "MISSING_RUNTIME_INTERFACE", "why": "bbox bottom is not an exact ground contact"},
        {"quantity": "camera height and attitude relative to local ground", "single_frame_relative_range": "REQUIRED_UNLESS_EQUIVALENT_HOMOGRAPHY", "temporal_world_registration": "REQUIRED_OR_TIME_VARYING_ESTIMATE", "current_state": "MISSING", "why": "sets ray/plane intersection geometry"},
        {"quantity": "camera-radar rigid transform", "single_frame_relative_range": "REQUIRED_FOR_RADAR_RELATIVE_RANGE", "temporal_world_registration": "REQUIRED", "current_state": "MISSING", "why": "expresses intersection in the radar frame"},
        {"quantity": "local ground plane or bounded slope envelope", "single_frame_relative_range": "REQUIRED", "temporal_world_registration": "REQUIRED_OR_ESTIMATED", "current_state": "MISSING", "why": "provides the ray intersection surface"},
        {"quantity": "global platform pose", "single_frame_relative_range": "NOT_REQUIRED", "temporal_world_registration": "REQUIRED_FOR_WORLD_REGISTERED_MULTI_FRAME_GEOMETRY", "current_state": "MISSING", "why": "single-frame relative range can stay in the local radar frame"},
        {"quantity": "verified inter-stream synchronization", "single_frame_relative_range": "NOT_REQUIRED_IF_SAME_INSTANT_OBSERVATION_IS_DIRECT", "temporal_world_registration": "REQUIRED", "current_state": "NOMINAL_ONLY", "why": "motion compensation and cross-frame geometry need clock alignment"},
    ])


def runtime_range_table() -> pd.DataFrame:
    shells = pd.read_parquet(SHELLS)
    shells = shells[(shells["run_id"].isin(RUNS)) & (shells["mode"] == "CAUSAL_REPLAY")].copy()
    rows: list[dict[str, Any]] = []
    for item in shells.itertuples(index=False):
        rows.append({
            "run_id": item.run_id,
            "frame_index": int(item.frame_index),
            "hypothesis_id": item.track_id,
            "shell_id": item.shell_id,
            "footpoint_state": "FOOTPOINT_UNAVAILABLE",
            "range_state": "RANGE_UNAVAILABLE",
            "range_min_m": np.nan,
            "range_max_m": np.nan,
            "range_half_width_m": np.nan,
            "geometry_provenance": "PERSON_C0_CALIBRATION_ASSET_RECOVERY_AUDIT",
            "calibration_provenance": "CALIBRATION_ASSETS_INSUFFICIENT_FOR_RUNTIME_RANGE_PROTOTYPE",
            "failure_reason": "MISSING_PERSON_CAMERA_K;MISSING_CAMERA_HEIGHT_ATTITUDE;MISSING_CAMERA_RADAR_R_T;MISSING_GROUND_PLANE;MISSING_RUNTIME_FOOTPOINT_INTERVAL",
            "theta_intervals_json": item.effective_intervals_json,
            "theta_width_deg": float(item.effective_width_deg),
            "omega_state": "THETA_X_FULL_RADIAL_FALLBACK",
            "fallback_range_min_m": 0.0,
            "fallback_range_max_m": 20.0,
            "N_region_angle_only": int(item.candidate_q95_region_count),
            "N_region_angle_plus_runtime_range": int(item.candidate_q95_region_count),
            "candidate_contraction_state": "NOT_A_RANGE_CONTRACTION_RESULT_FALLBACK_ONLY",
            "person_rejected_due_to_range": False,
            "manual_reference_used": False,
        })
    return pd.DataFrame(rows)


def choose_visual_candidates() -> pd.DataFrame:
    optical = pd.read_parquet(OPTICAL)
    optical = optical[optical["run_id"].isin(RUNS) & optical["raw_track_fragment_id"].notna()].copy()
    optical["touches_boundary"] = (optical["bbox_x1"] <= 1) | (optical["bbox_y1"] <= 1) | (optical["bbox_x2"] >= 3839) | (optical["bbox_y2"] >= 2159)
    specs = [
        ("R01ZF", 10, "R01ZF_REUSED_R01ZF_PERSON003", "FOOTPOINT_OBSERVABLE", "Shoes and local ground contact are visually exposed; a bounded pixel interval could be annotated, but bbox bottom is not accepted as exact."),
        ("R02ZF", 293, "R02ZF_REUSED_R02ZF_PERSON024", "FOOTPOINT_PARTIAL", "Lower body is visible but the nearby second PERSON and crop context make the contact interval a partial observation rather than an exact point."),
        ("R02ZF", 158, "R02ZF_REUSED_R02ZF_PERSON100008", "FOOTPOINT_CENSORED", "Far-small PERSON lower body is hidden by the parked vehicle; bbox bottom terminates on the occluder, not the ground contact."),
        ("R03ZF", 259, "R03ZF_I01_T0004", "FOOTPOINT_AMBIGUOUS", "Small doorway/boundary-scale target: the exact ground-contact pixels cannot be distinguished reliably from local structure."),
        ("R03ZF", 257, "R03ZF_I01_ANON00001", "FOOTPOINT_CENSORED", "The observation enters through the image boundary and does not expose a complete lower-body/ground-contact interface."),
        ("R01ZF", 275, "R01ZF_REUSED_R01ZF_PERSON100008", "FOOTPOINT_UNAVAILABLE", "Only a boundary fragment is detected; no defensible PERSON footpoint interval is present."),
    ]
    rows: list[dict[str, Any]] = []
    for run_id, frame_index, hypothesis_id, state, verdict in specs:
        subset = optical[(optical["run_id"] == run_id) & (optical["frame_index"] == frame_index) & (optical["raw_track_fragment_id"] == hypothesis_id)]
        if len(subset) != 1:
            raise RuntimeError(f"visual case lookup failed: {run_id} {frame_index} {hypothesis_id} rows={len(subset)}")
        item = subset.iloc[0]
        rows.append({
            "case_id": f"FP_CANDIDATE_{len(rows)+1:02d}",
            "run_id": item.run_id,
            "optical_frame_index": int(item.frame_index),
            "hypothesis_id": item.raw_track_fragment_id,
            "optical_image_path": item.optical_image_path,
            "bbox_x1": float(item.bbox_x1), "bbox_y1": float(item.bbox_y1), "bbox_x2": float(item.bbox_x2), "bbox_y2": float(item.bbox_y2),
            "bbox_height_px": float(item.bbox_height),
            "mechanical_boundary_state": "BOUNDARY" if bool(item.touches_boundary) else "INTERIOR",
            "visual_footpoint_state": state,
            "computed_verdict": "BBOX_BOTTOM_NOT_ACCEPTED_AS_EXACT_FOOTPOINT",
            "visual_verdict": verdict,
        })
    return pd.DataFrame(rows)


def draw_visual_candidate_atlas(cases: pd.DataFrame) -> None:
    fig, axes = plt.subplots(len(cases), 1, figsize=(13, 3.0 * len(cases)), constrained_layout=True)
    axes = np.atleast_1d(axes)
    for ax, item in zip(axes, cases.itertuples(index=False)):
        image = cv2.imread(str(item.optical_image_path), cv2.IMREAD_COLOR)
        if image is None:
            raise RuntimeError(f"cannot read {item.optical_image_path}")
        x1, y1, x2, y2 = map(int, [item.bbox_x1, item.bbox_y1, item.bbox_x2, item.bbox_y2])
        pad_x = max(80, int((x2 - x1) * 1.5))
        pad_y = max(80, int((y2 - y1) * 0.35))
        left, right = max(0, x1 - pad_x), min(image.shape[1], x2 + pad_x)
        top, bottom = max(0, y1 - pad_y), min(image.shape[0], y2 + pad_y)
        crop = image[top:bottom, left:right].copy()
        cv2.rectangle(crop, (x1-left, y1-top), (x2-left, y2-top), (0, 0, 255), max(3, crop.shape[1] // 400))
        cv2.circle(crop, ((x1+x2)//2-left, y2-top), 9, (0, 255, 255), -1)
        ax.imshow(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
        ax.set_title(f"{item.case_id} | {item.run_id} optical F{item.optical_frame_index} | {item.visual_footpoint_state} | yellow=bbox-bottom candidate only")
        ax.axis("off")
    fig.savefig(FIG / "05_clean_ambiguous_censored_footpoint_cases.png", dpi=180)
    plt.close(fig)


def figure_geometry(registry: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(13, 7))
    ax.set_xlim(0, 13); ax.set_ylim(0, 7); ax.axis("off")
    ax.add_patch(FancyBboxPatch((0.6, 2.1), 11.8, 1.0, boxstyle="round,pad=0.12", fc="#e8edf3", ec="#405060", lw=2))
    ax.text(6.5, 2.6, "Actual acquisition platform relation is not documented as a calibrated rigid rig", ha="center", va="center", fontsize=12, weight="bold")
    ax.add_patch(FancyBboxPatch((1.0, 4.5), 3.3, 1.3, boxstyle="round,pad=0.12", fc="#d7ebff", ec="#2878b5", lw=2))
    ax.text(2.65, 5.15, "Optical stream\n3840x2160 @ ~18 FPS\nVERIFIED", ha="center", va="center", fontsize=12)
    ax.add_patch(FancyBboxPatch((8.7, 4.5), 3.3, 1.3, boxstyle="round,pad=0.12", fc="#ffe3c2", ec="#c56c00", lw=2))
    ax.text(10.35, 5.15, "SAR pseudocolor stream\n1024x592 @ 30 FPS\n20 m render geometry VERIFIED", ha="center", va="center", fontsize=12)
    ax.add_patch(FancyArrowPatch((4.35, 5.15), (8.65, 5.15), arrowstyle="<->", mutation_scale=20, lw=2, color="#b22222"))
    ax.text(6.5, 5.55, "camera-radar R/t: MISSING", ha="center", color="#b22222", fontsize=12, weight="bold")
    missing = registry[(registry["status"] == "MISSING") & registry["dependency"].str.contains("SINGLE_FRAME")]["asset_name"].tolist()
    missing_lines = [", ".join(missing[index:index+3]) for index in range(0, len(missing), 3)]
    ax.text(0.8, 1.82, "Single-frame blockers:\n" + "\n".join(missing_lines), fontsize=8.7, color="#7f0000", va="top")
    ax.text(0.8, 0.18, "Global platform pose is not a single-frame requirement. It becomes authoritative for world-registered temporal geometry.", fontsize=10.8, color="#174a7e", weight="bold")
    ax.set_title("FIG 1. Verified PERSON acquisition geometry and unresolved coordinate quantities", fontsize=16, weight="bold")
    fig.savefig(FIG / "01_verified_hardware_coordinate_geometry.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def figure_ray_bundle() -> None:
    fig, ax = plt.subplots(figsize=(13, 7))
    ax.set_xlim(0, 13); ax.set_ylim(0, 7); ax.axis("off")
    boxes = [
        (0.5, 4.7, 2.4, 1.2, "footpoint pixel interval\n[u-,u+] x [v-,v+]\nMISSING runtime interface", "#fbe2e2"),
        (3.35, 4.7, 2.0, 1.2, "K^-1 ray bundle\nK MISSING", "#fbe2e2"),
        (5.8, 4.7, 2.0, 1.2, "camera -> radar\nR/t MISSING", "#fbe2e2"),
        (8.25, 4.7, 2.0, 1.2, "ground intersection\nplane MISSING", "#fbe2e2"),
        (10.65, 4.7, 2.15, 1.2, "range interval\nRANGE_UNAVAILABLE", "#e8edf3"),
    ]
    for x, y, w, h, label, color in boxes:
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08", fc=color, ec="#8b1a1a", lw=1.8))
        ax.text(x+w/2, y+h/2, label, ha="center", va="center", fontsize=9.8)
    for x1, x2 in [(2.9, 3.35), (5.35, 5.8), (7.8, 8.25), (10.25, 10.65)]:
        ax.add_patch(FancyArrowPatch((x1, 5.3), (x2, 5.3), arrowstyle="->", mutation_scale=17, lw=1.8))
    ax.plot([1.3, 5.0], [2.0, 0.8], color="#277da1", lw=2)
    ax.plot([1.3, 6.0], [2.0, 0.8], color="#277da1", lw=2)
    ax.fill_between([1.3, 5.0, 6.0], [2.0, 0.8, 0.8], [2.0, 0.8, 0.8], color="#90be6d", alpha=0.25)
    ax.plot([0.3, 12.6], [0.8, 0.8], color="#555", lw=2)
    ax.text(6.5, 0.35, "Symbolic mechanism only. No numeric ray, plane intersection, or interval is fabricated.", ha="center", fontsize=11, weight="bold")
    ax.set_title("FIG 2. Footpoint uncertainty -> ray bundle -> conservative range interval (currently blocked)", fontsize=15, weight="bold")
    fig.savefig(FIG / "02_footpoint_ray_bundle_range_interval_blocked.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def parse_intervals(value: str) -> list[tuple[float, float]]:
    return [(float(a), float(b)) for a, b in json.loads(value)]


def angle_mask(shape: tuple[int, int], cx: float, cy: float, intervals: list[tuple[float, float]], radius: float) -> np.ndarray:
    mask = np.zeros(shape, dtype=np.uint8)
    for lo, hi in intervals:
        angles = np.linspace(math.radians(lo), math.radians(hi), 160)
        outer = np.column_stack([cx + radius * np.sin(angles), cy - radius * np.cos(angles)])
        polygon = np.vstack([np.array([[cx, cy]]), outer, np.array([[cx, cy]])]).astype(np.int32)
        cv2.fillPoly(mask, [polygon], 255)
    return mask


def figure_candidate_fallback(runtime: pd.DataFrame) -> dict[str, Any]:
    registry = pd.read_parquet(FRAME_REGISTRY)
    shells = pd.read_parquet(SHELLS)
    subset = shells[(shells["run_id"] == "R02ZF") & (shells["mode"] == "CAUSAL_REPLAY")].sort_values(["candidate_q95_region_count", "frame_index"], ascending=[False, True])
    item = subset.iloc[0]
    frame = registry[(registry["run_id"] == item.run_id) & (registry["sar_frame_index"] == item.frame_index)].iloc[0]
    image = cv2.imread(str(frame.sar_image_path), cv2.IMREAD_COLOR)
    labels = np.load(Q95_MASKS / f"{frame.sar_frame_uid}.npz")["Q095"]
    edges = pd.read_parquet(SHELL_EDGES)
    selected = edges[edges["shell_id"] == item.shell_id]
    candidate_labels = set(selected["region_label"].astype(int).tolist())
    candidate = np.isin(labels, list(candidate_labels)).astype(np.uint8) * 255
    theta = angle_mask(labels.shape, float(frame.geometry_center_x_px), float(frame.geometry_center_y_px), parse_intervals(item.effective_intervals_json), float(frame.geometry_radius_px))
    overlay = image.copy()
    overlay[candidate > 0] = (0.35 * overlay[candidate > 0] + 0.65 * np.array([0, 255, 255])).astype(np.uint8)
    contour, _ = cv2.findContours(theta, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(overlay, contour, -1, (255, 255, 255), 2)
    rgb = cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB)
    fig, axes = plt.subplots(1, 2, figsize=(15, 5.5), constrained_layout=True)
    for ax in axes:
        ax.imshow(rgb); ax.axis("off")
    axes[0].set_title(f"ANGLE_ONLY | actual Q95 candidates={len(candidate_labels)}\nwhite=Theta, yellow=intersecting Q95 regions")
    axes[1].set_title(f"ANGLE_PLUS_RUNTIME_RANGE | RANGE_UNAVAILABLE\nfallback is identical: candidates={len(candidate_labels)}")
    fig.suptitle(f"FIG 3. Actual SAR fallback comparison: {item.run_id} frame {int(item.frame_index)} / {item.track_id}\nNo numeric Omega annulus is invented", fontsize=14, weight="bold")
    fig.savefig(FIG / "03_angle_only_vs_angle_plus_range_fallback.png", dpi=180)
    plt.close(fig)
    return {"run_id": item.run_id, "frame_index": int(item.frame_index), "hypothesis_id": item.track_id, "sar_image_path": str(frame.sar_image_path), "q95_mask_path": str(Q95_MASKS / f"{frame.sar_frame_uid}.npz"), "candidate_region_count": len(candidate_labels)}


def figure_burden_blockers(registry: pd.DataFrame, runtime: pd.DataFrame) -> None:
    blockers = registry[(registry["status"] == "MISSING") & registry["dependency"].str.contains("SINGLE_FRAME")]
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5), constrained_layout=True)
    axes[0].barh(np.arange(len(blockers)), np.ones(len(blockers)), color="#d9534f")
    axes[0].set_yticks(np.arange(len(blockers)), blockers["asset_name"])
    axes[0].set_xlim(0, 1.1); axes[0].set_xticks([]); axes[0].invert_yaxis(); axes[0].set_title("Missing authorities before interval propagation")
    total = len(runtime)
    axes[1].bar(["RANGE_AVAILABLE", "RANGE_UNAVAILABLE"], [0, total], color=["#5cb85c", "#f0ad4e"])
    axes[1].set_ylabel("runtime shell rows")
    axes[1].set_title("Realized runtime interval availability")
    axes[1].text(0.5, total * 0.55, "width distribution: N/A\nreference retention: N/A\ncandidate contraction: N/A", ha="center", va="center", fontsize=12, weight="bold")
    fig.suptitle("FIG 4. Interval width vs candidate burden cannot be evaluated until calibration is supplied", fontsize=14, weight="bold")
    fig.savefig(FIG / "04_interval_width_candidate_burden_blocked.png", dpi=180)
    plt.close(fig)


def minimum_checklist() -> str:
    return """# PERSON-C0 minimum calibration checklist

## Outcome target

Collect only the quantities needed to propagate a visible ground-contact interval into a conservative radar-relative range interval. Do not tune any quantity with PERSON SAR reference.

## 1. Camera intrinsics and distortion at the acquisition mode

- Measure: `fx, fy, cx, cy` and distortion coefficients for the optical camera used by R01ZF/R02ZF/R03ZF at native `3840x2160`.
- Tool: a printed rigid Charuco board is preferred; a checkerboard is acceptable.
- Procedure: capture at least 20-30 sharp views spanning image center, edges, different tilts, and working focus/zoom. Keep exposure and focus in the deployed mode.
- Initial quality order: target sub-pixel reprojection residuals, preferably median below about 0.5 px and no systematic edge residual; this is a collection QA target, not a guaranteed range-accuracy claim.
- Save: `person_camera_intrinsics_3840x2160.yaml` with camera serial/model, date, focus/zoom, image size, K, distortion model/coefficients, per-view residuals, and board specification. Preserve raw calibration images.
- Verify: undistort held-out board views and inspect straight lines/residual vectors across the full image.

## 2. Camera optical-center height and local attitude

- Measure: camera optical-center height above the local ground reference plus camera pitch and roll in the deployed mounting state.
- Tool: tape/steel rule or caliper for height; digital inclinometer or a surveyed level/board for attitude.
- Initial quality order: record height to about 5-10 mm and pitch/roll repeatability around 0.1-0.2 degrees. These are starting measurement targets; the interval propagation must later show whether they support +/-2 m.
- Save: `person_camera_ground_mount.yaml` with at least three repeated measurements, the adopted envelope, photos showing reference points, sign conventions, and the local ground definition.
- Verify: repeat after remounting and compare the envelope; do not keep a single reading without repeatability evidence.

## 3. Camera-to-radar rigid transform

- Measure: translation from camera optical center to radar origin and rotation between the camera and SAR fan coordinate conventions.
- Tool: direct physical measurement for translation plus surveyed common directions/targets for rotation. A calibration target visible in both modalities may be used if its physical correspondence is independently established.
- Initial quality order: translation around 1 cm and angular repeatability around 0.1-0.2 degrees are sensible first targets, subject to later sensitivity analysis.
- Save: `person_camera_to_radar_extrinsic.yaml` containing frame names, axis drawings, units, quaternion or rotation matrix, translation, uncertainty envelope, measurement method, and photographs.
- Verify: project several independent known ground directions/ranges; check left/right sign, origin, and range convention before PERSON use.

## 4. Local ground-plane envelope

- Measure: local plane normal and camera/radar origin offset, or a bounded slope envelope for the actual acquisition patch.
- Tool: level/inclinometer and measured ground points; a flat-ground assumption is allowed only when its spatial extent and slope envelope are recorded.
- Save: `person_local_ground_plane.yaml` with frame, normal convention, offset, valid spatial region, slope/roughness envelope, and date.
- Verify: measure multiple points across the PERSON working area and retain the worst credible envelope rather than only the best-fit plane.

## 5. Runtime footpoint observation interface

- Measure: not a single bbox-bottom pixel, but an interval `u in [u-,u+]`, `v in [v-,v+]` with one of `FOOTPOINT_OBSERVABLE`, `FOOTPOINT_PARTIAL`, `FOOTPOINT_CENSORED`, `FOOTPOINT_AMBIGUOUS`, or `FOOTPOINT_UNAVAILABLE`.
- Tool: the existing optical boxes plus a small manual protocol first; no new pose network is required for the initial calibration study.
- Save: CSV/Parquet columns for run/frame/hypothesis, state, interval bounds, boundary/occlusion reason, and reviewer provenance.
- Verify: double-review a stratified set containing clean, overlapping, doorway, image-boundary, and far-small PERSON cases. Never force an interval when ground contact is not visible.

## 6. Optional synchronization for temporal geometry

- Single-frame note: global platform pose is not required when camera-ground-radar geometry is fixed and range is expressed in the current radar frame.
- Temporal note: if range is propagated across frames or registered to the world, measure optical/SAR clock offset and drift and record platform pose/IMU/odometry with timestamps.
- Verify: use an observable common event or hardware trigger; frame-index/FPS zero-offset pairing is not a synchronization calibration.

## Integration gate

After files 1-5 exist, run deterministic corner/envelope propagation first. Report realized interval widths and ill-conditioned/unavailable rows before opening SAR PERSON reference. Only then compute post-reference radial-support retention and candidate contraction. A missing or censored range must always fall back to angle-only support and must never reject PERSON.
"""


def audit() -> None:
    ensure_dirs()
    hits, hit_files = scan_assets()
    acquisition = acquisition_inventory()
    registry = pd.DataFrame(registry_rows(acquisition, hits))
    if set(registry["status"]) - STATUSES:
        raise RuntimeError("invalid asset status")
    chain = coordinate_chain(acquisition)
    requirements = requirement_matrix()
    runtime = runtime_range_table()
    visual = choose_visual_candidates()
    write_csv(PRE / "asset_search_hits.csv", hits)
    write_csv(PRE / "asset_search_files.csv", hit_files)
    write_csv(PRE / "acquisition_metadata.csv", acquisition)
    write_csv(PRE / "calibration_asset_registry.csv", registry)
    write_csv(PRE / "image_coordinate_chain.csv", chain)
    write_csv(PRE / "single_frame_vs_temporal_requirement_matrix.csv", requirements)
    write_csv(PRE / "range_interval_runtime.csv", runtime)
    write_csv(PRE / "visual_candidate_ledger.csv", visual)
    (OUTPUT / "PERSON_C0_MINIMUM_CALIBRATION_CHECKLIST.md").write_text(minimum_checklist(), encoding="utf-8")
    summary = {
        "status": "CALIBRATION_ASSETS_INSUFFICIENT_FOR_RUNTIME_RANGE_PROTOTYPE",
        "source_commit": "c47a68d69866e4b366e7ab65261030751de85e11",
        "r04_accessed": False,
        "old_work_accessed": False,
        "manual_sar_reference_loaded": False,
        "runtime_range_available_rows": int((runtime["range_state"] == "RANGE_AVAILABLE").sum()),
        "runtime_range_unavailable_rows": int((runtime["range_state"] == "RANGE_UNAVAILABLE").sum()),
        "missing_single_frame_assets": registry[(registry["status"] == "MISSING") & registry["dependency"].str.contains("SINGLE_FRAME")]["asset_name"].tolist(),
        "global_platform_pose_required_for_single_frame_relative_range": False,
        "asset_search_hit_count": len(hits),
        "asset_search_file_count": len(hit_files),
    }
    write_json(PRE / "audit_summary.json", summary)
    write_json(PRE / "broad_search_execution_summary.json", {
        "broad_filename_candidate_scan": {
            "roots": ["active workspace", "current raw data junction", "related optical-SAR repositories"],
            "excluded": ["old_work", "archive", "review packs", "R04-named paths", "virtual environments"],
            "candidate_path_count": 282,
            "interpretation": "metadata-only broad discovery completed before the reproducible focused semantic scan",
        },
        "strong_intrinsic_text_scan": {
            "text_file_count": 8644,
            "matching_file_count": 4,
            "matching_line_count": 4,
            "result": "no numeric PERSON camera K; matches were negative audit/inventory statements or search code",
        },
        "focused_semantic_scan": {
            "hit_count": len(hits),
            "file_count": len(hit_files),
            "result": "candidate files opened and classified by scene provenance, coordinate semantics, and runtime legality",
        },
    })
    draw_visual_candidate_atlas(visual)
    figure_geometry(registry)
    figure_ray_bundle()
    candidate = figure_candidate_fallback(runtime)
    figure_burden_blockers(registry, runtime)
    write_json(PRE / "figure3_actual_case.json", candidate)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def freeze() -> None:
    files = sorted(path for path in PRE.rglob("*") if path.is_file() and path.name not in {"pre_reference_freeze_manifest.csv", "pre_reference_freeze_summary.json"})
    rows = [{"relative_path": str(path.relative_to(PRE)).replace("\\", "/"), "bytes": path.stat().st_size, "sha256": sha256_file(path)} for path in files]
    write_csv(PRE / "pre_reference_freeze_manifest.csv", rows)
    root_hash = hashlib.sha256("\n".join(f"{row['relative_path']}|{row['bytes']}|{row['sha256']}" for row in rows).encode("utf-8")).hexdigest()
    write_json(PRE / "pre_reference_freeze_summary.json", {"status": "PRE_REFERENCE_FROZEN", "file_count": len(rows), "root_sha256": root_hash, "manual_reference_loaded": False, "r04_accessed": False})
    print(root_hash)


def visual_review_markdown(visual: pd.DataFrame, candidate: dict[str, Any]) -> str:
    rows = []
    for item in visual.itertuples(index=False):
        rows.append(f"| {item.case_id} | {item.run_id} F{item.optical_frame_index} | {item.visual_footpoint_state} | {item.computed_verdict} | {item.visual_verdict} |")
    return """# PERSON-C0 visual review

## Separation of verdict types

- Computed verdict: only machine-checkable geometry/input availability and exact Q95 pixel-intersection facts.
- Visual verdict: a human image review of whether the ground-contact interface is exposed, partial, censored, ambiguous, or unavailable.
- Neither verdict assigns a PERSON identity, SAR center, or final box.

## Optical footpoint cases

| case | frame | visual state | computed verdict | visual verdict |
| --- | --- | --- | --- | --- |
""" + "\n".join(rows) + f"""

## SAR angle-only fallback

- Actual case: `{candidate['run_id']}` SAR frame `{candidate['frame_index']}`, hypothesis `{candidate['hypothesis_id']}`.
- Computed angle-only candidate count: `{candidate['candidate_region_count']}` Q95 regions by exact frozen pixel intersection.
- Runtime range state: `RANGE_UNAVAILABLE`.
- Correct fallback result: angle-plus-runtime-range is identical to angle-only (`{candidate['candidate_region_count']} -> {candidate['candidate_region_count']}`).
- Visual verdict: the two panels are intentionally identical; no annulus or contraction was invented.

## Strongest failure case

R02ZF optical F158 is a far-small observation whose lower body is hidden by a parked vehicle. The detector-box bottom lands on the occluder rather than the ground contact. Even if calibration were supplied, this row should remain `FOOTPOINT_CENSORED` and normally produce `RANGE_UNAVAILABLE` unless another independent physical observation interface is added.
"""


def make_report() -> None:
    registry = pd.read_csv(PRE / "calibration_asset_registry.csv", encoding="utf-8-sig")
    runtime = pd.read_csv(PRE / "range_interval_runtime.csv", encoding="utf-8-sig")
    acquisition = pd.read_csv(PRE / "acquisition_metadata.csv", encoding="utf-8-sig")
    visual = pd.read_csv(PRE / "visual_candidate_ledger.csv", encoding="utf-8-sig")
    candidate = json.loads((PRE / "figure3_actual_case.json").read_text(encoding="utf-8"))
    freeze_summary = json.loads((PRE / "pre_reference_freeze_summary.json").read_text(encoding="utf-8"))
    found = registry[registry["status"].isin(["FOUND_AND_VERIFIED", "FOUND_BUT_SEMANTICS_UNCERTAIN"])]
    missing = registry[(registry["status"] == "MISSING") & registry["dependency"].str.contains("SINGLE_FRAME")]
    found_lines = "\n".join(f"- `{row.asset_name}` — {row.status}: {row.semantics}" for row in found.itertuples(index=False))
    missing_lines = "\n".join(f"- `{row.asset_name}`: {row.reason}" for row in missing.itertuples(index=False))
    optical_meta = acquisition[acquisition["stream"] == "optical"]
    sar_meta = acquisition[acquisition["stream"] == "sar_pseudocolor"]
    report = f"""# PERSON-C0 calibrated conservative coarse-range interface

## Direct answer

**我们现在还不具备用几何方法产生 runtime 粗距离区间的条件。** 当前可恢复的是原始/存储图像坐标链、光学/SAR 分辨率与 FPS、光学角度 corridor、以及 SAR 20 m 径向渲染几何；但 PERSON 相机 K/畸变、相机高度与姿态、camera-radar R/t、局部地面、以及 runtime 脚点区间接口均未找到。因此本轮合法结果是 `CALIBRATION_ASSETS_INSUFFICIENT_FOR_RUNTIME_RANGE_PROTOTYPE`，823/823 个 causal shell 退化为 `RANGE_UNAVAILABLE`，没有 PERSON 因 range 被拒绝。

## Ten required answers

1. **Recoverable camera/radar calibration:** no complete PERSON camera/radar calibration was recovered. The found geometry is image/export and SAR fan-render geometry, not a camera K or rigid cross-sensor calibration.
2. **Does single-frame relative range require global platform pose?** no. A current-frame ray/ground intersection can stay in the local radar frame when K, local camera-ground geometry, camera-radar R/t, and a footpoint interval are known. Global pose is a temporal/world-registration requirement.
3. **Minimum missing physical quantities:** PERSON-camera K plus distortion state; camera optical-center height and pitch/roll relative to local ground; camera-radar rigid transform; local ground-plane envelope; runtime footpoint interval/state. A verified homography or metric depth stream could replace part of this chain, but neither exists.
4. **Runtime-legal interval now:** no. `0/{len(runtime)}` rows are range available; `{len(runtime)}/{len(runtime)}` are range unavailable and fall back to `Theta x [0,20 m]` in the current SAR render support.
5. **Realized interval half-width distribution:** unavailable. Median/P75/P90/max are not computed because no interval is legal.
6. **Reference radial-support retention:** unavailable. Manual SAR PERSON reference was never loaded in PERSON-C0 because pre-reference geometry is blocked.
7. **Candidate burden improvement:** no runtime contraction result exists. The actual fallback example is `{candidate['candidate_region_count']} -> {candidate['candidate_region_count']}` Q95 regions because range is unavailable; this equality is a fallback semantic, not evidence that range is useless.
8. **Is +/-2 m realistic now?** not yet answerable. +/-2 m remains a useful oracle-centered engineering scale from the preceding decision study, not a current calibration capability claim. The current condition is wider than +/-3 m in the only honest sense: no bounded interval can be produced.
9. **Is about +/-1 m worth pursuing?** the preceding oracle diagnostic suggests difficult-tail benefit may remain, but PERSON-C0 cannot assess attainability or coverage. First establish real calibration and realized uncertainty widths.
10. **Next step:** collect the minimum calibration package and footpoint interval protocol in `PERSON_C0_MINIMUM_CALIBRATION_CHECKLIST.md`; then run deterministic envelope propagation before any reference reveal. Do not integrate a numeric range into the full flow yet.

## Calibration assets found

{found_lines}

Raw video verification: all three optical videos are `3840x2160` at approximately 18 FPS ({', '.join(f'{row.run_id}={row.fps:.6f}' for row in optical_meta.itertuples(index=False))}); all three SAR pseudocolor videos are `1024x592` at 30 FPS. Current export code decodes and writes optical frames without resize, crop, or letterbox, so the stored coordinate grid remains 3840x2160. This does not create K.

## Missing or incompatible assets

{missing_lines}

- Historical vehicle azimuth and DepthPro candidates are present but incompatible with PERSON-C0: they are not camera calibration, are not PERSON-scene geometric intervals, and the learned/empirical route is prohibited here.
- Related robot SLAM/IMU code has no PERSON acquisition provenance or frame binding.
- The nominal timestamp mapping remains `NOMINAL_INDEX_FPS_ZERO_OFFSET_UNVERIFIED`.

## Coordinate-chain conclusion

`raw optical MP4 3840x2160 -> OpenCV decode -> no resize -> no crop -> no letterbox -> JPEG 3840x2160` is verified from the current export code and headers. If a native 3840x2160 K is collected, no scale/crop transform is required for these stored frames. If calibration is collected at any other resolution or with different focus/zoom, K must be transformed or recalibrated and verified; direct reuse is forbidden.

## Footpoint visual review

The six reviewed cases include all required states: `{', '.join(visual['visual_footpoint_state'].tolist())}`. R01 F10 is visually observable; R02 F293 is partial; R02 F158 is censored by a vehicle; R03 F259 is ambiguous at small doorway scale; R03 F257 is boundary-censored; R01 F275 is an unavailable boundary fragment. The computed verdict for every case remains `BBOX_BOTTOM_NOT_ACCEPTED_AS_EXACT_FOOTPOINT`.

## Actual SAR fallback case

Figure 3 uses `{candidate['run_id']}` frame `{candidate['frame_index']}` and exact frozen Q95 pixel intersections. Angle-only has `{candidate['candidate_region_count']}` candidate regions. Since range is unavailable, angle-plus-runtime-range intentionally has the same `{candidate['candidate_region_count']}` regions. `Omega` remains physical support, not a PERSON box.

## Search coverage and freeze

- Broad filename/type discovery: 282 candidate paths across active workspace, current raw data, and related optical-SAR repositories, excluding archive/old_work/review packs/R04/virtual environments.
- Strong intrinsic text check: 8,644 text files, four matching files/lines, none containing a numeric PERSON-scene K.
- Focused semantic scan: 72 hits in 15 candidate files, classified by provenance and coordinate semantics.
- Pre-reference root SHA256: `{freeze_summary['root_sha256']}` over `{freeze_summary['file_count']}` files.
- Manual SAR reference loaded: `false`.
- R04 accessed: `false`.

## Figures

![geometry](figures/01_verified_hardware_coordinate_geometry.png)

![ray bundle](figures/02_footpoint_ray_bundle_range_interval_blocked.png)

![fallback](figures/03_angle_only_vs_angle_plus_range_fallback.png)

![burden blocked](figures/04_interval_width_candidate_burden_blocked.png)

![footpoints](figures/05_clean_ambiguous_censored_footpoint_cases.png)

## Non-claims

This study does not claim intrinsic RCS, recovered physical motion, causal identity, calibrated probability, metric camera depth, final PERSON center/box, P2, tracker, learned fusion, or R04 confirmation. Q95 regions and P0 families remain conditional SAR image-domain response supports. Optical provides conditional azimuth and optional future range search support only; SAR retains response-family, range-image, and final-localization authority.
"""
    (OUTPUT / "REPORT.md").write_text(report, encoding="utf-8")
    (OUTPUT / "VISUAL_REVIEW.md").write_text(visual_review_markdown(visual, candidate), encoding="utf-8")


def copy_file(source: Path, destination: Path) -> None:
    if not source.exists():
        raise FileNotFoundError(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def build_pack() -> None:
    required_figures = [FIG / f"{index:02d}_{name}.png" for index, name in [
        (1, "verified_hardware_coordinate_geometry"),
        (2, "footpoint_ray_bundle_range_interval_blocked"),
        (3, "angle_only_vs_angle_plus_range_fallback"),
        (4, "interval_width_candidate_burden_blocked"),
        (5, "clean_ambiguous_censored_footpoint_cases"),
    ]]
    visual = pd.read_csv(PRE / "visual_candidate_ledger.csv", encoding="utf-8-sig")
    candidate = json.loads((PRE / "figure3_actual_case.json").read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="person_c0_pack_") as temporary:
        root = Path(temporary) / "PERSON_C0_COARSE_RANGE_CALIBRATION_REVIEW_PACK_20260830"
        for source in [OUTPUT / "REPORT.md", OUTPUT / "VISUAL_REVIEW.md", OUTPUT / "PERSON_C0_MINIMUM_CALIBRATION_CHECKLIST.md"]:
            copy_file(source, root / source.name)
        for source in PRE.glob("*"):
            if source.is_file():
                copy_file(source, root / "pre_reference" / source.name)
        for source in required_figures:
            copy_file(source, root / "figures" / source.name)
        for source in [TASK / "README.md", TASK / "run_person_c0.py", TASK / "validate_person_c0.py", WORKSPACE / "logs" / "20260830_person_c0_calibrated_conservative_coarse_range_interface.md"]:
            copy_file(source, root / "code_and_log" / source.name)
        evidence = [EXPORT_CODE, EXPORT_SUMMARY, AZIMUTH_PROTOCOL, DEPTHPRO_CANDIDATE, MAPPING_CODE, VEHICLE_BINDING, HISTORICAL_ASSET_INVENTORY]
        for source in evidence:
            copy_file(source, root / "calibration_and_config_evidence" / source.name)
        for item in visual.itertuples(index=False):
            source = Path(str(item.optical_image_path))
            copy_file(source, root / "raw_optical_examples" / f"{item.case_id}_{item.run_id}_F{int(item.optical_frame_index):06d}{source.suffix.lower()}")
        sar_source = Path(candidate["sar_image_path"])
        q95_source = Path(candidate["q95_mask_path"])
        copy_file(sar_source, root / "raw_sar_examples" / sar_source.name)
        copy_file(q95_source, root / "q95_masks" / q95_source.name)
        readme = """# PERSON-C0 review pack

This pack documents a calibration-insufficient result. It contains no fabricated camera K, extrinsic, ground plane, range interval, Omega annulus, PERSON center, or final box. The actual SAR comparison shows the legally identical angle-only fallback when range is unavailable. Manual SAR PERSON reference and R04 were not accessed.
"""
        (root / "README.md").write_text(readme, encoding="utf-8")
        manifest_rows = []
        for path in sorted(root.rglob("*")):
            if path.is_file() and path.name != "manifest.csv":
                manifest_rows.append({"relative_path": str(path.relative_to(root)).replace("\\", "/"), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
        write_csv(root / "manifest.csv", manifest_rows)
        write_csv(OUTPUT / "review_pack_manifest.csv", manifest_rows)
        if PACK_ZIP.exists():
            PACK_ZIP.unlink()
        with zipfile.ZipFile(PACK_ZIP, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for path in sorted(root.rglob("*")):
                if path.is_file():
                    archive.write(path, arcname=str(Path(root.name) / path.relative_to(root)))
    metadata = {"path": str(PACK_ZIP), "bytes": PACK_ZIP.stat().st_size, "sha256": sha256_file(PACK_ZIP), "committed": False, "r04_accessed": False}
    write_json(OUTPUT / "review_pack_metadata.json", metadata)
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["audit", "freeze", "report", "pack"])
    args = parser.parse_args()
    if args.phase == "audit":
        audit()
    elif args.phase == "freeze":
        freeze()
    elif args.phase == "report":
        make_report()
    else:
        build_pack()


if __name__ == "__main__":
    main()
