from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import cv2
import numpy as np
import pandas as pd


WORKSPACE = Path(r"D:\profile\research\workspace")
TASK = WORKSPACE / "tasks" / "person_r02_static_scene_skeleton_20260831"
OUT = WORKSPACE / "output" / "person_r02_static_scene_skeleton_20260831"
PRE = OUT / "pre_reference"
FIG = OUT / "figures" / "synchronized_review"
RAW_OPT = Path(
    r"C:\research_raw\optical_sar_data\20260721data\derived_frames"
    r"\pseudocolor_labelstudio_prep_20260722\frames\optical\R02ZF"
)
RAW_SAR = Path(
    r"C:\research_raw\optical_sar_data\20260721data\derived_frames"
    r"\pseudocolor_labelstudio_prep_20260722\frames\sar_pseudocolor\R02ZF"
)
NAME_RE = re.compile(r"frame_(\d+)_t(\d+)ms\.jpg$", re.IGNORECASE)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_bgr(path: Path) -> np.ndarray:
    image = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(path)
    return image


def inventory(folder: Path, modality: str) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for path in sorted(folder.glob("frame_*_t*ms.jpg")):
        match = NAME_RE.match(path.name)
        if not match:
            continue
        image = read_bgr(path)
        rows.append(
            {
                "run_id": "R02ZF",
                "modality": modality,
                "frame_index": int(match.group(1)),
                "timestamp_ms": int(match.group(2)),
                "image_path": str(path),
                "width_px": int(image.shape[1]),
                "height_px": int(image.shape[0]),
                "sha256": sha256_file(path),
            }
        )
    return pd.DataFrame(rows)


def pair_by_nearest_timestamp(optical: pd.DataFrame, sar: pd.DataFrame) -> pd.DataFrame:
    opt_ts = optical.timestamp_ms.to_numpy(int)
    rows: list[dict[str, object]] = []
    for item in sar.itertuples(index=False):
        pos = int(np.searchsorted(opt_ts, int(item.timestamp_ms)))
        candidates = [max(0, min(len(opt_ts) - 1, pos - 1)), max(0, min(len(opt_ts) - 1, pos))]
        best = min(candidates, key=lambda idx: (abs(int(opt_ts[idx]) - int(item.timestamp_ms)), idx))
        opt = optical.iloc[best]
        rows.append(
            {
                "run_id": "R02ZF",
                "sar_frame_index": int(item.frame_index),
                "sar_timestamp_ms": int(item.timestamp_ms),
                "sar_image_path": str(item.image_path),
                "optical_frame_index": int(opt.frame_index),
                "optical_timestamp_ms": int(opt.timestamp_ms),
                "optical_image_path": str(opt.image_path),
                "timestamp_residual_ms": int(opt.timestamp_ms) - int(item.timestamp_ms),
                "sync_status": "NOMINAL_INDEX_FPS_ZERO_OFFSET_UNVERIFIED",
            }
        )
    return pd.DataFrame(rows)


def fit_tile(image: np.ndarray, width: int, height: int) -> np.ndarray:
    scale = min(width / image.shape[1], height / image.shape[0])
    resized = cv2.resize(image, (max(1, round(image.shape[1] * scale)), max(1, round(image.shape[0] * scale))))
    tile = np.full((height, width, 3), 245, dtype=np.uint8)
    x0 = (width - resized.shape[1]) // 2
    y0 = (height - resized.shape[0]) // 2
    tile[y0 : y0 + resized.shape[0], x0 : x0 + resized.shape[1]] = resized
    return tile


def label_tile(tile: np.ndarray, lines: list[str]) -> np.ndarray:
    out = tile.copy()
    for index, value in enumerate(lines):
        y = 24 + 25 * index
        cv2.putText(out, value, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (0, 0, 0), 4, cv2.LINE_AA)
        cv2.putText(out, value, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (255, 255, 255), 1, cv2.LINE_AA)
    return out


