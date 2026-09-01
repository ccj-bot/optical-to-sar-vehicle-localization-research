from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path


WORKSPACE = Path(r"D:\profile\research\workspace")
OUT = WORKSPACE / "output" / "r02_manual_static_scene_anchor_preparation_20260902"
OPTICAL_DIR = Path(
    r"C:\research_raw\optical_sar_data\20260721data\derived_frames"
    r"\pseudocolor_labelstudio_prep_20260722\frames\optical\R02ZF"
)
SAR_DIR = Path(
    r"C:\research_raw\optical_sar_data\20260721data\derived_frames"
    r"\pseudocolor_labelstudio_prep_20260722\frames\sar_pseudocolor\R02ZF"
)
BATCH_PATH = OUT / "R02_STATIC_SCENE_ANNOTATION_BATCH_V1.csv"
MANIFEST_PATH = OUT / "R02_STATIC_SCENE_ANNOTATION_BATCH_V1_MANIFEST.json"
FILENAME_RE = re.compile(r"frame_(\d+)_t(\d+)ms\.jpg$", re.IGNORECASE)

SELECTED_OPTICAL_FRAMES = [
    0,
    30,
    60,
    90,
    110,
    115,
    120,
    125,
    130,
    135,
    160,
    198,
    201,
    225,
    250,
    275,
    290,
    297,
]


def inventory(folder: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for path in sorted(folder.glob("*.jpg")):
        match = FILENAME_RE.match(path.name)
        if not match:
            continue
        rows.append(
            {
                "frame_index": int(match.group(1)),
                "timestamp_ms": int(match.group(2)),
                "image_path": str(path),
            }
        )
    return rows


def selection_reason(frame_index: int) -> str:
    if frame_index == 120:
        return "USER_CORE_CASE_OPT_F120"
    if frame_index in {110, 115, 125, 130, 135}:
        return "DENSE_CONTEXT_AROUND_OPT_F110_F135"
    if frame_index in {198, 201}:
        return "PRIOR_STABLE_SEGMENT_CONTEXT_NOT_IDENTITY_AUTHORITY"
    return "UNIFORM_FULL_SEQUENCE_COVERAGE"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    optical = inventory(OPTICAL_DIR)
    sar = inventory(SAR_DIR)
    if len(optical) != 298 or len(sar) != 495:
        raise RuntimeError(f"Unexpected R02ZF inventory: optical={len(optical)} sar={len(sar)}")
    optical_by_index = {int(row["frame_index"]): row for row in optical}
    rows: list[dict[str, object]] = []
    for batch_index, optical_frame_index in enumerate(SELECTED_OPTICAL_FRAMES, start=1):
        optical_row = optical_by_index[optical_frame_index]
        optical_timestamp = int(optical_row["timestamp_ms"])
        sar_row = min(
            sar,
            key=lambda item: (
                abs(int(item["timestamp_ms"]) - optical_timestamp),
                int(item["frame_index"]),
            ),
        )
        residual = int(sar_row["timestamp_ms"]) - optical_timestamp
        rows.append(
            {
                "batch_index": batch_index,
                "run_id": "R02ZF",
                "optical_frame_index": optical_frame_index,
                "optical_timestamp_ms": optical_timestamp,
                "optical_image_path": optical_row["image_path"],
                "sar_frame_index": int(sar_row["frame_index"]),
                "sar_timestamp_ms": int(sar_row["timestamp_ms"]),
                "sar_image_path": sar_row["image_path"],
                "nominal_timestamp_residual_ms": residual,
                "sync_status": "NOMINAL_INDEX_FPS_ZERO_OFFSET_UNVERIFIED",
                "selection_reason": selection_reason(optical_frame_index),
                "annotation_status": "PENDING",
                "automatic_hint_is_identity_authority": False,
                "person_gt": False,
            }
        )
    OUT.mkdir(parents=True, exist_ok=True)
    with BATCH_PATH.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    manifest = {
        "run_id": "R02ZF",
        "batch_version": "R02_STATIC_SCENE_ANNOTATION_BATCH_V1",
        "pair_count": len(rows),
        "selected_optical_frames": SELECTED_OPTICAL_FRAMES,
        "selected_sar_frames": [row["sar_frame_index"] for row in rows],
        "core_optical_f120_included": any(row["optical_frame_index"] == 120 for row in rows),
        "stable_context_sar_frames": [
            row["sar_frame_index"] for row in rows if row["optical_frame_index"] in {198, 201}
        ],
        "max_abs_nominal_timestamp_residual_ms": max(
            abs(int(row["nominal_timestamp_residual_ms"])) for row in rows
        ),
        "sync_status": "NOMINAL_INDEX_FPS_ZERO_OFFSET_UNVERIFIED",
        "pairing_method": "OPTICAL_SELECTED_THEN_NEAREST_SAR_BY_FILENAME_TIMESTAMP",
        "automatic_candidates_are_hints_only": True,
        "person_gt": False,
        "batch_sha256": sha256_file(BATCH_PATH),
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
