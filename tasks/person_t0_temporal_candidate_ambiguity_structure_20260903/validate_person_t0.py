from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd


SCRIPT = Path(__file__).resolve()
TASK = SCRIPT.parent
WORKSPACE = TASK.parents[1]
OUTPUT = WORKSPACE / "output" / "person_t0_temporal_candidate_ambiguity_structure_20260903"
PRE = OUTPUT / "pre_reference"
POST = OUTPUT / "post_reference_diagnostic_only"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def validate_freeze() -> tuple[pd.DataFrame, str]:
    manifest_path = PRE / "pre_reference_freeze_manifest.csv"
    require(manifest_path.exists(), "missing pre-reference freeze manifest")
    manifest = pd.read_csv(manifest_path, encoding="utf-8-sig")
    require(manifest["relative_path"].is_unique, "freeze manifest paths are not unique")
    expected = set(manifest["relative_path"].astype(str))
    actual = {
        str(path.relative_to(PRE)).replace("\\", "/")
        for path in PRE.rglob("*")
        if path.is_file() and path.name != manifest_path.name
    }
    require(expected == actual, f"freeze tree mismatch missing={sorted(expected-actual)} extra={sorted(actual-expected)}")
    for row in manifest.itertuples(index=False):
        path = PRE / str(row.relative_path)
        require(path.stat().st_size == int(row.size_bytes), f"size mismatch {row.relative_path}")
        require(sha256_file(path) == str(row.sha256), f"hash mismatch {row.relative_path}")
    tree_hash = hashlib.sha256("".join(manifest.sort_values("relative_path")["sha256"]).encode("utf-8")).hexdigest()
    return manifest, tree_hash


