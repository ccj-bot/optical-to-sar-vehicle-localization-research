#!/usr/bin/env python3
"""Render the minimal B0R and P1E single-frame evidence report."""

from __future__ import annotations

import csv
import html
import json
import math
from collections import Counter, defaultdict
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve()
TASK_DIR = SCRIPT_PATH.parent
WORKSPACE = TASK_DIR.parents[1]
STUDY_OUTPUT = (
    WORKSPACE / "output" / "person_physics_guided_image_domain_study_20260824"
)
P1E_ROOT = STUDY_OUTPUT / "p1e_sar_only_response_interface"
B0R_DIR = P1E_ROOT / "b0r_minimal"
SINGLE_DIR = P1E_ROOT / "single_frame" / "manual_v4_physical_scale_p0_mask"
HTML_PATH = P1E_ROOT / "P1E_SAR_ONLY_RESPONSE_INTERFACE_REPORT.html"
MD_PATH = P1E_ROOT / "P1E_EXPLORATORY_CONCLUSION.md"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def number(value: object, digits: int = 3) -> str:
    try:
        converted = float(value)
    except (TypeError, ValueError):
        return "N/A"
    if not math.isfinite(converted):
        return "N/A"
    return f"{converted:.{digits}f}"


def percent(value: object, digits: int = 1) -> str:
    try:
        converted = float(value)
    except (TypeError, ValueError):
        return "N/A"
    if not math.isfinite(converted):
        return "N/A"
    return f"{100.0 * converted:.{digits}f}%"


def markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend("| " + " | ".join(str(cell) for cell in row) + " |" for row in rows)
    return "\n".join(lines)


def html_table(headers: list[str], rows: list[list[object]]) -> str:
    head = "".join(f"<th>{html.escape(str(item))}</th>" for item in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{html.escape(str(cell))}</td>" for cell in row) + "</tr>"
        for row in rows
    )
    return f"<div class='table-wrap'><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>"


