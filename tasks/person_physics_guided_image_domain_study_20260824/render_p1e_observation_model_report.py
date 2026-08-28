#!/usr/bin/env python3
"""Render and validate the PERSON-SAR observation-model diagnostic report.

The report is additive.  It reads the frozen observation-model diagnostic
tables and existing P0/P1E evidence, but it does not regenerate responses,
retune P0, alter C0-C3, or write any source image/annotation.
"""

from __future__ import annotations

import hashlib
import html
import json
import math
import os
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
from PIL import Image


SCRIPT_PATH = Path(__file__).resolve()
TASK_DIR = SCRIPT_PATH.parent
WORKSPACE = TASK_DIR.parents[1]
STUDY_OUTPUT = (
    WORKSPACE / "output" / "person_physics_guided_image_domain_study_20260824"
)
P1E_ROOT = STUDY_OUTPUT / "p1e_sar_only_response_interface"
OUTPUT_DIR = P1E_ROOT / "observation_model_diagnostic_v1"

SUMMARY_PATH = OUTPUT_DIR / "diagnostic_summary.json"
OBSERVATIONS_PATH = OUTPUT_DIR / "observation_condition_table.csv"
DISPLAY_PATH = OUTPUT_DIR / "frame_display_condition_table.csv"
P0_LOCAL_PATH = OUTPUT_DIR / "p0_local_transport_condition_table.csv"
TRADEOFF_PATH = OUTPUT_DIR / "lag_transport_response_tradeoff.csv"
OPTICAL_PATH = OUTPUT_DIR / "optical_shell_audit.csv"
CONDITION_PATH = OUTPUT_DIR / "condition_state_summary.csv"
CASE_PATH = OUTPUT_DIR / "case_registry.csv"
PROTOCOL_PATH = OUTPUT_DIR / "00_OBSERVATION_MODEL_DIAGNOSTIC_PROTOCOL_FROZEN_BEFORE_RUN.md"
REPORT_PATH = OUTPUT_DIR / "P1E_OBSERVATION_MODEL_DIAGNOSTIC_REPORT.html"
VALIDATION_PATH = OUTPUT_DIR / "report_validation.json"

DIAGNOSTIC_SCRIPT = TASK_DIR / "run_p1e_observation_model_diagnostic.py"
P1E_SCRIPT = TASK_DIR / "run_p1e_single_frame_position_specificity.py"
DYNAMIC_INTERPRETATION = (
    P1E_ROOT
    / "dynamic_evidence_temporal_v1"
    / "lag1_r02"
    / "post_analysis_v1"
    / "dynamic_evidence_interpretation_v1.json"
)

