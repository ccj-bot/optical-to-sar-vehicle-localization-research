#!/usr/bin/env python3
"""Render a first-principles HTML explanation of the completed PERSON P0 study.

The report reads frozen P0 outputs and extracts real HOLDOUT anchor examples.
It does not track anchors, fit models, tune parameters, or change the P0 result.
"""

from __future__ import annotations

import html
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


WORKSPACE = Path(r"D:\profile\research\workspace")
TASK_DIR = WORKSPACE / "tasks" / "person_physics_guided_image_domain_study_20260824"
P0_ROOT = (
    WORKSPACE
    / "output"
    / "person_physics_guided_image_domain_study_20260824"
    / "p0_common_apparent_motion"
)
OUTPUT_PATH = P0_ROOT / "P0_BACKGROUND_RESIDUAL_EXPLAINER.html"


def require_workspace_scope() -> None:
    workspace_resolved = WORKSPACE.resolve()
    for path in (TASK_DIR, P0_ROOT, OUTPUT_PATH.parent):
        if workspace_resolved not in path.resolve().parents and path.resolve() != workspace_resolved:
            raise RuntimeError(f"path outside active workspace: {path}")


def vector_norm(vector: list[float]) -> float:
    return float(math.hypot(vector[0], vector[1]))


def choose_real_anchor_examples() -> list[dict[str, Any]]:
    pair_path = P0_ROOT / "common_motion_pair_metrics.csv"
    anchor_path = P0_ROOT / "background_anchor_holdout_metrics.csv"

    pair_columns = [
        "run_id",
        "from_frame",
        "to_frame",
        "lag",
        "model",
        "model_available",
        "is_selected_frozen_model",
        "holdout_residual_median_px",
        "holdout_residual_p90_px",
        "M0_holdout_residual_median_px",
        "holdout_improved_vs_M0",
        "fit_anchor_count",
        "holdout_anchor_count",
        "display_js_divergence",
        "display_stratum",
    ]
    pairs = pd.read_csv(pair_path, usecols=pair_columns)
    selected = pairs[
        (pairs["run_id"] == "R04ZF")
        & pairs["is_selected_frozen_model"].astype(bool)
        & pairs["model_available"].astype(bool)
    ].copy()

    cases: list[dict[str, Any]] = []
    for lag in (1, 3, 5):
        group = selected[selected["lag"] == lag].copy()
        cross_pair_median = float(group["holdout_residual_median_px"].median())
        position = int(
            (group["holdout_residual_median_px"] - cross_pair_median)
            .abs()
            .to_numpy()
            .argmin()
        )
        row = group.iloc[position]
        cases.append(
            {
                "key": f"typical_lag_{lag}",
                "title": f"典型 lag {lag} 成功帧对",
                "kind": "TYPICAL_SUCCESS",
                "from_frame": int(row["from_frame"]),
                "to_frame": int(row["to_frame"]),
                "lag": int(row["lag"]),
                "model": str(row["model"]),
                "pair_holdout_median_px": float(row["holdout_residual_median_px"]),
                "pair_holdout_p90_px": float(row["holdout_residual_p90_px"]),
                "pair_M0_median_px": float(row["M0_holdout_residual_median_px"]),
                "pair_improved": bool(row["holdout_improved_vs_M0"]),
                "fit_anchor_count": int(row["fit_anchor_count"]),
                "holdout_anchor_count": int(row["holdout_anchor_count"]),
                "display_js_divergence": float(row["display_js_divergence"]),
                "display_stratum": str(row["display_stratum"]),
            }
        )

    failure_row = selected[
        (selected["from_frame"] == 168)
        & (selected["to_frame"] == 171)
        & (selected["lag"] == 3)
    ].iloc[0]
    cases.append(
        {
            "key": "failure_lag_3",
            "title": "唯一反向帧对 168→171",
            "kind": "FAILURE_RETAINED",
            "from_frame": 168,
            "to_frame": 171,
            "lag": 3,
            "model": str(failure_row["model"]),
            "pair_holdout_median_px": float(failure_row["holdout_residual_median_px"]),
            "pair_holdout_p90_px": float(failure_row["holdout_residual_p90_px"]),
            "pair_M0_median_px": float(failure_row["M0_holdout_residual_median_px"]),
            "pair_improved": bool(failure_row["holdout_improved_vs_M0"]),
            "fit_anchor_count": int(failure_row["fit_anchor_count"]),
            "holdout_anchor_count": int(failure_row["holdout_anchor_count"]),
            "display_js_divergence": float(failure_row["display_js_divergence"]),
            "display_stratum": str(failure_row["display_stratum"]),
        }
    )

    target_keys = {
        (case["from_frame"], case["to_frame"], case["lag"], case["model"])
        for case in cases
    }
    rows_by_key: dict[tuple[int, int, int, str], list[pd.DataFrame]] = {
        key: [] for key in target_keys
    }
    anchor_columns = [
        "run_id",
        "from_frame",
        "to_frame",
        "lag",
        "anchor_id",
        "anchor_split",
        "x_px",
        "y_px",
        "observed_dx_px",
        "observed_dy_px",
        "forward_backward_error_px",
        "local_gradient_ncc",
        "M1_predicted_dx_px",
        "M1_predicted_dy_px",
        "M1_residual_px",
        "M2_predicted_dx_px",
        "M2_predicted_dy_px",
        "M2_residual_px",
    ]
    for chunk in pd.read_csv(anchor_path, usecols=anchor_columns, chunksize=150_000):
        chunk = chunk[
            (chunk["run_id"] == "R04ZF") & (chunk["anchor_split"] == "HOLDOUT")
        ]
        if chunk.empty:
            continue
        for key in target_keys:
            from_frame, to_frame, lag, _model = key
            hit = chunk[
                (chunk["from_frame"] == from_frame)
                & (chunk["to_frame"] == to_frame)
                & (chunk["lag"] == lag)
            ]
            if not hit.empty:
                rows_by_key[key].append(hit)

    labels = {
        "small": "该帧对中残差较小的锚点",
        "near_median": "最接近该帧对中位数的锚点",
        "large": "该帧对中残差最大的锚点",
    }
    for case in cases:
        key = (case["from_frame"], case["to_frame"], case["lag"], case["model"])
        frames = rows_by_key[key]
        if not frames:
            raise RuntimeError(f"no HOLDOUT anchors found for {key}")
        anchors = pd.concat(frames, ignore_index=True)
        model = case["model"]
        residual_column = f"{model}_residual_px"
        predicted_dx_column = f"{model}_predicted_dx_px"
        predicted_dy_column = f"{model}_predicted_dy_px"
        anchor_median = float(anchors[residual_column].median())
        selections = [
            ("small", int(anchors[residual_column].idxmin())),
            (
                "near_median",
                int((anchors[residual_column] - anchor_median).abs().idxmin()),
            ),
            ("large", int(anchors[residual_column].idxmax())),
        ]
        extracted: list[dict[str, Any]] = []
        for label, index in selections:
            row = anchors.loc[index]
            observed = [float(row["observed_dx_px"]), float(row["observed_dy_px"])]
            predicted = [
                float(row[predicted_dx_column]),
                float(row[predicted_dy_column]),
            ]
            residual_vector = [
                observed[0] - predicted[0],
                observed[1] - predicted[1],
            ]
            extracted.append(
                {
                    "key": label,
                    "label": labels[label],
                    "anchor_id": str(row["anchor_id"]),
                    "x_px": float(row["x_px"]),
                    "y_px": float(row["y_px"]),
                    "observed": observed,
                    "observed_magnitude_px": vector_norm(observed),
                    "predicted": predicted,
                    "predicted_magnitude_px": vector_norm(predicted),
                    "residual_vector": residual_vector,
                    "residual_px": float(row[residual_column]),
                    "M0_anchor_residual_px": vector_norm(observed),
                    "forward_backward_error_px": float(row["forward_backward_error_px"]),
                    "local_gradient_ncc": float(row["local_gradient_ncc"]),
                }
            )
        case["anchors"] = extracted
        case["actual_holdout_anchor_count"] = int(len(anchors))
    return cases


