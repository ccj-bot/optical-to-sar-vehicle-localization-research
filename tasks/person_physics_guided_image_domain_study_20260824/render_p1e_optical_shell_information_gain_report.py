#!/usr/bin/env python3
"""Render and validate the matched-cost optical-shell information-gain report."""

from __future__ import annotations

import hashlib
import html
import json
import math
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
from PIL import Image


SCRIPT_PATH = Path(__file__).resolve()
TASK_DIR = SCRIPT_PATH.parent
WORKSPACE = TASK_DIR.parents[1]
STUDY_OUTPUT = WORKSPACE / "output" / "person_physics_guided_image_domain_study_20260824"
OUTPUT_DIR = (
    STUDY_OUTPUT
    / "p1e_sar_only_response_interface"
    / "optical_shell_information_gain_v1"
)

SUMMARY_PATH = OUTPUT_DIR / "diagnostic_summary.json"
PROTOCOL_PATH = OUTPUT_DIR / "00_MATCHED_OPTICAL_SHELL_INFORMATION_GAIN_PROTOCOL_FROZEN_BEFORE_RUN.md"
BASELINE_HASH_PATH = OUTPUT_DIR / "initial_run_core_hash_baseline.json"
SHELL_DEFINITION_PATH = OUTPUT_DIR / "shell_definition_table.csv"
SHELL_CANDIDATE_PATH = OUTPUT_DIR / "shell_candidate_table.csv"
SHELL_METRICS_PATH = OUTPUT_DIR / "shell_candidate_metrics.csv"
EVALUATION_PATH = OUTPUT_DIR / "offline_reference_shell_evaluation.csv"
COMPARISON_PATH = OUTPUT_DIR / "reference_true_vs_matched_null.csv"
RUN_TARGET_PATH = OUTPUT_DIR / "run_target_shell_information_gain.csv"
APPLICABILITY_PATH = OUTPUT_DIR / "reference_optical_prior_applicability.csv"
UNCONDITIONAL_PATH = OUTPUT_DIR / "unconditional_reference_summary.csv"
TOPK_PATH = OUTPUT_DIR / "topk_shell_recall_summary.csv"
CONDITIONED_PATH = OUTPUT_DIR / "conditioned_shell_information_gain.csv"
BOTH_RETAIN_PATH = OUTPUT_DIR / "conditional_both_shells_retain_rank_summary.csv"
CANDIDATE_FRAME_PATH = OUTPUT_DIR / "candidate_frame_search_cost_p0_summary.csv"
MISSING_PATH = OUTPUT_DIR / "true_shell_candidate_missing_audit.csv"
CASE_PATH = OUTPUT_DIR / "case_registry.csv"
NO_SHELL_PATH = OUTPUT_DIR / "no_optical_shell_frames.csv"
REPORT_PATH = OUTPUT_DIR / "P1E_MATCHED_OPTICAL_SHELL_INFORMATION_GAIN_REPORT.html"
VALIDATION_PATH = OUTPUT_DIR / "report_validation.json"
ANALYSIS_SCRIPT = TASK_DIR / "run_p1e_optical_shell_information_gain.py"


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
    return f"{float(value):.{digits}f}" if finite(value) else missing


def pct(value: Any, digits: int = 1, missing: str = "—") -> str:
    return f"{100.0 * float(value):.{digits}f}%" if finite(value) else missing


def make_table(headers: Iterable[str], rows: Iterable[Iterable[Any]], classes: str = "") -> str:
    head = "".join(f"<th>{esc(item)}</th>" for item in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{item}</td>" for item in row) + "</tr>" for row in rows
    )
    return (
        f'<div class="table-wrap"><table class="{esc(classes)}">'
        f"<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>"
    )


def relative_asset(path: Path) -> str:
    return Path(os.path.relpath(path, OUTPUT_DIR)).as_posix()


def image_block(path: Path, title: str, caption: str, eager: bool = False) -> str:
    return f"""
    <figure class="evidence-figure">
      <a href="{esc(relative_asset(path))}" target="_blank" rel="noopener">
        <img src="{esc(relative_asset(path))}" alt="{esc(title)}" loading="{'eager' if eager else 'lazy'}">
      </a>
      <figcaption><strong>{esc(title)}</strong><br>{caption}</figcaption>
    </figure>
    """


def select_row(data: pd.DataFrame, **conditions: Any) -> pd.Series:
    selected = data
    for column, value in conditions.items():
        selected = selected[selected[column] == value]
    if len(selected) != 1:
        raise RuntimeError(f"expected one row for {conditions}, found {len(selected)}")
    return selected.iloc[0]


