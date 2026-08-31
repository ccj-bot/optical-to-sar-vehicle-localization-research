from __future__ import annotations

import hashlib
import json
import math
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd


WORKSPACE = Path(r"D:\profile\research\workspace")
TASK = WORKSPACE / "tasks" / "person_r02_static_scene_skeleton_20260831"
OUT = WORKSPACE / "output" / "person_r02_static_scene_skeleton_20260831"
PRE = OUT / "pre_reference"
PACK = WORKSPACE / "review_packs" / "PERSON_R02_STATIC_SCENE_SKELETON_REVIEW_PACK_20260831.zip"
RESULTS = OUT / "VALIDATION_RESULTS.csv"
VALIDATION_SUMMARY = OUT / "VALIDATION_SUMMARY.json"
OUTPUT_MANIFEST = OUT / "OUTPUT_MANIFEST.csv"
EXPECTED_PACK_PATH = PACK.relative_to(WORKSPACE).as_posix()
EXCLUDED_PRE_REFERENCE_PREFIXES = ("static_landmark_", "visual_static_landmark_")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_false_series(series: pd.Series) -> bool:
    normalized = series.dropna().astype(str).str.strip().str.lower()
    return bool(normalized.isin({"false", "0", "0.0"}).all())


def longest_true_run(frame_indices: np.ndarray, mask: np.ndarray) -> tuple[int | None, int | None, int]:
    best: tuple[int | None, int | None, int] = (None, None, 0)
    start: int | None = None
    previous: int | None = None
    for frame, keep in zip(frame_indices.astype(int), mask.astype(bool)):
        if keep and (start is None or previous is None or frame != previous + 1):
            start = int(frame)
        if not keep and start is not None and previous is not None:
            length = int(previous) - start + 1
            if length > best[2]:
                best = (start, int(previous), length)
            start = None
        previous = int(frame)
    if start is not None and previous is not None:
        length = previous - start + 1
        if length > best[2]:
            best = (start, previous, length)
    return best


def build_output_manifest() -> None:
    rows: list[dict[str, object]] = []
    for path in sorted(item for item in OUT.rglob("*") if item.is_file()):
        if path.name == OUTPUT_MANIFEST.name:
            continue
        relative = path.relative_to(OUT)
        if "landmark_review" in relative.parts:
            continue
        if relative.parts and relative.parts[0] == "pre_reference" and relative.name.startswith(
            EXCLUDED_PRE_REFERENCE_PREFIXES
        ):
            continue
        rows.append(
            {
                "workspace_relative_path": path.relative_to(WORKSPACE).as_posix(),
                "artifact_scope": "output",
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "person_reference_used": False,
                "r04_accessed": False,
            }
        )
    rows.append(
        {
            "workspace_relative_path": EXPECTED_PACK_PATH,
            "artifact_scope": "uncommitted_review_pack",
            "bytes": PACK.stat().st_size,
            "sha256": sha256_file(PACK),
            "person_reference_used": False,
            "r04_accessed": False,
        }
    )
    pd.DataFrame(rows).to_csv(OUTPUT_MANIFEST, index=False, encoding="utf-8-sig")