PRIMARY = "C2_COMPACT_JET_GRADIENT_CONSENSUS"
DIAGNOSTIC = "C3_ISOTROPIC_BLOB_RIDGE_SUPPRESSED"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def finite(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def num(value: Any, digits: int = 3, missing: str = "—") -> str:
    if not finite(value):
        return missing
    return f"{float(value):.{digits}f}"


def pct(value: Any, digits: int = 1, missing: str = "—") -> str:
    if not finite(value):
        return missing
    return f"{100.0 * float(value):.{digits}f}%"


def median(series: pd.Series) -> float:
    values = pd.to_numeric(series, errors="coerce")
    return float(values.median()) if values.notna().any() else math.nan


def bool_series(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)
    return series.astype(str).str.lower().isin({"true", "1", "yes"})


def relative_asset(path: Path) -> str:
    return Path(os.path.relpath(path, OUTPUT_DIR)).as_posix()


def make_table(headers: Iterable[str], rows: Iterable[Iterable[Any]], classes: str = "") -> str:
    head = "".join(f"<th>{esc(item)}</th>" for item in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{item}</td>" for item in row) + "</tr>"
        for row in rows
    )
    return f'<div class="table-wrap"><table class="{esc(classes)}"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def state_badges(counts: Counter[str]) -> str:
    order = [
        "CANDIDATE_MISSING",
        "EDGE_CENSORED_OR_TRUNCATED",
        "LOW_RANK_BEYOND_TOP5",
        "RANK_COMPETITION_TOP5",
        "SHARED_IMAGE_RESPONSE",
        "TOP1_PRESENT",
    ]
    labels = {
        "CANDIDATE_MISSING": "候选缺失",
        "EDGE_CENSORED_OR_TRUNCATED": "边界/截断",
        "LOW_RANK_BEYOND_TOP5": "低 rank",
        "RANK_COMPETITION_TOP5": "Top-5 竞争",
        "SHARED_IMAGE_RESPONSE": "共享响应",
        "TOP1_PRESENT": "Top-1",
    }
    items = []
    for key in order:
        if counts.get(key, 0):
            items.append(
                f'<span class="badge state-{esc(key.lower())}">{esc(labels[key])} {counts[key]}</span>'
            )
    return " ".join(items) or "—"


def image_block(path: Path, title: str, caption: str, eager: bool = False) -> str:
    loading = "eager" if eager else "lazy"
    return f"""
    <figure class="evidence-figure">
      <a href="{esc(relative_asset(path))}" target="_blank" rel="noopener">
        <img src="{esc(relative_asset(path))}" alt="{esc(title)}" loading="{loading}">
      </a>
      <figcaption><strong>{esc(title)}</strong><br>{caption}</figcaption>
    </figure>
    """


def build_report() -> tuple[str, dict[str, Any]]:
    summary = load_json(SUMMARY_PATH)
    dynamic = load_json(DYNAMIC_INTERPRETATION)
    observations = pd.read_csv(OBSERVATIONS_PATH, low_memory=False)
    display = pd.read_csv(DISPLAY_PATH, low_memory=False)
    tradeoff = pd.read_csv(TRADEOFF_PATH, low_memory=False)
    optical = pd.read_csv(OPTICAL_PATH, low_memory=False)
    condition = pd.read_csv(CONDITION_PATH, low_memory=False)
    cases = pd.read_csv(CASE_PATH, low_memory=False)

    references = observations[observations["entity_kind"] == "PERSON_REFERENCE"].copy()
    r02 = references[references["run_id"] == "R02ZF"].copy()

    r02_rows = []
    for target_id, group in r02.groupby("target_id", sort=True):
        short = target_id.replace("R02ZF_SARPERSON", "P")
        counts = Counter(group["offline_response_state"].fillna("UNLABELED").astype(str))
        shared = int(bool_series(group["offline_shared_flag"]).sum())
        missing = int((group["offline_response_state"] == "CANDIDATE_MISSING").sum())
        rank_gt5 = int(
            (pd.to_numeric(group["nearest_C2_candidate_rank"], errors="coerce") > 5).sum()
        )
        core = float((group["p0_transport_domain_lag1"] == "P0_TRANSPORT_CORE").mean())
        r02_rows.append(
            [
                f"<strong>{esc(short)}</strong>",
                str(len(group)),
                state_badges(counts),
                f"{shared}/{len(group)}",
                f"{missing}/{len(group)}",
                f"{rank_gt5}/{len(group)}",
                num(median(group["nearest_C2_candidate_rank"]), 1),
                num(median(group["C2_percentile_in_frame_valid_region"]), 3),
                pct(core),
                num(median(group["range_m"]), 2) + " m",
            ]
        )

    p0_reference_rows = []
    for run_id in ("R01ZF", "R02ZF", "R03ZF", "R04ZF"):
        row = next(
            item
            for item in summary["P0_domain_summaries"]
            if item["run_id"] == run_id
            and item["lag"] == 1
            and item["entity_kind"] == "PERSON_REFERENCE"
        )
        p0_reference_rows.append(
            [
                f"<strong>{esc(run_id)}</strong>",
                str(row["count"]),
                pct(row["core_fraction"]),
                pct(row["extended_fraction"]),
                pct(row["unavailable_fraction"]),
                num(row["median_sigma_m"], 3) + " m",
                num(row["median_displacement_over_sigma"], 3),
                pct(row["nearest8_fallback_fraction"]),
                pct(row["radial_bracket_fraction"]),
                pct(row["azimuth_bracket_fraction"]),
            ]
        )

    lag_rows = []
    for row in summary["lag_tradeoff_summaries"]:
        lag_rows.append(
            [
                f"<strong>{int(row['lag'])}</strong>",
                str(row["pair_count"]),
                num(row["median_transport_displacement_m"], 4) + " m",
                num(row["median_local_sigma_m"], 4) + " m",
                num(row["median_transport_separability"], 3),
                num(row["median_C2_field_retention_correct"], 3),
                num(row["median_C2_field_retention_zero"], 3),
                num(row["median_correct_minus_zero_retention"], 3),
                pct(row["median_P0_core_grid_fraction"]),
            ]
        )

    display_rows = []
    for row in summary["frame_display_state_counts_by_run"]:
        display_rows.append(
            [
                f"<strong>{esc(row['run_id'])}</strong>",
                str(row["frame_count"]),
                pct(row["display_shift_fraction"]),
                pct(row["high_censor_proxy_fraction"]),
                pct(row["compressed_proxy_fraction"]),
            ]
        )

    optical_reference = summary["optical_mapping_audit"]["reference_coverage_by_run"]
    candidate_optical = optical[
        (optical["entity_kind"] == "SAR_ONLY_C2_CANDIDATE")
        & (optical["offline_response_state"] == "ALL")
    ].copy()
    optical_rows = []
    for ref_row in optical_reference:
        run_id = ref_row["run_id"]
        candidate_row = candidate_optical[candidate_optical["run_id"] == run_id].iloc[0]
        optical_rows.append(
            [
                f"<strong>{esc(run_id)}</strong>",
                pct(ref_row["window_250ms_shell_coverage"]),
                pct(ref_row["shift_minus18deg_coverage"]),
                pct(ref_row["shift_plus18deg_coverage"]),
                num(ref_row["mean_true_in_fan_width_deg"], 1) + "°",
                pct(candidate_row["window_250ms_shell_coverage"]),
                num(candidate_row["coverage_per_degree_true"], 4),
                num(
                    np.nanmedian(
                        [
                            candidate_row["coverage_per_degree_shift_minus"],
                            candidate_row["coverage_per_degree_shift_plus"],
                        ]
                    ),
                    4,
                ),
            ]
        )

    overall_counts = Counter(summary["reference_state_overall"])
    dynamic_scale = dynamic["transport_scale"]
    lag1 = summary["lag_tradeoff_summaries"][0]
    lag3 = summary["lag_tradeoff_summaries"][1]
    lag5 = summary["lag_tradeoff_summaries"][2]

    display_high_lag5 = next(
        row
        for row in summary["display_retention_summaries"]
        if row["lag"] == 5
        and row["display_stratum"] == "HIGH_GLOBAL_DISPLAY_DISTRIBUTION_CHANGE"
    )
    display_base_lag5 = next(
        row
        for row in summary["display_retention_summaries"]
        if row["lag"] == 5
        and row["display_stratum"] == "BASELINE_GLOBAL_DISPLAY_DISTRIBUTION"
    )

    case_map = {str(row.reason): Path(str(row.visual_path)) for row in cases.itertuples()}
    case_copy = {
        "R02_P01_P02_LOW_RANK_NEARBY_RESPONSE": (
            "R02 P01/P02：附近有响应，但 rank 与共享状态并存",
            "F472 的参考位置处 C2 百分位很高，附近候选却不是全扇面唯一强点。图像说明“候选存在”“rank 竞争”“共享”可以同时成立，不能用一个排他标签覆盖其它证据。",
        ),
        "R02_P02_CANDIDATE_MISSING_CASE": (
            "R02 P02：固定候选定义下的 missing",
            "F482 的参考处仍有连续 C2 响应，但 0.8 m 内没有经局部极大值/NMS 产生的候选；最近候选约 1.16 m。这里的 missing 是当前表示与候选提取的联合状态，不等于回波物理消失。",
        ),
        "R02_P03_P04_SHARED_IMAGE_RESPONSE": (
            "R02 P03/P04：高 rank 共享响应",
            "同一强局部响应同时落入两个离线 reference 邻域。它证明当前图像域未空间分离，不证明两个物理目标的散射发生了融合。",
        ),
        "R03_OUTER_BOUNDARY_TRUNCATION": (
            "R03 F458：接近 P0 的 1 m 外边界退让",
            "reference 距 20 m 外边界约 0.89 m，单帧支持为 FULL/1.00，附近候选 rank=18；它是 near-boundary/P0-retreat 病例，不是实际支持核截断，也不能自动判定“不可观察”。",
        ),
        "R03_SINGLE_FRAME_BOUNDARY_RECOVERY": (
            "R03 F494：单帧可见而 P0 时序不可用",
            "reference 距外边界约 2.47 m，单帧 C2 候选 rank=6，但 lag1 P0 状态不可用。它直接支持 SAR_SINGLE_FRAME_OBSERVABLE 与 P0_TRANSPORT 域必须分开。",
        ),
        "R04_ISOLATED_REFERENCE_CONTROL": (
            "R04：相对孤立的 Top-1 对照",
            "C2 在 reference 附近形成 rank=1 响应；同时该位置的 P0 仍因 nearest-8 fallback 属于 EXTENDED。单帧清晰不自动意味着时序输运处于 CORE。",
        ),
        "DISPLAY_PROXY_EXTREME_MANUAL_REFERENCE_FRAME": (
            "显示变化病例：图像状态与目标状态并列记录",
            "同一帧包含 Top-5 与 shared 状态，且被标记 DISPLAY_SHIFT。显示代理只能说明观测链发生变化，不能解释为 PERSON 回波真实增强或减弱。",
        ),
        "P0_LOCAL_ANCHOR_FALLBACK_OR_ONE_SIDED": (
            "P0 局部锚点 fallback 病例",
            "单帧候选 rank=2，但 P0 局部误差依赖 nearest-8 fallback，因此属于 EXTENDED。该病例显示图像证据和几何/输运可靠性是两个独立维度。",
        ),
    }

    case_html = "".join(
        image_block(case_map[key], title, caption, eager=(index == 0))
        for index, (key, (title, caption)) in enumerate(case_copy.items())
    )

    summary_images = [
        (
            OUTPUT_DIR / "visualizations" / "reference_state_range_azimuth.png",
            "PERSON 状态在 range–azimuth 空间中的分布",
            "R03 的低 rank 位于 20 m 外缘附近；R02 的 missing/low-rank 与 shared 分别落在不同目标簇。图中是共现分布，不是单变量因果证明。",
        ),
        (
            OUTPUT_DIR / "visualizations" / "p0_transport_displacement_vs_uncertainty.png",
            "P0 输运位移与局部不确定度",
            "同一扇面内的 transport displacement / sigma 并不均匀；CORE、EXTENDED 与 fallback 需要保留为位置条件。",
        ),
        (
            OUTPUT_DIR / "visualizations" / "lag_geometry_response_tradeoff.png",
            "几何可分辨性与 C2 保持性的 lag 权衡",
            "lag 增大使 correct transport 更容易区别于 zero，同时 C2 图像域响应逐步去相关。因此不存在“lag 越大越好”的单调结论。",
        ),
        (
            OUTPUT_DIR / "visualizations" / "retention_vs_display_change.png",
            "显示分布变化与响应保持性",
            "高 JS 变化条件下，特别是 lag5，correct-P0 后的 C2 保持性仍下降；显示链需要作为观测条件单独分层。",
        ),
        (
            OUTPUT_DIR / "visualizations" / "optical_shell_shift_control.png",
            "光学粗方位壳与 shifted-shell 对照",
            "reference 的正确壳覆盖高于 shifted 壳，但 SAR-only candidates 的覆盖比例/平均扇内角宽 proxy 相近。当前只能支持进入下一轮受控实验，不能声称已提升 SAR 定位。",
        ),
        (
            OUTPUT_DIR / "visualizations" / "display_condition_timeline.png",
            "逐 run 的显示状态时间线",
            "DISPLAY_SHIFT 在各 run 均出现；统一的 COMPRESSED_PROXY 对全部帧为真，因缺乏区分力只能保留为阴性诊断。",
        ),
    ]
    summary_figure_html = "".join(
        image_block(path, title, caption) for path, title, caption in summary_images
    )

    output_links = [
        ("冻结协议", PROTOCOL_PATH),
        ("统一观测条件表", OBSERVATIONS_PATH),
        ("逐帧显示条件", DISPLAY_PATH),
        ("P0 局部输运条件", P0_LOCAL_PATH),
        ("lag 权衡表", TRADEOFF_PATH),
        ("光学壳审计", OPTICAL_PATH),
        ("条件状态汇总", CONDITION_PATH),
        ("病例索引", CASE_PATH),
        ("机器总结", SUMMARY_PATH),
    ]
    output_link_html = "".join(
        f'<a class="file-link" href="{esc(relative_asset(path))}">{esc(label)}</a>'
        for label, path in output_links
    )

    html_text = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PERSON-SAR 观测模型诊断 v1</title>
  <style>
    :root {{ --ink:#122033; --muted:#5f6f82; --line:#dbe4ee; --paper:#f5f7fb; --card:#ffffff; --blue:#2764d8; --cyan:#0a8f98; --amber:#c57900; --red:#bd3d4f; --green:#23855a; --purple:#7455bb; }}
    * {{ box-sizing:border-box; }}
    html {{ scroll-behavior:smooth; }}
    body {{ margin:0; color:var(--ink); background:var(--paper); font:16px/1.68 "Segoe UI","Microsoft YaHei",sans-serif; }}
    a {{ color:var(--blue); }}
    .hero {{ padding:58px max(24px,calc((100vw - 1320px)/2)); background:linear-gradient(125deg,#0e263e 0%,#163e5a 58%,#1b6d72 100%); color:white; }}
    .eyebrow {{ letter-spacing:.08em; text-transform:uppercase; font-size:13px; opacity:.82; }}
    h1 {{ margin:.25rem 0 .65rem; font-size:clamp(34px,5vw,64px); line-height:1.08; }}
    .hero p {{ max-width:980px; font-size:18px; color:#e2f1f3; }}
    .status {{ display:inline-block; padding:7px 12px; border:1px solid #8ad3cf; border-radius:999px; background:#0d5558; font-weight:700; }}
    .metrics {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; margin-top:28px; }}
    .metric {{ padding:16px; border:1px solid #ffffff35; border-radius:14px; background:#ffffff12; }}
    .metric b {{ display:block; font-size:27px; }}
    .metric span {{ color:#d6e9ec; font-size:13px; }}
    nav {{ position:sticky; top:0; z-index:5; display:flex; gap:15px; overflow:auto; padding:12px max(20px,calc((100vw - 1320px)/2)); background:#ffffffee; border-bottom:1px solid var(--line); backdrop-filter:blur(10px); }}
    nav a {{ white-space:nowrap; text-decoration:none; font-weight:650; font-size:14px; }}
    main {{ max-width:1320px; margin:auto; padding:30px 22px 90px; }}
    section {{ scroll-margin-top:68px; margin:28px 0 44px; }}
    h2 {{ margin:0 0 15px; font-size:31px; line-height:1.25; }}
    h3 {{ margin:20px 0 9px; font-size:21px; }}
    .lead {{ color:var(--muted); font-size:18px; max-width:1050px; }}
    .callout {{ padding:18px 20px; border-left:5px solid var(--blue); border-radius:10px; background:#eaf2ff; }}
    .callout.warning {{ border-color:var(--amber); background:#fff6df; }}
    .callout.negative {{ border-color:var(--red); background:#fff0f2; }}
    .grid-2 {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:18px; }}
    .grid-3 {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:18px; }}
    .card {{ padding:20px; border:1px solid var(--line); border-radius:15px; background:var(--card); box-shadow:0 6px 20px #1025400a; }}
    .card h3 {{ margin-top:0; }}
    .answer {{ border-top:5px solid var(--cyan); }}
    .answer .q {{ color:var(--cyan); font-size:13px; font-weight:800; letter-spacing:.04em; }}
    .evidence-vector {{ display:grid; grid-template-columns:repeat(6,minmax(0,1fr)); gap:10px; margin:20px 0; }}
    .evidence-vector div {{ min-height:110px; padding:14px; border-radius:13px; color:white; background:#244c6e; }}
    .evidence-vector div:nth-child(2) {{ background:#356f78; }} .evidence-vector div:nth-child(3) {{ background:#5b668c; }}
    .evidence-vector div:nth-child(4) {{ background:#765d8d; }} .evidence-vector div:nth-child(5) {{ background:#876d3f; }} .evidence-vector div:nth-child(6) {{ background:#7d4d59; }}
    .evidence-vector b {{ display:block; margin-bottom:6px; }}
    .table-wrap {{ overflow:auto; margin:15px 0 22px; border:1px solid var(--line); border-radius:12px; background:white; }}
    table {{ width:100%; border-collapse:collapse; font-size:14px; }}
    th,td {{ padding:11px 12px; text-align:left; border-bottom:1px solid var(--line); vertical-align:top; white-space:nowrap; }}
    th {{ position:sticky; top:0; background:#edf3f9; color:#30465e; }}
    tr:last-child td {{ border-bottom:0; }}
    .badge {{ display:inline-block; padding:3px 7px; margin:2px; border-radius:999px; background:#eef1f6; font-size:12px; white-space:nowrap; }}
    .state-candidate_missing,.state-edge_censored_or_truncated {{ background:#ffe4e8; color:#8e2336; }}
    .state-low_rank_beyond_top5 {{ background:#fff0d8; color:#845100; }}
    .state-rank_competition_top5 {{ background:#fff5bc; color:#6a5500; }}
    .state-shared_image_response {{ background:#eee7ff; color:#55398b; }}
    .state-top1_present {{ background:#dff5e9; color:#176341; }}
    .figure-grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:20px; }}
    .evidence-figure {{ margin:0; border:1px solid var(--line); border-radius:14px; overflow:hidden; background:white; box-shadow:0 6px 20px #1025400a; }}
    .evidence-figure img {{ display:block; width:100%; height:auto; background:#f8fafc; }}
    .evidence-figure figcaption {{ padding:14px 16px 17px; color:var(--muted); }}
    .evidence-figure figcaption strong {{ color:var(--ink); }}
    code {{ padding:2px 5px; border-radius:5px; background:#edf1f5; font-family:Consolas,monospace; }}
    .formula {{ overflow:auto; padding:17px; border-radius:12px; background:#0f2539; color:#eaf5ff; font:15px/1.7 Consolas,monospace; }}
    .file-links {{ display:flex; flex-wrap:wrap; gap:8px; }}
    .file-link {{ padding:8px 11px; border:1px solid var(--line); border-radius:9px; background:white; text-decoration:none; }}
    .foot {{ color:var(--muted); font-size:13px; }}
    @media (max-width:980px) {{ .metrics,.grid-3,.evidence-vector {{ grid-template-columns:repeat(2,minmax(0,1fr)); }} .grid-2,.figure-grid {{ grid-template-columns:1fr; }} }}
    @media (max-width:600px) {{ .metrics,.grid-3,.evidence-vector {{ grid-template-columns:1fr; }} .hero {{ padding-top:36px; }} }}
  </style>
</head>
<body>
  <header class="hero">
    <div class="eyebrow">PERSON · SAR pseudocolor · observation model diagnostic v1</div>
    <h1>从“找一个点”转向<br>“描述观测状态”</h1>
    <span class="status">诊断完成 · 不授予新 PASS/FAIL</span>
    <p>本轮没有增加 C4/C5、没有重调冻结 P0、没有建立复杂 tracker，也没有把光学位置当作 SAR runtime truth。目标是回答：条件性 PERSON 响应在什么图像、几何、显示和时序条件下出现、竞争、共享或缺失，以及光学粗方位壳是否值得进入下一轮受控实验。</p>
    <div class="metrics">
      <div class="metric"><b>{summary['counts']['frame_display_rows']}</b><span>实际 SAR 伪彩帧</span></div>
      <div class="metric"><b>{summary['counts']['observation_rows']:,}</b><span>统一观测实体行</span></div>
      <div class="metric"><b>{summary['counts']['lag_pair_rows']:,}</b><span>lag1/3/5 帧对诊断行</span></div>
      <div class="metric"><b>{summary['counts']['case_count']}</b><span>直接成功/失败病例</span></div>
    </div>
  </header>

  <nav>
    <a href="#conclusion">结论</a><a href="#model">观测模型</a><a href="#states">响应状态</a>
    <a href="#domains">空间可靠域</a><a href="#lag">lag 权衡</a><a href="#display">显示链</a>
    <a href="#optical">光学软先验</a><a href="#cases">真实病例</a><a href="#answers">八问回答</a><a href="#audit">边界与复核</a>
  </nav>

  <main>
    <section id="conclusion">
      <h2>结论先行</h2>
      <div class="callout"><strong>目前最合理的研究结论不是“PERSON-SAR 成功/失败”，而是 reference 条件下存在多种可逆观测状态。</strong> R02 P01/P02 均为 9/9 最近候选 rank&gt;5，其中各 7/9 同时被离线标记为 shared，P02 另有 2 个 0.8 m 内候选缺失病例；P03/P04 是高 rank 但共享。边界、显示变化和 P0 局部锚点条件会改变可解释性，却不能统一解释所有失败。</div>
      <div class="grid-3" style="margin-top:18px">
        <div class="card"><h3>单帧图像证据</h3><p>C2 能在部分 reference 附近集中，但不是稳定的唯一定位器。总体离线排他状态计数为：{state_badges(overall_counts)}。</p></div>
        <div class="card"><h3>P0 / 时序证据</h3><p>lag1 全场位移仅 {num(lag1['median_transport_separability'],3)} 个设计容差，correct-zero 保持性增量只有 {num(lag1['median_correct_minus_zero_retention'],3)}；这与 correct≈zero 的尺度关系相容，但不是校准置信区间或唯一因果解释。lag3/5 聚合增量上升时，响应保持性下降。</p></div>
        <div class="card"><h3>光学软先验</h3><p>现有映射足以提出 provisional common-FoV 与粗方位壳假设；同步未验证、壳宽和边界截断仍存在，只值得进入带 shifted-shell 对照的下一轮实验。</p></div>
      </div>
      <div class="callout warning" style="margin-top:18px"><strong>两类时序指标必须分开：</strong>本轮的 C2 field retention 测“同一暴露图像对的全响应场经过冻结 P0 后是否更对齐”；既有 dynamic evidence 测“PERSON reference 邻近候选的 rank/线程是否被消歧”。前者是含背景与空间自相关的描述性 field-alignment 量，lag1 有小而系统的 correct-zero 差；后者尚未建立稳定 P0-specific 增益，两者并不矛盾。</div>
    </section>

    <section id="model">
      <h2>一、重构后的观测对象</h2>
      <p class="lead">候选峰只是当前伪彩显示域的局部高响应，不是人体固有 RCS、固定散射中心或真实目标轨迹。本轮先保留六个独立证据维度，不未经校准地加权成总分。</p>
      <div class="evidence-vector">
        <div><b>Image</b>C2 score、局部 percentile、rank fraction、竞争差、候选密度、C3/anisotropy。</div>
        <div><b>Observation</b>range、azimuth、扇面/20 m 边界、support、显示状态。</div>
        <div><b>P0 / Geometry</b>冻结公共表观输运、local sigma、锚点数、双侧覆盖、fallback。</div>
        <div><b>Temporal</b>响应保持、线程持续、strengthen/weaken、缺失与恢复。</div>
        <div><b>Optical</b>common-FoV、粗时间窗、azimuth shell；不指定 SAR range。</div>
        <div><b>Ambiguity</b>当前 low-rank/shared/missing 是 reference 条件的离线评价状态；尚未建立 GT-blind 运行时状态检测器。</div>
      </div>
      <div class="formula">E(x,t) = [ image evidence, observation condition, P0/geometric support, temporal persistence, optical support, ambiguity state ]

本轮不定义：w1·image + w2·P0 + w3·optical + …</div>
      <h3>统一 observation-condition table</h3>
      <p>同一位置条件函数被用于 PERSON reference、全部 GT-blind C2 candidates、固定 1.25 m 偏移、几何匹配对照和局部竞争对照。reference/ID 只在离线评价层出现，不进入 C2/C3、P0 拟合或光学壳选择。</p>
      {make_table(
          ["实体", "作用", "运行时/离线边界"],
          [
              ["<strong>PERSON_REFERENCE</strong>", "离线标记真实病例与状态", "不生成 S(x)、候选、输运或光学壳"],
              ["<strong>SAR_ONLY_C2_CANDIDATE</strong>", "全扇面 GT-blind 局部极大值/NMS 候选", "不截断为 Top-5"],
              ["<strong>FIXED_OFFSET_CONTROL</strong>", "径向/切向 1.25 m 空间对照", "不复制目标位移给背景"],
              ["<strong>GEOMETRY_MATCHED_CONTROL</strong>", "同距离的几何匹配对照", "与 reference 使用同一观测条件函数"],
              ["<strong>LOCAL_COMPETING_CONTROL</strong>", "局部最强竞争响应", "不是绝对纯背景"],
          ],
      )}
    </section>

    <section id="states">
      <h2>二、响应状态与观测条件</h2>
      <p class="lead">R02 的四个 PERSON 不是同一种失败。下表的“主状态”是排他标签：实现先判 shared，再判 missing/rank；因此必须同时查看 shared、missing 和 rank&gt;5 独立列。这些标签由人工 reference 在完整候选产生后离线赋予，不是运行时状态分类器。</p>
      {make_table(
          ["R02 目标", "帧", "排他主状态计数", "同时 shared", "0.8 m 内 missing", "最近候选 rank>5", "最近候选 rank 中位", "C2 percentile 中位", "lag1 P0 core", "range 中位"],
          r02_rows,
      )}
      <div class="grid-2">
        <div class="card"><h3>P01/P02：9/9 低 rank，并与 shared/missing 叠加</h3><p>P01/P02 的最近候选均为 9/9 rank&gt;5，rank 中位数均为 14；其中各 7/9 同时 shared。C2 percentile 通常仍很高，说明 reference 附近不是“没有任何连续响应”；但全扇面候选很多，参考附近峰常排在 7–24 名。P02 两个 0.8 m 内 missing 病例位于 FULL support、P0 core 且无 display shift，因此不能主要归咎于扇面边界、P0 低可靠或显示突变；当前表示/峰提取与局部竞争更值得优先检查。</p></div>
        <div class="card"><h3>P03/P04：高 rank 但共享</h3><p>两者各 9/9 shared；各自 5 帧 rank1、3 帧 rank2、1 帧 rank12。当前 0.8 m 离线邻域又接近两人约 0.70–0.81 m 的间距。只能说图像域候选未分离，不能把 shared/merge-like 写成物理散射融合或身份不可分的因果证明。</p></div>
      </div>
      {image_block(OUTPUT_DIR / 'visualizations' / 'reference_state_range_azimuth.png', '状态在 range–azimuth 空间中的位置', 'R03 边界病例清晰集中在 20 m 外缘附近；R02 的不同 PERSON 簇具有不同状态。R01/R04 则显示低 rank 并非只发生在单一 range 或 azimuth。')}
    </section>

    <section id="domains">
      <h2>三、SAR 空间可靠域不是一个 mask</h2>
      <div class="grid-3">
        <div class="card"><h3>SAR_SINGLE_FRAME_OBSERVABLE</h3><p>当前帧仍有真实扇面图像，固定 0.30 m 支持核有效比例可计算；FULL/TRUNCATED/INVALID 是单帧状态。</p></div>
        <div class="card"><h3>P0_TRANSPORT_CORE</h3><p>冻结 pair 可比较、source 在 P0 base mask、局部锚点足够且距离/方位双侧覆盖、无需 fallback、destination 仍单帧可观察。</p></div>
        <div class="card"><h3>P0_TRANSPORT_EXTENDED</h3><p>仍可预测，但可能位于 P0 退让区、锚点单侧或使用 nearest-8；保留更大的不确定性描述，不自动删除。</p></div>
      </div>
      <p class="callout warning"><strong>关键反例：</strong>R03 reference 的 lag1 core 为 0%，但单帧 reference 全部仍可评价；F494 甚至有 rank=6 候选而 lag1 P0 unavailable。P0 时序不可比较不等于 SAR 单帧不可观察。</p>
      {make_table(
          ["run", "reference 条件数", "CORE", "EXTENDED", "UNAVAILABLE", "sigma 中位", "位移/sigma", "nearest-8 fallback", "径向双侧", "方位双侧"],
          p0_reference_rows,
      )}
      <p class="foot">这些比例描述 PERSON reference 所在位置的 P0 条件，不等同于该 run 的全局 P0 成败。冻结 P0 本身保持不动。</p>
      {image_block(OUTPUT_DIR / 'visualizations' / 'p0_transport_displacement_vs_uncertainty.png', 'P0 局部可靠性是连续且位置相关的', 'reference、candidates 与 controls 在同一局部 sigma、锚点模式和双侧覆盖口径下比较。CORE 随 lag 下降，EXTENDED 不能被误写成“没有响应”。')}
    </section>

    <section id="lag">
      <h2>四、lag 不是越大越好：几何可分辨性 vs 响应保持性</h2>
      <p class="lead">诊断量 <code>|u_hat| / sigma_local</code> 只描述 correct transport 与 zero transport 的尺度分离；这里的 sigma 是 <code>sqrt(local P0 holdout error² + 0.30 m support²)</code> 的设计容差，不是校准置信区间。C2 field retention 则描述伪彩显示域响应在不同冻结 lag 配置下还能保留多少结构。</p>
      {make_table(
          ["lag", "帧对", "位移中位", "local sigma", "位移/sigma", "correct 保持", "zero 保持", "correct-zero", "P0 core 网格"],
          lag_rows,
      )}
      <div class="grid-3">
        <div class="card"><h3>lag1</h3><p>全场网格中位位移 {num(lag1['median_transport_displacement_m'],4)} m，仅 {num(lag1['median_transport_separability'],3)} 个设计容差，correct-zero 只有 {num(lag1['median_correct_minus_zero_retention'],3)}。既有 R02 候选节点审计为 {num(dynamic_scale['median_transport_displacement_m'],3)} m / {num(dynamic_scale['median_sigma_region_m'],3)} m = {num(dynamic_scale['median_transport_to_sigma_ratio'],3)}；采样对象不同，但都与 zero 仍落在同一可能区域的尺度解释相容。</p></div>
        <div class="card"><h3>lag3</h3><p>可分辨性升到 {num(lag3['median_transport_separability'],3)}σ，correct-zero 增到 {num(lag3['median_correct_minus_zero_retention'],3)}；但 correct C2 保持性已降到 {num(lag3['median_C2_field_retention_correct'],3)}。</p></div>
        <div class="card"><h3>lag5</h3><p>中位几何分离约 {num(lag5['median_transport_separability'],3)}σ，correct-zero 增到 {num(lag5['median_correct_minus_zero_retention'],3)}；同时 correct 保持性只剩 {num(lag5['median_C2_field_retention_correct'],3)}，且 R03 lag5 是明显反例。</p></div>
      </div>
      {image_block(OUTPUT_DIR / 'visualizations' / 'lag_geometry_response_tradeoff.png', '聚合 lag 权衡曲线', '绿色 correct-P0 在聚合中高于 zero，但这不是纯 lag 因果效应：lag1 使用 M1、lag3/5 使用 M2，帧对集合和 display JS 也不同；R03 的 separability 在 lag5 反而下降。图只描述总体 tradeoff。')}
      <p class="callout warning"><strong>field-retention 限定：</strong>P0 来自同一暴露图像对的背景拟合；当前全场 Pearson 未配置 wrong/shuffle 或等效亚像素插值控制。因此 {num(lag1['median_correct_minus_zero_retention'],3)} / {num(lag3['median_correct_minus_zero_retention'],3)} / {num(lag5['median_correct_minus_zero_retention'],3)} 只能称为 field-alignment 描述量，不能当作独立 PERSON 时序增益。</p>
      <div class="callout negative"><strong>与既有动态证据的关系：</strong>R02 lag1 的候选线程能区别 gross 错误输运，却与 zero 高度相似；当前状态仍是 <code>TEMPORAL_STRUCTURE_PRESENT_P0_SPECIFIC_GAIN_NOT_ESTABLISHED</code>。本轮全场 field alignment 的小增益不能直接外推为 PERSON 候选消歧成功。</div>
    </section>

    <section id="display">
      <h2>五、显示链正式进入观测条件</h2>
      <p class="lead">JPEG/JET 的 RGB 只是同一显示标量的冗余编码，不是三条独立雷达物理通道。绝对亮度、饱和代理和动态范围变化只能描述 DISPLAY_CENSORED / DISPLAY_SHIFT，不能解释为 PERSON 固有 RCS 改变。</p>
      {make_table(["run", "帧", "DISPLAY_SHIFT", "HIGH_CENSOR_PROXY", "COMPRESSED_PROXY"], display_rows)}
      <div class="grid-2">
        <div class="card"><h3>两个阴性结果</h3><p>HIGH_CENSOR_PROXY 在所有 run 都是 0；COMPRESSED_PROXY 在全部 398 帧都为 1，因此两个离散标签都没有提供有效的帧间区分。报告保留它们，是为了明确“当前代理没有辨识力”，而不是静默删除。</p></div>
        <div class="card"><h3>连续显示变化仍有信息</h3><p>display JS 与连续 JET 统计能分层。lag5 的 baseline correct retention 为 {num(display_base_lag5['median_correct_retention'],3)}，high-change 为 {num(display_high_lag5['median_correct_retention'],3)}；这是显示变化与响应去相关的共现证据，不是增益变化或物理回波减弱的证明。</p></div>
      </div>
      {image_block(OUTPUT_DIR / 'visualizations' / 'retention_vs_display_change.png', '显示 JS 变化与 C2 保持性', 'lag 越长，高 display change 条件下的响应保持性下降越明显。仍需把观察角变化、显示变化和响应中心变化并列为候选解释。')}
      {image_block(OUTPUT_DIR / 'visualizations' / 'display_condition_timeline.png', '显示条件时间线', '不同 run 中 DISPLAY_SHIFT 均间歇出现；这为未来 missing-state bridge 提供了观测可靠度条件，但不能无条件跨缺失帧。')}
    </section>

    <section id="optical">
      <h2>六、光学可以软引入到哪里</h2>
      <p class="lead">当前固定映射为 <code>{esc(summary['optical_mapping_audit']['common_fov_formula'])}</code>。R01 leave-one-person-out 方位 MAE 约 {num(summary['optical_mapping_audit']['R01_leave_one_person_out_macro_mae_deg'],2)}°；R04 在条件性同步假设下 nominal-zero macro MAE 约 {num(summary['optical_mapping_audit']['R04_nominal_zero_macro_mae_deg'],2)}°。同步仍未识别，因此只能形成 provisional common-FoV 与 ±250 ms 粗方位壳。</p>
      {make_table(
          ["run", "reference 真壳覆盖", "shift -18°", "shift +18°", "真壳扇内宽", "C2 candidate 真壳覆盖", "candidate-fraction/degree 真壳", "candidate-fraction/degree shifted 中位"],
          optical_rows,
      )}
      <div class="grid-2">
        <div class="card"><h3>安全支持的 O1/O2</h3><p><strong>O1：</strong>固定 common-FoV 几何。<br><strong>O2：</strong>粗时间窗内所有光学 PERSON 壳的并集。运行时不按 physical_target_id 选壳，不使用光学框决定 SAR range，SAR 在壳内仍凭自己的 image/geometry/temporal evidence 定位。</p></div>
        <div class="card"><h3>为什么还不能称为跨模态增益</h3><p>shift 前区间等宽，但经扇面裁剪后真壳与 shifted 壳的有效宽度并不相等；表中的 per-degree 量是“候选覆盖比例/平均扇内角宽”，不是候选数/度。该 proxy 在真/假壳间相近。±250 ms 也只是按 SAR timestamp 汇总相邻记录附带的 optical PERSON 壳，不代表同步已经验证。</p></div>
      </div>
      {image_block(OUTPUT_DIR / 'visualizations' / 'optical_shell_shift_control.png', '正确方位壳与 shifted-shell 对照', '图题中的 equal-width 只对 shift 前区间成立；扇内裁剪后宽度不等。reference 层显示有希望，candidate 层仍需更公平的实际面积/边界匹配，并报告逐帧候选数/实际扇内角宽。')}
      <div class="callout"><strong>本轮判断：</strong>光学粗方位壳值得进入下一轮“多模态候选实验”，但只作为 soft search prior。它尚未证明能提高 SAR 最终定位，也不能替代 SAR 对 range 和局部响应位置的决定权。</div>
    </section>

    <section id="cases">
      <h2>七、真实病例：先看图，再解释统计</h2>
      <p class="lead">每张图同时展示原始 SAR 伪彩、全扇面 C2、局部候选、人工 reference 离线叠加、controls、显示状态和 P0 局部条件。点击可打开原图。</p>
      <div class="figure-grid">{case_html}</div>
    </section>

    <section id="answers">
      <h2>八、用户提出的八个问题：直接回答</h2>
      <div class="grid-2">
        <article class="card answer" id="q1"><div class="q">Q1 · 低 rank / missing / shared 与什么条件相关？</div><h3>不是一个共同原因，且这些是离线 reference 条件状态</h3><p>R02 P01/P02 均 9/9 rank&gt;5，各 7/9 同时 shared；P02 另有 2 个 0.8 m 内 missing。P03/P04 是高 rank 共享。R03 的低 rank 与 20 m 外边界和部分 display shift 共现。R04 的低 rank 广泛分布，不能仅由边界解释。P02 两个 missing 又处于 FULL support、P0 core、无 display shift，提示当前表示/候选提取本身仍是独立阻断。</p></article>
        <article class="card answer" id="q2"><div class="q">Q2 · P0 可靠性是否随位置和锚点改变？</div><h3>是，而且变化很大</h3><p>reference lag1 core：R01 {pct(next(r['core_fraction'] for r in summary['P0_domain_summaries'] if r['run_id']=='R01ZF' and r['lag']==1 and r['entity_kind']=='PERSON_REFERENCE'))}、R02 {pct(next(r['core_fraction'] for r in summary['P0_domain_summaries'] if r['run_id']=='R02ZF' and r['lag']==1 and r['entity_kind']=='PERSON_REFERENCE'))}、R03 0%、R04 {pct(next(r['core_fraction'] for r in summary['P0_domain_summaries'] if r['run_id']=='R04ZF' and r['lag']==1 and r['entity_kind']=='PERSON_REFERENCE'))}。主要差别来自 P0 base mask、距离/方位双侧锚点与 nearest-8 fallback；local sigma 本身只是设计容差，不是校准置信区间。</p></article>
        <article class="card answer" id="q3"><div class="q">Q3 · 是否存在 P0 核心区和更宽单帧观察区？</div><h3>存在，且必须分开描述</h3><p>全场 P0 core 网格从 lag1 的 {pct(lag1['median_P0_core_grid_fraction'])} 降到 lag5 的 {pct(lag5['median_P0_core_grid_fraction'])}；同时 R03 提供单帧可观察但 P0 extended/unavailable 的直接反例。后续应保留连续可靠性与多标签，而不是恢复统一硬 gate。</p></article>
        <article class="card answer" id="q4"><div class="q">Q4 · lag1 correct≈zero 是否由位移小于不确定度解释？</div><h3>结果与这个尺度解释相容，但不是因果证明</h3><p>全场网格中位为 {num(lag1['median_transport_displacement_m'],3)} m / {num(lag1['median_local_sigma_m'],3)} m = {num(lag1['median_transport_separability'],3)} 个设计容差；R02 候选节点为 {num(dynamic_scale['median_transport_to_sigma_ratio'],3)}。sigma 含固定 0.30 m support 项，不是校准置信区间。两种采样都显示 correct 与 zero 尺度上高度重叠，这是候选消歧缺乏稳定特异增益的一个直接且相容的解释，而非唯一原因。</p></article>
        <article class="card answer" id="q5"><div class="q">Q5 · lag3/5 是否更可分，同时去相关？</div><h3>聚合数据呈现描述性 tradeoff，不是纯 lag 因果效应</h3><p>聚合位移/sigma 为 {num(lag1['median_transport_separability'],3)} → {num(lag3['median_transport_separability'],3)} → {num(lag5['median_transport_separability'],3)}，correct-zero field-alignment 差为 {num(lag1['median_correct_minus_zero_retention'],3)} → {num(lag3['median_correct_minus_zero_retention'],3)} → {num(lag5['median_correct_minus_zero_retention'],3)}；但 correct 保持性从 {num(lag1['median_C2_field_retention_correct'],3)} 降至 {num(lag5['median_C2_field_retention_correct'],3)}。同时 lag1=M1、lag3/5=M2，帧对与 display JS 不同，R03 lag5 又不单调，因此不能机械选择或因果归因于更大 lag。</p></article>
        <article class="card answer" id="q6"><div class="q">Q6 · display chain 的影响能否观察和分层？</div><h3>连续变化可以，两个离散代理不行</h3><p>DISPLAY_SHIFT 在各 run 为约 31%–48%；高 display-JS 在 lag5 对应更低 C2 retention。HIGH_CENSOR_PROXY 全 0、COMPRESSED_PROXY 全 1，均缺乏辨识力。显示变化只能作为观测删失/漂移状态，不能归因于 PERSON 回波物理变弱。</p></article>
        <article class="card answer" id="q7"><div class="q">Q7 · 现有光学映射可安全提供什么？</div><h3>provisional common-FoV 和粗 azimuth shell</h3><p>可以审计 O1/O2；不能安全提供精确逐帧 SAR 点、range、严格同步或姿态条件。±250 ms 壳必须由窗口内所有 PERSON 壳并集产生，不能使用 physical_target_id 选择“正确”轨迹。</p></article>
        <article class="card answer" id="q8"><div class="q">Q8 · 方位壳是否值得下一轮实验？</div><h3>值得，但证据级别只是“进入受控实验”</h3><p>reference 真壳覆盖系统高于 shifted-shell，是积极信号；candidate-fraction/degree proxy 与 shifted 壳相近，扇内面积与边界公平性尚未完全解决。下一轮应测试“壳内 SAR-only 候选的 rank、逐帧候选数/实际角宽和时序状态是否相对公平错误壳改善”，仍由 SAR 决定最终位置。</p></article>
      </div>
    </section>

    <section id="audit">
      <h2>九、研究边界、阴性结果与可复核输出</h2>
      <div class="grid-2">
        <div class="card"><h3>这次明确没有做</h3><ul><li>没有重拟合或调参冻结 P0；</li><li>没有修改 C0–C3 或旧 P1E 结果；</li><li>没有训练分类器、回归器或构造总分；</li><li>没有使用精确光学点、physical_target_id 或插值轨迹生成候选/输运；</li><li>没有把 RGB/JET 当独立物理通道；</li><li>没有创建或移动 SAR 框；</li><li>没有授予 P1_PASS，也不声称盲验证。</li></ul></div>
        <div class="card"><h3>最重要的阴性结论</h3><ul><li>lag1 的 P0-specific PERSON 候选消歧增益仍未建立；</li><li>shared/missing 仍是离线 reference 条件标签，尚未成为 GT-blind runtime state detector；</li><li>DISPLAY_COMPRESSED_PROXY 缺乏区分力；</li><li>光学壳尚未证明提高 SAR 定位；</li><li>shared/merge-like 不能解释为物理散射融合；</li><li>所有 R01/R02/R03/R04 都是已暴露开发语料。</li></ul></div>
      </div>
      <p class="callout warning"><strong>自动验证的边界：</strong><code>report_validation.json</code> 检查文件、哈希、行数、图片、链接和必要语义短语；它不是对因果解释、光学壳公平性或动态状态接口成熟度的科学认证。本报告完成的是统一观测条件诊断，不是已经建立的 GT-blind 动态候选状态接口。candidate×P0-domain/edge 的完整分层保留在原始表中，HTML 只展示关键聚合与直接病例，尚未穷尽该分析。</p>
      <h3>可复核文件</h3>
      <div class="file-links">{output_link_html}</div>
      <p class="foot">诊断脚本 SHA256：<code>{esc(summary.get('diagnostic_script_sha256','MISSING'))}</code><br>冻结协议 SHA256：<code>{esc(summary['protocol_sha256'])}</code><br>生成时间：{esc(now_iso())}</p>
    </section>

    <section>
      <h2>附：六张条件总览图</h2>
      <div class="figure-grid">{summary_figure_html}</div>
    </section>
  </main>
</body>
</html>
"""

    context = {
        "summary": summary,
        "dynamic": dynamic,
        "observations": observations,
        "display": display,
        "tradeoff": tradeoff,
        "optical": optical,
        "condition": condition,
        "cases": cases,
        "references": references,
    }
    return html_text, context


def validate_report(html_text: str, context: dict[str, Any]) -> dict[str, Any]:
    summary = context["summary"]
    observations = context["observations"]
    checks: list[dict[str, Any]] = []

    def add(name: str, passed: bool, detail: Any) -> None:
        checks.append({"name": name, "pass": bool(passed), "detail": detail})

    required = [
        SUMMARY_PATH,
        OBSERVATIONS_PATH,
        DISPLAY_PATH,
        P0_LOCAL_PATH,
        TRADEOFF_PATH,
        OPTICAL_PATH,
        CONDITION_PATH,
        CASE_PATH,
        PROTOCOL_PATH,
        DYNAMIC_INTERPRETATION,
    ]
    add("required_inputs_exist", all(path.is_file() for path in required), [str(path) for path in required if not path.is_file()])
    add(
        "contract_input_hashes_match",
        all(bool(row.get("match")) for row in summary["input_hash_checks"]),
        summary["input_hash_checks"],
    )
    add(
        "diagnostic_script_hash_matches_summary",
        summary.get("diagnostic_script_sha256") == sha256_file(DIAGNOSTIC_SCRIPT),
        {"summary": summary.get("diagnostic_script_sha256"), "actual": sha256_file(DIAGNOSTIC_SCRIPT)},
    )
    add(
        "row_counts_match_summary",
        len(observations) == summary["counts"]["observation_rows"]
        and len(context["display"]) == summary["counts"]["frame_display_rows"]
        and len(context["tradeoff"]) == summary["counts"]["lag_pair_rows"]
        and len(context["cases"]) == summary["counts"]["case_count"],
        {
            "observations": len(observations),
            "display": len(context["display"]),
            "tradeoff": len(context["tradeoff"]),
            "cases": len(context["cases"]),
        },
    )

    refs = observations[observations["entity_kind"] == "PERSON_REFERENCE"].copy()
    r02_details: dict[str, Any] = {}
    r02_pass = True
    for target_id in (
        "R02ZF_SARPERSON01",
        "R02ZF_SARPERSON02",
        "R02ZF_SARPERSON03",
        "R02ZF_SARPERSON04",
    ):
        group = refs[refs["target_id"] == target_id].copy()
        ranks = pd.to_numeric(group["nearest_C2_candidate_rank"], errors="coerce")
        rank_counts = Counter(int(value) for value in ranks.dropna())
        detail = {
            "rows": int(len(group)),
            "rank_gt5": int((ranks > 5).sum()),
            "shared": int(bool_series(group["offline_shared_flag"]).sum()),
            "missing": int((group["offline_response_state"] == "CANDIDATE_MISSING").sum()),
            "rank_counts": dict(sorted(rank_counts.items())),
        }
        r02_details[target_id] = detail
        if target_id.endswith(("01", "02")):
            r02_pass &= detail["rows"] == 9 and detail["rank_gt5"] == 9 and detail["shared"] == 7
        else:
            r02_pass &= (
                detail["rows"] == 9
                and detail["shared"] == 9
                and detail["rank_counts"] == {1: 5, 2: 3, 12: 1}
            )
    r02_pass &= r02_details["R02ZF_SARPERSON02"]["missing"] == 2
    add("R02_multilabel_rank_shared_missing_semantics", r02_pass, r02_details)

    f458 = refs[refs["frame_uid"] == "R03ZF_SARF000458"].iloc[0]
    add(
        "R03_F458_is_near_P0_retreat_not_support_truncation",
        str(f458["support_status"]) == "FULL"
        and float(f458["support_valid_fraction"]) >= 0.99
        and 0.0 < float(f458["outer_range_boundary_distance_m"]) < 1.0,
        {
            "support_status": str(f458["support_status"]),
            "support_valid_fraction": float(f458["support_valid_fraction"]),
            "outer_range_boundary_distance_m": float(f458["outer_range_boundary_distance_m"]),
        },
    )

    c2_candidates = observations[observations["entity_kind"] == "SAR_ONLY_C2_CANDIDATE"].copy()
    c2_diff = np.abs(
        pd.to_numeric(c2_candidates["C2_score_at_position"], errors="coerce")
        - pd.to_numeric(c2_candidates["candidate_score_existing"], errors="coerce")
    )
    c2_max_diff = float(c2_diff.max()) if c2_diff.notna().any() else math.nan
    add("existing_C2_candidate_score_parity", finite(c2_max_diff) and c2_max_diff <= 1e-7, {"max_abs_diff": c2_max_diff, "rows": int(c2_diff.notna().sum())})

    frozen_p1e_hash = summary["frozen_dependency_hashes"].get(str(P1E_SCRIPT))
    add(
        "existing_C0_C3_implementation_hash_preserved",
        frozen_p1e_hash == sha256_file(P1E_SCRIPT),
        {"summary": frozen_p1e_hash, "actual": sha256_file(P1E_SCRIPT)},
    )

    image_paths = [Path(str(path)) for path in context["cases"]["visual_path"]]
    image_paths += list((OUTPUT_DIR / "visualizations").glob("*.png"))
    image_paths = sorted(set(path.resolve() for path in image_paths))
    unreadable = []
    dimensions = {}
    for path in image_paths:
        try:
            with Image.open(path) as image:
                image.verify()
            with Image.open(path) as image:
                dimensions[str(path)] = list(image.size)
        except Exception as exc:  # pragma: no cover - validation path
            unreadable.append({"path": str(path), "error": repr(exc)})
    add("all_visualizations_readable", not unreadable and len(image_paths) >= 14, {"image_count": len(image_paths), "unreadable": unreadable, "dimensions": dimensions})

    local_refs = re.findall(r'(?:src|href)="([^"#]+)"', html_text)
    missing_refs = []
    for ref in local_refs:
        if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", ref):
            continue
        target = (OUTPUT_DIR / Path(ref)).resolve()
        if not target.exists():
            missing_refs.append({"ref": ref, "resolved": str(target)})
    add("html_local_references_resolve", not missing_refs, {"reference_count": len(local_refs), "missing": missing_refs})

    required_phrases = [
        "不是人体固有 RCS",
        "SAR 在壳内仍凭自己的",
        "没有授予 P1_PASS",
        "P0-specific PERSON 候选消歧增益仍未建立",
        "不能把 shared/merge-like 写成物理散射融合",
        "不是已经建立的 GT-blind 动态候选状态接口",
    ]
    add("semantic_boundaries_present", all(phrase in html_text for phrase in required_phrases), {phrase: phrase in html_text for phrase in required_phrases})
    add("all_eight_questions_present", all(f'id="q{index}"' in html_text for index in range(1, 9)), {"question_ids": [f"q{index}" for index in range(1, 9)]})
    add(
        "no_new_pass_fail_semantics",
        summary["status"] == "OBSERVATION_MODEL_DIAGNOSTIC_COMPLETE_NO_NEW_PASS_FAIL"
        and not summary["semantic_boundaries"]["new_PASS_or_FAIL_claimed"],
        {"status": summary["status"], "claimed": summary["semantic_boundaries"]["new_PASS_or_FAIL_claimed"]},
    )
    add(
        "frozen_boundaries_preserved",
        not summary["semantic_boundaries"]["P0_retuned_or_refit"]
        and not summary["semantic_boundaries"]["C0_C3_modified"]
        and summary["semantic_boundaries"]["SAR_boxes_created_or_moved"] == 0,
        summary["semantic_boundaries"],
    )

    status = "PASS" if all(item["pass"] for item in checks) else "FAIL"
    return {
        "schema": "PERSON_P1E_OBSERVATION_MODEL_REPORT_VALIDATION_V1",
        "created_at": now_iso(),
        "status": status,
        "checks_passed": sum(item["pass"] for item in checks),
        "checks_total": len(checks),
        "report_path": str(REPORT_PATH),
        "report_sha256": sha256_file(REPORT_PATH) if REPORT_PATH.is_file() else None,
        "report_script_path": str(SCRIPT_PATH),
        "report_script_sha256": sha256_file(SCRIPT_PATH),
        "diagnostic_script_sha256": sha256_file(DIAGNOSTIC_SCRIPT),
        "checks": checks,
    }


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    html_text, context = build_report()
    REPORT_PATH.write_text(html_text, encoding="utf-8")
    validation = validate_report(html_text, context)
    VALIDATION_PATH.write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": validation["status"], "checks": f"{validation['checks_passed']}/{validation['checks_total']}", "report": str(REPORT_PATH), "validation": str(VALIDATION_PATH)}, ensure_ascii=False, indent=2))
    if validation["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
