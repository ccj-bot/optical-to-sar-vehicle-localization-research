#!/usr/bin/env python
"""Phase5C-v0 post-hoc model diagnostic audit.

This audit evaluates frozen Phase5B-v0 proposals after generation. It may join
GT-like final boxes, condition labels, and A001 baseline outputs only for
post-hoc diagnosis. It does not regenerate proposals or change inference config.
"""

from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from statistics import mean, median
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

PROPOSAL_PATH = ROOT / "output" / "phase5B_first_diagnostic_run_v0_20260629_102746" / "proposal_candidates.csv"
PHASE4D_BASELINE_PATH = ROOT / "output" / "gm17_phase4D_candidate_pool_ceiling_audit_20260629_001655" / "candidate_pool_ceiling_per_target.csv"
A019_FINAL_PATH = ROOT / "output" / "hermes_annotation_consolidation_2026-05-20" / "00_tables" / "final_gt_working.csv"
A021_CONDITION_PATH = ROOT / "output" / "hermes_annotation_consolidation_2026-05-20" / "00_tables" / "visibility_condition_working.csv"
A001_BANK_PATH = ROOT / "output" / "clean_no_gt_localizer_2026-05-31_gm17_hard_candidate_expansion_v2" / "candidate_bank_inference.csv"

ROUTE_A = "shell_grid"
ROUTE_B = "energy_contrast_peak"
ROUTE_C = "connected_component"
SUBSETS = {
    "A_only": {ROUTE_A},
    "B_only": {ROUTE_B},
    "C_only": {ROUTE_C},
    "A_plus_B": {ROUTE_A, ROUTE_B},
    "A_plus_C": {ROUTE_A, ROUTE_C},
    "B_plus_C": {ROUTE_B, ROUTE_C},
    "A_plus_B_plus_C": {ROUTE_A, ROUTE_B, ROUTE_C},
}

CENTER_GOOD_PX = 10.0
IOU_GOOD = 0.5
CENTER_GAIN_EPS = 1.0
IOU_GAIN_EPS = 0.01


def norm_text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    if not path.exists():
        raise RuntimeError(f"required input not found: {path}")
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = [{k: norm_text(v) for k, v in row.items()} for row in reader]
        return rows, list(reader.fieldnames or [])


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def require_fields(name: str, header: list[str], fields: list[str]) -> None:
    missing = [field for field in fields if field not in header]
    if missing:
        raise RuntimeError(
            f"{name} missing required fields {missing}; available fields: {header}"
        )


def optional_fields(header: list[str], fields: list[str]) -> bool:
    return all(field in header for field in fields)


def to_float(row: dict[str, Any], field: str, target: str = "") -> float:
    text = norm_text(row.get(field))
    if text == "":
        label = f" for {target}" if target else ""
        raise RuntimeError(f"missing numeric field {field}{label}")
    try:
        return float(text)
    except ValueError as exc:
        label = f" for {target}" if target else ""
        raise RuntimeError(f"invalid numeric field {field}={text!r}{label}") from exc


def safe_float(row: dict[str, Any], field: str) -> float | None:
    text = norm_text(row.get(field))
    if text == "":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def center_error(cx1: float, cy1: float, cx2: float, cy2: float) -> float:
    return math.hypot(cx1 - cx2, cy1 - cy2)


def box_xyxy(cx: float, cy: float, w: float, h: float) -> tuple[float, float, float, float]:
    return cx - w / 2.0, cy - h / 2.0, cx + w / 2.0, cy + h / 2.0


def aabb_iou(box1: tuple[float, float, float, float], box2: tuple[float, float, float, float]) -> float:
    x11, y11, x12, y12 = box1
    x21, y21, x22, y22 = box2
    ix1 = max(x11, x21)
    iy1 = max(y11, y21)
    ix2 = min(x12, x22)
    iy2 = min(y12, y22)
    iw = max(0.0, ix2 - ix1)
    ih = max(0.0, iy2 - iy1)
    inter = iw * ih
    area1 = max(0.0, x12 - x11) * max(0.0, y12 - y11)
    area2 = max(0.0, x22 - x21) * max(0.0, y22 - y21)
    union = area1 + area2 - inter
    return inter / union if union > 0 else 0.0


def mean_or_blank(values: list[float]) -> float | str:
    return round(mean(values), 6) if values else ""


def median_or_blank(values: list[float]) -> float | str:
    return round(median(values), 6) if values else ""


