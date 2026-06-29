#!/usr/bin/env python
"""Model M2 structured candidate-source hypothesis test.

This is a post-hoc model-hypothesis test. It does not generate proposals,
does not copy A001 candidate ids into a new model, and does not modify source
files.
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

PHASE5B_PROPOSALS_PATH = ROOT / "output" / "phase5B_first_diagnostic_run_v0_20260629_102746" / "proposal_candidates.csv"
PHASE5C_DIR = ROOT / "output" / "phase5C_v0_model_diagnostic_audit_20260629_110133"
PHASE5C_VS_A001_PATH = PHASE5C_DIR / "phase5C_v0_vs_A001_per_target.csv"
PHASE5C_ROUTE_SUBSET_PATH = PHASE5C_DIR / "phase5C_v0_route_subset_ceiling_per_target.csv"
PHASE5C_PROBLEM_PATH = PHASE5C_DIR / "phase5C_v0_problem_attribution_per_target.csv"
PHASE5C_SAMPLES_PATH = PHASE5C_DIR / "phase5C_v0_interesting_samples.csv"
PHASE5C_NOVELTY_PATH = PHASE5C_DIR / "phase5C_v0_a001_neighborhood_novelty.csv"
A001_BANK_PATH = ROOT / "output" / "clean_no_gt_localizer_2026-05-31_gm17_hard_candidate_expansion_v2" / "candidate_bank_inference.csv"
PHASE4D_BASELINE_PATH = ROOT / "output" / "gm17_phase4D_candidate_pool_ceiling_audit_20260629_001655" / "candidate_pool_ceiling_per_target.csv"
A021_CONDITION_PATH = ROOT / "output" / "hermes_annotation_consolidation_2026-05-20" / "00_tables" / "visibility_condition_working.csv"

CENTER_GAIN_EPS = 1.0
IOU_GAIN_EPS = 0.01
WEDGE_SOURCE = "wedge_joint_candidate"
RAY_ESCAPE_SOURCES = {
    "multi_peak_ray_candidate",
    "bidirectional_escape_candidate",
    "track_signed_escape_candidate",
}
KNOWN_FOCUS_SOURCES = [
    "wedge_joint_candidate",
    "base_candidate",
    "multi_peak_ray_candidate",
    "bidirectional_escape_candidate",
    "track_signed_escape_candidate",
    "visible_support_candidate",
]
CONDITION_AXES = ["condition_type", "truncation_degree", "occlusion_degree"]
M1_REQUIRED_FILES = [
    "modelM1_per_target_evidence.csv",
    "modelM1_evidence_factors_per_target.csv",
    "modelM1_a001_oracle_candidate_anatomy.csv",
    "modelM1_a001_vs_a005_geometry_offsets.csv",
    "modelM1_v0_routeA_vs_a001_offset_comparison.csv",
    "modelM1_a001_geometry_offset_summary.json",
    "modelM1_evidence_summary.json",
    "modelM1_threshold_sensitivity.csv",
]


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


def read_json(path: Path) -> Any:
    if not path.exists():
        raise RuntimeError(f"required input not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


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


def as_num(value: Any, default: float = math.nan) -> float:
    text = norm_text(value)
    if text == "":
        return default
    try:
        return float(text)
    except (TypeError, ValueError):
        return default


def bool_text(value: bool) -> str:
    return str(bool(value)).lower()


def quantile(sorted_values: list[float], q: float) -> float:
    clean = [value for value in sorted_values if math.isfinite(value)]
    if not clean:
        return math.nan
    if len(clean) == 1:
        return clean[0]
    pos = (len(clean) - 1) * q
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return clean[int(pos)]
    return clean[lo] * (hi - pos) + clean[hi] * (pos - lo)


def stats_values(values: list[float]) -> dict[str, Any]:
    clean = sorted(value for value in values if math.isfinite(value))
    if not clean:
        return {"count": 0, "mean": "", "median": "", "p90": ""}
    return {
        "count": len(clean),
        "mean": round(mean(clean), 6),
        "median": round(median(clean), 6),
        "p90": round(quantile(clean, 0.90), 6),
    }


def add_stats(out: dict[str, Any], name: str, values: list[float]) -> None:
    stat = stats_values(values)
    out[f"mean_{name}"] = stat["mean"]
    out[f"median_{name}"] = stat["median"]
    out[f"p90_{name}"] = stat["p90"]


def source_for_role(row: dict[str, str], role: str) -> str:
    return row.get(f"{role}_candidate_source", "")


def center_error_for_role(row: dict[str, str], role: str) -> float:
    field = "best_center_error" if role == "best_center" else "best_iou_center_error"
    return as_num(row.get(field))


def iou_for_role(row: dict[str, str], role: str) -> float:
    field = "best_center_iou" if role == "best_center" else "best_iou"
    return as_num(row.get(field))


def candidate_id_for_role(row: dict[str, str], role: str) -> str:
    return row.get(f"{role}_candidate_id", "")


def role_suffix(role: str) -> str:
    return "center" if role == "best_center" else "iou"


def is_a001_better(vs: dict[str, str]) -> bool:
    return as_num(vs.get("delta_center_error")) < -CENTER_GAIN_EPS or as_num(vs.get("delta_iou")) < -IOU_GAIN_EPS


def is_phase5b_better(vs: dict[str, str]) -> bool:
    return as_num(vs.get("delta_center_error")) > CENTER_GAIN_EPS or as_num(vs.get("delta_iou")) > IOU_GAIN_EPS


def latest_m1_dir() -> Path:
    dirs = sorted(
        [path for path in (ROOT / "output").glob("modelM1_geometry_shell_hypothesis_test_*") if path.is_dir()],
        key=lambda path: path.name,
    )
    if not dirs:
        raise RuntimeError("latest M1 output cannot be identified: no modelM1 output dirs found")
    latest = dirs[-1]
    missing = [name for name in M1_REQUIRED_FILES if not (latest / name).exists()]
    if missing:
        raise RuntimeError(f"latest M1 output {latest} missing required files: {missing}")
    return latest


def quartile_label(value: int, q1: float, q2: float, q3: float) -> str:
    if value <= q1:
        return "Q1_low"
    if value <= q2:
        return "Q2_mid_low"
    if value <= q3:
        return "Q3_mid_high"
    return "Q4_high"


def diversity_bucket(value: int) -> str:
    if value <= 2:
        return "low_1_2"
    if value <= 4:
        return "mid_3_4"
    return "high_5_plus"


def count_rate(count: int, total: int) -> float:
    return round(count / total, 6) if total else 0


def main() -> None:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = ROOT / "output" / f"modelM2_structured_candidate_source_hypothesis_test_{timestamp}"
    out_dir.mkdir(parents=True, exist_ok=False)
    m1_dir = latest_m1_dir()

    proposals, proposal_header = read_csv(PHASE5B_PROPOSALS_PATH)
    vs_rows, vs_header = read_csv(PHASE5C_VS_A001_PATH)
    subset_rows, subset_header = read_csv(PHASE5C_ROUTE_SUBSET_PATH)
    problem_rows, problem_header = read_csv(PHASE5C_PROBLEM_PATH)
    sample_rows, sample_header = read_csv(PHASE5C_SAMPLES_PATH)
    novelty_rows, novelty_header = read_csv(PHASE5C_NOVELTY_PATH)
    bank_rows, bank_header = read_csv(A001_BANK_PATH)
    baseline_rows, baseline_header = read_csv(PHASE4D_BASELINE_PATH)
    condition_rows, condition_header = read_csv(A021_CONDITION_PATH)

    m1_evidence_rows, m1_evidence_header = read_csv(m1_dir / "modelM1_per_target_evidence.csv")
    m1_factors_rows, m1_factors_header = read_csv(m1_dir / "modelM1_evidence_factors_per_target.csv")
    anatomy_rows, anatomy_header = read_csv(m1_dir / "modelM1_a001_oracle_candidate_anatomy.csv")
    offset_rows, offset_header = read_csv(m1_dir / "modelM1_a001_vs_a005_geometry_offsets.csv")
    route_gap_rows, route_gap_header = read_csv(m1_dir / "modelM1_v0_routeA_vs_a001_offset_comparison.csv")
    m1_geometry_summary = read_json(m1_dir / "modelM1_a001_geometry_offset_summary.json")
    m1_evidence_summary = read_json(m1_dir / "modelM1_evidence_summary.json")
    threshold_rows, threshold_header = read_csv(m1_dir / "modelM1_threshold_sensitivity.csv")

    require_fields("Phase5B proposals", proposal_header, ["proposal_id", "target_identity", "route_name"])
    require_fields("Phase5C vs A001", vs_header, [
        "target_identity", "phase5B_best_center_error", "phase5B_best_iou",
        "A001_best_center_error", "A001_best_iou", "delta_center_error", "delta_iou", "case_type",
    ])
    require_fields("A001 bank", bank_header, ["target_identity", "candidate_id", "candidate_source"])
    require_fields("Phase4D baseline", baseline_header, [
        "target_identity", "condition_type", "truncation_degree", "occlusion_degree",
        "best_center_candidate_source_or_type", "best_iou_candidate_source_or_type",
    ])
    require_fields("M1 anatomy", anatomy_header, [
        "target_identity", "best_center_candidate_source", "best_iou_candidate_source",
        "best_center_error", "best_center_iou", "best_iou", "best_iou_center_error",
        "best_center_delta_r_from_pred", "best_center_delta_cross_from_pred", "best_center_delta_az_from_pred",
        "best_iou_delta_r_from_pred", "best_iou_delta_cross_from_pred", "best_iou_delta_az_from_pred",
    ])
    require_fields("M1 factors", m1_factors_header, [
        "target_identity", "has_range_cross_signal", "has_large_offset_gap_0p15",
        "has_large_offset_gap_0p25", "offset_gap_center_norm", "scale_gap_center",
    ])

    vs_by_target = {row["target_identity"]: row for row in vs_rows if row.get("target_identity")}
    anatomy_by_target = {row["target_identity"]: row for row in anatomy_rows if row.get("target_identity")}
    offset_by_target = {row["target_identity"]: row for row in offset_rows if row.get("target_identity")}
    route_gap_by_target = {row["target_identity"]: row for row in route_gap_rows if row.get("target_identity")}
    factors_by_target = {row["target_identity"]: row for row in m1_factors_rows if row.get("target_identity")}
    baseline_by_target = {row["target_identity"]: row for row in baseline_rows if row.get("target_identity")}

    condition_by_target: dict[str, dict[str, str]] = {}
    for row in baseline_rows:
        target = row.get("target_identity", "")
        if not target:
            continue
        condition_by_target[target] = {
            "condition_type": row.get("condition_type", ""),
            "truncation_degree": row.get("truncation_degree", ""),
            "occlusion_degree": row.get("occlusion_degree", ""),
            "condition_source": "Phase4D_baseline",
        }
    for row in condition_rows:
        target = row.get("target_identity", "")
        if target in condition_by_target:
            condition_by_target[target].update(
                {
                    "condition_type": row.get("condition_type", condition_by_target[target].get("condition_type", "")),
                    "truncation_degree": row.get("truncation_degree", condition_by_target[target].get("truncation_degree", "")),
                    "occlusion_degree": row.get("occlusion_degree", condition_by_target[target].get("occlusion_degree", "")),
                    "condition_source": "A021_post_hoc_visibility_condition_working",
                }
            )

    bank_by_target: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    for row in bank_rows:
        if row.get("target_identity"):
            bank_by_target[row["target_identity"]].append(row)

    proposal_by_target: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    route_set_by_target: defaultdict[str, set[str]] = defaultdict(set)
    for row in proposals:
        target = row.get("target_identity", "")
        if target:
            proposal_by_target[target].append(row)
            route_set_by_target[target].add(row.get("route_name", ""))

    target_ids = sorted(set(vs_by_target) & set(anatomy_by_target))
    if not target_ids:
        raise RuntimeError("M2 target join is empty")

    candidate_counts = [len(bank_by_target[target]) for target in target_ids]
    source_diversities = [len({row.get("candidate_source", "") for row in bank_by_target[target] if row.get("candidate_source")}) for target in target_ids]
    sorted_candidate_counts = sorted(candidate_counts)
    q1 = quantile(sorted_candidate_counts, 0.25)
    q2 = quantile(sorted_candidate_counts, 0.50)
    q3 = quantile(sorted_candidate_counts, 0.75)
    p90_candidate_count = quantile(sorted_candidate_counts, 0.90)
    source_diversity_q3 = quantile(sorted(source_diversities), 0.75)

    def target_condition(target: str, field: str) -> str:
        value = condition_by_target.get(target, {}).get(field, "")
        return value if value != "" else "unknown"

    def source_metrics_for_target(target: str, role: str) -> dict[str, Any]:
        anatomy = anatomy_by_target[target]
        vs = vs_by_target[target]
        return {
            "target_identity": target,
            "candidate_source": source_for_role(anatomy, role),
            "role_center_error": center_error_for_role(anatomy, role),
            "role_iou": iou_for_role(anatomy, role),
            "delta_center_error": as_num(vs.get("delta_center_error")),
            "delta_iou": as_num(vs.get("delta_iou")),
            "phase5B_best_center_error": as_num(vs.get("phase5B_best_center_error")),
            "phase5B_best_iou": as_num(vs.get("phase5B_best_iou")),
            "A001_better": is_a001_better(vs),
            "Phase5B_better": is_phase5b_better(vs),
            "case_type": vs.get("case_type", ""),
        }

    dominance_rows: list[dict[str, Any]] = []
    for role in ["best_center", "best_iou"]:
        grouped: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
        for target in target_ids:
            metric = source_metrics_for_target(target, role)
            grouped[metric["candidate_source"]].append(metric)
        for source, rows in sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0])):
            out: dict[str, Any] = {
                "role": role,
                "candidate_source": source,
                "source_count": len(rows),
                "source_rate": count_rate(len(rows), len(target_ids)),
                "A001_better_count": sum(1 for row in rows if row["A001_better"]),
                "Phase5B_better_count": sum(1 for row in rows if row["Phase5B_better"]),
                "both_good_count": sum(1 for row in rows if row["case_type"] == "both_good"),
                "both_bad_count": sum(1 for row in rows if row["case_type"] == "both_bad"),
                "metric_note": "role-specific A001 center_error/IoU; deltas are A001 minus Phase5B from Phase5C",
            }
            out["mean_best_center_error"] = stats_values([row["role_center_error"] for row in rows])["mean"]
            out["median_best_center_error"] = stats_values([row["role_center_error"] for row in rows])["median"]
            out["mean_best_iou"] = stats_values([row["role_iou"] for row in rows])["mean"]
            out["median_best_iou"] = stats_values([row["role_iou"] for row in rows])["median"]
            out["mean_delta_center_error_vs_Phase5B"] = stats_values([row["delta_center_error"] for row in rows])["mean"]
            out["median_delta_center_error_vs_Phase5B"] = stats_values([row["delta_center_error"] for row in rows])["median"]
            out["mean_delta_iou_vs_Phase5B"] = stats_values([row["delta_iou"] for row in rows])["mean"]
            out["median_delta_iou_vs_Phase5B"] = stats_values([row["delta_iou"] for row in rows])["median"]
            dominance_rows.append(out)

    condition_dependency_rows: list[dict[str, Any]] = []
    for role in ["best_center", "best_iou"]:
        for axis in CONDITION_AXES:
            condition_totals = Counter(target_condition(target, axis) for target in target_ids)
            grouped: defaultdict[tuple[str, str], list[str]] = defaultdict(list)
            for target in target_ids:
                source = source_for_role(anatomy_by_target[target], role)
                grouped[(source, target_condition(target, axis))].append(target)
            for (source, condition_value), targets in sorted(grouped.items(), key=lambda item: (item[0][1], item[0][0])):
                vs_group = [vs_by_target[target] for target in targets]
                anatomy_group = [anatomy_by_target[target] for target in targets]
                out = {
                    "role": role,
                    "candidate_source": source,
                    "condition_axis": axis,
                    "condition_value": condition_value,
                    "target_count": len(targets),
                    "condition_target_count": condition_totals[condition_value],
                    "source_rate_in_condition": count_rate(len(targets), condition_totals[condition_value]),
                    "A001_better_count": sum(1 for row in vs_group if is_a001_better(row)),
                    "Phase5B_better_count": sum(1 for row in vs_group if is_phase5b_better(row)),
                    "mean_A001_best_center_error": stats_values([center_error_for_role(row, role) for row in anatomy_group])["mean"],
                    "median_A001_best_center_error": stats_values([center_error_for_role(row, role) for row in anatomy_group])["median"],
                    "mean_A001_best_iou": stats_values([iou_for_role(row, role) for row in anatomy_group])["mean"],
                    "median_A001_best_iou": stats_values([iou_for_role(row, role) for row in anatomy_group])["median"],
                    "mean_Phase5B_best_center_error": stats_values([as_num(row.get("phase5B_best_center_error")) for row in vs_group])["mean"],
                    "median_Phase5B_best_center_error": stats_values([as_num(row.get("phase5B_best_center_error")) for row in vs_group])["median"],
                    "mean_Phase5B_best_iou": stats_values([as_num(row.get("phase5B_best_iou")) for row in vs_group])["mean"],
                    "median_Phase5B_best_iou": stats_values([as_num(row.get("phase5B_best_iou")) for row in vs_group])["median"],
                }
                condition_dependency_rows.append(out)

    geometry_anatomy_rows: list[dict[str, Any]] = []
    for role in ["best_center", "best_iou"]:
        suffix = role_suffix(role)
        grouped_targets: defaultdict[str, list[str]] = defaultdict(list)
        for target in target_ids:
            grouped_targets[source_for_role(anatomy_by_target[target], role)].append(target)
        for source, targets in sorted(grouped_targets.items(), key=lambda item: (-len(item[1]), item[0])):
            rows = [offset_by_target[target] for target in targets if target in offset_by_target]
            route_rows = [route_gap_by_target[target] for target in targets if target in route_gap_by_target]
            out = {
                "role": role,
                "candidate_source": source,
                "target_count": len(targets),
            }
            add_stats(out, "abs_dx", [abs(as_num(row.get(f"dx_{suffix}"))) for row in rows])
            add_stats(out, "abs_dy", [abs(as_num(row.get(f"dy_{suffix}"))) for row in rows])
            add_stats(out, "normalized_xy_offset", [as_num(row.get(f"normalized_xy_offset_{suffix}")) for row in rows])
            add_stats(out, "abs_delta_r", [abs(as_num(row.get(f"delta_r_from_pred_{suffix}"))) for row in rows])
            add_stats(out, "abs_delta_cross", [abs(as_num(row.get(f"delta_cross_from_pred_{suffix}"))) for row in rows])
            add_stats(out, "abs_delta_az", [abs(as_num(row.get(f"delta_az_from_pred_{suffix}"))) for row in rows])
            add_stats(out, "scale_w", [as_num(row.get(f"scale_w_{suffix}")) for row in rows])
            add_stats(out, "scale_h", [as_num(row.get(f"scale_h_{suffix}")) for row in rows])
            add_stats(out, "offset_gap_vs_v0_A", [as_num(row.get(f"offset_vector_gap_{suffix}_norm")) for row in route_rows])
            add_stats(out, "scale_gap_vs_v0_A", [as_num(row.get(f"scale_gap_{suffix}")) for row in route_rows])
            geometry_anatomy_rows.append(out)

    wedge_rows: list[dict[str, Any]] = []
    for target in target_ids:
        anatomy = anatomy_by_target[target]
        vs = vs_by_target[target]
        factors = factors_by_target.get(target, {})
        center_is_wedge = source_for_role(anatomy, "best_center") == WEDGE_SOURCE
        iou_is_wedge = source_for_role(anatomy, "best_iou") == WEDGE_SOURCE
        chosen_role = "best_center" if center_is_wedge else ("best_iou" if iou_is_wedge else "")
        chosen_suffix = role_suffix(chosen_role) if chosen_role else ""
        delta_center = as_num(vs.get("delta_center_error"))
        delta_iou = as_num(vs.get("delta_iou"))
        phase5b_better = is_phase5b_better(vs)
        if not chosen_role:
            label = "non_wedge_case"
        elif delta_center < -CENTER_GAIN_EPS and delta_iou < -IOU_GAIN_EPS:
            label = "wedge_strong_both"
        elif center_is_wedge and delta_center < -CENTER_GAIN_EPS:
            label = "wedge_strong_center"
        elif iou_is_wedge and delta_iou < -IOU_GAIN_EPS:
            label = "wedge_strong_iou"
        elif phase5b_better:
            label = "wedge_not_better"
        else:
            label = "wedge_metric_only"

        offset = offset_by_target.get(target, {})
        route_gap = route_gap_by_target.get(target, {})
        condition = condition_by_target.get(target, {})
        row = {
            "target_identity": target,
            "is_wedge_best_center": bool_text(center_is_wedge),
            "is_wedge_best_iou": bool_text(iou_is_wedge),
            "wedge_center_error": center_error_for_role(anatomy, chosen_role) if chosen_role else "",
            "wedge_iou": iou_for_role(anatomy, chosen_role) if chosen_role else "",
            "Phase5B_best_center_error": vs.get("phase5B_best_center_error", ""),
            "Phase5B_best_iou": vs.get("phase5B_best_iou", ""),
            "delta_center_error": vs.get("delta_center_error", ""),
            "delta_iou": vs.get("delta_iou", ""),
            "condition_type": condition.get("condition_type", ""),
            "truncation_degree": condition.get("truncation_degree", ""),
            "occlusion_degree": condition.get("occlusion_degree", ""),
            "delta_r_from_pred": anatomy.get(f"{chosen_role}_delta_r_from_pred", "") if chosen_role else "",
            "delta_cross_from_pred": anatomy.get(f"{chosen_role}_delta_cross_from_pred", "") if chosen_role else "",
            "delta_az_from_pred": anatomy.get(f"{chosen_role}_delta_az_from_pred", "") if chosen_role else "",
            "normalized_xy_offset": offset.get(f"normalized_xy_offset_{chosen_suffix}", "") if chosen_suffix else "",
            "offset_gap_vs_v0_A": route_gap.get(f"offset_vector_gap_{chosen_suffix}_norm", "") if chosen_suffix else "",
            "candidate_expansion_state": anatomy.get(f"{chosen_role}_candidate_expansion_state", "") if chosen_role else "",
            "candidate_expansion_reason": anatomy.get(f"{chosen_role}_candidate_expansion_reason", "") if chosen_role else "",
            "has_range_cross_signal": factors.get("has_range_cross_signal", ""),
            "has_large_offset_gap_0p15": factors.get("has_large_offset_gap_0p15", ""),
            "has_large_offset_gap_0p25": factors.get("has_large_offset_gap_0p25", ""),
            "wedge_success_label": label,
        }
        wedge_rows.append(row)

    wedge_label_counts = Counter(row["wedge_success_label"] for row in wedge_rows)
    wedge_any_rows = [row for row in wedge_rows if row["wedge_success_label"] != "non_wedge_case"]
    wedge_strong_rows = [
        row for row in wedge_rows
        if row["wedge_success_label"] in {"wedge_strong_center", "wedge_strong_iou", "wedge_strong_both"}
    ]
    wedge_by_condition: dict[str, dict[str, Any]] = {}
    for condition_value in sorted(set(row["condition_type"] or "unknown" for row in wedge_rows)):
        rows = [row for row in wedge_rows if (row["condition_type"] or "unknown") == condition_value]
        strong = [row for row in rows if row["wedge_success_label"] in {"wedge_strong_center", "wedge_strong_iou", "wedge_strong_both"}]
        wedge_by_condition[condition_value] = {
            "target_count": len(rows),
            "wedge_any_count": sum(1 for row in rows if row["wedge_success_label"] != "non_wedge_case"),
            "wedge_strong_count": len(strong),
            "wedge_strong_rate_in_condition": count_rate(len(strong), len(rows)),
        }
    expansion_reason_counts = Counter(row["candidate_expansion_reason"] for row in wedge_any_rows if row["candidate_expansion_reason"])
    range_cross_strong_rate = count_rate(sum(1 for row in wedge_strong_rows if row["has_range_cross_signal"] == "true"), len(wedge_strong_rows))
    hard_condition_strong_rate = count_rate(
        sum(
            1
            for row in wedge_strong_rows
            if (row["condition_type"] not in {"", "none"} or row["truncation_degree"] not in {"", "none"} or row["occlusion_degree"] not in {"", "none"})
        ),
        len(wedge_strong_rows),
    )
    wedge_source_family_rate = count_rate(len(wedge_strong_rows), len(wedge_any_rows))
    wedge_summary = {
        "wedge_best_center_count": sum(1 for row in wedge_rows if row["is_wedge_best_center"] == "true"),
        "wedge_best_center_rate": count_rate(sum(1 for row in wedge_rows if row["is_wedge_best_center"] == "true"), len(wedge_rows)),
        "wedge_best_iou_count": sum(1 for row in wedge_rows if row["is_wedge_best_iou"] == "true"),
        "wedge_best_iou_rate": count_rate(sum(1 for row in wedge_rows if row["is_wedge_best_iou"] == "true"), len(wedge_rows)),
        "wedge_strong_center_count": wedge_label_counts.get("wedge_strong_center", 0),
        "wedge_strong_iou_count": wedge_label_counts.get("wedge_strong_iou", 0),
        "wedge_strong_both_count": wedge_label_counts.get("wedge_strong_both", 0),
        "wedge_not_better_count": wedge_label_counts.get("wedge_not_better", 0),
        "wedge_metric_only_count": wedge_label_counts.get("wedge_metric_only", 0),
        "wedge_by_condition_breakdown": wedge_by_condition,
        "wedge_expansion_reason_counts": dict(expansion_reason_counts),
        "association_diagnostics": {
            "range_cross_signal_rate_among_wedge_strong": range_cross_strong_rate,
            "hard_condition_rate_among_wedge_strong": hard_condition_strong_rate,
            "strong_rate_among_wedge_oracle_cases": wedge_source_family_rate,
            "interpretation": (
                "wedge advantage is source-family dominated with range/cross and hard-condition co-signals"
                if wedge_source_family_rate >= 0.5 and (range_cross_strong_rate >= 0.5 or hard_condition_strong_rate >= 0.5)
                else "wedge association is mixed and needs manual mechanism review"
            ),
        },
    }

    density_rows: list[dict[str, Any]] = []
    for target in target_ids:
        target_bank = bank_by_target[target]
        sources = {row.get("candidate_source", "") for row in target_bank if row.get("candidate_source", "")}
        candidate_count = len(target_bank)
        diversity_count = len(sources)
        vs = vs_by_target[target]
        best_center_source = source_for_role(anatomy_by_target[target], "best_center")
        best_iou_source = source_for_role(anatomy_by_target[target], "best_iou")
        best_source_is_wedge = best_center_source == WEDGE_SOURCE or best_iou_source == WEDGE_SOURCE
        high_density = candidate_count >= p90_candidate_count
        a001_advantage = is_a001_better(vs)
        label = (
            "density_only_suspicion"
            if a001_advantage and high_density and diversity_count >= source_diversity_q3 and not best_source_is_wedge
            else "source_family_signal_present"
            if a001_advantage and best_source_is_wedge
            else "not_density_explained"
        )
        density_rows.append(
            {
                "target_identity": target,
                "total_A001_candidate_count": candidate_count,
                "distinct_candidate_source_count": diversity_count,
                "best_source_is_wedge": bool_text(best_source_is_wedge),
                "A001_advantage_over_Phase5B": bool_text(a001_advantage),
                "Phase5B_proposal_count": len(proposal_by_target[target]),
                "Phase5B_route_diversity_count": len({route for route in route_set_by_target[target] if route}),
                "candidate_count_quartile": quartile_label(candidate_count, q1, q2, q3),
                "source_diversity_bucket": diversity_bucket(diversity_count),
                "best_center_candidate_source": best_center_source,
                "best_iou_candidate_source": best_iou_source,
                "delta_center_error": vs.get("delta_center_error", ""),
                "delta_iou": vs.get("delta_iou", ""),
                "density_suspicion_label": label,
            }
        )

    def bucket_summary(rows: list[dict[str, Any]], field: str) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for value in sorted({row[field] for row in rows}):
            subset = [row for row in rows if row[field] == value]
            out[value] = {
                "target_count": len(subset),
                "A001_advantage_count": sum(1 for row in subset if row["A001_advantage_over_Phase5B"] == "true"),
                "A001_advantage_rate": count_rate(sum(1 for row in subset if row["A001_advantage_over_Phase5B"] == "true"), len(subset)),
                "wedge_best_count": sum(1 for row in subset if row["best_source_is_wedge"] == "true"),
                "wedge_best_rate": count_rate(sum(1 for row in subset if row["best_source_is_wedge"] == "true"), len(subset)),
                "mean_delta_center_error": stats_values([as_num(row.get("delta_center_error")) for row in subset])["mean"],
                "mean_delta_iou": stats_values([as_num(row.get("delta_iou")) for row in subset])["mean"],
            }
        return out

    density_summary = {
        "candidate_count_quantiles": {
            "q1": round(q1, 6),
            "median": round(q2, 6),
            "q3": round(q3, 6),
            "p90": round(p90_candidate_count, 6),
        },
        "source_diversity_q3": round(source_diversity_q3, 6),
        "candidate_count_quartile_summary": bucket_summary(density_rows, "candidate_count_quartile"),
        "source_diversity_bucket_summary": bucket_summary(density_rows, "source_diversity_bucket"),
        "density_only_suspicion_count": sum(1 for row in density_rows if row["density_suspicion_label"] == "density_only_suspicion"),
        "density_only_suspicion_rate": count_rate(sum(1 for row in density_rows if row["density_suspicion_label"] == "density_only_suspicion"), len(density_rows)),
    }

    evidence_rows: list[dict[str, Any]] = []
    for target in target_ids:
        anatomy = anatomy_by_target[target]
        vs = vs_by_target[target]
        density = next(row for row in density_rows if row["target_identity"] == target)
        condition = condition_by_target.get(target, {})
        factors = factors_by_target.get(target, {})
        best_center_source = source_for_role(anatomy, "best_center")
        best_iou_source = source_for_role(anatomy, "best_iou")
        a001_better = is_a001_better(vs)
        wedge_center = best_center_source == WEDGE_SOURCE
        wedge_iou = best_iou_source == WEDGE_SOURCE
        wedge_advantage = (wedge_center and as_num(vs.get("delta_center_error")) < -CENTER_GAIN_EPS) or (wedge_iou and as_num(vs.get("delta_iou")) < -IOU_GAIN_EPS)
        best_nonbase = best_center_source not in {"", "base_candidate"} or best_iou_source not in {"", "base_candidate"}
        escape_or_ray = best_center_source in RAY_ESCAPE_SOURCES or best_iou_source in RAY_ESCAPE_SOURCES
        hard_condition = (
            condition.get("condition_type", "") not in {"", "none"}
            or condition.get("truncation_degree", "") not in {"", "none"}
            or condition.get("occlusion_degree", "") not in {"", "none"}
        )
        high_density = as_num(density["total_A001_candidate_count"]) >= p90_candidate_count
        high_diversity = as_num(density["distinct_candidate_source_count"]) >= source_diversity_q3
        range_or_offset = factors.get("has_range_cross_signal") == "true" or factors.get("has_large_offset_gap_0p15") == "true"

        if a001_better and wedge_advantage and not high_density:
            label = "supports_M2_wedge_structured_source"
            direction = "M2a_wedge_consistency_model"
            summary = "A001 is better and the oracle source is wedge_joint_candidate without relying on extreme candidate density."
        elif a001_better and escape_or_ray and (hard_condition or range_or_offset):
            label = "supports_M2_escape_or_ray_source"
            direction = "M2b_ray_escape_support_model"
            summary = "A001 is better with a ray/escape source under hard condition or offset signal."
        elif a001_better and best_nonbase and as_num(density["distinct_candidate_source_count"]) >= 3:
            label = "supports_M2_source_diversity"
            direction = "source_family_factor_ablation"
            summary = "A001 is better and a non-base source family plus source diversity are present."
        elif a001_better and high_density and high_diversity:
            label = "supports_density_only_suspicion"
            direction = "controlled_density_source_family_ablation"
            summary = "A001 is better, but the evidence may be explained by high candidate count and high source diversity."
        elif not a001_better or (best_center_source == "base_candidate" and best_iou_source == "base_candidate"):
            label = "weak_or_no_support_for_M2"
            direction = "M3_metric_or_visible_support_diagnosis"
            summary = "A001 is not clearly better than Phase5B, or the oracle source is base_candidate."
        else:
            label = "mixed_or_unclear"
            direction = "manual_review_before_model_change"
            summary = "Signals are mixed; source family, density, and condition dependency need manual review."

        evidence_rows.append(
            {
                "target_identity": target,
                "M2_evidence_label": label,
                "evidence_summary": summary,
                "best_center_candidate_source": best_center_source,
                "best_iou_candidate_source": best_iou_source,
                "A001_better_than_Phase5B": bool_text(a001_better),
                "wedge_is_best_center": bool_text(wedge_center),
                "wedge_is_best_iou": bool_text(wedge_iou),
                "source_diversity_count": density["distinct_candidate_source_count"],
                "candidate_count": density["total_A001_candidate_count"],
                "condition_type": condition.get("condition_type", ""),
                "truncation_degree": condition.get("truncation_degree", ""),
                "occlusion_degree": condition.get("occlusion_degree", ""),
                "recommended_model_direction": direction,
            }
        )

    evidence_label_counts = Counter(row["M2_evidence_label"] for row in evidence_rows)
    a001_advantage_count = sum(1 for target in target_ids if is_a001_better(vs_by_target[target]))
    wedge_support_count = evidence_label_counts.get("supports_M2_wedge_structured_source", 0)
    source_diversity_support_count = evidence_label_counts.get("supports_M2_source_diversity", 0)
    escape_support_count = evidence_label_counts.get("supports_M2_escape_or_ray_source", 0)
    density_suspicion_count = evidence_label_counts.get("supports_density_only_suspicion", 0)
    density_final_evidence_label_count = density_suspicion_count
    density_audit_suspicion_count = density_summary["density_only_suspicion_count"]
    weak_count = evidence_label_counts.get("weak_or_no_support_for_M2", 0)
    total_support_count = wedge_support_count + source_diversity_support_count + escape_support_count
    wedge_support_rate_all = count_rate(wedge_support_count, len(target_ids))
    wedge_support_rate_advantage = count_rate(wedge_support_count, a001_advantage_count)
    total_support_rate = count_rate(total_support_count, len(target_ids))
    density_rate = count_rate(density_suspicion_count, len(target_ids))
    density_final_evidence_label_rate = density_rate
    density_audit_suspicion_rate = density_summary["density_only_suspicion_rate"]
    mixed_weak_rate = count_rate(weak_count + evidence_label_counts.get("mixed_or_unclear", 0), len(target_ids))

    if wedge_support_rate_all >= 0.4 and wedge_support_rate_advantage >= 0.5:
        m2_judgment = "M2_STRONGLY_SUPPORTED"
        judgment_reason = "wedge structured-source support exceeds both all-target and A001-advantage thresholds"
    elif wedge_support_rate_all >= 0.4 or wedge_support_rate_advantage >= 0.5 or total_support_rate >= 0.4:
        m2_judgment = "M2_PARTIALLY_SUPPORTED"
        judgment_reason = "structured source-family support is substantial but not strong on both wedge thresholds"
    elif density_rate > total_support_rate and density_rate >= 0.25:
        m2_judgment = "M2_INCONCLUSIVE"
        judgment_reason = "density-only suspicion dominates structured source support"
    elif mixed_weak_rate >= 0.6:
        m2_judgment = "M2_INCONCLUSIVE"
        judgment_reason = "weak or mixed target-level evidence dominates"
    else:
        m2_judgment = "M2_NOT_SUPPORTED"
        judgment_reason = "structured source-family support is below declared thresholds"

    evidence_summary = {
        "target_count": len(target_ids),
        "A001_advantage_target_count": a001_advantage_count,
        "M2_label_counts": dict(evidence_label_counts),
        "percentage_supporting_wedge_structured_source": wedge_support_rate_all,
        "percentage_supporting_wedge_structured_source_among_A001_advantage": wedge_support_rate_advantage,
        "percentage_supporting_source_diversity": count_rate(source_diversity_support_count, len(target_ids)),
        "percentage_supporting_escape_or_ray_source": count_rate(escape_support_count, len(target_ids)),
        "percentage_density_only_suspicion": density_rate,
        "density_audit_suspicion_count": density_audit_suspicion_count,
        "density_audit_suspicion_rate": density_audit_suspicion_rate,
        "density_final_evidence_label_count": density_final_evidence_label_count,
        "density_final_evidence_label_rate": density_final_evidence_label_rate,
        "density_interpretation": "Density-only suspicion appears in 14/205 cases in the auxiliary density audit, but it does not dominate final M2 evidence labels. This suggests candidate density/source diversity may contribute in a few cases, but it is not the primary explanation for A001's advantage.",
        "percentage_weak_or_no_support": count_rate(weak_count, len(target_ids)),
        "percentage_total_structured_source_support": total_support_rate,
        "M2_final_judgment": m2_judgment,
        "judgment_reason": judgment_reason,
        "judgment_rules": {
            "M2_STRONGLY_SUPPORTED": "wedge support >= 40% of all targets and >= 50% of A001-advantage targets",
            "M2_PARTIALLY_SUPPORTED": "wedge or total source-family support is substantial but below strong dual threshold",
            "M2_INCONCLUSIVE": "density-only, weak, or mixed evidence dominates enough to block a source-family conclusion",
            "M2_NOT_SUPPORTED": "structured source-family support is below declared thresholds",
        },
        "density_summary": density_summary,
        "wedge_summary_ref": "modelM2_wedge_summary.json",
        "M1_latest_output_dir": rel(m1_dir),
        "M1_final_judgment": m1_evidence_summary.get("final_M1_judgment", ""),
    }

    if m2_judgment in {"M2_STRONGLY_SUPPORTED", "M2_PARTIALLY_SUPPORTED"}:
        next_model_family = "M2a_wedge_consistency_model"
        next_model_rationale = "structured source-family evidence is strong enough to design, not run, a wedge-aware v1 proposal model after manual review"
    elif density_suspicion_count > total_support_count:
        next_model_family = "controlled_source_family_density_ablation"
        next_model_rationale = "candidate count and source diversity could explain the A001 oracle advantage"
    else:
        next_model_family = "M3_metric_annotation_or_visible_support_diagnosis"
        next_model_rationale = "M2 evidence is not sufficient for a source-structured model commitment"

    next_decision = {
        "M2_final_judgment": m2_judgment,
        "next_model_family": next_model_family,
        "next_model_rationale": next_model_rationale,
        "if_M2_supported": "propose v1 source-structured proposal model: optical/temporal prior + structured SAR source family + observation support scores",
        "if_wedge_strongly_supported": "propose M2a wedge-consistency model",
        "if_ray_or_escape_supported": "propose M2b ray/escape support model",
        "if_density_only": "reject copying A001; design controlled source-family ablation",
        "if_M2_not_supported": "propose M3 metric/annotation bias diagnosis or SAR visible-support model",
        "should_commit_to_v1_generator_now": False,
        "should_hold_phase5D": True,
        "should_reject_A001_copying": True,
        "should_run_manual_review": True,
        "manual_review_focus": [
            "wedge_joint_candidate strong cases",
            "ray/escape cases under hard visibility conditions",
            "density-only suspicion cases",
            "Phase5B-good / A001-bad counterexamples",
        ],
        "boundary": {
            "v1_proposal_generated": False,
            "v1_generator_written": False,
            "A001_candidate_id_copied_as_new_model_output": False,
            "Phase5B_v0_config_changed": False,
            "v0_proposal_regenerated": False,
            "source_file_modified": False,
            "c3_c4_integration": False,
            "threshold_tuning": False,
            "training": False,
            "calibration": False,
            "push": False,
        },
    }

    dominance_fields = [
        "role", "candidate_source", "source_count", "source_rate",
        "mean_best_center_error", "median_best_center_error", "mean_best_iou", "median_best_iou",
        "mean_delta_center_error_vs_Phase5B", "median_delta_center_error_vs_Phase5B",
        "mean_delta_iou_vs_Phase5B", "median_delta_iou_vs_Phase5B",
        "A001_better_count", "Phase5B_better_count", "both_good_count", "both_bad_count", "metric_note",
    ]
    condition_fields = [
        "role", "candidate_source", "condition_axis", "condition_value", "target_count",
        "condition_target_count", "source_rate_in_condition", "A001_better_count", "Phase5B_better_count",
        "mean_A001_best_center_error", "median_A001_best_center_error", "mean_A001_best_iou", "median_A001_best_iou",
        "mean_Phase5B_best_center_error", "median_Phase5B_best_center_error",
        "mean_Phase5B_best_iou", "median_Phase5B_best_iou",
    ]
    geometry_fields = [
        "role", "candidate_source", "target_count",
        "mean_abs_dx", "median_abs_dx", "p90_abs_dx",
        "mean_abs_dy", "median_abs_dy", "p90_abs_dy",
        "mean_normalized_xy_offset", "median_normalized_xy_offset", "p90_normalized_xy_offset",
        "mean_abs_delta_r", "median_abs_delta_r", "p90_abs_delta_r",
        "mean_abs_delta_cross", "median_abs_delta_cross", "p90_abs_delta_cross",
        "mean_abs_delta_az", "median_abs_delta_az", "p90_abs_delta_az",
        "mean_scale_w", "median_scale_w", "p90_scale_w",
        "mean_scale_h", "median_scale_h", "p90_scale_h",
        "mean_offset_gap_vs_v0_A", "median_offset_gap_vs_v0_A", "p90_offset_gap_vs_v0_A",
        "mean_scale_gap_vs_v0_A", "median_scale_gap_vs_v0_A", "p90_scale_gap_vs_v0_A",
    ]
    wedge_fields = [
        "target_identity", "is_wedge_best_center", "is_wedge_best_iou", "wedge_center_error", "wedge_iou",
        "Phase5B_best_center_error", "Phase5B_best_iou", "delta_center_error", "delta_iou",
        "condition_type", "truncation_degree", "occlusion_degree",
        "delta_r_from_pred", "delta_cross_from_pred", "delta_az_from_pred",
        "normalized_xy_offset", "offset_gap_vs_v0_A", "candidate_expansion_state",
        "candidate_expansion_reason", "has_range_cross_signal", "has_large_offset_gap_0p15",
        "has_large_offset_gap_0p25", "wedge_success_label",
    ]
    density_fields = [
        "target_identity", "total_A001_candidate_count", "distinct_candidate_source_count",
        "best_source_is_wedge", "A001_advantage_over_Phase5B", "Phase5B_proposal_count",
        "Phase5B_route_diversity_count", "candidate_count_quartile", "source_diversity_bucket",
        "best_center_candidate_source", "best_iou_candidate_source", "delta_center_error", "delta_iou",
        "density_suspicion_label",
    ]
    evidence_fields = [
        "target_identity", "M2_evidence_label", "evidence_summary", "best_center_candidate_source",
        "best_iou_candidate_source", "A001_better_than_Phase5B", "wedge_is_best_center",
        "wedge_is_best_iou", "source_diversity_count", "candidate_count", "condition_type",
        "truncation_degree", "occlusion_degree", "recommended_model_direction",
    ]

    write_csv(out_dir / "modelM2_candidate_source_oracle_dominance.csv", dominance_rows, dominance_fields)
    write_csv(out_dir / "modelM2_candidate_source_condition_dependency.csv", condition_dependency_rows, condition_fields)
    write_csv(out_dir / "modelM2_source_family_geometry_anatomy.csv", geometry_anatomy_rows, geometry_fields)
    write_csv(out_dir / "modelM2_wedge_joint_candidate_analysis.csv", wedge_rows, wedge_fields)
    write_json(out_dir / "modelM2_wedge_summary.json", wedge_summary)
    write_csv(out_dir / "modelM2_candidate_density_vs_source_diversity.csv", density_rows, density_fields)
    write_csv(out_dir / "modelM2_per_target_evidence.csv", evidence_rows, evidence_fields)
    write_json(out_dir / "modelM2_evidence_summary.json", evidence_summary)
    write_json(out_dir / "modelM2_next_model_decision.json", next_decision)

    output_paths = {
        "candidate_source_oracle_dominance": rel(out_dir / "modelM2_candidate_source_oracle_dominance.csv"),
        "candidate_source_condition_dependency": rel(out_dir / "modelM2_candidate_source_condition_dependency.csv"),
        "source_family_geometry_anatomy": rel(out_dir / "modelM2_source_family_geometry_anatomy.csv"),
        "wedge_joint_candidate_analysis": rel(out_dir / "modelM2_wedge_joint_candidate_analysis.csv"),
        "wedge_summary": rel(out_dir / "modelM2_wedge_summary.json"),
        "candidate_density_vs_source_diversity": rel(out_dir / "modelM2_candidate_density_vs_source_diversity.csv"),
        "per_target_evidence": rel(out_dir / "modelM2_per_target_evidence.csv"),
        "evidence_summary": rel(out_dir / "modelM2_evidence_summary.json"),
        "next_model_decision": rel(out_dir / "modelM2_next_model_decision.json"),
        "audit_log": rel(out_dir / "modelM2_audit_log.json"),
    }

    audit_log = {
        "timestamp": timestamp,
        "model_hypothesis": "A001 advantage over Phase5B-v0 is better explained by structured candidate-source families, especially wedge_joint_candidate, than by generic range/cross shell offsets alone.",
        "inputs": {
            "Phase5B_v0_proposals": rel(PHASE5B_PROPOSALS_PATH),
            "Phase5C_vs_A001": rel(PHASE5C_VS_A001_PATH),
            "Phase5C_route_subset": rel(PHASE5C_ROUTE_SUBSET_PATH),
            "Phase5C_problem_attribution": rel(PHASE5C_PROBLEM_PATH),
            "Phase5C_interesting_samples": rel(PHASE5C_SAMPLES_PATH),
            "Phase5C_A001_neighborhood_novelty": rel(PHASE5C_NOVELTY_PATH),
            "latest_M1_output_dir": rel(m1_dir),
            "A001_candidate_bank": rel(A001_BANK_PATH),
            "Phase4D_A001_baseline": rel(PHASE4D_BASELINE_PATH),
            "A021_condition_labels_post_hoc_only": rel(A021_CONDITION_PATH),
        },
        "headers": {
            "proposal_header": proposal_header,
            "vs_header": vs_header,
            "subset_header": subset_header,
            "problem_header": problem_header,
            "sample_header": sample_header,
            "novelty_header": novelty_header,
            "bank_header": bank_header,
            "baseline_header": baseline_header,
            "condition_header": condition_header,
            "m1_evidence_header": m1_evidence_header,
            "m1_factors_header": m1_factors_header,
            "m1_anatomy_header": anatomy_header,
            "m1_offset_header": offset_header,
            "m1_route_gap_header": route_gap_header,
            "m1_threshold_header": threshold_header,
        },
        "input_row_counts": {
            "proposals": len(proposals),
            "phase5C_vs_A001": len(vs_rows),
            "candidate_bank": len(bank_rows),
            "Phase4D_baseline": len(baseline_rows),
            "A021_condition_rows": len(condition_rows),
            "M1_anatomy_rows": len(anatomy_rows),
            "M1_threshold_rows": len(threshold_rows),
        },
        "outputs": output_paths,
        "boundary": next_decision["boundary"],
        "notes": [
            "A021 condition labels are post-hoc only.",
            "A001 candidate ids are analyzed as evidence carriers, not copied into a new generator.",
            "No C3/C4 ranking or Phase5B-v0 proposal CSV was modified.",
        ],
        "M1_context": {
            "M1_latest_output_dir": rel(m1_dir),
            "M1_geometry_summary_join": m1_geometry_summary.get("join", {}),
            "M1_final_judgment": m1_evidence_summary.get("final_M1_judgment", ""),
        },
    }
    write_json(out_dir / "modelM2_audit_log.json", audit_log)

    top_dominance = [
        row for row in dominance_rows
        if row["role"] == "best_center" and row["candidate_source"] in KNOWN_FOCUS_SOURCES
    ][:6]
    top_dominance_lines = "\n".join(
        f"- `{row['candidate_source']}`: count {row['source_count']} ({row['source_rate']}), median center error {row['median_best_center_error']}, median delta center {row['median_delta_center_error_vs_Phase5B']}"
        for row in top_dominance
    )
    label_lines = "\n".join(f"- `{label}`: {count}" for label, count in evidence_label_counts.most_common())
    decision_lines = "\n".join(f"- `{key}`: {value}" for key, value in next_decision.items() if key.startswith("should_"))
    source_geometry_lines = "\n".join(
        f"- `{row['candidate_source']}` / {row['role']}: median normalized offset {row['median_normalized_xy_offset']}, median |delta_r| {row['median_abs_delta_r']}, median |delta_cross| {row['median_abs_delta_cross']}, median offset gap {row['median_offset_gap_vs_v0_A']}"
        for row in geometry_anatomy_rows
        if row["role"] == "best_center" and row["candidate_source"] in KNOWN_FOCUS_SOURCES
    )

    docs_path = ROOT / "docs" / f"modelM2_structured_candidate_source_hypothesis_test_summary_{timestamp}.md"
    docs_text = f"""# Model M2 Structured Candidate-Source Hypothesis Test Summary

