from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from pathlib import Path

import cv2
import numpy as np


WORKSPACE = Path(r"D:\profile\research\workspace")
TASK = WORKSPACE / "tasks" / "r02_boundary_multibracket_preparation_20260902"
OUT = WORKSPACE / "output" / "r02_boundary_multibracket_preparation_20260902"
FIGURES = OUT / "figures"
USER_OUTPUT = OUT / "user_annotations"
OPTICAL_DIR = Path(
    r"C:\research_raw\optical_sar_data\20260721data\derived_frames"
    r"\pseudocolor_labelstudio_prep_20260722\frames\optical\R02ZF"
)
SAR_DIR = Path(
    r"C:\research_raw\optical_sar_data\20260721data\derived_frames"
    r"\pseudocolor_labelstudio_prep_20260722\frames\sar_pseudocolor\R02ZF"
)
FILENAME_RE = re.compile(r"frame_(\d+)_t(\d+)ms\.jpg$", re.IGNORECASE)

BRACKETS = [
    {
        "bracket_id": "A_EARLY",
        "start": 47,
        "end": 82,
        "review_frames": [47, 51, 55, 59, 63, 67, 71, 75, 79, 82],
        "selection_reason": "EARLY_IMAGE_LED_REPLICATION_WITH_VISIBLE_BOUNDARIES_AND_GRADUAL_CENTRAL_CLUTTER_CHANGE",
        "visual_difficulty": "MODERATE; boundary contrast and central response strength vary through the interval",
        "notes": "36 SAR frames inclusive; endpoints are non-round frames; excludes frozen comparator F150-F183.",
    },
    {
        "bracket_id": "B_MID_LATER",
        "start": 239,
        "end": 278,
        "review_frames": [239, 243, 248, 252, 256, 261, 265, 269, 274, 278],
        "selection_reason": "MID_LATER_IMAGE_LED_REPLICATION_ACROSS_RIDGE_INTENSITY_AND_LOWER_ARC_CLUTTER_VARIATION",
        "visual_difficulty": "MODERATE; mid-field intensity and lower response texture change without an obvious scene cut",
        "notes": "40 SAR frames inclusive; endpoints are non-round frames; temporally separated from A and comparator.",
    },
    {
        "bracket_id": "C_LATE",
        "start": 427,
        "end": 472,
        "review_frames": [427, 432, 437, 442, 447, 452, 457, 462, 467, 472],
        "selection_reason": "LATE_IMAGE_LED_REPLICATION_INCLUDING_STRONG_TO_WEAK_TO_RECOVERED_RESPONSE_CONDITIONS",
        "visual_difficulty": "CHALLENGING; substantial brightness weakening near the middle followed by recovery",
        "notes": "46 SAR frames inclusive; preserves a difficult visual transition instead of selecting only bright frames.",
    },
]


def inventory(folder: Path, expected_count: int) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for path in folder.glob("*.jpg"):
        match = FILENAME_RE.match(path.name)
        if match:
            rows.append({"frame_index": int(match.group(1)), "timestamp_ms": int(match.group(2)), "image_path": path})
    rows.sort(key=lambda row: int(row["frame_index"]))
    if len(rows) != expected_count:
        raise RuntimeError(f"Unexpected inventory in {folder}: {len(rows)}")
    return rows


def read_bgr(path: Path) -> np.ndarray:
    image = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(path)
    return image


