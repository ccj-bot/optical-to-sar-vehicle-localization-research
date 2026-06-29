#!/usr/bin/env python
"""Generate Phase5B first-run diagnostic proposals from the frozen v0 config.

This script only creates diagnostic proposal hypotheses. It does not join
A019/A021, does not compute GT/oracle metrics, and does not modify C3/C4.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import shutil
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs" / "phase5B_first_diagnostic_run_config_v0.json"
TARGET_PATH = ROOT / "output" / "gm17_phase4D_candidate_pool_ceiling_audit_20260629_001655" / "candidate_pool_ceiling_per_target.csv"
A005_PATH = ROOT / "output" / "clean_no_gt_localizer_2026-05-31_boundary_tables" / "gm17_temporal_inference.csv"
LOG_ROOT = ROOT / "logs"

EXPECTED_ROUTES = ["shell_grid", "energy_contrast_peak", "connected_component"]

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
    "pred_heading_deg",
]

FORBIDDEN_TARGET_FIELDS = [
    "selection_limited",
    "pool_limited",
    "oracle_usable",
    "oracle_high_quality",
    "best_iou",
    "best_center_error",
    "best_iou_center_error",
    "best_iou_candidate_id",
    "best_center_candidate_id",
    "c3_rank1_iou",
    "c3_rank1_center_error",
    "c4_rank1_iou",
    "c4_rank1_center_error",
    "failure_class",
    "diagnostic_label_boundary",
    "condition_type",
    "condition_degree",
    "condition_status",
    "truncation_degree",
    "occlusion_degree",
]

FORBIDDEN_A005_FIELDS = [
    "score",
    "lr_score",
    "sar_factor_score",
    "temporal_factor_score",
    "gm17_temporal_decision",
    "gm17_temporal_source",
    "gm17_anchor_strength",
    "n_candidates",
]

PROPOSAL_FIELDS = [
    "proposal_id",
    "target_identity",
    "scene",
    "sar_frame_num",
    "gm17_track_id",
    "cx",
    "cy",
    "w",
    "h",
    "theta",
    "proposal_source",
    "route_name",
    "route_config_id",
    "optical_prior_score",
    "sar_observation_score",
    "uncertainty_flags",
    "parent_shell_id",
    "source_crop_id",
    "provenance",
    "leakage_audit_status",
    "diagnostic_only_flag",
    "crop_x0",
    "crop_y0",
    "crop_x1",
    "crop_y1",
    "selected_image_source_id",
    "selected_image_path",
    "image_width",
    "image_height",
    "pred_cx",
    "pred_cy",
    "pred_w",
    "pred_h",
    "pred_r",
    "pred_az",
    "pred_cross",
    "pred_heading_deg",
    "route_rank",
    "route_score_semantics",
]


def norm_text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_selected_csv_rows(path: Path, allowed_fields: list[str]) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration as exc:
            raise RuntimeError(f"empty CSV: {path}") from exc

        index_by_name = {name: idx for idx, name in enumerate(header)}
        missing = [field for field in allowed_fields if field not in index_by_name]
        if missing:
            raise RuntimeError(f"{path} missing required allowed fields: {missing}")

        allowed_indices = [(field, index_by_name[field]) for field in allowed_fields]
        rows: list[dict[str, str]] = []
        for values in reader:
            row = {}
            for field, idx in allowed_indices:
                row[field] = norm_text(values[idx]) if idx < len(values) else ""
            rows.append(row)
    return rows


def validate_config(config: dict[str, Any]) -> None:
    checks = {
        "experiment_id": "phase5B_first_diagnostic_run_v0",
        "route_config_id": "phase5B_diag_v0_predeclared",
        "config_status": "frozen_before_generation",
    }
    for field, expected in checks.items():
        actual = config.get(field)
        if actual != expected:
            raise RuntimeError(f"config {field} must be {expected!r}, got {actual!r}")
    if config.get("diagnostic_only_flag") is not True:
        raise RuntimeError("config diagnostic_only_flag must be true")
    if config.get("route_list") != EXPECTED_ROUTES:
        raise RuntimeError(f"config route_list must exactly equal {EXPECTED_ROUTES!r}")


def parse_float(row: dict[str, str], field: str, target_identity: str) -> float:
    text = norm_text(row.get(field))
    if text == "":
        raise RuntimeError(f"{target_identity}: missing numeric field {field}")
    try:
        return float(text)
    except ValueError as exc:
        raise RuntimeError(f"{target_identity}: invalid numeric field {field}={text!r}") from exc


def frame_stem(a005: dict[str, str]) -> str:
    sar_frame = norm_text(a005.get("sar_frame"))
    if sar_frame:
        return Path(sar_frame).stem
    frame_num = norm_text(a005.get("sar_frame_num"))
    if not frame_num:
        return ""
    try:
        return f"{int(float(frame_num)):06d}"
    except ValueError:
        return frame_num


def path_from_policy(policy: str, a005: dict[str, str]) -> Path:
    stem = frame_stem(a005)
    path_text = policy.replace("<sar_frame>", stem)
    return Path(path_text)


def resolve_fallback_path(a005: dict[str, str], fallback_field: str) -> Path:
    text = norm_text(a005.get(fallback_field))
    path = Path(text)
    if path.is_absolute():
        return path
    return ROOT / path


def load_grayscale_image(path: Path) -> tuple[np.ndarray, int, int, str]:
    with Image.open(path) as image:
        original_mode = image.mode
        gray = image.convert("L")
        arr = np.asarray(gray, dtype=np.float32)
    height, width = arr.shape
    return arr, width, height, original_mode


def crop_bounds(cx: float, cy: float, width: int, height: int, crop_size: int) -> tuple[int, int, int, int]:
    x0 = int(round(cx - crop_size / 2.0))
    y0 = int(round(cy - crop_size / 2.0))
    x1 = x0 + crop_size
    y1 = y0 + crop_size
    x0 = max(0, x0)
    y0 = max(0, y0)
    x1 = min(width, x1)
    y1 = min(height, y1)
    if x1 <= x0 or y1 <= y0:
        raise RuntimeError(f"invalid crop bounds {(x0, y0, x1, y1)} for image {(width, height)}")
    return x0, y0, x1, y1


def clip_center_to_crop(cx: float, cy: float, bounds: tuple[int, int, int, int]) -> tuple[float, float]:
    x0, y0, x1, y1 = bounds
    return min(max(cx, float(x0)), float(x1 - 1)), min(max(cy, float(y0)), float(y1 - 1))


def distance_to_shell_center(cx: float, cy: float, pred_cx: float, pred_cy: float) -> float:
    return math.hypot(cx - pred_cx, cy - pred_cy)


def prior_score(cx: float, cy: float, pred_cx: float, pred_cy: float, crop_w: int, crop_h: int) -> float:
    diag = max(math.hypot(crop_w, crop_h), 1.0)
    return round(max(0.0, 1.0 - distance_to_shell_center(cx, cy, pred_cx, pred_cy) / diag), 6)


def make_base_context(
    target: dict[str, str],
    a005: dict[str, str],
    bounds: tuple[int, int, int, int],
    image_path: Path,
    selected_image_source_id: str,
    image_width: int,
    image_height: int,
) -> dict[str, Any]:
    x0, y0, x1, y1 = bounds
    return {
        "target_identity": target["target_identity"],
        "scene": target["scene"],
        "sar_frame_num": target["sar_frame_num"],
        "gm17_track_id": target["gm17_track_id"],
        "route_config_id": "phase5B_diag_v0_predeclared",
        "parent_shell_id": f"phase5B_shell::{target['target_identity']}",
        "source_crop_id": f"phase5B_crop::{target['target_identity']}::a005_centered_512",
        "leakage_audit_status": "pre_inference_allowed_fields_only_no_A019_A021_GT_oracle_panel",
        "diagnostic_only_flag": "true",
        "crop_x0": x0,
        "crop_y0": y0,
        "crop_x1": x1,
        "crop_y1": y1,
        "selected_image_source_id": selected_image_source_id,
        "selected_image_path": str(image_path).replace("\\", "/"),
        "image_width": image_width,
        "image_height": image_height,
        "pred_cx": a005["pred_cx"],
        "pred_cy": a005["pred_cy"],
        "pred_w": a005["pred_w"],
        "pred_h": a005["pred_h"],
        "pred_r": a005["pred_r"],
        "pred_az": a005["pred_az"],
        "pred_cross": a005["pred_cross"],
        "pred_heading_deg": a005.get("pred_heading_deg", ""),
    }


def make_proposal(
    context: dict[str, Any],
    route_name: str,
    cx: float,
    cy: float,
    w: float,
    h: float,
    theta: str,
    optical_score: Any,
    sar_score: Any,
    flags: list[str],
    route_score_semantics: str,
    route_meta: dict[str, Any],
) -> dict[str, Any]:
    provenance = {
        "config": "phase5B_diag_v0_predeclared",
        "contributing_routes": [route_name],
        "route_meta": route_meta,
        "diagnostic_note": "proposal hypothesis only; not a final SAR localization",
    }
    return {
        **context,
        "proposal_id": "",
        "cx": round(float(cx), 6),
        "cy": round(float(cy), 6),
        "w": round(float(w), 6),
        "h": round(float(h), 6),
        "theta": theta,
        "proposal_source": route_name,
        "route_name": route_name,
        "optical_prior_score": optical_score,
        "sar_observation_score": sar_score,
        "uncertainty_flags": "|".join(flags),
        "provenance_obj": provenance,
        "route_rank": "",
        "route_score_semantics": route_score_semantics,
    }


def generate_shell_grid(
    config: dict[str, Any],
    context: dict[str, Any],
    target: dict[str, str],
    a005: dict[str, str],
    bounds: tuple[int, int, int, int],
) -> list[dict[str, Any]]:
    pred_cx = parse_float(a005, "pred_cx", target["target_identity"])
    pred_cy = parse_float(a005, "pred_cy", target["target_identity"])
    pred_w = parse_float(a005, "pred_w", target["target_identity"])
    pred_h = parse_float(a005, "pred_h", target["target_identity"])
    theta = a005.get("pred_heading_deg", "")
    crop_w = int(context["crop_x1"]) - int(context["crop_x0"])
    crop_h = int(context["crop_y1"]) - int(context["crop_y0"])

    route_config = config["routes"]["shell_grid"]
    scales = route_config["scale_set"]
    dxs = route_config["offset_grid"]["dx_multipliers_of_pred_w"]
    dys = route_config["offset_grid"]["dy_multipliers_of_pred_h"]

    rows: list[dict[str, Any]] = []
    for scale in scales:
        w_scale = float(scale["w_scale"])
        h_scale = float(scale["h_scale"])
        for dx_mul in dxs:
            for dy_mul in dys:
                raw_cx = pred_cx + float(dx_mul) * pred_w
                raw_cy = pred_cy + float(dy_mul) * pred_h
                cx, cy = clip_center_to_crop(raw_cx, raw_cy, bounds)
                score = round(1.0 / (1.0 + math.hypot(float(dx_mul), float(dy_mul))), 6)
                flags = ["theta_metadata_only"]
                if cx != raw_cx or cy != raw_cy:
                    flags.append("center_clipped_to_crop_or_image_bounds")
                rows.append(
                    make_proposal(
                        context,
                        "shell_grid",
                        cx,
                        cy,
                        pred_w * w_scale,
                        pred_h * h_scale,
                        theta,
                        score,
                        "",
                        flags,
                        "optical_prior_score=1/(1+normalized_offset_distance); no SAR pixel score",
                        {
                            "scale_label": scale.get("label", ""),
                            "w_scale": w_scale,
                            "h_scale": h_scale,
                            "dx_multiplier_of_pred_w": float(dx_mul),
                            "dy_multiplier_of_pred_h": float(dy_mul),
                            "uses_sar_pixel_values": False,
                        },
                    )
                )
    max_count = int(route_config["max_proposals_per_target"])
    if len(rows) > max_count:
        raise RuntimeError(f"{target['target_identity']}: shell_grid produced {len(rows)} rows > {max_count}")
    return rows


def generate_energy_peaks(
    config: dict[str, Any],
    context: dict[str, Any],
    target: dict[str, str],
    a005: dict[str, str],
    crop: np.ndarray,
) -> list[dict[str, Any]]:
    pred_cx = parse_float(a005, "pred_cx", target["target_identity"])
    pred_cy = parse_float(a005, "pred_cy", target["target_identity"])
    pred_w = parse_float(a005, "pred_w", target["target_identity"])
    pred_h = parse_float(a005, "pred_h", target["target_identity"])
    theta = a005.get("pred_heading_deg", "")

    route_config = config["routes"]["energy_contrast_peak"]
    top_k = int(route_config["energy_peak_count"])
    radius = float(route_config["peak_suppression_policy"]["radius_px"])
    border = int(route_config["local_background_policy"]["border_exclusion_px"])
    minimum_mad = float(route_config["local_background_policy"]["minimum_mad"])

    if crop.shape[0] <= border * 2 or crop.shape[1] <= border * 2:
        interior = crop
        border = 0
    else:
        interior = crop[border : crop.shape[0] - border, border : crop.shape[1] - border]

    median = float(np.median(interior))
    mad = float(np.median(np.abs(interior - median)))
    scale = max(mad, minimum_mad)
    contrast = (crop - median) / scale

    ys, xs = np.mgrid[border : crop.shape[0] - border, border : crop.shape[1] - border]
    if ys.size == 0:
        ys, xs = np.mgrid[0 : crop.shape[0], 0 : crop.shape[1]]
    flat_y = ys.ravel()
    flat_x = xs.ravel()
    flat_contrast = contrast[flat_y, flat_x]
    flat_intensity = crop[flat_y, flat_x]
    shell_x = pred_cx - float(context["crop_x0"])
    shell_y = pred_cy - float(context["crop_y0"])
    flat_distance = np.hypot(flat_x - shell_x, flat_y - shell_y)
    order = np.lexsort((flat_distance, -flat_intensity, -flat_contrast))

    selected: list[tuple[int, int]] = []
    rows: list[dict[str, Any]] = []
    crop_w = int(context["crop_x1"]) - int(context["crop_x0"])
    crop_h = int(context["crop_y1"]) - int(context["crop_y0"])
    for idx in order:
        x = int(flat_x[idx])
        y = int(flat_y[idx])
        if any(math.hypot(x - sx, y - sy) < radius for sx, sy in selected):
            continue
        selected.append((x, y))
        cx = float(context["crop_x0"]) + x
        cy = float(context["crop_y0"]) + y
        rows.append(
            make_proposal(
                context,
                "energy_contrast_peak",
                cx,
                cy,
                pred_w,
                pred_h,
                theta,
                prior_score(cx, cy, pred_cx, pred_cy, crop_w, crop_h),
                round(float(contrast[y, x]), 6),
                ["theta_metadata_only", "energy_peak_not_vehicle_center_claim"],
                "sar_observation_score=local_contrast=(pixel-median)/max(MAD,1.0)",
                {
                    "peak_x_in_crop": x,
                    "peak_y_in_crop": y,
                    "median": round(median, 6),
                    "mad": round(mad, 6),
                    "minimum_mad": minimum_mad,
                    "nms_radius_px": radius,
                    "border_exclusion_px": border,
                    "uses_sar_pixel_values": True,
                },
            )
        )
        if len(rows) >= top_k:
            break
    return rows


def otsu_threshold(crop: np.ndarray) -> float:
    vals = np.clip(crop, 0, 255).astype(np.uint8).ravel()
    hist = np.bincount(vals, minlength=256).astype(np.float64)
    total = vals.size
    if total == 0:
        return 0.0
    sum_total = float(np.dot(np.arange(256), hist))
    weight_bg = 0.0
    sum_bg = 0.0
    max_between = -1.0
    best_threshold = 0
    for threshold in range(256):
        weight_bg += hist[threshold]
        if weight_bg == 0:
            continue
        weight_fg = total - weight_bg
        if weight_fg == 0:
            break
        sum_bg += threshold * hist[threshold]
        mean_bg = sum_bg / weight_bg
        mean_fg = (sum_total - sum_bg) / weight_fg
        between = weight_bg * weight_fg * (mean_bg - mean_fg) ** 2
        if between > max_between:
            max_between = between
            best_threshold = threshold
    return float(best_threshold)


def component_rows_for_threshold(
    context: dict[str, Any],
    target: dict[str, str],
    a005: dict[str, str],
    crop: np.ndarray,
    threshold: float,
    method: str,
) -> list[dict[str, Any]]:
    pred_cx = parse_float(a005, "pred_cx", target["target_identity"])
    pred_cy = parse_float(a005, "pred_cy", target["target_identity"])
    pred_w = parse_float(a005, "pred_w", target["target_identity"])
    pred_h = parse_float(a005, "pred_h", target["target_identity"])
    theta = a005.get("pred_heading_deg", "")
    min_area = 0.05 * pred_w * pred_h
    max_area = 0.50 * crop.shape[0] * crop.shape[1]
    min_side = 4

    mask = (crop >= threshold).astype(np.uint8)
    num_labels, _labels, stats, _centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)
    candidates: list[dict[str, Any]] = []
    for label in range(1, num_labels):
        x, y, w, h, area = [int(v) for v in stats[label]]
        if area < min_area or area > max_area or min(w, h) < min_side:
            continue
        full_cx = float(context["crop_x0"]) + x + w / 2.0
        full_cy = float(context["crop_y0"]) + y + h / 2.0
        candidates.append(
            {
                "x": x,
                "y": y,
                "w": w,
                "h": h,
                "area": area,
                "cx": full_cx,
                "cy": full_cy,
                "distance": distance_to_shell_center(full_cx, full_cy, pred_cx, pred_cy),
                "method": method,
                "threshold": threshold,
            }
        )
    candidates.sort(key=lambda row: (-row["area"], row["distance"]))

    fragmented = len(candidates) > 1
    rows: list[dict[str, Any]] = []
    crop_h, crop_w = crop.shape
    image_w = int(context["image_width"])
    image_h = int(context["image_height"])
    for comp in candidates:
        x = comp["x"]
        y = comp["y"]
        w = comp["w"]
        h = comp["h"]
        full_x0 = int(context["crop_x0"]) + x
        full_y0 = int(context["crop_y0"]) + y
        full_x1 = full_x0 + w
        full_y1 = full_y0 + h
        flags = ["theta_metadata_only"]
        if fragmented:
            flags.append("fragmented_component_set")
        if x <= 0 or y <= 0 or x + w >= crop_w or y + h >= crop_h or full_x0 <= 0 or full_y0 <= 0 or full_x1 >= image_w or full_y1 >= image_h:
            flags.append("boundary_touching_component")
        area_fraction = comp["area"] / max(float(crop_h * crop_w), 1.0)
        rows.append(
            make_proposal(
                context,
                "connected_component",
                comp["cx"],
                comp["cy"],
                float(w),
                float(h),
                theta,
                prior_score(comp["cx"], comp["cy"], pred_cx, pred_cy, crop_w, crop_h),
                round(area_fraction, 6),
                flags,
                "sar_observation_score=component_area_fraction_of_crop",
                {
                    "threshold_method": method,
                    "threshold_value": round(float(comp["threshold"]), 6),
                    "component_x_in_crop": x,
                    "component_y_in_crop": y,
                    "component_area_px": comp["area"],
                    "uses_sar_pixel_values": True,
                },
            )
        )
    return rows


def generate_connected_components(
    config: dict[str, Any],
    context: dict[str, Any],
    target: dict[str, str],
    a005: dict[str, str],
    crop: np.ndarray,
) -> list[dict[str, Any]]:
    route_config = config["routes"]["connected_component"]
    thresholds = [
        ("otsu_within_crop", otsu_threshold(crop)),
        ("percentile_90_within_crop", float(np.percentile(crop, 90))),
    ]
    rows: list[dict[str, Any]] = []
    for method, threshold in thresholds:
        rows.extend(component_rows_for_threshold(context, target, a005, crop, threshold, method))
    rows.sort(
        key=lambda row: (
            -float(row["provenance_obj"]["route_meta"]["component_area_px"]),
            distance_to_shell_center(
                float(row["cx"]),
                float(row["cy"]),
                parse_float(a005, "pred_cx", target["target_identity"]),
                parse_float(a005, "pred_cy", target["target_identity"]),
            ),
        )
    )
    max_components = int(route_config["component_selection_policy"]["max_components_after_filter"])
    return rows[:max_components]


def deduplicate(raw_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    by_key: dict[tuple[Any, ...], dict[str, Any]] = {}
    duplicate_count = 0
    for row in raw_rows:
        key = (
            row["route_config_id"],
            row["target_identity"],
            f"{float(row['cx']):.6f}",
            f"{float(row['cy']):.6f}",
            f"{float(row['w']):.6f}",
            f"{float(row['h']):.6f}",
            norm_text(row["theta"]),
        )
        existing = by_key.get(key)
        if existing is None:
            by_key[key] = row
            continue
        duplicate_count += 1
        existing_routes = existing["provenance_obj"].setdefault("contributing_routes", [])
        if row["route_name"] not in existing_routes:
            existing_routes.append(row["route_name"])
        existing["provenance_obj"].setdefault("deduplicated_route_sources", []).append(row["route_name"])
        existing["uncertainty_flags"] = "|".join(
            sorted(set(filter(None, existing["uncertainty_flags"].split("|") + row["uncertainty_flags"].split("|") + ["deduplicated_exact_geometry"])))
        )
    return list(by_key.values()), duplicate_count


def finalize_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows.sort(key=lambda row: (row["target_identity"], EXPECTED_ROUTES.index(row["route_name"]), float(row["cx"]), float(row["cy"]), float(row["w"]), float(row["h"])))
    counters: defaultdict[tuple[str, str], int] = defaultdict(int)
    for row in rows:
        key = (row["target_identity"], row["route_name"])
        counters[key] += 1
        row["route_rank"] = counters[key]
        row["proposal_id"] = f"phase5B_v0::{row['target_identity']}::{row['route_name']}::{counters[key]:03d}"
        row["provenance"] = json.dumps(row.pop("provenance_obj"), ensure_ascii=False, sort_keys=True)
    return rows


def route_summary(rows: list[dict[str, Any]], target_count: int, missing_image_count: int, generation_error_count: int) -> list[dict[str, Any]]:
    summary_rows: list[dict[str, Any]] = []
    for route in EXPECTED_ROUTES:
        counts = Counter(row["target_identity"] for row in rows if route in json.loads(row["provenance"])["contributing_routes"])
        values = list(counts.values())
        proposal_count = sum(values)
        summary_rows.append(
            {
                "route_name": route,
                "target_count": target_count,
                "proposal_count": proposal_count,
                "proposals_per_target_mean": round(proposal_count / target_count, 6) if target_count else 0,
                "proposals_per_target_min": min(values) if values else 0,
                "proposals_per_target_max": max(values) if values else 0,
                "missing_image_count": missing_image_count,
                "generation_error_count": generation_error_count,
                "diagnostic_only_flag": "true",
            }
        )
    return summary_rows


def write_docs_summary(
    path: Path,
    timestamp: str,
    out_dir: Path,
    route_rows: list[dict[str, Any]],
    proposal_count: int,
    warnings: list[str],
) -> None:
    route_lines = "\n".join(
        f"- `{row['route_name']}`: {row['proposal_count']} proposals; mean {row['proposals_per_target_mean']} per target"
        for row in route_rows
    )
    warning_lines = "\n".join(f"- {item}" for item in warnings) if warnings else "- None"
    text = f"""# Phase5B First Diagnostic Run v0 Summary