def f3(value: float) -> str:
    return f"{value:.3f}"


def build_r01_rows(freeze: dict[str, Any]) -> str:
    lookup = {
        (int(row["lag"]), str(row["model"])): float(row["holdout_pair_median_residual_px"])
        for row in freeze["model_comparison"]
    }
    selected = freeze["frozen"]["selected_model_by_lag"]
    reasons = {
        1: "M3 数值最低，但 M1 只高 0.043 px，处于冻结的 0.05 px 复杂度容差内，因此选更简单的平移。",
        3: "M2 最低；M1 比 M2 高约 0.054 px，略超复杂度容差。",
        5: "M2 明显最低，局部 M3 没有带来更好留出表现。",
    }
    rows = []
    for lag in (1, 3, 5):
        cells = "".join(
            f"<td>{f3(lookup[(lag, model)])}</td>" for model in ("M0", "M1", "M2", "M3")
        )
        rows.append(
            "<tr>"
            f"<th>lag {lag}</th>{cells}"
            f"<td><span class='chip selected'>{html.escape(selected[str(lag)])}</span></td>"
            f"<td class='explain-cell'>{html.escape(reasons[lag])}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def build_r04_rows(final: dict[str, Any]) -> str:
    rows = []
    for item in final["quantitative_validation"]["background_holdout"]["by_lag"]:
        rows.append(
            "<tr>"
            f"<th>lag {int(item['lag'])} / {html.escape(str(item['selected_model']))}</th>"
            f"<td>{int(item['valid_pair_count'])}</td>"
            f"<td>{f3(float(item['M0_holdout_pair_median_px']))}</td>"
            f"<td>{f3(float(item['selected_holdout_pair_median_px']))}</td>"
            f"<td>{float(item['improvement_fraction_vs_M0']) * 100:.1f}%</td>"
            "</tr>"
        )
    return "\n".join(rows)


def build_html() -> str:
    freeze = json.loads((P0_ROOT / "model_selection_R01.json").read_text(encoding="utf-8"))
    final = json.loads((P0_ROOT / "frozen_validation_R04.json").read_text(encoding="utf-8"))
    examples = choose_real_anchor_examples()
    q = final["quantitative_validation"]
    background = q["background_holdout"]
    person = q["stationary_PERSON"]
    all_person = person["all_accepted"]
    manual_person = person["manual_endpoints"]
    short_axis = float(person["short_axis_median_px_unique_R04_boxes"])
    overall_percent = float(background["overall_improvement_fraction_vs_M0"]) * 100.0
    frame_count = max(
        int(row["valid_pair_count"]) + int(row["lag"])
        for row in background["by_lag"]
    )
    data = {
        "examples": examples,
        "selected_model_by_lag": q["selected_model_by_lag"],
        "r04_frame_count": frame_count,
        "overall_improvement_percent": overall_percent,
        "short_axis_px": short_axis,
        "model_refit": False,
    }
    data_json = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    created = datetime.now().astimezone().isoformat(timespec="seconds")

    template = r'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PERSON P0 从零讲透：背景、lag、残差与指标</title>
  <style>
    :root {
      --ink: #172033;
      --muted: #5d687a;
      --paper: #ffffff;
      --canvas: #f3f6fb;
      --line: #d9e0ea;
      --blue: #2563eb;
      --blue-soft: #eaf1ff;
      --teal: #0f8a73;
      --teal-soft: #e4f7f1;
      --orange: #dd6b20;
      --orange-soft: #fff1e6;
      --red: #c9362b;
      --red-soft: #fff0ef;
      --purple: #7c3aed;
      --shadow: 0 12px 34px rgba(23, 32, 51, .08);
    }
    * { box-sizing: border-box; }
    html { scroll-behavior: smooth; }
    body {
      margin: 0;
      color: var(--ink);
      background: var(--canvas);
      font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", Arial, sans-serif;
      line-height: 1.72;
    }
    a { color: var(--blue); }
    .hero {
      background: linear-gradient(125deg, #13213c 0%, #1f3f75 58%, #0f766e 100%);
      color: white;
      padding: 62px 24px 54px;
    }
    .hero-inner, main, .nav-inner { max-width: 1160px; margin: 0 auto; }
    .eyebrow { letter-spacing: .12em; font-size: 13px; opacity: .78; text-transform: uppercase; }
    h1 { margin: 10px 0 16px; font-size: clamp(34px, 5vw, 58px); line-height: 1.13; }
    .hero p { max-width: 920px; margin: 0; font-size: 19px; color: #e6efff; }
    .hero-badges { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 24px; }
    .hero-badges span { padding: 7px 12px; border: 1px solid rgba(255,255,255,.3); border-radius: 999px; background: rgba(255,255,255,.09); }
    nav { position: sticky; top: 0; z-index: 10; background: rgba(255,255,255,.95); border-bottom: 1px solid var(--line); backdrop-filter: blur(8px); }
    .nav-inner { display: flex; gap: 17px; overflow-x: auto; padding: 12px 20px; white-space: nowrap; }
    nav a { color: #324158; text-decoration: none; font-size: 14px; font-weight: 700; }
    main { padding: 30px 20px 80px; }
    section { background: var(--paper); border: 1px solid var(--line); border-radius: 18px; box-shadow: var(--shadow); padding: 30px; margin: 22px 0; scroll-margin-top: 72px; }
    h2 { margin: 0 0 18px; font-size: 28px; line-height: 1.25; }
    h3 { margin: 26px 0 10px; font-size: 20px; }
    h4 { margin: 18px 0 8px; }
    p { margin: 9px 0; }
    .lead { font-size: 19px; color: #344259; }
    .callout { border-left: 5px solid var(--blue); background: var(--blue-soft); padding: 18px 20px; border-radius: 10px; margin: 18px 0; }
    .callout.orange { border-color: var(--orange); background: var(--orange-soft); }
    .callout.red { border-color: var(--red); background: var(--red-soft); }
    .callout.green { border-color: var(--teal); background: var(--teal-soft); }
    .big-answer { font-size: 22px; font-weight: 800; line-height: 1.55; }
    .grid-2 { display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 18px; }
    .grid-3 { display: grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap: 16px; }
    .grid-4 { display: grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap: 14px; }
    .card { border: 1px solid var(--line); border-radius: 14px; padding: 17px; background: #fbfcff; }
    .card h3, .card h4 { margin-top: 0; }
    .card.blue { background: var(--blue-soft); border-color: #bdd0ff; }
    .card.green { background: var(--teal-soft); border-color: #b7eadb; }
    .card.orange { background: var(--orange-soft); border-color: #ffd2b3; }
    .card.red { background: var(--red-soft); border-color: #ffc8c3; }
    .term { font-weight: 800; color: #153e75; }
    .equation { font-family: Cambria, "Times New Roman", serif; font-size: 23px; background: #f7f9fc; border: 1px solid var(--line); border-radius: 12px; padding: 16px; overflow-x: auto; }
    .plain-equation { font-family: Consolas, monospace; background: #101827; color: #e9f2ff; padding: 12px 15px; border-radius: 9px; overflow-x: auto; }
    .chip { display: inline-block; border-radius: 999px; padding: 3px 9px; background: #edf1f7; font-size: 13px; font-weight: 800; }
    .chip.selected { background: #dff7ee; color: #08755f; }
    .chip.fail { background: #ffe7e4; color: #a52b23; }
    .pipeline { display: grid; grid-template-columns: repeat(6, 1fr); gap: 8px; align-items: stretch; margin: 20px 0; }
    .pipeline .step { position: relative; min-height: 92px; padding: 13px 10px; border: 1px solid var(--line); background: #f8faff; border-radius: 12px; text-align: center; font-size: 14px; font-weight: 700; display: flex; align-items: center; justify-content: center; }
    .pipeline .step:not(:last-child)::after { content: "→"; position: absolute; right: -13px; top: 33%; z-index: 2; color: #70809a; font-size: 20px; }
    table { width: 100%; border-collapse: collapse; margin: 14px 0; font-size: 14px; }
    th, td { border-bottom: 1px solid var(--line); padding: 11px 10px; text-align: left; vertical-align: top; }
    thead th { background: #f2f5fa; color: #334158; }
    .explain-cell { min-width: 260px; }
    .scroll { overflow-x: auto; }
    .timeline { display: flex; align-items: center; gap: 8px; overflow-x: auto; padding: 16px 4px; }
    .frame { min-width: 78px; padding: 12px 8px; text-align: center; border: 2px solid #b9c6d8; background: white; border-radius: 10px; font-weight: 800; }
    .frame.source { border-color: var(--blue); background: var(--blue-soft); }
    .frame.target { border-color: var(--teal); background: var(--teal-soft); }
    .gap { color: #748197; font-size: 13px; min-width: 46px; text-align: center; }
    .demo-layout { display: grid; grid-template-columns: minmax(360px, 1.05fr) minmax(350px, .95fr); gap: 22px; align-items: start; }
    .controls { display: flex; flex-wrap: wrap; gap: 8px; margin: 12px 0 16px; }
    button { font: inherit; border: 1px solid #b9c5d6; background: white; color: #27344a; border-radius: 9px; padding: 8px 11px; cursor: pointer; font-weight: 700; }
    button:hover, button.active { border-color: var(--blue); background: var(--blue-soft); color: #1747a6; }
    .anchor-table tbody tr { cursor: pointer; }
    .anchor-table tbody tr:hover, .anchor-table tbody tr.active { background: #edf4ff; }
    .metric-line { display: flex; justify-content: space-between; gap: 18px; border-bottom: 1px dashed #d7deea; padding: 8px 0; }
    .metric-line strong { font-variant-numeric: tabular-nums; }
    .legend { display: flex; flex-wrap: wrap; gap: 14px; font-size: 13px; margin-top: 8px; }
    .legend span::before { content: ""; display: inline-block; width: 18px; height: 4px; margin-right: 6px; vertical-align: middle; border-radius: 3px; }
    .legend .observed::before { background: var(--blue); }
    .legend .predicted::before { background: var(--purple); }
    .legend .residual::before { background: var(--orange); }
    svg { width: 100%; height: auto; border: 1px solid var(--line); border-radius: 13px; background: #fbfcff; }
    figure { margin: 18px 0; }
    figure img { display: block; width: 100%; height: auto; border: 1px solid var(--line); border-radius: 13px; }
    figcaption { color: var(--muted); font-size: 13px; margin-top: 7px; }
    .bar-row { display: grid; grid-template-columns: 105px 1fr 82px; gap: 12px; align-items: center; margin: 9px 0; }
    .bar-track { height: 17px; background: #edf1f6; border-radius: 999px; overflow: hidden; }
    .bar-fill { height: 100%; border-radius: 999px; }
    .bar-fill.m0 { background: #94a3b8; }
    .bar-fill.model { background: var(--blue); }
    .bar-fill.person-before { background: #f59e0b; }
    .bar-fill.person-after { background: #10b981; }
    .number { font-variant-numeric: tabular-nums; font-weight: 800; }
    .small { color: var(--muted); font-size: 13px; }
    .footer-note { color: var(--muted); font-size: 13px; text-align: center; margin-top: 26px; }
    code { background: #eef2f7; border-radius: 5px; padding: 2px 5px; }
    details { border: 1px solid var(--line); border-radius: 11px; padding: 12px 15px; margin: 10px 0; background: #fbfcff; }
    summary { cursor: pointer; font-weight: 800; }
    @media (max-width: 900px) {
      .grid-2, .grid-3, .grid-4, .demo-layout { grid-template-columns: 1fr; }
      .pipeline { grid-template-columns: 1fr; }
      .pipeline .step:not(:last-child)::after { content: "↓"; right: 50%; top: auto; bottom: -23px; }
      section { padding: 22px 17px; }
      .hero { padding-top: 46px; }
    }
    @media print {
      nav, .controls { display: none; }
      body { background: white; }
      section { box-shadow: none; break-inside: avoid; }
    }
  </style>
</head>
<body>
  <header class="hero">
    <div class="hero-inner">
      <div class="eyebrow">PERSON · SAR image-domain P0 · frozen evidence</div>
      <h1>从零讲透：背景、lag、残差与指标</h1>
      <p>这份报告不只给“通过率”，而是从一个真实背景锚点开始，解释它如何被追踪、如何产生位移、模型预测了什么、残差为什么能检验公共运动，以及这些量怎样逐层汇总到 P0_PASS。</p>
      <div class="hero-badges">
        <span>P0_PASS</span><span>R01 选型冻结</span><span>R04 完全留出</span><span>真实 HOLDOUT 锚点算例</span><span>P1 未启动</span>
      </div>
    </div>
  </header>

  <nav>
    <div class="nav-inner">
      <a href="#answer">一句话</a><a href="#background">背景是什么</a><a href="#lag">lag</a><a href="#residual">残差怎么算</a><a href="#split">拟合/留出</a><a href="#models">M0–M3</a><a href="#metrics">指标层级</a><a href="#results">结果</a><a href="#person">PERSON</a><a href="#failure">失败病例</a><a href="#boundary">结论边界</a>
    </div>
  </nav>

  <main>
    <section id="answer">
      <h2>1. 先用一句话回答：背景残差用来干什么？</h2>
      <div class="callout big-answer">
        背景残差是一个<strong>验收误差</strong>：拿没有参加模型拟合的背景点，比较“它实际在图像里移动了多少”和“公共运动模型预测它应当移动多少”。两者越接近，说明公共图像输运越能被背景独立支持。
      </div>
      <h3>它在整个 P0 里有四个具体用途</h3>
      <ol>
        <li><strong>R01 选模型：</strong>比较 M1、M2、M3 谁能更好预测未参加拟合的背景点；</li>
        <li><strong>R04 验证泛化：</strong>检查冻结模型换到完全留出的场景后是否仍优于 M0；</li>
        <li><strong>识别困难帧：</strong>背景残差大时，提示该帧对存在去相关、局部失配或低阶模型不足，不能盲信补偿；</li>
        <li><strong>给 PERSON 去混杂：</strong>只有背景模型先被独立验收，才有资格从静止 PERSON 框位移中减去公共分量。</li>
      </ol>
      <div class="grid-3">
        <div class="card blue"><h3>背景位移</h3><p><span class="term">d</span>：一个背景锚点从第一帧到第二帧实际追踪出的位移。</p><p>它回答“图像里看见这个点移了多少”。</p></div>
        <div class="card green"><h3>模型预测</h3><p><span class="term">û(x)</span>：由其他 FIT 背景锚点拟合出的公共运动，在该位置的预测。</p><p>它回答“如果这是公共输运，这里应该移多少”。</p></div>
        <div class="card orange"><h3>背景残差</h3><p><span class="term">eᴮ=||d−û(x)||</span>：观测与预测的差。</p><p>它回答“还有多少位移没有被公共模型解释”。</p></div>
      </div>
      <div class="callout orange">
        <strong>最容易混淆的一点：</strong>背景移动很大，不等于残差很大。只要模型准确预测了这个大位移，残差仍然可以很小。反过来，一个点只移动 1 px，但模型预测方向完全错了，残差也可能很大。
      </div>
    </section>

    <section id="background">
      <h2>2. 这里说的“背景”到底是什么，怎样描述？</h2>
      <p class="lead">这里没有把背景描述成“树、地面、建筑”这样的语义类别，也没有用一块区域的平均颜色代表背景。P0 把背景描述成一组<strong>可追踪的局部图像结构及其位移向量</strong>。</p>
      <div class="equation">B<sub>t,ℓ</sub> = { (x<sub>k</sub>, y<sub>k</sub>, dx<sub>k</sub>, dy<sub>k</sub>, quality<sub>k</sub>, split<sub>k</sub>) }</div>
      <div class="grid-2">
        <div>
          <h3>一个背景锚点包含什么</h3>
          <ul>
            <li><strong>(x, y)</strong>：第一帧中的图像坐标；</li>
            <li><strong>(dx, dy)</strong>：追踪到第二帧后的观测位移；</li>
            <li><strong>forward-backward error</strong>：正向追踪再反向追踪是否回到原位置；</li>
            <li><strong>local gradient NCC</strong>：两帧局部梯度结构是否仍相似；</li>
            <li><strong>FIT / HOLDOUT</strong>：用于拟合，还是只用于验收。</li>
          </ul>
        </div>
        <div>
          <h3>哪些地方不能叫背景锚点</h3>
          <ul>
            <li>PERSON 框及安全扩张区；</li>
            <li>扇面外白区；</li>
            <li>20 m 外边界邻域和扇面侧边邻域；</li>
            <li>跟踪窗口不能完整落入两帧共同有效区的位置；</li>
            <li>前后向不一致、位移过大或局部结构相关性过低的点。</li>
          </ul>
        </div>
      </div>
      <div class="pipeline">
        <div class="step">两帧 SAR 伪彩图</div><div class="step">共同有效扇面<br>屏蔽 PERSON</div><div class="step">RGB 梯度结构<br>检测角点</div><div class="step">LK 双向追踪<br>NCC 质检</div><div class="step">得到 (x,y,dx,dy)</div><div class="step">分成 FIT 与 HOLDOUT</div>
      </div>
      <div class="callout">
        <strong>所以“描述背景”不是建一个背景外观模板。</strong>真正送进模型的是很多空间位置及其位移向量。模型试图描述的是“公共位移随图像位置怎样变化”，不是“背景长什么样”。
      </div>
    </section>

    <section id="lag">
      <h2>3. lag 1、3、5 到底是什么意思？</h2>
      <p><code>lag = ℓ</code> 是两帧的<strong>帧索引间隔</strong>。从第 <code>t</code> 帧配准到第 <code>t+ℓ</code> 帧：</p>
      <div class="timeline">
        <div class="frame source">t</div><div class="gap">lag 1 →</div><div class="frame target">t+1</div><div class="gap">再隔 2 帧</div><div class="frame target">t+3</div><div class="gap">再隔 2 帧</div><div class="frame target">t+5</div>
      </div>
      <div class="grid-3">
        <div class="card"><h3>lag 1</h3><p>相邻帧：t → t+1。</p><p>R04 有 196−1=195 对。</p><p>位移通常较小，检验短间隔稳定性。</p></div>
        <div class="card"><h3>lag 3</h3><p>相隔三个帧索引：t → t+3，中间跳过两帧。</p><p>R04 有 196−3=193 对。</p><p>公共位移积累更多，也更可能出现局部去相关。</p></div>
        <div class="card"><h3>lag 5</h3><p>相隔五个帧索引：t → t+5，中间跳过四帧。</p><p>R04 有 196−5=191 对。</p><p>是更长间隔、更困难的稳定性检查。</p></div>
      </div>
      <div class="callout orange">
        <strong>lag 不是秒数。</strong>lag 3 只表示帧索引相差 3；若要换成物理时间，需要可靠时间戳或帧率。P0 没有把 lag 直接解释为真实时间或载体路程。
      </div>
      <p>总计 195+193+191=579 个帧对。这些帧对会重叠，例如同一帧可能出现在多对中，因此“579”是配准验收单元数，不宣称是 579 个统计独立场景。</p>
    </section>

    <section id="residual">
      <h2>4. 用真实锚点逐项算一次背景残差</h2>
      <p class="lead">下面的数据直接来自冻结的 <code>background_anchor_holdout_metrics.csv</code>。选择帧对，再选择“小残差 / 接近中位数 / 最大残差”锚点，图中三根箭头会同步变化。</p>
      <div class="controls" id="caseControls"></div>
      <div class="demo-layout">
        <div>
          <svg id="vectorSvg" viewBox="0 0 560 360" role="img" aria-label="观测、预测和残差向量示意">
            <defs>
              <marker id="arrowBlue" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#2563eb"/></marker>
              <marker id="arrowPurple" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#7c3aed"/></marker>
              <marker id="arrowOrange" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#dd6b20"/></marker>
            </defs>
            <line x1="40" y1="180" x2="525" y2="180" stroke="#d4dce8"/><line x1="180" y1="28" x2="180" y2="330" stroke="#d4dce8"/>
            <text x="520" y="171" fill="#718096" font-size="12">+dx</text><text x="190" y="322" fill="#718096" font-size="12">+dy（图像向下）</text>
            <circle cx="180" cy="180" r="5" fill="#172033"/><text x="145" y="201" fill="#5d687a" font-size="12">锚点起点</text>
            <line id="observedArrow" x1="180" y1="180" x2="300" y2="180" stroke="#2563eb" stroke-width="5" marker-end="url(#arrowBlue)"/>
            <line id="predictedArrow" x1="180" y1="180" x2="270" y2="180" stroke="#7c3aed" stroke-width="4" marker-end="url(#arrowPurple)"/>
            <line id="residualArrow" x1="270" y1="180" x2="300" y2="180" stroke="#dd6b20" stroke-width="5" stroke-dasharray="8 5" marker-end="url(#arrowOrange)"/>
            <circle id="observedPoint" cx="300" cy="180" r="5" fill="#2563eb"/><circle id="predictedPoint" cx="270" cy="180" r="5" fill="#7c3aed"/>
            <text id="scaleText" x="40" y="340" fill="#718096" font-size="12"></text>
          </svg>
          <div class="legend"><span class="observed">蓝：实际观测位移 d</span><span class="predicted">紫：模型预测 û(x)</span><span class="residual">橙：差值 d−û(x)</span></div>
          <div class="controls" id="anchorControls"></div>
        </div>
        <div>
          <div class="card" id="caseSummary"></div>
          <h3>逐项代入</h3>
          <div class="plain-equation" id="numericFormula"></div>
          <div class="metric-line"><span>观测位移长度 ||d||</span><strong id="observedMagnitude"></strong></div>
          <div class="metric-line"><span>预测位移长度 ||û||</span><strong id="predictedMagnitude"></strong></div>
          <div class="metric-line"><span>背景残差 ||d−û||</span><strong id="residualMagnitude"></strong></div>
          <div class="metric-line"><span>若用 M0，该锚点残差</span><strong id="m0AnchorResidual"></strong></div>
          <div class="callout green" id="anchorInterpretation"></div>
        </div>
      </div>
      <div class="scroll">
        <table class="anchor-table">
          <thead><tr><th>锚点角色</th><th>位置</th><th>观测 (dx,dy)</th><th>预测 (dx,dy)</th><th>残差向量</th><th>残差长度</th></tr></thead>
          <tbody id="anchorTableBody"></tbody>
        </table>
      </div>
      <div class="callout">
        <strong>真实 lag 1 中位锚点示例：</strong>观测约为 (1.963, −0.076) px，M1 预测约为 (1.789, −0.157) px，相减得到 (0.173, 0.080) px，二范数约 0.191 px。这个点实际移动接近 1.96 px，但绝大部分由公共平移解释，未解释部分只有约 0.19 px。
      </div>
    </section>

    <section id="split">
      <h2>5. 为什么一定要分 FIT 背景锚点和 HOLDOUT 背景锚点？</h2>
      <div class="grid-2">
        <div class="card blue">
          <h3>FIT 锚点：用来求模型参数</h3>
          <p>例如 M1 要从 FIT 锚点求一个全局平移向量，M2 要求一个仿射矩阵。</p>
          <p>FIT 残差可以发现拟合是否离谱，但不能独立证明模型会泛化。</p>
        </div>
        <div class="card green">
          <h3>HOLDOUT 锚点：只用来验收</h3>
          <p>它们不参加参数求解。模型拟合完后才到这些位置做预测并计算残差。</p>
          <p>因此“背景留出残差”相当于空间上的交叉验证误差。</p>
        </div>
      </div>
      <p>锚点按 48 px 空间单元确定性分组，约四分之一作为 HOLDOUT。不是先看残差，再把好点放进验证集。每个可比较帧对至少需要 24 个 FIT、8 个 HOLDOUT，并覆盖至少 10 个拟合空间单元。</p>
      <div class="callout red">
        如果所有背景点都参加拟合，再在同一批点上报告误差，复杂模型可能只是记住这些点。P0 的核心可信度来自：<strong>用 FIT 拟合，用 HOLDOUT 验收，再用完全留出的 R04 验证。</strong>
      </div>
    </section>

    <section id="models">
      <h2>6. M0、M1、M2、M3 分别在假设什么？</h2>
      <div class="grid-4">
        <div class="card"><h3>M0 无补偿</h3><p><code>û(x)=0</code></p><p>假设不预测任何移动。残差就是锚点实际位移长度。</p><p class="small">只是算法基线，不是“同一像素=同一物理背景”。</p></div>
        <div class="card blue"><h3>M1 全局平移</h3><p><code>û(x)=b</code></p><p>整幅有效区在所有位置使用同一个 dx、dy。</p><p class="small">适合近似整体平移。</p></div>
        <div class="card green"><h3>M2 全局仿射</h3><p><code>û(x)=(A−I)x+b</code></p><p>预测随位置线性变化，可表示平移、旋转、尺度和一阶剪切。</p><p class="small">lag 3/5 最终冻结模型。</p></div>
        <div class="card orange"><h3>M3 距离—方位场</h3><p><code>Φ=[1,r,θ,rθ,r²,θ²]</code></p><p>分别预测径向和切向位移，允许更局部的非均匀变化。</p><p class="small">更复杂，必须由留出收益证明。</p></div>
      </div>
      <h3>R01 留出背景残差中位数与冻结选择</h3>
      <div class="scroll">
        <table>
          <thead><tr><th>间隔</th><th>M0</th><th>M1</th><th>M2</th><th>M3</th><th>冻结</th><th>为什么</th></tr></thead>
          <tbody>__R01_ROWS__</tbody>
        </table>
      </div>
      <p>lag 1 中 M3 数值最小，并不意味着必须选 M3。预注册复杂度保护规定：更简单模型若落在最佳值的冻结容差内，就选更简单模型。因此 lag 1 冻结 M1；lag 3、5 冻结 M2。</p>
    </section>

    <section id="metrics">
      <h2>7. 指标是怎样一层层汇总的？每一层说明什么？</h2>
      <div class="grid-4">
        <div class="card"><h3>第1层：锚点</h3><p><code>eᴮ_k=||d_k−û(x_k)||</code></p><p>一个 HOLDOUT 背景点有多少位移未被解释。</p></div>
        <div class="card"><h3>第2层：帧对</h3><p>同一帧对所有 HOLDOUT 锚点残差的中位数。</p><p>说明这一帧对的典型背景预测误差。</p></div>
        <div class="card"><h3>第3层：lag</h3><p>同一 lag 下所有帧对中位残差的中位数和 P90。</p><p>说明该时间间隔下的总体水平和尾部。</p></div>
        <div class="card"><h3>第4层：门槛</h3><p>统计多少帧对的冻结模型优于 M0。</p><p>说明改善是否普遍，而非少数帧拉低均值。</p></div>
      </div>
      <div class="callout orange"><strong>决策指标与诊断指标要分开：</strong>真正决定 P0 的是 R04 改善帧对比例、PERSON P90 尺度门槛、框来源敏感性和遮罩/冻结完整性。FIT 残差、单帧 P90、锚点数量、显示 JS 分层和最差病例主要用于诊断“为什么好或为什么坏”，不能单独替代通过门槛。</div>
      <div class="scroll">
        <table>
          <thead><tr><th>指标</th><th>严格含义</th><th>不能误读成</th></tr></thead>
          <tbody>
            <tr><th>背景帧对残差中位数</th><td>一个帧对中，50% HOLDOUT 锚点残差不高于该数值。</td><td>真实平台定位误差。</td></tr>
            <tr><th>背景残差 P90</th><td>一个帧对或一组帧对中，90% 残差不高于该值；强调尾部。</td><td>90%“准确率”。</td></tr>
            <tr><th>578/579 改善</th><td>578 个帧对中，冻结模型的 HOLDOUT 中位残差低于同帧对 M0。</td><td>99.83% 像素正确，或 99.83% 真实运动恢复。</td></tr>
            <tr><th>PERSON 补偿残差</th><td>框中心观测位移减背景模型在框中心的预测。</td><td>人体独立物理位移。</td></tr>
            <tr><th>PERSON P90 &lt; 短轴中位数</th><td>90% PERSON 对的补偿残差小于目标典型短轴尺度。</td><td>目标定位误差已经达到 3.557 px 真值精度。</td></tr>
            <tr><th>人工端点方向一致</th><td>去掉插值端点后，补偿仍使中位数/P90下降。</td><td>人工框就是固定散射中心。</td></tr>
            <tr><th>显示 JS 分层</th><td>两帧全局显示灰度分布变化程度的描述量。</td><td>已证明是增益变化。</td></tr>
          </tbody>
        </table>
      </div>
    </section>

    <section id="results">
      <h2>8. R04 的直接背景配准结果说明什么？</h2>
      <div class="scroll">
        <table>
          <thead><tr><th>lag / 冻结模型</th><th>帧对数</th><th>M0 中位残差</th><th>冻结模型中位残差</th><th>逐帧对改善率</th></tr></thead>
          <tbody>__R04_ROWS__</tbody>
        </table>
      </div>
      <div class="grid-3">
        <div class="card"><h3>lag 1</h3><div class="bar-row"><span>M0</span><div class="bar-track"><div class="bar-fill m0" style="width:100%"></div></div><span class="number">1.878</span></div><div class="bar-row"><span>M1</span><div class="bar-track"><div class="bar-fill model" style="width:10.2%"></div></div><span class="number">0.191</span></div></div>
        <div class="card"><h3>lag 3</h3><div class="bar-row"><span>M0</span><div class="bar-track"><div class="bar-fill m0" style="width:100%"></div></div><span class="number">6.058</span></div><div class="bar-row"><span>M2</span><div class="bar-track"><div class="bar-fill model" style="width:22.5%"></div></div><span class="number">1.366</span></div></div>
        <div class="card"><h3>lag 5</h3><div class="bar-row"><span>M0</span><div class="bar-track"><div class="bar-fill m0" style="width:100%"></div></div><span class="number">10.919</span></div><div class="bar-row"><span>M2</span><div class="bar-track"><div class="bar-fill model" style="width:21.4%"></div></div><span class="number">2.336</span></div></div>
      </div>
      <div class="callout green">
        <strong>这组结果真正说明：</strong>在 R04 的未调参帧对中，背景锚点实际位移不是随机散乱到无法预测；由其他背景锚点拟合的低阶公共场，在 578/579 个帧对上比“不做补偿”更能预测 HOLDOUT 背景点。
      </div>
      <figure><img src="visualizations/R04_background_holdout_residual_by_lag.png" alt="R04各lag背景留出残差"><figcaption>这张图比较的是留出背景预测误差，不是平台轨迹误差。</figcaption></figure>
    </section>

    <section id="person">
      <h2>9. 为什么背景通过后，还要看静止 PERSON 残差？</h2>
      <p>背景残差只证明模型能预测背景。P0 还要回答：把同一个背景模型放到 PERSON 框中心，能否解释静止 PERSON 框轨迹中的大部分共同位移。</p>
      <div class="equation">e<sup>P</sup> = || Δc<sub>PERSON</sub> − û(c<sub>PERSON</sub>) ||</div>
      <div class="grid-2">
        <div class="card"><h3>全部接受框，1050 对</h3><div class="bar-row"><span>补偿前 P90</span><div class="bar-track"><div class="bar-fill person-before" style="width:100%"></div></div><span class="number">__ALL_BEFORE__</span></div><div class="bar-row"><span>补偿后 P90</span><div class="bar-track"><div class="bar-fill person-after" style="width:__ALL_AFTER_WIDTH__%"></div></div><span class="number">__ALL_AFTER__</span></div></div>
        <div class="card"><h3>两端均为人工框，120 对</h3><div class="bar-row"><span>补偿前 P90</span><div class="bar-track"><div class="bar-fill person-before" style="width:100%"></div></div><span class="number">__MANUAL_BEFORE__</span></div><div class="bar-row"><span>补偿后 P90</span><div class="bar-track"><div class="bar-fill person-after" style="width:__MANUAL_AFTER_WIDTH__%"></div></div><span class="number">__MANUAL_AFTER__</span></div></div>
      </div>
      <p>PERSON 短轴中位数为 <strong>__SHORT_AXIS__ px</strong>。P90=3.557 px 的含义是：在全部接受框口径下，90% 的可评估 PERSON 帧对补偿残差不高于 3.557 px；它不是“PERSON 定位精度真值”。</p>
      <div class="callout orange">
        背景残差小而某个 PERSON 残差仍大，说明该 PERSON 附近还有局部响应变化、显示变化或标注不确定性，不能由全场公共模型消除。这不是背景模型自动判定“人动了”。
      </div>
      <figure><img src="visualizations/R04_stationary_person_before_after.png" alt="静止PERSON补偿前后残差"><figcaption>人工端点和全部接受框方向一致，用于检查结论是否依赖插值框来源。</figcaption></figure>
    </section>

    <section id="failure">
      <h2>10. 唯一反向帧对为什么重要？</h2>
      <div class="callout red">
        R04 168→171、lag 3：冻结 M2 的 HOLDOUT 中位残差为 <strong>4.502 px</strong>，M0 为 <strong>4.287 px</strong>。这是 579 个帧对中唯一一个“补偿后反而略差”的帧对。
      </div>
      <figure><img src="visualizations/worst_05_R04ZF_000168_000171_lag3.jpg" alt="唯一背景反向帧对168到171"><figcaption>黄/白点：FIT/HOLDOUT 背景锚点；橙框：PERSON 扩张排除区；青线：有效扇面边界；白/洋红箭头：观测/M2预测。该病例原样保留。</figcaption></figure>
      <p>该帧对中，背景观测方向更分散，局部失配或去相关更明显。复核没有发现锚点吸附 PERSON 或扇面边界，因此它揭示的是低阶公共场的单帧局限，而不是遮罩违规。</p>
      <div class="grid-2">
        <div class="card red"><h3>它限制了什么</h3><p>公共运动不能被当成逐帧绝对正确。实际使用需要保留背景残差、锚点覆盖和显示变化层作为置信度信息。</p></div>
        <div class="card green"><h3>它为什么没有推翻 P0</h3><p>预注册门槛是至少 75% 有效帧对改善，实际为 578/579=99.83%；困难帧没有删除，也没有用 R04 重新调参。</p></div>
      </div>
    </section>

    <section id="boundary">
      <h2>11. 把整条逻辑重新连起来</h2>
      <ol>
        <li>从 PERSON 外的有效 SAR 背景中提取可追踪局部结构；</li>
        <li>把每个结构表示为位置和观测位移，不做背景语义分类；</li>
        <li>用 FIT 锚点拟合 M0–M3，用 HOLDOUT 锚点计算真正的背景预测残差；</li>
        <li>在 R01 只看背景留出残差选择低复杂度模型并冻结；</li>
        <li>把冻结模型原样应用到 R04，检验不同 lag 下是否普遍优于 M0；</li>
        <li>再把同一模型放到已知静止 PERSON 框中心，检查公共位移是否被去除到目标尺度内；</li>
        <li>保留反向帧和 PERSON 尾部病例，确认模型没有靠 PERSON 或边界作弊。</li>
      </ol>
      <div class="grid-2">
        <div class="card green"><h3>P0_PASS 能说明</h3><ul><li>当前显示域背景中存在可稳定估计的公共图像输运；</li><li>它在完全留出的 R04 中能预测背景；</li><li>它能显著减少静止 PERSON 框中的共同位移分量；</li><li>P1 从方法资格上可以另行设计。</li></ul></div>
        <div class="card red"><h3>P0_PASS 不能说明</h3><ul><li>真实载体轨迹或地理配准；</li><li>人体固有 RCS 或稳定人体模板；</li><li>SAR 框轨迹就是目标独立运动；</li><li>补偿残差就是人体速度；</li><li>已经完成 PERSON 候选生成或最终 SAR 定位。</li></ul></div>
      </div>
      <div class="callout">
        光学仍只提供时间、行为、连续性和方位搜索先验；SAR 保留最终定位权。本报告仍停在 P0，P1 状态为 <code>ELIGIBLE_BUT_NOT_STARTED</code>。
      </div>
    </section>

    <section>
      <h2>12. 术语快速复查</h2>
      <details open><summary>背景位移和背景残差有什么区别？</summary><p>背景位移是锚点实际移动的长度；背景残差是实际移动减去模型预测后剩下的长度。前者大而后者小，表示发生了较大的公共运动但模型解释得好。</p></details>
      <details><summary>为什么不用 PERSON 框来拟合公共运动？</summary><p>因为 PERSON 是随后要评估的对象。若把它用于拟合，模型可能主动贴合 PERSON 框轨迹，形成循环证明。</p></details>
      <details><summary>为什么 M0 重要？</summary><p>M0 表示完全不做补偿。只有冻结模型在同一批 HOLDOUT 锚点上优于 M0，才能说模型比“保持原像素坐标”更有解释力。</p></details>
      <details><summary>为什么用中位数，不直接平均？</summary><p>锚点追踪不可避免地有局部离群点。中位数描述帧对中的典型残差，对少量极端错误更稳健；P90和最差病例再负责暴露尾部。</p></details>
      <details><summary>99.83% 是准确率吗？</summary><p>不是。它只是“冻结模型帧对中位残差低于 M0”的帧对比例。</p></details>
    </section>

    <section>
      <h2>13. 冻结证据与报告来源</h2>
      <ul>
        <li><code>model_selection_R01.json</code>：R01 模型比较、参数和哈希冻结；</li>
        <li><code>frozen_validation_R04.json</code>：R04 定量门槛与最终 P0_PASS；</li>
        <li><code>background_anchor_holdout_metrics.csv</code>：本报告真实锚点算例来源；</li>
        <li><code>common_motion_pair_metrics.csv</code>：帧对和 lag 层指标；</li>
        <li><code>stationary_person_residuals.csv</code>：PERSON 补偿前后残差；</li>
        <li><code>MULTIMODAL_WORST_FRAME_REVIEW.md</code>：失败病例人工复核。</li>
      </ul>
      <p>本 HTML 由 <code>render_p0_explained_html.py</code> 从冻结产物生成。<strong>model_refit=false</strong>，没有重新追踪锚点、重新拟合、修改门槛或进入 P1。</p>
      <figure><img src="visualizations/P0_RESEARCH_OVERVIEW.png" alt="P0研究总览"><figcaption>前一版总览保留在此作为全局索引；本 HTML 的重点是把其中每个概念拆开解释。</figcaption></figure>
    </section>

    <p class="footer-note">生成时间：__CREATED__ · 状态：P0_COMPLETE_STOPPED_BEFORE_P1 · 静态本地报告，无外部网络依赖</p>
  </main>

  <script id="reportData" type="application/json">__DATA_JSON__</script>
  <script>
    const report = JSON.parse(document.getElementById('reportData').textContent);
    let activeCase = 0;
    let activeAnchor = 1;
    const fmt = value => Number(value).toFixed(3);
    const caseControls = document.getElementById('caseControls');
    const anchorControls = document.getElementById('anchorControls');

    function makeButtons() {
      caseControls.innerHTML = '';
      report.examples.forEach((item, index) => {
        const button = document.createElement('button');
        button.textContent = item.kind === 'FAILURE_RETAINED' ? '失败 168→171' : `典型 lag ${item.lag}`;
        button.className = index === activeCase ? 'active' : '';
        button.onclick = () => { activeCase = index; activeAnchor = 1; render(); };
        caseControls.appendChild(button);
      });
      anchorControls.innerHTML = '';
      const names = ['小残差锚点', '接近中位数锚点', '最大残差锚点'];
      report.examples[activeCase].anchors.forEach((item, index) => {
        const button = document.createElement('button');
        button.textContent = names[index];
        button.className = index === activeAnchor ? 'active' : '';
        button.onclick = () => { activeAnchor = index; render(); };
        anchorControls.appendChild(button);
      });
    }

    function setArrow(id, x1, y1, x2, y2) {
      const el = document.getElementById(id);
      el.setAttribute('x1', x1); el.setAttribute('y1', y1); el.setAttribute('x2', x2); el.setAttribute('y2', y2);
    }

    function renderVector(anchor) {
      const origin = {x: 180, y: 180};
      const maxValue = Math.max(anchor.observed_magnitude_px, anchor.predicted_magnitude_px, anchor.residual_px, 0.5);
      const scale = Math.min(62, 145 / maxValue);
      const point = vector => ({x: origin.x + vector[0] * scale, y: origin.y + vector[1] * scale});
      const observed = point(anchor.observed);
      const predicted = point(anchor.predicted);
      setArrow('observedArrow', origin.x, origin.y, observed.x, observed.y);
      setArrow('predictedArrow', origin.x, origin.y, predicted.x, predicted.y);
      setArrow('residualArrow', predicted.x, predicted.y, observed.x, observed.y);
      const observedPoint = document.getElementById('observedPoint');
      observedPoint.setAttribute('cx', observed.x); observedPoint.setAttribute('cy', observed.y);
      const predictedPoint = document.getElementById('predictedPoint');
      predictedPoint.setAttribute('cx', predicted.x); predictedPoint.setAttribute('cy', predicted.y);
      document.getElementById('scaleText').textContent = `绘图缩放：1 px 位移 ≈ ${scale.toFixed(1)} SVG 单位；数值以右侧为准`;
    }

    function renderTable(item) {
      const body = document.getElementById('anchorTableBody');
      body.innerHTML = '';
      item.anchors.forEach((anchor, index) => {
        const row = document.createElement('tr');
        row.className = index === activeAnchor ? 'active' : '';
        row.innerHTML = `<th>${anchor.label}</th><td>(${fmt(anchor.x_px)}, ${fmt(anchor.y_px)})</td><td>(${fmt(anchor.observed[0])}, ${fmt(anchor.observed[1])})</td><td>(${fmt(anchor.predicted[0])}, ${fmt(anchor.predicted[1])})</td><td>(${fmt(anchor.residual_vector[0])}, ${fmt(anchor.residual_vector[1])})</td><td><strong>${fmt(anchor.residual_px)} px</strong></td>`;
        row.onclick = () => { activeAnchor = index; render(); };
        body.appendChild(row);
      });
    }

    function render() {
      makeButtons();
      const item = report.examples[activeCase];
      const anchor = item.anchors[activeAnchor];
      renderVector(anchor);
      renderTable(item);
      const status = item.pair_improved ? `<span class="chip selected">该帧对优于 M0</span>` : `<span class="chip fail">该帧对略差于 M0</span>`;
      document.getElementById('caseSummary').innerHTML = `<h3>${item.title}</h3><p>R04 ${item.from_frame}→${item.to_frame} · lag ${item.lag} · 冻结 ${item.model}</p><p>${status}</p><div class="metric-line"><span>FIT / HOLDOUT 锚点</span><strong>${item.fit_anchor_count} / ${item.holdout_anchor_count}</strong></div><div class="metric-line"><span>帧对 HOLDOUT 中位残差</span><strong>${fmt(item.pair_holdout_median_px)} px</strong></div><div class="metric-line"><span>同帧对 M0 中位残差</span><strong>${fmt(item.pair_M0_median_px)} px</strong></div><div class="metric-line"><span>显示变化层</span><strong>${item.display_stratum}</strong></div>`;
      document.getElementById('numericFormula').textContent = `sqrt( (${fmt(anchor.observed[0])} - ${fmt(anchor.predicted[0])})² + ((${fmt(anchor.observed[1])}) - (${fmt(anchor.predicted[1])}))² ) = ${fmt(anchor.residual_px)} px`;
      document.getElementById('observedMagnitude').textContent = `${fmt(anchor.observed_magnitude_px)} px`;
      document.getElementById('predictedMagnitude').textContent = `${fmt(anchor.predicted_magnitude_px)} px`;
      document.getElementById('residualMagnitude').textContent = `${fmt(anchor.residual_px)} px`;
      document.getElementById('m0AnchorResidual').textContent = `${fmt(anchor.M0_anchor_residual_px)} px`;
      const ratio = anchor.residual_px / Math.max(anchor.observed_magnitude_px, 1e-9);
      let text;
      if (ratio < .25) text = `该锚点残差只有观测位移的 ${(ratio*100).toFixed(1)}%，说明公共模型解释了大部分位移。`;
      else if (ratio < .8) text = `该锚点仍有 ${(ratio*100).toFixed(1)}% 的观测位移未被解释，是中等局部偏差。`;
      else text = `该锚点残差达到观测位移的 ${(ratio*100).toFixed(1)}%，模型在这个局部结构上解释较差；必须依靠整批 HOLDOUT 中位数和尾部共同判断。`;
      document.getElementById('anchorInterpretation').innerHTML = `<strong>${anchor.label}：</strong>${text}<br><span class="small">前后向误差 ${fmt(anchor.forward_backward_error_px)} px，局部梯度 NCC ${fmt(anchor.local_gradient_ncc)}。</span>`;
    }
    render();
  </script>
</body>
</html>
'''

    replacements = {
        "__R01_ROWS__": build_r01_rows(freeze),
        "__R04_ROWS__": build_r04_rows(final),
        "__ALL_BEFORE__": f"{f3(float(all_person['uncompensated_p90_px']))} px",
        "__ALL_AFTER__": f"{f3(float(all_person['compensated_p90_px']))} px",
        "__ALL_AFTER_WIDTH__": f"{float(all_person['compensated_p90_px']) / float(all_person['uncompensated_p90_px']) * 100:.1f}",
        "__MANUAL_BEFORE__": f"{f3(float(manual_person['uncompensated_p90_px']))} px",
        "__MANUAL_AFTER__": f"{f3(float(manual_person['compensated_p90_px']))} px",
        "__MANUAL_AFTER_WIDTH__": f"{float(manual_person['compensated_p90_px']) / float(manual_person['uncompensated_p90_px']) * 100:.1f}",
        "__SHORT_AXIS__": f3(short_axis),
        "__CREATED__": html.escape(created),
        "__DATA_JSON__": data_json,
    }
    for key, value in replacements.items():
        template = template.replace(key, value)
    return template


def main() -> None:
    require_workspace_scope()
    html_text = build_html()
    OUTPUT_PATH.write_text(html_text, encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(OUTPUT_PATH),
                "bytes": OUTPUT_PATH.stat().st_size,
                "model_refit": False,
                "external_dependencies": False,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
