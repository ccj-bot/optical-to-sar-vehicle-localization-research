#!/usr/bin/env python
"""Validate Experiment A input schema readiness without running decomposition.

This A1 validator checks headers, artifact roles, and the A0.2b key-only join
summary. It does not compute high-IoU decomposition, metrics, IoU, center error,
SAR descriptors, keyframe confidence, or performance.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


ARTIFACT_MANIFEST = "artifact_manifest.csv"
JOIN_SUMMARY = "join_key_validation_summary.csv"
FORMAL_PHASE5_STATUS = "BLOCKED_FOR_OOF_CALIBRATION"
SCRIPT_SCOPE = "A1_experimentA_schema_validation_only"

ALLOWED_JOIN_STATUSES = {"GO", "POLICY_ACCEPTED_GO_FOR_LEFT_COVERAGE"}

CANONICAL_ALIASES: dict[str, list[str]] = {
    "target_identity": ["target_identity", "target_id"],
    "scene": ["scene", "scene_id"],
    "sar_frame_num": ["sar_frame_num", "sar_frame", "frame_id"],
    "gm17_track_id": ["gm17_track_id", "track_id"],
    "candidate_id": ["candidate_id", "cand_id"],
    "cx": ["cx", "candidate_cx", "box_cx"],
    "cy": ["cy", "candidate_cy", "box_cy"],
    "w": ["w", "candidate_w", "box_w"],
    "h": ["h", "candidate_h", "box_h"],
    "rank": ["rank", "pilot_rank", "selected_rank", "rank1", "c1_rank", "c2_rank", "c3_rank", "c4_rank", "c5_rank"],
    "candidate_source": [
        "candidate_source",
        "candidate_detail",
        "candidate_expansion_state",
        "candidate_expansion_reason",
        "proposal_source",
        "route",
        "route_name",
        "provenance",
    ],
    "axis_aligned_proxy_iou": ["axis_aligned_proxy_iou"],
    "center_error": ["center_error", "candidate_center_err_px", "center_err_px", "center_err"],
    "oracle_fields": [
        "best_proxy_candidate_id",
        "best_center_candidate_id",
        "best_candidate_id",
        "oracle_candidate_id",
        "oracle_rank_iou",
        "oracle_rank_center",
    ],
    "final_fields": ["final_*"],
    "condition_fields": [
        "condition_type",
        "condition_status",
        "condition_degree",
        "truncation_degree",
        "occlusion_degree",
        "visibility_label",
        "partial_visible",
    ],
}

FORBIDDEN_IN_INFERENCE = {
    "axis_aligned_proxy_iou",
    "center_error",
    "best_iou",
    "best_center_error",
    "best_proxy_iou",
    "best_proxy_center_error",
    "best_center_proxy_iou",
    "final_cx",
    "final_cy",
    "final_w",
    "final_h",
    "final_heading_deg",
    "condition_type",
    "condition_status",
    "condition_degree",
    "truncation_degree",
    "occlusion_degree",
}

INFERENCE_FACING_ARTIFACTS = {
    "A001_candidate_bank",
    "A005_optical_temporal_prior",
    "A007_signed_escape_posterior",
    "A008_candidate_factor_joined",
}

ALLOWED_SOURCE_ARTIFACTS = {
    "A001_candidate_bank",
    "frozen_ranked_candidates",
    "per_target_audit_output",
    "A019_final_boxes",
    "A021_condition_labels",
    "A005_optical_temporal_prior",
    "A007_signed_escape_posterior",
    "A008_candidate_factor_joined",
}


@dataclass
class CheckResult:
    check_id: str
    category: str
    status: str
    required_fields: str
    observed_fields: str
    blocking_issue: str
    notes: str


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate GM17 Experiment A schema readiness only.")
    parser.add_argument(
        "--resolver-output-dir",
        default="output/gm17_scattering_artifact_resolver_20260630_013623",
        help="A0 resolver output directory containing artifact_manifest.csv.",
    )
    parser.add_argument(
        "--join-validation-output-dir",
        required=True,
        help="A0.2b join validation output directory containing join_key_validation_summary.csv.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory. Defaults to output/gm17_experimentA_schema_validation_<timestamp>.",
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
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def read_manifest(resolver_output_dir: Path) -> dict[str, dict[str, str]]:
    manifest_path = resolver_output_dir / ARTIFACT_MANIFEST
    if not manifest_path.exists():
        raise FileNotFoundError(manifest_path)
    rows = read_csv_dicts(manifest_path)
    return {row.get("artifact_id", ""): row for row in rows if row.get("artifact_id")}


def read_join_summary(join_validation_output_dir: Path) -> dict[str, dict[str, str]]:
    summary_path = join_validation_output_dir / JOIN_SUMMARY
    if not summary_path.exists():
        raise FileNotFoundError(summary_path)
    rows = read_csv_dicts(summary_path)
    return {row.get("join_pair", ""): row for row in rows if row.get("join_pair")}


def artifact_path(row: dict[str, str]) -> Path | None:
    path_text = row.get("path", "")
    if not path_text:
        return None
    return Path(path_text)


def header_columns(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        try:
            return next(reader)
        except StopIteration:
            return []


def row_count_if_small(path: Path, max_bytes: int = 50_000_000) -> int | None:
    try:
        if path.stat().st_size > max_bytes:
            return None
        with path.open("rb") as f:
            line_count = sum(1 for _ in f)
        return max(0, line_count - 1)
    except OSError:
        return None


def has_alias(columns: list[str], canonical: str) -> bool:
    if canonical == "center_error":
        return any(col in CANONICAL_ALIASES[canonical] or "center_error" in col or "center_err" in col for col in columns)
    if canonical == "oracle_fields":
        return any(
            col in CANONICAL_ALIASES[canonical] or col.startswith("oracle_") or col.startswith("best_")
            for col in columns
        )
    if canonical == "final_fields":
        return any(col.startswith("final_") for col in columns)
    return any(alias in columns for alias in CANONICAL_ALIASES[canonical])


def observed_aliases(columns: list[str], canonical_fields: list[str]) -> list[str]:
    observed: list[str] = []
    for canonical in canonical_fields:
        if canonical == "center_error":
            observed.extend([col for col in columns if col in CANONICAL_ALIASES[canonical] or "center_error" in col or "center_err" in col])
        elif canonical == "oracle_fields":
            observed.extend(
                [
                    col
                    for col in columns
                    if col in CANONICAL_ALIASES[canonical] or col.startswith("oracle_") or col.startswith("best_")
                ]
            )
        elif canonical == "final_fields":
            observed.extend([col for col in columns if col.startswith("final_")])
        else:
            observed.extend([alias for alias in CANONICAL_ALIASES[canonical] if alias in columns])
    return sorted(dict.fromkeys(observed))


def missing_aliases(columns: list[str], canonical_fields: list[str]) -> list[str]:
    return [field for field in canonical_fields if not has_alias(columns, field)]


def make_check(
    check_id: str,
    category: str,
    status: str,
    required_fields: list[str] | str,
    observed_fields: list[str] | str,
    blocking_issue: str = "",
    notes: str = "",
) -> CheckResult:
    if isinstance(required_fields, list):
        required = ";".join(required_fields)
    else:
        required = required_fields
    if isinstance(observed_fields, list):
        observed = ";".join(observed_fields)
    else:
        observed = observed_fields
    return CheckResult(check_id, category, status, required, observed, blocking_issue, notes)


def artifact_headers(manifest: dict[str, dict[str, str]]) -> tuple[dict[str, list[str]], dict[str, int | None]]:
    headers: dict[str, list[str]] = {}
    row_counts: dict[str, int | None] = {}
    for artifact_id in ALLOWED_SOURCE_ARTIFACTS:
        row = manifest.get(artifact_id)
        path = artifact_path(row) if row else None
        if row and str(row.get("exists", "")).lower() == "true" and path and path.exists():
            headers[artifact_id] = header_columns(path)
            row_counts[artifact_id] = row_count_if_small(path)
        else:
            headers[artifact_id] = []
            row_counts[artifact_id] = None
    return headers, row_counts


def check_artifact_presence(manifest: dict[str, dict[str, str]]) -> CheckResult:
    missing: list[str] = []
    observed: list[str] = []
    for artifact_id in ALLOWED_SOURCE_ARTIFACTS:
        row = manifest.get(artifact_id)
        if row and str(row.get("exists", "")).lower() == "true":
            observed.append(artifact_id)
        else:
            missing.append(artifact_id)
    status = "GO" if not missing else "HOLD"
    return make_check(
        "artifact_presence",
        "artifact",
        status,
        sorted(ALLOWED_SOURCE_ARTIFACTS),
        sorted(observed),
        ";".join(missing),
        "resolved from A0 artifact_manifest; no source values read",
    )


def check_line_separation(manifest: dict[str, dict[str, str]]) -> CheckResult:
    bad: list[str] = []
    line_gp: list[str] = []
    for artifact_id, row in manifest.items():
        if row.get("line") == "Line-GP":
            line_gp.append(artifact_id)
            if row.get("status") != "EXCLUDED_LINE":
                bad.append(artifact_id)
    status = "GO" if not bad else "STOP"
    return make_check(
        "line_fb_line_gp_separation",
        "line_boundary",
        status,
        "Line-GP artifacts marked EXCLUDED_LINE and not used",
        line_gp,
        ";".join(bad),
        "schema validator uses only Line-FB/post-inference audit artifacts",
    )


def check_candidate_bank_schema(headers: dict[str, list[str]]) -> CheckResult:
    required = ["target_identity", "scene", "sar_frame_num", "gm17_track_id", "candidate_id", "cx", "cy", "w", "h", "candidate_source"]
    columns = headers["A001_candidate_bank"]
    missing = missing_aliases(columns, required)
    status = "GO" if not missing else "HOLD"
    return make_check(
        "a001_candidate_bank_schema",
        "candidate_rank_chain",
        status,
        required,
        observed_aliases(columns, required),
        ";".join(missing),
        "candidate_source is provenance only; no scoring use authorized",
    )


def check_frozen_ranked_schema(headers: dict[str, list[str]]) -> CheckResult:
    required = ["target_identity", "scene", "sar_frame_num", "gm17_track_id", "candidate_id", "cx", "cy", "w", "h", "rank"]
    columns = headers["frozen_ranked_candidates"]
    missing = missing_aliases(columns, required)
    status = "GO" if not missing else "HOLD"
    return make_check(
        "frozen_ranked_schema",
        "candidate_rank_chain",
        status,
        required,
        observed_aliases(columns, required),
        ";".join(missing),
        "rank/pilot_rank is a frozen-output reference only; no reranking or retuning",
    )


def check_a008_factor_joined_schema(headers: dict[str, list[str]]) -> CheckResult:
    required = ["target_identity", "scene", "sar_frame_num", "gm17_track_id", "candidate_id", "cx", "cy", "w", "h"]
    columns = headers["A008_candidate_factor_joined"]
    missing = missing_aliases(columns, required)
    status = "GO" if not missing else "HOLD"
    return make_check(
        "a008_candidate_factor_joined_schema",
        "candidate_rank_chain",
        status,
        required,
        observed_aliases(columns, required + ["candidate_source"]),
        ";".join(missing),
        "diagnostic field availability and double-counting audit readiness only",
    )


def check_a005_a007_context_schema(headers: dict[str, list[str]]) -> CheckResult:
    required_by_artifact = {
        "A005_optical_temporal_prior": ["target_identity", "scene", "sar_frame_num", "gm17_track_id"],
        "A007_signed_escape_posterior": ["target_identity", "scene", "sar_frame_num", "gm17_track_id"],
    }
    missing: list[str] = []
    observed: list[str] = []
    for artifact_id, required in required_by_artifact.items():
        columns = headers[artifact_id]
        observed.extend([f"{artifact_id}:{field}" for field in observed_aliases(columns, required)])
        missing.extend([f"{artifact_id}:{field}" for field in missing_aliases(columns, required)])
    status = "GO" if not missing else "HOLD"
    return make_check(
        "a005_a007_context_schema",
        "context_readiness",
        status,
        [f"{artifact}:{';'.join(fields)}" for artifact, fields in required_by_artifact.items()],
        observed,
        ";".join(missing),
        "context schema only; no center-size likelihood or descriptor computation",
    )


def check_per_target_audit_schema(headers: dict[str, list[str]]) -> CheckResult:
    required = [
        "target_identity",
        "scene",
        "sar_frame_num",
        "gm17_track_id",
        "axis_aligned_proxy_iou",
        "center_error",
        "oracle_fields",
        "final_fields",
    ]
    columns = headers["per_target_audit_output"]
    missing = missing_aliases(columns, required)
    status = "GO" if not missing else "HOLD"
    return make_check(
        "per_target_audit_schema",
        "post_inference_audit_schema",
        status,
        required,
        observed_aliases(columns, required),
        ";".join(missing),
        "audit fields are header-confirmed only; values not read; AABB proxy is not rotated IoU",
    )


def check_a019_schema(headers: dict[str, list[str]]) -> CheckResult:
    required = ["target_identity", "scene", "sar_frame_num", "final_fields"]
    columns = headers["A019_final_boxes"]
    missing = missing_aliases(columns, required)
    status = "GO" if not missing else "HOLD"
    return make_check(
        "a019_final_boxes_schema",
        "post_inference_audit_schema",
        status,
        required,
        observed_aliases(columns, required),
        ";".join(missing),
        "A019 final_* fields are audit-only headers; numeric values not read",
    )


def check_a021_schema(headers: dict[str, list[str]]) -> CheckResult:
    required = ["target_identity", "scene", "sar_frame_num", "condition_fields"]
    columns = headers["A021_condition_labels"]
    missing = missing_aliases(columns, required)
    status = "GO" if not missing else "HOLD"
    return make_check(
        "a021_condition_schema",
        "post_inference_audit_schema",
        status,
        required,
        observed_aliases(columns, required),
        ";".join(missing),
        "A021 condition/truncation/occlusion fields are audit-only headers; values not read",
    )


def check_join_policy(join_summary: dict[str, dict[str, str]]) -> list[CheckResult]:
    checks: list[CheckResult] = []
    required_pairs = [
        "per_target_audit_to_A019",
        "per_target_audit_to_A021",
        "frozen_ranked_to_per_target_audit",
    ]
    for pair in required_pairs:
        row = join_summary.get(pair)
        status_value = row.get("status", "") if row else ""
        ok = status_value in ALLOWED_JOIN_STATUSES
        checks.append(
            make_check(
                f"join_policy_{pair}",
                "join_policy",
                "GO" if ok else "HOLD",
                "GO or POLICY_ACCEPTED_GO_FOR_LEFT_COVERAGE",
                status_value,
                "" if ok else f"join_status={status_value or 'missing'}",
                "uses A0.2b key-only join validation; A019/A021 track_id not required when policy accepted",
            )
        )
    return checks


def check_forbidden_inference_fields(headers: dict[str, list[str]]) -> CheckResult:
    violations: list[str] = []
    observed: list[str] = []
    for artifact_id in INFERENCE_FACING_ARTIFACTS:
        columns = set(headers.get(artifact_id, []))
        hits = sorted(columns.intersection(FORBIDDEN_IN_INFERENCE))
        if hits:
            violations.extend([f"{artifact_id}:{hit}" for hit in hits])
        observed.extend([f"{artifact_id}:checked"])
    status = "GO" if not violations else "STOP"
    return make_check(
        "forbidden_field_boundary",
        "field_layer",
        status,
        "no eval-only columns in inference-facing artifacts",
        observed,
        ";".join(violations),
        "final/condition/IoU/center-error fields may appear only in post-inference audit artifacts",
    )


def check_descriptor_independence() -> CheckResult:
    return make_check(
        "descriptor_independence",
        "descriptor_boundary",
        "GO",
        "SAR physical convention may remain HOLD without blocking Experiment A schema validation",
        "descriptor_extraction=HOLD; Experiment_A_schema_independent=true",
        "",
        "Experiment A schema validation does not compute or require SAR descriptors",
    )


def check_axis_proxy_boundary(headers: dict[str, list[str]]) -> CheckResult:
    columns = headers["per_target_audit_output"]
    has_proxy = has_alias(columns, "axis_aligned_proxy_iou")
    return make_check(
        "axis_aligned_proxy_iou_boundary",
        "metric_boundary",
        "GO" if has_proxy else "HOLD",
        "axis_aligned_proxy_iou header exists as audit-only AABB proxy",
        observed_aliases(columns, ["axis_aligned_proxy_iou"]),
        "" if has_proxy else "axis_aligned_proxy_iou_missing",
        "proxy is not rotated IoU and cannot support heading/orientation conclusions",
    )


def overall_status(checks: list[CheckResult]) -> str:
    counts = Counter(check.status for check in checks)
    if counts.get("STOP", 0):
        return "STOP"
    if counts.get("HOLD", 0):
        return "HOLD_FOR_SCHEMA_REVIEW"
    return "GO_FOR_EXPERIMENT_A_DECOMPOSITION_PROPOSAL"


def write_summary_csv(path: Path, checks: list[CheckResult]) -> None:
    fieldnames = [
        "check_id",
        "category",
        "status",
        "required_fields",
        "observed_fields",
        "blocking_issue",
        "notes",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for check in checks:
            writer.writerow(check.__dict__)


def markdown_check_table(checks: list[CheckResult]) -> str:
    cols = ["check_id", "category", "status", "blocking_issue", "notes"]
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    for check in checks:
        lines.append(
            "| "
            + " | ".join(
                [
                    check.check_id,
                    check.category,
                    check.status,
                    check.blocking_issue or "",
                    check.notes,
                ]
            )
            + " |"
        )
    return "\n".join(lines)


def write_report(
    path: Path,
    *,
    output_dir: Path,
    resolver_output_dir: Path,
    join_validation_output_dir: Path,
    checks: list[CheckResult],
    row_counts: dict[str, int | None],
) -> None:
    status = overall_status(checks)
    counts = Counter(check.status for check in checks)
    lines: list[str] = [
        "# GM17 Experiment A Schema Validation Report",
        "",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        "",
        f"Output directory: `{output_dir}`",
        f"Resolver output directory: `{resolver_output_dir}`",
        f"Join validation output directory: `{join_validation_output_dir}`",
        "",
        "This is A1 schema validation only. It is not Experiment A decomposition, not a metric report, not a performance conclusion, and not Phase5 approval.",
        "",
        f"Formal Phase5 remains `{FORMAL_PHASE5_STATUS}`.",
        "",
        "## Overall Status",
        "",
        f"`{status}`",
        "",
        f"- GO items: {counts.get('GO', 0)}",
        f"- HOLD items: {counts.get('HOLD', 0)}",
        f"- STOP items: {counts.get('STOP', 0)}",
        "",
        "Experiment A decomposition was not run.",
        "",
        "If the overall status is `GO_FOR_EXPERIMENT_A_DECOMPOSITION_PROPOSAL`, the next permissible step is to propose a decomposition run design for approval. It is not permission to run decomposition automatically.",
        "",
        "## Boundaries",
        "",
        "- Headers and resolver/join summaries were inspected.",
        "- Source audit values were not read for statistics.",
        "- IoU values were not read for statistics.",
        "- Center-error values were not read for statistics.",
        "- Final box numeric values were not read.",
        "- A021 condition/truncation/occlusion values were not read.",
        "- No high-IoU bins, failure buckets, or performance metrics were computed.",
        "- No SAR descriptor, scatter centroid, keyframe confidence, or soft-anchor simulation was computed.",
        "- Candidate bank and GM17 selector were not modified.",
        "",
        "## Checks",
        "",
        markdown_check_table(checks),
        "",
        "## Header-Level Row Count Notes",
        "",
        "Row counts are included only when cheap and were not used for metric computation.",
        "",
        "| artifact_id | row_count |",
        "|---|---:|",
    ]
    for artifact_id in sorted(row_counts):
        value = row_counts[artifact_id]
        lines.append(f"| `{artifact_id}` | {'' if value is None else value} |")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    root = repo_root()
    resolver_output_dir = resolve_cli_path(args.resolver_output_dir, root)
    join_validation_output_dir = resolve_cli_path(args.join_validation_output_dir, root)
    output_dir = resolve_cli_path(args.output_dir, root, "gm17_experimentA_schema_validation")
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest = read_manifest(resolver_output_dir)
    join_summary = read_join_summary(join_validation_output_dir)
    headers, row_counts = artifact_headers(manifest)

    checks: list[CheckResult] = [
        check_artifact_presence(manifest),
        check_line_separation(manifest),
        check_candidate_bank_schema(headers),
        check_frozen_ranked_schema(headers),
        check_a008_factor_joined_schema(headers),
        check_a005_a007_context_schema(headers),
        check_per_target_audit_schema(headers),
        check_a019_schema(headers),
        check_a021_schema(headers),
        check_forbidden_inference_fields(headers),
        check_axis_proxy_boundary(headers),
        check_descriptor_independence(),
    ]
    checks.extend(check_join_policy(join_summary))

    summary_csv = output_dir / "experimentA_schema_validation_summary.csv"
    report_md = output_dir / "experimentA_schema_validation_report.md"
    summary_json = output_dir / "experimentA_schema_validation_summary.json"

    write_summary_csv(summary_csv, checks)
    write_report(
        report_md,
        output_dir=output_dir,
        resolver_output_dir=resolver_output_dir,
        join_validation_output_dir=join_validation_output_dir,
        checks=checks,
        row_counts=row_counts,
    )

    status = overall_status(checks)
    counts = Counter(check.status for check in checks)
    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "script_scope": SCRIPT_SCOPE,
        "resolver_output_dir": str(resolver_output_dir),
        "join_validation_output_dir": str(join_validation_output_dir),
        "output_dir": str(output_dir),
        "overall_status": status,
        "status_counts": dict(counts),
        "formal_phase5_status": FORMAL_PHASE5_STATUS,
        "experiment_a_decomposition_ran": False,
        "metrics_computed": False,
        "iou_computed": False,
        "center_error_computed": False,
        "descriptor_computed": False,
        "scatter_centroid_computed": False,
        "keyframe_confidence_computed": False,
        "soft_anchor_simulation_ran": False,
        "candidate_bank_modified": False,
        "selector_modified": False,
        "performance_conclusion_produced": False,
        "source_value_read_scope": "headers_and_join_summary_only; no audit value statistics",
        "outputs": {
            "experimentA_schema_validation_summary": str(summary_csv),
            "experimentA_schema_validation_report": str(report_md),
            "experimentA_schema_validation_summary_json": str(summary_json),
        },
        "checks": [check.__dict__ for check in checks],
        "row_counts": row_counts,
    }
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({"output_dir": str(output_dir), "overall_status": status, "status_counts": dict(counts)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