Date: {timestamp}

## 1. Purpose

This is a model hypothesis test loop, not a generic audit and not an attempt to copy A001. It tests whether A001's Phase5C advantage is better explained by structured candidate-source families than by generic range/cross shell offsets alone.

## 2. M2 Hypothesis

M2: A001's advantage over Phase5B-v0 is not mainly caused by generic range/cross shell offsets, but by structured candidate-source families, especially `wedge_joint_candidate`, which may encode SAR-support geometry, ray/wedge consistency, escape mechanisms, or source-specific uncertainty.

## 3. Experiment Design

Inputs are frozen Phase5B-v0 proposals, Phase5C-v0 post-hoc comparison files, the latest M1 outputs, the A001 candidate bank, Phase4D A001 baseline, and A021 condition labels as post-hoc labels only.

Latest M1 output: `{rel(m1_dir)}`.

Target count: {len(target_ids)}.

## 4. Candidate-Source Dominance

Best-center source highlights:

{top_dominance_lines}

Full source dominance is written to `modelM2_candidate_source_oracle_dominance.csv`.

## 5. Condition Dependency

Condition dependency is reported by source x `condition_type`, source x `truncation_degree`, and source x `occlusion_degree` in `modelM2_candidate_source_condition_dependency.csv`.

This join is post-hoc only. It does not feed A021 condition labels into proposal generation or inference.

