from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


TASK_NAME = "person_terg_r2_runtime_grounding_and_full_stream_hypothesis_management_20260830"
RUNS = ("R01ZF", "R02ZF", "R03ZF")
MODES = ("CAUSAL_REPLAY", "FIXED_LAG_100MS", "FULL_CONTEXT_OFFLINE")
EXPECTED_P0_AVAILABLE = {"R01ZF": 141, "R02ZF": 22, "R03ZF": 36}
EXPECTED_FIGURES = {
    "01_full_stream_observability_and_anchor_overview.png",
    "02_lifecycle_R01ZF_causal_replay.png",
    "02_lifecycle_R01ZF_fixed_lag_100ms.png",
    "02_lifecycle_R01ZF_full_context_offline.png",
    "02_lifecycle_R02ZF_causal_replay.png",
    "02_lifecycle_R02ZF_fixed_lag_100ms.png",
    "02_lifecycle_R02ZF_full_context_offline.png",
    "02_lifecycle_R03ZF_causal_replay.png",
    "02_lifecycle_R03ZF_fixed_lag_100ms.png",
    "02_lifecycle_R03ZF_full_context_offline.png",
    "03_full_stream_q95_and_shell_burden.png",
    "04_negative_time_structural_control.png",
    "05_r1_semantic_corrections.png",
    "06_r02_anchor_relation_propagation_chain_blocked.png",
}