def build_report() -> tuple[str, dict[str, Any]]:
    summary = load_json(SUMMARY_PATH)
    baseline = load_json(BASELINE_HASH_PATH)
    shell_definitions = pd.read_csv(SHELL_DEFINITION_PATH, low_memory=False)
    evaluation = pd.read_csv(EVALUATION_PATH, low_memory=False)
    comparison = pd.read_csv(COMPARISON_PATH, low_memory=False)
    run_target = pd.read_csv(RUN_TARGET_PATH, low_memory=False)
    applicability = pd.read_csv(APPLICABILITY_PATH, low_memory=False)
    unconditional = pd.read_csv(UNCONDITIONAL_PATH, low_memory=False)
    topk = pd.read_csv(TOPK_PATH, low_memory=False)
    conditioned = pd.read_csv(CONDITIONED_PATH, low_memory=False)
    both_retain = pd.read_csv(BOTH_RETAIN_PATH, low_memory=False)
    candidate_frame = pd.read_csv(CANDIDATE_FRAME_PATH, low_memory=False)
    missing = pd.read_csv(MISSING_PATH, low_memory=False)
    cases = pd.read_csv(CASE_PATH, low_memory=False)

    overall = summary["overall_reference_comparison"]
    geometry = summary["geometry_fairness"]
    unconditional_overall = select_row(unconditional, scope_type="OVERALL", scope_value="ALL")
    both_overall = select_row(both_retain, scope_type="OVERALL", scope_value="ALL")
    candidate_frame_overall = select_row(
        candidate_frame, condition_dimension="OVERALL", condition_value="ALL"
    )

    topk_overall = topk[(topk["scope_type"] == "OVERALL") & (topk["radius_m"] == 0.8)]
    topk_rows = [
        [
            int(row.K),
            pct(row.true_recall_unconditional_all_references),
            pct(row.true_recall_available_references),
            pct(row.matched_null_recall_available_references),
            pct(row.true_minus_matched_null_available),
            pct(row.true_recall_given_reference_inside_shell),
            pct(row.matched_null_recall_given_reference_inside_shell),
        ]
        for row in topk_overall.sort_values("K").itertuples(index=False)
    ]

    r02 = run_target[run_target["run_id"] == "R02ZF"].copy()
    r02["person"] = r02["target_id"].astype(str).str.extract(r"PERSON(\d+)$", expand=False).map(
        lambda value: f"P{value}"
    )
    r02_rows = [
        [
            row.person,
            int(row.reference_rows),
            pct(row.true_reference_coverage),
            pct(row.true_candidate_presence_0p8m),
            f"{num(row.global_best_rank_median, 1)} → {num(row.true_shell_local_rank_median, 1)}",
            pct(row.true_one_to_one_coverage),
            pct(row.true_shared_fraction),
            pct(row.true_candidate_burden_mean),
            pct(row.null_candidate_burden_median_mean),
        ]
        for row in r02.sort_values("person").itertuples(index=False)
    ]

    unavailable = applicability[applicability["optical_prior_unavailable"].astype(bool)]
    unavailable_rows = [
        [row.run_id, int(row.frame_index), str(row.target_id).replace(f"{row.run_id}_SARPERSON", "P"), row.optical_prior_unavailable_reason]
        for row in unavailable.itertuples(index=False)
    ]

    condition_rows = []
    for dimension, values in (
        ("P0_DOMAIN", ["P0_TRANSPORT_CORE", "P0_TRANSPORT_EXTENDED", "P0_TRANSPORT_UNAVAILABLE"]),
        ("DISPLAY_SHIFT", ["False", "True"]),
        ("COMMON_FOV", ["MULTIMODAL_COMMON_FOV_PROVISIONAL", "OUTSIDE_PROVISIONAL_COMMON_FOV"]),
    ):
        for value in values:
            selected = conditioned[
                (conditioned["condition_dimension"] == dimension)
                & (conditioned["condition_value"].astype(str) == value)
            ]
            if selected.empty:
                continue
            row = selected.iloc[0]
            condition_rows.append(
                [
                    dimension,
                    value,
                    int(row.reference_rows),
                    pct(row.true_candidate_presence_0p8m),
                    pct(row.null_candidate_presence_0p8m_mean),
                    pct(row.true_minus_null_candidate_presence),
                    pct(row.true_top5_0p8m),
                    pct(row.true_shared_fraction),
                ]
            )

    missing_rows = [
        [
            row.run_id,
            int(row.frame_index),
            str(row.target_id).replace(f"{row.run_id}_SARPERSON", "P"),
            num(row.reference_C2_percentile, 3),
            num(row.reference_nearest_C2_candidate_distance_m_full_fan, 3),
            row.reference_support_status,
            row.p0_transport_domain_lag1,
            "是" if bool(row.display_shift) else "否",
        ]
        for row in missing.itertuples(index=False)
    ]

    case_captions = {
        "R02_P02_F482_RESPONSE_PRESENT_PEAK_MISSING": "reference 处连续 C2 percentile 约 0.959，但 0.8 m 内没有离散 local-max/NMS candidate；TRUE 壳保留方位，不能凭空造出峰。",
        "R02_P03_P04_SHARED_AFTER_TRUE_SHELL": "TRUE 壳保留高响应候选，但同一邻近候选仍可同时支持多个 reference；这是图像域 shared，不是物理散射融合证明。",
        "R03_F458_OUTER_BOUNDARY_COMMON_FOV": "位于冻结 P0 的 1 m 外边界退让附近，但支持核仍为 FULL；全场 rank 18 经 TRUE 壳变为 local rank 1。",
        "R03_F494_SINGLE_FRAME_VISIBLE_P0_UNAVAILABLE": "P0 transport unavailable 不等于单帧不可观察；TRUE 壳把全场 rank 6 变为 local rank 1。",
        "R02_P01_TRUE_SHELL_BEST_INFORMATION_GAIN": "P01 的低 rank 候选被正确方位壳保留并显著缩小候选池，但当帧仍可能与他人共享。",
        "R02_P02_TRUE_SHELL_BEST_INFORMATION_GAIN": "P02 的成功侧病例：低 rank 候选进入更小的方位问题；这不是唯一定位已经解决。",
        "R04_TRUE_SHELL_BEST_INFORMATION_GAIN": "R04 中 TRUE 壳保留 reference 邻近候选，而同成本 NULL 壳落在错误方位。",
        "R04_TRUE_SHELL_WORST_OR_NULL_LIKE_CASE": "明确失败：TRUE 壳把 reference 排除；粗映射/common-FoV 只能作为 provisional 先验。",
        "R02_P02_F490_HIGH_RESPONSE_JUST_OUTSIDE_CANDIDATE_RADIUS": "reference 处 C2 percentile 约 0.993，最近峰距 0.820 m，刚超出固定 0.8 m；说明 missing 标签对峰表示与半径敏感。",
    }
    case_html = "".join(
        image_block(
            Path(row.visualization_path),
            f"{row.case_id} · {row.case_slug}",
            case_captions.get(row.case_slug, esc(row.selection_reason)),
            eager=index < 2,
        )
        for index, row in enumerate(cases.itertuples(index=False))
    )

    summary_figures = [
        (
            "matched_null_geometry_fairness.png",
            "Matched-null 几何公平性",
            "实际扇内角宽、有效面积、common-FoV 与边界差连续报告；没有删除 C 级困难控制。",
        ),
        (
            "true_vs_null_information_gain_by_run.png",
            "TRUE 与 matched NULL 的 run 级保留",
            "主要差异来自正确方位覆盖与候选保留，不来自更小的搜索面积。",
        ),
        (
            "r02_global_to_shell_local_rank.png",
            "R02 全场 rank 到壳内 rank",
            "P01/P02 的问题明显变小，但 P03/P04 共享仍在；NULL 在 R02 不覆盖 reference，因此不能作条件 local-rank 对照。",
        ),
        (
            "p0_display_conditioned_shell_gain.png",
            "P0/display 作为条件",
            "仅在已有 C2 candidate 的 120 帧上比较；不构造加权总分。",
        ),
    ]
    summary_figure_html = "".join(
        image_block(OUTPUT_DIR / "visualizations" / name, title, caption)
        for name, title, caption in summary_figures
    )

    output_files = [
        PROTOCOL_PATH,
        SUMMARY_PATH,
        SHELL_DEFINITION_PATH,
        SHELL_METRICS_PATH,
        APPLICABILITY_PATH,
        UNCONDITIONAL_PATH,
        TOPK_PATH,
        CONDITIONED_PATH,
        BOTH_RETAIN_PATH,
        CANDIDATE_FRAME_PATH,
        MISSING_PATH,
        CASE_PATH,
    ]
    output_links = "".join(
        f'<a href="{esc(relative_asset(path))}" target="_blank" rel="noopener">{esc(path.name)}</a>'
        for path in output_files
    )

    html_text = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PERSON P1E · 等搜索成本光学方位壳信息增益</title>
  <style>
    :root {{ --ink:#142337; --muted:#5d6b7c; --paper:#f5f7fb; --card:#fff; --line:#d9e0ea; --green:#0c8c61; --orange:#c66b15; --blue:#2967c8; --pink:#b33676; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; background:var(--paper); color:var(--ink); font:15px/1.65 "Segoe UI","Microsoft YaHei",sans-serif; }}
    header {{ padding:46px max(24px,calc((100vw - 1180px)/2)); color:white; background:linear-gradient(125deg,#12243c,#1e4965 58%,#176b5a); }}
    header h1 {{ margin:0 0 10px; font-size:clamp(28px,4vw,48px); line-height:1.15; }}
    header p {{ max-width:960px; margin:8px 0; color:#d9edf1; font-size:17px; }}
    .status {{ display:inline-block; margin-top:14px; padding:7px 12px; border:1px solid #82cab7; border-radius:999px; background:#0a4c40; font-weight:700; }}
    nav {{ position:sticky; top:0; z-index:5; display:flex; gap:10px; overflow:auto; padding:10px max(20px,calc((100vw - 1180px)/2)); background:#ffffffee; border-bottom:1px solid var(--line); backdrop-filter:blur(8px); }}
    nav a {{ color:#29445f; text-decoration:none; white-space:nowrap; padding:5px 9px; border-radius:7px; }} nav a:hover {{ background:#e9f0f7; }}
    main {{ width:min(1180px,calc(100% - 32px)); margin:28px auto 80px; }}
    section {{ margin:24px 0; padding:26px; background:var(--card); border:1px solid var(--line); border-radius:16px; box-shadow:0 8px 28px #1c355008; }}
    h2 {{ margin:0 0 16px; font-size:27px; }} h3 {{ margin:0 0 8px; font-size:18px; }}
    .lead {{ font-size:17px; color:#354a61; }}
    .grid-2 {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:16px; }}
    .grid-4 {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; }}
    .card {{ padding:18px; border:1px solid var(--line); border-radius:12px; background:#fbfcfe; }}
    .metric {{ padding:16px; border-left:4px solid var(--blue); border-radius:10px; background:#f3f7fd; }}
    .metric strong {{ display:block; font-size:26px; color:#174f9a; }}
    .callout {{ margin:16px 0; padding:16px 18px; border-left:5px solid var(--green); background:#effaf6; border-radius:10px; }}
    .warning {{ border-left-color:var(--orange); background:#fff7ed; }}
    .negative {{ border-left-color:var(--pink); background:#fff2f7; }}
    .table-wrap {{ overflow:auto; margin:14px 0; }} table {{ width:100%; border-collapse:collapse; min-width:760px; }} th,td {{ padding:9px 10px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; }} th {{ position:sticky; top:0; background:#edf2f7; color:#31475e; }}
    .figure-grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:18px; }}
    .evidence-figure {{ margin:0; padding:12px; border:1px solid var(--line); border-radius:12px; background:#fbfcfe; }} .evidence-figure img {{ display:block; width:100%; height:auto; border-radius:8px; }} figcaption {{ padding:10px 3px 2px; color:var(--muted); }}
    code {{ padding:2px 5px; border-radius:5px; background:#edf2f7; }}
    .answer .q {{ color:var(--blue); font-weight:800; margin-bottom:6px; }}
    .file-links {{ display:flex; flex-wrap:wrap; gap:9px; }} .file-links a {{ padding:7px 10px; border:1px solid var(--line); border-radius:8px; color:#21538b; text-decoration:none; background:#f8fbff; }}
    .foot {{ color:var(--muted); font-size:13px; }}
    @media (max-width:850px) {{ .grid-2,.grid-4,.figure-grid {{ grid-template-columns:1fr; }} section {{ padding:19px; }} }}
  </style>
</head>
<body>
<header>
  <h1>等搜索成本光学方位壳：保留了什么，没解决什么</h1>
  <p>研究问题：在实际 SAR 扇面内匹配角宽、面积、边界裁剪和时间窗后，正确粗光学方位先验是否比明确偏移的错误先验更能保留 PERSON 附近的既有 SAR-only C2 响应，同时把全扇面候选问题缩小。</p>
  <span class="status">MATCHED_OPTICAL_SHELL_DIAGNOSTIC_COMPLETE_NO_NEW_PASS_FAIL</span>
</header>
<nav><a href="#conclusion">结论</a><a href="#design">公平设计</a><a href="#decomposition">信息分解</a><a href="#r02">R02</a><a href="#conditions">P0/display/边界</a><a href="#missing">missing</a><a href="#cases">病例图</a><a href="#answers">七问</a><a href="#audit">审计</a></nav>
<main>
  <section id="conclusion">
    <h2>一、结论先行</h2>
    <div class="callout"><strong>有稳定的跨模态几何信息，但没有建立新的壳内 SAR 唯一定位能力。</strong>在 245 条有 TRUE 壳的 reference 上，TRUE 保留 0.8 m 邻近候选为 {pct(overall['true_candidate_presence_0p8m'])}，matched NULL 为 {pct(overall['matched_null_candidate_presence_0p8m'])}；两者 reference 加权的候选负担中位数却几乎相同：{pct(overall['true_candidate_burden_median'])} vs {pct(overall['matched_null_candidate_burden_median'])}。</div>
    <div class="grid-4">
      <div class="metric"><span>TRUE 几何覆盖</span><strong>{pct(overall['true_reference_geometry_coverage'])}</strong><small>matched NULL {pct(overall['matched_null_reference_geometry_coverage'])}</small></div>
      <div class="metric"><span>TRUE 候选保留</span><strong>{pct(overall['true_candidate_presence_0p8m'])}</strong><small>matched NULL {pct(overall['matched_null_candidate_presence_0p8m'])}</small></div>
      <div class="metric"><span>Top-5 / 0.8 m</span><strong>{pct(select_row(topk_overall, K=5).true_recall_available_references)}</strong><small>matched NULL {pct(select_row(topk_overall, K=5).matched_null_recall_available_references)}</small></div>
      <div class="metric"><span>严格一对一覆盖</span><strong>{pct(overall['true_one_to_one_inside_coverage_0p8m'])}</strong><small>matched NULL {pct(overall['matched_null_one_to_one_inside_coverage_0p8m'])}</small></div>
    </div>
    <div class="callout negative"><strong>局部唯一性阴性结果：</strong>在 TRUE 与至少一个 NULL 都保留 reference 邻近候选的 {int(both_overall.both_shells_retain_reference_neighbor_rows)} 条记录中，TRUE-vs-NULL 的 local-rank 中位优势为 {num(both_overall.rank_advantage_true_vs_null_median,1)}；{pct(both_overall.rank_tie_fraction)} 持平，TRUE 更好仅 {pct(both_overall.true_rank_better_fraction)}，更差 {pct(both_overall.true_rank_worse_fraction)}。光学壳提供的是“去哪一段方位找”的信息，不会让 C2 响应自动变得更 PERSON-specific。</div>
  </section>

  <section id="design">
    <h2>二、什么叫“等搜索成本”</h2>
    <p class="lead">TRUE 壳与每帧 3 个错误壳都先由光学窗口、固定映射、SAR 扇面、单帧有效掩膜和 provisional common-FoV 产生。reference、C2 候选与分数均不参与 NULL 选择；之后才把既有 GT-blind C2 candidates 截取进各壳，最后用 reference 离线评价。</p>
    <div class="grid-2">
      <div class="card"><h3>控制实际匹配到的量</h3><ul><li>376 个 TRUE 壳，每帧固定 3 个 matched NULL，共 1,128 个；</li><li>角宽误差中位 {num(geometry['width_relative_error_median'],6)}，P90 {num(geometry['width_relative_error_p90'],6)}；</li><li>面积误差中位 {num(geometry['area_relative_error_median'],6)}，P90 {num(geometry['area_relative_error_p90'],6)}；</li><li>common-FoV overlap 差中位 {num(geometry['common_fov_overlap_diff_median'],4)}；</li><li>|shift| 中位 {num(geometry['shift_abs_median_deg'],1)}°，TRUE/NULL Jaccard 中位 {num(geometry['angular_jaccard_median'],3)}。</li></ul></div>
      <div class="card"><h3>没有被匹配成同一量的条件</h3><p>P0 reliability 与局部 candidate density 作为观测条件报告，不进入 NULL 选择总分。仅看有 C2 candidate 的 120 帧，TRUE/NULL candidate burden 中位为 {pct(candidate_frame_overall.true_candidate_burden_median)} / {pct(candidate_frame_overall.null_candidate_burden_median)}；TRUE 的 P0 core 比例反而更低（{pct(candidate_frame_overall.true_p0_core_fraction_median)} vs {pct(candidate_frame_overall.null_p0_core_fraction_median)}），fallback 更高（{pct(candidate_frame_overall.true_p0_fallback_fraction_median)} vs {pct(candidate_frame_overall.null_p0_fallback_fraction_median)}）。因此 TRUE 优势不能解释为“采到了更可靠 P0 区域”。</p></div>
    </div>
    {image_block(OUTPUT_DIR / 'visualizations' / 'matched_null_geometry_fairness.png', 'Matched-null 几何公平性', 'A/B/C 控制质量全部保留并连续报告。搜索成本按实际扇内角宽与有效面积定义，不按结果后候选数量挑壳。', eager=True)}
  </section>

  <section id="decomposition">
    <h2>三、优势来自哪里</h2>
    <p>TRUE 与 NULL 的总体候选保留差为 {pct(overall['true_candidate_presence_0p8m'] - overall['matched_null_candidate_presence_0p8m'])}，与几何覆盖差 {pct(overall['true_reference_geometry_coverage'] - overall['matched_null_reference_geometry_coverage'])} 几乎一致。给定 reference 已经落入壳内后，邻近候选存在率为 TRUE {pct(overall['true_candidate_presence_given_reference_inside'])}、NULL {pct(overall['matched_null_candidate_presence_given_reference_inside'])}；Top-5 为 {pct(overall['true_top5_0p8m_given_reference_inside'])} / {pct(overall['matched_null_top5_0p8m_given_reference_inside'])}。这表明主要新增信息是正确方位覆盖，不是 C2 在 TRUE 壳内发生了新的判别变化。</p>
    {make_table(['K','TRUE·全251','TRUE·有壳245','NULL·有壳245','TRUE−NULL','TRUE | ref在壳内','NULL | ref在壳内'], topk_rows)}
    <div class="grid-2">
      <div class="card"><h3>全 251 条 reference 的无条件口径</h3><p>光学先验可用 {int(unconditional_overall.optical_prior_available_count)}/{int(unconditional_overall.reference_count_total)}（{pct(unconditional_overall.optical_prior_available_fraction)}）。将不可用也计入分母后，TRUE 中心覆盖与 0.8 m 候选保留均为 {pct(unconditional_overall.reference_inside_true_shell_unconditional)}，Top-5/0.8 m 为 {pct(select_row(topk_overall, K=5).true_recall_unconditional_all_references)}。这 6 条没有被静默删除。</p></div>
      <div class="card"><h3>同壳条件下没有 local-rank 增益</h3><p>两类壳都保留邻近候选时，TRUE local rank 中位 {num(both_overall.true_shell_local_rank_median,1)}，NULL 中位 {num(both_overall.matched_null_local_rank_median,1)}。这不是 optical shell 失败，而是它解决的层次有限：缩小搜索方位，不改写 SAR-only 响应排序。</p></div>
    </div>
    <h3>明确的 OPTICAL_PRIOR_UNAVAILABLE</h3>
    {make_table(['run','frame','PERSON','原因'], unavailable_rows)}
  </section>

  <section id="r02">
    <h2>四、R02：低 rank 变简单，但 shared 没有消失</h2>
    {make_table(['PERSON','帧数','TRUE中心覆盖','TRUE候选存在','global→TRUE local rank 中位','一对一覆盖','shared','TRUE burden','NULL burden'], r02_rows)}
    <div class="grid-2">
      <div class="card"><h3>P01 / P02</h3><p>P01 从全扇面 rank 中位 11 变为 TRUE 壳内 3，9/9 保留邻近候选；P02 从 18 变为 6，7/9 保留。说明它们确有“全扇面竞争被方位先验削弱”的成分。但 P01/P02 各 7/9 同时 shared；P02 的 F482/F490 仍无 0.8 m 离散峰，所以不是唯一定位已经成立。</p></div>
      <div class="card"><h3>P03 / P04</h3><p>二者 global rank 中位 1 → TRUE local rank 1，且在 TRUE 覆盖的 7/9 帧中仍共享同一邻近响应。TRUE 壳还分别把 2/9 reference 排除。结论很直接：粗方位壳能解决搜索范围，不能解决多人近邻下的 SAR 空间共享/未分离。</p></div>
    </div>
    <p class="callout warning"><strong>R02 的 null 限制：</strong>三个 matched NULL 在 R02 的 reference 几何覆盖均为 0，因此 R02 能可靠说明 TRUE 壳把低 rank 问题缩小，却不能在“TRUE 与 NULL 都保留同一 reference 邻域”的条件下比较 local rank。条件 local-rank 阴性结果主要来自 R01/R04 的 114 条记录。</p>
    {image_block(OUTPUT_DIR / 'visualizations' / 'r02_global_to_shell_local_rank.png', 'R02 全场 rank → TRUE 壳内 rank', 'NULL 不覆盖 R02 reference，图中的 NULL rank 缺失不是 0，也不应被当作 TRUE 的无限优势。')}
  </section>

  <section id="conditions">
    <h2>五、P0、display、边界与 common-FoV 只作为条件</h2>
    {make_table(['条件维度','条件值','n','TRUE候选存在','NULL候选存在','差值','TRUE Top-5','TRUE shared'], condition_rows)}
    <div class="grid-2">
      <div class="card"><h3>P0 与 optical shell 是不同证据</h3><p>TRUE 壳没有更集中在 P0 CORE；候选帧上 TRUE core 中位反而比 NULL 低约 {pct(candidate_frame_overall.null_p0_core_fraction_median - candidate_frame_overall.true_p0_core_fraction_median)}。R03 F494 即使 P0 unavailable，TRUE 壳仍把 global rank 6 变为 local rank 1。不能把方位先验增益解释成公共输运更可靠。</p></div>
      <div class="card"><h3>display 分层不是因果</h3><p>DISPLAY_SHIFT=False/True 下 TRUE 相对 NULL 的候选保留优势都存在，但分别约 69.5 与 50.0 个百分点；run、边界、壳位置同时变化，不能归因于显示链改变 PERSON 回波。RGB/JET 仍只是同一显示标量代理，不是独立雷达物理通道；当前研究对象不是人体固有 RCS。</p></div>
      <div class="card"><h3>common-FoV 给出可观察状态</h3><p>在 provisional common-FoV 内的 225 条有壳 reference 上，TRUE 候选存在率约 95.6%；在其外 20 条仅 20.0%，TRUE−NULL 差也缩至约 6.7 个百分点。common-FoV 可用于解释先验何时失效，但不是新的硬 gate。</p></div>
      <div class="card"><h3>边界病例</h3><p>R03 F458 的支持核为 FULL，只是接近冻结 P0 的 1 m 外边界退让；TRUE 壳仍将 rank 18 → 1。R04 F005 则被 TRUE 壳排除，是粗映射/共同视场失败的直接反例。不能删除这类困难帧。</p></div>
    </div>
    {image_block(OUTPUT_DIR / 'visualizations' / 'p0_display_conditioned_shell_gain.png', 'P0/display 条件下的搜索负担', '图只使用有 C2 candidate 的 120 帧；条件并列报告，没有被合成新的加权总分。')}
  </section>

  <section id="missing">
    <h2>六、candidate missing 不等于响应不存在</h2>
    {make_table(['run','frame','PERSON','reference C2 percentile','最近离散峰距/m','support','P0','display shift'], missing_rows)}
    <p class="callout"><strong>重复出现的表示问题：</strong>F482 的 reference C2 percentile 为 0.959，但最近峰 1.159 m；F490 percentile 为 0.993，最近峰 0.820 m，仅比固定 0.8 m 半径多约 2 cm。两者都为 FULL support、P0 CORE、无 display shift。光学壳只能保留已有响应区域，不能修复 local-max/NMS 没有产生合适离散峰的问题。后续若该模式继续出现，可研究 response-region / ridge support，但本轮没有新增算法。</p>
  </section>

  <section id="cases">
    <h2>七、九个直接病例</h2>
    <p class="lead">每张图同时给出全 SAR 扇面、TRUE 壳、matched NULL1、原始 GT-blind C2 candidates、壳内剩余 candidates、冻结 C2 response field 和离线 reference。reference 只用于图后解释。</p>
    <div class="figure-grid">{case_html}</div>
  </section>

  <section id="answers">
    <h2>八、用户提出的七个问题：直接回答</h2>
    <div class="grid-2">
      <article class="card answer" id="q1"><div class="q">Q1 · 匹配面积/角宽后，TRUE 是否仍优于错误壳？</div><h3>是，优点稳定落在方位覆盖与候选保留</h3><p>TRUE/NULL 候选负担相近，但中心覆盖 89.4% vs 26.8%，0.8 m 候选存在 89.4% vs 27.3%，Top-5 81.6% vs 24.5%。全 251 条无条件 Top-5 为 79.7%。这是开发语料中的强几何信息，不是盲验证或 P2_PASS。</p></article>
      <article class="card answer" id="q2"><div class="q">Q2 · 优势来自什么？</div><h3>主要是保留正确方位，不是减少更多候选或改变 C2 排序</h3><p>TRUE/NULL 搜索面积严格接近，reference 帧上的 burden 中位 44.6% / 44.3%。给定 reference 已在壳内，候选存在 99.1% / 97.5%，Top-5 90.9% / 87.8%；两壳都保留时 local-rank 中位优势为 0。</p></article>
      <article class="card answer" id="q3"><div class="q">Q3 · R02 P01/P02 是否主要是全扇面竞争？</div><h3>有明显这一成分，但不是全部</h3><p>P01 11→3，P02 18→6；方位壳把问题变小。P01 仍 7/9 shared，P02 仍 7/9 shared并有 F482/F490 两个峰表示 missing，所以还需要 SAR 自身的共享/区域表示或时序证据，不能让光学直接选点。</p></article>
      <article class="card answer" id="q4"><div class="q">Q4 · P03/P04 的 shared 是否仍存在？</div><h3>存在，而且方位壳没有提供空间分离</h3><p>TRUE 覆盖各 7/9；覆盖时 global/local rank 多为 1，但同一候选仍邻近多个 reference。这里只能称 shared image response / 未分离，不能把 shared/merge-like 写成物理散射融合。</p></article>
      <article class="card answer" id="q5"><div class="q">Q5 · 边界/common-FoV 提供了什么？</div><h3>提供可观察状态解释，也暴露明确失败</h3><p>common-FoV 内 TRUE 优势强，外部优势明显衰减；R03 F458/F494 说明单帧壳信息与 P0 transport 域不同，R04 F005 和 6 条 OPTICAL_PRIOR_UNAVAILABLE 则说明粗先验并非每帧可用。</p></article>
      <article class="card answer" id="q6"><div class="q">Q6 · P0/display 是否影响增益？</div><h3>存在分层共现，但未建立因果</h3><p>TRUE 壳的 P0 CORE 比例更低、fallback 更高，仍保有候选保留优势；DISPLAY_SHIFT 两层都为正，但幅度不同。它们应继续作为独立证据维度，不进入未经校准的总分。</p></article>
      <article class="card answer" id="q7"><div class="q">Q7 · 下一步最值得改善什么？</div><h3>先改善同步/runtime optical track 与壳可用性，再决定是否加 SAR 表示</h3><p>公平控制已显示粗方位映射确有搜索信息；因此下一步最值钱的不是继续堆 C4/C5，而是验证同步、建立 GT-blind runtime optical track identity、量化壳误差，并保持 SAR 决定 range 与最终响应位置。对 F482/F490 这类病例，再单独评估最小 response-region 表示。</p></article>
    </div>
  </section>

  <section id="audit">
    <h2>九、边界与可复核产物</h2>
    <div class="grid-2">
      <div class="card"><h3>明确没有做</h3><ul><li>没有重拟合/调参冻结 P0；</li><li>没有修改 B0R、C0–C3 或旧诊断；</li><li>没有用 reference、SAR range GT、physical_target_id 或人工框中心生成 TRUE/NULL 壳；</li><li>没有用“壳中心最亮点”定位；</li><li>没有新增总分、分类器、tracker 或 SAR 框；</li><li>没有把 RGB/JET 解释为人体固有 RCS；</li><li>没有授予 P1/P2 PASS，也不声称盲验证。</li></ul></div>
      <div class="card"><h3>过程隔离的准确口径</h3><p>TRUE/NULL 壳先生成，之后才截取既有 GT-blind C2 candidates，最后 materialize reference slice 做离线评价。由于候选 P0 条件与 reference 位于同一个 observation CSV，脚本为候选 parity 先读取该单体文件、再筛选 candidate rows；因此不声称严格 sealed-data process isolation，但 reference 内容没有参与 shell/null/candidate 计算。</p></div>
    </div>
    <p class="callout warning"><strong>报告状态：</strong>这是受控的多模态候选信息增益诊断，不是最终 P2，不生成 SAR 框，也不授予新的 PASS/FAIL。所有 R01/R02/R03/R04 都是已暴露开发语料；SAR 在壳内仍凭自己的 C2/image/geometry/temporal evidence 判断，保留最终定位权。</p>
    <div class="file-links">{output_links}</div>
    <p class="foot">分析脚本 SHA256：<code>{esc(summary['analysis_script_sha256'])}</code><br>协议 SHA256：<code>{esc(summary['protocol_sha256'])}</code><br>报告生成时间：{esc(now_iso())}</p>
  </section>

  <section><h2>附：四张汇总图</h2><div class="figure-grid">{summary_figure_html}</div></section>
</main>
</body>
</html>"""

    context = {
        "summary": summary,
        "baseline": baseline,
        "shell_definitions": shell_definitions,
        "evaluation": evaluation,
        "comparison": comparison,
        "run_target": run_target,
        "applicability": applicability,
        "unconditional": unconditional,
        "topk": topk,
        "conditioned": conditioned,
        "both_retain": both_retain,
        "candidate_frame": candidate_frame,
        "missing": missing,
        "cases": cases,
    }
    return html_text, context


def validate_report(html_text: str, context: dict[str, Any]) -> dict[str, Any]:
    summary = context["summary"]
    checks: list[dict[str, Any]] = []

    def add(name: str, passed: bool, detail: Any) -> None:
        checks.append({"name": name, "pass": bool(passed), "detail": detail})

    required = [
        SUMMARY_PATH,
        PROTOCOL_PATH,
        BASELINE_HASH_PATH,
        SHELL_DEFINITION_PATH,
        SHELL_CANDIDATE_PATH,
        SHELL_METRICS_PATH,
        EVALUATION_PATH,
        COMPARISON_PATH,
        RUN_TARGET_PATH,
        APPLICABILITY_PATH,
        UNCONDITIONAL_PATH,
        TOPK_PATH,
        CONDITIONED_PATH,
        BOTH_RETAIN_PATH,
        CANDIDATE_FRAME_PATH,
        MISSING_PATH,
        CASE_PATH,
        NO_SHELL_PATH,
    ]
    add("required_inputs_exist", all(path.is_file() for path in required), [str(path) for path in required if not path.is_file()])
    add(
        "frozen_dependency_hashes_match",
        all(bool(row.get("match")) for row in summary["input_hash_checks"]),
        summary["input_hash_checks"],
    )
    add(
        "analysis_script_hash_matches_summary",
        summary["analysis_script_sha256"] == sha256_file(ANALYSIS_SCRIPT),
        {"summary": summary["analysis_script_sha256"], "actual": sha256_file(ANALYSIS_SCRIPT)},
    )

    baseline_files = context["baseline"]["files"]
    preserved = {
        name: {
            "baseline": baseline_files[name],
            "current": sha256_file(OUTPUT_DIR / name),
            "match": baseline_files[name] == sha256_file(OUTPUT_DIR / name),
        }
        for name in ("shell_definition_table.csv", "shell_candidate_table.csv", "shell_candidate_metrics.csv")
    }
    add("first_run_shell_and_candidate_core_hashes_preserved", all(row["match"] for row in preserved.values()), preserved)

    counts = summary["counts"]
    add(
        "row_counts_match_summary",
        len(context["shell_definitions"]) == counts["shell_definition_rows"]
        and len(context["evaluation"]) == counts["offline_reference_shell_rows"]
        and len(context["comparison"]) == counts["reference_true_vs_null_rows"]
        and len(context["applicability"]) == counts["reference_rows_total_unconditional"]
        and len(context["cases"]) == counts["case_count"],
        {
            "shell_definitions": len(context["shell_definitions"]),
            "evaluation": len(context["evaluation"]),
            "comparison": len(context["comparison"]),
            "applicability": len(context["applicability"]),
            "cases": len(context["cases"]),
        },
    )

    definitions = context["shell_definitions"]
    per_frame = definitions.groupby("frame_uid")["shell_kind"].value_counts().unstack(fill_value=0)
    add(
        "three_matched_nulls_per_true_shell",
        len(per_frame) == 376
        and (per_frame.get("TRUE", 0) == 1).all()
        and (per_frame.get("MATCHED_NULL", 0) == 3).all(),
        {"frame_count": len(per_frame), "counts": per_frame.sum().to_dict()},
    )
    add(
        "null_selection_is_reference_and_candidate_blind",
        not definitions["reference_used_for_shell_generation"].astype(bool).any()
        and not definitions["candidate_used_for_null_selection"].astype(bool).any()
        and not definitions["physical_target_id_used_for_shell_selection"].astype(bool).any(),
        {
            "reference_used": int(definitions["reference_used_for_shell_generation"].astype(bool).sum()),
            "candidate_used": int(definitions["candidate_used_for_null_selection"].astype(bool).sum()),
            "physical_target_id_used": int(definitions["physical_target_id_used_for_shell_selection"].astype(bool).sum()),
        },
    )

    app = context["applicability"]
    unavailable = app[app["optical_prior_unavailable"].astype(bool)]
    unavailable_keys = set(zip(unavailable["run_id"], unavailable["frame_index"].astype(int), unavailable["target_id"]))
    expected_unavailable = {
        ("R01ZF", 133, "R01ZF_SARPERSON01"),
        ("R01ZF", 135, "R01ZF_SARPERSON01"),
        ("R01ZF", 140, "R01ZF_SARPERSON01"),
        ("R01ZF", 141, "R01ZF_SARPERSON01"),
        ("R04ZF", 175, "R04ZF_SARPERSON03"),
        ("R04ZF", 180, "R04ZF_SARPERSON03"),
    }
    add(
        "all_251_references_and_six_unavailable_are_explicit",
        len(app) == 251 and unavailable_keys == expected_unavailable,
        {"reference_rows": len(app), "unavailable": sorted(unavailable_keys)},
    )

    top5 = context["topk"][
        (context["topk"]["scope_type"] == "OVERALL")
        & (context["topk"]["K"] == 5)
        & (context["topk"]["radius_m"] == 0.8)
    ].iloc[0]
    add(
        "headline_metrics_match_direct_tables",
        abs(float(top5["true_recall_available_references"]) - 0.8163265306122449) < 1e-12
        and abs(float(top5["matched_null_recall_available_references"]) - 0.2448979591836734) < 1e-12
        and counts["both_shells_retain_rank_rows"] == 114
        and counts["true_shell_candidate_missing_inside_rows"] == 2,
        top5.to_dict(),
    )

    image_paths = [Path(str(path)) for path in context["cases"]["visualization_path"]]
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
        except Exception as exc:  # pragma: no cover
            unreadable.append({"path": str(path), "error": repr(exc)})
    add(
        "all_visualizations_readable",
        not unreadable and len(context["cases"]) == 9 and len(image_paths) >= 13,
        {"image_count": len(image_paths), "unreadable": unreadable, "dimensions": dimensions},
    )

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
        "有稳定的跨模态几何信息，但没有建立新的壳内 SAR 唯一定位能力",
        "不是人体固有 RCS",
        "SAR 在壳内仍凭自己的",
        "不能把 shared/merge-like 写成物理散射融合",
        "不声称严格 sealed-data process isolation",
        "没有授予 P1/P2 PASS",
        "不授予新的 PASS/FAIL",
    ]
    add(
        "semantic_boundaries_present",
        all(phrase in html_text for phrase in required_phrases),
        {phrase: phrase in html_text for phrase in required_phrases},
    )
    add(
        "all_seven_questions_present",
        all(f'id="q{index}"' in html_text for index in range(1, 8)),
        {"question_ids": [f"q{index}" for index in range(1, 8)]},
    )
    add(
        "no_new_pass_fail_and_frozen_boundaries_preserved",
        summary["status"] == "MATCHED_OPTICAL_SHELL_DIAGNOSTIC_COMPLETE_NO_NEW_PASS_FAIL"
        and not summary["semantic_boundaries"]["new_PASS_or_FAIL_claimed"]
        and not summary["semantic_boundaries"]["P0_retuned_or_refit"]
        and not summary["semantic_boundaries"]["C0_C3_modified"]
        and summary["semantic_boundaries"]["SAR_boxes_created_or_moved"] == 0,
        summary["semantic_boundaries"],
    )

    status = "PASS" if all(check["pass"] for check in checks) else "FAIL"
    return {
        "schema": "PERSON_P1E_MATCHED_OPTICAL_SHELL_REPORT_VALIDATION_V1",
        "created_at": now_iso(),
        "status": status,
        "checks_passed": sum(check["pass"] for check in checks),
        "checks_total": len(checks),
        "report_path": str(REPORT_PATH),
        "report_sha256": sha256_file(REPORT_PATH) if REPORT_PATH.is_file() else None,
        "report_script_path": str(SCRIPT_PATH),
        "report_script_sha256": sha256_file(SCRIPT_PATH),
        "analysis_script_sha256": sha256_file(ANALYSIS_SCRIPT),
        "checks": checks,
    }


def main() -> None:
    html_text, context = build_report()
    REPORT_PATH.write_text(html_text, encoding="utf-8")
    validation = validate_report(html_text, context)
    VALIDATION_PATH.write_text(
        json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": validation["status"],
                "checks": f"{validation['checks_passed']}/{validation['checks_total']}",
                "report": str(REPORT_PATH),
                "validation": str(VALIDATION_PATH),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if validation["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
