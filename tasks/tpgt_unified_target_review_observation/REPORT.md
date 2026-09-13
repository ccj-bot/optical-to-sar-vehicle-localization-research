# TPGT A-line：统一目标复核与 SAR 观察交付报告

## 目的

本任务把 Phase 1A Observation Workbench 组织为一条可审计入口：

`完整 Optical Sequence Review → Human Target / Interval Freeze → PRE_OPEN_BOOK SAR Observation → OPEN_BOOK Interpretation`

它是人工复核与证据记录工具，不是 detector、tracker、mapping 或 SAR 自动定位器。

## 到底要标什么

### 1. Optical Sequence Review（必须先做）

在完整光学序列中，人工确认“研究对象是谁、何时可见”，填写：

- `human_local_target_id`：本次 review 内的人工局部 ID，不等同于真实身份；
- `visible interval`：目标在光学中可见的起止帧；
- `core interval`：主体完整、适合后续观察的核心帧段；
- `identity status`、`body completeness`、`boundary state`、`occlusion`、`target type`；
- `research admission` 与自由备注。

B1.2 detector / provisional track / interval 只显示为灰色 `READ_ONLY PROPOSAL`。它们可以提示“从哪里开始看”，但不能自动填入 human interval，也不能把 provisional ID 升格为 human identity。

### 2. SAR Observation（冻结后）

冻结后，在 SAR 显示序列中只记录可见结构：point、rectangle ROI、形态、转变、连续性、确定性和文字观察。记录的 `view_mode` 固定为 `PRE_OPEN_BOOK_MULTIMODAL_OBSERVATION`，不加载 GT、历史答案或 mapping。

### 3. Open-book Interpretation（观察之后）

解释单独保存为 interpretation candidate：可能假设、观察到的一致/不一致、歧义和仍需的证据。它不修改 Observation，不注册机制（包括 M001），也不产生自动分数或最终框。

## 光学有没有对应？

有，但对应关系是“目标与时间范围的人工锚点”，不是把光学框直接当成 SAR 真值：

- 光学提供候选目标、完整序列、可见/core interval、粗粒度目标类型和遮挡/边界状态；
- SAR 在冻结目标约束下独立记录其显示结构与空间 ROI；
- 光学与 SAR 帧索引分开，当前只保留名义时间上下文，精确同步仍标记为 `unverified`；
- 光学 source bbox 与 B1.2 proposal 是可追溯的参考层，不能替代人工冻结，也不能决定最终 SAR 位置。

## 已核对数据

- B1.2 branch：`feature/tpgt-gm-complete-interval-b12`，commit `946e4750b998c3667d09bcf43fa05cb7b08d1e71`；
- GM_RM017 optical full stream：368 帧（0–367）；SAR：766 帧；
- CAR proposal：PV001 129–159、PV002 154–173、PV003 162–188、PV004 169–201；PV001 标为 truck/large vehicle，当前无 SAR reference；
- PERSON：91 detections、15 provisional tracks，仅作为 proposal metadata。

## 验证与复现

默认解释器：`D:\MINICONDA\envs\py311\python.exe`

```powershell
cd D:\profile\research\workspace
D:\MINICONDA\envs\py311\python.exe tasks\tpgt_unified_target_review_observation\build_unified_workbench.py
D:\MINICONDA\envs\py311\python.exe tasks\tpgt_unified_target_review_observation\serve_unified_workbench.py --port 8780
D:\MINICONDA\envs\py311\python.exe tasks\tpgt_unified_target_review_observation\check_unified_workbench.py
```

入口：`http://127.0.0.1:8780/workspace/output/tpgt/unified_target_review_observation/index.html`

QA 结果写入 `output/tpgt/unified_target_review_observation/audit/unified_workbench_qa.json`；构建审计写入 `audit/build_validation.json`。输出根目录为 `output/tpgt/unified_target_review_observation`。

## 明确未做

未重跑 YOLO，未修改 CAR/PERSON tracker，未生成 B1.2 candidates，未做 mapping fit/residual、truncation correction、mechanism/M001、selector/ranking/score/IoU、自动 SAR box 或最终 localization。
