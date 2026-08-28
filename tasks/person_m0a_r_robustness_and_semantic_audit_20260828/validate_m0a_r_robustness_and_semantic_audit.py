#!/usr/bin/env python3
"""Independent validator for materialized PERSON M0A-R audit outputs."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from PIL import Image


SCRIPT_PATH = Path(__file__).resolve()
TASK_DIR = SCRIPT_PATH.parent
WORKSPACE = TASK_DIR.parents[1]
STUDY_OUTPUT = WORKSPACE / "output" / "person_physics_guided_image_domain_study_20260824"
M0A_ROOT = STUDY_OUTPUT / "m0a_r02_lag1_q95_region_support_transport_pilot"
OUTPUT_DIR = STUDY_OUTPUT / "m0a_r_robustness_and_semantic_audit"
FREEZE_PATH = OUTPUT_DIR / "protocol_freeze.json"
PROTOCOL_PATH = OUTPUT_DIR / "M0A_R_ROBUSTNESS_AND_SEMANTIC_AUDIT_PROTOCOL_FROZEN_BEFORE_RUN.md"
VALIDATION_PATH = OUTPUT_DIR / "independent_validation.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def bool_series(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series.dtype):
        return series.astype(bool)
    parsed = series.astype("string").str.strip().str.lower().map(
        {"true": True, "false": False, "1": True, "0": False}
    )
    if parsed.isna().any():
        raise ValueError(series[parsed.isna()].unique().tolist())
    return parsed.astype(bool)


def check(condition: bool, name: str, details: Any, checks: list[dict[str, Any]]) -> None:
    checks.append({"name": name, "status": "PASS" if condition else "FAIL", "details": details})


def main() -> None:
    checks: list[dict[str, Any]] = []
    required_names = [
        "support_size_strata.csv",
        "support_size_sensitivity.csv",
        "supported_edge_audit.csv",
        "cluster_aware_summary.csv",
        "leave_one_frame_pair_out.csv",
        "matched_alternative_cluster_audit.csv",
        "background_high_response_controls.csv",
        "supported_matched_background_controls.csv",
        "p0_gain_family_comparison.csv",
        "p0_gain_family_by_frame_pair.csv",
        "q95_relative_percentile_semantic_audit.csv",
        "shared_unresolved_positive_audit.csv",
        "correlated_descriptor_audit.csv",
        "real_case_registry.csv",
        "audit_summary.json",
        "execution_ledger.json",
        "output_manifest.json",
        "M0A_R_ROBUSTNESS_AND_SEMANTIC_AUDIT_REPORT.md",
    ]
    required = [OUTPUT_DIR / name for name in required_names]
    check(all(path.is_file() for path in required), "required_audit_outputs", [path.name for path in required if not path.is_file()], checks)

    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    check(freeze.get("status") == "FROZEN_BEFORE_RUN", "protocol_freeze_status", freeze.get("status"), checks)
    check(sha256_file(PROTOCOL_PATH) == freeze["protocol_sha256"], "protocol_hash", sha256_file(PROTOCOL_PATH), checks)
    input_hashes_ok = all(
        sha256_file(WORKSPACE / item["path"]) == item["sha256"] for item in freeze["input_hashes"]
    )
    check(input_hashes_ok, "frozen_m0a_inputs_unchanged", None, checks)

    nodes = pd.read_csv(M0A_ROOT / "pre_reference_region_nodes.csv")
    source = nodes[nodes["frame_index"].between(472, 493)]
    quantiles = source["q95_pixel_count"].quantile([0.25, 0.50, 0.75], interpolation="linear")
    expected_cuts = [int(math.floor(float(quantiles.loc[q]))) for q in (0.25, 0.50, 0.75)]
    strata = pd.read_csv(OUTPUT_DIR / "support_size_strata.csv")
    observed_cuts = [
        int(strata["q25_floor_px"].iloc[0]),
        int(strata["q50_floor_px"].iloc[0]),
        int(strata["q75_floor_px"].iloc[0]),
    ]
    check(expected_cuts == observed_cuts == [70, 209, 587], "gt_blind_strata_cutpoints", {"expected": expected_cuts, "observed": observed_cuts}, checks)
    check(int(strata["source_region_count"].sum()) == 1064, "all_source_regions_accounted", int(strata["source_region_count"].sum()), checks)
    check(bool(strata["contains_1px"].map(bool).any()) and bool(strata["contains_6px"].map(bool).any()) and bool(strata["contains_19px"].map(bool).any()), "tiny_cases_preserved_in_strata", None, checks)

    supported = pd.read_csv(OUTPUT_DIR / "supported_edge_audit.csv", low_memory=False)
    check(len(supported) == 6 and supported[["from_frame", "to_frame"]].drop_duplicates().shape[0] == 3, "effective_supported_clusters", {"edges": len(supported), "pairs": supported[["from_frame", "to_frame"]].drop_duplicates().shape[0]}, checks)
    check(bool(supported["support_size_stratum"].eq("LARGE_Q4").all()), "supported_not_tiny_driven", supported["support_size_stratum"].value_counts().to_dict(), checks)
    check(bool(bool_series(supported["shared_or_unresolved"]).all()) and bool((supported["supported_target_count"] == 2).all()), "all_supported_shared_two_targets", None, checks)

    controls = pd.read_csv(OUTPUT_DIR / "background_high_response_controls.csv", low_memory=False)
    check(len(controls) == 1064 and controls["source_region_id"].nunique() == 1064, "one_structural_control_per_source", {"rows": len(controls), "sources": controls["source_region_id"].nunique()}, checks)
    check(bool(controls["selection_semantics"].eq("ONE_EDGE_PER_SOURCE_MIN_PRE_REFERENCE_STRUCTURAL_CHANGE_COST_NO_TRANSPORT_METRIC").all()), "control_selection_semantics", None, checks)
    matched_controls = pd.read_csv(OUTPUT_DIR / "supported_matched_background_controls.csv", low_memory=False)
    check(len(matched_controls) == 30 and matched_controls["supported_base_edge_id"].nunique() == 6, "five_background_controls_per_supported_edge", {"rows": len(matched_controls), "supported": matched_controls["supported_base_edge_id"].nunique()}, checks)
    check(bool(bool_series(matched_controls["reference_free_endpoint_pair"]).all()), "matched_controls_reference_free", None, checks)

    loo = pd.read_csv(OUTPUT_DIR / "leave_one_frame_pair_out.csv")
    check(len(loo) == 4 and int(loo["analysis"].eq("LEAVE_ONE_FRAME_PAIR_OUT").sum()) == 3, "leave_one_pair_out_complete", loo["dropped_frame_pair"].tolist(), checks)
    check(bool((loo["p0_retention_median"] > 0.5).all()) and bool((loo["delta_p0_median"] > 0).all()), "loo_transport_direction_stable", loo[["dropped_frame_pair", "p0_retention_median", "delta_p0_median"]].to_dict("records"), checks)

    family = pd.read_csv(OUTPUT_DIR / "p0_gain_family_comparison.csv")
    expected_families = {
        "REFERENCE_SUPPORTED_EDGES",
        "REFERENCE_UNSUPPORTED_MATCHED_ALTERNATIVES",
        "REFERENCE_FREE_STRUCTURAL_HIGH_RESPONSE_CONTROLS",
        "SUPPORTED_MATCHED_REFERENCE_FREE_CONTROLS",
    }
    check(set(family["evidence_family"]) == expected_families, "p0_gain_evidence_families", sorted(family["evidence_family"]), checks)

    shared = pd.read_csv(OUTPUT_DIR / "shared_unresolved_positive_audit.csv")
    check(len(shared) == 6 and bool(shared["positive_semantics"].eq("REFERENCE_SUPPORTED_DYNAMIC_EXPLANATION").all()), "positive_semantics_not_upgraded", None, checks)
    check(not bool(bool_series(shared["person_exclusive_positive"]).any()), "no_person_exclusive_positive", None, checks)

    dependency = pd.read_csv(OUTPUT_DIR / "correlated_descriptor_audit.csv")
    exact = dependency[dependency["relationship"].isin(["SAME_NUMERATOR_DIFFERENT_DENOMINATOR", "SAME_INTERSECTION_IN_NUMERATOR_AND_UNION", "NESTED_RELATIVE_PERCENTILE_LAYERS"])]
    check(len(exact) == 3 and not bool(bool_series(exact["independent_evidence_claim_allowed"]).any()), "correlated_descriptor_semantics", exact[["descriptor_a", "descriptor_b"]].to_dict("records"), checks)

    cases = pd.read_csv(OUTPUT_DIR / "real_case_registry.csv")
    figures = sorted((OUTPUT_DIR / "figures").glob("*.png"))
    readable = True
    for path in figures:
        try:
            with Image.open(path) as image:
                image.verify()
        except Exception:
            readable = False
            break
    check(len(cases) == 10 and cases["case_type"].nunique() == 10, "ten_deterministic_real_cases", cases["case_type"].tolist(), checks)
    check(len(figures) == 10 and readable, "ten_real_case_figures_readable", {"count": len(figures)}, checks)
    exact_sizes = set(cases["source_support_total"].astype(int))
    check({1, 6, 19}.issubset(exact_sizes), "one_six_nineteen_pixel_cases_rendered", sorted(exact_sizes), checks)

    summary = json.loads((OUTPUT_DIR / "audit_summary.json").read_text(encoding="utf-8"))
    check(summary["final_audit_state"] == "M0A_R_TRANSPORT_VALID_BUT_PERSON_SPECIFICITY_NOT_ESTABLISHED", "evidence_faithful_state", summary["final_audit_state"], checks)
    check(not summary["audit_changes_frozen_m0a_state"] and not summary["m0b_executed"], "m0a_unchanged_m0b_not_executed", None, checks)
    check(not any(summary["prohibited_claims"].values()), "prohibited_claims_false", summary["prohibited_claims"], checks)

    report = (OUTPUT_DIR / "M0A_R_ROBUSTNESS_AND_SEMANTIC_AUDIT_REPORT.md").read_text(encoding="utf-8")
    required_phrases = [
        "insufficient independent frame-pair clusters",
        "REFERENCE_SUPPORTED_DYNAMIC_EXPLANATION",
        "M0A_R_TRANSPORT_VALID_BUT_PERSON_SPECIFICITY_NOT_ESTABLISHED",
        "M0B",
        "do not construct a tracker",
    ]
    check(all(phrase in report for phrase in required_phrases), "report_semantic_boundaries", [phrase for phrase in required_phrases if phrase not in report], checks)

    manifest = json.loads((OUTPUT_DIR / "output_manifest.json").read_text(encoding="utf-8"))
    manifest_ok = all(sha256_file(WORKSPACE / item["path"]) == item["sha256"] for item in manifest["outputs"])
    check(manifest_ok and not manifest["m0a_inputs_modified"] and not manifest["m0b_executed"], "manifest_hashes_and_boundaries", None, checks)

    status = "PASS" if all(item["status"] == "PASS" for item in checks) else "FAIL"
    result = {
        "schema": "PERSON_M0A_R_INDEPENDENT_VALIDATION_V1",
        "status": status,
        "checks_passed": sum(item["status"] == "PASS" for item in checks),
        "checks_total": len(checks),
        "checks": checks,
    }
    VALIDATION_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    if status != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