def write_image(path: Path, image: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ok, encoded = cv2.imencode(path.suffix, image)
    if not ok:
        raise RuntimeError(path)
    encoded.tofile(path)


def contact_sheet(frame: pd.DataFrame, path: Path, columns: int = 5, tile_size: tuple[int, int] = (620, 330)) -> None:
    width, height = tile_size
    tiles: list[np.ndarray] = []
    for row in frame.itertuples(index=False):
        image = read_bgr(Path(row.image_path))
        tile = fit_tile(image, width, height)
        tile = label_tile(tile, [f"{row.modality} F{row.frame_index:03d}", f"t={row.timestamp_ms:06d} ms"])
        tiles.append(tile)
    rows = (len(tiles) + columns - 1) // columns
    blank = np.full((height, width, 3), 245, dtype=np.uint8)
    tiles.extend([blank] * (rows * columns - len(tiles)))
    canvas = np.vstack([np.hstack(tiles[start : start + columns]) for start in range(0, len(tiles), columns)])
    write_image(path, canvas)


def paired_sheet(pairs: pd.DataFrame, path: Path, max_rows: int = 20) -> None:
    tiles: list[np.ndarray] = []
    for row in pairs.head(max_rows).itertuples(index=False):
        opt = label_tile(
            fit_tile(read_bgr(Path(row.optical_image_path)), 870, 460),
            [f"OPT F{row.optical_frame_index:03d} t={row.optical_timestamp_ms:06d}ms"],
        )
        sar = label_tile(
            fit_tile(read_bgr(Path(row.sar_image_path)), 870, 460),
            [f"SAR F{row.sar_frame_index:03d} t={row.sar_timestamp_ms:06d}ms", f"dt={row.timestamp_residual_ms:+d}ms"],
        )
        tiles.append(np.hstack([opt, sar]))
    canvas = np.vstack(tiles)
    write_image(path, canvas)


def main() -> None:
    PRE.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    optical = inventory(RAW_OPT, "OPTICAL")
    sar = inventory(RAW_SAR, "SAR_PSEUDOCOLOR")
    paired = pair_by_nearest_timestamp(optical, sar)
    optical.to_csv(PRE / "r02zf_optical_frame_inventory_pre_reference.csv", index=False, encoding="utf-8-sig")
    sar.to_csv(PRE / "r02zf_sar_frame_inventory_pre_reference.csv", index=False, encoding="utf-8-sig")
    paired.to_csv(PRE / "r02zf_timestamp_pairing_pre_reference.csv", index=False, encoding="utf-8-sig")
    paired.to_parquet(PRE / "r02zf_timestamp_pairing_pre_reference.parquet", index=False)

    for start in (80, 120, 160):
        block = optical[optical.frame_index.between(start, start + 39)]
        contact_sheet(block, FIG / f"optical_F{start:03d}_F{start+39:03d}_consecutive.png", columns=5)
    for start in (133, 173, 213, 253, 293):
        block = sar[sar.frame_index.between(start, start + 39)]
        contact_sheet(block, FIG / f"sar_F{start:03d}_F{start+39:03d}_consecutive.png", columns=5)

    core_opt = optical[optical.frame_index.between(110, 135)].copy()
    core_rows = []
    for opt in core_opt.itertuples(index=False):
        candidates = paired.iloc[(paired.sar_timestamp_ms - int(opt.timestamp_ms)).abs().argsort()[:1]]
        core_rows.append(candidates.iloc[0].to_dict())
    core = pd.DataFrame(core_rows).drop_duplicates("sar_frame_index")
    paired_sheet(core.iloc[::2], FIG / "core_OPT110_135_nearest_SAR_every2.png", max_rows=20)

    sampled = paired[
        paired.optical_frame_index.between(80, 200)
        & paired.optical_frame_index.mod(5).eq(0)
    ].drop_duplicates("optical_frame_index")
    paired_sheet(sampled.iloc[:20], FIG / "paired_OPT080_175_step5_part1.png", max_rows=20)
    paired_sheet(sampled.iloc[20:40], FIG / "paired_OPT080_200_step5_part2.png", max_rows=20)

    core_exact = paired[(paired.optical_frame_index == 120) & (paired.sar_timestamp_ms == 6667)].iloc[0]
    summary = {
        "run_id": "R02ZF",
        "optical_frames": int(len(optical)),
        "sar_frames": int(len(sar)),
        "optical_time_span_ms": [int(optical.timestamp_ms.min()), int(optical.timestamp_ms.max())],
        "sar_time_span_ms": [int(sar.timestamp_ms.min()), int(sar.timestamp_ms.max())],
        "max_abs_nearest_timestamp_residual_ms": int(paired.timestamp_residual_ms.abs().max()),
        "core_case": {
            "optical_frame_index": int(core_exact.optical_frame_index),
            "optical_timestamp_ms": int(core_exact.optical_timestamp_ms),
            "sar_frame_index": int(core_exact.sar_frame_index),
            "sar_timestamp_ms": int(core_exact.sar_timestamp_ms),
            "timestamp_residual_ms": int(core_exact.timestamp_residual_ms),
        },
        "sync_status": "NOMINAL_INDEX_FPS_ZERO_OFFSET_UNVERIFIED",
        "person_reference_used": False,
        "r04_accessed": False,
    }
    (PRE / "synchronized_review_summary_pre_reference.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