def main() -> None:
    if WORKSPACE.resolve() != Path(r"D:\profile\research\workspace").resolve():
        raise RuntimeError(f"workspace mismatch: {WORKSPACE}")
    if "old_work" in str(SCRIPT_PATH).lower() or "old_work" in str(P1E_ROOT).lower():
        raise RuntimeError("forbidden old_work dependency")

    b0r = read_json(B0R_DIR / "b0r_summary.json")
    summary = read_json(SINGLE_DIR / "p1e_single_frame_summary_manual.json")
    target_rows = read_csv(SINGLE_DIR / "p1e_run_target_effects_manual.csv")
    b0r_local = read_csv(B0R_DIR / "b0r_local_error_budget_R02_R03.csv")

    candidates = {item["candidate"]: item for item in summary["summaries"]}
    c2 = candidates["C2_COMPACT_JET_GRADIENT_CONSENSUS"]
    c3 = candidates["C3_ISOTROPIC_BLOB_RIDGE_SUPPRESSED"]

    candidate_names = {
        "C0_JET_CENTER_RING": "C0 中心—外环 JET 对比",
        "C1_RANGE_RANK_TOPHAT": "C1 距离归一紧凑顶帽",
        "C2_COMPACT_JET_GRADIENT_CONSENSUS": "C2 紧凑 JET＋梯度共识",
        "C3_ISOTROPIC_BLOB_RIDGE_SUPPRESSED": "C3 各向同性亮核＋长脊惩罚",
    }
    overall_rows: list[list[object]] = []
    for key in candidate_names:
        item = candidates[key]
        overall_rows.append(
            [
                candidate_names[key],
                item["evaluable_count"],
                item["abstain_count"],
                percent(item["reference_beats_hard_background_fraction"]),
                number(item["median_advantage_vs_hard_background"]),
                number(item["median_advantage_vs_hard_background_p95"]),
                number(item["median_local_peak_distance_m"]),
                number(item["p90_local_peak_distance_m"]),
            ]
        )

    c2_run_rows: list[list[object]] = []
    for run_id in ("R01ZF", "R02ZF", "R03ZF", "R04ZF"):
        item = c2["per_run"][run_id]
        c2_run_rows.append(
            [
                run_id,
                item["evaluable_count"],
                item["abstain_count"],
                percent(item["reference_beats_hard_background_fraction"]),
                number(item["median_advantage_vs_hard_background_p95"]),
                number(item["median_local_peak_distance_m"]),
                number(item["p90_local_peak_distance_m"]),
            ]
        )

    target_effects: list[list[object]] = []
    for row in target_rows:
        if row["candidate"] != "C2_COMPACT_JET_GRADIENT_CONSENSUS":
            continue
        target_effects.append(
            [
                row["run_id"],
                row["target_id"].split("SARPERSON")[-1],
                row["box_count"],
                number(row["median_advantage_vs_hard"]),
                number(row["median_advantage_vs_hard_p95"]),
                percent(row["beats_hard_fraction"]),
                number(row["median_peak_distance_m"]),
            ]
        )

    local_counts: Counter[tuple[str, int, str]] = Counter()
    for row in b0r_local:
        local_counts[(row["run_id"], int(row["lag"]), row["local_compensation_status"])] += 1
    b0r_rows: list[list[object]] = []
    for run_id in ("R02ZF", "R03ZF"):
        for lag in (1, 3, 5):
            comparable = local_counts[(run_id, lag, "P0_COMPENSATION_COMPARABLE")]
            not_comparable = local_counts[(run_id, lag, "P0_COMPENSATION_NOT_COMPARABLE")]
            insufficient = local_counts[(run_id, lag, "INSUFFICIENT_BACKGROUND_SUPPORT")]
            b0r_rows.append([run_id, lag, comparable, not_comparable, insufficient])

    case_captions = {
        "R04_COMPACT_RESPONSE": "成功：R04 F100/P03。原图有孤立紧凑亮核，C2/C3 都把响应集中到参考位置附近。",
        "R02_GROUP_CLUTTER_P01": "失败：R02 F472/P01。参考位置嵌在多人/背景亮链中，局部峰漂到约 0.6 m 外，硬背景更强。",
        "R02_REFERENCE_WEAK_P03": "条件性成功：R02 F490/P03。C3 捕捉到紧凑核，C2 仅略高于最强硬背景，说明候选间存在形态依赖。",
        "R03_BOUNDARY_EARLY": "弃权：R03 F458。冻结 P0 的 1.0 m 外边界退让使参考支持区无效；病例保留展示但不计成功。",
        "R03_BOUNDARY_RECOVERY": "边界恢复：R03 F494。进入有效区后 C2 出现集中响应；但 R03 只有 2 个可评价人工框，不能承担稳定性结论。",
        "R04_VISIBLE_CORE_OPERATOR_MISS": "最小修复有效：R04 F90/P03。旧顶帽算子漏检；连续尺度的 C2/C3 恢复了参考亮核，证明部分失败确属表示问题。",
        "R02ZF_C3_WORST_FAIR": "不可分辨失败：R02 F494/P01。参考点落在长亮链上，C0–C3 均被更强局部结构压过。",
        "R04ZF_C3_WORST_FAIR": "剩余失败：R04 F32/P02。响应沿边界附近斜向结构延展，C2/C3 对最强硬背景没有优势。",
    }
    registry_by_reason = {item["reason"]: item for item in summary["visual_case_registry"]}
    case_order = [
        "R04_COMPACT_RESPONSE",
        "R02_REFERENCE_WEAK_P03",
        "R04_VISIBLE_CORE_OPERATOR_MISS",
        "R02_GROUP_CLUTTER_P01",
        "R02ZF_C3_WORST_FAIR",
        "R04ZF_C3_WORST_FAIR",
        "R03_BOUNDARY_EARLY",
        "R03_BOUNDARY_RECOVERY",
    ]
    cases: list[tuple[str, str]] = []
    for reason in case_order:
        item = registry_by_reason.get(reason)
        if item is None:
            continue
        relative = Path(item["visual_path"]).resolve().relative_to(P1E_ROOT.resolve()).as_posix()
        cases.append((relative, case_captions[reason]))

    conclusion = (
        "目前已经能生成运行时可计算的 SAR-only S(x)，其中 C2 对孤立、紧凑 PERSON 响应具有明确位置优势；"
        "但尚不能构成跨条件稳定、可直接用于后续定位的通用接口。决定性失败来自 R02 的多人/长亮链场景："
        "C2 对局部最强硬背景仅 47.2%，峰到参考位置的中位距离约 0.57 m，且 P01/P02 的目标级硬背景中位优势为负。"
    )

    md = f"""# P1E SAR-only PERSON 响应接口探索结论

> 状态：`P1E_SINGLE_FRAME_CONDITIONAL_SIGNAL_FOUND_BUT_NOT_STABLE_ENOUGH_FOR_INTERFACE_FREEZE`  
> 数据角色：R01/R02/R03/R04 全部为已暴露开发语料；不授予 P1_PASS。  
> 时序状态：未启动。单帧通用位置特异性尚未建立。

## 结论先行

{conclusion}

- 可保留的首选候选：`C2_COMPACT_JET_GRADIENT_CONSENSUS`。
- C3 能修复部分“有亮核但顶帽漏检”病例，尤其 R04；但没有修复 R02，不能作为通用替代。
- 主要阻断不是单一统计门槛，而是拥挤/长脊条件下 PERSON 响应与场景强散射缺乏可分离的位置结构；有效空间分辨与场景融合是主因，表示问题是次因且已被部分修复。
- 不进入补偿后时序；否则会用时序复杂度掩盖单帧定位歧义。

## B0R 最低必要门控

{markdown_table(["run", "lag", "可做时序位置", "不可比较", "背景支持不足"], b0r_rows)}

B0R 已足够决定“哪里可做时序、哪里只做单帧”，不继续扩展审计。它仍是经验误差预算，不是校准置信上界。

## 公平评价修正

1. 主分数由“9 px 内最大值”改为固定 0.30 m 支持盘均值，参考、匹配背景、四方向偏移和硬背景使用同一算子。
2. 有效区直接复用冻结 P0 掩膜：内圈 0.75 m、外边界退让 1.0 m、侧边退让 1.5°。
3. 尺度改为扇面几何换算的固定物理尺度 0.30/0.55/0.90 m；不再读取 PERSON 框宽高生成响应。
4. 匹配背景改为固定米制切向间隔；硬背景报告池大小、P90/P95 和最大值；四个固定偏移方向分别保留。
5. 增加局部峰到参考位置的距离，避免把“附近某处有峰”误写成“参考位置有峰”。

## 四个候选的整体结果

{markdown_table(["候选", "可评价", "弃权", "胜最强硬背景", "中位 Δhard", "中位 Δhard-P95", "峰距中位 m", "峰距 P90 m"], overall_rows)}

## 首选 C2 的跨 run 结果

{markdown_table(["run", "可评价", "弃权", "胜最强硬背景", "中位 Δhard-P95", "峰距中位 m", "峰距 P90 m"], c2_run_rows)}

关键解释：R02 中 C2 相对硬背景池 P95 的中位优势仍为正，但对单个最强硬背景的胜率只有 47.2%，峰距接近 0.65 m 搜索半径边缘。这说明它在拥挤场景里常能找到“高响应区域”，却不能唯一落到 PERSON 参考位置。

## C2 的逐目标效应

{markdown_table(["run", "目标", "框数", "中位 Δhard", "中位 Δhard-P95", "胜最强硬背景", "峰距中位 m"], target_effects)}

## 失败归因

- **表示问题：部分存在。** R04 F90 被旧 C1 漏检，但 C2/C3 修复，说明不能把所有失败归因于 PERSON 无响应。
- **显示链问题：可能限制信息，但不是当前唯一主因。** 同一伪彩链下 R01/R04 可形成集中响应，R02 却在亮链内失去唯一性。
- **空间分辨/场景融合：重要主因。** R02 的局部峰常漂移约 0.6 m，PERSON 参考位置与弧线、链状强散射难分。
- **PERSON 响应缺乏通用位置特异性：当前主要结论。** 在孤立紧凑条件下成立，在多人/长脊/边界邻近条件下不稳定。

## 是否进入时序

否。先保留 C2 为探索候选，C3 作为“紧凑核/长脊”诊断候选；不融合、不继续加特征、不运行全部插值框，也不进入时序。若后续继续，应优先新采集覆盖孤立与拥挤条件，并在冻结公式后做盲验证。

## 核心产物

- B0R：`b0r_minimal/b0r_summary.json`
- 单帧机器可读汇总：`single_frame/manual_v4_physical_scale_p0_mask/p1e_single_frame_summary_manual.json`
- 逐框指标：`single_frame/manual_v4_physical_scale_p0_mask/p1e_single_frame_metrics_manual.csv`
- 逐 run×target×time-block：`single_frame/manual_v4_physical_scale_p0_mask/p1e_run_target_time_block_effects_manual.csv`
- 直接证据 HTML：`P1E_SAR_ONLY_RESPONSE_INTERFACE_REPORT.html`
"""
    MD_PATH.write_text(md, encoding="utf-8")

    figures = "".join(
        f"<figure><a href='{html.escape(path)}'><img loading='lazy' src='{html.escape(path)}' alt='{html.escape(caption)}'></a><figcaption>{html.escape(caption)}</figcaption></figure>"
        for path, caption in cases
    )
    candidate_explanations = [
        ["C0", "JET 代理中心支持减外环", "紧凑亮团高于邻域", "任何紧凑强散射体都会触发；R02 硬背景失败"],
        ["C1", "距离带归一后的多尺度顶帽", "压制距离依赖和宽弧", "连接到长链时会被开运算保留或漏检"],
        ["C2", "紧凑 JET 与局部梯度共识", "同时要求亮核与内部边/脊支持", "当前最强；多人亮链中峰会漂移"],
        ["C3", "Hessian 双向负曲率＋结构张量长脊惩罚", "偏好二维紧凑核、抑制长弧", "改善 R04，但 R02 仍不稳定，且会压低部分真实延展响应"],
    ]
    html_text = f"""<!doctype html>
<html lang='zh-CN'>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<title>P1E SAR-only PERSON 响应接口探索</title>
<style>
:root {{ color-scheme: light; --ink:#172033; --muted:#5a6578; --line:#d9dfeb; --panel:#f6f8fc; --warn:#8a3d14; --good:#135f46; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; font-family:"Segoe UI","Microsoft YaHei",sans-serif; color:var(--ink); background:#fff; line-height:1.65; }}
main {{ max-width:1220px; margin:0 auto; padding:34px 28px 70px; }}
h1 {{ font-size:2rem; margin:0 0 8px; }} h2 {{ margin-top:42px; border-bottom:1px solid var(--line); padding-bottom:8px; }}
.status {{ display:inline-block; padding:5px 10px; border-radius:999px; background:#fff1e8; color:var(--warn); font-weight:700; }}
.lead {{ font-size:1.12rem; background:var(--panel); border-left:5px solid #315ea8; padding:18px 20px; margin:22px 0; }}
.grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:18px; }}
.card {{ border:1px solid var(--line); border-radius:12px; padding:16px 18px; background:#fff; }}
.card strong {{ color:var(--good); }}
.table-wrap {{ overflow-x:auto; border:1px solid var(--line); border-radius:10px; }}
table {{ width:100%; border-collapse:collapse; font-size:.93rem; }} th,td {{ padding:9px 10px; border-bottom:1px solid var(--line); text-align:left; white-space:nowrap; }} th {{ background:#edf2fa; }} tr:last-child td {{ border-bottom:0; }}
figure {{ margin:26px 0 34px; border:1px solid var(--line); border-radius:12px; overflow:hidden; background:#fff; }} figure img {{ width:100%; display:block; }} figcaption {{ padding:12px 16px; color:var(--muted); }}
code {{ background:#eef2f8; padding:2px 5px; border-radius:4px; }}
.note {{ color:var(--muted); font-size:.93rem; }}
@media (max-width:800px) {{ main {{ padding:22px 14px 50px; }} .grid {{ grid-template-columns:1fr; }} }}
</style>
</head>
<body><main>
<h1>P1E SAR-only PERSON 响应接口探索</h1>
<div class='status'>条件性信号存在，但不足以冻结为通用定位接口</div>
<p class='note'>现有四个 run 全部是开发语料；本报告不授予 P1_PASS，也未进入时序。</p>
<div class='lead'>{html.escape(conclusion)}</div>

<div class='grid'>
<div class='card'><strong>目前最有希望：</strong><br>C2 紧凑 JET＋梯度共识。孤立、紧凑响应中位置集中明显。</div>
<div class='card'><strong>决定性阻断：</strong><br>R02 多人/长亮链中最强硬背景经常胜出，峰位漂离参考位置。</div>
<div class='card'><strong>最小修复结论：</strong><br>固定支持均值、冻结 P0 掩膜和物理尺度消除了饱和与边界伪成功。</div>
<div class='card'><strong>时序决定：</strong><br>不进入。单帧一般位置特异性没有建立。</div>
</div>

<h2>这次到底测试什么</h2>
<p>对有效扇面内任意候选位置 <code>x</code>，只用 SAR 伪彩图像、扇面几何、固定物理尺度和有效区计算 <code>S(x)</code>。PERSON 框中心、宽高和 physical_target_id 只在响应图生成后用于离线采样和评价。</p>
{html_table(["候选", "测什么", "为什么可能位置特异", "主要失败方式"], candidate_explanations)}

<h2>B0R：哪里以后可以做时序</h2>
{html_table(["run", "lag", "可做时序位置", "不可比较", "背景支持不足"], b0r_rows)}
<p>R02 主要只有 lag1 和少量 lag3；R03 基本只适合作为单帧边界语料。B0R 已完成最低门控，不继续扩大审计。</p>

<h2>审核发现与修正</h2>
<ul>
<li>移除“9 px 内最大值”主评价，改为固定 0.30 m 支持盘均值，并单列峰距。</li>
<li>直接复用冻结 P0 有效掩膜；R03 F458 现在明确弃权。</li>
<li>移除来自 PERSON 框短轴的尺度，改用 0.30/0.55/0.90 m 固定物理尺度。</li>
<li>匹配背景使用固定米制切向偏移；四方向偏移分开；硬背景报告整个候选池。</li>
<li>病例选择改为含硬背景的公平效用，并直接展示 C2/C3 成功与失败。</li>
</ul>

<h2>四个候选的整体结果</h2>
{html_table(["候选", "可评价", "弃权", "胜最强硬背景", "中位 Δhard", "中位 Δhard-P95", "峰距中位 m", "峰距 P90 m"], overall_rows)}

<h2>首选 C2 的跨 run 结果</h2>
{html_table(["run", "可评价", "弃权", "胜最强硬背景", "中位 Δhard-P95", "峰距中位 m", "峰距 P90 m"], c2_run_rows)}
<p><strong>关键不是 85.4% 的总体数，而是 R02 的 47.2%。</strong> R02 中位数仍高于硬背景池 P95，说明响应有显著性；但它经常不是附近唯一最强位置，因此不能直接承担最终定位。</p>

<h2>C2 的逐目标效应</h2>
{html_table(["run", "目标", "框数", "中位 Δhard", "中位 Δhard-P95", "胜最强硬背景", "峰距中位 m"], target_effects)}

<h2>直接图像证据与失败病例</h2>
{figures}

<h2>最终研究判断</h2>
<ul>
<li><strong>能否构造运行时 S(x)：</strong>能。</li>
<li><strong>能否构造稳定通用、足以进入后续定位的 S(x)：</strong>目前不能。</li>
<li><strong>优势来自：</strong>孤立紧凑亮核、局部梯度/曲率共同支持、参考峰距较小。</li>
<li><strong>成立条件：</strong>完整有效支持区，PERSON 响应未与长弧/亮链融合，局部不存在更强同尺度散射体。</li>
<li><strong>失败位置：</strong>R02 P01/P02 的多人/亮链、R04 边界邻近延展响应，以及冻结 P0 支持区外的 R03 早期帧。</li>
<li><strong>主要阻断：</strong>场景强散射与 PERSON 条件响应在当前伪彩空间分辨下缺乏可分离的位置结构；表示问题只解释其中一部分。</li>
</ul>
<p>因此保留 C2 为 P1E 首选探索候选、C3 为结构诊断候选；不融合、不继续堆特征、不运行时序。下一步若继续，应先做覆盖孤立/拥挤条件的新采集，并在新数据前冻结公式和弃权规则。</p>

<h2>可复核文件</h2>
<ul>
<li><a href='b0r_minimal/b0r_summary.json'>B0R 机器可读摘要</a></li>
<li><a href='single_frame/manual_v4_physical_scale_p0_mask/p1e_single_frame_summary_manual.json'>P1E 单帧摘要</a></li>
<li><a href='single_frame/manual_v4_physical_scale_p0_mask/p1e_single_frame_metrics_manual.csv'>逐框指标</a></li>
<li><a href='single_frame/manual_v4_physical_scale_p0_mask/p1e_run_target_time_block_effects_manual.csv'>逐 run×target×time-block 指标</a></li>
<li><a href='P1E_EXPLORATORY_CONCLUSION.md'>Markdown 结论</a></li>
</ul>
</main></body></html>"""
    HTML_PATH.write_text(html_text, encoding="utf-8")
    print(json.dumps({"html": str(HTML_PATH), "markdown": str(MD_PATH)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