def main() -> None:
    required = [
        "analysis_contract.json",
        "input_manifest.csv",
        "window_registry.parquet",
        "window_track_registry.parquet",
        "candidate_region_family_events.parquet",
        "candidate_frame_evolution.parquet",
        "candidate_survival_elimination_ledger.parquet",
        "limited_information_ablation_ledger.parquet",
        "set_valued_representation_overlap_ledger.parquet",
        "multi_target_relation_ablation_ledger.parquet",
        "remaining_ambiguity_taxonomy_pre_reference.csv",
        "pre_reference_freeze_summary.json",
    ]
    for relative in required:
        require((PRE / relative).exists(), f"missing {relative}")
    manifest, tree_hash = validate_freeze()

    contract = json.loads((PRE / "analysis_contract.json").read_text(encoding="utf-8"))
    summary = json.loads((PRE / "pre_reference_freeze_summary.json").read_text(encoding="utf-8"))
    inputs = pd.read_csv(PRE / "input_manifest.csv", encoding="utf-8-sig")
    windows = pd.read_parquet(PRE / "window_registry.parquet")
    tracks = pd.read_parquet(PRE / "window_track_registry.parquet")
    events = pd.read_parquet(PRE / "candidate_region_family_events.parquet")
    evolution = pd.read_parquet(PRE / "candidate_frame_evolution.parquet")
    ledger = pd.read_parquet(PRE / "candidate_survival_elimination_ledger.parquet")
    ablation = pd.read_parquet(PRE / "limited_information_ablation_ledger.parquet")
    representation = pd.read_parquet(PRE / "set_valued_representation_overlap_ledger.parquet")
    relation = pd.read_parquet(PRE / "multi_target_relation_ablation_ledger.parquet")
    taxonomy = pd.read_csv(PRE / "remaining_ambiguity_taxonomy_pre_reference.csv", encoding="utf-8-sig")

    require(contract["construction_phase"] == "PRE_REFERENCE_ONLY", "construction phase changed")
    require(summary["manual_reference_loaded"] is False, "summary says reference loaded")
    require(summary["r04_used"] is False, "summary says R04 used")
    require(len(windows) == 5 and windows["window_id"].is_unique, "expected five unique windows")
    require(set(windows["run_id"]) <= {"R01ZF", "R02ZF", "R03ZF"}, "unexpected run in windows")
    require(not windows["run_id"].astype(str).str.contains("R04", case=False).any(), "R04 window")
    require(not inputs["path"].astype(str).str.contains("R04", case=False).any(), "R04 input path")
    require(not events["run_id"].astype(str).str.contains("R04", case=False).any(), "R04 event")
    require(len(tracks) == 12, "expected 12 window-track rows")
    require(len(evolution) == int(summary["candidate_frame_state_count"]), "frame-state count mismatch")
    require(len(ledger) == int(summary["strict_family_window_track_count"]), "family-ledger count mismatch")
    require(events[["window_id", "track_id", "frame_index", "region_id"]].duplicated().sum() == 0, "candidate event duplicate")
    require(evolution[["window_id", "track_id", "frame_index"]].duplicated().sum() == 0, "frame evolution duplicate")
    require(ledger[["window_id", "track_id", "strict_family_id"]].duplicated().sum() == 0, "family ledger duplicate")
    require(events["person_identity_claimed"].sum() == 0 if "person_identity_claimed" in events.columns else True, "identity claim in events")
    require(ledger["person_identity_claimed"].sum() == 0, "identity claim in ledger")
    require(ledger["final_localization_claimed"].sum() == 0, "localization claim in ledger")
    allowed_statuses = {
        "SURVIVED_TO_WINDOW_END",
        "LEFT_AZIMUTH_CORRIDOR",
        "NO_STRICT_P0_CONTINUATION",
        "STRICT_CORE_BREAK_BUT_UPPER_OPTIONAL_CONTINUATION",
        "P0_INTERFACE_UNAVAILABLE_CANNOT_DECIDE",
    }
    require(set(ledger["primary_status"]) <= allowed_statuses, "unknown primary status")
    require(ledger["primary_status"].eq("SURVIVED_TO_WINDOW_END").any(), "no survivors")
    require(ledger["primary_status"].eq("P0_INTERFACE_UNAVAILABLE_CANNOT_DECIDE").any(), "missing unavailable-state evidence")
    require(ledger["secondary_statuses"].fillna("").str.contains("REPRESENTATION_FRAGMENTATION_OR_TOPOLOGY_AMBIGUITY").any(), "missing representation ambiguity")
    require(ledger["secondary_statuses"].fillna("").str.contains("MULTI_TARGET_IDENTITY_PERMUTATION_COMPATIBLE").any(), "missing multi-target ambiguity")
    require(ledger["secondary_statuses"].fillna("").str.contains("BACKGROUND_COMPATIBLE_PERSISTENCE").any(), "missing matched-null compatibility")
    require((evolution["count_comparison_semantics"] == "NON_NESTED_REPRESENTATION_VIEWS_NOT_MONOTONIC_TRACKER_ABLATION").all(), "count semantics drift")
    require(ablation["comparison_warning"].str.contains("non-nested", case=False).all(), "ablation warning missing")
    require(len(representation) > 0, "empty set-valued representation ledger")
    require(len(relation) > 0, "empty relation ledger")
    require(taxonomy["ambiguity_mode"].nunique() >= 8, "taxonomy incomplete")
    figures = sorted((PRE / "figures").glob("*.png"))
    require(len(figures) == 15, f"expected 15 figures, got {len(figures)}")
    require(all(path.stat().st_size > 20_000 for path in figures), "one or more figures too small")

    post_required = [
        "post_reference_phase_state.json",
        "post_reference_summary.json",
        "reference_frame_diagnostic.parquet",
        "reference_family_diagnostic.parquet",
        "reference_window_track_summary.parquet",
        "reference_state_summary.csv",
    ]
    for relative in post_required:
        require((POST / relative).exists(), f"missing post-reference artifact {relative}")
    require((OUTPUT / "REPORT.md").exists(), "missing final report")
    require((OUTPUT / "VISUAL_REVIEW.md").exists(), "missing visual review")
    require((OUTPUT / "ARTIFACT_MANIFEST.csv").exists(), "missing artifact manifest")

    post_state = json.loads((POST / "post_reference_phase_state.json").read_text(encoding="utf-8"))
    post_summary = json.loads((POST / "post_reference_summary.json").read_text(encoding="utf-8"))
    ref_frame = pd.read_parquet(POST / "reference_frame_diagnostic.parquet")
    ref_family = pd.read_parquet(POST / "reference_family_diagnostic.parquet")
    ref_track = pd.read_parquet(POST / "reference_window_track_summary.parquet")
    require(post_state["status"] == "REFERENCE_LOADED_ONLY_AFTER_VERIFIED_PRE_REFERENCE_FREEZE", "post phase state drift")
    require(post_state["construction_changed"] is False, "reference changed construction")
    require(post_state["pre_reference_verification"]["tree_sha256"] == tree_hash, "post phase used a different pre tree")
    require(post_summary["pre_reference_tree_sha256"] == tree_hash, "post summary pre hash mismatch")
    require(len(ref_frame) == int(post_summary["reference_sample_count"]), "reference sample count mismatch")
    require(len(ref_track) == 12, "expected 12 post window-track summaries")
    require(ref_frame["construction_changed_by_reference"].sum() == 0, "reference changed a frozen candidate row")
    require(ref_frame["reference_loaded_after_frozen_construction"].all(), "reference phase flag missing")
    require(not ref_frame["run_id"].astype(str).str.contains("R04", case=False).any(), "R04 post row")
    require(ref_family["no_reference_overlap_is_false_candidate_claimed"].sum() == 0, "sparse no-overlap was called false")
    require(int(ref_frame["track_shell_available"].sum()) == int(post_summary["admitted_reference_sample_count"]), "admitted denominator mismatch")
    require(int(ref_frame["post_reference_state"].eq("REFERENCE_IN_CANDIDATE_SET").sum()) == int(post_summary["reference_in_candidate_count"]), "retention numerator mismatch")
    require(int(ref_frame["post_reference_state"].eq("REFERENCE_NOT_IN_Q95_SUPPORT").sum()) == int(post_summary["reference_not_in_q95_count"]), "Q95 miss mismatch")
    require(int(ref_frame["post_reference_state"].eq("TRACK_NOT_YET_ADMITTED_IN_WINDOW").sum()) == int(post_summary["track_not_yet_admitted_count"]), "admission count mismatch")
    require(int(ref_family["primary_status"].eq("SURVIVED_TO_WINDOW_END").sum()) == int(post_summary["survivor_family_window_track_count"]), "post survivor count mismatch")
    post_figures = sorted((POST / "figures").glob("*.png"))
    require(len(post_figures) == 5, f"expected 5 post figures, got {len(post_figures)}")
    require(all(path.stat().st_size > 20_000 for path in post_figures), "one or more post figures too small")
    report_text = (OUTPUT / "REPORT.md").read_text(encoding="utf-8")
    require("CASE_C_PLUS_CASE_D" not in report_text, "internal conclusion label leaked into prose")
    require("情况 C + 情况 D" in report_text, "final scientific conclusion missing")

    result = {
        "status": "PASS",
        "scope": "artifact integrity, phase separation, schema, status completeness, R04 exclusion from outputs, and figure presence only",
        "non_claim": "validator PASS is not PERSON confirmation, reference retention, physical motion recovery, or final localization",
        "pre_reference_file_count": len(manifest),
        "pre_reference_tree_sha256": tree_hash,
        "window_count": len(windows),
        "window_track_count": len(tracks),
        "candidate_event_count": len(events),
        "candidate_family_ledger_count": len(ledger),
        "figure_count": len(figures),
        "post_reference_figure_count": len(post_figures),
        "reference_sample_count": len(ref_frame),
        "admitted_reference_sample_count": int(post_summary["admitted_reference_sample_count"]),
        "reference_in_candidate_count": int(post_summary["reference_in_candidate_count"]),
        "reference_not_in_q95_count": int(post_summary["reference_not_in_q95_count"]),
        "track_not_yet_admitted_count": int(post_summary["track_not_yet_admitted_count"]),
        "primary_status_counts": {str(key): int(value) for key, value in ledger["primary_status"].value_counts().sort_index().items()},
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
