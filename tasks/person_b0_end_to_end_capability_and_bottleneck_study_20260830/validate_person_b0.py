#!/usr/bin/env python3
"""Independent integrity and semantic-boundary validator for PERSON-B0."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import zipfile
from pathlib import Path

import pandas as pd


SCRIPT = Path(__file__).resolve()
TASK = SCRIPT.parent
WORKSPACE = TASK.parents[1]
OUTPUT = WORKSPACE / "output" / "person_b0_end_to_end_capability_and_bottleneck_study_20260830"
PRE = OUTPUT / "pre_reference"
POST = OUTPUT / "post_reference_oracle_diagnostic_only"
PACK = WORKSPACE / "review_packs" / "PERSON_B0_DEEP_REVIEW_PACK_20260830"
ZIP = PACK.with_suffix(".zip")
RUNS = {"R01ZF", "R02ZF", "R03ZF"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-pack", action="store_true")
    args = parser.parse_args()
    checks: list[dict[str, object]] = []

    def check(name: str, passed: bool, detail: str) -> None:
        checks.append({"check": name, "passed": bool(passed), "detail": detail})

    required = [
        TASK / "README.md", TASK / "run_person_b0.py", OUTPUT / "REPORT.md", OUTPUT / "summary.json",
        PRE / "full_stream_p0_availability.parquet", PRE / "full_stream_p0_models.jsonl",
        PRE / "full_stream_p0_graded_p0_q95_edges.parquet", PRE / "threshold_and_authority_audit.csv",
        POST / "combined_oracle_ladder.csv", POST / "oracle_timing_status.csv",
    ]
    for path in required:
        check(f"required::{path.name}", path.exists() and path.stat().st_size > 0, str(path))

    p0 = pd.read_parquet(PRE / "full_stream_p0_availability.parquet")
    check("p0_development_runs_only", set(p0["run_id"].unique()) == RUNS, str(sorted(p0["run_id"].unique())))
    check("p0_all_adjacent_pairs", len(p0) == 3 * 494 and p0.groupby("run_id").size().eq(494).all(), str(p0.groupby("run_id").size().to_dict()))
    check("p0_explicit_states", set(p0["p0_state"].unique()) <= {"P0_AVAILABLE", "P0_UNRELIABLE_OR_AMBIGUOUS", "P0_UNAVAILABLE"}, str(sorted(p0["p0_state"].unique())))
    check("p0_no_manual_reference", not p0["manual_person_reference_used"].astype(bool).any(), "all false")
    check("p0_no_optical_identity", not p0["optical_identity_used"].astype(bool).any(), "all false")
    available = p0[p0["p0_state"] == "P0_AVAILABLE"]
    check("p0_available_requires_two_improvements", bool((available["m1_improves_median"] & available["m1_improves_p90"] & available["comparable"]).all()), f"available={len(available)}")

    edges = pd.read_parquet(PRE / "full_stream_p0_graded_p0_q95_edges.parquet")
    check("graded_edges_positive_upper_only", bool((edges["soft_intersection_px"] > 0).all() and edges["upper_possible"].all()), f"edges={len(edges)}")
    check("optional_is_dominance_union", bool((edges["optional_compatible"] == (edges["source_dominant"] | edges["destination_dominant"])).all()), "exact")
    check("lower_is_mutual_dominance", bool((edges["lower_mutual_dominant"] == (edges["source_dominant"] & edges["destination_dominant"])).all()), "exact")
    check("no_reference_in_graded_edges", not edges["reference_used"].astype(bool).any(), "all false")

    timing = pd.read_csv(POST / "oracle_timing_status.csv", encoding="utf-8-sig")
    check("oracle_timing_unavailable", timing.iloc[0]["status"] == "ORACLE_TIMING_UNAVAILABLE" and not bool(timing.iloc[0]["invented_timing_truth"]), timing.to_json(orient="records"))
    threshold = pd.read_csv(PRE / "threshold_and_authority_audit.csv", encoding="utf-8-sig")
    check("timing_named_context", bool(threshold["parameter"].str.contains("context", case=False).any()) and not bool(threshold["parameter"].str.contains("timing uncertainty", case=False).any()), "context terminology present")
    check("one_pixel_not_topology_authority", bool(threshold[threshold["parameter"] == "R2 P0 continuation"]["claim_use"].eq("not topology authority").all()), "audited")

    ladder = pd.read_csv(POST / "combined_oracle_ladder.csv", encoding="utf-8-sig")
    required_stages = {"CURRENT_RUNTIME", "FULL_STREAM_P0", "ORACLE_OPTICAL_IDENTITY", "FULL_P0_PLUS_ONE_CORRECT_ANCHOR"}
    check("required_ladder_stages", required_stages <= set(ladder["ladder_stage"]), str(sorted(set(ladder["ladder_stage"]))))
    range_rows = pd.read_csv(POST / "full_stream_p0_coarse_range_oracle_sweep.csv", encoding="utf-8-sig")
    check("range_levels_complete", set(range_rows["range_tolerance_m"].unique()) == {0.05, 0.5, 1.0, 2.0, 3.0}, str(sorted(range_rows["range_tolerance_m"].unique())))
    check("range_reference_retained", bool(range_rows["reference_range_retained"].all()), f"fraction={range_rows['reference_range_retained'].mean():.6f}")
    anchor = pd.read_csv(POST / "full_p0_one_correct_unary_anchor_effect.csv", encoding="utf-8-sig")
    check("anchor_oracle_only", bool(anchor["oracle_diagnostic_only"].all()), f"rows={len(anchor)}")

    report = (OUTPUT / "REPORT.md").read_text(encoding="utf-8")
    check("report_direct_conclusion", "COARSE_RANGE_IS_DOMINANT_MISSING_OBSERVABLE" in report, "present")
    check("report_nonclaims", all(token in report for token in ["ORACLE_TIMING_UNAVAILABLE", "final center", "final box", "physical motion"]), "required boundaries present")
    figures = sorted((OUTPUT / "figures").glob("*.png"))
    check("panels_A_to_H", all(any(path.name.startswith(f"panel_{letter}_") for path in figures) for letter in "ABCDEFGH"), str([path.name for path in figures]))

    if args.require_pack:
        check("pack_directory", PACK.exists(), str(PACK))
        check("pack_zip", ZIP.exists() and ZIP.stat().st_size > 0, str(ZIP))
        manifest_path = PACK / "PACK_MANIFEST.csv"
        manifest = pd.read_csv(manifest_path, encoding="utf-8-sig")
        required_columns = {"relative_path", "bytes", "sha256", "source_original_path", "data_role", "runtime_or_oracle_scope"}
        check("manifest_schema", required_columns <= set(manifest.columns), str(manifest.columns.tolist()))
        mismatches = []
        for row in manifest.itertuples(index=False):
            path = PACK / row.relative_path
            if not path.exists() or int(path.stat().st_size) != int(row.bytes) or sha256_file(path) != str(row.sha256):
                mismatches.append(str(row.relative_path))
        check("manifest_hashes", not mismatches, str(mismatches[:10]))
        summary = json.loads((PACK / "PACK_SUMMARY.json").read_text(encoding="utf-8"))
        check("raw_sar_count", int(summary["raw_sar_image_count"]) == len(list((PACK / "raw_sar").rglob("*.jpg"))), str(summary["raw_sar_image_count"]))
        check("raw_optical_count", int(summary["raw_optical_image_count"]) == len(list((PACK / "raw_optical").rglob("*.jpg"))), str(summary["raw_optical_image_count"]))
        check("q95_count", int(summary["q95_mask_count"]) == len(list((PACK / "q95_masks").rglob("*.npz"))), str(summary["q95_mask_count"]))
        with zipfile.ZipFile(ZIP, "r") as archive:
            bad = archive.testzip()
            names = archive.namelist()
        check("zip_integrity", bad is None, str(bad))
        check("zip_contains_pack", any(name.endswith("README_FOR_GPT_DEEP_REVIEW.md") for name in names), f"entries={len(names)}")

    failures = [row for row in checks if not row["passed"]]
    result = {"validator": "PERSON_B0_INDEPENDENT_VALIDATOR_V1", "status": "PASS" if not failures else "FAIL", "passed": len(checks) - len(failures), "total": len(checks), "failures": failures, "checks": checks}
    path = OUTPUT / "validation_results.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("validator", "status", "passed", "total", "failures")}, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
