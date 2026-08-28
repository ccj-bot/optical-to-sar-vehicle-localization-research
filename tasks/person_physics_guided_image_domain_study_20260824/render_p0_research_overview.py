#!/usr/bin/env python3
"""Render a theory-to-evidence overview of the completed P0 study.

Visualization only: this script reads frozen outputs and does not refit models.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


WORKSPACE = Path(r"D:\profile\research\workspace")
P0_ROOT = (
    WORKSPACE
    / "output"
    / "person_physics_guided_image_domain_study_20260824"
    / "p0_common_apparent_motion"
)
VIS_DIR = P0_ROOT / "visualizations"
OUTPUT_PATH = VIS_DIR / "P0_RESEARCH_OVERVIEW.png"
FONT_PATH = Path(r"C:\Windows\Fonts\msyh.ttc")


def setup_font() -> None:
    if FONT_PATH.is_file():
        font = fm.FontProperties(fname=str(FONT_PATH))
        plt.rcParams["font.family"] = font.get_name()
    plt.rcParams["axes.unicode_minus"] = False


def panel(ax, title: str) -> None:
    ax.set_facecolor("#ffffff")
    for spine in ax.spines.values():
        spine.set_color("#d9dee8")
        spine.set_linewidth(1.0)
    ax.set_title(title, loc="left", fontsize=15, fontweight="bold", color="#172033", pad=10)


def rounded_text(ax, xy, width, height, text, face, edge="#c8d0df", fontsize=11) -> None:
    box = FancyBboxPatch(
        xy,
        width,
        height,
        boxstyle="round,pad=0.015,rounding_size=0.025",
        facecolor=face,
        edgecolor=edge,
        linewidth=1.2,
        transform=ax.transAxes,
    )
    ax.add_patch(box)
    ax.text(
        xy[0] + width / 2,
        xy[1] + height / 2,
        text,
        ha="center",
        va="center",
        fontsize=fontsize,
        color="#172033",
        transform=ax.transAxes,
        linespacing=1.35,
    )


def main() -> None:
    setup_font()
    VIS_DIR.mkdir(parents=True, exist_ok=True)
    freeze = json.loads((P0_ROOT / "model_selection_R01.json").read_text(encoding="utf-8"))
    final = json.loads((P0_ROOT / "frozen_validation_R04.json").read_text(encoding="utf-8"))
    q = final["quantitative_validation"]

    lag_rows = q["background_holdout"]["by_lag"]
    lags = [int(row["lag"]) for row in lag_rows]
    m0_values = [float(row["M0_holdout_pair_median_px"]) for row in lag_rows]
    selected_values = [float(row["selected_holdout_pair_median_px"]) for row in lag_rows]
    selected_names = [str(row["selected_model"]) for row in lag_rows]
    improvement = [float(row["improvement_fraction_vs_M0"]) for row in lag_rows]
    all_person = q["stationary_PERSON"]["all_accepted"]
    manual_person = q["stationary_PERSON"]["manual_endpoints"]
    short_axis = float(q["stationary_PERSON"]["short_axis_median_px_unique_R04_boxes"])

    fig = plt.figure(figsize=(19, 13), facecolor="#f3f5f9")
    grid = fig.add_gridspec(4, 12, height_ratios=[0.75, 1.8, 2.7, 3.2], hspace=0.38, wspace=0.42)

    title_ax = fig.add_subplot(grid[0, :])
    title_ax.axis("off")
    title_ax.text(
        0.0,
        0.78,
        "PERSON P0：SAR伪彩图像域公共表观运动可观测性",
        fontsize=25,
        fontweight="bold",
        color="#111827",
        transform=title_ax.transAxes,
    )
    title_ax.text(
        0.0,
        0.30,
        "研究问题：只看不含PERSON的SAR背景，能否估计公共图像输运，并在完全留出的R04中把静止PERSON框残差压到目标尺度以内？",
        fontsize=14,
        color="#334155",
        transform=title_ax.transAxes,
    )
    title_ax.text(
        1.0,
        0.76,
        "P0_PASS",
        ha="right",
        fontsize=25,
        fontweight="bold",
        color="#087f5b",
        transform=title_ax.transAxes,
    )
    title_ax.text(
        1.0,
        0.30,
        "图像域方法资格通过；P1 未启动",
        ha="right",
        fontsize=13,
        color="#087f5b",
        transform=title_ax.transAxes,
    )

    theory_ax = fig.add_subplot(grid[1, :5])
    panel(theory_ax, "1. 理论上分解什么")
    theory_ax.set_xticks([])
    theory_ax.set_yticks([])
    theory_ax.text(
        0.04,
        0.78,
        r"$\Delta c_{i,t,\ell}=u_{t,\ell}(c_{i,t})+v_{i,t,\ell}+\epsilon_{display}+\epsilon_{ann}$",
        fontsize=16,
        color="#111827",
        transform=theory_ax.transAxes,
    )
    theory_ax.text(
        0.04,
        0.55,
        "框位移 = 公共场景表观运动 + PERSON相对残差 + 显示/标注误差",
        fontsize=12.5,
        color="#334155",
        transform=theory_ax.transAxes,
    )
    theory_ax.text(
        0.04,
        0.31,
        r"背景留出残差：$e^B=\|d_k-\hat u(x_k)\|_2$",
        fontsize=14,
        color="#111827",
        transform=theory_ax.transAxes,
    )
    theory_ax.text(
        0.04,
        0.13,
        r"静止PERSON残差：$e^P=\|\Delta c-\hat u(c_t)\|_2$",
        fontsize=14,
        color="#111827",
        transform=theory_ax.transAxes,
    )

    flow_ax = fig.add_subplot(grid[1, 5:])
    panel(flow_ax, "2. 实操怎样计算")
    flow_ax.set_xlim(0, 1)
    flow_ax.set_ylim(0, 1)
    flow_ax.set_xticks([])
    flow_ax.set_yticks([])
    steps = [
        ("有效扇面\n+ PERSON排除", "#e0f2fe"),
        ("RGB梯度表征\n背景锚点追踪", "#e0e7ff"),
        ("拟合 M0–M3\n拟合/留出分离", "#ede9fe"),
        ("R01选型冻结\n不看PERSON残差", "#fef3c7"),
        ("R04直接验证\n不重新调参", "#dcfce7"),
        ("背景+PERSON\n尺度门槛", "#d1fae5"),
    ]
    width = 0.135
    gap = 0.025
    start_x = 0.025
    for idx, (text, color) in enumerate(steps):
        x = start_x + idx * (width + gap)
        rounded_text(flow_ax, (x, 0.34), width, 0.36, text, color, fontsize=10.5)
        if idx < len(steps) - 1:
            arrow = FancyArrowPatch(
                (x + width + 0.003, 0.52),
                (x + width + gap - 0.003, 0.52),
                arrowstyle="-|>",
                mutation_scale=12,
                linewidth=1.3,
                color="#64748b",
                transform=flow_ax.transAxes,
            )
            flow_ax.add_patch(arrow)

    bg_ax = fig.add_subplot(grid[2, :7])
    panel(bg_ax, "3. R04背景留出：M0 与冻结模型")
    x = np.arange(len(lags))
    bar_width = 0.34
    bars_m0 = bg_ax.bar(x - bar_width / 2, m0_values, bar_width, label="M0 无补偿", color="#94a3b8")
    bars_selected = bg_ax.bar(x + bar_width / 2, selected_values, bar_width, label="冻结模型", color="#2563eb")
    bg_ax.set_xticks(x, [f"lag {lag}\n{selected_names[idx]}" for idx, lag in enumerate(lags)])
    bg_ax.set_ylabel("帧对背景留出锚点残差中位数 / px")
    bg_ax.grid(axis="y", alpha=0.22)
    bg_ax.legend(frameon=False, loc="upper left")
    for bars in (bars_m0, bars_selected):
        for bar in bars:
            bg_ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.18,
                f"{bar.get_height():.3f}",
                ha="center",
                va="bottom",
                fontsize=10,
                color="#334155",
            )
    for idx, fraction in enumerate(improvement):
        bg_ax.text(
            idx,
            max(m0_values[idx], selected_values[idx]) + 1.05,
            f"逐帧对改善率 {fraction * 100:.1f}%",
            ha="center",
            fontsize=10.5,
            color="#087f5b",
            fontweight="bold",
        )

    person_ax = fig.add_subplot(grid[2, 7:])
    panel(person_ax, "4. 静止PERSON：补偿前后 P90")
    groups = ["全部接受框", "人工端点"]
    before = [float(all_person["uncompensated_p90_px"]), float(manual_person["uncompensated_p90_px"])]
    after = [float(all_person["compensated_p90_px"]), float(manual_person["compensated_p90_px"])]
    gx = np.arange(2)
    before_bars = person_ax.bar(gx - bar_width / 2, before, bar_width, label="补偿前", color="#f59e0b")
    after_bars = person_ax.bar(gx + bar_width / 2, after, bar_width, label="补偿后", color="#10b981")
    person_ax.axhline(short_axis, color="#dc2626", linestyle="--", linewidth=1.6, label=f"短轴中位数 {short_axis:.3f}px")
    person_ax.set_xticks(gx, groups)
    person_ax.set_ylabel("PERSON框中心残差 P90 / px")
    person_ax.set_ylim(0, short_axis * 1.2)
    person_ax.grid(axis="y", alpha=0.22)
    person_ax.legend(frameon=False, loc="upper left")
    for bars in (before_bars, after_bars):
        for bar in bars:
            person_ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.35,
                f"{bar.get_height():.3f}",
                ha="center",
                fontsize=10.5,
                color="#334155",
            )

    evidence_ax = fig.add_subplot(grid[3, :8])
    panel(evidence_ax, "5. 直接失败病例：唯一背景反向帧对 168→171（lag 3）")
    image_path = VIS_DIR / "worst_05_R04ZF_000168_000171_lag3.jpg"
    image = plt.imread(image_path)
    evidence_ax.imshow(image)
    evidence_ax.set_xticks([])
    evidence_ax.set_yticks([])
    evidence_ax.text(
        0.01,
        -0.08,
        "黄/白：拟合/留出背景锚点；橙：PERSON扩张排除区；青：有效扇面边界；白/洋红箭头：观测/冻结M2预测。该帧对原样保留。",
        transform=evidence_ax.transAxes,
        fontsize=10.5,
        color="#475569",
    )

    conclusion_ax = fig.add_subplot(grid[3, 8:])
    panel(conclusion_ax, "6. 结果允许怎样解释")
    conclusion_ax.set_xticks([])
    conclusion_ax.set_yticks([])
    rounded_text(
        conclusion_ax,
        (0.06, 0.72),
        0.88,
        0.18,
        "P0_PASS\n578 / 579 个R04有效帧对优于M0",
        "#d1fae5",
        edge="#6ee7b7",
        fontsize=13,
    )
    rounded_text(
        conclusion_ax,
        (0.06, 0.44),
        0.88,
        0.20,
        "全部接受框 P90：11.143 → 3.557 px\n人工端点 P90：12.203 → 5.029 px\n均低于短轴中位数 18.504 px",
        "#eff6ff",
        edge="#93c5fd",
        fontsize=11.5,
    )
    rounded_text(
        conclusion_ax,
        (0.06, 0.10),
        0.88,
        0.25,
        "能说明：公共图像输运在当前PERSON尺度上可用。\n不能说明：真实载体轨迹、人体RCS、身份、独立运动或最终SAR定位。\nP1仅具备资格，本研究没有自动进入P1。",
        "#fff7ed",
        edge="#fdba74",
        fontsize=11.2,
    )

    fig.text(
        0.01,
        0.008,
        "R01模型冻结：lag1=M1，lag3=M2，lag5=M2。显示分布变化单独分层，不直接归因于增益。PERSON与边界锚点违规均为0。",
        fontsize=10.5,
        color="#64748b",
    )
    fig.savefig(OUTPUT_PATH, dpi=170, bbox_inches="tight")
    plt.close(fig)
    print(json.dumps({"output": str(OUTPUT_PATH), "model_refit": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