def write_png(path: Path, image: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ok, encoded = cv2.imencode(".png", image)
    if not ok:
        raise RuntimeError(path)
    encoded.tofile(path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def render_review_strip(bracket: dict[str, object], sar_by_index: dict[int, dict[str, object]]) -> np.ndarray:
    width = 410
    tiles: list[np.ndarray] = []
    review_frames = list(bracket["review_frames"])
    for position, frame_index in enumerate(review_frames):
        row = sar_by_index[frame_index]
        image = read_bgr(Path(row["image_path"]))
        height = round(image.shape[0] * width / image.shape[1])
        image = cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA)
        role = "START" if position == 0 else "END" if position == len(review_frames) - 1 else "PROCESS"
        header = np.full((38, width, 3), (24, 22, 20), dtype=np.uint8)
        cv2.putText(header, f"{role}  F{frame_index:03d}  t={int(row['timestamp_ms']):05d}ms", (9, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (238, 238, 238), 1, cv2.LINE_AA)
        tiles.append(np.vstack([header, image]))
    columns = 5
    rows = math.ceil(len(tiles) / columns)
    blank = np.full_like(tiles[0], 255)
    tiles.extend([blank] * (rows * columns - len(tiles)))
    return np.vstack([np.hstack(tiles[row * columns : (row + 1) * columns]) for row in range(rows)])


def main() -> None:
    optical = inventory(OPTICAL_DIR, 298)
    sar = inventory(SAR_DIR, 495)
    sar_by_index = {int(row["frame_index"]): row for row in sar}
    rows: list[dict[str, object]] = []
    for bracket in BRACKETS:
        for seed_role, frame_index in (("START", int(bracket["start"])), ("END", int(bracket["end"]))):
            sar_row = sar_by_index[frame_index]
            sar_timestamp = int(sar_row["timestamp_ms"])
            optical_row = min(optical, key=lambda item: (abs(int(item["timestamp_ms"]) - sar_timestamp), int(item["frame_index"])))
            residual = sar_timestamp - int(optical_row["timestamp_ms"])
            rows.append(
                {
                    "batch_index": len(rows) + 1,
                    "run_id": "R02ZF",
                    "bracket_id": bracket["bracket_id"],
                    "seed_role": seed_role,
                    "optical_frame_index": optical_row["frame_index"],
                    "optical_timestamp_ms": optical_row["timestamp_ms"],
                    "optical_image_path": str(optical_row["image_path"]),
                    "sar_frame_index": frame_index,
                    "sar_timestamp_ms": sar_timestamp,
                    "sar_image_path": str(sar_row["image_path"]),
                    "nominal_timestamp_residual_ms": residual,
                    "sync_status": "NOMINAL_INDEX_FPS_ZERO_OFFSET_UNVERIFIED",
                    "nearest_optical_frame": optical_row["frame_index"],
                    "nearest_optical_timestamp_ms": optical_row["timestamp_ms"],
                    "sync_residual_ms": residual,
                    "selection_reason": bracket["selection_reason"],
                    "visual_difficulty": bracket["visual_difficulty"],
                    "notes": bracket["notes"],
                    "annotation_scope": "SAR_BOUNDARY_ONLY",
                    "annotation_status": "PENDING",
                    "automatic_hint_is_identity_authority": False,
                    "person_gt": False,
                }
            )

    OUT.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    USER_OUTPUT.mkdir(parents=True, exist_ok=True)
    if any(USER_OUTPUT.iterdir()):
        raise RuntimeError(f"User output directory must be empty before delivery: {USER_OUTPUT}")

    batch_path = OUT / "R02_BOUNDARY_MULTIBRACKET_ANNOTATION_BATCH_V1.csv"
    with batch_path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    figure_paths: list[Path] = []
    for bracket, letter in zip(BRACKETS, "ABC", strict=True):
        figure_path = FIGURES / f"bracket_{letter}_review_strip.png"
        write_png(figure_path, render_review_strip(bracket, sar_by_index))
        figure_paths.append(figure_path)

    report_path = OUT / "MULTIBRACKET_SELECTION_REPORT.md"
    report_lines = [
        "# R02 manual-boundary multi-bracket selection report",
        "",
        "## Decision boundary",
        "",
        "This is an image-led annotation preparation only. No propagation result, PERSON evidence, tree anchor, automatic range hint, or R04 material was used to select the brackets.",
        "The boundary coordinate remains an image/scene-relative `d_perp` proxy and is not called PERSON radial range or physical calibration.",
        "Frozen comparator F150-F183 is excluded and remains unchanged.",
        "",
        "## Selected brackets",
        "",
        "| Bracket | Inclusive SAR span | Frames | Manual endpoints | Visual selection reason |",
        "|---|---:|---:|---|---|",
    ]
    for bracket in BRACKETS:
        frame_count = int(bracket["end"]) - int(bracket["start"]) + 1
        report_lines.append(
            f"| {bracket['bracket_id']} | F{int(bracket['start']):03d}-F{int(bracket['end']):03d} | {frame_count} | F{int(bracket['start']):03d} START; F{int(bracket['end']):03d} END | {bracket['selection_reason']} |"
        )
    report_lines.extend(
        [
            "",
            "## Visual review performed",
            "",
            "- Reviewed the complete F0-F494 stream at 5-frame spacing with no overlays.",
            "- Reviewed every frame in F45-F90, F235-F285, and F425-F475.",
            "- For each final bracket, checked START, approximately 25%, 50%, 75%, END, and visible weakening/clutter transitions.",
            "- Review strips contain 10 process frames each and show no algorithmic proposal or propagation result.",
            "",
            "## User task",
            "",
            "For each of the six keyframes, draw only `SAR_BOUNDARY_NEAR` and `SAR_BOUNDARY_FAR`, then save/advance. If either boundary is not visually supportable, use the unresolved/not-visible control rather than guessing.",
            "",
            "## Explicit non-claims",
            "",
            "The selected brackets are candidates for later independent bidirectional replication. Selection does not establish propagation, closure, physical boundary calibration, PERSON range, PERSON identity, or final localization.",
        ]
    )
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    manifest_path = OUT / "R02_BOUNDARY_MULTIBRACKET_PREPARATION_MANIFEST.json"
    manifest = {
        "schema": "R02_BOUNDARY_MULTIBRACKET_PREPARATION_V1",
        "annotation_scope": "SAR_BOUNDARY_ONLY",
        "brackets": BRACKETS,
        "keyframe_count": len(rows),
        "required_object_types": ["SAR_BOUNDARY_NEAR", "SAR_BOUNDARY_FAR"],
        "batch_path": str(batch_path),
        "batch_sha256": sha256(batch_path),
        "figure_sha256": {path.name: sha256(path) for path in figure_paths},
        "user_output_directory": str(USER_OUTPUT),
        "user_output_directory_empty": not any(USER_OUTPUT.iterdir()),
        "propagation_run": False,
        "r04_accessed": False,
        "person_experiment_run": False,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
