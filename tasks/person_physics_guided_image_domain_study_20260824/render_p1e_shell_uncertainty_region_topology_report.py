"""Render a compact Chinese report for shell uncertainty and region topology."""

from __future__ import annotations

import html
import importlib.util
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import unquote, urlparse

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager
from matplotlib.patches import Polygon


CHINESE_FONT_PATH = Path(r"C:\Windows\Fonts\msyh.ttc")
if CHINESE_FONT_PATH.is_file():
    font_manager.fontManager.addfont(str(CHINESE_FONT_PATH))
    plt.rcParams["font.family"] = font_manager.FontProperties(fname=str(CHINESE_FONT_PATH)).get_name()
plt.rcParams["axes.unicode_minus"] = False


SCRIPT_PATH = Path(__file__).resolve()
TASK_DIR = SCRIPT_PATH.parent
WORKSPACE = TASK_DIR.parents[1]
P1E_ROOT = (
    WORKSPACE
    / "output"
    / "person_physics_guided_image_domain_study_20260824"
    / "p1e_sar_only_response_interface"
)
OUTPUT_DIR = P1E_ROOT / "shell_uncertainty_region_topology_v1"
VIS_DIR = OUTPUT_DIR / "visualizations"
HTML_PATH = OUTPUT_DIR / "P1E_SHELL_UNCERTAINTY_REGION_TOPOLOGY_REPORT.html"
ANALYSIS_SCRIPT = TASK_DIR / "run_p1e_shell_uncertainty_region_topology.py"
PREVIOUS_SCRIPT = TASK_DIR / "run_p1e_runtime_track_response_region_minimal.py"
OPTICAL_HYPOTHESES = (
    WORKSPACE
    / "output"
    / "person_optical_guided_sar_annotation_full_20260823"
    / "optical_person_frame_hypotheses.parquet"
)

SHELLS_CSV = OUTPUT_DIR / "optical_shell_uncertainty_decomposition_pre_reference.csv"
FRAME_SHELLS_CSV = OUTPUT_DIR / "frame_shell_uncertainty_summary_pre_reference.csv"
PAIR_SEP_CSV = OUTPUT_DIR / "offline_r02_associated_shell_separability.csv"
REFERENCE_EVAL_CSV = OUTPUT_DIR / "offline_reference_shell_retention.csv"
COMPONENTS_CSV = OUTPUT_DIR / "gt_blind_bipartite_components_pre_reference.csv"
SHELL_NODES_CSV = OUTPUT_DIR / "gt_blind_shell_nodes_with_conditions.csv"
REGION_NODES_CSV = OUTPUT_DIR / "gt_blind_region_nodes_with_conditions.csv"
REFERENCE_TOPOLOGY_CSV = OUTPUT_DIR / "offline_reference_region_topology_interpretation.csv"
OBSERVATION_CSV = P1E_ROOT / "observation_model_diagnostic_v1" / "observation_condition_table.csv"
MASK_DIR = P1E_ROOT / "runtime_track_response_region_minimal_v1" / "response_region_masks"
SUMMARY_JSON = OUTPUT_DIR / "diagnostic_summary.json"

PRIMARY_GUARD = "CURRENT_G6"
POLICY_ORDER = ["SAME_FRAME", "PAST_ONLY_250MS", "BUFFERED_100MS", "CENTERED_250MS"]
POLICY_LABEL = {
    "SAME_FRAME": "同帧",
    "PAST_ONLY_250MS": "因果过去 250 ms",
    "BUFFERED_100MS": "缓冲 +100 ms",
    "CENTERED_250MS": "居中 ±250 ms",
}
GUARD_ORDER = ["CURRENT_G6", "R04_MAE_PROXY_G2P652", "NO_GUARD_LOWER_BOUND_G0"]
GUARD_LABEL = {
    "CURRENT_G6": "当前 ±6°",
    "R04_MAE_PROXY_G2P652": "几何敏感性 ±2.652°",
    "NO_GUARD_LOWER_BOUND_G0": "raw-box 下界 0°",
}
CASE_SPECS = [
    ("R02ZF_SARF000472", "R02_F472_LOW_RANK_AND_SHARED", "R02 首帧：P01/P02 低 rank 与 P03/P04 shared 同时存在"),
    ("R02ZF_SARF000482", "R02_F482_PEAK_MISSING_REGION_PRESENT", "F482：P02 离散 peak missing，但 q95 region 明确存在"),
    ("R02ZF_SARF000490", "R02_F490_PEAK_MISSING_REGION_PRESENT", "F490：延展 q95 region 与多个 shell 相交"),
    ("R03ZF_SARF000489", "R03_F489_ONE_SHELL_ONE_CORE", "R03：q97.5 可出现 one-shell/one-region 强核心"),
    ("R03ZF_SARF000494", "R03_F494_EDGE_OBSERVABLE", "R03 边界：单帧可观察不等于 P0 可输运"),
    ("R04ZF_SARF000014", "R04_F014_ONE_SHELL_MULTI_REGION", "R04：一个粗方位壳内仍包含多个 SAR response regions"),
    ("R04ZF_SARF000191", "R04_F191_MULTI_MULTI", "R04：多 shell/多 region 的运行时歧义拓扑"),
]


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def file_url_to_path(value: str) -> Path:
    parsed = urlparse(str(value))
    raw = unquote(parsed.path) if parsed.scheme.lower() == "file" else value
    if raw.startswith("/") and len(raw) > 3 and raw[2] == ":":
        raw = raw[1:]
    return Path(raw.replace("/", "\\"))


def fmt(value: Any, digits: int = 3) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "—"
    return f"{number:.{digits}f}" if np.isfinite(number) else "—"


def pct(value: Any, digits: int = 1) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "—"
    return f"{100.0 * number:.{digits}f}%" if np.isfinite(number) else "—"


def finite_median(values: Iterable[Any]) -> float:
    array = pd.to_numeric(pd.Series(list(values)), errors="coerce").to_numpy(float)
    array = array[np.isfinite(array)]
    return float(np.median(array)) if len(array) else math.nan


def union_intervals(intervals: Iterable[tuple[float, float]]) -> list[tuple[float, float]]:
    normalized = sorted((min(float(a), float(b)), max(float(a), float(b))) for a, b in intervals)
    output: list[list[float]] = []
    for low, high in normalized:
        if not output or low > output[-1][1]:
            output.append([low, high])
        else:
            output[-1][1] = max(output[-1][1], high)
    return [(a, b) for a, b in output]


