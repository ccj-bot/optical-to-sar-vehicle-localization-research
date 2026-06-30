#!/usr/bin/env python
"""Validate GM17 post-inference audit join keys only.

This A0.2 utility reads only join-key columns from resolver-selected artifacts.
It does not compute metrics, IoU, center error, SAR descriptors, keyframe
confidence, or any performance result.
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

import pandas as pd


SCRIPT_SCOPE = "A0_2_post_inference_key_only_join_validation"
FORMAL_PHASE5_STATUS = "BLOCKED_FOR_OOF_CALIBRATION"

ARTIFACT_MANIFEST = "artifact_manifest.csv"

CANONICAL_ALIASES: dict[str, list[str]] = {
    "target_identity": ["target_identity", "target_id"],
    "scene": ["scene", "scene_id"],
    "sar_frame_num": ["sar_frame_num", "sar_frame", "frame_id"],
    "gm17_track_id": ["gm17_track_id", "track_id"],
    "candidate_id": ["candidate_id"],
    "sample_id": ["sample_id"],
    "final_id": ["final_id"],
}

FORBIDDEN_VALUE_COLUMNS = {
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
    "visibility_label",
    "partial_visible",
}


@dataclass(frozen=True)
class JoinSpec:
    join_pair: str
    left_artifact_id: str
    right_artifact_id: str
    required_keys: tuple[str, ...]
    optional_keys: tuple[str, ...] = ()
    left_duplicate_policy: str = "hold"
    right_duplicate_policy: str = "hold"
    right_superset_allowed: bool = False
    left_coverage_required: bool = False
    notes: str = ""


JOIN_SPECS: tuple[JoinSpec, ...] = (
    JoinSpec(
        join_pair="per_target_audit_to_A019",
        left_artifact_id="per_target_audit_output",
        right_artifact_id="A019_final_boxes",
        required_keys=("target_identity", "scene", "sar_frame_num"),
        optional_keys=("sample_id", "final_id"),
        right_superset_allowed=True,
        left_coverage_required=True,
        notes="target/frame-level post-inference audit join; final_* values are not read",
    ),
    JoinSpec(
        join_pair="per_target_audit_to_A021",
        left_artifact_id="per_target_audit_output",
        right_artifact_id="A021_condition_labels",
        required_keys=("target_identity", "scene", "sar_frame_num"),
        optional_keys=("sample_id",),
        right_superset_allowed=True,
        left_coverage_required=True,
        notes="target/frame-level post-inference audit join; condition/truncation/occlusion values are not read",
    ),
    JoinSpec(
        join_pair="frozen_ranked_to_per_target_audit",
        left_artifact_id="frozen_ranked_candidates",
        right_artifact_id="per_target_audit_output",
        required_keys=("target_identity", "scene", "sar_frame_num", "gm17_track_id"),
        left_duplicate_policy="expected_many",
        notes="candidate-level frozen rows to target/frame/track audit; left duplicates are expected candidate rows",
    ),
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate GM17 post-inference join keys only.")
    parser.add_argument(
        "--resolver-output-dir",
        default="output/gm17_scattering_artifact_resolver_20260630_013623",
        help="A0 resolver output directory containing artifact_manifest.csv.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory. Defaults to output/gm17_post_inference_join_key_validation_<timestamp>.",
    )
    return parser.parse_args()


def resolve_cli_path(path_text: str | None, root: Path) -> Path:
    if not path_text:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return root / "output" / f"gm17_post_inference_join_key_validation_{timestamp}"
    path = Path(path_text)
    return path if path.is_absolute() else root / path


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


def read_manifest(resolver_output_dir: Path) -> dict[str, dict[str, str]]:
    manifest_path = resolver_output_dir / ARTIFACT_MANIFEST
    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing resolver artifact manifest: {manifest_path}")
    with manifest_path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    return {row.get("artifact_id", ""): row for row in rows if row.get("artifact_id")}


def artifact_path(row: dict[str, str]) -> Path | None:
    path_text = row.get("path", "")
    if not path_text:
        return None
    return Path(path_text)


def header_columns(path: Path) -> list[str]:
    return list(pd.read_csv(path, nrows=0, dtype=str, encoding="utf-8-sig").columns)


def pick_alias(columns: list[str], canonical: str) -> str | None:
    available = set(columns)
    for alias in CANONICAL_ALIASES[canonical]:
        if alias in available:
            return alias
    return None


def selected_keys_for_artifact(path: Path, requested_keys: tuple[str, ...]) -> tuple[dict[str, str], list[str]]:
    columns = header_columns(path)
    alias_map: dict[str, str] = {}
    missing: list[str] = []
    for canonical in requested_keys:
        alias = pick_alias(columns, canonical)
        if alias:
            alias_map[canonical] = alias
        else:
            missing.append(canonical)
    return alias_map, missing


def enforce_no_forbidden_value_columns(usecols: list[str], artifact_id: str) -> None:
    forbidden = sorted(set(usecols).intersection(FORBIDDEN_VALUE_COLUMNS))
    if forbidden:
        raise RuntimeError(
            f"Refusing to read forbidden value columns for {artifact_id}: {forbidden}. "
            "This validator is key-only."
        )


def load_key_frame(artifact_id: str, path: Path, canonical_to_alias: dict[str, str]) -> pd.DataFrame:
    usecols = list(dict.fromkeys(canonical_to_alias.values()))
    enforce_no_forbidden_value_columns(usecols, artifact_id)
    df = pd.read_csv(path, usecols=usecols, dtype=str, encoding="utf-8-sig")
    out = pd.DataFrame()
    for canonical, alias in canonical_to_alias.items():
        out[canonical] = df[alias].map(
            lambda value, key=canonical: normalize_text(value, frame_like=(key == "sar_frame_num"))
        )
    return out


def key_counter(df: pd.DataFrame, keys: tuple[str, ...]) -> Counter[tuple[str, ...]]:
    nonmissing = df.loc[~missing_key_mask(df, keys), list(keys)]
    tuples = [tuple(row) for row in nonmissing.itertuples(index=False, name=None)]
    return Counter(tuples)


def missing_key_mask(df: pd.DataFrame, keys: tuple[str, ...]) -> pd.Series:
    mask = pd.Series(False, index=df.index)
    for key in keys:
        mask = mask | df[key].isna() | df[key].astype(str).eq("")
    return mask


def duplicate_key_count(counter: Counter[tuple[str, ...]]) -> int:
    return sum(1 for count in counter.values() if count > 1)


def key_examples(keys: set[tuple[str, ...]], key_names: tuple[str, ...], limit: int = 10) -> list[dict[str, str]]:
    examples: list[dict[str, str]] = []
    for key_tuple in sorted(keys)[:limit]:
        examples.append(dict(zip(key_names, key_tuple)))
    return examples


def validation_status(
    *,
    missing_columns: list[str],
    left_missing_rows: int,
    right_missing_rows: int,
    left_duplicate_count: int,
    right_duplicate_count: int,
    left_only_count: int,
    right_only_count: int,
    spec: JoinSpec,
) -> str:
    if missing_columns:
        return "HOLD"
    if left_missing_rows or right_missing_rows:
        return "HOLD"
    if spec.left_duplicate_policy != "expected_many" and left_duplicate_count:
        return "HOLD"
    if spec.right_duplicate_policy != "expected_many" and right_duplicate_count:
        return "HOLD"
    if left_only_count:
        return "HOLD"
    if right_only_count:
        if spec.left_coverage_required and spec.right_superset_allowed:
            return "POLICY_ACCEPTED_GO_FOR_LEFT_COVERAGE"
        return "HOLD"
    return "GO"


def validate_join(
    spec: JoinSpec,
    manifest: dict[str, dict[str, str]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    left_row = manifest.get(spec.left_artifact_id)
    right_row = manifest.get(spec.right_artifact_id)
    missing_artifacts = [
        artifact
        for artifact, row in ((spec.left_artifact_id, left_row), (spec.right_artifact_id, right_row))
        if not row or str(row.get("exists", "")).lower() != "true"
    ]

    detail: dict[str, Any] = {
        "join_pair": spec.join_pair,
        "left_artifact_id": spec.left_artifact_id,
        "right_artifact_id": spec.right_artifact_id,
        "requested_keys": list(spec.required_keys),
        "optional_keys": list(spec.optional_keys),
        "left_examples": {},
        "right_examples": {},
    }

    if missing_artifacts:
        row = {
            "join_pair": spec.join_pair,
            "left_artifact_id": spec.left_artifact_id,
            "right_artifact_id": spec.right_artifact_id,
            "proposed_keys": ";".join(spec.required_keys),
            "left_rows_read": 0,
            "right_rows_read": 0,
            "left_missing_key_rows": 0,
            "right_missing_key_rows": 0,
            "left_duplicate_key_count": 0,
            "right_duplicate_key_count": 0,
            "left_only_key_count": 0,
            "right_only_key_count": 0,
            "status": "HOLD",
            "notes": f"missing_artifacts={';'.join(missing_artifacts)}; key_columns_only; no_metrics",
        }
        detail["status"] = "HOLD"
        detail["notes"] = row["notes"]
        return row, detail

    assert left_row is not None and right_row is not None
    left_path = artifact_path(left_row)
    right_path = artifact_path(right_row)
    if left_path is None or right_path is None or not left_path.exists() or not right_path.exists():
        missing_paths = []
        if left_path is None or not left_path.exists():
            missing_paths.append(spec.left_artifact_id)
        if right_path is None or not right_path.exists():
            missing_paths.append(spec.right_artifact_id)
        row = {
            "join_pair": spec.join_pair,
            "left_artifact_id": spec.left_artifact_id,
            "right_artifact_id": spec.right_artifact_id,
            "proposed_keys": ";".join(spec.required_keys),
            "left_rows_read": 0,
            "right_rows_read": 0,
            "left_missing_key_rows": 0,
            "right_missing_key_rows": 0,
            "left_duplicate_key_count": 0,
            "right_duplicate_key_count": 0,
            "left_only_key_count": 0,
            "right_only_key_count": 0,
            "status": "HOLD",
            "notes": f"missing_paths={';'.join(missing_paths)}; key_columns_only; no_metrics",
        }
        detail["status"] = "HOLD"
        detail["notes"] = row["notes"]
        return row, detail

    left_header = header_columns(left_path)
    right_header = header_columns(right_path)
    shared_optional_keys = tuple(
        key
        for key in spec.optional_keys
        if pick_alias(left_header, key) is not None and pick_alias(right_header, key) is not None
    )
    proposed_keys = (*spec.required_keys, *shared_optional_keys)

    left_aliases, left_missing_columns = selected_keys_for_artifact(left_path, proposed_keys)
    right_aliases, right_missing_columns = selected_keys_for_artifact(right_path, proposed_keys)
    missing_columns = [f"left:{col}" for col in left_missing_columns] + [
        f"right:{col}" for col in right_missing_columns
    ]

    if missing_columns:
        row = {
            "join_pair": spec.join_pair,
            "left_artifact_id": spec.left_artifact_id,
            "right_artifact_id": spec.right_artifact_id,
            "proposed_keys": ";".join(proposed_keys),
            "left_rows_read": 0,
            "right_rows_read": 0,
            "left_missing_key_rows": 0,
            "right_missing_key_rows": 0,
            "left_duplicate_key_count": 0,
            "right_duplicate_key_count": 0,
            "left_only_key_count": 0,
            "right_only_key_count": 0,
            "status": "HOLD",
            "notes": f"missing_key_columns={';'.join(missing_columns)}; key_columns_only; no_metrics",
        }
        detail.update(
            {
                "status": "HOLD",
                "notes": row["notes"],
                "left_path": str(left_path),
                "right_path": str(right_path),
                "left_aliases": left_aliases,
                "right_aliases": right_aliases,
            }
        )
        return row, detail

    left_df = load_key_frame(spec.left_artifact_id, left_path, left_aliases)
    right_df = load_key_frame(spec.right_artifact_id, right_path, right_aliases)

    left_missing_rows = int(missing_key_mask(left_df, proposed_keys).sum())
    right_missing_rows = int(missing_key_mask(right_df, proposed_keys).sum())
    left_counts = key_counter(left_df, proposed_keys)
    right_counts = key_counter(right_df, proposed_keys)
    left_keys = set(left_counts)
    right_keys = set(right_counts)
    left_only = left_keys - right_keys
    right_only = right_keys - left_keys
    left_dups = duplicate_key_count(left_counts)
    right_dups = duplicate_key_count(right_counts)

    status = validation_status(
        missing_columns=[],
        left_missing_rows=left_missing_rows,
        right_missing_rows=right_missing_rows,
        left_duplicate_count=left_dups,
        right_duplicate_count=right_dups,
        left_only_count=len(left_only),
        right_only_count=len(right_only),
        spec=spec,
    )

    notes = [
        "key_columns_only",
        "no_iou",
        "no_center_error",
        "no_final_box_values",
        "no_condition_values",
        "no_performance",
    ]
    if shared_optional_keys:
        notes.append(f"shared_optional_keys={';'.join(shared_optional_keys)}")
    if spec.left_duplicate_policy == "expected_many" and left_dups:
        notes.append("left_duplicates_expected_candidate_rows")
    if status == "POLICY_ACCEPTED_GO_FOR_LEFT_COVERAGE":
        notes.append("left_coverage_required_satisfied")
        notes.append("right_only_keys_allowed_as_annotation_superset")
    if status == "HOLD":
        notes.append("requires_policy_or_key_coverage_review")

    row = {
        "join_pair": spec.join_pair,
        "left_artifact_id": spec.left_artifact_id,
        "right_artifact_id": spec.right_artifact_id,
        "proposed_keys": ";".join(proposed_keys),
        "left_rows_read": int(len(left_df)),
        "right_rows_read": int(len(right_df)),
        "left_missing_key_rows": left_missing_rows,
        "right_missing_key_rows": right_missing_rows,
        "left_duplicate_key_count": left_dups,
        "right_duplicate_key_count": right_dups,
        "left_only_key_count": int(len(left_only)),
        "right_only_key_count": int(len(right_only)),
        "status": status,
        "notes": "; ".join(notes),
    }

    detail.update(
        {
            "status": status,
            "notes": row["notes"],
            "left_path": str(left_path),
            "right_path": str(right_path),
            "left_aliases": left_aliases,
            "right_aliases": right_aliases,
            "proposed_keys": list(proposed_keys),
            "left_only_examples": key_examples(left_only, proposed_keys),
            "right_only_examples": key_examples(right_only, proposed_keys),
            "left_duplicate_examples": key_examples(
                {key for key, count in left_counts.items() if count > 1}, proposed_keys
            ),
            "right_duplicate_examples": key_examples(
                {key for key, count in right_counts.items() if count > 1}, proposed_keys
            ),
        }
    )
    return row, detail


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "join_pair",
        "left_artifact_id",
        "right_artifact_id",
        "proposed_keys",
        "left_rows_read",
        "right_rows_read",
        "left_missing_key_rows",
        "right_missing_key_rows",
        "left_duplicate_key_count",
        "right_duplicate_key_count",
        "left_only_key_count",
        "right_only_key_count",
        "status",
        "notes",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def markdown_table(rows: list[dict[str, Any]]) -> str:
    cols = [
        "join_pair",
        "proposed_keys",
        "left_missing_key_rows",
        "right_missing_key_rows",
        "left_duplicate_key_count",
        "right_duplicate_key_count",
        "left_only_key_count",
        "right_only_key_count",
        "status",
    ]
    out = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    for row in rows:
        out.append("| " + " | ".join(str(row[col]) for col in cols) + " |")
    return "\n".join(out)


def write_report(path: Path, *, output_dir: Path, rows: list[dict[str, Any]], details: list[dict[str, Any]]) -> None:
    lines: list[str] = [
        "# GM17 Post-Inference Join Key Validation Report",
        "",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        "",
        f"Output directory: `{output_dir}`",
        "",
        "This is A0.2 key-only join validation. It is not Experiment A, not an experiment report, not a performance conclusion, and not Phase5 approval.",
        "",
        f"Formal Phase5 remains `{FORMAL_PHASE5_STATUS}`.",
        "",
        "## Boundaries",
        "",
        "- Read only join-key columns.",
        "- Did not read IoU, center error, final box numeric values, condition/truncation/occlusion values, oracle labels, or descriptor values.",
        "- Did not compute metrics, IoU, center error, descriptors, scatter centroid, keyframe confidence, or soft-anchor simulation.",
        "- Did not modify candidate bank or GM17 selector.",
        "",
        "## Summary",
        "",
        markdown_table(rows),
        "",
        "## Key-Only Examples",
        "",
        "Examples are capped at 10 per category and contain only proposed key columns.",
        "",
    ]
    for detail in details:
        lines.extend(
            [
                f"### {detail['join_pair']}",
                "",
                f"- Status: `{detail.get('status', '')}`",
                f"- Notes: {detail.get('notes', '')}",
                f"- Proposed keys: `{';'.join(detail.get('proposed_keys', detail.get('requested_keys', [])))}`",
                "",
            ]
        )
        for label in [
            "left_only_examples",
            "right_only_examples",
            "left_duplicate_examples",
            "right_duplicate_examples",
        ]:
            examples = detail.get(label, [])
            lines.append(f"- {label}:")
            if examples:
                lines.append("")
                lines.append("```json")
                lines.append(json.dumps(examples, ensure_ascii=False, indent=2))
                lines.append("```")
                lines.append("")
            else:
                lines.append("  none")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    root = repo_root()
    resolver_output_dir = resolve_cli_path(args.resolver_output_dir, root)
    output_dir = resolve_cli_path(args.output_dir, root)
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest = read_manifest(resolver_output_dir)
    rows: list[dict[str, Any]] = []
    details: list[dict[str, Any]] = []
    for spec in JOIN_SPECS:
        row, detail = validate_join(spec, manifest)
        rows.append(row)
        details.append(detail)

    summary_csv = output_dir / "join_key_validation_summary.csv"
    report_md = output_dir / "join_key_validation_report.md"
    summary_json = output_dir / "join_key_validation_summary.json"

    write_csv(summary_csv, rows)
    write_report(report_md, output_dir=output_dir, rows=rows, details=details)

    status_counts = Counter(str(row["status"]) for row in rows)
    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "script_scope": SCRIPT_SCOPE,
        "resolver_output_dir": str(resolver_output_dir),
        "output_dir": str(output_dir),
        "formal_phase5_status": FORMAL_PHASE5_STATUS,
        "experiment_ran": False,
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
        "forbidden_value_columns_read": False,
        "source_rows_read_scope": "join_key_columns_only",
        "status_counts": dict(status_counts),
        "outputs": {
            "join_key_validation_summary": str(summary_csv),
            "join_key_validation_report": str(report_md),
            "join_key_validation_summary_json": str(summary_json),
        },
        "joins": rows,
        "details": details,
    }
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({"output_dir": str(output_dir), "status_counts": dict(status_counts), "joins": rows}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
