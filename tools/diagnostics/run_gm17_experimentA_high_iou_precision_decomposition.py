#!/usr/bin/env python
"""Run GM17 Experiment A fixed-bank high-IoU precision decomposition.

This script is audit-only. It reads existing Line-FB post-inference audit
columns and frozen rank outputs to decompose high-AABB-proxy precision failure
patterns. It does not recompute IoU, recompute center error, read SAR pixels,
compute descriptors, modify the candidate bank, or modify the GM17 selector.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


SCRIPT_SCOPE = "Experiment_A_fixed_bank_high_iou_precision_decomposition"
FORMAL_PHASE5_STATUS = "BLOCKED_FOR_OOF_CALIBRATION"
SCHEMA_GO_STATUS = "GO_FOR_EXPERIMENT_A_DECOMPOSITION_PROPOSAL"
ALLOWED_JOIN_STATUSES = {"GO", "POLICY_ACCEPTED_GO_FOR_LEFT_COVERAGE"}

DEFAULT_RESOLVER_OUTPUT_DIR = "output/gm17_scattering_artifact_resolver_20260630_013623"
DEFAULT_JOIN_VALIDATION_OUTPUT_DIR = "output/gm17_post_inference_join_key_validation_20260630_091128"
DEFAULT_SCHEMA_VALIDATION_OUTPUT_DIR = "output/gm17_experimentA_schema_validation_20260630_091528"

TARGET_KEY_COLUMNS = ["target_identity", "scene", "sar_frame_num", "gm17_track_id"]

PER_TARGET_REQUIRED_COLUMNS = [
    "target_identity",
    "scene",
    "sar_frame_num",
    "gm17_track_id",
    "candidate_id",
    "pilot_rank",
    "axis_aligned_proxy_iou",
    "center_error",
    "best_proxy_candidate_id",
    "best_proxy_pilot_rank",
    "best_proxy_iou",
    "best_proxy_center_error",
    "best_center_candidate_id",
    "best_center_pilot_rank",
    "best_center_error",
    "best_center_proxy_iou",
]

PER_TARGET_OPTIONAL_CONTEXT_COLUMNS = [
    "condition_type",
    "condition_status",
    "truncation_degree",
    "occlusion_degree",
]

SELECTED_REQUIRED_COLUMNS = [
    "target_identity",
    "scene",
    "sar_frame_num",
    "gm17_track_id",
    "candidate_id",
    "pilot_rank",
]

FROZEN_REQUIRED_COLUMNS = [
    "target_identity",
    "scene",
    "sar_frame_num",
    "gm17_track_id",
    "candidate_id",
    "pilot_rank",
]

A001_SOURCE_COLUMNS = [
    "candidate_id",
    "candidate_source",
    "candidate_detail",
    "candidate_expansion_state",
    "candidate_expansion_reason",
]

OUTPUT_TARGET_COLUMNS = [
    "target_identity",
    "scene",
    "sar_frame_num",
    "gm17_track_id",
    "selected_candidate_id",
    "selected_rank",
    "selected_axis_aligned_proxy_iou",
    "selected_center_error",
    "selected_candidate_source",
    "best_proxy_candidate_id",
    "best_proxy_rank",
    "best_axis_aligned_proxy_iou",
    "best_proxy_center_error",
    "best_proxy_candidate_source",
    "best_center_candidate_id",
    "best_center_rank",
    "best_center_error",
    "best_center_axis_aligned_proxy_iou",
    "best_center_candidate_source",
    "selected_matches_best_proxy",
    "selected_matches_best_center",
    "aabb_proxy_gap_selected_to_best",
    "center_error_gap_selected_to_best_center",
    "bucket",
    "bucket_reason",
    "bucket_detail_status",
    "uses_aabb_proxy_only",
    "heading_orientation_claim",
]

CASE_REVIEW_COLUMNS = [
    "case_priority",
    "target_identity",
    "scene",
    "sar_frame_num",
    "gm17_track_id",
    "bucket",
    "bucket_reason",
    "review_hint",
    "selected_candidate_id",
    "selected_rank",
    "selected_axis_aligned_proxy_iou",
    "selected_center_error",
    "best_proxy_candidate_id",
    "best_proxy_rank",
    "best_axis_aligned_proxy_iou",
    "best_proxy_center_error",
    "best_center_candidate_id",
    "best_center_rank",
    "best_center_error",
    "best_center_axis_aligned_proxy_iou",
    "condition_type_context_only",
    "truncation_degree_context_only",
    "occlusion_degree_context_only",
    "uses_aabb_proxy_only",
    "heading_orientation_claim",
]

BUCKET_TAXONOMY = [
    "Candidate-Present-But-Selector-Missed",
    "Candidate-Scarcity / No-Sufficient-Candidate",
    "Center-Limited",
    "Size-Limited",
    "Center-Size Combined",
    "Aspect/Shape-Hypothesis Limited",
    "Proxy-Metric Limitation",
    "Needs-Manual-Review",
]


@dataclass(frozen=True)
class Preconditions:
    schema_status: str
    join_statuses: dict[str, str]
    selected_alignment_status: str
    selected_alignment_mismatch_count: int


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run GM17 Experiment A fixed-bank high-IoU precision decomposition."
    )
    parser.add_argument(
        "--resolver-output-dir",
        default=DEFAULT_RESOLVER_OUTPUT_DIR,
        help="A0 resolver output directory containing artifact_manifest.csv.",
    )
    parser.add_argument(
        "--join-validation-output-dir",
        default=DEFAULT_JOIN_VALIDATION_OUTPUT_DIR,
        help="A0.2b join validation output directory containing join_key_validation_summary.json.",
    )
    parser.add_argument(
        "--schema-validation-output-dir",
        default=DEFAULT_SCHEMA_VALIDATION_OUTPUT_DIR,
        help="A1 schema validation output directory containing experimentA_schema_validation_summary.json.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory. Defaults to output/gm17_experimentA_high_iou_precision_decomposition_<timestamp>.",
    )
    parser.add_argument(
        "--high-proxy-threshold",
        type=float,
        default=0.90,
        help="Audit-only AABB proxy threshold for high precision decomposition.",
    )
    parser.add_argument(
        "--strict-proxy-threshold",
        type=float,
        default=0.95,
        help="Audit-only AABB proxy threshold for stricter high precision count.",
    )
    parser.add_argument(
        "--center-threshold-px",
        type=float,
        default=50.0,
        help="Audit-only center threshold aligned with the existing center_hit_50px convention.",
    )
    return parser.parse_args()


def resolve_cli_path(path_text: str | None, root: Path, default_prefix: str | None = None) -> Path:
    if not path_text:
        if not default_prefix:
            raise ValueError("default_prefix is required when path_text is empty")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return root / "output" / f"{default_prefix}_{timestamp}"
    path = Path(path_text)
    return path if path.is_absolute() else root / path


def read_csv_dicts(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return data


def read_manifest(resolver_output_dir: Path) -> dict[str, dict[str, str]]:
    path = resolver_output_dir / "artifact_manifest.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing artifact manifest: {path}")
    return {row["artifact_id"]: row for row in read_csv_dicts(path) if row.get("artifact_id")}


def artifact_path(manifest: dict[str, dict[str, str]], artifact_id: str) -> Path:
    row = manifest.get(artifact_id)
    if not row:
        raise KeyError(f"Missing artifact in manifest: {artifact_id}")
    if str(row.get("exists", "")).lower() != "true":
        raise FileNotFoundError(f"Artifact is not marked exists=true: {artifact_id}")
    path = Path(row.get("path", ""))
    if not path.exists():
        raise FileNotFoundError(f"Resolved artifact path does not exist for {artifact_id}: {path}")
    return path


def header_columns(path: Path) -> list[str]:
    return list(pd.read_csv(path, nrows=0, dtype=str, encoding="utf-8-sig").columns)


def require_columns(path: Path, required: list[str], *, optional: list[str] | None = None) -> list[str]:
    columns = header_columns(path)
    missing = [column for column in required if column not in columns]
    if missing:
        raise RuntimeError(f"Missing required columns in {path}: {missing}")
    selected = list(required)
    for column in optional or []:
        if column in columns:
            selected.append(column)
    return selected


def read_table(path: Path, required: list[str], *, optional: list[str] | None = None) -> pd.DataFrame:
    usecols = require_columns(path, required, optional=optional)
    return pd.read_csv(path, usecols=usecols, dtype=str, encoding="utf-8-sig")


def normalize_key_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for column in TARGET_KEY_COLUMNS:
        if column in out.columns:
            out[column] = out[column].map(lambda value: normalize_text(value, frame_like=(column == "sar_frame_num")))
    return out


def normalize_text(value: Any, *, frame_like: bool = False) -> str:
    if value is None:
        return ""
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if frame_like and text.endswith(".0"):
        head = text[:-2]
        if head.lstrip("-").isdigit():
            return head
    return text


def to_float(value: Any) -> float:
    if value is None:
        return math.nan
    if pd.isna(value):
        return math.nan
    text = str(value).strip()
    if not text:
        return math.nan
    try:
        return float(text)
    except ValueError:
        return math.nan


def to_int_text(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip()
    if text.endswith(".0"):
        head = text[:-2]
        if head.lstrip("-").isdigit():
            return head
    return text


def finite_values(values: list[float]) -> list[float]:
    return [value for value in values if not math.isnan(value)]


def quantile(values: list[float], q: float) -> float | None:
    clean = sorted(finite_values(values))
    if not clean:
        return None
    if len(clean) == 1:
        return clean[0]
    pos = (len(clean) - 1) * q
    lower = math.floor(pos)
    upper = math.ceil(pos)
    if lower == upper:
        return clean[int(pos)]
    return clean[lower] * (upper - pos) + clean[upper] * (pos - lower)


def fmt_float(value: float | None, digits: int = 6) -> str:
    if value is None or math.isnan(value):
        return ""
    return f"{value:.{digits}f}"


def parse_source_from_candidate_id(candidate_id: str) -> str:
    parts = str(candidate_id).split("::")
    if len(parts) >= 3 and parts[1]:
        return parts[1]
    return ""


def build_candidate_source_map(a001_df: pd.DataFrame) -> dict[str, dict[str, str]]:
    source_map: dict[str, dict[str, str]] = {}
    for row in a001_df.to_dict("records"):
        candidate_id = normalize_text(row.get("candidate_id"))
        if not candidate_id:
            continue
        source_map[candidate_id] = {
            "candidate_source": normalize_text(row.get("candidate_source")) or parse_source_from_candidate_id(candidate_id),
            "candidate_detail": normalize_text(row.get("candidate_detail")),
            "candidate_expansion_state": normalize_text(row.get("candidate_expansion_state")),
            "candidate_expansion_reason": normalize_text(row.get("candidate_expansion_reason")),
        }
    return source_map


def candidate_source(candidate_id: str, source_map: dict[str, dict[str, str]]) -> str:
    candidate_id = normalize_text(candidate_id)
    row = source_map.get(candidate_id, {})
    return row.get("candidate_source") or parse_source_from_candidate_id(candidate_id) or "unknown"


def load_preconditions(join_dir: Path, schema_dir: Path) -> tuple[str, dict[str, str]]:
    schema_path = schema_dir / "experimentA_schema_validation_summary.json"
    join_path = join_dir / "join_key_validation_summary.json"
    if not schema_path.exists():
        raise FileNotFoundError(f"Missing schema validation summary: {schema_path}")
    if not join_path.exists():
        raise FileNotFoundError(f"Missing join validation summary: {join_path}")
    schema_summary = read_json(schema_path)
    join_summary = read_json(join_path)
    schema_status = str(schema_summary.get("overall_status", ""))
    join_statuses = {
        str(row.get("join_pair", "")): str(row.get("status", ""))
        for row in join_summary.get("joins", [])
        if isinstance(row, dict)
    }
    return schema_status, join_statuses


def assert_preconditions(schema_status: str, join_statuses: dict[str, str]) -> None:
    if schema_status != SCHEMA_GO_STATUS:
        raise RuntimeError(
            f"Experiment A decomposition is blocked: schema overall_status={schema_status!r}, "
            f"expected {SCHEMA_GO_STATUS!r}."
        )
    required_join_pairs = [
        "per_target_audit_to_A019",
        "per_target_audit_to_A021",
        "frozen_ranked_to_per_target_audit",
    ]
    bad_pairs = {
        pair: join_statuses.get(pair, "")
        for pair in required_join_pairs
        if join_statuses.get(pair, "") not in ALLOWED_JOIN_STATUSES
    }
    if bad_pairs:
        raise RuntimeError(f"Experiment A decomposition is blocked by join status: {bad_pairs}")


def selected_alignment_status(per_target_df: pd.DataFrame, selected_df: pd.DataFrame) -> tuple[str, int]:
    left = normalize_key_columns(
        per_target_df[TARGET_KEY_COLUMNS + ["candidate_id"]].rename(
            columns={"candidate_id": "per_target_candidate_id"}
        )
    )
    right = normalize_key_columns(
        selected_df[TARGET_KEY_COLUMNS + ["candidate_id"]].rename(
            columns={"candidate_id": "selected_output_candidate_id"}
        )
    )
    merged = left.merge(right, on=TARGET_KEY_COLUMNS, how="left", validate="one_to_one")
    missing = merged["selected_output_candidate_id"].isna() | merged["selected_output_candidate_id"].eq("")
    mismatch = (
        merged["selected_output_candidate_id"].fillna("")
        != merged["per_target_candidate_id"].fillna("")
    )
    count = int((missing | mismatch).sum())
    return ("GO" if count == 0 else "HOLD_FOR_SELECTED_ALIGNMENT_REVIEW", count)


def classify_bucket(
    *,
    selected_candidate_id: str,
    selected_iou: float,
    selected_center_error: float,
    best_proxy_candidate_id: str,
    best_proxy_iou: float,
    best_center_error: float,
    high_proxy_threshold: float,
    center_threshold_px: float,
) -> tuple[str, str, str]:
    if math.isnan(selected_iou) or math.isnan(best_proxy_iou) or math.isnan(best_center_error):
        return (
            "Needs-Manual-Review",
            "missing_required_existing_audit_values",
            "HOLD_FOR_BUCKET_DETAIL",
        )

    selected_matches_best_proxy = (
        normalize_text(selected_candidate_id) != ""
        and normalize_text(selected_candidate_id) == normalize_text(best_proxy_candidate_id)
    )
    selected_high = selected_iou >= high_proxy_threshold
    best_high = best_proxy_iou >= high_proxy_threshold
    best_center_within = best_center_error <= center_threshold_px

    if best_high and not selected_high and not selected_matches_best_proxy:
        return (
            "Candidate-Present-But-Selector-Missed",
            (
                "existing_best_proxy_candidate_reaches_high_AABB_proxy_but_frozen_rank1_does_not; "
                "structured_selection_bottleneck_candidate"
            ),
            "OK",
        )

    if best_high and selected_high:
        return (
            "Needs-Manual-Review",
            (
                "selected_candidate_already_reaches_high_AABB_proxy; "
                "not_a_high_precision_failure_bucket_under_Experiment_A"
            ),
            "NO_FAILURE_BUCKET_ASSIGNED",
        )

    if not best_high and not best_center_within:
        return (
            "Center-Limited",
            (
                "no_existing_candidate_reaches_high_AABB_proxy_and_best_center_error_exceeds_existing_50px_audit_convention"
            ),
            "OK",
        )

    if not best_high and best_center_within:
        return (
            "Candidate-Scarcity / No-Sufficient-Candidate",
            (
                "no_existing_candidate_reaches_high_AABB_proxy; best_center_candidate_is_within_existing_50px_audit_convention; "
                "HOLD_FOR_BUCKET_DETAIL_size_aspect_shape_need_size_residual_or_rotated_OBB_audit_fields"
            ),
            "HOLD_FOR_BUCKET_DETAIL",
        )

    if not best_high and not math.isnan(selected_center_error) and selected_center_error > center_threshold_px:
        return (
            "Center-Size Combined",
            (
                "selected_center_error_exceeds_existing_50px_audit_convention_and_no_high_AABB_proxy_candidate_exists; "
                "HOLD_FOR_BUCKET_DETAIL_without_size_residual_fields"
            ),
            "HOLD_FOR_BUCKET_DETAIL",
        )

    return (
        "Needs-Manual-Review",
        "existing_audit_fields_do_not_support_stricter_bucket_assignment",
        "HOLD_FOR_BUCKET_DETAIL",
    )


def make_target_summary(
    per_target_df: pd.DataFrame,
    source_map: dict[str, dict[str, str]],
    *,
    high_proxy_threshold: float,
    center_threshold_px: float,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for row in per_target_df.to_dict("records"):
        selected_candidate_id = normalize_text(row.get("candidate_id"))
        best_proxy_candidate_id = normalize_text(row.get("best_proxy_candidate_id"))
        best_center_candidate_id = normalize_text(row.get("best_center_candidate_id"))
        selected_iou = to_float(row.get("axis_aligned_proxy_iou"))
        selected_center = to_float(row.get("center_error"))
        best_proxy_iou = to_float(row.get("best_proxy_iou"))
        best_proxy_center = to_float(row.get("best_proxy_center_error"))
        best_center_error = to_float(row.get("best_center_error"))
        best_center_proxy_iou = to_float(row.get("best_center_proxy_iou"))
        bucket, reason, detail_status = classify_bucket(
            selected_candidate_id=selected_candidate_id,
            selected_iou=selected_iou,
            selected_center_error=selected_center,
            best_proxy_candidate_id=best_proxy_candidate_id,
            best_proxy_iou=best_proxy_iou,
            best_center_error=best_center_error,
            high_proxy_threshold=high_proxy_threshold,
            center_threshold_px=center_threshold_px,
        )
        rows.append(
            {
                "target_identity": normalize_text(row.get("target_identity")),
                "scene": normalize_text(row.get("scene")),
                "sar_frame_num": normalize_text(row.get("sar_frame_num"), frame_like=True),
                "gm17_track_id": normalize_text(row.get("gm17_track_id")),
                "selected_candidate_id": selected_candidate_id,
                "selected_rank": to_int_text(row.get("pilot_rank")),
                "selected_axis_aligned_proxy_iou": fmt_float(selected_iou),
                "selected_center_error": fmt_float(selected_center),
                "selected_candidate_source": candidate_source(selected_candidate_id, source_map),
                "best_proxy_candidate_id": best_proxy_candidate_id,
                "best_proxy_rank": to_int_text(row.get("best_proxy_pilot_rank")),
                "best_axis_aligned_proxy_iou": fmt_float(best_proxy_iou),
                "best_proxy_center_error": fmt_float(best_proxy_center),
                "best_proxy_candidate_source": candidate_source(best_proxy_candidate_id, source_map),
                "best_center_candidate_id": best_center_candidate_id,
                "best_center_rank": to_int_text(row.get("best_center_pilot_rank")),
                "best_center_error": fmt_float(best_center_error),
                "best_center_axis_aligned_proxy_iou": fmt_float(best_center_proxy_iou),
                "best_center_candidate_source": candidate_source(best_center_candidate_id, source_map),
                "selected_matches_best_proxy": str(selected_candidate_id == best_proxy_candidate_id).lower(),
                "selected_matches_best_center": str(selected_candidate_id == best_center_candidate_id).lower(),
                "aabb_proxy_gap_selected_to_best": fmt_float(
                    None if math.isnan(best_proxy_iou) or math.isnan(selected_iou) else best_proxy_iou - selected_iou
                ),
                "center_error_gap_selected_to_best_center": fmt_float(
                    None
                    if math.isnan(selected_center) or math.isnan(best_center_error)
                    else selected_center - best_center_error
                ),
                "bucket": bucket,
                "bucket_reason": reason,
                "bucket_detail_status": detail_status,
                "uses_aabb_proxy_only": "true",
                "heading_orientation_claim": "false",
            }
        )
    return pd.DataFrame(rows, columns=OUTPUT_TARGET_COLUMNS)


def role_records(target_summary: pd.DataFrame) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    role_specs = [
        (
            "selected_rank1",
            "selected_candidate_id",
            "selected_rank",
            "selected_axis_aligned_proxy_iou",
            "selected_center_error",
            "selected_candidate_source",
        ),
        (
            "best_proxy_candidate",
            "best_proxy_candidate_id",
            "best_proxy_rank",
            "best_axis_aligned_proxy_iou",
            "best_proxy_center_error",
            "best_proxy_candidate_source",
        ),
        (
            "best_center_candidate",
            "best_center_candidate_id",
            "best_center_rank",
            "best_center_axis_aligned_proxy_iou",
            "best_center_error",
            "best_center_candidate_source",
        ),
    ]
    for role, id_col, rank_col, proxy_col, center_col, source_col in role_specs:
        for row in target_summary.to_dict("records"):
            records.append(
                {
                    "role": role,
                    "target_identity": row["target_identity"],
                    "candidate_id": row[id_col],
                    "rank": to_float(row[rank_col]),
                    "axis_aligned_proxy_iou": to_float(row[proxy_col]),
                    "center_error": to_float(row[center_col]),
                    "candidate_source": row[source_col] or "unknown",
                }
            )
    return records


def make_candidate_role_summary(
    target_summary: pd.DataFrame,
    *,
    high_proxy_threshold: float,
    strict_proxy_threshold: float,
    center_threshold_px: float,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for role in ["selected_rank1", "best_proxy_candidate", "best_center_candidate"]:
        records = [record for record in role_records(target_summary) if record["role"] == role]
        proxy_values = [record["axis_aligned_proxy_iou"] for record in records]
        center_values = [record["center_error"] for record in records]
        rank_values = [record["rank"] for record in records]
        source_counts = Counter(record["candidate_source"] for record in records)
        rows.append(
            {
                "role": role,
                "assignment_count": len(records),
                "unique_target_count": len({record["target_identity"] for record in records}),
                "unique_candidate_count": len({record["candidate_id"] for record in records if record["candidate_id"]}),
                "candidate_source_top_counts": ";".join(
                    f"{source}:{count}" for source, count in source_counts.most_common(8)
                ),
                "rank_median": fmt_float(quantile(rank_values, 0.50), 3),
                "rank_p90": fmt_float(quantile(rank_values, 0.90), 3),
                "aabb_proxy_min": fmt_float(quantile(proxy_values, 0.00)),
                "aabb_proxy_median": fmt_float(quantile(proxy_values, 0.50)),
                "aabb_proxy_p90": fmt_float(quantile(proxy_values, 0.90)),
                "aabb_proxy_max": fmt_float(quantile(proxy_values, 1.00)),
                "high_aabb_proxy_ge_0_90_count": sum(
                    1 for value in proxy_values if not math.isnan(value) and value >= high_proxy_threshold
                ),
                "strict_aabb_proxy_ge_0_95_count": sum(
                    1 for value in proxy_values if not math.isnan(value) and value >= strict_proxy_threshold
                ),
                "center_error_min": fmt_float(quantile(center_values, 0.00)),
                "center_error_median": fmt_float(quantile(center_values, 0.50)),
                "center_error_p90": fmt_float(quantile(center_values, 0.90)),
                "center_error_max": fmt_float(quantile(center_values, 1.00)),
                "center_error_le_50px_count": sum(
                    1 for value in center_values if not math.isnan(value) and value <= center_threshold_px
                ),
                "uses_aabb_proxy_only": "true",
                "heading_orientation_claim": "false",
            }
        )
    return pd.DataFrame(rows)


def make_bucket_summary(target_summary: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    total = len(target_summary)
    for bucket in BUCKET_TAXONOMY:
        subset = target_summary[target_summary["bucket"] == bucket]
        selected_proxy = [to_float(value) for value in subset["selected_axis_aligned_proxy_iou"].tolist()]
        best_proxy = [to_float(value) for value in subset["best_axis_aligned_proxy_iou"].tolist()]
        best_center = [to_float(value) for value in subset["best_center_error"].tolist()]
        detail_counts = Counter(subset["bucket_detail_status"].tolist())
        rows.append(
            {
                "bucket": bucket,
                "target_count": int(len(subset)),
                "target_share": fmt_float((len(subset) / total) if total else None, 4),
                "selected_aabb_proxy_median": fmt_float(quantile(selected_proxy, 0.50)),
                "best_aabb_proxy_median": fmt_float(quantile(best_proxy, 0.50)),
                "best_center_error_median": fmt_float(quantile(best_center, 0.50)),
                "bucket_detail_status_counts": ";".join(
                    f"{status}:{count}" for status, count in detail_counts.most_common()
                ),
                "uses_aabb_proxy_only": "true",
                "heading_orientation_claim": "false",
            }
        )
    return pd.DataFrame(rows)


def make_case_review_list(per_target_df: pd.DataFrame, target_summary: pd.DataFrame) -> pd.DataFrame:
    context_cols = [
        col
        for col in ["target_identity", "condition_type", "truncation_degree", "occlusion_degree"]
        if col in per_target_df.columns
    ]
    context = per_target_df[context_cols].copy() if context_cols else pd.DataFrame({"target_identity": []})
    if "target_identity" in context.columns:
        context["target_identity"] = context["target_identity"].map(normalize_text)

    def priority(row: dict[str, Any]) -> tuple[int, float]:
        gap = to_float(row.get("aabb_proxy_gap_selected_to_best"))
        center_gap = to_float(row.get("center_error_gap_selected_to_best_center"))
        bucket = row.get("bucket", "")
        if bucket == "Candidate-Present-But-Selector-Missed":
            return (1, -(0.0 if math.isnan(gap) else gap))
        if bucket == "Center-Limited":
            best_center = to_float(row.get("best_center_error"))
            return (2, -(0.0 if math.isnan(best_center) else best_center))
        if bucket == "Candidate-Scarcity / No-Sufficient-Candidate":
            return (3, -(0.0 if math.isnan(center_gap) else abs(center_gap)))
        return (4, 0.0)

    rows: list[dict[str, Any]] = []
    context_by_target = {
        normalize_text(row.get("target_identity")): row for row in context.to_dict("records")
    }
    for row in sorted(target_summary.to_dict("records"), key=priority):
        ctx = context_by_target.get(normalize_text(row.get("target_identity")), {})
        bucket = row["bucket"]
        if bucket == "Candidate-Present-But-Selector-Missed":
            hint = "compare frozen rank1 with existing best_proxy candidate; audit selector structure only"
        elif bucket == "Center-Limited":
            hint = "inspect candidate precision scarcity under existing center audit fields; do not alter bank here"
        elif bucket == "Candidate-Scarcity / No-Sufficient-Candidate":
            hint = "size/aspect/shape detail requires future fields; no hard assignment in Experiment A"
        else:
            hint = "manual review only; existing fields do not justify a narrower bucket"
        rows.append(
            {
                "case_priority": priority(row)[0],
                "target_identity": row["target_identity"],
                "scene": row["scene"],
                "sar_frame_num": row["sar_frame_num"],
                "gm17_track_id": row["gm17_track_id"],
                "bucket": bucket,
                "bucket_reason": row["bucket_reason"],
                "review_hint": hint,
                "selected_candidate_id": row["selected_candidate_id"],
                "selected_rank": row["selected_rank"],
                "selected_axis_aligned_proxy_iou": row["selected_axis_aligned_proxy_iou"],
                "selected_center_error": row["selected_center_error"],
                "best_proxy_candidate_id": row["best_proxy_candidate_id"],
                "best_proxy_rank": row["best_proxy_rank"],
                "best_axis_aligned_proxy_iou": row["best_axis_aligned_proxy_iou"],
                "best_proxy_center_error": row["best_proxy_center_error"],
                "best_center_candidate_id": row["best_center_candidate_id"],
                "best_center_rank": row["best_center_rank"],
                "best_center_error": row["best_center_error"],
                "best_center_axis_aligned_proxy_iou": row["best_center_axis_aligned_proxy_iou"],
                "condition_type_context_only": normalize_text(ctx.get("condition_type")),
                "truncation_degree_context_only": normalize_text(ctx.get("truncation_degree")),
                "occlusion_degree_context_only": normalize_text(ctx.get("occlusion_degree")),
                "uses_aabb_proxy_only": "true",
                "heading_orientation_claim": "false",
            }
        )
    return pd.DataFrame(rows, columns=CASE_REVIEW_COLUMNS)


def write_csv(path: Path, df: pd.DataFrame) -> None:
    df.to_csv(path, index=False, encoding="utf-8", lineterminator="\n")


def markdown_table_from_df(df: pd.DataFrame, columns: list[str]) -> str:
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in df[columns].to_dict("records"):
        lines.append("| " + " | ".join(str(row.get(col, "")) for col in columns) + " |")
    return "\n".join(lines)


def build_report(
    *,
    output_dir: Path,
    preconditions: Preconditions,
    target_count: int,
    frozen_candidate_count: int,
    selected_count: int,
    bucket_summary: pd.DataFrame,
    role_summary: pd.DataFrame,
    case_review_count: int,
    high_proxy_threshold: float,
    strict_proxy_threshold: float,
    center_threshold_px: float,
) -> str:
    lines = [
        "# GM17 Experiment A High-IoU Precision Decomposition Report",
        "",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        "",
        f"Output directory: `{output_dir}`",
        "",
        "This is Experiment A audit-only decomposition. It is not a mainline performance claim, not a selector update, not a candidate-bank update, and not Phase5 approval.",
        "",
        f"Formal Phase5 remains `{FORMAL_PHASE5_STATUS}`.",
        "",
        "## Boundaries",
        "",
        "- Uses existing post-inference audit fields only.",
        "- Does not recompute IoU.",
        "- Does not recompute center error.",
        "- Does not read SAR image pixels.",
        "- Does not compute SAR descriptors, scatter centroid, keyframe confidence, or soft-anchor simulation.",
        "- Does not train, calibrate, or run OOF calibration.",
        "- Does not modify the candidate bank or GM17 selector.",
        "- `axis_aligned_proxy_iou` is used only as an AABB audit proxy, not rotated IoU.",
        "- No heading, orientation, or long-axis correctness conclusion is made.",
        "- A019/A021/final/condition fields are context-only where present and are not used for scoring.",
        "",
        "## Preconditions",
        "",
        f"- Schema validation: `{preconditions.schema_status}`",
        f"- Join validation `per_target_audit_to_A019`: `{preconditions.join_statuses.get('per_target_audit_to_A019', '')}`",
        f"- Join validation `per_target_audit_to_A021`: `{preconditions.join_statuses.get('per_target_audit_to_A021', '')}`",
        f"- Join validation `frozen_ranked_to_per_target_audit`: `{preconditions.join_statuses.get('frozen_ranked_to_per_target_audit', '')}`",
        f"- Selected rank1 alignment: `{preconditions.selected_alignment_status}` ({preconditions.selected_alignment_mismatch_count} mismatches)",
        "",
        "## Audit Thresholds",
        "",
        f"- High AABB proxy threshold: `{high_proxy_threshold}`",
        f"- Strict AABB proxy threshold: `{strict_proxy_threshold}`",
        f"- Center threshold: `{center_threshold_px}` px, aligned with the existing `center_hit_50px` audit convention.",
        "",
        "These thresholds support bucket assignment only. They are not new selector thresholds and not mainline performance gates.",
        "",
        "## Counts",
        "",
        f"- Target rows: {target_count}",
        f"- Frozen candidate rows: {frozen_candidate_count}",
        f"- Selected rank1 rows: {selected_count}",
        f"- Case review rows: {case_review_count}",
        "",
        "## Bucket Summary",
        "",
        markdown_table_from_df(
            bucket_summary,
            [
                "bucket",
                "target_count",
                "target_share",
                "selected_aabb_proxy_median",
                "best_aabb_proxy_median",
                "best_center_error_median",
                "bucket_detail_status_counts",
            ],
        ),
        "",
        "## Candidate Role Summary",
        "",
        markdown_table_from_df(
            role_summary,
            [
                "role",
                "assignment_count",
                "unique_candidate_count",
                "rank_median",
                "aabb_proxy_median",
                "center_error_median",
                "high_aabb_proxy_ge_0_90_count",
                "strict_aabb_proxy_ge_0_95_count",
                "candidate_source_top_counts",
            ],
        ),
        "",
        "## Bucket Detail Holds",
        "",
        "The current fields support selector-missed, candidate-scarcity, and center-limited decomposition. They do not support a strict split between size-limited, center-size combined, and aspect/shape-hypothesis-limited cases because no approved size residual, shape residual, rotated-OBB IoU, or heading-convention audit field is available in Experiment A.",
        "",
        "Rows that require that distinction are marked `HOLD_FOR_BUCKET_DETAIL` instead of forcing an unsupported bucket.",
        "",
        "## Interpretation Boundary",
        "",
        "This decomposition may be used to plan the next diagnostic audit. It must not be cited as a GM17 mainline performance result, must not be used to approve Phase5, and must not be fed back into scoring or active selection.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    root = repo_root()
    resolver_output_dir = resolve_cli_path(args.resolver_output_dir, root)
    join_validation_output_dir = resolve_cli_path(args.join_validation_output_dir, root)
    schema_validation_output_dir = resolve_cli_path(args.schema_validation_output_dir, root)
    output_dir = resolve_cli_path(
        args.output_dir,
        root,
        "gm17_experimentA_high_iou_precision_decomposition",
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    schema_status, join_statuses = load_preconditions(join_validation_output_dir, schema_validation_output_dir)
    assert_preconditions(schema_status, join_statuses)

    manifest = read_manifest(resolver_output_dir)
    per_target_path = artifact_path(manifest, "per_target_audit_output")
    selected_path = artifact_path(manifest, "selected_rank1_output")
    frozen_path = artifact_path(manifest, "frozen_ranked_candidates")
    a001_path = artifact_path(manifest, "A001_candidate_bank")

    per_target_df = read_table(
        per_target_path,
        PER_TARGET_REQUIRED_COLUMNS,
        optional=PER_TARGET_OPTIONAL_CONTEXT_COLUMNS,
    )
    selected_df = read_table(selected_path, SELECTED_REQUIRED_COLUMNS)
    frozen_df = read_table(frozen_path, FROZEN_REQUIRED_COLUMNS)
    a001_df = read_table(a001_path, ["candidate_id"], optional=A001_SOURCE_COLUMNS[1:])

    per_target_df = normalize_key_columns(per_target_df)
    selected_df = normalize_key_columns(selected_df)
    frozen_df = normalize_key_columns(frozen_df)

    alignment_status, alignment_mismatch_count = selected_alignment_status(per_target_df, selected_df)
    preconditions = Preconditions(
        schema_status=schema_status,
        join_statuses=join_statuses,
        selected_alignment_status=alignment_status,
        selected_alignment_mismatch_count=alignment_mismatch_count,
    )

    source_map = build_candidate_source_map(a001_df)
    target_summary = make_target_summary(
        per_target_df,
        source_map,
        high_proxy_threshold=args.high_proxy_threshold,
        center_threshold_px=args.center_threshold_px,
    )
    role_summary = make_candidate_role_summary(
        target_summary,
        high_proxy_threshold=args.high_proxy_threshold,
        strict_proxy_threshold=args.strict_proxy_threshold,
        center_threshold_px=args.center_threshold_px,
    )
    bucket_summary = make_bucket_summary(target_summary)
    case_review = make_case_review_list(per_target_df, target_summary)

    target_summary_path = output_dir / "experimentA_target_summary.csv"
    role_summary_path = output_dir / "experimentA_candidate_role_summary.csv"
    bucket_summary_path = output_dir / "experimentA_bucket_summary.csv"
    case_review_path = output_dir / "experimentA_case_review_list.csv"
    report_path = output_dir / "experimentA_report.md"
    summary_path = output_dir / "experimentA_summary.json"

    write_csv(target_summary_path, target_summary)
    write_csv(role_summary_path, role_summary)
    write_csv(bucket_summary_path, bucket_summary)
    write_csv(case_review_path, case_review)

    report = build_report(
        output_dir=output_dir,
        preconditions=preconditions,
        target_count=len(per_target_df),
        frozen_candidate_count=len(frozen_df),
        selected_count=len(selected_df),
        bucket_summary=bucket_summary,
        role_summary=role_summary,
        case_review_count=len(case_review),
        high_proxy_threshold=args.high_proxy_threshold,
        strict_proxy_threshold=args.strict_proxy_threshold,
        center_threshold_px=args.center_threshold_px,
    )
    report_path.write_text(report, encoding="utf-8")

    bucket_counts = {
        row["bucket"]: int(row["target_count"]) for row in bucket_summary.to_dict("records")
    }
    role_counts = {
        row["role"]: {
            "assignment_count": int(row["assignment_count"]),
            "unique_candidate_count": int(row["unique_candidate_count"]),
            "high_aabb_proxy_ge_0_90_count": int(row["high_aabb_proxy_ge_0_90_count"]),
            "strict_aabb_proxy_ge_0_95_count": int(row["strict_aabb_proxy_ge_0_95_count"]),
        }
        for row in role_summary.to_dict("records")
    }
    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "script_scope": SCRIPT_SCOPE,
        "resolver_output_dir": str(resolver_output_dir),
        "join_validation_output_dir": str(join_validation_output_dir),
        "schema_validation_output_dir": str(schema_validation_output_dir),
        "output_dir": str(output_dir),
        "formal_phase5_status": FORMAL_PHASE5_STATUS,
        "experiment_a_decomposition_ran": True,
        "audit_only_decomposition": True,
        "mainline_performance_conclusion_produced": False,
        "source_value_read_scope": "existing per-target audit fields and frozen Line-FB rank/candidate provenance only",
        "iou_recomputed": False,
        "center_error_recomputed": False,
        "sar_descriptor_computed": False,
        "sar_pixels_opened": False,
        "scatter_centroid_computed": False,
        "keyframe_confidence_computed": False,
        "soft_anchor_simulation_ran": False,
        "model_trained": False,
        "oof_calibration_ran": False,
        "candidate_bank_modified": False,
        "selector_modified": False,
        "line_gp_or_phase5b_used": False,
        "axis_aligned_proxy_iou_interpretation": "AABB audit proxy only; not rotated IoU",
        "heading_orientation_claim": False,
        "preconditions": {
            "schema_status": preconditions.schema_status,
            "join_statuses": preconditions.join_statuses,
            "selected_alignment_status": preconditions.selected_alignment_status,
            "selected_alignment_mismatch_count": preconditions.selected_alignment_mismatch_count,
        },
        "thresholds": {
            "high_aabb_proxy": args.high_proxy_threshold,
            "strict_aabb_proxy": args.strict_proxy_threshold,
            "center_threshold_px": args.center_threshold_px,
        },
        "counts": {
            "target_rows": int(len(per_target_df)),
            "frozen_candidate_rows": int(len(frozen_df)),
            "selected_rank1_rows": int(len(selected_df)),
            "a001_candidate_rows": int(len(a001_df)),
            "case_review_rows": int(len(case_review)),
            "bucket_detail_hold_rows": int(
                (target_summary["bucket_detail_status"] == "HOLD_FOR_BUCKET_DETAIL").sum()
            ),
        },
        "bucket_counts": bucket_counts,
        "candidate_role_counts": role_counts,
        "outputs": {
            "experimentA_target_summary": str(target_summary_path),
            "experimentA_candidate_role_summary": str(role_summary_path),
            "experimentA_bucket_summary": str(bucket_summary_path),
            "experimentA_case_review_list": str(case_review_path),
            "experimentA_report": str(report_path),
            "experimentA_summary": str(summary_path),
        },
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "output_dir": str(output_dir),
                "target_rows": len(per_target_df),
                "frozen_candidate_rows": len(frozen_df),
                "bucket_counts": bucket_counts,
                "selected_alignment_status": alignment_status,
                "iou_recomputed": False,
                "center_error_recomputed": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