def inside_intervals(theta: np.ndarray, intervals: Iterable[tuple[float, float]]) -> np.ndarray:
    output = np.zeros(theta.shape, dtype=bool)
    for low, high in union_intervals(intervals):
        output |= (theta >= low) & (theta <= high)
    return output


def polar_grid(frame: dict[str, Any], shape: tuple[int, int]) -> tuple[np.ndarray, np.ndarray]:
    height, width = shape
    yy, xx = np.indices((height, width), dtype=np.float32)
    geometry = frame["geometry"]
    cx = float(geometry["center_x_px"])
    cy = float(geometry["center_y_px"])
    radial = np.hypot(xx - cx, cy - yy)
    theta = np.degrees(np.arctan2(xx - cx, cy - yy))
    return radial, theta


def add_binary_contour(axis: Any, binary: np.ndarray, color: str, width: float, alpha: float) -> None:
    contours, _ = cv2.findContours(binary.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for contour in contours:
        if len(contour) < 2:
            continue
        points = contour[:, 0, :]
        axis.plot(points[:, 0], points[:, 1], color=color, linewidth=width, alpha=alpha)


def shell_polygon(center_x: float, center_y: float, radius: float, low: float, high: float) -> np.ndarray:
    angles = np.linspace(low, high, max(8, int(abs(high - low) * 1.5) + 2))
    radians = np.radians(angles)
    outer_x = center_x + radius * np.sin(radians)
    outer_y = center_y - radius * np.cos(radians)
    return np.column_stack(([center_x, *outer_x, center_x], [center_y, *outer_y, center_y]))


def draw_shells(axis: Any, frame: dict[str, Any], shell_rows: pd.DataFrame) -> None:
    colors = ["#3cd6a0", "#ffb14e", "#75a7ff", "#ef6f9f", "#b78cff", "#5fd0d6", "#e7d65f"]
    geometry = frame["geometry"]
    cx = float(geometry["center_x_px"])
    cy = float(geometry["center_y_px"])
    radius = float(geometry["radius_px"])
    for index, shell in enumerate(shell_rows.itertuples(index=False)):
        color = colors[index % len(colors)]
        for low, high in json.loads(shell.effective_intervals_json):
            polygon = shell_polygon(cx, cy, radius, float(low), float(high))
            axis.add_patch(Polygon(polygon, closed=True, facecolor=color, edgecolor=color, alpha=0.06, linewidth=0.9))


def render_case(
    frame: dict[str, Any],
    title: str,
    slug: str,
    shells: pd.DataFrame,
    region_nodes: pd.DataFrame,
    references: pd.DataFrame,
    components: pd.DataFrame,
) -> dict[str, Any]:
    frame_uid = str(frame["sar_frame_uid"])
    image_path = file_url_to_path(frame["sar_image_url"])
    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(image_path)
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    with np.load(MASK_DIR / f"{frame_uid}.npz") as archive:
        q90 = archive["Q090"] > 0
        q95 = archive["Q095"] > 0
        q975 = archive["Q0975"] > 0
    _, theta = polar_grid(frame, q95.shape)
    refs = references[references["frame_uid"].astype(str).eq(frame_uid)]

    fig, axes = plt.subplots(2, 2, figsize=(16, 9), constrained_layout=True)
    panel_specs = [
        (axes[0, 0], None, "原始 SAR 伪彩图（reference 仅后置叠加）"),
        (axes[0, 1], "SAME_FRAME", "same-frame：理想同帧可用性"),
        (axes[1, 0], "PAST_ONLY_250MS", "past-only：零未来观测"),
        (axes[1, 1], "CENTERED_250MS", "centered ±250 ms：保守但含未来观测"),
    ]
    panel_metrics: list[dict[str, Any]] = []
    for axis, policy, label in panel_specs:
        axis.imshow(rgb)
        axis.set_title(label, fontsize=11)
        axis.set_xlim(0, rgb.shape[1])
        axis.set_ylim(rgb.shape[0], 0)
        axis.axis("off")
        if policy is not None:
            frame_shells = shells[
                (shells["frame_uid"].astype(str) == frame_uid)
                & (shells["temporal_policy"] == policy)
                & (shells["guard_variant"] == PRIMARY_GUARD)
            ]
            draw_shells(axis, frame, frame_shells)
            coverage_count = np.zeros(q95.shape, dtype=np.uint8)
            for shell in frame_shells.itertuples(index=False):
                coverage_count += inside_intervals(theta, json.loads(shell.effective_intervals_json)).astype(np.uint8)
            single_intersection = q95 & (coverage_count == 1)
            multi_intersection = q95 & (coverage_count >= 2)
            overlay = np.zeros((*q95.shape, 4), dtype=float)
            overlay[single_intersection] = (0.10, 0.85, 0.55, 0.22)
            overlay[multi_intersection] = (1.00, 0.30, 0.18, 0.30)
            axis.imshow(overlay)
            add_binary_contour(axis, q90, "#ffd166", 0.45, 0.50)
            add_binary_contour(axis, q95, "#58d6ff", 0.70, 0.72)
            add_binary_contour(axis, q975, "#ff5fa2", 0.85, 0.86)
            nodes = region_nodes[
                (region_nodes["frame_uid"].astype(str) == frame_uid)
                & (region_nodes["temporal_policy"] == policy)
                & (region_nodes["percentile_tag"] == "Q095")
            ]
            intersected = nodes[nodes["region_degree_shell_count"] > 0]
            multi_regions = intersected[intersected["region_degree_shell_count"] > 1]
            component_rows = components[
                (components["frame_uid"].astype(str) == frame_uid)
                & (components["temporal_policy"] == policy)
                & (components["percentile_tag"] == "Q095")
                & (components["shell_count"] > 0)
            ]
            states = Counter(component_rows["topology_state"].astype(str))
            axis.text(
                0.01,
                0.99,
                f"shell={len(frame_shells)} · q95相交region={len(intersected)} · 多shell覆盖region={len(multi_regions)}\n"
                f"component={dict(states)}",
                transform=axis.transAxes,
                va="top",
                ha="left",
                fontsize=8,
                color="white",
                bbox=dict(facecolor="#07111dcc", edgecolor="none", pad=3),
            )
            panel_metrics.append(
                {
                    "frame_uid": frame_uid,
                    "temporal_policy": policy,
                    "shell_count": int(len(frame_shells)),
                    "q95_intersected_region_count": int(len(intersected)),
                    "q95_multi_shell_region_count": int(len(multi_regions)),
                    "component_states": json.dumps(dict(states), ensure_ascii=False),
                }
            )
        for ref in refs.itertuples(index=False):
            axis.scatter(float(ref.x_px), float(ref.y_px), marker="x", s=70, linewidths=1.8, c="#ffffff", zorder=20)
            target = str(ref.target_id).replace(f"{frame['run_id']}_SARPERSON", "P")
            axis.text(float(ref.x_px) + 6, float(ref.y_px) - 6, target, color="white", fontsize=8, zorder=21,
                      bbox=dict(facecolor="#00000099", edgecolor="none", pad=1.5))
    fig.suptitle(title + "\n黄=q90弱支持外层 · 青=q95主区域 · 粉=q97.5强核心 · 绿=q95与1个shell相交 · 红=q95与≥2个shell相交", fontsize=14)
    path = VIS_DIR / f"case_{slug}.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return {"frame_uid": frame_uid, "case_slug": slug, "title": title, "image": f"visualizations/{path.name}", "panel_metrics": panel_metrics}


def build_fragmentation_summary() -> pd.DataFrame:
    hypotheses = pd.read_parquet(OPTICAL_HYPOTHESES)
    detected = hypotheses[
        hypotheses["run_id"].isin(["R01ZF", "R02ZF", "R03ZF", "R04ZF"])
        & hypotheses["box_source"].astype(str).eq("DETECTED")
    ].copy()
    parent_fragments = (
        detected.groupby(["run_id", "optical_person_id"])["raw_track_fragment_id"]
        .nunique()
        .reset_index(name="raw_fragment_count")
    )
    rows = []
    for run_id, group in detected.groupby("run_id", sort=True):
        parent = parent_fragments[parent_fragments["run_id"] == run_id]
        rows.append(
            {
                "run_id": run_id,
                "detected_row_count": int(len(group)),
                "raw_fragment_count": int(group["raw_track_fragment_id"].nunique()),
                "parent_stitched_id_count": int(group["optical_person_id"].nunique()),
                "parent_with_multiple_fragments_count": int((parent["raw_fragment_count"] > 1).sum()),
                "raw_fragments_per_parent_median": float(parent["raw_fragment_count"].median()),
                "raw_fragments_per_parent_max": int(parent["raw_fragment_count"].max()),
                "ambiguous_stitch_count_max": int(group["ambiguous_stitch_count"].max()),
                "rows_with_ambiguous_stitch": int((group["ambiguous_stitch_count"] > 0).sum()),
                "semantics": "PARENT_STITCHED_ID_IS_GT_BLIND_OFFLINE_CONTINUITY_PROVENANCE_NOT_RUNTIME_IDENTITY",
            }
        )
    return pd.DataFrame(rows)


def plot_shell_decomposition(frame_shells: pd.DataFrame, path: Path) -> None:
    rows = frame_shells[
        (frame_shells["run_id"] == "R02ZF")
        & (frame_shells["guard_variant"] == PRIMARY_GUARD)
        & frame_shells["temporal_policy"].isin(POLICY_ORDER)
        & frame_shells["track_shell_available"].astype(bool)
    ]
    values = []
    for policy in POLICY_ORDER:
        group = rows[rows["temporal_policy"] == policy]
        values.append(
            {
                "policy": policy,
                "box": finite_median(group["single_box_width_median_deg"]),
                "time": finite_median(group["temporal_union_increment_median_deg"]),
                "guard": finite_median(group["guard_increment_median_deg"]),
                "clip": finite_median(group["fan_clip_loss_median_deg"]),
            }
        )
    data = pd.DataFrame(values)
    x = np.arange(len(data))
    fig, axis = plt.subplots(figsize=(10, 5), constrained_layout=True)
    bottom = np.zeros(len(data))
    for column, label, color in [
        ("box", "代表性单框角宽", "#4f8cff"),
        ("time", "时间/视角 union 扩张", "#ffb14e"),
        ("guard", "固定 guard 实际增量", "#ef6f9f"),
    ]:
        axis.bar(x, data[column], bottom=bottom, label=label, color=color)
        bottom += data[column].to_numpy(float)
    axis.set_xticks(x, [POLICY_LABEL[p] for p in data["policy"]], rotation=12)
    axis.set_ylabel("角宽贡献（deg，R02 帧中位数）")
    axis.set_title("R02 optical shell 宽度不是一个来源：同帧主要由 guard，时间窗再额外扩张")
    axis.legend(ncol=3, fontsize=9)
    axis.grid(axis="y", alpha=0.2)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_guard_jaccard(pair_sep: pd.DataFrame, path: Path) -> None:
    subset = pair_sep[
        pair_sep["temporal_policy"].isin(["SAME_FRAME", "PAST_ONLY_250MS", "CENTERED_250MS"])
    ]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), constrained_layout=True, sharey=True)
    colors = {"SAME_FRAME": "#4f8cff", "PAST_ONLY_250MS": "#ffb14e", "CENTERED_250MS": "#ef6f9f"}
    for axis, pair_name in zip(axes, ["P01_P02", "P03_P04"]):
        pair = subset[subset["target_pair"] == pair_name]
        for policy in ["SAME_FRAME", "PAST_ONLY_250MS", "CENTERED_250MS"]:
            group = pair[pair["temporal_policy"] == policy].set_index("guard_variant")
            axis.plot(
                np.arange(3),
                [group.loc[tag, "associated_shell_angular_jaccard"] .median() for tag in GUARD_ORDER],
                marker="o",
                linewidth=2,
                color=colors[policy],
                label=POLICY_LABEL[policy],
            )
        axis.set_xticks(np.arange(3), ["±6°", "±2.652°", "0°下界"])
        axis.set_title(pair_name.replace("_", " / "))
        axis.set_ylim(-0.03, 0.85)
        axis.grid(alpha=0.25)
    axes[0].set_ylabel("离线一对一关联壳 Jaccard（中位数）")
    axes[1].legend(fontsize=9)
    fig.suptitle("同步与 guard 是两个独立来源：同帧 guard 可造成重叠，±250 ms union 在 0° guard 下仍可重叠")
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_retention_burden(frame_shells: pd.DataFrame, reference_eval: pd.DataFrame, path: Path) -> None:
    frames = frame_shells[
        (frame_shells["run_id"] == "R02ZF")
        & (frame_shells["guard_variant"] == PRIMARY_GUARD)
        & frame_shells["temporal_policy"].isin(POLICY_ORDER)
    ]
    refs = reference_eval[
        (reference_eval["run_id"] == "R02ZF")
        & (reference_eval["guard_variant"] == PRIMARY_GUARD)
        & reference_eval["temporal_policy"].isin(POLICY_ORDER)
    ]
    rows = []
    for policy in POLICY_ORDER:
        f = frames[frames["temporal_policy"] == policy]
        r = refs[refs["temporal_policy"] == policy]
        rows.append(
            {
                "policy": policy,
                "retention": r["any_shell_reference_retained"].astype(bool).mean(),
                "union_burden": f["all_track_union_effective_area_fraction_of_omega"].median(),
                "shell_count": f["active_raw_fragment_shell_count"].median(),
            }
        )
    data = pd.DataFrame(rows)
    fig, axis = plt.subplots(figsize=(8, 5.4), constrained_layout=True)
    axis.plot(data["union_burden"] * 100, data["retention"] * 100, color="#54cfa3", linewidth=1.5)
    for row in data.itertuples(index=False):
        axis.scatter(row.union_burden * 100, row.retention * 100, s=85)
        axis.text(row.union_burden * 100 + 0.4, row.retention * 100 + 0.25,
                  f"{POLICY_LABEL[row.policy]}\n壳数中位={row.shell_count:g}", fontsize=8)
    axis.set_xlabel("all-track union 搜索负担（Ω_single 面积中位数，%）")
    axis.set_ylabel("reference 被任一 raw shell 保留（%）")
    axis.set_title("延迟/时间不确定度的价值不是免费：retention 上升，同时 burden 与壳数上升")
    axis.grid(alpha=0.25)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_local_degree(region_nodes: pd.DataFrame, shell_nodes: pd.DataFrame, path: Path) -> None:
    rows = []
    for policy in ["SAME_FRAME", "PAST_ONLY_250MS", "CENTERED_250MS"]:
        region = region_nodes[
            (region_nodes["run_id"] == "R02ZF")
            & (region_nodes["percentile_tag"] == "Q095")
            & (region_nodes["temporal_policy"] == policy)
            & (region_nodes["region_degree_shell_count"] > 0)
        ]
        rows.append(
            {
                "policy": policy,
                "one": int((region["region_degree_shell_count"] == 1).sum()),
                "two": int((region["region_degree_shell_count"] == 2).sum()),
                "three_plus": int((region["region_degree_shell_count"] >= 3).sum()),
            }
        )
    data = pd.DataFrame(rows)
    fig, axis = plt.subplots(figsize=(9, 5), constrained_layout=True)
    x = np.arange(len(data))
    bottom = np.zeros(len(data))
    for column, label, color in [
        ("one", "region 仅被1个shell覆盖", "#54cfa3"),
        ("two", "region 被2个shell覆盖", "#ffb14e"),
        ("three_plus", "region 被≥3个shell覆盖", "#ef6f9f"),
    ]:
        axis.bar(x, data[column], bottom=bottom, label=label, color=color)
        bottom += data[column].to_numpy(float)
    axis.set_xticks(x, [POLICY_LABEL[p] for p in data["policy"]])
    axis.set_ylabel("R02 q95 与至少一个 shell 相交的 region 数")
    axis.set_title("局部 degree 比连通分量标签更直接：多数 R02 q95 region 同时落入多个 optical shells")
    axis.legend(fontsize=9)
    axis.grid(axis="y", alpha=0.2)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_fragmentation_clipping(fragmentation: pd.DataFrame, shells: pd.DataFrame, path: Path) -> None:
    clip_rows = []
    base = shells[(shells["temporal_policy"] == "SAME_FRAME") & (shells["guard_variant"] == PRIMARY_GUARD)]
    for run_id, group in base.groupby("run_id", sort=True):
        clip_rows.append(
            {
                "run_id": run_id,
                "fan_clip_fraction": float((group["fan_clip_loss_deg"] > 1e-9).mean()),
                "outside_common_fraction": float((group["effective_width_outside_common_fov_deg"] > 1e-9).mean()),
            }
        )
    clip = pd.DataFrame(clip_rows).set_index("run_id")
    data = fragmentation.set_index("run_id").join(clip).reset_index()
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.7), constrained_layout=True)
    x = np.arange(len(data))
    axes[0].bar(x - 0.18, data["raw_fragment_count"], 0.36, label="raw fragments", color="#4f8cff")
    axes[0].bar(x + 0.18, data["parent_stitched_id_count"], 0.36, label="offline parent IDs", color="#54cfa3")
    axes[0].set_xticks(x, data["run_id"])
    axes[0].set_title("fragmentation provenance（parent 不是 runtime identity）")
    axes[0].legend(fontsize=9)
    axes[0].grid(axis="y", alpha=0.2)
    axes[1].bar(x - 0.18, data["fan_clip_fraction"] * 100, 0.36, label="SAR fan clipping", color="#ef6f9f")
    axes[1].bar(x + 0.18, data["outside_common_fraction"] * 100, 0.36, label="部分超出 provisional common-FoV", color="#ffb14e")
    axes[1].set_xticks(x, data["run_id"])
    axes[1].set_ylabel("same-frame shell 比例（%）")
    axes[1].set_title("clipping 是条件变量，不自动等于 response absent")
    axes[1].legend(fontsize=9)
    axes[1].grid(axis="y", alpha=0.2)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def table_html(frame: pd.DataFrame, columns: list[tuple[str, str]], max_rows: int | None = None) -> str:
    data = frame.head(max_rows) if max_rows else frame
    header = "".join(f"<th>{html.escape(label)}</th>" for _, label in columns)
    rows = []
    for record in data.to_dict("records"):
        cells = []
        for key, _ in columns:
            value = record.get(key, "")
            cells.append(f"<td>{html.escape(str(value))}</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return f"<div class='table-wrap'><table><thead><tr>{header}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    VIS_DIR.mkdir(parents=True, exist_ok=True)
    analysis = load_module("person_shell_topology_report_analysis", ANALYSIS_SCRIPT)
    previous = load_module("person_shell_topology_report_previous", PREVIOUS_SCRIPT)
    frames, _ = previous.load_explorer_sanitized()
    frame_map = {str(frame["sar_frame_uid"]): frame for frame in frames}

    summary = json.loads(SUMMARY_JSON.read_text(encoding="utf-8"))
    shells = pd.read_csv(SHELLS_CSV)
    frame_shells = pd.read_csv(FRAME_SHELLS_CSV)
    pair_sep = pd.read_csv(PAIR_SEP_CSV)
    reference_eval = pd.read_csv(REFERENCE_EVAL_CSV)
    components = pd.read_csv(COMPONENTS_CSV)
    shell_nodes = pd.read_csv(SHELL_NODES_CSV)
    region_nodes = pd.read_csv(REGION_NODES_CSV)
    reference_topology = pd.read_csv(REFERENCE_TOPOLOGY_CSV)
    observations = pd.read_csv(
        OBSERVATION_CSV,
        usecols=["entity_kind", "run_id", "frame_uid", "frame_index", "target_id", "x_px", "y_px"],
    )
    references = observations[observations["entity_kind"].astype(str).eq("PERSON_REFERENCE")].drop_duplicates(
        ["run_id", "frame_uid", "target_id"]
    )

    fragmentation = build_fragmentation_summary()
    fragmentation.to_csv(OUTPUT_DIR / "optical_fragmentation_summary.csv", index=False, encoding="utf-8-sig")

    plot_shell_decomposition(frame_shells, VIS_DIR / "r02_shell_width_decomposition.png")
    plot_guard_jaccard(pair_sep, VIS_DIR / "r02_guard_time_jaccard.png")
    plot_retention_burden(frame_shells, reference_eval, VIS_DIR / "r02_latency_retention_burden.png")
    plot_local_degree(region_nodes, shell_nodes, VIS_DIR / "r02_q95_local_region_degree.png")
    plot_fragmentation_clipping(fragmentation, shells, VIS_DIR / "fragmentation_and_clipping.png")

    case_registry = []
    for frame_uid, slug, title in CASE_SPECS:
        if frame_uid not in frame_map:
            continue
        case_registry.append(
            render_case(frame_map[frame_uid], title, slug, shells, region_nodes, references, components)
        )
    pd.DataFrame(
        [{"frame_uid": row["frame_uid"], "case_slug": row["case_slug"], "title": row["title"], "image": row["image"]} for row in case_registry]
    ).to_csv(OUTPUT_DIR / "case_registry.csv", index=False, encoding="utf-8-sig")

    r02_decomp_rows = []
    r02_ref_rows = []
    for policy in POLICY_ORDER:
        f = frame_shells[
            (frame_shells["run_id"] == "R02ZF")
            & (frame_shells["guard_variant"] == PRIMARY_GUARD)
            & (frame_shells["temporal_policy"] == policy)
        ]
        available = f[f["track_shell_available"].astype(bool)]
        r = reference_eval[
            (reference_eval["run_id"] == "R02ZF")
            & (reference_eval["guard_variant"] == PRIMARY_GUARD)
            & (reference_eval["temporal_policy"] == policy)
        ]
        r02_decomp_rows.append(
            {
                "policy": POLICY_LABEL[policy],
                "box": fmt(finite_median(available["single_box_width_median_deg"]), 2),
                "time": fmt(finite_median(available["temporal_union_increment_median_deg"]), 2),
                "guard": fmt(finite_median(available["guard_increment_median_deg"]), 2),
                "track_width": fmt(finite_median(available["single_track_width_median_deg"]), 2),
                "active_shells": fmt(finite_median(available["active_raw_fragment_shell_count"]), 1),
                "union_burden": pct(finite_median(available["all_track_union_effective_area_fraction_of_omega"])),
                "retention": pct(r["any_shell_reference_retained"].astype(bool).mean()),
            }
        )
        r02_ref_rows.append(r)
    decomp_table = pd.DataFrame(r02_decomp_rows)

    guard_table_rows = []
    for guard in GUARD_ORDER:
        same_ref = reference_eval[
            (reference_eval["run_id"] == "R02ZF")
            & (reference_eval["temporal_policy"] == "SAME_FRAME")
            & (reference_eval["guard_variant"] == guard)
        ]
        same_frame = frame_shells[
            (frame_shells["run_id"] == "R02ZF")
            & (frame_shells["temporal_policy"] == "SAME_FRAME")
            & (frame_shells["guard_variant"] == guard)
        ]
        row = {"guard": GUARD_LABEL[guard], "retention": pct(same_ref["any_shell_reference_retained"].astype(bool).mean()),
               "union_burden": pct(same_frame["all_track_union_effective_area_fraction_of_omega"].median())}
        for pair_name in ["P01_P02", "P03_P04"]:
            pair = pair_sep[
                (pair_sep["target_pair"] == pair_name)
                & (pair_sep["temporal_policy"] == "SAME_FRAME")
                & (pair_sep["guard_variant"] == guard)
                & pair_sep["both_associated_shells_available"].astype(bool)
            ]
            row[pair_name] = fmt(pair["associated_shell_angular_jaccard"].median(), 3)
            row[pair_name + "_n"] = f"{len(pair)}/9"
        guard_table_rows.append(row)
    guard_table = pd.DataFrame(guard_table_rows)

    degree_rows = []
    for policy in ["SAME_FRAME", "PAST_ONLY_250MS", "CENTERED_250MS"]:
        nodes = region_nodes[
            (region_nodes["run_id"] == "R02ZF")
            & (region_nodes["percentile_tag"] == "Q095")
            & (region_nodes["temporal_policy"] == policy)
            & (region_nodes["region_degree_shell_count"] > 0)
        ]
        degree_rows.append(
            {
                "policy": POLICY_LABEL[policy],
                "intersected": len(nodes),
                "degree1": int((nodes["region_degree_shell_count"] == 1).sum()),
                "degree2": int((nodes["region_degree_shell_count"] == 2).sum()),
                "degree3plus": int((nodes["region_degree_shell_count"] >= 3).sum()),
                "multi_fraction": pct((nodes["region_degree_shell_count"] >= 2).mean()),
            }
        )
    degree_table = pd.DataFrame(degree_rows)

    shared_rows = []
    shared = reference_topology[
        (reference_topology["run_id"] == "R02ZF")
        & (reference_topology["percentile_tag"] == "Q095")
        & reference_topology["shared_region_flag"].astype(bool)
    ]
    for policy in ["SAME_FRAME", "PAST_ONLY_250MS", "CENTERED_250MS"]:
        group = shared[shared["temporal_policy"] == policy]
        shared_rows.append(
            {
                "policy": POLICY_LABEL[policy],
                "shared_ref_rows": len(group),
                "no_shell": int((group["region_degree_shell_count"].fillna(0) == 0).sum()),
                "one_shell": int((group["region_degree_shell_count"] == 1).sum()),
                "multi_shell": int((group["region_degree_shell_count"] >= 2).sum()),
                "component_multi_multi": int((group["topology_state"] == "MULTIPLE_SHELLS_MULTIPLE_REGIONS").sum()),
            }
        )
    shared_table = pd.DataFrame(shared_rows)

    f_cases = reference_topology[
        (reference_topology["run_id"] == "R02ZF")
        & reference_topology["frame_index"].isin([482, 490])
        & (reference_topology["percentile_tag"] == "Q095")
        & reference_topology["temporal_policy"].isin(["SAME_FRAME", "CENTERED_250MS"])
    ].copy()
    f_cases["person"] = f_cases["target_id"].str.extract(r"PERSON(\d+)")[0].map(lambda x: f"P{int(x):02d}" if pd.notna(x) else "")
    f_cases["policy_cn"] = f_cases["temporal_policy"].map(POLICY_LABEL)
    f_cases["region_degree"] = f_cases["region_degree_shell_count"].fillna(0).astype(int)
    f_cases["component"] = f_cases["topology_state"].fillna("REGION_NO_SHELL")

    derived = {
        "status": summary["status"],
        "r02_same_frame_current": {
            "single_box_width_median_deg": float(decomp_table.iloc[0]["box"]),
            "guard_increment_median_deg": float(decomp_table.iloc[0]["guard"]),
            "retention": float(reference_eval[(reference_eval.run_id == "R02ZF") & (reference_eval.temporal_policy == "SAME_FRAME") & (reference_eval.guard_variant == PRIMARY_GUARD)].any_shell_reference_retained.astype(bool).mean()),
        },
        "guard_table": guard_table.to_dict("records"),
        "degree_table": degree_table.to_dict("records"),
        "shared_table": shared_table.to_dict("records"),
        "case_count": len(case_registry),
        "component_state_absences": {
            "MULTIPLE_SHELLS_ONE_REGION_component": int((components.topology_state == "MULTIPLE_SHELLS_ONE_REGION").sum()),
            "SHELL_NO_REGION_component": int((components.topology_state == "SHELL_NO_REGION").sum()),
        },
        "analysis_script_sha256": analysis.sha256_file(ANALYSIS_SCRIPT),
    }
    (OUTPUT_DIR / "report_derived_metrics.json").write_text(
        json.dumps(analysis.json_safe(derived), ensure_ascii=False, indent=2), encoding="utf-8"
    )

    cards = [
        ("同帧壳宽来源", "2.69° 单框 + 12° guard", "R02 中位；同步理想化后 guard 仍主导宽度"),
        ("居中窗新增扩张", "+6.91°", "R02 centered ±250 ms 的时间/视角 union 中位增量"),
        ("同帧壳 Jaccard", "0.635 / 0.517", "P01/P02；P03/P04（后者仅 4/9 帧双壳可关联）"),
        ("q95 局部多壳覆盖", "82.1% → 87.3%", "R02 same-frame → centered；在已与壳相交的 region 内"),
    ]
    card_html = "".join(
        f"<div class='metric'><div class='metric-label'>{html.escape(label)}</div><div class='metric-value'>{value}</div><div class='metric-note'>{html.escape(note)}</div></div>"
        for label, value, note in cards
    )
    case_html = "".join(
        f"<figure><img src='{html.escape(case['image'])}' alt='{html.escape(case['title'])}'><figcaption>{html.escape(case['title'])}</figcaption></figure>"
        for case in case_registry
    )

    report = f"""<!doctype html>
<html lang='zh-CN'>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<title>PERSON P1E · 光学方位壳不确定度与 SAR response-region 拓扑</title>
<style>
:root{{--bg:#07111d;--panel:#0e1d2b;--panel2:#122538;--text:#edf6ff;--muted:#9cb2c5;--line:#29445b;--green:#54cfa3;--orange:#ffb14e;--pink:#ef6f9f;--blue:#58b8ff}}
*{{box-sizing:border-box}} body{{margin:0;background:linear-gradient(135deg,#06101a,#0a1725 46%,#08131f);color:var(--text);font-family:"Microsoft YaHei","Noto Sans SC",sans-serif;line-height:1.68}}
main{{max-width:1240px;margin:0 auto;padding:34px 24px 64px}} h1{{font-size:34px;line-height:1.25;margin:0 0 10px}} h2{{margin-top:42px;padding-top:10px;border-top:1px solid var(--line)}} h3{{margin-top:28px}} p,li{{color:#d5e4ef}} .lead{{font-size:18px;color:#cce4f5;max-width:1020px}}
.status{{display:inline-block;padding:6px 11px;border:1px solid #4b7693;border-radius:999px;color:#bfe8ff;background:#102a3d;margin-bottom:16px}}
.metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:22px 0}} .metric{{background:linear-gradient(160deg,var(--panel2),var(--panel));border:1px solid var(--line);border-radius:14px;padding:16px}} .metric-label{{color:var(--muted);font-size:13px}} .metric-value{{font-size:24px;font-weight:700;color:var(--green);margin:4px 0}} .metric-note{{font-size:12px;color:var(--muted)}}
.callout{{border-left:4px solid var(--orange);background:#132334;padding:16px 18px;border-radius:8px;margin:18px 0}} .negative{{border-left-color:var(--pink)}} .good{{border-left-color:var(--green)}}
.formula{{font-family:Consolas,monospace;background:#06101a;border:1px solid var(--line);padding:14px;border-radius:10px;overflow:auto;color:#b9e4ff}}
.figure-grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}} figure{{margin:0;background:var(--panel);border:1px solid var(--line);padding:10px;border-radius:12px}} figure img{{width:100%;display:block;border-radius:7px}} figcaption{{font-size:13px;color:var(--muted);padding:8px 4px 2px}}
.wide-fig{{background:var(--panel);border:1px solid var(--line);padding:12px;border-radius:12px;margin:18px 0}} .wide-fig img{{width:100%;display:block;border-radius:8px}}
.table-wrap{{overflow:auto;border:1px solid var(--line);border-radius:10px;margin:12px 0 20px}} table{{border-collapse:collapse;width:100%;min-width:760px;background:#0b1825}} th,td{{padding:10px 11px;border-bottom:1px solid #20384b;text-align:left;font-size:13px}} th{{position:sticky;top:0;background:#14293b;color:#cceaff}} td{{color:#d7e5ef}}
.semantic-grid{{display:grid;grid-template-columns:1fr 1fr;gap:14px}} .semantic-grid>div{{background:var(--panel);border:1px solid var(--line);padding:15px;border-radius:10px}} code{{color:#9edcff}} a{{color:#6dc8ff}} .footer{{color:var(--muted);font-size:13px;margin-top:42px}}
@media(max-width:900px){{.metrics{{grid-template-columns:repeat(2,1fr)}}.figure-grid,.semantic-grid{{grid-template-columns:1fr}}}} @media(max-width:560px){{main{{padding:24px 14px}}h1{{font-size:27px}}.metrics{{grid-template-columns:1fr}}}}
</style>
</head>
<body><main>
<div class='status'>本轮状态：COMPLETE_NO_NEW_PASS_FAIL_NO_P2_CLAIM</div>
<h1>光学方位壳的不确定度由什么组成？<br>它与 SAR response-region 已形成什么 GT-blind 结构？</h1>
<p class='lead'>结论先说：当前多人 shell 未分离不是单一同步问题。同帧理想化后，R02 每个检测框映射角宽中位约 2.69°，但固定 guard 直接增加 12°；而 centered ±250 ms 又额外引入约 6.91° 的时间/视角 union。另一方面，shell 与 q90/q95/q97.5 response regions 已能形成稳定、可运行时计算的二部关系，但它主要表达搜索歧义与共享，不是 PERSON identity 或最终定位。</p>
<div class='metrics'>{card_html}</div>

<div class='callout good'><b>这轮建立了两个清楚接口。</b> optical shell 可以拆出宽度来源和 latency/burden 代价；SAR region 可以用像素级相交形成局部 degree 与二部连通分量。两者都不需要人工 ID 或 SAR reference 才能生成。</div>
<div class='callout negative'><b>这轮没有建立 P2。</b> 所有 run 仍是开发语料；q95 region 不是 PERSON box；offline one-to-one assignment 只是解释工具；没有生成 range、box、总分或 tracker。</div>

<h2>1. 方位壳宽度：guard 与时间 union 是两个独立来源</h2>
<div class='formula'>W_effective = W_single_box + ΔW_time/view + ΔW_guard − ΔW_fan_clip</div>
<p>这里的 mapping 先把 optical box 的横向跨度转成角跨度。纯 intercept 修正只能整体平移壳，不会让 optical box 自身变窄；只有 mapping uncertainty 被独立验证后，才可能合理缩小 guard。</p>
<div class='wide-fig'><img src='visualizations/r02_shell_width_decomposition.png' alt='R02 shell width decomposition'></div>
{table_html(decomp_table, [("policy","时间策略"),("box","单框角宽°"),("time","时间/视角增量°"),("guard","guard增量°"),("track_width","单track壳宽°"),("active_shells","活动raw壳数"),("union_burden","union负担"),("retention","reference retention")])}

<h3>1.1 “理想同帧”后还剩多少不可分性？</h3>
<p>在当前 ±6° guard 下，同帧 associated-shell Jaccard 仍为 P01/P02 <b>0.635</b>、P03/P04 <b>0.517</b>。因此不能把同帧不可分性简单归因于同步。把 guard 改成既有 R04 nominal-zero macro MAE 量级的 ±2.652° 几何敏感性后，Jaccard 降到约 0.415/0.325；raw-box 0° 下界进一步降到 0/0.025，但 retention 也明显下降，而且 0° 并不是可部署壳。</p>
<div class='wide-fig'><img src='visualizations/r02_guard_time_jaccard.png' alt='guard and time jaccard'></div>
{table_html(guard_table, [("guard","同帧 guard 版本"),("retention","reference retention"),("union_burden","union负担"),("P01_P02","P01/P02 Jaccard"),("P01_P02_n","有效帧"),("P03_P04","P03/P04 Jaccard"),("P03_P04_n","有效帧")])}
<p class='callout'><b>解释：</b>同帧重叠主要由当前 guard 扩张造成；但这不等于应直接缩 guard。±2.652° 与 0° 都是预先固定的几何反事实，不是通过 reference 调出来的新 mapping。</p>

<h3>1.2 不改变同步、只看时间策略的代价</h3>
<div class='wide-fig'><img src='visualizations/r02_latency_retention_burden.png' alt='latency retention burden'></div>
<p>R02 从 same-frame 到 past-only 250 ms，retention 约 83.3%→91.7%，union burden 约 28.3%→29.0%；固定允许 +100 ms 延迟可达到与 centered ±250 ms 相同的 94.4% retention，但 union burden 约 29.8%，低于 centered 的 31.9%。这是描述性 latency–uncertainty–burden 关系，不是最优窗口选择。</p>
<p>更关键的是：centered ±250 ms 即使使用 0° guard 下界，P01/P02 与 P03/P04 Jaccard 仍约 0.492/0.505。说明时间窗 union 本身会重新制造重叠，不能靠“更准同步”与“更小 guard”只讨论其中一个。</p>

<h3>1.3 raw fragment availability 与 clipping</h3>
<div class='wide-fig'><img src='visualizations/fragmentation_and_clipping.png' alt='fragmentation and clipping'></div>
{table_html(fragmentation.assign(raw_fragments_per_parent_median=fragmentation.raw_fragments_per_parent_median.map(lambda x: fmt(x,1))), [("run_id","run"),("raw_fragment_count","raw fragments"),("parent_stitched_id_count","offline parent IDs"),("parent_with_multiple_fragments_count","多fragment parent"),("raw_fragments_per_parent_median","fragment/parent中位"),("raw_fragments_per_parent_max","最大"),("ambiguous_stitch_count_max","ambiguous最大")])}
<p>R02 有 33 个 raw fragments、14 个 offline parent continuity IDs，7 个 parent 含多个 fragment，单个 parent 最多 10 个 fragments。same-frame 每帧活动 raw 壳中位只有 3 个，而离线 R02 reference 有 4 人；P03/P04 两条 distinct associated shells 同时可用仅 4/9 帧，centered 后为 7/9。这里的瓶颈既有宽度重叠，也有 runtime fragment 可用性。</p>

<h2>2. shell ↔ response-region：已经建立的是“歧义拓扑”</h2>
<p>本轮没有再使用粗角包围盒相交。每条 edge 都来自真实像素：region 中有多少像素落在 shell 内、占 region 多少、占 shell 多少，并保留交叠的 range/azimuth 跨度。</p>
<div class='wide-fig'><img src='visualizations/r02_q95_local_region_degree.png' alt='R02 q95 local degree'></div>
{table_html(degree_table, [("policy","策略"),("intersected","与壳相交q95 region"),("degree1","被1壳覆盖"),("degree2","被2壳覆盖"),("degree3plus","被≥3壳覆盖"),("multi_fraction","多壳覆盖比例")])}
<p>在 R02 中，same-frame 已与至少一个壳相交的 257 个 q95 regions 里，211 个同时落入 ≥2 个 shells（82.1%）；centered 时为 268/307（87.3%）。所以“多个 optical shells → 同一个 SAR region”是可 GT-blind 直接计算的局部状态。</p>

<div class='callout'><b>为什么完整连通分量里没有 <code>MULTIPLE_SHELLS_ONE_REGION</code>？</b> 不是因为多壳共享 region 不存在，而是这些 shell 同时还会碰到其它 regions，连通分量会扩展成 <code>MULTIPLE_SHELLS_MULTIPLE_REGIONS</code>。因此报告同时保留 component topology 与更直接的 region/shell local degree。</div>
<div class='callout negative'><b>为什么没有 <code>SHELL_NO_REGION</code>？</b> q90/q95/q97.5 是每帧分位超水平层，每个当前 shell 至少会碰到某个 region。这只表示壳内存在相对高响应，不表示壳内存在 PERSON。相反，full fan 中大量 <code>REGION_NO_SHELL</code> 只是光学先验排除了这些方位。</div>

<h3>2.1 旧 q95 shared=94.4% 对应什么拓扑？</h3>
{table_html(shared_table, [("policy","策略"),("shared_ref_rows","R02 shared reference行"),("no_shell","region无shell"),("one_shell","region被1壳覆盖"),("multi_shell","region被多壳覆盖"),("component_multi_multi","multi-shell/multi-region component")])}
<p>same-frame 的 34 条 R02 q95 shared reference 中，24 条所属 region 被 ≥2 个 shells 覆盖；centered 时为 30/34，且 34/34 都进入 multi-shell/multi-region 连通分量。粗光学壳减少全扇面搜索，却没有解决 P03/P04 的 SAR 局部共享。</p>

<h3>2.2 哪些状态可运行时直接计算，哪些仍依赖 reference？</h3>
<div class='semantic-grid'>
<div><b>GT-blind 可计算</b><ul><li>q90/q95/q97.5 region level 与 compact/extended-ridge shape</li><li>shell/region 像素相交、local degree、component topology</li><li>edge/truncated/common-FoV/display 条件</li><li>旧 candidate artifact 覆盖帧内的 accepted peak-in-region</li></ul></div>
<div><b>只能 reference-conditioned 离线解释</b><ul><li><code>PEAK_PRESENT</code> / <code>PEAK_MISSING_REGION_PRESENT</code></li><li>PERSON <code>SHARED_REGION</code></li><li>reference retention、rank、P01/P02/P03/P04 归因</li><li>offline one-to-one associated shell</li></ul></div>
</div>
<p>旧 candidate artifact 未覆盖的 272/398 帧仍标为 peak artifact unavailable，绝不解释为 peak absent。P0 条件也只用 GT-blind C2 candidate 采样；无样本处标记 unavailable，不用 reference 补值。</p>

<h2>3. 直接病例：看原图、嵌套 region、shell 与局部 degree</h2>
<p>病例图中，白色叉号是运行完成后才叠加的 manual reference。绿色表示 q95 像素只被一个 shell 覆盖，红色表示同一 q95 像素被多个 shells 覆盖；这比只看 component 名称更直接。</p>
<div class='figure-grid'>{case_html}</div>

<h3>3.1 F482 / F490 的语义没有退回 peak missing</h3>
{table_html(f_cases[["frame_index","person","policy_cn","representation_state","shared_region_flag","nearest_region_id","region_degree","component"]], [("frame_index","帧"),("person","reference"),("policy_cn","策略"),("representation_state","离线表示状态"),("shared_region_flag","shared"),("nearest_region_id","q95 region"),("region_degree","覆盖shell数"),("component","连通分量")], max_rows=24)}
<p>F482 P01/P02 同落在 q95 R0012；P02 是 <code>PEAK_MISSING_REGION_PRESENT</code>，但该 region same-frame 已被 2 个 shells 覆盖、centered 被 3 个 shells 覆盖。F490 P01/P02 同落在 R0012，P02 同样是 peak-missing-region-present，region degree 为 3。它们证明“离散峰缺失”不是“连续响应缺失”，也说明 region presence 本身仍不能完成身份分离。</p>

<h2>4. 本轮对两个核心问题的回答</h2>
<ol>
<li><b>光学方位不确定度由什么组成？</b> 单框角跨度较窄；当前 ±6° guard 是同帧宽度的最大固定来源；past/buffered/centered 的时间 union 再引入独立扩张；raw fragment 可用性限制每帧可形成多少独立壳；fan/common-FoV clipping 主要是跨 run/边界条件，R02 本身没有 fan clipping。</li>
<li><b>不看 GT 时已经形成什么结构？</b> 可以形成 shell nodes、nested response-region nodes、真实像素 edges、local degree 与二部连通分量。R02 的主导状态不是“一个壳对应一个 region”，而是一个壳含多个 regions、同一 region 又被多个 shells 覆盖的多对多歧义。</li>
</ol>
<div class='callout good'><b>最有价值的下一步不是增加 C4/C5。</b> 若继续，应先改善可验证的 runtime optical continuity/synchronization/mapping uncertainty，再用相同 topology 接口观察 degree 与 burden 是否下降。只有 single-frame topology 更清楚后，才值得做冻结 P0 的 region continue/split/merge-like 极小时序传播。</div>
<div class='callout negative'><b>本轮停止点：</b> 不进入 P2，不生成 SAR range/box，不实现复杂 region tracker，不把 image/P0/optical 维度相加成总分。</div>

<h2>5. 复现与数据入口</h2>
<ul>
<li><a href='00_SHELL_UNCERTAINTY_REGION_TOPOLOGY_PROTOCOL_FROZEN_BEFORE_RUN.md'>冻结协议</a></li>
<li><a href='diagnostic_summary.json'>机器可读诊断摘要</a></li>
<li><a href='optical_shell_uncertainty_decomposition_pre_reference.csv'>逐 shell 不确定度分解</a></li>
<li><a href='gt_blind_shell_region_pixel_edges_pre_reference.csv'>像素级 shell-region edges</a></li>
<li><a href='gt_blind_bipartite_components_pre_reference.csv'>GT-blind 二部连通分量</a></li>
<li><a href='offline_reference_region_topology_interpretation.csv'>reference-conditioned 后置解释</a></li>
<li><a href='case_registry.csv'>病例注册表</a></li>
</ul>
<p class='footer'>解释边界：PERSON 特征仍是目标、场景、载体、成像处理与显示链共同形成的条件性图像域响应；公共表观输运不是真实载体轨迹；RGB/JET 不作为独立雷达物理通道；SAR 保留 range 与最终定位权。</p>
</main></body></html>"""
    HTML_PATH.write_text(report, encoding="utf-8")
    print(json.dumps({"html": str(HTML_PATH), "cases": len(case_registry), "figures": 5 + len(case_registry)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
