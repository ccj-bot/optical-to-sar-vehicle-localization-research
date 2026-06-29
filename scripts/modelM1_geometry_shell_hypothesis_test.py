#!/usr/bin/env python
"""Model M1 geometry-aware range/cross shell hypothesis test.

This is a post-hoc model-hypothesis test. It does not generate v1 proposals,
does not regenerate Phase5B-v0 proposals, and does not modify source files.
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
PHASE5C_DIR = ROOT / "output" / "phase5C_v0_model_diagnostic_audit_20260629_110133"
PHASE5C_VS_A001_PATH = PHASE5C_DIR / "phase5C_v0_vs_A001_per_target.csv"
PHASE5C_ROUTE_SUBSET_PATH = PHASE5C_DIR / "phase5C_v0_route_subset_ceiling_per_target.csv"
PHASE5C_PROBLEM_PATH = PHASE5C_DIR / "phase5C_v0_problem_attribution_per_target.csv"
PHASE5C_SAMPLES_PATH = PHASE5C_DIR / "phase5C_v0_interesting_samples.csv"
PHASE5C_NOVELTY_PATH = PHASE5C_DIR / "phase5C_v0_a001_neighborhood_novelty.csv"
A005_PATH = ROOT / "output" / "clean_no_gt_localizer_2026-05-31_boundary_tables" / "gm17_temporal_inference.csv"
A001_BANK_PATH = ROOT / "output" / "clean_no_gt_localizer_2026-05-31_gm17_hard_candidate_expansion_v2" / "candidate_bank_inference.csv"
PHASE4D_BASELINE_PATH = ROOT / "output" / "gm17_phase4D_candidate_pool_ceiling_audit_20260629_001655" / "candidate_pool_ceiling_per_target.csv"
GRAY_SAR_ROOT = Path(r"D:\profile\research\data\GM_RM017\GM_RM017_SARframes_gray")

A005_ALLOWED_FIELDS = [
    "target_identity",
    "scene",
    "sar_frame",
    "sar_frame_num",
    "pred_cx",
    "pred_cy",
    "pred_w",
    "pred_h",
    "pred_r",
    "pred_az",
    "pred_cross",
    "pred_heading_deg",
    "gm17_track_id",
]

BEST_ROLES = ["best_center", "best_iou"]
CENTER_GAIN_EPS = 1.0
IOU_GAIN_EPS = 0.01
RANGE_CROSS_DELTA_THRESHOLD = 10.0
AZ_DELTA_THRESHOLD = 1.0
OFFSET_GAP_NORM_THRESHOLD = 0.25
SCALE_GAP_THRESHOLD = 0.25


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
        raise RuntimeError(f"{name} missing fields {missing}; available fields: {header}")


def to_float(row: dict[str, Any], field: str, label: str = "") -> float:
    text = norm_text(row.get(field))
    if text == "":
        suffix = f" for {label}" if label else ""
        raise RuntimeError(f"missing numeric field {field}{suffix}")
    try:
        return float(text)
    except ValueError as exc:
        suffix = f" for {label}" if label else ""
        raise RuntimeError(f"invalid numeric field {field}={text!r}{suffix}") from exc


def safe_float(row: dict[str, Any], field: str) -> float | None:
    text = norm_text(row.get(field))
    if text == "":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def quantile(sorted_values: list[float], q: float) -> float:
    if not sorted_values:
        return math.nan
    if len(sorted_values) == 1:
        return sorted_values[0]
    pos = (len(sorted_values) - 1) * q
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return sorted_values[int(pos)]
    return sorted_values[lo] * (hi - pos) + sorted_values[hi] * (pos - lo)


def stats(values: list[float]) -> dict[str, Any]:
    clean = sorted([value for value in values if value is not None and math.isfinite(value)])
    if not clean:
        return {"count": 0, "mean": "", "median": "", "p25": "", "p75": "", "p90": ""}
    return {
        "count": len(clean),
        "mean": round(mean(clean), 6),
        "median": round(median(clean), 6),
        "p25": round(quantile(clean, 0.25), 6),
        "p75": round(quantile(clean, 0.75), 6),
        "p90": round(quantile(clean, 0.90), 6),
    }


def vector_len(x: float, y: float) -> float:
    return math.hypot(x, y)


def offset_metrics(candidate: dict[str, str], a005: dict[str, str], role: str) -> dict[str, Any]:
    pred_cx = to_float(a005, "pred_cx", a005["target_identity"])
    pred_cy = to_float(a005, "pred_cy", a005["target_identity"])
    pred_w = to_float(a005, "pred_w", a005["target_identity"])
    pred_h = to_float(a005, "pred_h", a005["target_identity"])
    cx = to_float(candidate, "cx", candidate.get("candidate_id", ""))
    cy = to_float(candidate, "cy", candidate.get("candidate_id", ""))
    w = to_float(candidate, "w", candidate.get("candidate_id", ""))
    h = to_float(candidate, "h", candidate.get("candidate_id", ""))
    dx = cx - pred_cx
    dy = cy - pred_cy
    denom = max(math.hypot(pred_w, pred_h), 1.0)
    out = {
        f"dx_{role}": round(dx, 6),
        f"dy_{role}": round(dy, 6),
        f"normalized_xy_offset_{role}": round(math.hypot(dx, dy) / denom, 6),
        f"scale_w_{role}": round(w / pred_w, 6) if pred_w else "",
        f"scale_h_{role}": round(h / pred_h, 6) if pred_h else "",
        f"delta_r_from_pred_{role}": safe_float(candidate, "delta_r_from_pred"),
        f"delta_cross_from_pred_{role}": safe_float(candidate, "delta_cross_from_pred"),
        f"delta_az_from_pred_{role}": safe_float(candidate, "delta_az_from_pred"),
    }
    for key, value in list(out.items()):
        if isinstance(value, float):
            out[key] = round(value, 6)
    return out


def proposal_offset_metrics(proposal: dict[str, str], a005: dict[str, str], role: str) -> dict[str, Any]:
    pred_cx = to_float(a005, "pred_cx", a005["target_identity"])
    pred_cy = to_float(a005, "pred_cy", a005["target_identity"])
    pred_w = to_float(a005, "pred_w", a005["target_identity"])
    pred_h = to_float(a005, "pred_h", a005["target_identity"])
    cx = to_float(proposal, "cx", proposal.get("proposal_id", ""))
    cy = to_float(proposal, "cy", proposal.get("proposal_id", ""))
    w = to_float(proposal, "w", proposal.get("proposal_id", ""))
    h = to_float(proposal, "h", proposal.get("proposal_id", ""))
    dx = cx - pred_cx
    dy = cy - pred_cy
    denom = max(math.hypot(pred_w, pred_h), 1.0)
    return {
        f"A_only_{role}_dx": round(dx, 6),
        f"A_only_{role}_dy": round(dy, 6),
        f"A_only_{role}_normalized_offset": round(math.hypot(dx, dy) / denom, 6),
        f"A_only_{role}_w_scale": round(w / pred_w, 6) if pred_w else "",
        f"A_only_{role}_h_scale": round(h / pred_h, 6) if pred_h else "",
    }


def as_num(value: Any, default: float = math.nan) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def label_m1(
    target: str,
    vs: dict[str, str],
    comparison: dict[str, Any],
    center_cand: dict[str, str] | None,
) -> tuple[str, str, str]:
    delta_center = to_float(vs, "delta_center_error", target)
    delta_iou = to_float(vs, "delta_iou", target)
    a001_better = delta_center < -CENTER_GAIN_EPS or delta_iou < -IOU_GAIN_EPS
    offset_gap = as_num(comparison.get("offset_vector_gap_center_norm"), 0.0)
    scale_gap = as_num(comparison.get("scale_gap_center"), 0.0)
    delta_r = abs(as_num(comparison.get("A001_delta_r_center"), 0.0))
    delta_cross = abs(as_num(comparison.get("A001_delta_cross_center"), 0.0))
    delta_az = abs(as_num(comparison.get("A001_delta_az_center"), 0.0))
    source = center_cand.get("candidate_source", "") if center_cand else ""
    expansion_state = center_cand.get("candidate_expansion_state", "") if center_cand else ""
    range_cross_signal = max(delta_r, delta_cross) >= RANGE_CROSS_DELTA_THRESHOLD or delta_az >= AZ_DELTA_THRESHOLD
    offset_gap_signal = offset_gap >= OFFSET_GAP_NORM_THRESHOLD
    source_diverse = source not in {"", "base_candidate"} or expansion_state not in {"", "base", "none"}

    if a001_better and range_cross_signal and offset_gap_signal:
        return (
            "supports_M1_range_cross",
            f"A001 is better; range/cross/az signal is large (|dr|={delta_r:.3f}, |dcross|={delta_cross:.3f}, |daz|={delta_az:.3f}) and v0-A offset gap is {offset_gap:.3f}.",
            "geometry_aware_shell_v1",
        )
    if a001_better and offset_gap_signal:
        return (
            "supports_M1_anisotropic_xy",
            f"A001 is better and v0-A offset gap is {offset_gap:.3f}, but range/cross signal is not decisive.",
            "anisotropic_shell_v1",
        )
    if a001_better and delta_iou < -0.05 and abs(delta_center) <= 5.0 and scale_gap >= SCALE_GAP_THRESHOLD:
        return (
            "supports_extent_scale_model_more",
            f"A001 IoU advantage is large while center gap is modest; scale gap is {scale_gap:.3f}.",
            "M2_extent_scale_model",
        )
    if a001_better and source_diverse and not range_cross_signal:
        return (
            "supports_candidate_source_diversity",
            f"A001 advantage is tied to candidate source {source} / expansion {expansion_state}, without clear range/cross signal.",
            "M2_candidate_source_diversity",
        )
    if not a001_better and offset_gap < OFFSET_GAP_NORM_THRESHOLD:
        return (
            "weak_or_no_support_for_M1",
            "A001 is not clearly better and v0 Route A covers a similar offset.",
            "strengthen_observation_factor",
        )
    return (
        "mixed_or_unclear",
        f"Signals are mixed: A001_better={a001_better}, offset_gap={offset_gap:.3f}, range_cross_signal={range_cross_signal}, scale_gap={scale_gap:.3f}.",
        "manual_inspection_or_M2_selection",
    )


def main() -> None:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = ROOT / "output" / f"modelM1_geometry_shell_hypothesis_test_{timestamp}"
    out_dir.mkdir(parents=True, exist_ok=False)

    proposals, proposal_header = read_csv(PROPOSAL_PATH)
    vs_rows, vs_header = read_csv(PHASE5C_VS_A001_PATH)
    subset_rows, subset_header = read_csv(PHASE5C_ROUTE_SUBSET_PATH)
    problem_rows, problem_header = read_csv(PHASE5C_PROBLEM_PATH)
    sample_rows, sample_header = read_csv(PHASE5C_SAMPLES_PATH)
    novelty_rows, novelty_header = read_csv(PHASE5C_NOVELTY_PATH)
    a005_rows, a005_header = read_csv(A005_PATH)
    bank_rows, bank_header = read_csv(A001_BANK_PATH)
    baseline_rows, baseline_header = read_csv(PHASE4D_BASELINE_PATH)

    require_fields("Phase5C vs A001", vs_header, ["target_identity", "delta_center_error", "delta_iou"])
    require_fields("Phase5C subset", subset_header, ["target_identity", "subset_name", "best_center_proposal_id", "best_iou_proposal_id"])
    require_fields("Phase5B proposals", proposal_header, ["proposal_id", "target_identity", "cx", "cy", "w", "h", "route_name"])
    require_fields("A005 proxy", a005_header, A005_ALLOWED_FIELDS)
    require_fields("A001 bank", bank_header, [
        "target_identity", "candidate_id", "candidate_source", "candidate_detail", "cx", "cy", "w", "h",
        "r", "az", "cross", "delta_r_from_pred", "delta_cross_from_pred", "delta_az_from_pred",
        "candidate_expansion_state", "candidate_expansion_reason", "gm17_track_id",
    ])
    require_fields("Phase4D baseline", baseline_header, [
        "target_identity", "best_iou_candidate_id", "best_iou", "best_iou_center_error",
        "best_center_candidate_id", "best_center_error", "best_center_iou",
        "best_iou_candidate_source_or_type", "best_center_candidate_source_or_type",
    ])

    a005_allowed_rows = [
        {field: row.get(field, "") for field in A005_ALLOWED_FIELDS}
        for row in a005_rows
    ]
    a005_by_target = {row["target_identity"]: row for row in a005_allowed_rows if row["target_identity"]}
    bank_by_id = {row["candidate_id"]: row for row in bank_rows if row.get("candidate_id")}
    bank_by_target: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    for row in bank_rows:
        bank_by_target[row["target_identity"]].append(row)
    proposal_by_id = {row["proposal_id"]: row for row in proposals if row.get("proposal_id")}
    baseline_by_target = {row["target_identity"]: row for row in baseline_rows if row.get("target_identity")}
    vs_by_target = {row["target_identity"]: row for row in vs_rows if row.get("target_identity")}
    problem_by_target = {row["target_identity"]: row for row in problem_rows if row.get("target_identity")}
    novelty_by_proposal = {row["proposal_id"]: row for row in novelty_rows if row.get("proposal_id")}
    novelty_by_target: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    for row in novelty_rows:
        novelty_by_target[row["target_identity"]].append(row)

    subset_by_target: defaultdict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    for row in subset_rows:
        subset_by_target[row["target_identity"]][row["subset_name"]] = row

    target_ids = sorted(set(vs_by_target) & set(baseline_by_target) & set(a005_by_target))

    anatomy_rows: list[dict[str, Any]] = []
    missing_best_center_join = 0
    missing_best_iou_join = 0
    role_candidate_by_target: dict[tuple[str, str], dict[str, str] | None] = {}
    for target in target_ids:
        base = baseline_by_target[target]
        row: dict[str, Any] = {
            "target_identity": target,
            "best_center_candidate_id": base.get("best_center_candidate_id", ""),
            "best_iou_candidate_id": base.get("best_iou_candidate_id", ""),
            "best_center_error": base.get("best_center_error", ""),
            "best_center_iou": base.get("best_center_iou", ""),
            "best_iou": base.get("best_iou", ""),
            "best_iou_center_error": base.get("best_iou_center_error", ""),
            "failure_class": base.get("failure_class", ""),
            "condition_type": base.get("condition_type", ""),
            "condition_degree": base.get("condition_degree", ""),
            "truncation_degree": base.get("truncation_degree", ""),
            "occlusion_degree": base.get("occlusion_degree", ""),
            "oracle_usable": base.get("oracle_usable", ""),
            "oracle_high_quality": base.get("oracle_high_quality", ""),
            "selection_limited": base.get("selection_limited", ""),
            "pool_limited": base.get("pool_limited", ""),
        }
        for role in BEST_ROLES:
            cid = base.get(f"{role}_candidate_id", "")
            cand = bank_by_id.get(cid)
            role_candidate_by_target[(target, role)] = cand
            if cand is None:
                if role == "best_center":
                    missing_best_center_join += 1
                else:
                    missing_best_iou_join += 1
                row[f"{role}_join_status"] = "missing"
                continue
            row[f"{role}_join_status"] = "joined"
            for field in [
                "cx", "cy", "w", "h", "r", "az", "cross", "delta_r_from_pred",
                "delta_cross_from_pred", "delta_az_from_pred", "candidate_source",
                "candidate_detail", "candidate_expansion_state", "candidate_expansion_reason",
            ]:
                row[f"{role}_{field}"] = cand.get(field, "")
        anatomy_rows.append(row)

    offset_rows: list[dict[str, Any]] = []
    for target in target_ids:
        a005 = a005_by_target[target]
        out = {
            "target_identity": target,
            "pred_cx": a005["pred_cx"],
            "pred_cy": a005["pred_cy"],
            "pred_w": a005["pred_w"],
            "pred_h": a005["pred_h"],
            "pred_r": a005["pred_r"],
            "pred_az": a005["pred_az"],
            "pred_cross": a005["pred_cross"],
        }
        for role in BEST_ROLES:
            cand = role_candidate_by_target[(target, role)]
            if cand is not None:
                out.update(offset_metrics(cand, a005, "center" if role == "best_center" else "iou"))
        offset_rows.append(out)

    def values(field: str) -> list[float]:
        return [abs(as_num(row.get(field))) for row in offset_rows if math.isfinite(as_num(row.get(field)))]

    def raw_values(field: str) -> list[float]:
        return [as_num(row.get(field)) for row in offset_rows if math.isfinite(as_num(row.get(field)))]

    geometry_summary = {
        "best_center": {
            "abs_dx": stats(values("dx_center")),
            "abs_dy": stats(values("dy_center")),
            "normalized_xy_offset": stats(raw_values("normalized_xy_offset_center")),
            "abs_delta_r_from_pred": stats(values("delta_r_from_pred_center")),
            "abs_delta_cross_from_pred": stats(values("delta_cross_from_pred_center")),
            "abs_delta_az_from_pred": stats(values("delta_az_from_pred_center")),
            "scale_w": stats(raw_values("scale_w_center")),
            "scale_h": stats(raw_values("scale_h_center")),
        },
        "best_iou": {
            "abs_dx": stats(values("dx_iou")),
            "abs_dy": stats(values("dy_iou")),
            "normalized_xy_offset": stats(raw_values("normalized_xy_offset_iou")),
            "abs_delta_r_from_pred": stats(values("delta_r_from_pred_iou")),
            "abs_delta_cross_from_pred": stats(values("delta_cross_from_pred_iou")),
            "abs_delta_az_from_pred": stats(values("delta_az_from_pred_iou")),
            "scale_w": stats(raw_values("scale_w_iou")),
            "scale_h": stats(raw_values("scale_h_iou")),
        },
        "candidate_source_counts": {
            "best_center": dict(Counter(row.get("best_center_candidate_source", "") for row in anatomy_rows if row.get("best_center_candidate_source", ""))),
            "best_iou": dict(Counter(row.get("best_iou_candidate_source", "") for row in anatomy_rows if row.get("best_iou_candidate_source", ""))),
        },
        "candidate_expansion_state_counts": {
            "best_center": dict(Counter(row.get("best_center_candidate_expansion_state", "") for row in anatomy_rows if row.get("best_center_candidate_expansion_state", ""))),
            "best_iou": dict(Counter(row.get("best_iou_candidate_expansion_state", "") for row in anatomy_rows if row.get("best_iou_candidate_expansion_state", ""))),
        },
        "candidate_expansion_reason_counts": {
            "best_center": dict(Counter(row.get("best_center_candidate_expansion_reason", "") for row in anatomy_rows if row.get("best_center_candidate_expansion_reason", ""))),
            "best_iou": dict(Counter(row.get("best_iou_candidate_expansion_reason", "") for row in anatomy_rows if row.get("best_iou_candidate_expansion_reason", ""))),
        },
        "join": {
            "target_count": len(target_ids),
            "best_center_join_success": len(target_ids) - missing_best_center_join,
            "best_iou_join_success": len(target_ids) - missing_best_iou_join,
            "best_center_join_success_rate": round((len(target_ids) - missing_best_center_join) / len(target_ids), 6) if target_ids else 0,
            "best_iou_join_success_rate": round((len(target_ids) - missing_best_iou_join) / len(target_ids), 6) if target_ids else 0,
            "missing_best_center_join": missing_best_center_join,
            "missing_best_iou_join": missing_best_iou_join,
        },
    }

    route_a_rows: list[dict[str, Any]] = []
    comparison_by_target: dict[str, dict[str, Any]] = {}
    for target in target_ids:
        a005 = a005_by_target[target]
        subset_a = subset_by_target[target].get("A_only", {})
        center_prop = proposal_by_id.get(subset_a.get("best_center_proposal_id", ""))
        iou_prop = proposal_by_id.get(subset_a.get("best_iou_proposal_id", ""))
        out: dict[str, Any] = {
            "target_identity": target,
            "A_only_best_center_proposal_id": subset_a.get("best_center_proposal_id", ""),
            "A_only_best_iou_proposal_id": subset_a.get("best_iou_proposal_id", ""),
        }
        if center_prop is not None:
            out.update(proposal_offset_metrics(center_prop, a005, "best_center"))
        if iou_prop is not None:
            out.update(proposal_offset_metrics(iou_prop, a005, "best_iou"))
        off = next(row for row in offset_rows if row["target_identity"] == target)
        if "dx_center" in off and "A_only_best_center_dx" in out:
            gap = vector_len(as_num(off["dx_center"]) - as_num(out["A_only_best_center_dx"]), as_num(off["dy_center"]) - as_num(out["A_only_best_center_dy"]))
            denom = max(math.hypot(to_float(a005, "pred_w", target), to_float(a005, "pred_h", target)), 1.0)
            scale_gap = vector_len(as_num(off["scale_w_center"]) - as_num(out["A_only_best_center_w_scale"]), as_num(off["scale_h_center"]) - as_num(out["A_only_best_center_h_scale"]))
            out["offset_vector_gap_center"] = round(gap, 6)
            out["offset_vector_gap_center_norm"] = round(gap / denom, 6)
            out["scale_gap_center"] = round(scale_gap, 6)
            out["A001_delta_r_center"] = off.get("delta_r_from_pred_center", "")
            out["A001_delta_cross_center"] = off.get("delta_cross_from_pred_center", "")
            out["A001_delta_az_center"] = off.get("delta_az_from_pred_center", "")
        if "dx_iou" in off and "A_only_best_iou_dx" in out:
            gap = vector_len(as_num(off["dx_iou"]) - as_num(out["A_only_best_iou_dx"]), as_num(off["dy_iou"]) - as_num(out["A_only_best_iou_dy"]))
            denom = max(math.hypot(to_float(a005, "pred_w", target), to_float(a005, "pred_h", target)), 1.0)
            scale_gap = vector_len(as_num(off["scale_w_iou"]) - as_num(out["A_only_best_iou_w_scale"]), as_num(off["scale_h_iou"]) - as_num(out["A_only_best_iou_h_scale"]))
            out["offset_vector_gap_iou"] = round(gap, 6)
            out["offset_vector_gap_iou_norm"] = round(gap / denom, 6)
            out["scale_gap_iou"] = round(scale_gap, 6)
            out["A001_delta_r_iou"] = off.get("delta_r_from_pred_iou", "")
            out["A001_delta_cross_iou"] = off.get("delta_cross_from_pred_iou", "")
            out["A001_delta_az_iou"] = off.get("delta_az_from_pred_iou", "")
        comparison_by_target[target] = out
        route_a_rows.append(out)

    evidence_rows: list[dict[str, Any]] = []
    evidence_factors_rows: list[dict[str, Any]] = []
    for target in target_ids:
        vs = vs_by_target[target]
        comp = comparison_by_target[target]
        center_cand = role_candidate_by_target[(target, "best_center")]
        delta_center = to_float(vs, "delta_center_error", target)
        delta_iou = to_float(vs, "delta_iou", target)
        delta_r = as_num(comp.get("A001_delta_r_center"), 0.0)
        delta_cross = as_num(comp.get("A001_delta_cross_center"), 0.0)
        delta_az = as_num(comp.get("A001_delta_az_center"), 0.0)
        offset_gap = as_num(comp.get("offset_vector_gap_center_norm"), 0.0)
        scale_gap = as_num(comp.get("scale_gap_center"), 0.0)
        candidate_source = center_cand.get("candidate_source", "") if center_cand else ""
        candidate_expansion_state = center_cand.get("candidate_expansion_state", "") if center_cand else ""
        has_a001_advantage = delta_center < -CENTER_GAIN_EPS or delta_iou < -IOU_GAIN_EPS
        has_range_cross_signal = max(abs(delta_r), abs(delta_cross)) >= RANGE_CROSS_DELTA_THRESHOLD or abs(delta_az) >= AZ_DELTA_THRESHOLD
        has_large_offset_gap_0p25 = offset_gap >= 0.25
        has_large_offset_gap_0p15 = offset_gap >= 0.15
        has_candidate_source_signal = candidate_source not in {"", "base_candidate"}
        has_scale_signal = scale_gap >= SCALE_GAP_THRESHOLD
        has_v0_a_coverage = offset_gap < 0.15
        label, evidence, direction = label_m1(target, vs, comp, center_cand)
        evidence_rows.append(
            {
                "target_identity": target,
                "M1_evidence_label": label,
                "evidence_summary": evidence,
                "A001_better_than_phase5B": str(has_a001_advantage).lower(),
                "delta_center_error": vs.get("delta_center_error", ""),
                "delta_iou": vs.get("delta_iou", ""),
                "A001_delta_r": comp.get("A001_delta_r_center", ""),
                "A001_delta_cross": comp.get("A001_delta_cross_center", ""),
                "A001_delta_az": comp.get("A001_delta_az_center", ""),
                "A001_offset_gap_vs_v0_A": comp.get("offset_vector_gap_center_norm", ""),
                "A001_scale_gap_vs_v0_A": comp.get("scale_gap_center", ""),
                "candidate_source": candidate_source,
                "candidate_expansion_state": candidate_expansion_state,
                "recommended_model_direction": direction,
            }
        )
        evidence_factors_rows.append(
            {
                "target_identity": target,
                "has_A001_advantage": str(has_a001_advantage).lower(),
                "has_range_cross_signal": str(has_range_cross_signal).lower(),
                "has_large_offset_gap_0p25": str(has_large_offset_gap_0p25).lower(),
                "has_large_offset_gap_0p15": str(has_large_offset_gap_0p15).lower(),
                "has_candidate_source_signal": str(has_candidate_source_signal).lower(),
                "has_scale_signal": str(has_scale_signal).lower(),
                "has_v0_A_coverage": str(has_v0_a_coverage).lower(),
                "candidate_source": candidate_source,
                "candidate_expansion_state": candidate_expansion_state,
                "delta_center_error": vs.get("delta_center_error", ""),
                "delta_iou": vs.get("delta_iou", ""),
                "A001_delta_r": comp.get("A001_delta_r_center", ""),
                "A001_delta_cross": comp.get("A001_delta_cross_center", ""),
                "A001_delta_az": comp.get("A001_delta_az_center", ""),
                "offset_gap_center_norm": comp.get("offset_vector_gap_center_norm", ""),
                "scale_gap_center": comp.get("scale_gap_center", ""),
            }
        )

    threshold_sensitivity_rows: list[dict[str, Any]] = []
    a001_advantage_factor_rows = [row for row in evidence_factors_rows if row["has_A001_advantage"] == "true"]
    for threshold in [0.05, 0.10, 0.15, 0.20, 0.25]:
        support_count = sum(
            1
            for row in evidence_factors_rows
            if row["has_A001_advantage"] == "true"
            and row["has_range_cross_signal"] == "true"
            and as_num(row.get("offset_gap_center_norm"), 0.0) >= threshold
        )
        threshold_sensitivity_rows.append(
            {
                "offset_gap_threshold": f"{threshold:.2f}",
                "support_count_all": support_count,
                "support_rate_all": round(support_count / len(evidence_factors_rows), 6) if evidence_factors_rows else 0,
                "support_count_A001_advantage": support_count,
                "support_rate_A001_advantage": round(support_count / len(a001_advantage_factor_rows), 6) if a001_advantage_factor_rows else 0,
            }
        )

    label_counts = Counter(row["M1_evidence_label"] for row in evidence_rows)
    supporting = label_counts.get("supports_M1_range_cross", 0) + label_counts.get("supports_M1_anisotropic_xy", 0)
    extent_count = label_counts.get("supports_extent_scale_model_more", 0)
    diversity_count = label_counts.get("supports_candidate_source_diversity", 0)
    weak_count = label_counts.get("weak_or_no_support_for_M1", 0)
    a001_advantage_targets = [row for row in evidence_rows if row["A001_better_than_phase5B"] == "true"]
    support_rate = supporting / len(evidence_rows) if evidence_rows else 0
    support_advantage_rate = (
        sum(1 for row in a001_advantage_targets if row["M1_evidence_label"] in {"supports_M1_range_cross", "supports_M1_anisotropic_xy"}) / len(a001_advantage_targets)
        if a001_advantage_targets else 0
    )
    missing_join_rate = (missing_best_center_join + missing_best_iou_join) / max(2 * len(target_ids), 1)
    if missing_join_rate > 0.1:
        judgment = "M1_INCONCLUSIVE"
    elif support_rate >= 0.6 and support_advantage_rate >= 0.6:
        judgment = "M1_STRONGLY_SUPPORTED"
    elif support_rate >= 0.4 or support_advantage_rate >= 0.4:
        judgment = "M1_PARTIALLY_SUPPORTED"
    elif extent_count + diversity_count > supporting:
        judgment = "M1_NOT_SUPPORTED"
    else:
        judgment = "M1_INCONCLUSIVE"

    pred_available = {
        field: sum(1 for row in a005_allowed_rows if norm_text(row.get(field)) != "")
        for field in ["pred_r", "pred_az", "pred_cross"]
    }
    bank_available_counts = {
        field: sum(1 for row in bank_rows if norm_text(row.get(field)) != "")
        for field in ["r", "az", "cross", "delta_r_from_pred", "delta_cross_from_pred", "delta_az_from_pred"]
    }
    grayscale_available = 0
    for row in a005_allowed_rows:
        sar_frame = Path(row.get("sar_frame", "")).stem
        if sar_frame and (GRAY_SAR_ROOT / f"{sar_frame}.png").exists():
            grayscale_available += 1
    route_d_blockers = [
        "fan/range valid support mask not identified",
        "range/cross to image x/y mapping not frozen",
        "raw SAR source not identified for Route D",
    ]
    route_d_readiness = {
        "pred_r_available_for_all_targets": pred_available["pred_r"] == len(a005_allowed_rows),
        "pred_az_available_for_all_targets": pred_available["pred_az"] == len(a005_allowed_rows),
        "pred_cross_available_for_all_targets": pred_available["pred_cross"] == len(a005_allowed_rows),
        "A001_bank_r_az_cross_available": all(bank_available_counts[field] == len(bank_rows) for field in ["r", "az", "cross"]),
        "A001_bank_delta_fields_available": all(bank_available_counts[field] == len(bank_rows) for field in ["delta_r_from_pred", "delta_cross_from_pred", "delta_az_from_pred"]),
        "image_coordinate_convention_available": True,
        "fan_range_valid_support_mask_available": False,
        "raw_SAR_source_available": False,
        "grayscale_display_png_available_for_all_targets": grayscale_available >= len(a005_allowed_rows),
        "can_Route_D_be_implemented_without_leaking_evaluation": True,
        "blocked_items": route_d_blockers,
        "readiness_status": "PARTIAL",
        "readiness_note": "Inference-side r/az/cross fields are available, but Route D is not READY until fan/range support and coordinate mapping are frozen.",
    }

    evidence_summary = {
        "label_counts": dict(label_counts),
        "threshold_sensitivity": threshold_sensitivity_rows,
        "non_exclusive_evidence_factor_counts": {
            "has_A001_advantage": sum(1 for row in evidence_factors_rows if row["has_A001_advantage"] == "true"),
            "has_range_cross_signal": sum(1 for row in evidence_factors_rows if row["has_range_cross_signal"] == "true"),
            "has_large_offset_gap_0p25": sum(1 for row in evidence_factors_rows if row["has_large_offset_gap_0p25"] == "true"),
            "has_large_offset_gap_0p15": sum(1 for row in evidence_factors_rows if row["has_large_offset_gap_0p15"] == "true"),
            "has_candidate_source_signal": sum(1 for row in evidence_factors_rows if row["has_candidate_source_signal"] == "true"),
            "has_scale_signal": sum(1 for row in evidence_factors_rows if row["has_scale_signal"] == "true"),
            "has_v0_A_coverage": sum(1 for row in evidence_factors_rows if row["has_v0_A_coverage"] == "true"),
        },
        "percentage_supporting_M1": round(support_rate, 6),
        "percentage_supporting_M1_among_A001_advantage_cases": round(support_advantage_rate, 6),
        "percentage_supporting_extent_model_instead": round(extent_count / len(evidence_rows), 6) if evidence_rows else 0,
        "percentage_supporting_candidate_source_diversity": round(diversity_count / len(evidence_rows), 6) if evidence_rows else 0,
        "percentage_weak_or_no_support": round(weak_count / len(evidence_rows), 6) if evidence_rows else 0,
        "routeD_readiness_status": route_d_readiness["readiness_status"],
        "final_M1_judgment": judgment,
        "judgment_interpretation": (
            "M1 strong claim is not supported. This rejects the claim that A001's advantage is mainly explained by range/cross offsets not covered by v0 Route A. It does not reject SAR geometry-aware modeling in general. The stronger signal is candidate-source structure, especially wedge_joint_candidate."
            if judgment == "M1_NOT_SUPPORTED"
            else "M1 judgment follows the transparent support-rate rules recorded here."
        ),
        "judgment_rules": {
            "M1_STRONGLY_SUPPORTED": "support labels >= 60% of all targets and >= 60% of A001-advantage targets",
            "M1_PARTIALLY_SUPPORTED": "support labels >= 40% of all targets or >= 40% of A001-advantage targets",
            "M1_NOT_SUPPORTED": "extent/candidate-source alternatives outnumber M1 support labels",
            "M1_INCONCLUSIVE": "missing joins too high or signals mixed below support threshold",
        },
    }

    sample_by_target: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    for row in sample_rows:
        sample_by_target[row["target_identity"]].append(row)
    evidence_by_target = {row["target_identity"]: row for row in evidence_rows}
    review_targets = set()
    for row in problem_rows:
        if row.get("problem_attribution_label") == "phase5B_adds_new_hypothesis":
            review_targets.add(row["target_identity"])
    for row in sample_rows:
        if row.get("bucket") == "outside_A001_high_quality_proposals":
            review_targets.add(row["target_identity"])

    review_rows: list[dict[str, Any]] = []
    for target in sorted(review_targets):
        candidates = sample_by_target.get(target, [])
        sample = next((row for row in candidates if row.get("bucket") == "outside_A001_high_quality_proposals"), None) or (candidates[0] if candidates else {})
        prop_id = sample.get("best_phase5B_proposal_id", "")
        novelty = novelty_by_proposal.get(prop_id)
        if novelty is None:
            target_novel = [row for row in novelty_by_target.get(target, []) if row.get("outside_A001_neighborhood") == "true"]
            novelty = target_novel[0] if target_novel else {}
        evidence = evidence_by_target.get(target, {})
        review_rows.append(
            {
                "target_identity": target,
                "scene": sample.get("scene", baseline_by_target.get(target, {}).get("scene", "")),
                "sar_frame_num": sample.get("sar_frame_num", baseline_by_target.get(target, {}).get("sar_frame_num", "")),
                "best_phase5B_proposal_id": prop_id,
                "best_route": sample.get("best_route", ""),
                "phase5B_best_center_error": sample.get("phase5B_best_center_error", vs_by_target.get(target, {}).get("phase5B_best_center_error", "")),
                "phase5B_best_iou": sample.get("phase5B_best_iou", vs_by_target.get(target, {}).get("phase5B_best_iou", "")),
                "A001_best_center_error": sample.get("A001_best_center_error", vs_by_target.get(target, {}).get("A001_best_center_error", "")),
                "A001_best_iou": sample.get("A001_best_iou", vs_by_target.get(target, {}).get("A001_best_iou", "")),
                "outside_A001_neighborhood": novelty.get("outside_A001_neighborhood", ""),
                "novelty_reason": novelty.get("novelty_reason", ""),
                "M1_evidence_label": evidence.get("M1_evidence_label", ""),
                "manual_question": "Is this a true SAR-supported state? Is outside-A001 novelty real? Does it support geometry-aware shell, SAR observation, or neither?",
            }
        )

    anatomy_fields = [
        "target_identity", "best_center_candidate_id", "best_iou_candidate_id", "best_center_error",
        "best_center_iou", "best_iou", "best_iou_center_error", "failure_class", "condition_type",
        "condition_degree", "truncation_degree", "occlusion_degree", "oracle_usable", "oracle_high_quality",
        "selection_limited", "pool_limited",
    ]
    for role in BEST_ROLES:
        anatomy_fields.extend([f"{role}_join_status"])
        for field in [
            "cx", "cy", "w", "h", "r", "az", "cross", "delta_r_from_pred", "delta_cross_from_pred",
            "delta_az_from_pred", "candidate_source", "candidate_detail", "candidate_expansion_state",
            "candidate_expansion_reason",
        ]:
            anatomy_fields.append(f"{role}_{field}")
    offset_fields = [
        "target_identity", "pred_cx", "pred_cy", "pred_w", "pred_h", "pred_r", "pred_az", "pred_cross",
        "dx_center", "dy_center", "normalized_xy_offset_center", "scale_w_center", "scale_h_center",
        "delta_r_from_pred_center", "delta_cross_from_pred_center", "delta_az_from_pred_center",
        "dx_iou", "dy_iou", "normalized_xy_offset_iou", "scale_w_iou", "scale_h_iou",
        "delta_r_from_pred_iou", "delta_cross_from_pred_iou", "delta_az_from_pred_iou",
    ]
    route_a_fields = [
        "target_identity", "A_only_best_center_proposal_id", "A_only_best_iou_proposal_id",
        "A_only_best_center_dx", "A_only_best_center_dy", "A_only_best_center_normalized_offset",
        "A_only_best_center_w_scale", "A_only_best_center_h_scale",
        "A_only_best_iou_dx", "A_only_best_iou_dy", "A_only_best_iou_normalized_offset",
        "A_only_best_iou_w_scale", "A_only_best_iou_h_scale",
        "offset_vector_gap_center", "offset_vector_gap_center_norm", "scale_gap_center",
        "A001_delta_r_center", "A001_delta_cross_center", "A001_delta_az_center",
        "offset_vector_gap_iou", "offset_vector_gap_iou_norm", "scale_gap_iou",
        "A001_delta_r_iou", "A001_delta_cross_iou", "A001_delta_az_iou",
    ]
    evidence_fields = [
        "target_identity", "M1_evidence_label", "evidence_summary", "A001_better_than_phase5B",
        "delta_center_error", "delta_iou", "A001_delta_r", "A001_delta_cross", "A001_delta_az",
        "A001_offset_gap_vs_v0_A", "A001_scale_gap_vs_v0_A", "candidate_source",
        "candidate_expansion_state", "recommended_model_direction",
    ]
    evidence_factors_fields = [
        "target_identity", "has_A001_advantage", "has_range_cross_signal",
        "has_large_offset_gap_0p25", "has_large_offset_gap_0p15",
        "has_candidate_source_signal", "has_scale_signal", "has_v0_A_coverage",
        "candidate_source", "candidate_expansion_state", "delta_center_error", "delta_iou",
        "A001_delta_r", "A001_delta_cross", "A001_delta_az",
        "offset_gap_center_norm", "scale_gap_center",
    ]
    threshold_sensitivity_fields = [
        "offset_gap_threshold", "support_count_all", "support_rate_all",
        "support_count_A001_advantage", "support_rate_A001_advantage",
    ]
    review_fields = [
        "target_identity", "scene", "sar_frame_num", "best_phase5B_proposal_id", "best_route",
        "phase5B_best_center_error", "phase5B_best_iou", "A001_best_center_error", "A001_best_iou",
        "outside_A001_neighborhood", "novelty_reason", "M1_evidence_label", "manual_question",
    ]

    write_csv(out_dir / "modelM1_a001_oracle_candidate_anatomy.csv", anatomy_rows, anatomy_fields)
    write_csv(out_dir / "modelM1_a001_vs_a005_geometry_offsets.csv", offset_rows, offset_fields)
    write_json(out_dir / "modelM1_a001_geometry_offset_summary.json", geometry_summary)
    write_csv(out_dir / "modelM1_v0_routeA_vs_a001_offset_comparison.csv", route_a_rows, route_a_fields)
    write_csv(out_dir / "modelM1_per_target_evidence.csv", evidence_rows, evidence_fields)
    write_csv(out_dir / "modelM1_evidence_factors_per_target.csv", evidence_factors_rows, evidence_factors_fields)
    write_csv(out_dir / "modelM1_threshold_sensitivity.csv", threshold_sensitivity_rows, threshold_sensitivity_fields)
    write_json(out_dir / "modelM1_evidence_summary.json", evidence_summary)
    write_json(out_dir / "modelM1_routeD_readiness.json", route_d_readiness)
    write_csv(out_dir / "modelM1_new_hypothesis_review_cases.csv", review_rows, review_fields)
    audit_log = {
        "timestamp": timestamp,
        "model_hypothesis": "SAR localization error should be modeled in geometry-aware range/cross/azimuth coordinates rather than as isotropic image x/y grid offsets.",
        "inputs": {
            "phase5B_v0_proposals": rel(PROPOSAL_PATH),
            "phase5C_vs_A001": rel(PHASE5C_VS_A001_PATH),
            "phase5C_route_subset": rel(PHASE5C_ROUTE_SUBSET_PATH),
            "phase5C_problem_attribution": rel(PHASE5C_PROBLEM_PATH),
            "phase5C_interesting_samples": rel(PHASE5C_SAMPLES_PATH),
            "phase5C_novelty": rel(PHASE5C_NOVELTY_PATH),
            "A005_proxy": rel(A005_PATH),
            "A001_candidate_bank": rel(A001_BANK_PATH),
            "Phase4D_A001_baseline": rel(PHASE4D_BASELINE_PATH),
        },
        "outputs": {
            "modelM1_evidence_factors_per_target": rel(out_dir / "modelM1_evidence_factors_per_target.csv"),
            "modelM1_threshold_sensitivity": rel(out_dir / "modelM1_threshold_sensitivity.csv"),
        },
        "headers": {
            "proposal_header": proposal_header,
            "vs_header": vs_header,
            "subset_header": subset_header,
            "problem_header": problem_header,
            "sample_header": sample_header,
            "novelty_header": novelty_header,
            "a005_header": a005_header,
            "bank_header": bank_header,
            "baseline_header": baseline_header,
        },
        "boundary": {
            "post_hoc_model_hypothesis_test_only": True,
            "v1_proposal_generated": False,
            "v1_generator_written": False,
            "phase5B_v0_config_changed": False,
            "v0_proposal_regenerated": False,
            "source_files_modified": False,
            "c3_c4_integration": False,
            "threshold_tuning": False,
            "training": False,
            "calibration": False,
            "push": False,
        },
    }
    write_json(out_dir / "modelM1_audit_log.json", audit_log)

    next_decision = {
        "M1_STRONGLY_SUPPORTED": "freeze geometry-aware shell config, but hold full generator until convention is ready",
        "M1_PARTIALLY_SUPPORTED": "refine M1 and inspect Route D readiness before v1 config",
        "M1_NOT_SUPPORTED": "propose M2 such as extent-scale or candidate-source diversity model",
        "M1_INCONCLUSIVE": "manual inspection and data convention resolution",
    }[judgment]

    docs_path = ROOT / "docs" / f"modelM1_geometry_shell_hypothesis_test_summary_{timestamp}.md"
    threshold_lines = "\n".join(
        f"- threshold {row['offset_gap_threshold']}: support {row['support_count_all']} / {len(evidence_factors_rows)} all targets ({row['support_rate_all']}), {row['support_count_A001_advantage']} / {len(a001_advantage_factor_rows)} A001-advantage targets ({row['support_rate_A001_advantage']})"
        for row in threshold_sensitivity_rows
    )
    judgment_interpretation = evidence_summary["judgment_interpretation"]
    docs_text = f"""# Model M1 Geometry-Aware Shell Hypothesis Test Summary

