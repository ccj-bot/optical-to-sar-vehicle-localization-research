from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pandas as pd


SCRIPT = Path(__file__).resolve()
TASK = SCRIPT.parent
WORKSPACE = TASK.parents[1]
OUTPUT = WORKSPACE / "output" / "person_terg_r0_set_valued_explanation_constraint_propagation_20260829"
PRE = OUTPUT / "pre_reference"
POST = OUTPUT / "post_reference"
V1_ROOT = WORKSPACE / "output" / "person_terg_d0r_set_valued_graph_representation_repair_20260829"
EXPECTED_ROUTE = "TERG_R0_CONSTRAINT_PROPAGATION_MECHANISM_ESTABLISHED"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str, checks: list[dict[str, Any]]) -> None:
    checks.append({"check": message, "passed": bool(condition)})
    if not condition:
        raise AssertionError(message)


def verify_pre_reference_manifest(checks: list[dict[str, Any]]) -> None:
    manifest = pd.read_csv(PRE / "pre_reference_hash_manifest.csv")
    for row in manifest.itertuples(index=False):
        path = OUTPUT / str(row.relative_path)
        require(path.is_file(), f"pre-reference file exists: {row.relative_path}", checks)
        require(path.stat().st_size == int(row.bytes), f"pre-reference byte size matches: {row.relative_path}", checks)
        require(sha256_file(path) == str(row.sha256), f"pre-reference sha256 matches: {row.relative_path}", checks)


def verify_frozen_v1(checks: list[dict[str, Any]]) -> None:
    frozen = load_json(PRE / "frozen_terg_v1_input_hashes.json")
    current = {
        str(path.relative_to(WORKSPACE)).replace("\\", "/"): sha256_file(path)
        for path in sorted(V1_ROOT.rglob("*"))
        if path.is_file()
    }
    require(current == frozen, "frozen TERG-v1 files are byte-identical", checks)


def reconstruct_exact_worlds(
    family_status: pd.DataFrame,
    pair_registry: pd.DataFrame,
    burden: pd.DataFrame,
    checks: list[dict[str, Any]],
) -> None:
    domain_lookup = {
        (str(segment), str(track)): sorted(map(str, values))
        for (segment, track), values in family_status.groupby(["segment_id", "track_id"])["family_id"]
    }
    pairing_lookup = {
        (str(segment), str(track_a), str(track_b), str(family_a), str(family_b)): str(status)
        for segment, track_a, track_b, family_a, family_b, status in pair_registry[
            ["segment_id", "track_a", "track_b", "family_a", "family_b", "pairing_status"]
        ].itertuples(index=False, name=None)
    }
    status_lookup = family_status.set_index("family_id")
    for segment in burden.itertuples(index=False):
        tracks = [value for value in str(segment.track_ids).split(";") if value]
        domains = [domain_lookup[(str(segment.segment_id), track)] for track in tracks]
        shape = tuple(len(domain) for domain in domains)
        require(int(math.prod(shape)) == int(segment.N_temporal_joint_worlds), f"baseline product exact: {segment.segment_id}", checks)
        mask = np.ones(shape, dtype=bool)
        for axis_a, track_a in enumerate(tracks):
            for axis_b in range(axis_a + 1, len(tracks)):
                track_b = tracks[axis_b]
                matrix = np.ones((len(domains[axis_a]), len(domains[axis_b])), dtype=bool)
                seen = False
                for index_a, family_a in enumerate(domains[axis_a]):
                    for index_b, family_b in enumerate(domains[axis_b]):
                        key = (str(segment.segment_id), track_a, track_b, family_a, family_b)
                        reverse = (str(segment.segment_id), track_b, track_a, family_b, family_a)
                        if key in pairing_lookup:
                            status = pairing_lookup[key]
                            seen = True
                        elif reverse in pairing_lookup:
                            status = pairing_lookup[reverse]
                            seen = True
                        else:
                            continue
                        matrix[index_a, index_b] = status != "LOGICALLY_EXCLUDED_PAIRING"
                if not seen:
                    continue
                index_a_shape = [1] * len(tracks)
                index_b_shape = [1] * len(tracks)
                index_a_shape[axis_a] = len(domains[axis_a])
                index_b_shape[axis_b] = len(domains[axis_b])
                idx_a = np.arange(len(domains[axis_a])).reshape(index_a_shape)
                idx_b = np.arange(len(domains[axis_b])).reshape(index_b_shape)
                mask &= matrix[idx_a, idx_b]
        possible = int(mask.sum(dtype=np.int64))
        require(possible == int(segment.N_possible_joint_worlds), f"exact possible worlds match: {segment.segment_id}", checks)
        for axis, domain in enumerate(domains):
            other_axes = tuple(index for index in range(len(tracks)) if index != axis)
            marginals = mask.sum(axis=other_axes, dtype=np.int64) if other_axes else mask.astype(np.int64)
            for family_id, marginal in zip(domain, np.asarray(marginals).reshape(-1)):
                reported = int(status_lookup.loc[family_id, "possible_joint_worlds_containing_family"])
                require(int(marginal) == reported, f"exact family marginal matches: {family_id}", checks)