def recursively_collect_flags(value: object, path: str = "") -> list[tuple[str, object]]:
    found: list[tuple[str, object]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            child = f"{path}.{key}" if path else key
            if key in {"person_reference_used", "manual_person_reference_used", "r04_accessed"}:
                found.append((child, item))
            found.extend(recursively_collect_flags(item, child))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(recursively_collect_flags(item, f"{path}[{index}]"))
    return found


def main() -> None:
    summary = json.loads((OUT / "SUMMARY.json").read_text(encoding="utf-8"))
    boundary = json.loads(
        (PRE / "static_boundary_analysis_summary_pre_reference.json").read_text(encoding="utf-8")
    )
    mapping = json.loads(
        (PRE / "tree_static_anchor_mapping_summary_pre_reference.json").read_text(encoding="utf-8")
    )
    sync = json.loads(
        (PRE / "synchronized_review_summary_pre_reference.json").read_text(encoding="utf-8")
    )
    optical = pd.read_csv(PRE / "r02zf_optical_frame_inventory_pre_reference.csv")
    sar = pd.read_csv(PRE / "r02zf_sar_frame_inventory_pre_reference.csv")
    pairing = pd.read_csv(PRE / "r02zf_timestamp_pairing_pre_reference.csv")
    boundary_frames = pd.read_csv(PRE / "static_boundary_frame_summary_pre_reference.csv")
    pair = pd.read_csv(PRE / "parallel_boundary_pair_frame_summary_pre_reference.csv")
    trees = pd.read_csv(PRE / "tree_visual_yellow_strap_tracks_pre_reference.csv")
    winners = pd.read_csv(PRE / "tree_sar_competition_winners_pre_reference.csv")
    competitors = pd.read_csv(PRE / "tree_sar_competitor_trajectories_pre_reference.csv")

    build_output_manifest()
    output_manifest = pd.read_csv(OUTPUT_MANIFEST)
    rows: list[dict[str, str]] = []

    def check(check_id: str, passed: bool, observed: object, expected: object, evidence: str) -> None:
        rows.append(
            {
                "check_id": check_id,
                "status": "PASS" if passed else "FAIL",
                "observed": json.dumps(observed, ensure_ascii=False, allow_nan=True),
                "expected": json.dumps(expected, ensure_ascii=False, allow_nan=True),
                "evidence": evidence,
            }
        )

    core = pairing[pairing.sar_frame_index.eq(200)]
    core_ok = len(core) == 1
    if core_ok:
        item = core.iloc[0]
        core_ok = (
            int(item.optical_frame_index) == 120
            and int(item.sar_timestamp_ms) == 6667
            and int(item.optical_timestamp_ms) == 6667
            and int(item.timestamp_residual_ms) == 0
        )
    check(
        "SYNC_CORE_F120_F200_EXACT",
        core_ok,
        core[["sar_frame_index", "optical_frame_index", "sar_timestamp_ms", "optical_timestamp_ms", "timestamp_residual_ms"]].to_dict("records"),
        [{"sar_frame_index": 200, "optical_frame_index": 120, "sar_timestamp_ms": 6667, "optical_timestamp_ms": 6667, "timestamp_residual_ms": 0}],
        "pre_reference/r02zf_timestamp_pairing_pre_reference.csv",
    )
    check(
        "SYNC_INVENTORY_AND_RESIDUAL",
        len(optical) == 298
        and len(sar) == 495
        and len(pairing) == 495
        and int(pairing.timestamp_residual_ms.abs().max()) == 23
        and pairing.sync_status.eq("NOMINAL_INDEX_FPS_ZERO_OFFSET_UNVERIFIED").all()
        and sync["sync_status"] == "NOMINAL_INDEX_FPS_ZERO_OFFSET_UNVERIFIED",
        {"optical": len(optical), "sar": len(sar), "pairs": len(pairing), "max_abs_residual_ms": int(pairing.timestamp_residual_ms.abs().max())},
        {"optical": 298, "sar": 495, "pairs": 495, "max_abs_residual_ms": 23},
        "inventories + synchronized_review_summary_pre_reference.json",
    )

    denominator_counts = boundary_frames.groupby("boundary_id").size().to_dict()
    expected_boundaries = {"STATIC_BOUNDARY_A", "STATIC_BOUNDARY_B", "STATIC_BOUNDARY_C"}
    check(
        "BOUNDARY_COMPLETE_495_BY_3_DENOMINATOR",
        len(boundary_frames) == 1485
        and set(denominator_counts) == expected_boundaries
        and all(int(value) == 495 for value in denominator_counts.values())
        and boundary_frames.sar_frame_index.nunique() == 495,
        {"rows": len(boundary_frames), "counts": denominator_counts, "unique_frames": int(boundary_frames.sar_frame_index.nunique())},
        {"rows": 1485, "counts_each": 495, "unique_frames": 495},
        "pre_reference/static_boundary_frame_summary_pre_reference.csv",
    )

    available = pair[pair.pair_available]
    median = float(available.delta_r_median_m.median())
    temporal_p90 = float(np.quantile(np.abs(available.delta_r_median_m - median), 0.90))
    theta_p90_median = float(available.delta_r_p90_absdev_m.median())
    check(
        "PAIR_FULL_SEQUENCE_METRICS",
        len(pair) == 495
        and int(pair.pair_available.sum()) == 122
        and math.isclose(median, 2.4999977350234985, abs_tol=1e-9)
        and math.isclose(temporal_p90, 0.24999964237213135, abs_tol=1e-9)
        and math.isclose(theta_p90_median, 0.5424995183944703, abs_tol=1e-9),
        {"available": int(pair.pair_available.sum()), "total": len(pair), "median_m": median, "temporal_p90_absdev_m": temporal_p90, "theta_p90_absdev_median_m": theta_p90_median},
        {"available": 122, "total": 495, "median_m": 2.4999977350234985, "temporal_p90_absdev_m": 0.24999964237213135, "theta_p90_absdev_median_m": 0.5424995183944703},
        "pre_reference/parallel_boundary_pair_frame_summary_pre_reference.csv",
    )

    eligible = (
        pair.pair_available
        & pair.delta_r_median_m.between(1.5, 3.0)
        & pair.delta_r_p90_absdev_m.le(0.55)
        & pair.ordering_a_before_b_fraction.ge(0.95)
    )
    stable_start, stable_end, stable_length = longest_true_run(
        pair.sar_frame_index.to_numpy(), eligible.to_numpy()
    )
    stable = pair[pair.sar_frame_index.between(stable_start, stable_end)]
    stable_median = float(stable.delta_r_median_m.median())
    stable_p90 = float(np.quantile(np.abs(stable.delta_r_median_m - stable_median), 0.90))
    check(
        "PAIR_STRICT_STABLE_SEGMENT_F330_F335",
        (stable_start, stable_end, stable_length) == (330, 335, 6)
        and math.isclose(stable_median, 2.512497305870056, abs_tol=1e-9)
        and math.isclose(stable_p90, 0.09999990463256836, abs_tol=1e-9),
        {"start": stable_start, "end": stable_end, "length": stable_length, "median_m": stable_median, "temporal_p90_absdev_m": stable_p90},
        {"start": 330, "end": 335, "length": 6, "median_m": 2.512497305870056, "temporal_p90_absdev_m": 0.09999990463256836},
        "independent recomputation from pair frame summary",
    )

    expected_boundary_stats = {
        "STATIC_BOUNDARY_A": (353, 4.849997520446777),
        "STATIC_BOUNDARY_B": (173, 7.299994945526123),
        "STATIC_BOUNDARY_C": (296, 12.39999008178711),
    }
    observed_boundary_stats: dict[str, dict[str, object]] = {}
    boundary_stats_ok = True
    for boundary_id, (expected_available, expected_center) in expected_boundary_stats.items():
        group = boundary_frames[boundary_frames.boundary_id.eq(boundary_id)]
        usable = group[group.frame_available]
        observed_boundary_stats[boundary_id] = {
            "available": int(group.frame_available.sum()),
            "center_m": float(usable.d_center_m.median()),
        }
        boundary_stats_ok &= int(group.frame_available.sum()) == expected_available
        boundary_stats_ok &= math.isclose(float(usable.d_center_m.median()), expected_center, abs_tol=1e-9)
    check(
        "THREE_NEUTRAL_BOUNDARY_LAYERS",
        boundary_stats_ok and boundary["boundary_names_are_physical_identity_neutral"] is True,
        observed_boundary_stats,
        {key: {"available": value[0], "center_m": value[1]} for key, value in expected_boundary_stats.items()},
        "boundary frame summary + static boundary analysis summary",
    )

    expected_tree_counts = {
        "TREE_A_USER_F120": (61, 66),
        "TREE_B_NEXT": (70, 81),
        "TREE_C_NEXT": (67, 81),
    }
    observed_tree_counts = {
        tree_id: (int(group.track_available.sum()), len(group))
        for tree_id, group in trees.groupby("tree_id")
    }
    check(
        "THREE_VISUAL_TREES_COMPLETE_COUNTS",
        observed_tree_counts == expected_tree_counts,
        observed_tree_counts,
        expected_tree_counts,
        "pre_reference/tree_visual_yellow_strap_tracks_pre_reference.csv",
    )
    check(
        "ZERO_CONFIRMED_STATIC_ANCHORS",
        mapping["accepted_static_anchor_count"] == 0
        and mapping["accepted_static_anchor_ids"] == []
        and winners.anchor_verdict.eq("VISUAL_CANDIDATE_NOT_TEMPORALLY_CONFIRMED").all(),
        {"accepted": mapping["accepted_static_anchor_count"], "winner_verdicts": sorted(winners.anchor_verdict.unique().tolist())},
        {"accepted": 0, "winner_verdicts": ["VISUAL_CANDIDATE_NOT_TEMPORALLY_CONFIRMED"]},
        "tree mapping summary + competition winners",
    )
    check(
        "AZIMUTH_MAPPING_INSUFFICIENT_TO_JUDGE",
        mapping["current_azimuth_mapping_verdict"] == "STATIC_ANCHORS_INSUFFICIENT_TO_JUDGE"
        and mapping["mapping_update_authorized"] is False
        and mapping["leave_one_anchor_out_available"] is False
        and summary["current_azimuth_mapping"] == "STATIC_ANCHORS_INSUFFICIENT_TO_JUDGE",
        {"verdict": mapping["current_azimuth_mapping_verdict"], "mapping_update_authorized": mapping["mapping_update_authorized"], "leave_one_out": mapping["leave_one_anchor_out_available"]},
        {"verdict": "STATIC_ANCHORS_INSUFFICIENT_TO_JUDGE", "mapping_update_authorized": False, "leave_one_out": False},
        "tree_static_anchor_mapping_summary_pre_reference.json + SUMMARY.json",
    )

    user_rank1 = winners[(winners.tree_id.eq("TREE_A_USER_F120")) & winners.competition_rank.eq(1)].iloc[0]
    false_rank3 = winners[(winners.tree_id.eq("TREE_A_USER_F120")) & winners.competition_rank.eq(3)].iloc[0]
    false_core = competitors[
        competitors.tree_id.eq("TREE_A_USER_F120")
        & competitors.competition_rank.eq(3)
        & competitors.sar_frame_index.eq(200)
    ].iloc[0]
    check(
        "USER_TREE_BEST_COMPETITOR_REJECTED",
        math.isclose(float(user_rank1.range_hypothesis_center_m), 14.50, abs_tol=1e-12)
        and int(user_rank1.matched_frames) == 75
        and int(user_rank1.available_sar_frames) == 108
        and math.isclose(float(user_rank1.median_abs_theta_residual_deg), 1.634077, abs_tol=1e-5)
        and math.isclose(float(user_rank1.p90_abs_theta_residual_deg), 3.705923, abs_tol=1e-5),
        user_rank1[["range_hypothesis_center_m", "matched_frames", "available_sar_frames", "persistence_fraction", "median_abs_theta_residual_deg", "p90_abs_theta_residual_deg"]].to_dict(),
        {"range_m": 14.5, "matched": 75, "available": 108, "median_abs_residual_deg": 1.634077, "p90_abs_residual_deg": 3.705923},
        "tree_sar_competition_winners_pre_reference.csv",
    )
    check(
        "STRONGEST_FALSE_SINGLE_FRAME_CORRESPONDENCE",
        math.isclose(float(false_rank3.range_hypothesis_center_m), 18.75, abs_tol=1e-12)
        and math.isclose(float(false_rank3.persistence_fraction), 0.5092592592592593, abs_tol=1e-12)
        and round(float(false_rank3.median_abs_theta_residual_deg), 2) == 1.76
        and round(float(false_rank3.p90_abs_theta_residual_deg), 2) == 4.51
        and round(float(false_core.theta_residual_deg), 2) == 0.14,
        {"range_m": float(false_rank3.range_hypothesis_center_m), "persistence": float(false_rank3.persistence_fraction), "median_abs_residual_deg": float(false_rank3.median_abs_theta_residual_deg), "p90_abs_residual_deg": float(false_rank3.p90_abs_theta_residual_deg), "f200_residual_deg": float(false_core.theta_residual_deg)},
        {"range_m": 18.75, "persistence": 0.5092592592592593, "median_abs_residual_deg_rounded": 1.76, "p90_abs_residual_deg_rounded": 4.51, "f200_residual_deg_rounded": 0.14},
        "competition winners + competitor trajectory at SAR F200",
    )

    table_flag_failures: list[str] = []
    for path in sorted(PRE.glob("*.csv")):
        try:
            frame = pd.read_csv(path)
        except pd.errors.EmptyDataError:
            continue
        for column in [name for name in frame.columns if name in {"manual_person_reference_used", "person_reference_used", "r04_accessed"}]:
            if not is_false_series(frame[column]):
                table_flag_failures.append(f"{path.name}:{column}")
    json_flag_failures: list[str] = []
    for path in sorted(PRE.glob("*.json")) + [OUT / "SUMMARY.json"]:
        data = json.loads(path.read_text(encoding="utf-8"))
        for key, value in recursively_collect_flags(data):
            if value is not False:
                json_flag_failures.append(f"{path.name}:{key}={value!r}")
    check(
        "NO_PERSON_REFERENCE_OR_R04_FLAGS",
        not table_flag_failures and not json_flag_failures,
        {"table_failures": table_flag_failures, "json_failures": json_flag_failures},
        {"table_failures": [], "json_failures": []},
        "all pre-reference CSV flag columns + JSON flags + SUMMARY.json",
    )

    manifest_pack = output_manifest[output_manifest.workspace_relative_path.eq(EXPECTED_PACK_PATH)]
    pack_hash = sha256_file(PACK)
    pack_metadata_ok = len(manifest_pack) == 1
    if pack_metadata_ok:
        item = manifest_pack.iloc[0]
        pack_metadata_ok = (
            int(item.bytes) == PACK.stat().st_size
            and item.sha256 == pack_hash
            and int(summary["review_pack_bytes"]) == PACK.stat().st_size
            and summary["review_pack_sha256"] == pack_hash
        )
    check(
        "REVIEW_PACK_SIZE_SHA_MANIFEST_MATCH",
        pack_metadata_ok,
        {"bytes": PACK.stat().st_size, "sha256": pack_hash, "summary_bytes": summary["review_pack_bytes"], "summary_sha256": summary["review_pack_sha256"], "manifest_rows": manifest_pack.to_dict("records")},
        "same size and SHA256 in filesystem, SUMMARY.json, and OUTPUT_MANIFEST.csv",
        "review pack + SUMMARY.json + OUTPUT_MANIFEST.csv",
    )

    zip_failures: list[str] = []
    archive_paths: list[str] = []
    source_paths: list[str] = []
    with zipfile.ZipFile(PACK, "r") as archive:
        archive_paths = archive.namelist()
        internal_manifest = json.loads(archive.read("MANIFEST.json").decode("utf-8"))
        source_paths = [str(item["source_path"]) for item in internal_manifest["entries"]]
        if internal_manifest["entry_count_excluding_manifest"] != len(internal_manifest["entries"]):
            zip_failures.append("internal entry count field mismatch")
        if len(archive_paths) != len(internal_manifest["entries"]) + 1:
            zip_failures.append("zip entry count mismatch")
        for item in internal_manifest["entries"]:
            payload = archive.read(item["archive_path"])
            if len(payload) != int(item["bytes"]):
                zip_failures.append(f"size:{item['archive_path']}")
            if hashlib.sha256(payload).hexdigest() != item["sha256"]:
                zip_failures.append(f"sha256:{item['archive_path']}")
    check(
        "REVIEW_PACK_INTERNAL_INTEGRITY",
        not zip_failures and len(archive_paths) == int(summary["review_pack_entry_count"]),
        {"entry_count": len(archive_paths), "summary_entry_count": summary["review_pack_entry_count"], "failures": zip_failures},
        {"entry_count": summary["review_pack_entry_count"], "failures": []},
        "ZIP MANIFEST.json and per-entry SHA256",
    )

    preliminary_tokens = (
        "landmark_review/",
        "static_landmark_",
        "visual_static_landmark_",
        "analyze_static_landmarks.py",
        "prepare_landmark_grid.py",
    )
    preliminary_hits = [
        path for path in archive_paths if any(token in path.lower() for token in preliminary_tokens)
    ]
    check(
        "PRELIMINARY_SHORT_LANDMARK_EXPERIMENT_EXCLUDED",
        not preliminary_hits,
        preliminary_hits,
        [],
        "review-pack archive paths",
    )

    forbidden_archive_tokens = ("r04", "final_box", "final_location", "final_center", "person_grounding")
    forbidden_path_hits = [
        path for path in archive_paths if any(token in path.lower() for token in forbidden_archive_tokens)
    ]
    forbidden_source_hits = [
        path
        for path in source_paths
        if "\\r04" in path.lower() or "/r04" in path.lower()
    ]
    check(
        "NO_R04_OR_FINAL_LOCALIZATION_ARTIFACTS",
        not forbidden_path_hits and not forbidden_source_hits,
        {"archive_hits": forbidden_path_hits, "source_hits": forbidden_source_hits},
        {"archive_hits": [], "source_hits": []},
        "review-pack archive paths and internal source paths",
    )

    raw_counts = {
        "core_optical": sum(path.startswith("raw_sequences/core_optical_F110_F135/") for path in archive_paths),
        "core_sar": sum(path.startswith("raw_sequences/core_sar_F183_F225/") for path in archive_paths),
        "stable_sar": sum(path.startswith("raw_sequences/stable_sar_F330_F335/") for path in archive_paths),
        "stable_optical": sum(path.startswith("raw_sequences/stable_optical_context_F198_F202/") for path in archive_paths),
    }
    check(
        "REVIEW_PACK_CONTINUOUS_RAW_SEQUENCES",
        raw_counts == {"core_optical": 26, "core_sar": 43, "stable_sar": 6, "stable_optical": 5},
        raw_counts,
        {"core_optical": 26, "core_sar": 43, "stable_sar": 6, "stable_optical": 5},
        "review-pack raw_sequences directories",
    )

    validation = pd.DataFrame(rows)
    pass_count = int(validation.status.eq("PASS").sum())
    fail_count = int(validation.status.eq("FAIL").sum())
    validation.to_csv(RESULTS, index=False, encoding="utf-8-sig")
    validation_summary = {
        "status": "PASS" if fail_count == 0 else "FAIL",
        "pass_count": pass_count,
        "fail_count": fail_count,
        "total_count": len(validation),
        "review_pack_sha256": pack_hash,
        "person_reference_used": False,
        "r04_accessed": False,
    }
    VALIDATION_SUMMARY.write_text(
        json.dumps(validation_summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    summary["validation_status"] = validation_summary["status"]
    summary["validation_pass_count"] = pass_count
    summary["validation_total_count"] = len(validation)
    (OUT / "SUMMARY.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    build_output_manifest()
    print(json.dumps(validation_summary, ensure_ascii=False, indent=2))
    if fail_count:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