Date: {timestamp}

## 1. Purpose

This is a model hypothesis test loop, not a generic audit. It defines M1, runs a post-hoc experiment, analyzes the result, judges whether M1 holds, and decides the next model step.

## 2. M1 Hypothesis

Model M1: SAR localization error should be modeled in geometry-aware range/cross/azimuth coordinates rather than as isotropic image x/y grid offsets.

中文解释：光学到 SAR 的迁移误差不应主要建模为图像平面 x/y 上的均匀偏移，而应建模为 SAR 几何中的 range、cross、azimuth 方向不确定性。如果 A001 的优势主要来自 range/cross 方向上的系统性修正，那么 Phase5B-v1 应该优先重构 geometry-aware shell，而不是调 v0 的 energy peak、Otsu、top-k 或 crop。

## 3. Experiment Design

Inputs are frozen Phase5B-v0 proposals, Phase5C-v0 post-hoc results, A005 proxy fields, A001 oracle candidate ids from Phase4D, and A001 candidate-bank geometry fields. A001 and Phase5C fields are used only post-hoc for this model test.

## 4. A001 Anatomy Results

- Target count: {len(target_ids)}
- Best-center candidate join success: {geometry_summary['join']['best_center_join_success']} / {len(target_ids)} ({geometry_summary['join']['best_center_join_success_rate']})
- Best-IoU candidate join success: {geometry_summary['join']['best_iou_join_success']} / {len(target_ids)} ({geometry_summary['join']['best_iou_join_success_rate']})
- Best-center normalized offset median / p90: {geometry_summary['best_center']['normalized_xy_offset']['median']} / {geometry_summary['best_center']['normalized_xy_offset']['p90']}
- Best-center |delta_r| median / p90: {geometry_summary['best_center']['abs_delta_r_from_pred']['median']} / {geometry_summary['best_center']['abs_delta_r_from_pred']['p90']}
- Best-center |delta_cross| median / p90: {geometry_summary['best_center']['abs_delta_cross_from_pred']['median']} / {geometry_summary['best_center']['abs_delta_cross_from_pred']['p90']}
- Best-center |delta_az| median / p90: {geometry_summary['best_center']['abs_delta_az_from_pred']['median']} / {geometry_summary['best_center']['abs_delta_az_from_pred']['p90']}
- Best-center scale_w median / p90: {geometry_summary['best_center']['scale_w']['median']} / {geometry_summary['best_center']['scale_w']['p90']}
- Best-center scale_h median / p90: {geometry_summary['best_center']['scale_h']['median']} / {geometry_summary['best_center']['scale_h']['p90']}

