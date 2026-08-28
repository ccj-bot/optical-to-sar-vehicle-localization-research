from __future__ import annotations

import hashlib
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


WORKSPACE = Path(r"D:\profile\research\workspace")
TASK_OUTPUT = (
    WORKSPACE
    / "output"
    / "person_physics_guided_image_domain_study_20260824"
)
CONTRACT_PATH = TASK_OUTPUT / "research_contract_v1.json"
EXPLORER_PATH = (
    WORKSPACE
    / "output"
    / "person_multidimensional_response_explorer_20260823"
    / "explorer_data.js"
)
PRIOR_INTERPRETATION_PATH = EXPLORER_PATH.with_name("RESEARCH_INTERPRETATION_V2.md")
OUTPUT_PATH = TASK_OUTPUT / "05_POST_REVIEW_LOCAL_EVIDENCE_AUDIT_DATA.json"

MANUAL_SOURCE = "MANUAL_NATIVE_SAR"
INTERPOLATED_SOURCE = "TEMPORAL_LINEAR_INTERPOLATION_SEED_REVIEW_REQUIRED"
ADJUSTED_SOURCE = "MANUAL_ADJUSTED_FROM_TEMPORAL_LINEAR_INTERPOLATION_SEED"
LAGS = (1, 3, 5)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def load_explorer(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    start = text.index("{")
    end = text.rindex("}") + 1
    return json.loads(text[start:end])


def finite_numbers(items: list[dict[str, Any]], key: str) -> list[float]:
    values: list[float] = []
    for item in items:
        value = item.get(key)
        if isinstance(value, (int, float)):
            values.append(float(value))
    return values


def min_max(values: list[float]) -> dict[str, float] | None:
    if not values:
        return None
    return {"min": min(values), "max": max(values)}


def main() -> None:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    hash_gate = []
    for item in contract["input_snapshot"]:
        path = Path(item["path"])
        actual = sha256(path)
        expected = item["sha256"].upper()
        hash_gate.append(
            {
                "path": str(path),
                "expected_sha256": expected,
                "actual_sha256": actual,
                "match": actual == expected,
            }
        )
    if not all(item["match"] for item in hash_gate):
        raise RuntimeError("Frozen input SHA256 mismatch; audit stopped.")

    explorer = load_explorer(EXPLORER_PATH)
    frames = explorer["frames"]
    frames_by_run: dict[str, list[dict[str, Any]]] = defaultdict(list)
    annotations_by_key: dict[tuple[str, str, int], dict[str, Any]] = {}

    for frame in frames:
        run_id = frame["run_id"]
        frames_by_run[run_id].append(frame)
        for annotation in frame["annotations"]:
            key = (run_id, annotation["instance_id"], frame["sar_frame_index"])
            annotations_by_key[key] = annotation

    run_summary: dict[str, Any] = {}
    lag_source_pairs: list[dict[str, Any]] = []
    manual_gap_audit: dict[str, Any] = {}

    for run_id in sorted(frames_by_run):
        run_frames = frames_by_run[run_id]
        annotations = [a for f in run_frames for a in f["annotations"]]
        target_ids = sorted({a["instance_id"] for a in annotations})
        source_counts = Counter(a["source"] for a in annotations)

        run_summary[run_id] = {
            "frames": len(run_frames),
            "targets": len(target_ids),
            "accepted_boxes": len(annotations),
            "source_counts": dict(sorted(source_counts.items())),
            "sync_status_counts": dict(
                sorted(Counter(f["sync_status"] for f in run_frames).items())
            ),
            "range_m": min_max(finite_numbers(annotations, "range_m")),
            "outer_radial_margin_m": min_max(
                finite_numbers(annotations, "outer_radial_margin_m")
            ),
            "local_valid_fraction": min_max(
                finite_numbers(annotations, "local_valid_fraction")
            ),
            "nearest_other_target_center_distance_px": min_max(
                finite_numbers(annotations, "nearest_target_center_distance_px")
            ),
        }

        run_gap_counter: Counter[int] = Counter()
        per_target_gap_counts: dict[str, Any] = {}
        for target_id in target_ids:
            manual_indices = sorted(
                frame_index
                for (r, t, frame_index), annotation in annotations_by_key.items()
                if r == run_id
                and t == target_id
                and annotation["source"] == MANUAL_SOURCE
            )
            gaps = [right - left for left, right in zip(manual_indices, manual_indices[1:])]
            run_gap_counter.update(gaps)
            per_target_gap_counts[target_id] = {
                "manual_box_count": len(manual_indices),
                "consecutive_manual_gap_counts": {
                    str(gap): count for gap, count in sorted(Counter(gaps).items())
                },
            }
        expanded_gaps = list(run_gap_counter.elements())
        manual_gap_audit[run_id] = {
            "all_targets_gap_counts": {
                str(gap): count for gap, count in sorted(run_gap_counter.items())
            },
            "median_gap_frames": (
                statistics.median(expanded_gaps) if expanded_gaps else None
            ),
            "per_target": per_target_gap_counts,
        }

        for lag in LAGS:
            source_pair_counter: Counter[tuple[str, str]] = Counter()
            total_pairs = 0
            for target_id in target_ids:
                indices = sorted(
                    frame_index
                    for r, t, frame_index in annotations_by_key
                    if r == run_id and t == target_id
                )
                index_set = set(indices)
                for frame_index in indices:
                    later = frame_index + lag
                    if later not in index_set:
                        continue
                    first = annotations_by_key[(run_id, target_id, frame_index)]
                    second = annotations_by_key[(run_id, target_id, later)]
                    source_pair_counter[(first["source"], second["source"])] += 1
                    total_pairs += 1

            manual_manual = source_pair_counter[(MANUAL_SOURCE, MANUAL_SOURCE)]
            contains_interpolation = sum(
                count
                for (source_a, source_b), count in source_pair_counter.items()
                if INTERPOLATED_SOURCE in (source_a, source_b)
            )
            contains_adjusted = sum(
                count
                for (source_a, source_b), count in source_pair_counter.items()
                if ADJUSTED_SOURCE in (source_a, source_b)
            )
            lag_source_pairs.append(
                {
                    "run_id": run_id,
                    "lag_frames": lag,
                    "target_track_pairs": total_pairs,
                    "manual_manual_pairs": manual_manual,
                    "manual_manual_fraction": (
                        manual_manual / total_pairs if total_pairs else None
                    ),
                    "pairs_containing_linear_interpolation": contains_interpolation,
                    "pairs_containing_manual_adjusted_interpolation": contains_adjusted,
                    "source_pair_counts": {
                        f"{source_a} -> {source_b}": count
                        for (source_a, source_b), count in sorted(
                            source_pair_counter.items()
                        )
                    },
                }
            )

    frame_keys = sorted({key for frame in frames for key in frame})
    optical_records = [
        optical
        for frame in frames
        for optical in frame.get("optical_persons", [])
    ]
    optical_keys = sorted({key for record in optical_records for key in record})
    annotation_keys = sorted(
        {key for frame in frames for annotation in frame["annotations"] for key in annotation}
    )

    prior_lines = PRIOR_INTERPRETATION_PATH.read_text(encoding="utf-8").splitlines()
    exposure_ranges = ((9, 14), (31, 61), (86, 90))
    exposure_excerpt = [
        {"line": line_no, "text": prior_lines[line_no - 1]}
        for start, end in exposure_ranges
        for line_no in range(start, end + 1)
    ]

    result = {
        "schema": "PERSON_POST_P0_LOCAL_EVIDENCE_AUDIT_V1",
        "status": "POST_REVIEW_METADATA_AND_EXPOSURE_AUDIT_COMPLETE_NO_P1_RUN",
        "interpreter": r"D:\MINICONDA\envs\py311\python.exe",
        "workspace": str(WORKSPACE),
        "input_hash_gate": hash_gate,
        "contract_available_data": contract["available_data"],
        "explorer_counts": explorer["counts"],
        "run_summary": run_summary,
        "lag_source_pairs": lag_source_pairs,
        "manual_annotation_gap_audit": manual_gap_audit,
        "field_audit": {
            "frame_record_keys": frame_keys,
            "optical_person_record_keys": optical_keys,
            "annotation_record_keys": annotation_keys,
            "frame_behavior_keys": [key for key in frame_keys if "behavior" in key.lower()],
            "optical_person_behavior_keys": [
                key for key in optical_keys if "behavior" in key.lower()
            ],
            "sync_status_counts": dict(
                sorted(Counter(frame["sync_status"] for frame in frames).items())
            ),
            "optical_person_record_count": len(optical_records),
        },
        "prior_data_exposure": {
            "path": str(PRIOR_INTERPRETATION_PATH),
            "sha256": sha256(PRIOR_INTERPRETATION_PATH),
            "verified_line_ranges": ["9-14", "31-61", "86-90"],
            "excerpt": exposure_excerpt,
        },
        "audit_boundaries": {
            "p0_refit": False,
            "p1_feature_experiment_run": False,
            "p2_started": False,
            "sar_boxes_created_moved_or_corrected": 0,
            "old_work_dependency": False,
        },
    }

    OUTPUT_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"WROTE {OUTPUT_PATH}")
    print(json.dumps({"status": result["status"], "run_summary": run_summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
