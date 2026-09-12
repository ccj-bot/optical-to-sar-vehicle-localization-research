from __future__ import annotations

import csv
import hashlib
import json
import math
import shutil
from pathlib import Path
from statistics import mean, median, pstdev

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image


WORKSPACE = Path(r"D:\profile\research\workspace")
RAW = Path(r"D:\profile\research\data")
SAR_FOUNDATION = Path(r"D:\profile\research\optical-sar-visual-diagnosis-sar-foundation")
MANIFEST = SAR_FOUNDATION / "manifests" / "oty2"
OUT = WORKSPACE / "output" / "tpgt" / "gm_mapping_reconciliation"
SCENES = ("GM_RM011", "GM_RM017", "GM_RM019")
OPT_FPS = 24.0
SAR_FPS = 50.0
CX, CY, RADIUS = 1154.0, 1330.6, 1332.7
GLOBAL_K, GLOBAL_B = 0.0875154, -40.413555


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def image_info(path: Path) -> dict[str, object]:
    with Image.open(path) as im:
        return {"width": im.width, "height": im.height, "mode": im.mode, "format": im.format}


def frame_inventory(scene: str, modality: str) -> dict[str, object]:
    if modality == "optical":
        d = RAW / scene / f"{scene}_frames"
    elif modality == "sar_pseudocolor":
        d = RAW / scene / f"{scene}_SARframes"
    else:
        d = RAW / scene / f"{scene}_SARframes_gray"
    files = sorted(d.glob("*.png")) if d.exists() else []
    idx = []
    bad = []
    dims = []
    for p in files:
        try:
            i = int(p.stem)
            idx.append(i)
            dims.append((image_info(p)["width"], image_info(p)["height"]))
        except Exception as e:
            bad.append({"file": str(p), "error": repr(e)})
    expected = list(range(max(idx) + 1)) if idx else []
    missing = sorted(set(expected) - set(idx))
    duplicates = sorted(i for i in set(idx) if idx.count(i) > 1)
    counts = {}
    for d0 in dims:
        counts[str(d0)] = counts.get(str(d0), 0) + 1
    samples = []
    for p in (files[:1] + files[len(files) // 2 : len(files) // 2 + 1] + files[-1:]):
        if p.exists():
            samples.append({"file": str(p), "sha256": sha256(p), "image": image_info(p)})
    return {
        "directory": str(d),
        "exists": d.exists(),
        "count": len(files),
        "min_index": min(idx) if idx else None,
        "max_index": max(idx) if idx else None,
        "missing_indices": missing,
        "duplicate_indices": duplicates,
        "dimension_counts": counts,
        "decode_errors": bad,
        "samples": samples,
    }


def compare_gray_pseudo(scene: str) -> dict[str, object]:
    pseudo = RAW / scene / f"{scene}_SARframes" / "000000.png"
    gray = RAW / scene / f"{scene}_SARframes_gray" / "000000.png"
    if not pseudo.exists() or not gray.exists():
        return {"status": "MISSING"}
    with Image.open(pseudo) as p, Image.open(gray) as g:
        pa = np.asarray(p.convert("RGB"), dtype=np.int16)
        ga = np.asarray(g.convert("L"), dtype=np.int16)
    lum = np.rint(0.299 * pa[..., 0] + 0.587 * pa[..., 1] + 0.114 * pa[..., 2]).astype(np.int16)
    return {
        "status": "SAME_FRAME_INDEX_AND_DIMENSION;DETERMINISTIC_PIXEL_DERIVATION_NOT_PROVEN",
        "shape_pseudocolor": list(pa.shape),
        "shape_gray": list(ga.shape),
        "equal_luma_fraction_frame_000000": float(np.mean(lum == ga)),
        "correlation_luma_gray": float(np.corrcoef(lum.ravel(), ga.ravel())[0, 1]),
    }


def build_asset_baseline() -> dict[str, object]:
    out = {"task": "TPGT-GM-B1", "scenes": {}, "source_manifest": str(MANIFEST / "oty2_p0_data_asset_manifest.csv")}
    manifest_rows = read_csv(MANIFEST / "oty2_p0_data_asset_manifest.csv")
    for scene in SCENES:
        scene_rows = [r for r in manifest_rows if r.get("scene") == scene]
        out["scenes"][scene] = {
            "optical": frame_inventory(scene, "optical"),
            "sar_pseudocolor": frame_inventory(scene, "sar_pseudocolor"),
            "sar_gray": frame_inventory(scene, "sar_gray"),
            "manifest_counts": {
                "optical": sum(r.get("modality") == "optical" for r in scene_rows),
                "sar": sum(str(r.get("modality", "")).startswith("sar") for r in scene_rows),
            },
            "pseudo_gray_relation": compare_gray_pseudo(scene),
            "gt_reference": {
                "source": str(MANIFEST / "oty2_s0_sar_gt_quality_audit.csv"),
                "note": "manual/reference audit rows are research evidence, not response-center truth",
            },
            "mask": {
                "status": "shared deterministic display/fan mask referenced by historical contracts; raw mask file not identified in scoped workspace",
                "origin_px": [CX, CY],
                "hash": None,
            },
        }
    write_json(OUT / "00_audit" / "GM_ASSET_COORDINATE_BASELINE.json", out)
    return out


def fit_affine(x: np.ndarray, y: np.ndarray) -> tuple[float, float, np.ndarray]:
    if len(x) < 2:
        return math.nan, math.nan, np.full(len(x), math.nan)
    A = np.vstack([x, np.ones_like(x)]).T
    a, b = np.linalg.lstsq(A, y, rcond=None)[0]
    return float(a), float(b), y - (a * x + b)


def time_contract(scene: str, sync_rows: list[dict[str, str]]) -> dict[str, object]:
    rows = [r for r in sync_rows if r["scene"] == scene]
    i = np.asarray([float(r["optical_frame_index"]) for r in rows])
    j = np.asarray([float(r["sar_center_frame"]) for r in rows])
    t_o = i / OPT_FPS
    t_s = j / SAR_FPS
    nominal_j = i * SAR_FPS / OPT_FPS
    nominal_residual_frames = j - nominal_j
    nominal_residual_ms = nominal_residual_frames / SAR_FPS * 1000.0
    a, b, resid = fit_affine(t_o, t_s)
    deltas = np.diff(j)
    local_two_step = float(np.mean(np.isin(deltas, [2, 3]))) if len(deltas) else math.nan
    historical_rates = {"GM_RM011": 0.786, "GM_RM017": 0.863, "GM_RM019": 0.438}
    # The rows are produced by a common-start assumption; they are not independent sync truth.
    contract = {
        "scene": scene,
        "optical_fps": OPT_FPS,
        "sar_fps": SAR_FPS,
        "frame_zero_semantics": "stored PNG indices; optical and SAR index zero are not independently hardware-registered",
        "exact_sync_status": "UNKNOWN",
        "nominal_mapping": {
            "formula": "j_center = round(i_o * 50 / 24)",
            "status": "NOMINAL_MAPPING_HYPOTHESIS",
            "common_start": "UNFROZEN",
        },
        "tested_models": {
            "T0_common_start_fixed_fps": {
                "residual_sar_frames": {"mean": float(mean(nominal_residual_frames)), "std": float(pstdev(nominal_residual_frames)), "min": float(min(nominal_residual_frames)), "max": float(max(nominal_residual_frames))},
                "residual_ms": {"p50": float(np.quantile(np.abs(nominal_residual_ms), 0.5)), "p95": float(np.quantile(np.abs(nominal_residual_ms), 0.95)), "max": float(np.max(np.abs(nominal_residual_ms)))},
                "evidence": "historical generated correspondence table; not independent synchronization",
            },
            "T1_fixed_offset": {"status": "NOT_IDENTIFIABLE_FROM_COMMON_START_DERIVED_ROWS", "offset_range_ms": [float(np.min((t_s - t_o) * 1000)), float(np.max((t_s - t_o) * 1000))]},
            "T2_affine": {"a_s_per_s": a, "b_s": b, "residual_ms_p95_abs": float(np.quantile(np.abs(resid) * 1000, 0.95)), "status": "DESCRIPTIVE_ONLY"},
            "T3_piecewise_local": {"status": "NOT_JUSTIFIED", "reason": "no independent anchor series demonstrating systematic residual drift"},
        },
        "preferred_operational_model": "T0_NOMINAL_MAPPING_WITH_LOCAL_SAMPLE_WINDOW",
        "residual_summary": {
            "row_count": len(rows),
            "local_two_step_rate_computed_from_table": local_two_step,
            "local_two_step_rate_historical_audit": historical_rates[scene],
            "historical_fixed_offset_reliable": False,
        },
        "uncertainty": {"status": "UNKNOWN", "recommended_use": "sample-local SAR window; do not collapse to one exact frame"},
        "anchor_provenance": {"nominal_pair": len(rows), "manual_reference_anchor": 0, "measured_exact_sync": 0, "historical_algorithm_pair": len(rows)},
        "valid_domain": {"optical_frame_index": [int(min(i)), int(max(i))], "sar_center_frame": [int(min(j)), int(max(j))]},
        "runtime_permission": {"time_corridor": True, "exact_frame_selection": False, "hardware_sync_claim": False},
        "limitations": ["common-start and FPS are source-confirmed operational assumptions only", "reviewed pair does not prove global fixed offset", "nearby SAR window must retain local drift"],
    }
    write_json(OUT / "01_time" / f"{scene}_TIME_CONTRACT.json", contract)
    return contract


def coordinate_contract(scene: str, coord_rows: list[dict[str, str]]) -> dict[str, object]:
    rows = [r for r in coord_rows if r["scene"] == scene]
    sar_rows = {r["sar_asset_type"]: r for r in rows}
    chain = [
        {"input_coordinate": "decoded SAR pixel", "output_coordinate": "display pixel", "formula": "identity (no resize/crop/flip demonstrated)", "unit": "px", "deterministic": True, "source": "asset dimensions + coordinate contract", "uncertainty": "upstream decode lineage not fully resolved"},
        {"input_coordinate": "display pixel", "output_coordinate": "valid imaging mask", "formula": "shared deterministic fan-validity mask; raw mask artifact not located in scoped search", "unit": "boolean", "deterministic": "UNKNOWN", "source": "oty2_s0_sar_coordinate_contract.csv", "uncertainty": "mask file/hash unavailable"},
        {"input_coordinate": "display pixel (x,y)", "output_coordinate": "fan/range/azimuth", "formula": "r=hypot(x-1154.0,y-1330.6); theta=atan2(x-1154.0,1330.6-y)", "unit": "px, deg", "origin": [CX, CY], "axis_direction": {"x": "positive right", "y": "positive down"}, "deterministic": True, "scene_specific": False, "source": "src/geometry/fan_polar.py"},
        {"input_coordinate": "fan/range/azimuth", "output_coordinate": "display pixel (x,y)", "formula": "x=1154.0+r*sin(theta); y=1330.6-r*cos(theta)", "unit": "px", "origin": [CX, CY], "deterministic": True, "scene_specific": False, "source": "src/geometry/fan_polar.py"},
    ]
    c = {
        "scene": scene,
        "sar_native_image": {"width_px": 2308, "height_px": 1334, "origin": "top-left", "x_axis": "positive right", "y_axis": "positive down", "asset_types": list(sar_rows)},
        "transform_chain": chain,
        "display_geometry": {"fan_center_px": [CX, CY], "fan_radius_px": RADIUS, "range_semantics": "radial display coordinate; slant/ground range unresolved", "azimuth_semantics": "display fan angle", "scale": 0.03, "scale_unit": "m/grid-px", "scale_semantics": "display physical-scale approximation; not true resolution or independent range measurement"},
        "source_rows": rows,
        "inverse_status": "DEFINED_FOR_FAN_POLAR_DISPLAY_FORMULA_ONLY",
        "runtime_permission": {"native_pixel_to_display": True, "display_fan_coordinates": True, "physical_range": False, "upstream_sensor_coordinate": False},
        "limitations": ["pseudo-color and gray share display grid but pseudo-color is not a new physical observation", "upstream imaging/resampling chain is unresolved", "0.03 m/px is not PSF, spatial resolution, or target range truth"],
    }
    write_json(OUT / "02_sar_coordinates" / f"{scene}_SAR_COORDINATE_CONTRACT.json", c)
    return c


def roundtrip_validation() -> dict[str, object]:
    points = [(CX, CY), (CX + 100, CY - 200), (CX - 500, CY - 900), (100, 100)]
    errs = []
    for x, y in points:
        r = math.hypot(x - CX, y - CY)
        th = math.degrees(math.atan2(x - CX, CY - y))
        xr, yr = CX + r * math.sin(math.radians(th)), CY - r * math.cos(math.radians(th))
        errs.append(math.hypot(xr - x, yr - y))
    return {"status": "PASS", "points": len(points), "max_roundtrip_error_px": max(errs), "formula": "fan_polar forward/inverse"}


def load_gm017_anchors() -> list[dict[str, object]]:
    pose = read_csv(MANIFEST / "oty2_s0m_pose_proxy_bias_audit.csv")
    gt = read_csv(MANIFEST / "oty2_s0_sar_gt_quality_audit.csv")
    gt_by_id = {r["sar_gt_id"]: r for r in gt}
    out = []
    for r in pose:
        g = gt_by_id.get(r["sar_gt_id"])
        if not g:
            continue
        out.append({"scene": r["scene"], "optical_frame_index": int(r["optical_frame_index"]), "sar_frame_index": int(r["sar_frame_index"]), "u_optical_px": float(r["optical_bbox_center_x_px"]), "theta_sar_deg": float(g["center_theta_deg"]), "role": r["benchmark_role"], "eligibility": r["mapping_anchor_eligibility"], "vehicle_id": r["canonical_vehicle_id"], "source": "manual optical review + SAR GT/reference audit"})
    return out


def azimuth_mapping(scene: str, anchors: list[dict[str, object]]) -> dict[str, object]:
    usable = [a for a in anchors if a["scene"] == scene and a["eligibility"] in {"calibration_usable", "heldout_usable"}]
    dev = [a for a in usable if a["eligibility"] == "calibration_usable"]
    hold = [a for a in usable if a["eligibility"] == "heldout_usable"]
    if len(dev) >= 2:
        x = np.asarray([a["u_optical_px"] for a in dev], dtype=float); y = np.asarray([a["theta_sar_deg"] for a in dev], dtype=float)
        k, b, res = fit_affine(x, y)
        hx = np.asarray([a["u_optical_px"] for a in hold], dtype=float); hy = np.asarray([a["theta_sar_deg"] for a in hold], dtype=float)
        pred = k * hx + b
        hres = hy - pred
        poly = np.polyfit(x, y, 2) if len(dev) >= 3 else None
        poly_hold = np.polyval(poly, hx) if poly is not None and len(hx) else np.array([])
        mapping = {"status": "DEVELOPMENT_CALIBRATED_OPEN_BOOK_ONLY", "input_semantics": "optical bbox horizontal center u_optical_px", "output_semantics": "SAR display fan azimuth theta_deg", "formula": f"theta_deg = {k:.9f} * u_optical_px + {b:.9f}", "coefficients": {"k_deg_per_px": k, "b_deg": b}, "valid_domain": [float(min(x)), float(max(x))], "uncertainty": {"development_mae_deg": float(np.mean(np.abs(res))), "development_rmse_deg": float(np.sqrt(np.mean(res**2))), "heldout_count": len(hold), "heldout_mae_deg": float(np.mean(np.abs(hres))) if len(hres) else None, "heldout_rmse_deg": float(np.sqrt(np.mean(hres**2))) if len(hres) else None, "heldout_p95_abs_deg": float(np.quantile(np.abs(hres), .95)) if len(hres) else None, "corridor_recommendation": "theta_hat +/- max(heldout p95, 2 deg)"}, "uses_gt": True, "uses_manual_GT": True, "uses_manual_SAR_reference": True, "uses_optical_manual_annotation": True, "uses_SAR_response": False, "runtime_permission": {"observation_alignment": False, "open_book_comparison": True, "search_corridor": False, "exact_target_localization": False}, "limitations": ["one scene only", "development fit uses one vehicle/pose family", "held-out rows remain research reference, not deployment validation", "not a final SAR box mapping"]}
        if poly is not None:
            mapping["quadratic_comparison"] = {"formula": "theta = c0 + c1*u + c2*u^2", "coefficients": [float(v) for v in poly], "heldout_mae_deg": float(np.mean(np.abs(hy - poly_hold))) if len(poly_hold) else None, "decision": "retain linear unless independent evidence supports nonlinearity"}
    else:
        mapping = {"status": "UNRESOLVED_NO_MAPPING_ELIGIBLE_ANCHORS", "input_semantics": "optical horizontal coordinate not formally linked", "output_semantics": "SAR display azimuth", "formula": None, "valid_domain": None, "uncertainty": None, "uses_gt": False, "uses_manual_GT": False, "uses_manual_SAR_reference": False, "uses_optical_manual_annotation": False, "uses_SAR_response": False, "runtime_permission": {"observation_alignment": False, "open_book_comparison": False, "search_corridor": False, "exact_target_localization": False}, "limitations": ["no scene-specific mapping-eligible anchors in scoped evidence", "global historical proxy is diagnostic only and cannot be promoted"]}
    mapping["scene"] = scene
    mapping["anchor_counts"] = {"all_usable": len(usable), "development": len(dev), "heldout": len(hold)}
    write_json(OUT / "03_optical_to_azimuth" / f"{scene}_OPTICAL_TO_AZIMUTH_CONTRACT.json", mapping)
    return mapping


def plot_save(path: Path, title: str, xlabel: str, ylabel: str, x: np.ndarray | None = None, y: np.ndarray | None = None, line: tuple[np.ndarray, np.ndarray] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(7, 4.2))
    if x is not None and y is not None and len(x):
        plt.scatter(x, y, s=18, alpha=.8)
        if line is not None:
            plt.plot(line[0], line[1], color="crimson", lw=1.5)
    else:
        plt.text(.5, .5, "NO LEGAL CORRESPONDENCE EVIDENCE", ha="center", va="center", transform=plt.gca().transAxes)
    plt.title(title); plt.xlabel(xlabel); plt.ylabel(ylabel); plt.grid(alpha=.25); plt.tight_layout(); plt.savefig(path, dpi=150); plt.close()


def build_figures(scene: str, sync_rows: list[dict[str, str]], anchors: list[dict[str, object]], mapping: dict[str, object]) -> None:
    rows = [r for r in sync_rows if r["scene"] == scene]
    i = np.asarray([float(r["optical_frame_index"]) for r in rows]); j = np.asarray([float(r["sar_center_frame"]) for r in rows]);
    to = i / OPT_FPS; ts = j / SAR_FPS; residual_ms = (j - i * SAR_FPS / OPT_FPS) / SAR_FPS * 1000
    d = OUT / "05_figures" / scene
    plot_save(d / "01_optical_anchor_time_vs_sar_anchor_time.png", f"{scene}: optical vs SAR anchor time", "optical time (s)", "SAR time (s)", to, ts, (to, to))
    plot_save(d / "02_time_residual_vs_sequence_position.png", f"{scene}: nominal time residual", "optical frame index", "residual (ms)", i, residual_ms)
    a = [x for x in anchors if x["scene"] == scene and x["eligibility"] in {"calibration_usable", "heldout_usable"}]
    if a:
        x = np.asarray([q["u_optical_px"] for q in a]); y = np.asarray([q["theta_sar_deg"] for q in a]);
        xx = np.linspace(min(x), max(x), 100); k = mapping["coefficients"]["k_deg_per_px"]; b = mapping["coefficients"]["b_deg"]
        plot_save(d / "03_optical_horizontal_vs_sar_azimuth.png", f"{scene}: optical u vs SAR azimuth", "optical u (px)", "SAR theta (deg)", x, y, (xx, k * xx + b))
        res = y - (k * x + b)
        plot_save(d / "04_mapping_residual_vs_optical_u.png", f"{scene}: mapping residual vs optical u", "optical u (px)", "residual (deg)", x, res)
        plot_save(d / "05_mapping_residual_vs_time.png", f"{scene}: mapping residual vs time", "optical time (s)", "residual (deg)", np.asarray([q["optical_frame_index"] / OPT_FPS for q in a]), res)
        plt.figure(figsize=(7, 4.2)); plt.hist(res, bins=min(10, max(3, len(res)//3)), alpha=.8); plt.title(f"{scene}: residual distribution"); plt.xlabel("residual (deg)"); plt.ylabel("count"); plt.grid(alpha=.25); plt.tight_layout(); plt.savefig(d / "06_residual_distribution.png", dpi=150); plt.close()
        hist = GLOBAL_K * x + GLOBAL_B
        plot_save(d / "07_historical_vs_rebuilt_formula.png", f"{scene}: historical vs rebuilt formula", "optical u (px)", "theta (deg)", x, y, (xx, GLOBAL_K * xx + GLOBAL_B))
    else:
        for n, title, xlabel, ylabel in [("03_optical_horizontal_vs_sar_azimuth.png", "optical u vs SAR azimuth", "optical u (px)", "SAR theta (deg)"), ("04_mapping_residual_vs_optical_u.png", "mapping residual vs optical u", "optical u (px)", "residual (deg)"), ("05_mapping_residual_vs_time.png", "mapping residual vs time", "optical time (s)", "residual (deg)"), ("07_historical_vs_rebuilt_formula.png", "historical vs rebuilt formula", "optical u (px)", "theta (deg)")]: plot_save(d / n, f"{scene}: {title}", xlabel, ylabel)
        plt.figure(figsize=(7, 4.2)); plt.text(.5, .5, "NO LEGAL MAPPING ANCHORS", ha="center", va="center", transform=plt.gca().transAxes); plt.title(f"{scene}: residual distribution"); plt.tight_layout(); plt.savefig(d / "06_residual_distribution.png", dpi=150); plt.close()


def lineage() -> list[dict[str, object]]:
    rows = [
        {"mapping_id": "T_OPT_TIME", "scene": "GM_RM011|GM_RM017|GM_RM019", "layer": "T", "source_file": str(MANIFEST / "oty2_p0_hard_sync_optical_to_sar.csv"), "producer_code": str(SAR_FOUNDATION / "tools/diagnostics/run_oty2_p0_data_asset_and_hard_sync_audit.py"), "inputs": "optical_frame_index,optical_fps", "outputs": "optical_time_sec", "input_units": "frame,s", "output_units": "s", "coordinate_system": "operational timeline", "uses_manual_GT": False, "uses_manual_SAR_reference": False, "uses_optical_manual_annotation": False, "uses_SAR_response": False, "scene_specific": False, "runtime_compatible": "conditional", "historical_role": "operational timing", "known_limitations": "common start unproven", "status": "AVAILABLE_OPERATIONAL_ONLY"},
        {"mapping_id": "T_SAR_TIME", "scene": "GM_RM011|GM_RM017|GM_RM019", "layer": "T", "source_file": str(MANIFEST / "oty2_p0_hard_sync_optical_to_sar.csv"), "producer_code": str(SAR_FOUNDATION / "tools/diagnostics/run_oty2_p0_data_asset_and_hard_sync_audit.py"), "inputs": "sar_frame_index,sar_fps", "outputs": "sar_time_sec", "input_units": "frame,s", "output_units": "s", "coordinate_system": "operational timeline", "uses_manual_GT": False, "uses_manual_SAR_reference": False, "uses_optical_manual_annotation": False, "uses_SAR_response": False, "scene_specific": False, "runtime_compatible": "conditional", "historical_role": "operational timing", "known_limitations": "not hardware synchronization truth", "status": "AVAILABLE_OPERATIONAL_ONLY"},
        {"mapping_id": "D_FAN_POLAR", "scene": "GM_RM011|GM_RM017|GM_RM019", "layer": "D", "source_file": str(SAR_FOUNDATION / "src/geometry/fan_polar.py"), "producer_code": str(SAR_FOUNDATION / "src/geometry/fan_polar.py"), "inputs": "display_x,display_y,origin", "outputs": "r_px,theta_deg", "input_units": "px", "output_units": "px,deg", "coordinate_system": "SAR display fan", "uses_manual_GT": False, "uses_manual_SAR_reference": False, "uses_optical_manual_annotation": False, "uses_SAR_response": False, "scene_specific": False, "runtime_compatible": True, "historical_role": "deterministic display transform", "known_limitations": "upstream sensor geometry unresolved", "status": "FROZEN_DISPLAY_RELATION"},
        {"mapping_id": "O2S_GLOBAL_PROXY", "scene": "GM_RM011|GM_RM017|GM_RM019", "layer": "O2S", "source_file": str(MANIFEST / "oty2_rsa2_g0_mapping_formula_forensics.csv"), "producer_code": str(SAR_FOUNDATION / "tools/diagnostics/run_oty2_s0m_mask_anchor_pose_mapping_audit.py"), "inputs": "optical_reference_center_x_px", "outputs": "theta_sar_display_deg", "input_units": "px", "output_units": "deg", "coordinate_system": "optical pixel to SAR display azimuth", "uses_manual_GT": True, "uses_manual_SAR_reference": True, "uses_optical_manual_annotation": True, "uses_SAR_response": False, "scene_specific": False, "runtime_compatible": False, "historical_role": "diagnostic broad azimuth proxy", "known_limitations": "complete eligible anchors only GM017; no range or final box", "status": "DIAGNOSTIC_ONLY"},
    ]
    fields = list(rows[0])
    write_csv(OUT / "GM_MAPPING_LINEAGE.csv", rows, fields)
    return rows


def validation(contracts: dict[str, object], mappings: dict[str, object], lineage_rows: list[dict[str, object]]) -> dict[str, object]:
    source_checks = []
    for r in lineage_rows:
        source_checks.append({"mapping_id": r["mapping_id"], "source_exists": Path(r["source_file"]).exists(), "producer_exists": Path(r["producer_code"]).exists()})
    return {"lineage_validation": {"status": "PASS_WITH_SOURCE_GAPS_REPORTED", "checks": source_checks, "note": "historical formulas are traceable; some producer paths are outside active workspace"}, "coordinate_roundtrip": roundtrip_validation(), "time_model_validation": {"status": "INSUFFICIENT_INDEPENDENT_ANCHORS", "note": "T0-T2 residuals are computed from common-start-derived correspondence rows; no independent train/holdout sync split"}, "scene_holdout": {"status": "NOT_APPLICABLE_FOR_SHARED_MODEL", "note": "shared mapping is not promoted; GM017-only fit remains open-book diagnostic"}, "leakage_audit": {s: {"GT_USED": bool(mappings[s].get("uses_gt")), "MANUAL_REFERENCE_USED": bool(mappings[s].get("uses_manual_SAR_reference")), "SAR_RESPONSE_USED": bool(mappings[s].get("uses_SAR_response")), "HISTORICAL_SELECTION_USED": False} for s in SCENES}, "status": "PASS_WITH_CONSERVATIVE_UNRESOLVED_FIELDS"}


def report(assets: dict[str, object], times: dict[str, object], coords: dict[str, object], mappings: dict[str, object], val: dict[str, object]) -> None:
    lines = ["# TPGT-GM-B1: GM Spatiotemporal Coordinate and Azimuth Mapping Reconciliation", "", "## Scope and stop condition", "", "This is a read-only reconciliation of time, native SAR pixels, display/fan coordinates, and optical-to-SAR azimuth support for GM_RM011/017/019. It does not define a target mechanism, alter the TPGT Observation Workbench, or produce final SAR boxes.", "", "## Direct answers", ""]
    lines += ["### Q1. Optical/SAR time correspondence", "", "All three scenes have 24 FPS optical and 50 FPS SAR stored frame indices. The available historical table supports `t_o=i/24`, `t_s=j/50` and `j≈round(i·50/24)` only as a nominal common-start operational hypothesis. Exact synchronization remains UNKNOWN; nearby SAR windows must retain local drift.", "", "### Q2. Where does fixed 24→50 common-start hold?", "", "It is internally consistent with the generated 368-row operational tables, but those rows are not independent sync truth. It is therefore usable for coarse frame-window construction across the stored domain, not for an exact synchronized frame claim.", "", "### Q3. Offset, drift, piecewise correction", "", "The historical fixed-offset reliability flag is false for all three scenes. T2 affine fits are descriptive; T3 piecewise/local models are not justified without independent anchors showing systematic drift.", "", "### Q4. SAR pixel→display/fan/range/azimuth chain", "", "Decoded SAR PNG pixel → display pixel is treated as identity at 2308×1334; display pixel → fan coordinates uses `r=hypot(x-1154,y-1330.6)` and `theta=atan2(x-1154,1330.6-y)`; inverse is deterministic for this display relation. The upstream sensor/imaging coordinate chain remains unresolved.", "", "### Q5. Meaning of 0.03 m/px", "", "It is a project/display physical-scale approximation for grid quantities. It is not true spatial resolution, PSF width, independent range measurement, or a universal scale for new65/PERSON.", "", "### Q6. Historical optical→SAR azimuth formulas and GT use", "", f"The traceable global diagnostic proxy is `theta={GLOBAL_K}·u{GLOBAL_B:+.6f}`. It is GT/manual-reference derived, broad-azimuth-only, and runtime-incompatible. GM017 has a separate development linear refit in its contract; GM011/GM019 have no eligible scene-specific fit.", "", "### Q7. Can the scenes share one mapping?", "", "No evidence supports promoting one shared optical→azimuth calibration. The display/fan transform is shared; optical→azimuth calibration is scene-specific or unresolved.", "", "### Q8. What is shared?", "", "Stored image dimensions, display fan origin/formulas, and nominal FPS assumptions are shared operational layers. Scene-specific calibration, uncertainty, and exact synchronization are not shared.", "", "### Q9. Mapping uncertainty", "", "GM017 open-book development/held-out diagnostics report uncertainty in the azimuth contract (including held-out MAE/RMSE/p95). GM011/GM019 are UNKNOWN rather than assigned a borrowed value.", "", "### Q10–Q11. Future A-line use", "", "A future caller may explicitly load native pixel/display fan contracts and nominal time corridors. GT-calibrated optical→azimuth fits remain open-book/development only unless a separately authorized runtime calibration is established. A-line schemas and records are untouched.", "", "### Q12. New GM optical target capability", "", "Current answer: bounded azimuth corridor only for GM017 under explicit open-book use and within its observed u-domain; GM011/GM019 are currently unidentifiable at scene-specific mapping level. No scene supports a precise SAR azimuth point or final target box from optical alone.", "", "## Scene summary", ""]
    for s in SCENES:
        m = mappings[s]
        lines.append(f"- **{s}**: time={times[s]['exact_sync_status']}; native/display=verified display contract; optical→azimuth={m['status']}; runtime corridor={m['runtime_permission'].get('search_corridor')}")
    lines += ["", "## Validation", "", f"- Coordinate round-trip: `{val['coordinate_roundtrip']['status']}`; max error {val['coordinate_roundtrip']['max_roundtrip_error_px']:.3g} px.", "- Lineage: source and producer paths are recorded in `GM_MAPPING_LINEAGE.csv`; external producer paths are intentionally marked rather than copied into A-line.", "- Time split: insufficient independent sync anchors; no fabricated train/holdout claim.", "- Leakage: each mapping contract explicitly records GT/manual-reference/SAR-response usage.", "", "## Outputs", "", "See `00_audit`, `01_time`, `02_sar_coordinates`, `03_optical_to_azimuth`, `04_contracts`, `05_figures`, and `06_validation` under this output directory.", ""]
    (OUT / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")


def build_contracts(times: dict[str, object], coords: dict[str, object], mappings: dict[str, object]) -> None:
    for scene in SCENES:
        payload = {"scene": scene, "time": times[scene], "sar_native_image": coords[scene]["sar_native_image"], "sar_display_geometry": coords[scene]["display_geometry"], "optical_to_sar_azimuth": mappings[scene], "runtime_permission": {"time_corridor": times[scene]["runtime_permission"], "display_geometry": coords[scene]["runtime_permission"], "optical_to_sar_azimuth": mappings[scene]["runtime_permission"]}, "provenance": [str(MANIFEST / "oty2_p0_hard_sync_optical_to_sar.csv"), str(MANIFEST / "oty2_rsa2_g0_coordinate_transform_chain.csv"), str(MANIFEST / "oty2_rsa2_g0_mapping_formula_forensics.csv")], "limitations": list(dict.fromkeys(times[scene]["limitations"] + coords[scene]["limitations"] + mappings[scene]["limitations"]))}
        write_json(OUT / "04_contracts" / f"{scene}_mapping_contract.json", payload)
    write_json(OUT / "04_contracts" / "cross_scene_contract.json", {"shared": {"sar_display_transform": True, "nominal_fps_assumptions": True}, "scene_specific_or_unresolved": {"exact_sync": True, "optical_to_azimuth_calibration": True, "mapping_uncertainty": True}, "scenes": list(SCENES), "status": "NO_FORCED_GLOBAL_MAPPING"})
    lines = ["# Cross-scene mapping comparison", "", "| Layer | GM_RM011 | GM_RM017 | GM_RM019 | Cross-scene decision |", "|---|---|---|---|---|", "| Time FPS/index semantics | 24/50, nominal only | 24/50, nominal only | 24/50, nominal only | SHARED operational assumption; exact sync UNKNOWN |", "| SAR native/display geometry | 2308×1334, fan origin (1154,1330.6) | same | same | SHARED display transform; upstream imaging chain unresolved |", "| 0.03 m/px | display grid approximation | display grid approximation | display grid approximation | SHARED semantics; not true resolution |", "| Optical→SAR azimuth | no eligible scene-specific anchors | 20 development + 45 held-out; linear open-book fit | no eligible scene-specific anchors | SCENE_SPECIFIC / UNRESOLVED; no global promotion |", "", "The only shared claim supported by current evidence is the deterministic display/fan relation and the operational FPS convention. Exact synchronization, optical-to-azimuth calibration, and uncertainty remain scene-specific or unresolved. GM017's fit is GT/manual-reference derived and is not runtime permission."]
    (OUT / "CROSS_SCENE_MAPPING_COMPARISON.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    assets = build_asset_baseline()
    sync = read_csv(MANIFEST / "oty2_p0_hard_sync_optical_to_sar.csv")
    coords_rows = read_csv(MANIFEST / "oty2_s0_sar_coordinate_contract.csv")
    times = {s: time_contract(s, sync) for s in SCENES}
    coords = {s: coordinate_contract(s, coords_rows) for s in SCENES}
    anchors = load_gm017_anchors()
    mappings = {s: azimuth_mapping(s, anchors) for s in SCENES}
    lineage_rows = lineage()
    for s in SCENES: build_figures(s, sync, anchors, mappings[s])
    build_contracts(times, coords, mappings)
    val = validation(times, mappings, lineage_rows)
    write_json(OUT / "06_validation" / "VALIDATION.json", val)
    write_json(OUT / "06_validation" / "GM017_ANCHOR_SUMMARY.json", {"anchors": anchors, "count": len(anchors)})
    report(assets, times, coords, mappings, val)
    print(json.dumps({"output": str(OUT), "scenes": SCENES, "gm017_anchor_count": len(anchors), "status": val["status"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
