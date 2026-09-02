from __future__ import annotations

import argparse
import math
import re
from pathlib import Path

import cv2
import numpy as np


WORKSPACE = Path(r"D:\profile\research\workspace")
SAR_DIR = Path(
    r"C:\research_raw\optical_sar_data\20260721data\derived_frames"
    r"\pseudocolor_labelstudio_prep_20260722\frames\sar_pseudocolor\R02ZF"
)
OUT = WORKSPACE / "output" / "r02_boundary_multibracket_preparation_20260902" / "selection_audit"
FILENAME_RE = re.compile(r"frame_(\d+)_t(\d+)ms\.jpg$", re.IGNORECASE)


def read_bgr(path: Path) -> np.ndarray:
    image = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(path)
    return image


def write_png(path: Path, image: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ok, encoded = cv2.imencode(".png", image)
    if not ok:
        raise RuntimeError(f"Could not encode {path}")
    encoded.tofile(path)


def inventory() -> dict[int, tuple[int, Path]]:
    rows: dict[int, tuple[int, Path]] = {}
    for path in SAR_DIR.glob("*.jpg"):
        match = FILENAME_RE.match(path.name)
        if match:
            rows[int(match.group(1))] = (int(match.group(2)), path)
    if sorted(rows) != list(range(495)):
        raise RuntimeError(f"Unexpected R02ZF SAR inventory: {len(rows)} frames")
    return rows


def tile(frame_index: int, timestamp_ms: int, path: Path, width: int = 410) -> np.ndarray:
    image = read_bgr(path)
    height = round(image.shape[0] * width / image.shape[1])
    image = cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA)
    header = np.full((34, width, 3), (24, 22, 20), dtype=np.uint8)
    cv2.putText(
        header,
        f"F{frame_index:03d}   t={timestamp_ms:05d}ms",
        (10, 24),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.62,
        (235, 235, 235),
        1,
        cv2.LINE_AA,
    )
    return np.vstack([header, image])


def sheet(frame_indices: list[int], registry: dict[int, tuple[int, Path]], columns: int = 4) -> np.ndarray:
    tiles = [tile(index, *registry[index]) for index in frame_indices]
    rows = math.ceil(len(tiles) / columns)
    blank = np.full_like(tiles[0], 255)
    tiles.extend([blank] * (rows * columns - len(tiles)))
    return np.vstack([np.hstack(tiles[row * columns : (row + 1) * columns]) for row in range(rows)])


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate image-only dense R02ZF SAR selection sheets")
    parser.add_argument("--chunk-size", type=int, default=20)
    args = parser.parse_args()
    registry = inventory()
    regions = {
        "early": range(45, 91),
        "mid_later": range(235, 286),
        "late": range(425, 476),
    }
    outputs: list[str] = []
    for name, region in regions.items():
        indices = list(region)
        for part, start in enumerate(range(0, len(indices), args.chunk_size), start=1):
            selected = indices[start : start + args.chunk_size]
            path = OUT / f"dense_{name}_part{part}_F{selected[0]:03d}_F{selected[-1]:03d}.png"
            write_png(path, sheet(selected, registry))
            outputs.append(str(path))
    print("\n".join(outputs))


if __name__ == "__main__":
    main()