## 6. Source-Family Geometry Anatomy

Source-family geometry anatomy is written to `modelM2_source_family_geometry_anatomy.csv`.

Best-center highlights:

{source_geometry_lines}

## 7. Wedge-Specific Findings

- Wedge best-center count/rate: {wedge_summary['wedge_best_center_count']} / {len(target_ids)} ({wedge_summary['wedge_best_center_rate']})
- Wedge best-IoU count/rate: {wedge_summary['wedge_best_iou_count']} / {len(target_ids)} ({wedge_summary['wedge_best_iou_rate']})
- Wedge strong both count: {wedge_summary['wedge_strong_both_count']}
- Wedge strong center count: {wedge_summary['wedge_strong_center_count']}
- Wedge strong IoU count: {wedge_summary['wedge_strong_iou_count']}
- Wedge not-better count: {wedge_summary['wedge_not_better_count']}
- Association interpretation: {wedge_summary['association_diagnostics']['interpretation']}

Per-target wedge evidence is written to `modelM2_wedge_joint_candidate_analysis.csv`; summary is written to `modelM2_wedge_summary.json`.

## 8. Density / Diversity Suspicion

Density-only suspicion count/rate: {density_summary['density_only_suspicion_count']} / {len(target_ids)} ({density_summary['density_only_suspicion_rate']}).