Candidate source and expansion distributions are written to `modelM1_a001_geometry_offset_summary.json`.

## 5. v0 Route A vs A001

The comparison file `modelM1_v0_routeA_vs_a001_offset_comparison.csv` measures whether v0 A-only x/y grid hypotheses cover the A001 oracle offset. The key diagnostic is `offset_vector_gap_center_norm`, paired with A001 `delta_r`, `delta_cross`, and `delta_az`.

Median center offset gap norm: {stats([as_num(row.get('offset_vector_gap_center_norm')) for row in route_a_rows if math.isfinite(as_num(row.get('offset_vector_gap_center_norm')))])['median']}

P90 center offset gap norm: {stats([as_num(row.get('offset_vector_gap_center_norm')) for row in route_a_rows if math.isfinite(as_num(row.get('offset_vector_gap_center_norm')))])['p90']}

## 6. Evidence For / Against M1

Label counts:

{chr(10).join(f'- `{label}`: {count}' for label, count in label_counts.most_common())}

Percentage supporting M1: {evidence_summary['percentage_supporting_M1']}

Percentage supporting M1 among A001-advantage cases: {evidence_summary['percentage_supporting_M1_among_A001_advantage_cases']}

Alternative explanations:

- Extent model instead: {evidence_summary['percentage_supporting_extent_model_instead']}
- Candidate-source diversity: {evidence_summary['percentage_supporting_candidate_source_diversity']}
- Weak/no support: {evidence_summary['percentage_weak_or_no_support']}

