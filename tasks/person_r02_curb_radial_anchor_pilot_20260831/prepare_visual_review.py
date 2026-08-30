from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
import pandas as pd


WORKSPACE = Path(r"D:\profile\research\workspace")
OUT = WORKSPACE / "output" / "person_r02_curb_radial_anchor_pilot_20260831"
PRE = OUT / "pre_reference"
FIG = OUT / "figures" / "visual_review"
REGISTRY = (
    WORKSPACE
    / "output"
    / "person_terg_r2_runtime_grounding_and_full_stream_hypothesis_management_20260830"
    / "pre_reference"
    / "full_stream_frame_registry_pre_reference.parquet"
)
OPTICAL_HYP = (
    WORKSPACE
    / "output"
    / "person_optical_guided_sar_annotation_full_20260823"
    / "optical_person_frame_hypotheses.parquet"
)
OPTICAL_DIR = Path(
    r"C:\research_raw\optical_sar_data\20260721data\derived_frames"
    r"\pseudocolor_labelstudio_prep_20260722\frames\optical\R02ZF"
)


FRAME_GROUPS = {
    "01_early_middle": [0, 30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330],
    "02_late_to_f421": [345, 360, 375, 390, 405, 414, 421, 428, 435, 442],
    "03_f450_f494": [450, 456, 462, 468, 474, 480, 486, 492, 494],
    "04_dense_and_controls": [95, 110, 155, 260, 380, 421, 450, 472, 482, 488, 494],
}


def read_bgr(path: Path) -> np.ndarray:
    arr = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
    if arr is None:
        raise FileNotFoundError(path)
    return arr


