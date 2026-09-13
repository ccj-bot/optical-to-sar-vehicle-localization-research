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

## Optical Review UX v0.2

本轮入口改为按场景 `GM_RM011 / GM_RM017 / GM_RM019`，每个场景直接打开 368 帧完整光学流。页面默认打开 YOLO11、YOLO26 和机器同目标建议，车辆/人员类别及置信度可独立切换；点击检测框只创建 `HUMAN_CAR_xxx` 或 `HUMAN_PERSON_xxx` 的人工 session，不代表 physical identity。

机器建议采用轻量 IoU、中心距离、尺度连续性和类别一致性组合，允许 A 接受、R 重选、V/P/X 标记当前帧状态；用户可编辑 visible/core interval 并冻结光学目标。PERSON provisional ID 已移入来源语义，不再作为主 UI 对象。SAR 页面本轮未扩展。

## Optical Review UX v0.3：多目标与无框观察

当前保存模型为 `TPGT_OPTICAL_HUMAN_TARGET_SET_v0.1`：一个场景可以同时包含任意多个人工目标，每个目标独立维护 `anchors`、`frame_observations`、`visible_segments`、`primary_core_interval`、`research_status` 和 append-only `frozen_revisions`。切换目标不会覆盖其他目标，当前帧会同时显示所有已确认目标，当前目标高亮。

无检测框时可使用 `MANUAL_OPTICAL_BBOX`；截断对象只保存真实可见支持框，不推断完整 physical box。也可以把本帧记为 `VISIBLE_UNBOXED`，此时 `bbox=null`。每帧状态保留 visibility、bbox、bbox_role、bbox_source、identity_relation 和 human_confirmed。

场景入口由 `scene_manifest.json` 驱动，当前包含 GM_RM011/017/019、R35ZF、R01ZF。实际帧数为 GM 三场景 368、R35ZF 298、R01ZF 297；R35ZF/R01ZF 图像尺寸从真实文件读取为 3840×2160，未假定 GM 参数。new65 场景无统一 detector cache 时显示空 proposal，但人工复核仍可继续。

后续接入核对确认了可复用 detector cache：R35ZF 使用 4212 个车辆 proposal 与 25 个人员 proposal，R01ZF 使用 77 个车辆 proposal 与 205 个人员 proposal。Workbench 只导入 frame/class/confidence/bbox/model；历史 track/person/car ID 不进入 Human Target identity。
