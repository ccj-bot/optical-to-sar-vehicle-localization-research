#!/usr/bin/env python3
"""Render deterministic real-case sheets and the final M0A HTML report."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
from pathlib import Path
from typing import Any

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


SCRIPT_PATH = Path(__file__).resolve()
TASK_DIR = SCRIPT_PATH.parent
WORKSPACE = TASK_DIR.parents[1]
STUDY_OUTPUT = WORKSPACE / "output" / "person_physics_guided_image_domain_study_20260824"
OUTPUT_DIR = STUDY_OUTPUT / "m0a_r02_lag1_q95_region_support_transport_pilot"
REGION_ROOT = STUDY_OUTPUT / "p1e_sar_only_response_interface" / "runtime_track_response_region_minimal_v1"
MASK_DIR = REGION_ROOT / "response_region_masks"
IMAGE_DIR = WORKSPACE / "output" / "pseudocolor_labelstudio_prep_20260722" / "frames" / "sar_pseudocolor" / "R02ZF"
REFERENCE_CENTER_PATH = STUDY_OUTPUT / "p1e_sar_only_response_interface" / "candidate_recall_semantic_split_v1" / "single_frame_candidate_recall" / "manual_reference_candidate_interpretation_v2.csv"
NODE_PATH = OUTPUT_DIR / "pre_reference_region_nodes.csv"
MATRIX_PATH = OUTPUT_DIR / "pre_reference_compatibility_matrix.csv"
PRE_CASE_PATH = OUTPUT_DIR / "pre_reference_case_registry.csv"
POST_CASE_PATH = OUTPUT_DIR / "post_reference_case_registry.csv"
POST_SUPPORTED_PATH = OUTPUT_DIR / "post_reference_supported_explanations.csv"
POST_SUMMARY_PATH = OUTPUT_DIR / "post_reference_summary.json"
FINAL_VALIDATION_PATH = OUTPUT_DIR / "final_validation.json"
REPORT_PATH = OUTPUT_DIR / "M0A_R02_LAG1_Q95_REGION_SUPPORT_TRANSPORT_REPORT.html"
FIGURE_DIR = OUTPUT_DIR / "figures"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def bool_value(value: Any) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    normalized = str(value).strip().lower()
    if normalized in {"true", "1"}:
        return True
    if normalized in {"false", "0"}:
        return False
    raise ValueError(f"invalid boolean value: {value!r}")


def find_image(frame_index: int) -> Path:
    matches = sorted(IMAGE_DIR.glob(f"frame_{frame_index:06d}_t*ms.jpg"))
    if len(matches) != 1:
        raise RuntimeError(f"expected one image for frame {frame_index}, got {matches}")
    return matches[0]


def load_masks(frame_uid: str) -> dict[str, np.ndarray]:
    with np.load(MASK_DIR / f"{frame_uid}.npz") as archive:
        return {tag: archive[tag].astype(np.int32) for tag in ("Q090", "Q095", "Q0975")}


def warp(mask: np.ndarray, dx: float, dy: float) -> np.ndarray:
    height, width = mask.shape
    matrix = np.array([[1.0, 0.0, dx], [0.0, 1.0, dy]], np.float32)
    return np.clip(cv2.warpAffine(mask.astype(np.float32), matrix, (width, height), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0.0), 0.0, 1.0)


def draw_contour(axis: plt.Axes, mask: np.ndarray, color: str, linewidth: float, label: str | None = None) -> None:
    if np.any(mask):
        axis.contour(mask.astype(float), levels=[0.5], colors=[color], linewidths=[linewidth])
        if label:
            axis.plot([], [], color=color, linewidth=linewidth, label=label)


def q95_label(nodes: pd.DataFrame, frame_uid: str, region_id: str) -> int:
    row = nodes[(nodes["frame_uid"].eq(frame_uid)) & (nodes["region_id"].eq(region_id))]
    if len(row) != 1:
        raise RuntimeError(f"cannot resolve region label: {frame_uid} {region_id}")
    return int(row.iloc[0]["region_label"])


def crop_bounds(masks: list[np.ndarray], width: int, height: int, margin: int = 70) -> tuple[int, int, int, int]:
    union = np.zeros((height, width), bool)
    for mask in masks:
        union |= np.asarray(mask) > 0
    yy, xx = np.where(union)
    if len(xx) == 0:
        return 0, width, 0, height
    x0, x1 = max(0, int(xx.min()) - margin), min(width, int(xx.max()) + margin + 1)
    y0, y1 = max(0, int(yy.min()) - margin), min(height, int(yy.max()) + margin + 1)
    if x1 - x0 < 360:
        center = (x0 + x1) // 2
        x0, x1 = max(0, center - 180), min(width, center + 180)
    if y1 - y0 < 300:
        center = (y0 + y1) // 2
        y0, y1 = max(0, center - 150), min(height, center + 150)
    return x0, x1, y0, y1


def overlay_centers(axis: plt.Axes, centers: pd.DataFrame, frame_uid: str) -> None:
    frame = centers[centers["frame_uid"].eq(frame_uid)]
    for row in frame.itertuples(index=False):
        axis.scatter(float(row.reference_x_px), float(row.reference_y_px), marker="*", s=90, c="#ff2bd6", edgecolors="white", linewidths=0.7, zorder=10)
        axis.text(float(row.reference_x_px) + 5, float(row.reference_y_px) - 5, str(row.target_id).replace("R02ZF_SARPERSON", "P"), color="#ff2bd6", fontsize=7, weight="bold")


def render_case(
    case: pd.Series,
    phase: str,
    nodes: pd.DataFrame,
    matrix: pd.DataFrame,
    centers: pd.DataFrame | None,
    output_path: Path,
) -> None:
    base_edge_id = str(case["base_edge_id"])
    p0_rows = matrix[(matrix["condition"].eq("P0")) & (matrix["base_edge_id"].eq(base_edge_id))]
    zero_rows = matrix[(matrix["condition"].eq("ZERO")) & (matrix["base_edge_id"].eq(base_edge_id))]
    if len(p0_rows) != 1 or len(zero_rows) != 1:
        raise RuntimeError(f"case edge not unique: {base_edge_id}")
    p0, zero = p0_rows.iloc[0], zero_rows.iloc[0]
    from_uid, to_uid = str(p0["from_frame_uid"]), str(p0["to_frame_uid"])
    source_masks, destination_masks = load_masks(from_uid), load_masks(to_uid)
    source_label = q95_label(nodes, from_uid, str(p0["source_region_id"]))
    destination_label = q95_label(nodes, to_uid, str(p0["destination_region_id"]))
    source_q95 = source_masks["Q095"] == source_label
    destination_q95 = destination_masks["Q095"] == destination_label
    source_q975 = source_q95 & (source_masks["Q0975"] > 0)
    source_q90_labels = np.unique(source_masks["Q090"][source_q95])
    source_q90_labels = source_q90_labels[source_q90_labels > 0]
    source_q90 = np.isin(source_masks["Q090"], source_q90_labels)
    destination_q975 = destination_q95 & (destination_masks["Q0975"] > 0)
    destination_q90_labels = np.unique(destination_masks["Q090"][destination_q95])
    destination_q90_labels = destination_q90_labels[destination_q90_labels > 0]
    destination_q90 = np.isin(destination_masks["Q090"], destination_q90_labels)
    p0_warp = warp(source_q95, float(p0["p0_dx_px"]), float(p0["p0_dy_px"]))
    zero_warp = source_q95.astype(np.float32)
    related_raw = case.get("related_destination_region_ids_json", "[]")
    related_ids = json.loads(related_raw) if isinstance(related_raw, str) and related_raw else []
    related_source_masks: list[np.ndarray] = []
    related_destination_masks: list[np.ndarray] = []
    for region_id in related_ids:
        if str(case["case_type"]) == "MERGE_LIKE":
            label = q95_label(nodes, from_uid, str(region_id))
            related_source_masks.append(source_masks["Q095"] == label)
        else:
            label = q95_label(nodes, to_uid, str(region_id))
            related_destination_masks.append(destination_masks["Q095"] == label)

    source_bgr = cv2.imread(str(find_image(int(p0["from_frame"]))))
    destination_bgr = cv2.imread(str(find_image(int(p0["to_frame"]))))
    if source_bgr is None or destination_bgr is None:
        raise RuntimeError("case image unreadable")
    source_rgb = cv2.cvtColor(source_bgr, cv2.COLOR_BGR2RGB)
    destination_rgb = cv2.cvtColor(destination_bgr, cv2.COLOR_BGR2RGB)
    height, width = source_q95.shape
    x0, x1, y0, y1 = crop_bounds(
        [source_q90, destination_q90, p0_warp, *related_source_masks, *related_destination_masks],
        width,
        height,
    )

    fig, axes = plt.subplots(2, 3, figsize=(17, 10), constrained_layout=True)
    for axis in axes.ravel():
        axis.set_xlim(x0, x1)
        axis.set_ylim(y1, y0)
        axis.set_xticks([])
        axis.set_yticks([])

    axes[0, 0].imshow(source_rgb)
    draw_contour(axes[0, 0], source_q90, "#37d67a", 1.0, "q90 envelope")
    draw_contour(axes[0, 0], source_q95, "#ffd43b", 2.0, "q95 source")
    draw_contour(axes[0, 0], source_q975, "#ff6b6b", 1.2, "q97.5 core")
    for related in related_source_masks:
        draw_contour(axes[0, 0], related, "#00d5ff", 1.5, "related source")
    axes[0, 0].set_title(f"Source F{int(p0['from_frame'])}: q90/q95/q97.5")

    axes[0, 1].imshow(destination_rgb)
    draw_contour(axes[0, 1], destination_masks["Q095"] > 0, "#888888", 0.35, "all q95")
    draw_contour(axes[0, 1], destination_q90, "#37d67a", 1.0, "selected q90")
    draw_contour(axes[0, 1], destination_q95, "#ff3b30", 2.0, "selected q95")
    draw_contour(axes[0, 1], destination_q975, "#ffcc00", 1.1, "selected q97.5")
    for related in related_destination_masks:
        draw_contour(axes[0, 1], related, "#00d5ff", 1.5, "related region")
    axes[0, 1].set_title(f"Destination F{int(p0['to_frame'])}: all relevant regions")

    axes[0, 2].imshow(destination_rgb)
    axes[0, 2].imshow(np.ma.masked_less_equal(p0_warp, 0), cmap="magma", alpha=0.72, vmin=0, vmax=1)
    draw_contour(axes[0, 2], destination_q95, "#00ffff", 1.8)
    axes[0, 2].set_title(f"P0 warped soft occupancy dx={p0['p0_dx_px']:.3f}, dy={p0['p0_dy_px']:.3f}")

    axes[1, 0].imshow(destination_rgb)
    draw_contour(axes[1, 0], p0_warp >= 0.5, "#ffd43b", 1.5, "P0 warp")
    draw_contour(axes[1, 0], destination_q95, "#ff3b30", 2.0, "destination")
    axes[1, 0].set_title(f"P0: source-total={p0['q95_source_total_retention']:.3f}; conditional={p0['q95_conditional_valid_retention']:.3f}")

    axes[1, 1].imshow(destination_rgb)
    draw_contour(axes[1, 1], zero_warp >= 0.5, "#8ec5ff", 1.5, "ZERO warp")
    draw_contour(axes[1, 1], destination_q95, "#ff3b30", 2.0, "destination")
    axes[1, 1].set_title(f"ZERO: source-total={zero['q95_source_total_retention']:.3f}; conditional={zero['q95_conditional_valid_retention']:.3f}")

    if phase == "post-reference" and centers is not None:
        overlay_centers(axes[0, 0], centers, from_uid)
        for axis in (axes[0, 1], axes[0, 2], axes[1, 0], axes[1, 1]):
            overlay_centers(axis, centers, to_uid)

    axes[1, 2].axis("off")
    descriptor_text = "\n".join(
        [
            f"Case: {case['case_type']}",
            f"Phase: {phase}",
            f"Source: {p0['source_region_id']}",
            f"Destination: {p0['destination_region_id']}",
            f"source_support_total = {p0['source_support_total']:.3f}",
            f"warped_before_valid = {p0['warped_support_before_valid_clip']:.3f}",
            f"warped_in_valid = {p0['warped_support_in_destination_valid']:.3f}",
            f"out_of_frame_or_invalid = {p0['transport_out_of_frame_or_invalid']:.3f}",
            f"valid_transport_fraction = {p0['valid_transport_fraction']:.4f}",
            f"P0 q95 source-total = {p0['q95_source_total_retention']:.4f}",
            f"ZERO q95 source-total = {zero['q95_source_total_retention']:.4f}",
            f"P0-ZERO = {p0['q95_source_total_retention'] - zero['q95_source_total_retention']:+.4f}",
            f"q97.5->q97.5 = {p0['q975_to_q975_core_retention']:.4f}" if pd.notna(p0['q975_to_q975_core_retention']) else "q97.5->q97.5 = unavailable",
            f"q90 envelope = {p0['q90_weak_envelope_retention']:.4f}",
            f"area ratio = {p0['destination_to_source_area_ratio']:.3f}",
            f"theta midpoint delta = {p0['theta_midpoint_change_deg']:+.3f} deg",
            f"range midpoint delta = {p0['range_midpoint_change_m']:+.3f} m",
            f"boundary/truncated = {any(bool_value(p0[field]) for field in ['source_touches_observable_boundary', 'destination_touches_observable_boundary', 'source_has_truncated_support', 'destination_has_truncated_support'])}",
            "Manual magenta stars are post-reference only." if phase == "post-reference" else "No manual reference loaded or shown.",
        ]
    )
    axes[1, 2].text(0.0, 1.0, descriptor_text, va="top", family="monospace", fontsize=10)
    fig.suptitle("M0A R02 lag1 q95 region-support transport — real case", fontsize=15, weight="bold")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=145)
    plt.close(fig)


def render_phase(phase: str) -> list[Path]:
    nodes = pd.read_csv(NODE_PATH)
    matrix = pd.read_csv(MATRIX_PATH, low_memory=False)
    pre_cases = pd.read_csv(PRE_CASE_PATH)
    centers = None
    cases = pre_cases.copy()
    if phase == "post-reference":
        centers = pd.read_csv(REFERENCE_CENTER_PATH, usecols=["run_id", "frame_uid", "frame_index", "target_id", "reference_x_px", "reference_y_px"])
        centers = centers[centers["run_id"].eq("R02ZF")].drop_duplicates(["frame_uid", "target_id"])
        post_cases = pd.read_csv(POST_CASE_PATH)
        cases = pd.concat([pre_cases, post_cases], ignore_index=True, sort=False)
    output_paths: list[Path] = []
    destination = FIGURE_DIR / ("pre_reference" if phase == "pre-reference" else "post_reference")
    for index, case in cases.iterrows():
        slug = str(case["case_type"]).lower()
        path = destination / f"{index + 1:02d}_{slug}.png"
        render_case(case, phase, nodes, matrix, centers, path)
        output_paths.append(path)
    return output_paths


def fmt(value: Any, digits: int = 3) -> str:
    if value is None or (isinstance(value, float) and not math.isfinite(value)):
        return "unavailable"
    return f"{float(value):.{digits}f}"


def build_report() -> None:
    summary = json.loads(POST_SUMMARY_PATH.read_text(encoding="utf-8"))
    pre_cases = pd.read_csv(PRE_CASE_PATH)
    post_cases = pd.read_csv(POST_CASE_PATH)
    supported = pd.read_csv(POST_SUPPORTED_PATH, low_memory=False)
    p0 = supported[supported["condition"].eq("P0")]
    important = pd.concat(
        [
            pre_cases[pre_cases["case_type"].isin(["P0_CLEARLY_BETTER_THAN_ZERO", "P0_APPROX_EQUAL_ZERO", "ZERO_BETTER_THAN_P0", "SPLIT_LIKE", "BOUNDARY_OR_TRUNCATED"])],
            post_cases.head(3),
        ],
        ignore_index=True,
        sort=False,
    ).head(8)
    case_items = []
    all_post = pd.concat([pre_cases, post_cases], ignore_index=True, sort=False)
    for index, row in all_post.iterrows():
        filename = f"figures/post_reference/{index + 1:02d}_{str(row['case_type']).lower()}.png"
        case_items.append(f"<article class='case'><h3>{html.escape(str(row['case_type']))}</h3><img src='{html.escape(filename)}'><p><code>{html.escape(str(row['base_edge_id']))}</code></p></article>")
    important_rows = "".join(
        f"<tr><td>{html.escape(str(row['case_type']))}</td><td><code>{html.escape(str(row['base_edge_id']))}</code></td></tr>"
        for _, row in important.iterrows()
    )
    pvz = summary["p0_vs_zero"]
    matched = summary["matched_reference_unsupported"]
    qlayers = summary["q975_and_q90"]
    state = summary["final_m0a_state"]
    css = """
    body{font-family:Segoe UI,Arial,sans-serif;background:#f4f6f8;color:#17202a;margin:0}.wrap{max-width:1320px;margin:auto;padding:28px}
    .hero{background:#132238;color:white;padding:28px;border-radius:16px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:14px;margin:18px 0}
    .card,.case{background:white;border-radius:13px;padding:16px;box-shadow:0 3px 14px #00000012}.metric{font-size:1.65rem;font-weight:700;color:#145da0}.case img{width:100%;border-radius:8px}.cases{display:grid;grid-template-columns:repeat(auto-fit,minmax(460px,1fr));gap:18px}
    table{width:100%;border-collapse:collapse;background:white}th,td{padding:9px;border-bottom:1px solid #ddd;text-align:left}code{word-break:break-all}.warn{border-left:5px solid #f39c12;padding-left:14px}
    """
    document = f"""<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'><title>M0A R02 region support transport</title><style>{css}</style></head><body><div class='wrap'>
    <section class='hero'><h1>M0A R02 lag1 q95 region-support transport pilot</h1><p>Scientific role: <b>M0 SAR-temporal prerequisite</b>. Final state: <b>{html.escape(state)}</b>.</p><p>This report does not establish Optical–SAR motion consistency, runtime identity, ambiguity resolution, or final SAR localization.</p></section>
    <section class='grid'>
      <div class='card'><div class='metric'>22 / 22</div><p>R02 adjacent lag1 comparable pairs</p></div>
      <div class='card'><div class='metric'>{fmt(summary['p0_supported_q95_source_total_retention']['median'])}</div><p>P0 supported median q95 source-total retention</p></div>
      <div class='card'><div class='metric'>{fmt(summary['zero_supported_q95_source_total_retention']['median'])}</div><p>ZERO supported median q95 source-total retention</p></div>
      <div class='card'><div class='metric'>{fmt(pvz['median_source_total_retention_delta'],4)}</div><p>Median P0 − ZERO retention</p></div>
      <div class='card'><div class='metric'>{fmt(matched['p0_supported_win_rate'])}</div><p>P0 supported win rate vs reference-unsupported matched alternatives</p></div>
      <div class='card'><div class='metric'>{fmt(summary['p0_supported_rank']['median'],1)}</div><p>Supported destination rank median</p></div>
    </section>
    <section class='card'><h2>Denominator and control interpretation</h2><p>Source-total retention and conditional-valid retention remain separate. Median valid transport fraction is {fmt(summary['p0_valid_transport_fraction']['median'],4)}. P0 is better than ZERO on {fmt(pvz['p0_better_fraction'])} of supported edges, tied on {fmt(pvz['tie_fraction'])}, and worse on {fmt(pvz['zero_better_fraction'])}. No parameter was changed to make P0 win.</p></section>
    <section class='grid'><div class='card'><h2>q97.5 core</h2><p>Median q97.5→q97.5 retention: {fmt(qlayers['p0_q975_to_q975_core_retention']['median'])}. Median q95 minus core: {fmt(qlayers['q95_minus_q975_median'])}.</p></div><div class='card'><h2>q90 envelope</h2><p>Median q90 envelope retention: {fmt(qlayers['p0_q90_weak_envelope_retention']['median'])}. Median q90 minus q95: {fmt(qlayers['q90_minus_q95_median'])}.</p></div></section>
    <section class='card warn'><h2>Why this is not Optical–SAR motion consistency</h2><p>The experiment contains no raw optical angular dynamics and does not compare Δtheta_optical with Δtheta_SAR. It only tests one-step SAR image-domain region-support continuity and candidate ordering. The complete matrix is not pruned or assigned, so no unique dynamic identity or ambiguity-reduction count exists.</p></section>
    <section><h2>Most important deterministic cases</h2><table><tr><th>Case</th><th>Frozen edge</th></tr>{important_rows}</table></section>
    <section><h2>Real-case sheets</h2><p>Magenta stars appear only in post-reference versions. The corresponding nine pre-reference images remain under <code>figures/pre_reference</code>.</p><div class='cases'>{''.join(case_items)}</div></section>
    <section class='card'><h2>Audit artifacts</h2><ul><li><a href='pre_reference_manifest.json'>pre-reference manifest</a></li><li><a href='execution_ledger.json'>execution ledger</a></li><li><a href='pre_reference_output_hashes.json'>pre-reference hash freeze</a></li><li><a href='post_reference_summary.json'>post-reference summary</a></li><li><a href='final_validation.json'>final validation</a></li></ul><p>Reference-supported explanation rows: {len(supported)}; unique P0 target transitions: {len(p0)}.</p></section>
    </div></body></html>"""
    REPORT_PATH.write_text(document, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("pre-reference", "post-reference"), required=True)
    args = parser.parse_args()
    paths = render_phase(args.phase)
    if args.phase == "post-reference":
        build_report()
    print(json.dumps({"phase": args.phase, "figure_count": len(paths), "figures": [str(path.relative_to(WORKSPACE)) for path in paths], "report": str(REPORT_PATH.relative_to(WORKSPACE)) if args.phase == "post-reference" else None}, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