def write_png(path: Path, image: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ok, buf = cv2.imencode(".png", image)
    if not ok:
        raise RuntimeError(f"Failed to encode {path}")
    buf.tofile(path)


def optical_path(frame_index: int) -> Path:
    matches = sorted(OPTICAL_DIR.glob(f"frame_{frame_index:06d}_t*ms.jpg"))
    if len(matches) != 1:
        raise FileNotFoundError(f"Expected one optical frame {frame_index}, found {matches}")
    return matches[0]


def letterbox(image: np.ndarray, width: int, height: int) -> np.ndarray:
    scale = min(width / image.shape[1], height / image.shape[0])
    resized = cv2.resize(
        image,
        (max(1, round(image.shape[1] * scale)), max(1, round(image.shape[0] * scale))),
        interpolation=cv2.INTER_AREA,
    )
    canvas = np.full((height, width, 3), 248, dtype=np.uint8)
    x = (width - resized.shape[1]) // 2
    y = (height - resized.shape[0]) // 2
    canvas[y : y + resized.shape[0], x : x + resized.shape[1]] = resized
    return canvas


def add_label(image: np.ndarray, lines: list[str]) -> np.ndarray:
    bar_h = 34 + 24 * (len(lines) - 1)
    out = np.full((image.shape[0] + bar_h, image.shape[1], 3), 255, dtype=np.uint8)
    out[bar_h:] = image
    for i, line in enumerate(lines):
        cv2.putText(
            out,
            line,
            (10, 24 + i * 24),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.58,
            (20, 20, 20),
            1,
            cv2.LINE_AA,
        )
    return out


def draw_person_boxes(image: np.ndarray, rows: pd.DataFrame) -> np.ndarray:
    out = image.copy()
    for _, row in rows.iterrows():
        p1 = (round(float(row.bbox_x1)), round(float(row.bbox_y1)))
        p2 = (round(float(row.bbox_x2)), round(float(row.bbox_y2)))
        cv2.rectangle(out, p1, p2, (0, 0, 255), 8)
        label = str(row.raw_track_fragment_id)
        cv2.putText(
            out,
            label,
            (p1[0], max(32, p1[1] - 12)),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (0, 0, 255),
            3,
            cv2.LINE_AA,
        )
    return out


def make_pair_panel(reg_row: pd.Series, hyp: pd.DataFrame) -> tuple[np.ndarray, dict]:
    sar_idx = int(reg_row.sar_frame_index)
    opt_idx = int(reg_row.nominal_optical_frame_index)
    sar_path = Path(reg_row.sar_image_path)
    opt_path = optical_path(opt_idx)
    sar = read_bgr(sar_path)
    optical = read_bgr(opt_path)
    hrows = hyp[hyp.frame_index.eq(opt_idx)]
    optical_overlay = draw_person_boxes(optical, hrows)

    optical_panel = letterbox(optical_overlay, 960, 540)
    sar_panel = letterbox(sar, 960, 540)
    optical_panel = add_label(
        optical_panel,
        [f"OPT R02ZF F{opt_idx}  t={int(reg_row.nominal_optical_timestamp_ms)} ms", f"PERSON hypotheses={len(hrows)}"],
    )
    sar_panel = add_label(
        sar_panel,
        [f"SAR R02ZF F{sar_idx}  t={int(reg_row.sar_timestamp_ms)} ms", "raw pseudocolor; no curb selection"],
    )
    panel = np.hstack([optical_panel, sar_panel])
    record = {
        "run_id": "R02ZF",
        "sar_frame_index": sar_idx,
        "optical_frame_index": opt_idx,
        "sar_timestamp_ms": int(reg_row.sar_timestamp_ms),
        "optical_timestamp_ms": int(reg_row.nominal_optical_timestamp_ms),
        "timestamp_delta_ms": int(reg_row.nominal_optical_timestamp_ms - reg_row.sar_timestamp_ms),
        "person_hypothesis_count": int(len(hrows)),
        "sar_image_path": str(sar_path),
        "optical_image_path": str(opt_path),
        "sync_status": str(reg_row.sync_status),
    }
    return panel, record


def make_contact_sheet(panels: list[np.ndarray], columns: int = 2) -> np.ndarray:
    cell_h = max(x.shape[0] for x in panels)
    cell_w = max(x.shape[1] for x in panels)
    rows = (len(panels) + columns - 1) // columns
    sheet = np.full((rows * cell_h, columns * cell_w, 3), 238, dtype=np.uint8)
    for idx, panel in enumerate(panels):
        y = (idx // columns) * cell_h
        x = (idx % columns) * cell_w
        sheet[y : y + panel.shape[0], x : x + panel.shape[1]] = panel
    return sheet


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    registry = pd.read_parquet(REGISTRY)
    registry = registry[registry.run_id.eq("R02ZF")].set_index("sar_frame_index", drop=False)
    hyp = pd.read_parquet(OPTICAL_HYP)
    hyp = hyp[hyp.run_id.eq("R02ZF")].copy()

    records: list[dict] = []
    unique_written: set[int] = set()
    for group_name, sar_indices in FRAME_GROUPS.items():
        panels: list[np.ndarray] = []
        for sar_idx in sar_indices:
            reg_row = registry.loc[sar_idx]
            panel, record = make_pair_panel(reg_row, hyp)
            panels.append(panel)
            record["review_group"] = group_name
            records.append(record)
            if sar_idx not in unique_written:
                write_png(FIG / "paired_keyframes" / f"R02ZF_SARF{sar_idx:06d}.png", panel)
                unique_written.add(sar_idx)
        write_png(FIG / f"{group_name}_contact_sheet.png", make_contact_sheet(panels))

    inventory = pd.DataFrame(records).drop_duplicates(
        subset=["sar_frame_index", "optical_frame_index"], keep="first"
    )
    inventory.to_csv(PRE / "visual_review_frame_inventory.csv", index=False, encoding="utf-8-sig")
    summary = {
        "run_id": "R02ZF",
        "unique_pair_count": int(len(inventory)),
        "group_counts": {k: len(v) for k, v in FRAME_GROUPS.items()},
        "frame_groups": FRAME_GROUPS,
        "pairing_semantics": "NOMINAL_INDEX_FPS_ZERO_OFFSET_UNVERIFIED",
        "reference_used": False,
        "curb_detector_used": False,
        "r04_accessed": False,
    }
    (PRE / "visual_review_generation_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