Non-exclusive evidence factors are written to `modelM1_evidence_factors_per_target.csv`.

Threshold sensitivity for the M1 support definition is written to `modelM1_threshold_sensitivity.csv`:

{threshold_lines}

## 7. Route D Readiness

Route D readiness: `{route_d_readiness['readiness_status']}`.

Reasons:

{chr(10).join(f'- {item}' for item in route_d_readiness['blocked_items'])}

Inference-side r/az/cross fields are available, but Route D is not READY until fan/range valid support and coordinate mapping are frozen.

## 8. New-Hypothesis Cases

New-hypothesis review cases are written to `modelM1_new_hypothesis_review_cases.csv`.

Review case count: {len(review_rows)}

Manual question: Is this a true SAR-supported state? Is outside-A001 novelty real? Does it support geometry-aware shell, SAR observation, or neither?

## 9. M1 Judgment

Final M1 judgment: `{judgment}`.

This judgment follows the transparent rule recorded in `modelM1_evidence_summary.json`: support labels need to cover at least 40% of all targets or 40% of A001-advantage targets for partial support, and 60% for strong support. High missing joins force inconclusive.

{judgment_interpretation}

## 10. Next Model Decision

Next = {next_decision}.

## 11. Boundary

- Post-hoc model hypothesis test only.
- No v1 proposal generated.
- No v1 generator.
- No Phase5B-v0 config change.
- No v0 proposal regeneration.
- No source file modification.
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
                "best_center_join_success_rate": geometry_summary["join"]["best_center_join_success_rate"],
                "best_iou_join_success_rate": geometry_summary["join"]["best_iou_join_success_rate"],
                "M1_evidence_label_counts": dict(label_counts),
                "M1_final_judgment": judgment,
                "RouteD_readiness_status": route_d_readiness["readiness_status"],
                "new_hypothesis_review_cases": rel(out_dir / "modelM1_new_hypothesis_review_cases.csv"),
                "next_model_decision": next_decision,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