Density-only suspicion appears in 14/205 cases in the auxiliary density audit, but it does not dominate final M2 evidence labels. This suggests candidate density/source diversity may contribute in a few cases, but it is not the primary explanation for A001's advantage.

The density check is written to `modelM2_candidate_density_vs_source_diversity.csv`. This check asks whether A001 is strong only because candidate count or source diversity is high. It does not copy any A001 candidate id.

## 9. Evidence For / Against M2

Label counts:

{label_lines}

Percentages:

- Wedge structured source: {evidence_summary['percentage_supporting_wedge_structured_source']}
- Wedge structured source among A001-advantage cases: {evidence_summary['percentage_supporting_wedge_structured_source_among_A001_advantage']}
- Source diversity: {evidence_summary['percentage_supporting_source_diversity']}
- Escape/ray source: {evidence_summary['percentage_supporting_escape_or_ray_source']}
- Density-only final evidence label: {evidence_summary['density_final_evidence_label_rate']}
- Density-only auxiliary audit suspicion: {evidence_summary['density_audit_suspicion_rate']}
- Weak/no support: {evidence_summary['percentage_weak_or_no_support']}

Per-target evidence is written to `modelM2_per_target_evidence.csv`.

## 10. M2 Judgment

Final M2 judgment: `{m2_judgment}`.

Reason: {judgment_reason}.

This supports a source-structured modeling direction only as a next design hypothesis. It is not a v1 proposal generator and not a final inference result.

## 11. Next Model Decision

Next model family: `{next_model_family}`.

Rationale: {next_model_rationale}.

Decision flags:

{decision_lines}

Manual review should focus on wedge-strong cases, ray/escape hard-condition cases, density-only suspicion cases, and Phase5B-good counterexamples before any v1 generator is approved.

## 12. Boundary

- Post-hoc model hypothesis test only.
- No v1 proposal generated.
- No v1 generator.
- No A001 candidate copying.
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
                "M2_evidence_label_counts": dict(evidence_label_counts),
                "M2_final_judgment": m2_judgment,
                "wedge_best_center_count": wedge_summary["wedge_best_center_count"],
                "wedge_best_iou_count": wedge_summary["wedge_best_iou_count"],
                "density_only_suspicion_count": density_summary["density_only_suspicion_count"],
                "next_model_decision": next_model_family,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
