#!/usr/bin/env python3
"""Render post-freeze PERSON worst-case review sheets.

This script is visualization-only. It reads the already frozen R01/R04 outputs
and never refits or changes a common-motion model.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
P0_SCRIPT = HERE / "run_p0_common_apparent_motion.py"
SPEC = importlib.util.spec_from_file_location("p0_common", P0_SCRIPT)
assert SPEC and SPEC.loader
p0 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = p0
SPEC.loader.exec_module(p0)


def draw_anchor_points(image: np.ndarray, anchors: pd.DataFrame) -> None:
    if len(anchors) > 180:
        indices = np.linspace(0, len(anchors) - 1, 180).round().astype(int)
        anchors = anchors.iloc[indices]
    for row in anchors.itertuples(index=False):
        point = (int(round(float(row.x_px))), int(round(float(row.y_px))))
        color = (0, 255, 255) if row.anchor_split == "FIT" else (255, 255, 255)
        cv2.circle(image, point, 2, color, -1, cv2.LINE_AA)


def draw_person_vectors(image: np.ndarray, rows: pd.DataFrame, vector_scale: float) -> None:
    for offset, row in enumerate(rows.itertuples(index=False)):
        start = np.array([float(row.from_cx_px), float(row.from_cy_px)], dtype=float)
        observed = np.array([float(row.observed_dx_px), float(row.observed_dy_px)], dtype=float)
        predicted = np.array([float(row.predicted_common_dx_px), float(row.predicted_common_dy_px)], dtype=float)
        start_i = tuple(np.rint(start).astype(int))
        observed_i = tuple(np.rint(start + observed * vector_scale).astype(int))
        predicted_i = tuple(np.rint(start + predicted * vector_scale).astype(int))
        cv2.circle(image, start_i, 4, (0, 255, 0), -1, cv2.LINE_AA)
        cv2.arrowedLine(image, start_i, observed_i, (255, 255, 255), 2, cv2.LINE_AA, tipLength=0.2)
        cv2.arrowedLine(image, start_i, predicted_i, (255, 0, 255), 2, cv2.LINE_AA, tipLength=0.2)
        target_short = str(row.target_id).split("PERSON")[-1]
        label = f"P{target_short} residual={float(row.compensated_residual_px):.2f}px"
        label_point = (max(4, start_i[0] - 65), max(20, start_i[1] - 18 - offset * 18))
        cv2.putText(image, label, label_point, cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(image, label, label_point, cv2.FONT_HERSHEY_SIMPLEX, 0.48, (20, 20, 20), 1, cv2.LINE_AA)


def add_band(image: np.ndarray, lines: list[str]) -> np.ndarray:
    band_height = 28 + 24 * len(lines)
    output = np.full((image.shape[0] + band_height, image.shape[1], 3), 245, dtype=np.uint8)
    output[band_height:] = image
    for idx, line in enumerate(lines):
        cv2.putText(output, line, (12, 28 + idx * 24), cv2.FONT_HERSHEY_SIMPLEX, 0.56, (20, 20, 20), 1, cv2.LINE_AA)
    return output


def choose_pair_groups(person: pd.DataFrame, manual_only: bool, count: int = 6) -> pd.DataFrame:
    subset = person[person["both_manual_endpoints"]].copy() if manual_only else person.copy()
    grouped = (
        subset.groupby(["from_frame", "to_frame", "lag"], as_index=False)
        .agg(
            max_person_residual_px=("compensated_residual_px", "max"),
            mean_person_residual_px=("compensated_residual_px", "mean"),
            target_count=("target_id", "size"),
        )
        .sort_values(["max_person_residual_px", "mean_person_residual_px"], ascending=False)
        .head(count)
    )
    return grouped


def render_readable_summary_plots(
    pair_metrics: pd.DataFrame,
    person: pd.DataFrame,
    selected: dict[int, str],
) -> None:
    selected_pairs = pair_metrics[
        pair_metrics["is_selected_frozen_model"] & pair_metrics["model_available"]
    ].copy()
    fig, axes = plt.subplots(1, len(p0.ALGORITHM_CONFIG["lags"]), figsize=(12, 4), constrained_layout=True)
    for axis, lag in zip(axes, p0.ALGORITHM_CONFIG["lags"]):
        rows = selected_pairs[selected_pairs["lag"] == int(lag)]
        axis.boxplot(
            [rows["M0_holdout_residual_median_px"].dropna(), rows["holdout_residual_median_px"].dropna()],
            tick_labels=["M0", selected[int(lag)]],
            showfliers=True,
        )
        axis.set_title(f"R04 lag {lag}")
        axis.set_ylabel("Background holdout residual (px)")
        axis.grid(alpha=0.25)
    fig.suptitle("Frozen R04 background holdout residuals; no difficult-pair deletion")
    fig.savefig(p0.VIS_DIR / "R04_background_holdout_residual_by_lag.png", dpi=170)
    plt.close(fig)

    fig, axis = plt.subplots(figsize=(7, 5), constrained_layout=True)
    axis.boxplot(
        [person["uncompensated_residual_px"], person["compensated_residual_px"]],
        tick_labels=["Uncompensated", "Frozen compensation"],
        showfliers=True,
    )
    axis.set_ylabel("Stationary PERSON box-centre residual (px)")
    axis.set_title("R04 stationary PERSON residual before/after compensation")
    axis.grid(alpha=0.25)
    fig.savefig(p0.VIS_DIR / "R04_stationary_person_before_after.png", dpi=170)
    plt.close(fig)


def render_subset(
    subset_name: str,
    selected_pairs: pd.DataFrame,
    person: pd.DataFrame,
    anchors: pd.DataFrame,
    pair_metrics: pd.DataFrame,
    frame_map: dict[str, dict],
) -> list[dict]:
    rendered: list[np.ndarray] = []
    registry: list[dict] = []
    vector_scale = 6.0
    for rank, pair in enumerate(selected_pairs.itertuples(index=False), start=1):
        pair_people = person[
            (person["from_frame"] == int(pair.from_frame))
            & (person["to_frame"] == int(pair.to_frame))
            & (person["lag"] == int(pair.lag))
        ].copy()
        metric = pair_metrics[
            (pair_metrics["from_frame"] == int(pair.from_frame))
            & (pair_metrics["to_frame"] == int(pair.to_frame))
            & (pair_metrics["lag"] == int(pair.lag))
            & pair_metrics["is_selected_frozen_model"]
        ].iloc[0]
        frame_uid_a = str(metric["from_frame_uid"])
        frame_uid_b = str(metric["to_frame_uid"])
        frame_a = frame_map[frame_uid_a]
        frame_b = frame_map[frame_uid_b]
        image_a = cv2.imread(str(p0.file_url_to_path(frame_a["sar_image_url"])), cv2.IMREAD_COLOR)
        image_b = cv2.imread(str(p0.file_url_to_path(frame_b["sar_image_url"])), cv2.IMREAD_COLOR)
        p0.draw_valid_boundaries(image_a, frame_a, p0.ALGORITHM_CONFIG)
        p0.draw_valid_boundaries(image_b, frame_b, p0.ALGORITHM_CONFIG)
        p0.draw_expanded_person_regions(image_a, frame_a, p0.ALGORITHM_CONFIG)
        p0.draw_expanded_person_regions(image_b, frame_b, p0.ALGORITHM_CONFIG)
        pair_anchors = anchors[
            (anchors["from_frame_uid"] == frame_uid_a)
            & (anchors["to_frame_uid"] == frame_uid_b)
            & (anchors["lag"] == int(pair.lag))
        ]
        draw_anchor_points(image_a, pair_anchors)
        draw_person_vectors(image_b, pair_people, vector_scale)
        left = add_band(
            image_a,
            [
                f"{subset_name} source {frame_uid_a} | yellow=fit white=holdout anchors",
                "red=PERSON orange=expanded exclusion cyan=valid fan boundary",
            ],
        )
        right = add_band(
            image_b,
            [
                f"target {frame_uid_b} | PERSON white=observed magenta=frozen common prediction (x{vector_scale:g})",
                f"lag={int(pair.lag)} model={metric['model']} max PERSON residual={float(pair.max_person_residual_px):.3f}px background holdout={float(metric['holdout_residual_median_px']):.3f}px",
            ],
        )
        sheet = np.concatenate([left, right], axis=1)
        filename = (
            f"worst_PERSON_{subset_name}_{rank:02d}_R04ZF_"
            f"{int(pair.from_frame):06d}_{int(pair.to_frame):06d}_lag{int(pair.lag)}.jpg"
        )
        path = p0.VIS_DIR / filename
        cv2.imwrite(str(path), sheet, [cv2.IMWRITE_JPEG_QUALITY, 94])
        scale = min(1.0, 1200.0 / sheet.shape[1])
        rendered.append(cv2.resize(sheet, (int(round(sheet.shape[1] * scale)), int(round(sheet.shape[0] * scale)))))
        registry.append(
            {
                "subset": subset_name,
                "rank": rank,
                "from_frame": int(pair.from_frame),
                "to_frame": int(pair.to_frame),
                "lag": int(pair.lag),
                "model": str(metric["model"]),
                "max_person_residual_px": float(pair.max_person_residual_px),
                "mean_person_residual_px": float(pair.mean_person_residual_px),
                "background_holdout_residual_median_px": float(metric["holdout_residual_median_px"]),
                "M0_background_holdout_residual_median_px": float(metric["M0_holdout_residual_median_px"]),
                "display_stratum": str(metric["display_stratum"]),
                "visual_path": str(path),
                "manual_multimodal_review": "PENDING",
            }
        )
    if rendered:
        width = max(image.shape[1] for image in rendered)
        padded: list[np.ndarray] = []
        for image in rendered:
            if image.shape[1] < width:
                pad = np.full((image.shape[0], width - image.shape[1], 3), 255, dtype=np.uint8)
                image = np.concatenate([image, pad], axis=1)
            padded.append(image)
        montage = np.concatenate(padded, axis=0)
        cv2.imwrite(
            str(p0.VIS_DIR / f"R04_worst_PERSON_{subset_name}_montage.jpg"),
            montage,
            [cv2.IMWRITE_JPEG_QUALITY, 92],
        )
    return registry


def main() -> None:
    p0.assert_workspace_scope()
    freeze = p0.load_and_verify_freeze()
    validation = json.loads(p0.QUANT_VALIDATION_PATH.read_text(encoding="utf-8"))
    if validation["R01_freeze_payload_sha256"] != freeze["freeze_payload_sha256"]:
        raise RuntimeError("quantitative validation is not linked to the current R01 freeze")
    explorer = p0.load_explorer()
    selected = {int(key): value for key, value in validation["selected_model_by_lag"].items()}
    person = pd.read_csv(p0.OUTPUT_DIR / "stationary_person_residuals.csv")
    person = person[(person["run_id"] == p0.HELDOUT_RUN) & person["model_available"]].copy()
    person = person[person.apply(lambda row: row["model"] == selected[int(row["lag"])], axis=1)].copy()
    anchors = pd.read_csv(p0.OUTPUT_DIR / "background_anchor_holdout_metrics.csv")
    anchors = anchors[anchors["run_id"] == p0.HELDOUT_RUN].copy()
    pair_metrics = pd.read_csv(p0.OUTPUT_DIR / "common_motion_pair_metrics.csv")
    pair_metrics = pair_metrics[pair_metrics["run_id"] == p0.HELDOUT_RUN].copy()
    frame_map = {
        frame["sar_frame_uid"]: frame
        for frame in explorer["frames"]
        if frame["run_id"] == p0.HELDOUT_RUN
    }
    render_readable_summary_plots(pair_metrics, person, selected)
    registry: list[dict] = []
    registry.extend(
        render_subset(
            "ALL_ACCEPTED",
            choose_pair_groups(person, manual_only=False),
            person,
            anchors,
            pair_metrics,
            frame_map,
        )
    )
    registry.extend(
        render_subset(
            "MANUAL_ENDPOINTS",
            choose_pair_groups(person, manual_only=True),
            person,
            anchors,
            pair_metrics,
            frame_map,
        )
    )
    pd.DataFrame(registry).to_csv(
        p0.OUTPUT_DIR / "worst_PERSON_case_registry.csv", index=False, encoding="utf-8-sig"
    )
    print(json.dumps({"rendered_case_count": len(registry), "model_refit": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