Date: {timestamp}

## Purpose

This run generated diagnostic proposal hypotheses from the frozen Phase5B v0 config. It is not Phase5C evaluation, not C3/C4 integration, and not a final SAR localization model.

## Config

- Config id: `phase5B_diag_v0_predeclared`
- Experiment id: `phase5B_first_diagnostic_run_v0`
- Output directory: `{rel(out_dir)}`

## Input Sources

- Config: `{rel(CONFIG_PATH)}`
- Target identity/frame/track source: `{rel(TARGET_PATH)}`
- A005 proxy source: `{rel(A005_PATH)}`
- SAR image source: grayscale display PNG, with pseudocolor fallback if needed.

Only pre-inference allowed fields were used. A019/A021, GT boxes, oracle labels, IoU, center error, panel review, and post-hoc failure labels were not joined or read for generation.

## Route Counts

{route_lines}

Total proposals after exact-geometry deduplication: {proposal_count}

## Warnings

{warning_lines}

## Boundary

- No Phase5C metrics were computed.
- No A019/A021 join was performed.
- No GT/oracle labels were used.
- No IoU or center error was computed.
- No C3/C4 comparison was made.
- No A001/A005/A019/A021 source file was modified.
- No threshold tuning, training, or calibration was performed.

## Next Step

Phase5C post-hoc ceiling audit can be designed only after this proposal output is frozen and reviewed. Phase5C must stay separate from Phase5B generation and cannot modify this v0 config for the same run.
"""
    path.write_text(text, encoding="utf-8")


def main() -> None:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    config = read_json(CONFIG_PATH)
    validate_config(config)

    out_dir = ROOT / "output" / f"phase5B_first_diagnostic_run_v0_{timestamp}"
    out_dir.mkdir(parents=True, exist_ok=False)

    target_rows = read_selected_csv_rows(TARGET_PATH, TARGET_ALLOWED_FIELDS)
    a005_rows = read_selected_csv_rows(A005_PATH, A005_ALLOWED_FIELDS)

    if len(target_rows) != 205:
        raise RuntimeError(f"target count should be 205, got {len(target_rows)}")
    target_duplicates = [target for target, count in Counter(row["target_identity"] for row in target_rows).items() if count > 1]
    if target_duplicates:
        raise RuntimeError(f"target table duplicate target_identity count should be 0, got {len(target_duplicates)}")

    a005_by_target: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in a005_rows:
        a005_by_target[row["target_identity"]].append(row)
    a005_duplicates = [target for target, rows in a005_by_target.items() if len(rows) > 1]
    if a005_duplicates:
        raise RuntimeError(f"A005 duplicate target_identity count should be 0, got {len(a005_duplicates)}")

    joined: list[tuple[dict[str, str], dict[str, str]]] = []
    missing_targets: list[str] = []
    for target in target_rows:
        matches = a005_by_target.get(target["target_identity"], [])
        if not matches:
            missing_targets.append(target["target_identity"])
            continue
        joined.append((target, matches[0]))
    if missing_targets:
        raise RuntimeError(f"A005 missing should be 0, got {len(missing_targets)}")
    if len(joined) != 205:
        raise RuntimeError(f"A005 join success should be 205, got {len(joined)}")

    image_counts: Counter[str] = Counter()
    conversion_counts: Counter[str] = Counter()
    warnings: list[str] = []
    generation_errors: list[dict[str, str]] = []
    raw_proposals: list[dict[str, Any]] = []
    missing_image_count = 0

    crop_size = int(config["shared_policies"]["crop_policy"]["crop_size_px"])
    gray_policy = config["sources"]["sar_image_source_path_policy"]
    fallback_field = config["sources"]["sar_image_fallback_path_field"]

    for target, a005 in joined:
        try:
            pred_cx = parse_float(a005, "pred_cx", target["target_identity"])
            pred_cy = parse_float(a005, "pred_cy", target["target_identity"])
            preferred_path = path_from_policy(gray_policy, a005)
            fallback_path = resolve_fallback_path(a005, fallback_field)
            if preferred_path.exists():
                image_path = preferred_path
                selected_source = config["sources"]["sar_image_source_id"]
            elif fallback_path.exists():
                image_path = fallback_path
                selected_source = config["sources"]["sar_image_fallback_source_id"]
            else:
                missing_image_count += 1
                raise RuntimeError(f"missing preferred and fallback image paths: {preferred_path}; {fallback_path}")

            image, image_width, image_height, original_mode = load_grayscale_image(image_path)
            image_counts[selected_source] += 1
            if original_mode != "L":
                conversion_counts[f"{selected_source}:{original_mode}->L"] += 1

            bounds = crop_bounds(pred_cx, pred_cy, image_width, image_height, crop_size)
            x0, y0, x1, y1 = bounds
            crop = image[y0:y1, x0:x1]
            context = make_base_context(target, a005, bounds, image_path, selected_source, image_width, image_height)

            raw_proposals.extend(generate_shell_grid(config, context, target, a005, bounds))
            raw_proposals.extend(generate_energy_peaks(config, context, target, a005, crop))
            raw_proposals.extend(generate_connected_components(config, context, target, a005, crop))
        except Exception as exc:  # noqa: BLE001 - report target-level generation failures.
            generation_errors.append({"target_identity": target["target_identity"], "error": str(exc)})

    if generation_errors:
        write_json(out_dir / "generation_errors.json", generation_errors)
        raise RuntimeError(f"generation errors encountered: {len(generation_errors)}; see {rel(out_dir / 'generation_errors.json')}")

    for conversion, count in sorted(conversion_counts.items()):
        warnings.append(f"{count} selected SAR display PNGs converted for diagnostic pixel operations: {conversion}")

    deduped, deduplicated_count = deduplicate(raw_proposals)
    final_rows = finalize_rows(deduped)
    route_rows = route_summary(final_rows, len(target_rows), missing_image_count, len(generation_errors))

    proposal_csv = out_dir / "proposal_candidates.csv"
    route_summary_csv = out_dir / "proposal_route_summary.csv"
    generation_log_json = out_dir / "proposal_generation_log.json"
    leakage_json = out_dir / "leakage_audit_report.json"
    config_used_json = out_dir / "config_used.json"
    docs_summary = ROOT / "docs" / f"phase5B_first_diagnostic_run_v0_summary_{timestamp}.md"
    run_log = LOG_ROOT / f"phase5B_first_diagnostic_run_v0_{timestamp}.md"

    write_csv(proposal_csv, final_rows, PROPOSAL_FIELDS)
    write_csv(
        route_summary_csv,
        route_rows,
        [
            "route_name",
            "target_count",
            "proposal_count",
            "proposals_per_target_mean",
            "proposals_per_target_min",
            "proposals_per_target_max",
            "missing_image_count",
            "generation_error_count",
            "diagnostic_only_flag",
        ],
    )
    shutil.copyfile(CONFIG_PATH, config_used_json)

    proposal_count_by_route = {row["route_name"]: int(row["proposal_count"]) for row in route_rows}
    generation_log = {
        "timestamp": timestamp,
        "config_path": rel(CONFIG_PATH),
        "config_hash_sha256": sha256_file(CONFIG_PATH),
        "input_source_paths": {
            "target_source": rel(TARGET_PATH),
            "a005_proxy_source": rel(A005_PATH),
            "gray_sar_policy": gray_policy,
            "fallback_field": fallback_field,
        },
        "target_count": len(target_rows),
        "join_success_count": len(joined),
        "selected_image_source_counts": dict(image_counts),
        "proposal_count_total": len(final_rows),
        "proposal_count_by_route": proposal_count_by_route,
        "raw_proposal_count_before_dedup": len(raw_proposals),
        "deduplicated_count": deduplicated_count,
        "warnings": warnings,
        "implementation_boundary_assertions": {
            "a019_a021_joined": False,
            "gt_or_oracle_metrics_computed": False,
            "iou_computed": False,
            "center_error_computed": False,
            "c3_c4_modified": False,
            "a001_a005_a019_a021_source_modified": False,
            "threshold_tuning_performed": False,
            "training_performed": False,
            "calibration_performed": False,
            "push_performed": False,
        },
    }
    write_json(generation_log_json, generation_log)

    leakage_report = {
        "allowed_fields_actually_used": {
            "phase4D_target_source": TARGET_ALLOWED_FIELDS,
            "a005_temporal_proxy": A005_ALLOWED_FIELDS,
            "image_source": ["path_exists", "png_width", "png_height", "pixel_values_for_generation"],
        },
        "forbidden_fields_not_selected_or_used": sorted(set(FORBIDDEN_TARGET_FIELDS + FORBIDDEN_A005_FIELDS)),
        "forbidden_tables_not_read": [
            "A019",
            "A021",
            "GT boxes",
            "oracle outputs",
            "panel review outputs",
        ],
        "A019_A021_not_read": True,
        "GT_oracle_not_read": True,
        "metrics_not_computed": ["IoU", "center_error", "oracle_best", "rank1_comparison", "C3_C4_comparison"],
        "C3_C4_not_modified": True,
        "A001_A005_A019_A021_not_modified": True,
        "Phase5C_join_not_performed": True,
        "diagnostic_only_flag": True,
    }
    write_json(leakage_json, leakage_report)

    write_docs_summary(docs_summary, timestamp, out_dir, route_rows, len(final_rows), warnings)

    run_log.write_text(
        "\n".join(
            [
                f"# Phase5B first diagnostic run v0 log",
                "",
                f"Timestamp: {timestamp}",
                f"Interpreter: D:/MINICONDA/envs/py311/python.exe",
                f"Output directory: {rel(out_dir)}",
                f"Proposal count total: {len(final_rows)}",
                f"Proposal count by route: {proposal_count_by_route}",
                "Boundary: no A019/A021 join, no GT/oracle metrics, no C3/C4 modification, no training, no calibration.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "output_dir": rel(out_dir),
                "proposal_candidates_csv": rel(proposal_csv),
                "proposal_count_total": len(final_rows),
                "proposal_count_by_route": proposal_count_by_route,
                "deduplicated_count": deduplicated_count,
                "warnings_count": len(warnings),
                "docs_summary": rel(docs_summary),
                "run_log": rel(run_log),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