def main() -> None:
    checks: list[dict[str, Any]] = []
    required = [
        PRE / "reasoning_specification.json",
        PRE / "family_domain_status_pre_reference.parquet",
        PRE / "pair_constraint_registry_pre_reference.parquet",
        PRE / "segment_joint_world_burden_pre_reference.parquet",
        PRE / "evidence_family_contribution_pre_reference.parquet",
        PRE / "order_independence_audit_pre_reference.parquet",
        PRE / "synergy_audit_pre_reference.parquet",
        PRE / "observational_equivalence_audit_pre_reference.parquet",
        PRE / "pre_reference_freeze_summary.json",
        PRE / "pre_reference_hash_manifest.csv",
        POST / "family_grounding_retention_post_reference.parquet",
        POST / "segment_likely_joint_world_retention_post_reference.parquet",
        POST / "evaluation_summary.json",
        POST / "real_image_review_registry_post_reference.parquet",
        OUTPUT / "TERG_R0_SCIENTIFIC_MECHANISM_REPORT.md",
        OUTPUT / "TERG_R0_FROZEN_REASONING_SPECIFICATION.md",
        OUTPUT / "TERG_R0_ISSUE_FAILURE_ROOT_CAUSE_LEDGER.md",
        OUTPUT / "terg_r0_summary.json",
    ]
    for path in required:
        require(path.is_file() and path.stat().st_size > 0, f"required artifact exists: {path.name}", checks)
    verify_pre_reference_manifest(checks)
    verify_frozen_v1(checks)

    specification = load_json(PRE / "reasoning_specification.json")
    freeze = load_json(PRE / "pre_reference_freeze_summary.json")
    evaluation = load_json(POST / "evaluation_summary.json")
    summary = load_json(OUTPUT / "terg_r0_summary.json")
    family = pd.read_parquet(PRE / "family_domain_status_pre_reference.parquet")
    pair = pd.read_parquet(PRE / "pair_constraint_registry_pre_reference.parquet")
    burden = pd.read_parquet(PRE / "segment_joint_world_burden_pre_reference.parquet")
    contribution = pd.read_parquet(PRE / "evidence_family_contribution_pre_reference.parquet")
    order_audit = pd.read_parquet(PRE / "order_independence_audit_pre_reference.parquet")
    synergy = pd.read_parquet(PRE / "synergy_audit_pre_reference.parquet")
    equivalence = pd.read_parquet(PRE / "observational_equivalence_audit_pre_reference.parquet")
    retention = pd.read_parquet(POST / "family_grounding_retention_post_reference.parquet")
    tuple_retention = pd.read_parquet(POST / "segment_likely_joint_world_retention_post_reference.parquet")
    visual = pd.read_parquet(POST / "real_image_review_registry_post_reference.parquet")

    require(specification["reasoning_formulation_count"] == 1, "exactly one principal formulation", checks)
    require(specification["real_bug_correction_count"] <= 1, "at most one real-bug correction", checks)
    for key in ["weighted_score_used", "arbitrary_threshold_used", "top_k_used", "assignment_used", "tracker_used", "manual_reference_used", "r04zf_accessed"]:
        require(specification[key] is False, f"forbidden mechanism disabled: {key}", checks)
    require(freeze["manual_reference_loaded_before_freeze"] is False, "pre-reference freeze precedes reference load", checks)
    require(freeze["r04zf_accessed"] is False, "R04ZF not accessed", checks)

    require(len(burden) == 38, "segment denominator is complete: 38", checks)
    require(len(family) == 3414, "family denominator is complete: 3414", checks)
    require(int(burden["N_temporal_joint_worlds"].sum()) == 3920966, "baseline joint-world total exact", checks)
    require(int(burden["N_possible_joint_worlds"].sum()) == 3506018, "possible joint-world total exact", checks)
    require(int(burden["N_excluded_joint_worlds"].sum()) == 414948, "excluded joint-world total exact", checks)
    require(int(burden["N_excluded_joint_worlds"].gt(0).sum()) == 15, "contracted segment count exact", checks)
    require(int(family["family_status"].eq("LOGICALLY_EXCLUDED").sum()) == 0, "no individual family falsely excluded", checks)
    require((family["possible_joint_worlds_containing_family"] > 0).all(), "every family has an exact supporting world", checks)
    reconstruct_exact_worlds(family, pair, burden, checks)

    require(len(order_audit) == math.factorial(8), "all eight-evidence permutations audited", checks)
    require(order_audit["order_independent"].all(), "factor intersection is order independent", checks)
    require(order_audit["final_possible_joint_world_count"].nunique() == 1, "all evidence orders give the same count", checks)
    require(int(order_audit["final_possible_joint_world_count"].iloc[0]) == 3506018, "order-independent count is exact", checks)
    active = contribution.set_index("evidence_family")["new_logically_excluded_joint_world_count"].to_dict()
    require(active["optical_raw_definite_order_alone"] == 0, "optical order alone excludes zero", checks)
    require(active["sar_family_pair_geometry_alone"] == 0, "SAR geometry alone excludes zero", checks)
    require(active["cross_modal_definite_order_intersection"] == 414948, "cross-modal intersection supplies all exclusions", checks)
    combined = synergy[synergy["condition"].eq("COMBINED_CROSS_MODAL_ORDER")]
    require(int(combined["excluded_joint_world_count"].sum()) == 414948, "synergy total exact", checks)
    require(int(equivalence["true_observational_equivalence_merge_allowed"].sum()) == 0, "no unjustified observational merge", checks)

    likely = retention[retention["component_grounding_state"].eq("LIKELY_SUPPORTED_EXPLORATORY")]
    require(len(likely) == 79, "likely-supported family denominator exact", checks)
    require(likely["retained_by_r0"].all(), "79/79 likely-supported families retained", checks)
    require(len(tuple_retention) == 31, "unique likely joint tuple denominator exact", checks)
    require(tuple_retention["r0_tuple_status"].eq("RETAINED").all(), "31/31 likely joint tuples retained", checks)
    require(evaluation["strict_branch_identity_evaluation"] == "STRICT_BRANCH_IDENTITY_EVALUATION_UNAVAILABLE", "strict identity unavailability explicit", checks)
    require(evaluation["route_decision"] == EXPECTED_ROUTE, "route decision exact", checks)
    require(evaluation["future_confirmation_requirement"] == "NEW_INDEPENDENT_CONFIRMATION_DATA_REQUIRED", "new independent data requirement explicit", checks)
    require(summary["frozen_terg_v1_unchanged"] is True, "summary records frozen V1 unchanged", checks)

    required_categories = {
        "STRONG_JOINT_WORLD_CONTRACTION",
        "FIVE_TRACK_COMPOUND_CONTRACTION",
        "PARTIAL_DIRECTION_AND_SHARED",
        "NO_CONTRACTION",
        "OPTIONAL_EDGE_DOMINATED_CONTINUITY",
        "DEFORMATION_SPLIT_MERGE_AMBIGUITY",
        "SHARED_AND_COMPETING_DIRECTION",
        "HUMAN_VISIBLE_BUT_GROUNDING_UNRESOLVED",
        "BOUNDARY_OR_CENSORED",
        "LIKELY_SUPPORTED_TUPLE_RETENTION",
        "LIKELY_SUPPORTED_TUPLE_MISTAKENLY_EXCLUDED_SEARCH",
    }
    require(required_categories.issubset(set(visual["case_category"])), "all required real-image review categories registered", checks)
    require(visual["inspection_state"].eq("CODEX_PERSONALLY_INSPECTED").all(), "all registered cases personally inspected", checks)
    for relative_path in visual["figure_path"].unique():
        path = WORKSPACE / str(relative_path)
        require(path.is_file() and path.stat().st_size > 0, f"visual artifact exists: {relative_path}", checks)
        image = cv2.imread(str(path), cv2.IMREAD_COLOR)
        require(image is not None and image.shape[0] >= 700 and image.shape[1] >= 1000, f"visual artifact decodes with review resolution: {relative_path}", checks)

    report = {
        "validator": "PERSON_TERG_R0_INDEPENDENT_VALIDATION_V1",
        "status": "PASS",
        "check_count": len(checks),
        "passed_count": sum(int(item["passed"]) for item in checks),
        "route_decision": EXPECTED_ROUTE,
        "baseline_joint_world_count": 3920966,
        "possible_joint_world_count": 3506018,
        "logically_excluded_joint_world_count": 414948,
        "family_level_logical_exclusion_count": 0,
        "likely_supported_family_retention": "79/79",
        "unique_likely_joint_tuple_retention": "31/31",
        "checks": checks,
    }
    (OUTPUT / "validation_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    manifest_rows = []
    for path in sorted(OUTPUT.rglob("*")):
        if (
            not path.is_file()
            or path.name == "ARTIFACT_MANIFEST.csv"
            or path.name == "01_strong_contraction_likely_tuple.png"
        ):
            continue
        manifest_rows.append(
            {
                "relative_path": str(path.relative_to(OUTPUT)).replace("\\", "/"),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    pd.DataFrame(manifest_rows).to_csv(OUTPUT / "ARTIFACT_MANIFEST.csv", index=False, encoding="utf-8-sig")
    print(json.dumps({key: report[key] for key in report if key != "checks"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