def best_by_center(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not rows:
        return None
    return min(rows, key=lambda row: (float(row["center_error_to_final"]), -float(row["aabb_proxy_iou_to_final"])))


def best_by_iou(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not rows:
        return None
    return max(rows, key=lambda row: (float(row["aabb_proxy_iou_to_final"]), -float(row["center_error_to_final"])))


def subset_row(target_identity: str, subset_name: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    center_best = best_by_center(rows)
    iou_best = best_by_iou(rows)
    return {
        "target_identity": target_identity,
        "subset_name": subset_name,
        "proposal_count": len(rows),
        "best_center_error": round(float(center_best["center_error_to_final"]), 6) if center_best else "",
        "best_iou": round(float(iou_best["aabb_proxy_iou_to_final"]), 6) if iou_best else "",
        "best_center_proposal_id": center_best["proposal_id"] if center_best else "",
        "best_iou_proposal_id": iou_best["proposal_id"] if iou_best else "",
        "best_center_route": center_best["route_name"] if center_best else "",
        "best_iou_route": iou_best["route_name"] if iou_best else "",
    }


def num(row: dict[str, Any], field: str, default: float = math.nan) -> float:
    value = row.get(field)
    if value == "" or value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def label_route_contribution(b_gain: float, c_gain: float, bc_center: float, bc_iou: float, a_center: float, a_iou: float, abc_center: float, abc_iou: float) -> str:
    b_help = b_gain > CENTER_GAIN_EPS
    c_help = c_gain > IOU_GAIN_EPS
    synergy = bc_center > CENTER_GAIN_EPS or bc_iou > IOU_GAIN_EPS
    if b_help and c_help and synergy:
        return "energy_and_component_complementary"
    if b_help:
        return "energy_center_helpful"
    if c_help:
        return "component_extent_helpful"
    if math.isfinite(a_center) and math.isfinite(abc_center) and abs(a_center - abc_center) <= CENTER_GAIN_EPS and abs(abc_iou - a_iou) <= IOU_GAIN_EPS:
        return "prior_dominant"
    if (not math.isfinite(abc_center) or abc_center > 50.0) and abc_iou < 0.2:
        return "no_route_effective"
    return "mixed_or_unclear"


def case_type(phase5_center: float, phase5_iou: float, a001_center: float, a001_iou: float) -> str:
    p_center_good = phase5_center <= CENTER_GOOD_PX
    p_iou_good = phase5_iou >= IOU_GOOD
    a_center_good = a001_center <= CENTER_GOOD_PX
    a_iou_good = a001_iou >= IOU_GOOD
    center_delta = a001_center - phase5_center
    iou_delta = phase5_iou - a001_iou
    if (p_center_good or p_iou_good) and (a_center_good or a_iou_good):
        return "both_good"
    if (not p_center_good and not p_iou_good) and (not a_center_good and not a_iou_good):
        return "both_bad"
    if center_delta > CENTER_GAIN_EPS and iou_delta > IOU_GAIN_EPS:
        return "phase5B_better_center"
    if iou_delta > IOU_GAIN_EPS:
        return "phase5B_better_iou"
    if center_delta < -CENTER_GAIN_EPS and iou_delta < -IOU_GAIN_EPS:
        return "A001_better_center"
    if iou_delta < -IOU_GAIN_EPS:
        return "A001_better_iou"
    return "mixed"


def parse_flags(text: str) -> set[str]:
    return {part for part in norm_text(text).split("|") if part}


def problem_label_and_action(
    target_identity: str,
    contribution: dict[str, Any],
    compare: dict[str, Any],
    subset_by_name: dict[str, dict[str, Any]],
    best_phase5_row: dict[str, Any] | None,
    novelty_for_best: dict[str, Any] | None,
) -> tuple[str, str, str]:
    a_center = num(contribution, "A_best_center_error")
    a_iou = num(contribution, "A_best_iou")
    abc_center = num(contribution, "ABC_best_center_error")
    abc_iou = num(contribution, "ABC_best_iou")
    b_gain = num(contribution, "B_center_gain_over_A", 0.0)
    c_gain = num(contribution, "C_iou_gain_over_A", 0.0)
    delta_center = num(compare, "delta_center_error", 0.0)
    delta_iou = num(compare, "delta_iou", 0.0)
    route_label = contribution.get("route_contribution_label", "")

    flags = parse_flags(best_phase5_row.get("uncertainty_flags", "")) if best_phase5_row else set()
    outside = novelty_for_best and norm_text(novelty_for_best.get("outside_A001_neighborhood")).lower() == "true"

    if delta_center > CENTER_GAIN_EPS and delta_iou > IOU_GAIN_EPS and outside:
        return (
            "phase5B_adds_new_hypothesis",
            f"Phase5B improves A001 center by {delta_center:.3f}px and IoU by {delta_iou:.3f}; best proposal is outside A001 neighborhood.",
            "prepare_phase5D",
        )
    if delta_center < -CENTER_GAIN_EPS and delta_iou < -IOU_GAIN_EPS:
        return (
            "A001_still_stronger",
            f"A001 oracle is stronger by {-delta_center:.3f}px center and {-delta_iou:.3f} IoU.",
            "open_phase5B_v1",
        )
    if (abc_center > 50.0 and abc_iou < 0.2) and (a_center > 50.0 or a_iou < 0.2):
        return (
            "shell_limited",
            f"A/B/C all weak: A center={a_center:.3f}, A IoU={a_iou:.3f}, ABC center={abc_center:.3f}, ABC IoU={abc_iou:.3f}.",
            "rebuild_shell",
        )
    if b_gain > CENTER_GAIN_EPS:
        return (
            "sar_center_evidence_helpful",
            f"Energy route improves center over A by {b_gain:.3f}px.",
            "keep_energy_factor",
        )
    if c_gain > IOU_GAIN_EPS:
        return (
            "visible_extent_helpful",
            f"Component route improves IoU over A by {c_gain:.3f}.",
            "keep_visible_support_factor",
        )
    c_subset = subset_by_name.get("C_only", {})
    c_count = int(num(c_subset, "proposal_count", 0.0))
    if c_count > 0 and c_gain <= IOU_GAIN_EPS and ({"fragmented_component_set", "boundary_touching_component"} & flags):
        return (
            "component_fragmentation_or_clutter",
            "Connected components are present but do not improve IoU; best proposal carries fragmentation or boundary uncertainty.",
            "strengthen_sar_observation",
        )
    if route_label == "prior_dominant":
        return (
            "prior_dominant",
            "A-only is close to ABC; v0 mainly relies on optical/temporal prior support.",
            "inspect_sample_manually",
        )
    return (
        "mixed_or_unclear",
        "No single route or comparison dominates the diagnosis.",
        "inspect_sample_manually",
    )


def recommendation_from_counts(label_counts: Counter[str]) -> str:
    if label_counts.get("phase5B_adds_new_hypothesis", 0) >= 20:
        return "GO Phase5D + STRENGTHEN SAR OBSERVATION"
    if label_counts.get("A001_still_stronger", 0) > label_counts.get("phase5B_adds_new_hypothesis", 0):
        return "OPEN Phase5B-v1"
    if label_counts.get("shell_limited", 0) >= 20:
        return "REBUILD SHELL"
    if label_counts.get("sar_center_evidence_helpful", 0) + label_counts.get("visible_extent_helpful", 0) >= 30:
        return "HOLD Phase5D + STRENGTHEN SAR OBSERVATION"
    return "HOLD Phase5D + OPEN Phase5B-v1"


def nearest_a001(
    proposal: dict[str, Any],
    bank_rows: list[dict[str, str]],
    threshold_dist: float,
) -> dict[str, Any]:
    pcx = float(proposal["cx"])
    pcy = float(proposal["cy"])
    pw = float(proposal["w"])
    ph = float(proposal["h"])
    pbox = box_xyxy(pcx, pcy, pw, ph)
    best: dict[str, Any] | None = None
    for cand in bank_rows:
        ccx = to_float(cand, "cx", cand.get("target_identity", ""))
        ccy = to_float(cand, "cy", cand.get("target_identity", ""))
        cw = to_float(cand, "w", cand.get("target_identity", ""))
        ch = to_float(cand, "h", cand.get("target_identity", ""))
        dist = center_error(pcx, pcy, ccx, ccy)
        iou = aabb_iou(pbox, box_xyxy(ccx, ccy, cw, ch))
        if best is None or dist < best["nearest_A001_center_distance"]:
            best = {
                "nearest_A001_candidate_id": cand.get("candidate_id", ""),
                "nearest_A001_center_distance": dist,
                "nearest_A001_aabb_iou": iou,
            }
    if best is None:
        return {
            "nearest_A001_candidate_id": "",
            "nearest_A001_center_distance": "",
            "nearest_A001_aabb_iou": "",
            "outside_A001_neighborhood": "",
            "novelty_reason": "no_A001_candidates_for_target",
        }
    outside_dist = best["nearest_A001_center_distance"] > threshold_dist
    outside_iou = best["nearest_A001_aabb_iou"] < 0.5
    reasons = []
    if outside_dist:
        reasons.append("center_distance_gt_threshold")
    if outside_iou:
        reasons.append("nearest_iou_lt_0.5")
    best["outside_A001_neighborhood"] = bool(outside_dist or outside_iou)
    best["novelty_reason"] = "|".join(reasons) if reasons else "inside_A001_neighborhood"
    return best


def add_sample(
    samples: list[dict[str, Any]],
    seen: set[tuple[str, str]],
    bucket: str,
    target_identity: str,
    per_target_best: dict[str, dict[str, Any]],
    baseline: dict[str, dict[str, str]],
    reason: str,
    visual_check: str,
) -> None:
    key = (bucket, target_identity)
    if key in seen:
        return
    if sum(1 for row in samples if row["bucket"] == bucket) >= 10:
        return
    best = per_target_best.get(target_identity, {})
    base = baseline.get(target_identity, {})
    samples.append(
        {
            "bucket": bucket,
            "target_identity": target_identity,
            "scene": best.get("scene", base.get("scene", "")),
            "sar_frame_num": best.get("sar_frame_num", base.get("sar_frame_num", "")),
            "best_phase5B_proposal_id": best.get("best_center_proposal_id", ""),
            "best_route": best.get("best_center_route", ""),
            "phase5B_best_center_error": best.get("best_center_error", ""),
            "phase5B_best_iou": best.get("best_iou", ""),
            "A001_best_center_error": base.get("best_center_error", ""),
            "A001_best_iou": base.get("best_iou", ""),
            "key_reason": reason,
            "recommended_visual_check": visual_check,
        }
    )
    seen.add(key)


def main() -> None:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = ROOT / "output" / f"phase5C_v0_model_diagnostic_audit_{timestamp}"
    out_dir.mkdir(parents=True, exist_ok=False)

    proposals, proposal_header = read_csv(PROPOSAL_PATH)
    baseline_rows, baseline_header = read_csv(PHASE4D_BASELINE_PATH)
    final_rows, final_header = read_csv(A019_FINAL_PATH)

    require_fields("Phase5B proposals", proposal_header, [
        "proposal_id", "target_identity", "scene", "sar_frame_num", "cx", "cy", "w", "h",
        "route_name", "proposal_source", "route_rank", "uncertainty_flags", "pred_w", "pred_h",
    ])
    require_fields("A001 Phase4D baseline", baseline_header, [
        "target_identity", "scene", "sar_frame_num", "best_iou", "best_center_error", "failure_class",
    ])
    require_fields("A019 final boxes", final_header, [
        "target_identity", "final_cx", "final_cy", "final_w", "final_h",
    ])

    condition_rows: list[dict[str, str]] = []
    condition_header: list[str] = []
    a021_joined = False
    condition_available = A021_CONDITION_PATH.exists()
    if condition_available:
        condition_rows, condition_header = read_csv(A021_CONDITION_PATH)
        if optional_fields(condition_header, ["target_identity", "condition_type", "condition_degree", "truncation_degree", "occlusion_degree"]):
            a021_joined = True

    bank_available = A001_BANK_PATH.exists()
    bank_rows: list[dict[str, str]] = []
    bank_header: list[str] = []
    a001_novelty_available = False
    if bank_available:
        bank_rows, bank_header = read_csv(A001_BANK_PATH)
        if optional_fields(bank_header, ["target_identity", "candidate_id", "cx", "cy", "w", "h"]):
            a001_novelty_available = True

    final_by_target = {row["target_identity"]: row for row in final_rows if row.get("target_identity")}
    baseline_by_target = {row["target_identity"]: row for row in baseline_rows if row.get("target_identity")}
    condition_by_target = {row["target_identity"]: row for row in condition_rows if row.get("target_identity")} if a021_joined else {}
    bank_by_target: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    if a001_novelty_available:
        for row in bank_rows:
            bank_by_target[row["target_identity"]].append(row)

    target_ids = sorted({row["target_identity"] for row in proposals})
    missing_final = sorted([target for target in target_ids if target not in final_by_target])
    missing_baseline = sorted([target for target in target_ids if target not in baseline_by_target])
    if missing_final:
        raise RuntimeError(f"A019 final boxes missing for {len(missing_final)} targets; examples: {missing_final[:10]}")
    if missing_baseline:
        raise RuntimeError(f"A001 baseline missing for {len(missing_baseline)} targets; examples: {missing_baseline[:10]}")

    proposal_count_by_target = Counter(row["target_identity"] for row in proposals)
    eval_rows: list[dict[str, Any]] = []
    for row in proposals:
        target = row["target_identity"]
        final = final_by_target[target]
        pcx = to_float(row, "cx", target)
        pcy = to_float(row, "cy", target)
        pw = to_float(row, "w", target)
        ph = to_float(row, "h", target)
        fcx = to_float(final, "final_cx", target)
        fcy = to_float(final, "final_cy", target)
        fw = to_float(final, "final_w", target)
        fh = to_float(final, "final_h", target)
        ce = center_error(pcx, pcy, fcx, fcy)
        iou = aabb_iou(box_xyxy(pcx, pcy, pw, ph), box_xyxy(fcx, fcy, fw, fh))
        eval_rows.append(
            {
                **{field: row.get(field, "") for field in [
                    "proposal_id", "target_identity", "scene", "sar_frame_num", "gm17_track_id",
                    "cx", "cy", "w", "h", "theta", "proposal_source", "route_name", "route_config_id",
                    "route_rank", "uncertainty_flags", "pred_cx", "pred_cy", "pred_w", "pred_h",
                    "selected_image_source_id",
                ]},
                "final_cx": final["final_cx"],
                "final_cy": final["final_cy"],
                "final_w": final["final_w"],
                "final_h": final["final_h"],
                "center_error_to_final": round(ce, 6),
                "aabb_proxy_iou_to_final": round(iou, 6),
                "proposal_count_for_target": proposal_count_by_target[target],
                "phase5C_metric_boundary": "post_hoc_eval_only_not_phase5B_generation",
            }
        )

    eval_by_target: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    eval_by_id: dict[str, dict[str, Any]] = {}
    for row in eval_rows:
        eval_by_target[row["target_identity"]].append(row)
        eval_by_id[row["proposal_id"]] = row

    subset_rows: list[dict[str, Any]] = []
    subset_by_target: defaultdict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for target in target_ids:
        target_rows = eval_by_target[target]
        for subset_name, routes in SUBSETS.items():
            rows = [row for row in target_rows if row["route_name"] in routes]
            srow = subset_row(target, subset_name, rows)
            subset_rows.append(srow)
            subset_by_target[target][subset_name] = srow

    contribution_rows: list[dict[str, Any]] = []
    for target in target_ids:
        s = subset_by_target[target]
        a = s["A_only"]
        ab = s["A_plus_B"]
        ac = s["A_plus_C"]
        abc = s["A_plus_B_plus_C"]
        a_center = num(a, "best_center_error")
        a_iou = num(a, "best_iou", 0.0)
        ab_center = num(ab, "best_center_error")
        ac_iou = num(ac, "best_iou", 0.0)
        abc_center = num(abc, "best_center_error")
        abc_iou = num(abc, "best_iou", 0.0)
        b_gain = a_center - ab_center
        c_gain = ac_iou - a_iou
        bc_center_gain = min(ab_center, num(ac, "best_center_error")) - abc_center
        bc_iou_gain = abc_iou - max(num(ab, "best_iou", 0.0), ac_iou)
        label = label_route_contribution(b_gain, c_gain, bc_center_gain, bc_iou_gain, a_center, a_iou, abc_center, abc_iou)
        contribution_rows.append(
            {
                "target_identity": target,
                "A_best_center_error": round(a_center, 6),
                "A_best_iou": round(a_iou, 6),
                "AB_best_center_error": round(ab_center, 6),
                "AC_best_iou": round(ac_iou, 6),
                "ABC_best_center_error": round(abc_center, 6),
                "ABC_best_iou": round(abc_iou, 6),
                "B_center_gain_over_A": round(b_gain, 6),
                "C_iou_gain_over_A": round(c_gain, 6),
                "BC_synergy_center_gain": round(bc_center_gain, 6),
                "BC_synergy_iou_gain": round(bc_iou_gain, 6),
                "route_contribution_label": label,
            }
        )

    contribution_by_target = {row["target_identity"]: row for row in contribution_rows}
    abc_by_target = {target: subset_by_target[target]["A_plus_B_plus_C"] for target in target_ids}
    vs_a001_rows: list[dict[str, Any]] = []
    for target in target_ids:
        abc = abc_by_target[target]
        base = baseline_by_target[target]
        phase5_center = num(abc, "best_center_error")
        phase5_iou = num(abc, "best_iou", 0.0)
        a001_center = to_float(base, "best_center_error", target)
        a001_iou = to_float(base, "best_iou", target)
        delta_center = a001_center - phase5_center
        delta_iou = phase5_iou - a001_iou
        vs_a001_rows.append(
            {
                "target_identity": target,
                "phase5B_best_center_error": round(phase5_center, 6),
                "phase5B_best_iou": round(phase5_iou, 6),
                "phase5B_best_center_route": abc["best_center_route"],
                "phase5B_best_iou_route": abc["best_iou_route"],
                "A001_best_center_error": round(a001_center, 6),
                "A001_best_iou": round(a001_iou, 6),
                "delta_center_error": round(delta_center, 6),
                "delta_iou": round(delta_iou, 6),
                "case_type": case_type(phase5_center, phase5_iou, a001_center, a001_iou),
                "phase5C_metric_boundary": "post_hoc_eval_only_not_phase5B_generation",
            }
        )

    vs_by_target = {row["target_identity"]: row for row in vs_a001_rows}

    novelty_rows: list[dict[str, Any]] = []
    novelty_by_proposal: dict[str, dict[str, Any]] = {}
    if a001_novelty_available:
        for row in eval_rows:
            target = row["target_identity"]
            pred_w = safe_float(row, "pred_w") or float(row["w"])
            pred_h = safe_float(row, "pred_h") or float(row["h"])
            threshold_dist = max(10.0, 0.25 * math.hypot(pred_w, pred_h))
            nearest = nearest_a001(row, bank_by_target.get(target, []), threshold_dist)
            nrow = {
                "proposal_id": row["proposal_id"],
                "target_identity": target,
                "route_name": row["route_name"],
                "nearest_A001_candidate_id": nearest["nearest_A001_candidate_id"],
                "nearest_A001_center_distance": round(float(nearest["nearest_A001_center_distance"]), 6) if nearest["nearest_A001_center_distance"] != "" else "",
                "nearest_A001_aabb_iou": round(float(nearest["nearest_A001_aabb_iou"]), 6) if nearest["nearest_A001_aabb_iou"] != "" else "",
                "outside_A001_neighborhood": str(nearest["outside_A001_neighborhood"]).lower() if nearest["outside_A001_neighborhood"] != "" else "",
                "novelty_reason": nearest["novelty_reason"],
            }
            novelty_rows.append(nrow)
            novelty_by_proposal[row["proposal_id"]] = nrow

    problem_rows: list[dict[str, Any]] = []
    for target in target_ids:
        abc = abc_by_target[target]
        best_phase5 = eval_by_id.get(abc.get("best_center_proposal_id", "")) or eval_by_id.get(abc.get("best_iou_proposal_id", ""))
        novelty = novelty_by_proposal.get(best_phase5["proposal_id"]) if best_phase5 else None
        label, evidence, action = problem_label_and_action(
            target,
            contribution_by_target[target],
            vs_by_target[target],
            subset_by_target[target],
            best_phase5,
            novelty,
        )
        problem_rows.append(
            {
                "target_identity": target,
                "problem_attribution_label": label,
                "evidence_summary": evidence,
                "recommended_next_action": action,
            }
        )
    problem_by_target = {row["target_identity"]: row for row in problem_rows}

    samples: list[dict[str, Any]] = []
    seen_samples: set[tuple[str, str]] = set()
    per_target_best = {
        target: {
            **abc_by_target[target],
            "scene": baseline_by_target[target].get("scene", ""),
            "sar_frame_num": baseline_by_target[target].get("sar_frame_num", ""),
        }
        for target in target_ids
    }

    for row in sorted(vs_a001_rows, key=lambda r: (-num(r, "delta_iou", 0.0), -num(r, "delta_center_error", 0.0))):
        if num(row, "delta_iou", 0.0) > IOU_GAIN_EPS or num(row, "delta_center_error", 0.0) > CENTER_GAIN_EPS:
            add_sample(samples, seen_samples, "A001_bad_Phase5B_good", row["target_identity"], per_target_best, baseline_by_target, "Phase5B ABC ceiling improves over A001.", "Inspect best Phase5B hypothesis against A001 oracle geometry.")
    for row in sorted(vs_a001_rows, key=lambda r: (num(r, "delta_iou", 0.0), num(r, "delta_center_error", 0.0))):
        if num(row, "delta_iou", 0.0) < -IOU_GAIN_EPS or num(row, "delta_center_error", 0.0) < -CENTER_GAIN_EPS:
            add_sample(samples, seen_samples, "Phase5B_bad_A001_good", row["target_identity"], per_target_best, baseline_by_target, "A001 oracle ceiling is stronger than Phase5B.", "Inspect whether v0 shell or observation missed A001-like support.")
    for row in sorted(contribution_rows, key=lambda r: -num(r, "B_center_gain_over_A", 0.0)):
        if num(row, "B_center_gain_over_A", 0.0) > CENTER_GAIN_EPS:
            add_sample(samples, seen_samples, "RouteB_center_rescue", row["target_identity"], per_target_best, baseline_by_target, "Energy route improves center over A-only.", "Check whether peak is vehicle evidence or clutter.")
    for row in sorted(contribution_rows, key=lambda r: -num(r, "C_iou_gain_over_A", 0.0)):
        if num(row, "C_iou_gain_over_A", 0.0) > IOU_GAIN_EPS:
            add_sample(samples, seen_samples, "RouteC_extent_rescue", row["target_identity"], per_target_best, baseline_by_target, "Component route improves IoU over A-only.", "Check whether component support matches visible SAR extent.")
    for row in problem_rows:
        if row["problem_attribution_label"] == "shell_limited":
            add_sample(samples, seen_samples, "shell_limited_failures", row["target_identity"], per_target_best, baseline_by_target, row["evidence_summary"], "Inspect A005 proxy shell placement and crop coverage.")
    for row in problem_rows:
        if row["problem_attribution_label"] == "component_fragmentation_or_clutter":
            add_sample(samples, seen_samples, "component_clutter_or_fragmentation", row["target_identity"], per_target_best, baseline_by_target, row["evidence_summary"], "Inspect connected-component fragmentation, boundary contact, and clutter merge.")
    if novelty_rows:
        best_ids = {abc_by_target[target]["best_iou_proposal_id"] for target in target_ids} | {abc_by_target[target]["best_center_proposal_id"] for target in target_ids}
        outside_best = [row for row in novelty_rows if row["proposal_id"] in best_ids and row["outside_A001_neighborhood"] == "true"]
        outside_best.sort(key=lambda row: -num(vs_by_target[row["target_identity"]], "delta_iou", 0.0))
        for row in outside_best:
            add_sample(samples, seen_samples, "outside_A001_high_quality_proposals", row["target_identity"], per_target_best, baseline_by_target, "Best Phase5B proposal is outside A001 neighborhood.", "Inspect whether this is a true new state hypothesis.")

    condition_breakdown_rows: list[dict[str, Any]] = []
    if a021_joined:
        groups: defaultdict[str, list[str]] = defaultdict(list)
        for target in target_ids:
            cond = condition_by_target.get(target, {})
            key = "|".join(
                [
                    cond.get("condition_type", "missing"),
                    cond.get("condition_degree", ""),
                    cond.get("truncation_degree", ""),
                    cond.get("occlusion_degree", ""),
                ]
            )
            groups[key].append(target)
        for key, targets in sorted(groups.items()):
            phase5_centers = [num(vs_by_target[t], "phase5B_best_center_error") for t in targets]
            phase5_ious = [num(vs_by_target[t], "phase5B_best_iou", 0.0) for t in targets]
            a001_centers = [num(vs_by_target[t], "A001_best_center_error") for t in targets]
            a001_ious = [num(vs_by_target[t], "A001_best_iou", 0.0) for t in targets]
            phase5_better_count = sum(
                1
                for t in targets
                if num(vs_by_target[t], "delta_center_error", 0.0) > CENTER_GAIN_EPS or num(vs_by_target[t], "delta_iou", 0.0) > IOU_GAIN_EPS
            )
            a001_better_count = sum(
                1
                for t in targets
                if num(vs_by_target[t], "delta_center_error", 0.0) < -CENTER_GAIN_EPS or num(vs_by_target[t], "delta_iou", 0.0) < -IOU_GAIN_EPS
            )
            dominant_problem = Counter(problem_by_target[t]["problem_attribution_label"] for t in targets).most_common(1)[0][0]
            condition_breakdown_rows.append(
                {
                    "condition_group": key,
                    "target_count": len(targets),
                    "mean_phase5B_best_center_error": mean_or_blank(phase5_centers),
                    "median_phase5B_best_center_error": median_or_blank(phase5_centers),
                    "mean_phase5B_best_iou": mean_or_blank(phase5_ious),
                    "median_phase5B_best_iou": median_or_blank(phase5_ious),
                    "mean_A001_best_center_error": mean_or_blank(a001_centers),
                    "median_A001_best_center_error": median_or_blank(a001_centers),
                    "mean_A001_best_iou": mean_or_blank(a001_ious),
                    "median_A001_best_iou": median_or_blank(a001_ious),
                    "phase5B_better_count": phase5_better_count,
                    "A001_better_count": a001_better_count,
                    "dominant_problem_attribution": dominant_problem,
                }
            )

    proposal_eval_fields = [
        "proposal_id", "target_identity", "scene", "sar_frame_num", "gm17_track_id",
        "cx", "cy", "w", "h", "theta", "proposal_source", "route_name", "route_config_id",
        "final_cx", "final_cy", "final_w", "final_h", "center_error_to_final", "aabb_proxy_iou_to_final",
        "proposal_count_for_target", "route_rank", "uncertainty_flags", "pred_cx", "pred_cy", "pred_w", "pred_h",
        "selected_image_source_id", "phase5C_metric_boundary",
    ]
    subset_fields = [
        "target_identity", "subset_name", "proposal_count", "best_center_error", "best_iou",
        "best_center_proposal_id", "best_iou_proposal_id", "best_center_route", "best_iou_route",
    ]
    contribution_fields = [
        "target_identity", "A_best_center_error", "A_best_iou", "AB_best_center_error",
        "AC_best_iou", "ABC_best_center_error", "ABC_best_iou", "B_center_gain_over_A",
        "C_iou_gain_over_A", "BC_synergy_center_gain", "BC_synergy_iou_gain", "route_contribution_label",
    ]
    vs_fields = [
        "target_identity", "phase5B_best_center_error", "phase5B_best_iou",
        "phase5B_best_center_route", "phase5B_best_iou_route", "A001_best_center_error",
        "A001_best_iou", "delta_center_error", "delta_iou", "case_type", "phase5C_metric_boundary",
    ]
    problem_fields = ["target_identity", "problem_attribution_label", "evidence_summary", "recommended_next_action"]
    sample_fields = [
        "bucket", "target_identity", "scene", "sar_frame_num", "best_phase5B_proposal_id",
        "best_route", "phase5B_best_center_error", "phase5B_best_iou", "A001_best_center_error",
        "A001_best_iou", "key_reason", "recommended_visual_check",
    ]
    condition_fields = [
        "condition_group", "target_count", "mean_phase5B_best_center_error", "median_phase5B_best_center_error",
        "mean_phase5B_best_iou", "median_phase5B_best_iou", "mean_A001_best_center_error",
        "median_A001_best_center_error", "mean_A001_best_iou", "median_A001_best_iou",
        "phase5B_better_count", "A001_better_count", "dominant_problem_attribution",
    ]
    novelty_fields = [
        "proposal_id", "target_identity", "route_name", "nearest_A001_candidate_id",
        "nearest_A001_center_distance", "nearest_A001_aabb_iou", "outside_A001_neighborhood", "novelty_reason",
    ]

    write_csv(out_dir / "phase5C_v0_proposal_eval.csv", eval_rows, proposal_eval_fields)
    write_csv(out_dir / "phase5C_v0_route_subset_ceiling_per_target.csv", subset_rows, subset_fields)
    write_csv(out_dir / "phase5C_v0_route_contribution_per_target.csv", contribution_rows, contribution_fields)
    write_csv(out_dir / "phase5C_v0_vs_A001_per_target.csv", vs_a001_rows, vs_fields)
    write_csv(out_dir / "phase5C_v0_problem_attribution_per_target.csv", problem_rows, problem_fields)
    write_csv(out_dir / "phase5C_v0_interesting_samples.csv", samples, sample_fields)
    write_csv(out_dir / "phase5C_v0_condition_breakdown.csv", condition_breakdown_rows, condition_fields)
    if a001_novelty_available:
        write_csv(out_dir / "phase5C_v0_a001_neighborhood_novelty.csv", novelty_rows, novelty_fields)

    phase5_centers = [num(row, "phase5B_best_center_error") for row in vs_a001_rows]
    phase5_ious = [num(row, "phase5B_best_iou", 0.0) for row in vs_a001_rows]
    a001_centers = [num(row, "A001_best_center_error") for row in vs_a001_rows]
    a001_ious = [num(row, "A001_best_iou", 0.0) for row in vs_a001_rows]
    phase5_better_count = sum(1 for row in vs_a001_rows if num(row, "delta_center_error", 0.0) > CENTER_GAIN_EPS or num(row, "delta_iou", 0.0) > IOU_GAIN_EPS)
    a001_better_count = sum(1 for row in vs_a001_rows if num(row, "delta_center_error", 0.0) < -CENTER_GAIN_EPS or num(row, "delta_iou", 0.0) < -IOU_GAIN_EPS)
    route_label_counts = Counter(row["route_contribution_label"] for row in contribution_rows)
    problem_counts = Counter(row["problem_attribution_label"] for row in problem_rows)
    action_counts = Counter(row["recommended_next_action"] for row in problem_rows)
    case_counts = Counter(row["case_type"] for row in vs_a001_rows)
    sample_bucket_counts = Counter(row["bucket"] for row in samples)
    subset_summary = {}
    for subset_name in SUBSETS:
        subset_targets = [row for row in subset_rows if row["subset_name"] == subset_name]
        subset_summary[subset_name] = {
            "mean_best_center_error": mean_or_blank([num(row, "best_center_error") for row in subset_targets if row["best_center_error"] != ""]),
            "median_best_center_error": median_or_blank([num(row, "best_center_error") for row in subset_targets if row["best_center_error"] != ""]),
            "mean_best_iou": mean_or_blank([num(row, "best_iou", 0.0) for row in subset_targets if row["best_iou"] != ""]),
            "median_best_iou": median_or_blank([num(row, "best_iou", 0.0) for row in subset_targets if row["best_iou"] != ""]),
        }

    recommendation = recommendation_from_counts(problem_counts)
    summary = {
        "timestamp": timestamp,
        "target_count": len(target_ids),
        "proposal_count": len(proposals),
        "A019_joined": True,
        "A021_joined": a021_joined,
        "A001_baseline_joined": True,
        "A001_neighborhood_novelty_available": a001_novelty_available,
        "phase5B_ABC_ceiling": {
            "mean_center_error": mean_or_blank(phase5_centers),
            "median_center_error": median_or_blank(phase5_centers),
            "mean_iou": mean_or_blank(phase5_ious),
            "median_iou": median_or_blank(phase5_ious),
        },
        "A001_ceiling": {
            "mean_center_error": mean_or_blank(a001_centers),
            "median_center_error": median_or_blank(a001_centers),
            "mean_iou": mean_or_blank(a001_ious),
            "median_iou": median_or_blank(a001_ious),
        },
        "phase5B_better_count": phase5_better_count,
        "A001_better_count": a001_better_count,
        "case_type_counts": dict(case_counts),
        "route_subset_summary": subset_summary,
        "route_contribution_label_counts": dict(route_label_counts),
        "problem_attribution_counts": dict(problem_counts),
        "recommended_next_action_counts": dict(action_counts),
        "interesting_sample_bucket_counts": dict(sample_bucket_counts),
        "recommendation": recommendation,
        "boundary_assertions": {
            "post_hoc_only": True,
            "phase5B_v0_config_changed": False,
            "proposals_regenerated": False,
            "c3_c4_integration": False,
            "threshold_tuning": False,
            "training": False,
            "calibration": False,
            "push": False,
        },
    }
    write_json(out_dir / "phase5C_v0_diagnostic_summary.json", summary)

    audit_log = {
        "timestamp": timestamp,
        "inputs": {
            "proposals": rel(PROPOSAL_PATH),
            "A001_phase4D_baseline": rel(PHASE4D_BASELINE_PATH),
            "A019_final_boxes": rel(A019_FINAL_PATH),
            "A021_condition_labels": rel(A021_CONDITION_PATH) if condition_available else "",
            "A001_candidate_bank": rel(A001_BANK_PATH) if bank_available else "",
        },
        "field_mapping": {
            "proposal_box": ["cx", "cy", "w", "h"],
            "final_box": ["final_cx", "final_cy", "final_w", "final_h"],
            "baseline": ["best_iou", "best_center_error", "failure_class"],
            "condition": ["condition_type", "condition_degree", "truncation_degree", "occlusion_degree"] if a021_joined else [],
        },
        "headers": {
            "proposal_header": proposal_header,
            "baseline_header": baseline_header,
            "A019_header": final_header,
            "A021_header": condition_header,
            "A001_bank_header": bank_header,
        },
        "boundary": summary["boundary_assertions"],
    }
    write_json(out_dir / "phase5C_v0_audit_log.json", audit_log)

    docs_path = ROOT / "docs" / f"phase5C_v0_model_diagnostic_audit_summary_{timestamp}.md"
    route_lines = "\n".join(
        f"- `{name}`: mean center `{vals['mean_best_center_error']}`, median center `{vals['median_best_center_error']}`, mean IoU `{vals['mean_best_iou']}`, median IoU `{vals['median_best_iou']}`"
        for name, vals in subset_summary.items()
    )
    problem_lines = "\n".join(f"- `{label}`: {count}" for label, count in problem_counts.most_common())
    action_lines = "\n".join(f"- `{label}`: {count}" for label, count in action_counts.most_common())
    bucket_lines = "\n".join(f"- `{label}`: {count}" for label, count in sample_bucket_counts.most_common())
    docs_text = f"""# Phase5C-v0 Model Diagnostic Audit Summary

Date: {timestamp}

## Purpose

Phase5C-v0 is a post-hoc model diagnostic audit. It evaluates frozen Phase5B-v0 proposals after generation and does not modify Phase5B-v0 config, regenerate proposals, tune thresholds, train, calibrate, or integrate anything into C3/C4.

## Inputs

- Phase5B-v0 proposals: `{rel(PROPOSAL_PATH)}`
- A001 / Phase4D baseline: `{rel(PHASE4D_BASELINE_PATH)}`
- A019 final boxes: `{rel(A019_FINAL_PATH)}`
- A021 condition labels: `{rel(A021_CONDITION_PATH) if a021_joined else 'unavailable or unmapped'}`
- A001 candidate bank for novelty: `{rel(A001_BANK_PATH) if a001_novelty_available else 'unavailable or unmapped'}`

All A019/A021/A001 oracle fields are post-hoc evaluation inputs only. They were not used for Phase5B generation.

## Overall Result

- Target count: {len(target_ids)}
- Proposal count: {len(proposals)}
- Phase5B ABC mean / median center error: {summary['phase5B_ABC_ceiling']['mean_center_error']} / {summary['phase5B_ABC_ceiling']['median_center_error']}
- Phase5B ABC mean / median IoU: {summary['phase5B_ABC_ceiling']['mean_iou']} / {summary['phase5B_ABC_ceiling']['median_iou']}
- A001 mean / median center error: {summary['A001_ceiling']['mean_center_error']} / {summary['A001_ceiling']['median_center_error']}
- A001 mean / median IoU: {summary['A001_ceiling']['mean_iou']} / {summary['A001_ceiling']['median_iou']}
- Phase5B better count: {phase5_better_count}
- A001 better count: {a001_better_count}

## Route Diagnosis

{route_lines}

Route contribution labels:

{chr(10).join(f'- `{label}`: {count}' for label, count in route_label_counts.most_common())}

## Problem Attribution

{problem_lines}

Top recommended next actions:

{action_lines}

## Interesting Sample Buckets

{bucket_lines}

See `{rel(out_dir / 'phase5C_v0_interesting_samples.csv')}`.

## Interpretation

- Prior shell usefulness is diagnosed by `A_only` and its gap to `A_plus_B_plus_C`.
- SAR center evidence is diagnosed by `B_center_gain_over_A`.
- Visible support is diagnosed by `C_iou_gain_over_A`.
- Novel hypotheses beyond A001 are diagnosed by the optional A001-neighborhood file when available.
- Failure attribution separates shell limitation, weak SAR center evidence, visible-support value, component fragmentation/clutter, Phase5B novelty, and A001 superiority.

## Recommendation

{recommendation}

## Boundary

- Post-hoc only.
- Phase5B v0 config not changed.
- Proposals not regenerated.
- No C3/C4 integration.
- No threshold tuning.
- No training.
- No calibration.
- No push.
"""
    docs_path.write_text(docs_text, encoding="utf-8")

    print(
        json.dumps(
            {
                "output_dir": rel(out_dir),
                "docs_summary": rel(docs_path),
                "target_count": len(target_ids),
                "proposal_count": len(proposals),
                "A019_joined": True,
                "A021_joined": a021_joined,
                "A001_baseline_joined": True,
                "phase5B_ABC_mean_center_error": summary["phase5B_ABC_ceiling"]["mean_center_error"],
                "phase5B_ABC_median_center_error": summary["phase5B_ABC_ceiling"]["median_center_error"],
                "phase5B_ABC_mean_iou": summary["phase5B_ABC_ceiling"]["mean_iou"],
                "phase5B_ABC_median_iou": summary["phase5B_ABC_ceiling"]["median_iou"],
                "A001_mean_center_error": summary["A001_ceiling"]["mean_center_error"],
                "A001_median_center_error": summary["A001_ceiling"]["median_center_error"],
                "A001_mean_iou": summary["A001_ceiling"]["mean_iou"],
                "A001_median_iou": summary["A001_ceiling"]["median_iou"],
                "phase5B_better_count": phase5_better_count,
                "A001_better_count": a001_better_count,
                "top_problem_attribution": problem_counts.most_common(5),
                "recommendation": recommendation,
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