def parse_bool(value: Any) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no", "", "nan", "none"}:
        return False
    raise ValueError(f"not a boolean value: {value!r}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def npy_header_from_npz(path: Path, member: str) -> tuple[tuple[int, ...], np.dtype[Any]]:
    with zipfile.ZipFile(path) as archive:
        if member not in archive.namelist():
            raise AssertionError(f"{path.name} missing {member}")
        with archive.open(member) as stream:
            major, minor = np.lib.format.read_magic(stream)
            if (major, minor) == (1, 0):
                shape, _, dtype = np.lib.format.read_array_header_1_0(stream)
            elif (major, minor) == (2, 0):
                shape, _, dtype = np.lib.format.read_array_header_2_0(stream)
            else:
                shape, _, dtype = np.lib.format._read_array_header(stream, (major, minor))
    return tuple(shape), np.dtype(dtype)


class Validator:
    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace.resolve()
        self.output = self.workspace / "output" / TASK_NAME
        self.pre = self.output / "pre_reference"
        self.post = self.output / "post_reference_evaluation_only"
        self.checks: list[dict[str, Any]] = []

    def check(self, name: str, condition: bool, detail: str) -> None:
        passed = bool(condition)
        self.checks.append({"check": name, "passed": passed, "detail": detail})
        if not passed:
            raise AssertionError(f"{name}: {detail}")

    def read_csv(self, relative: str) -> pd.DataFrame:
        path = self.output / relative
        self.check(f"exists:{relative}", path.is_file(), str(path))
        return pd.read_csv(path, low_memory=False)

    def validate_registry(self) -> None:
        registry = self.read_csv("pre_reference/full_stream_frame_registry_pre_reference.csv")
        self.check("registry_total", len(registry) == 1485, f"rows={len(registry)}")
        counts = registry.groupby("run_id").size().to_dict()
        self.check("registry_per_run", counts == {run: 495 for run in RUNS}, f"counts={counts}")
        ranges = registry.groupby("run_id")["sar_frame_index"].agg(["min", "max", "nunique"])
        valid_ranges = all(int(row["min"]) == 0 and int(row["max"]) == 494 and int(row["nunique"]) == 495 for _, row in ranges.iterrows())
        self.check("registry_frame_ranges", valid_ranges, ranges.to_dict(orient="index").__repr__())
        geometry = registry.groupby("run_id")[["sar_width_px", "sar_height_px", "theta_low_deg", "theta_high_deg"]].nunique()
        self.check("frozen_geometry_constant_per_run", bool((geometry == 1).all().all()), geometry.to_dict(orient="index").__repr__())

    def validate_masks_and_parity(self) -> None:
        masks = sorted((self.pre / "full_stream_q95_masks").glob("*.npz"))
        self.check("mask_count", len(masks) == 1485, f"masks={len(masks)}")
        expected = {f"{run}_SARF{frame:06d}.npz" for run in RUNS for frame in range(495)}
        self.check("mask_names_complete", {path.name for path in masks} == expected, "expected all R01/R02/R03 F000000-F000494")
        bad_headers: list[str] = []
        for path in masks:
            try:
                shape, dtype = npy_header_from_npz(path, "Q095.npy")
                if shape != (592, 1024) or dtype.kind not in {"i", "u"}:
                    bad_headers.append(f"{path.name}:{shape}:{dtype}")
            except Exception as error:  # validation should report every malformed archive succinctly
                bad_headers.append(f"{path.name}:{error}")
        self.check("mask_headers_readable", not bad_headers, f"bad={bad_headers[:5]}")

        parity = self.read_csv("pre_reference/frozen_coverage_q95_recomputation_parity.csv")
        exact = parity["q95_label_mask_pixel_exact"].map(parse_bool)
        counts_match = parity["region_count_match"].map(parse_bool)
        self.check("frozen_parity_frame_count", len(parity) == 202, f"rows={len(parity)}")
        self.check("frozen_q95_pixel_exact", bool(exact.all()), f"exact_fraction={float(exact.mean())}")
        self.check("frozen_region_counts_match", bool(counts_match.all()), f"match_fraction={float(counts_match.mean())}")

    def validate_p0_and_modes(self) -> None:
        availability = self.read_csv("pre_reference/full_stream_frozen_p0_availability_pre_reference.csv")
        self.check("p0_pair_rows", len(availability) == 1482, f"rows={len(availability)}")
        available = availability[availability["p0_model_available"].map(parse_bool)].groupby("run_id").size().to_dict()
        self.check("p0_available_counts", available == EXPECTED_P0_AVAILABLE, f"counts={available}")
        unavailable_states = set(availability.loc[~availability["p0_model_available"].map(parse_bool), "p0_state"].astype(str))
        self.check("p0_unavailable_explicit", unavailable_states == {"SAR_P0_CONTINUITY_INTERFACE_UNAVAILABLE"}, f"states={unavailable_states}")

        for relative in (
            "pre_reference/full_stream_frame_observability_pre_reference.csv",
            "pre_reference/full_stream_optical_shells_pre_reference.csv",
            "pre_reference/full_stream_hypothesis_lifecycle_with_anchor_state_pre_reference.csv",
            "pre_reference/runtime_unary_anchor_hypothesis_ledger_pre_reference.csv",
        ):
            table = self.read_csv(relative)
            modes = set(table["mode"].dropna().astype(str))
            self.check(f"three_modes:{Path(relative).name}", modes == set(MODES), f"modes={sorted(modes)}")

    def validate_pre_reference_boundaries(self) -> None:
        shells = self.read_csv("pre_reference/full_stream_optical_shells_pre_reference.csv")
        for column in ("manual_reference_used", "sar_range_assigned_by_optical", "strict_runtime_identity_claimed"):
            values = shells[column].map(parse_bool)
            self.check(f"shell_boundary:{column}", not bool(values.any()), f"true_count={int(values.sum())}")

        regions = self.read_csv("pre_reference/full_stream_q95_response_regions_pre_reference.csv")
        for column in ("reference_used_for_region_generation", "region_is_final_person_box"):
            values = regions[column].map(parse_bool)
            self.check(f"region_boundary:{column}", not bool(values.any()), f"true_count={int(values.sum())}")

        p0_edges = self.read_csv("pre_reference/full_stream_available_frozen_p0_q95_edges_pre_reference.csv")
        p0_reference = p0_edges["reference_used"].map(parse_bool)
        self.check("p0_edges_no_reference", not bool(p0_reference.any()), f"true_count={int(p0_reference.sum())}")

        hypotheses = self.read_csv("pre_reference/stream_hypothesis_object_registry_pre_reference.csv")
        for column in ("raw_fragment_is_person_truth", "cross_modal_identity_committed"):
            values = hypotheses[column].map(parse_bool)
            self.check(f"hypothesis_boundary:{column}", not bool(values.any()), f"true_count={int(values.sum())}")

        lifecycle = self.read_csv("pre_reference/full_stream_hypothesis_lifecycle_with_anchor_state_pre_reference.csv")
        for column in ("closure_condition_satisfied", "person_identity_truth_claimed", "final_localization_claimed"):
            values = lifecycle[column].map(parse_bool)
            self.check(f"lifecycle_boundary:{column}", not bool(values.any()), f"true_count={int(values.sum())}")
        self.check("no_true_closed_state", not lifecycle["lifecycle_state"].astype(str).eq("CLOSED").any(), "CLOSED must remain absent")
        unavailable = lifecycle["sar_p0_interface_state"].astype(str).eq("SAR_P0_CONTINUITY_INTERFACE_UNAVAILABLE")
        unavailable_evidence = lifecycle.loc[unavailable, "uncertainty_state"].fillna("").astype(str)
        forbidden = unavailable_evidence.str.contains(r"RESPONSE_ABSENCE|P0_ABSENCE|CLOSED_BY|EXIT_BY", regex=True)
        self.check("p0_unavailable_not_absence_or_exit", not bool(forbidden.any()), f"forbidden_rows={int(forbidden.sum())}")

        headers_with_offline_identity: list[str] = []
        for path in sorted(self.pre.glob("*.csv")):
            with path.open("r", encoding="utf-8-sig", newline="") as stream:
                header = next(csv.reader(stream), [])
            if "optical_person_id" in header or "manual_sar_reference" in header:
                headers_with_offline_identity.append(path.name)
        self.check("pre_reference_no_offline_identity_columns", not headers_with_offline_identity, f"files={headers_with_offline_identity}")

        sources = self.read_csv("pre_reference/runtime_anchor_source_registry_pre_reference.csv")
        offline = sources[sources["anchor_source_class"].eq("OFFLINE_REFERENCE_ANCHOR")]
        self.check("offline_anchor_runtime_forbidden", len(offline) == 1 and not parse_bool(offline.iloc[0]["runtime_use_allowed"]), offline.to_dict(orient="records").__repr__())

    def validate_negative_time(self) -> None:
        audit = self.read_csv("pre_reference/negative_time_no_optical_admission_audit_pre_reference.csv")
        self.check("negative_audit_rows", len(audit) == 9, f"rows={len(audit)}")
        false_events = pd.to_numeric(audit["structural_sar_only_false_admission_event_count"], errors="raise")
        false_frames = pd.to_numeric(audit["structural_sar_only_false_admission_frame_count"], errors="raise")
        clutter = audit["sar_clutter_used_to_open_hypothesis"].map(parse_bool)
        self.check("negative_time_sar_only_false_admission_events_zero", int(false_events.sum()) == 0, f"sum={int(false_events.sum())}")
        self.check("negative_time_sar_only_false_admission_frames_zero", int(false_frames.sum()) == 0, f"sum={int(false_frames.sum())}")
        self.check("sar_clutter_never_opens_hypothesis", not bool(clutter.any()), f"true_count={int(clutter.sum())}")

    def validate_r1_corrections(self) -> None:
        visual = self.read_csv("pre_reference/r1_independent_visual_review_ledger_correction.csv")
        required_visual = {"computed_geometric_verdict", "independent_visual_review_verdict", "review_source", "relative_order_primitive_freeze_supported"}
        self.check("r1_visual_fields", required_visual.issubset(visual.columns), f"missing={sorted(required_visual - set(visual.columns))}")
        self.check("r1_visual_case_count", len(visual) == 10, f"rows={len(visual)}")
        direct = visual["review_source"].astype(str).str.contains("DIRECT_IMAGE_INSPECTION", regex=False)
        self.check("r1_visual_review_independent_source", bool(direct.all()), f"direct_fraction={float(direct.mean())}")
        freeze = visual["relative_order_primitive_freeze_supported"].map(parse_bool)
        self.check("relative_order_freeze_has_direct_support", bool(freeze.any()), f"supporting_cases={int(freeze.sum())}")

        for relative in (
            "post_reference_evaluation_only/r1_one_anchor_specific_likely_family_retention_correction.csv",
            "post_reference_evaluation_only/r1_two_anchor_specific_likely_family_retention_correction.csv",
        ):
            table = self.read_csv(relative)
            required = {"specific_likely_family_retained", "specific_likely_family_retention_detail", "corrected_semantics"}
            self.check(f"specific_likely_fields:{Path(relative).name}", required.issubset(table.columns), f"missing={sorted(required - set(table.columns))}")
            semantics = set(table["corrected_semantics"].dropna().astype(str))
            self.check(f"specific_likely_semantics:{Path(relative).name}", semantics == {"SPECIFIC_LIKELY_FAMILY_RETAINED_NOT_DOMAIN_NONEMPTY"}, f"semantics={semantics}")

        clusters = self.read_csv("pre_reference/r1_temporal_overlap_cluster_registry_correction.csv")
        assignments = self.read_csv("pre_reference/r1_temporal_overlap_cluster_assignment_correction.csv")
        self.check("cluster_registry_term", "temporal_overlap_cluster_id" in clusters.columns and "episode_id" not in clusters.columns, f"columns={list(clusters.columns)}")
        self.check("cluster_assignment_term", "temporal_overlap_cluster_id" in assignments.columns and "episode_id" not in assignments.columns, f"columns={list(assignments.columns)}")
        semantics = set(clusters["cluster_semantics"].astype(str))
        self.check("cluster_not_physical_episode", semantics == {"INTERVAL_OVERLAP_CONNECTED_COMPONENT_NOT_INDEPENDENT_PHYSICAL_EPISODE"}, f"semantics={semantics}")

    def validate_summary_report_figures(self) -> None:
        summary_path = self.output / "terg_r2_summary.json"
        report_path = self.output / "TERG_R2_SCIENTIFIC_REPORT.md"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        report = report_path.read_text(encoding="utf-8")
        self.check("summary_frames", int(summary["full_stream_frame_count"]) == 1485, json.dumps(summary, ensure_ascii=False))
        self.check("summary_parity", float(summary["frozen_q95_pixel_exact_fraction"]) == 1.0, str(summary["frozen_q95_pixel_exact_fraction"]))
        self.check("summary_p0_counts", summary["p0_available_pair_count_by_run"] == EXPECTED_P0_AVAILABLE, str(summary["p0_available_pair_count_by_run"]))
        self.check("summary_no_strong_anchor", int(summary["strong_auto_anchor_count"]) == 0, str(summary["strong_auto_anchor_count"]))
        self.check("summary_anchor_conclusion", summary["runtime_unary_anchor_conclusion"] == "NO_STRONG_AUTO_RUNTIME_UNARY_ANCHOR_ESTABLISHED", str(summary["runtime_unary_anchor_conclusion"]))
        self.check("summary_no_sar_only_admission", int(summary["sar_only_false_admission_event_count"]) == 0, str(summary["sar_only_false_admission_event_count"]))
        self.check("summary_no_closed", int(summary["true_closed_hypothesis_frame_count"]) == 0, str(summary["true_closed_hypothesis_frame_count"]))
        for phrase in (
            "RELATIVE_ANGULAR_ORDER_CONTRADICTION",
            "TEMPORAL_OVERLAP_CLUSTER",
            "no strong automatic runtime-legal unary anchor",
            "SAR_P0_CONTINUITY_INTERFACE_UNAVAILABLE",
            "## Direct answers",
        ):
            self.check(f"report_phrase:{phrase}", phrase in report, phrase)
        figures = {path.name for path in (self.output / "figures").glob("*.png")}
        self.check("figure_set", figures == EXPECTED_FIGURES, f"figures={sorted(figures)}")
        empty_or_unreadable = [name for name in figures if (self.output / "figures" / name).stat().st_size < 10_000]
        self.check("figures_nontrivial", not empty_or_unreadable, f"small={empty_or_unreadable}")

    def validate_manifest(self) -> None:
        manifest_path = self.output / "ARTIFACT_MANIFEST.csv"
        manifest = pd.read_csv(manifest_path)
        actual_files = {path for path in self.output.rglob("*") if path.is_file() and path != manifest_path}
        manifest_paths = {self.workspace / Path(str(value).replace("/", "\\")) for value in manifest["path"]}
        self.check("manifest_file_set", manifest_paths == actual_files, f"manifest={len(manifest_paths)} actual={len(actual_files)}")
        bad: list[str] = []
        for row in manifest.itertuples(index=False):
            path = self.workspace / Path(str(row.path).replace("/", "\\"))
            if not path.is_file():
                bad.append(f"missing:{row.path}")
                continue
            if int(path.stat().st_size) != int(row.size_bytes):
                bad.append(f"size:{row.path}")
                continue
            if sha256(path) != str(row.sha256).upper():
                bad.append(f"sha256:{row.path}")
        self.check("manifest_sizes_and_hashes", not bad, f"bad={bad[:5]}")

    def run(self) -> dict[str, Any]:
        self.check("workspace_exists", self.workspace.is_dir(), str(self.workspace))
        self.check("output_exists", self.output.is_dir(), str(self.output))
        self.validate_registry()
        self.validate_masks_and_parity()
        self.validate_p0_and_modes()
        self.validate_pre_reference_boundaries()
        self.validate_negative_time()
        self.validate_r1_corrections()
        self.validate_summary_report_figures()
        self.validate_manifest()
        return {
            "schema": "TERG_R2_INDEPENDENT_VALIDATION_V1",
            "status": "PASS",
            "check_count": len(self.checks),
            "checks": self.checks,
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, default=Path(__file__).resolve().parents[2])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = Validator(args.workspace).run()
    except Exception as error:
        print(json.dumps({"schema": "TERG_R2_INDEPENDENT_VALIDATION_V1", "status": "FAIL", "error": str(error)}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
