# PERSON P1E — 等搜索成本光学方位壳信息增益实验协议

- 协议状态：`FROZEN_BEFORE_CANDIDATE_OR_REFERENCE_EVALUATION`
- 日期：2026-08-26
- 解释器：`D:\MINICONDA\envs\py311\python.exe`
- 输出目录：`p1e_sar_only_response_interface/optical_shell_information_gain_v1`

## 1. 研究问题

在相同或可量化接近的 SAR 单帧搜索成本下，正确的粗光学方位先验是否比明确偏移的错误方位先验：

1. 更能保留人工 reference 附近既有 GT-blind C2 候选；
2. 更能降低无关候选负担；
3. 更能把全扇面低 rank 候选提升为可处理的 shell-local rank；
4. 改善一对一 candidate/reference coverage；
5. 在 R02 P03/P04 等多人场景中仍保留 shared/未分离状态。

本实验是已暴露开发语料上的受控诊断，不是最终 P2，不生成 SAR 框，不授予新的 PASS/FAIL。

## 2. 冻结运行时输入

- SAR-only C2 candidates：沿用既有 `gt_blind_candidates_all_processed_frames.csv`，不重新生成或调参。
- C2 response：沿用冻结 C2 公式，仅用于直接病例响应图；不修改 C0–C3。
- TRUE shell：使用既有固定 optical→SAR 方位映射；对每个 SAR 帧取其时间戳 ±250 ms 内所有 optical PERSON 粗方位壳的并集。
- 不使用 `physical_target_id` 选择所谓正确光学轨迹；当前是保守 O2 先验，不等同于未来 runtime optical track identity。
- 光学不提供 SAR range；SAR 搜索范围固定为 `SAR_SINGLE_FRAME_OBSERVABLE` 中的 0.75–20 m。
- SAR 保留最终响应定位权；禁止“壳中心附近最亮点”。

## 3. TRUE shell 的实际搜索成本

先将 ±250 ms 光学壳并集与当前 SAR 几何扇面相交，得到实际运行时 TRUE search shell。逐帧记录：

- 扇内有效角宽；
- `SAR_SINGLE_FRAME_OBSERVABLE` 有效像素面积和物理面积；
- 左/右扇面裁剪量、最近边界距离；
- provisional common-FoV 重叠比例；
- 时间窗源帧数和原始壳数；
- 固定 SAR range 0.75–20 m；
- 壳内候选的 P0 CORE/EXTENDED/UNAVAILABLE、sigma、fallback/bracket 分布；
- 当前帧 display JS / DISPLAY_SHIFT。

## 4. 等成本 matched null shells

null 生成和选择只允许使用：光学壳、固定映射、时间窗、SAR 几何、`SAR_SINGLE_FRAME_OBSERVABLE` 掩膜和 provisional common-FoV。不得读取 C2 candidate、C2 score 或人工 reference 来选择 null。

1. 以 TRUE shell 与 SAR 扇面相交后的实际区间组为模板，保持区间数、各区间宽度和间隔结构，沿方位做刚性平移。
2. 固定候选位移网格：`-100° ... +100°`，步长 `0.5°`；排除 `|shift| < 12°`。
3. 平移后重新与实际 SAR 扇面相交；要求搜索面积大于 0，且与 TRUE shell 的扇内角区间 Jaccard 不高于 0.80。
4. 几何匹配代价预先固定为：

   `cost = width_rel_error + area_rel_error + 0.5*common_fov_overlap_diff + 0.25*boundary_gap_diff + 0.05*angular_jaccard`

   其中 `boundary_gap_diff` 由 TRUE/NULL 到最近扇面边界的距离差除以整扇面角宽得到。
5. 每帧选择代价最低的 3 个 null；所选 shift 彼此至少相隔 8°。不根据 reference coverage、候选数量或结果方向替换 null。
6. 不删除几何匹配较差的边界帧；连续报告每个 null 的宽度误差、面积误差、common-FoV 差和边界差，并将其解释为控制质量而非新 gate。

几何-only 预审计显示：376 个存在 TRUE shell 的帧均可生成 3 个上述 null；该审计没有读取人工 reference 或候选结果。

## 5. SAR-only 壳内候选指标

所有 shell 先生成完成，再截取既有 GT-blind C2 candidates。逐 shell 记录：

- candidate count；
- candidate density（每平方米及每度）；
- candidate burden `N_shell/N_full_fan`；
- 每个候选的 global rank、shell-local rank、shell-local percentile；
- P0 domain、sigma、fallback、radial/azimuth bracket；
- SAR edge 与 display 条件。

不构造加权总分、分类器或 tracker。

## 6. 仅离线 reference 评价

人工 reference、目标 ID 和人工框只在所有 TRUE/NULL shell 与壳内候选生成完成后使用。固定评价：

- 半径：0.3 m / 0.5 m / 0.8 m；
- K：1 / 2 / 3 / 5；
- reference 是否落入 shell；
- 最近壳内候选距离；
- full-fan rank → shell-local rank；
- full-fan 0.8 m 最佳候选是否被保留；
- Top-K coverage；
- 0.8 m 内基于距离的 Hungarian 一对一 matching；
- shared、low-rank、missing 的多标签与排他状态变化。

`shared/missing/low-rank` 仍是 reference 条件下的离线标签，不是 GT-blind runtime 状态检测器。`missing` 只表示当前 local-max/NMS candidate representation 在固定半径内缺峰，不等于 SAR 连续响应物理消失。

## 7. 固定比较与病例

- TRUE 与同帧 3 个 matched null 做配对比较；null 构成经验分布，不做结果后壳宽调参。
- 分 run，并重点报告 R02 P01/P02、P03/P04、R03/R04 边界病例。
- display 是同帧配对条件；仅比较 DISPLAY_SHIFT 与 baseline 下信息增益是否不同。
- P0 只作为壳内候选条件，不进入总分。
- 固定病例：R02 P02 F482 的“连续响应存在但 0.8 m 内无 local-max candidate”。
- 其他成功/失败病例按预先声明的规则选择：各指定 run/target 中 TRUE-vs-null rank/retention 改善最大与最小者，仅用于可视化，不参与主统计定义。

## 8. 冻结边界

- 不重调 P0；不修改 B0R、C0–C3、candidate semantic split、dynamic evidence 或 observation diagnostic。
- 不使用 SAR manual reference、SAR range GT、人工框中心或 `physical_target_id` 生成/调整 TRUE 或 NULL shell。
- 不使用未验证同步做精确逐帧 optical→SAR 点映射。
- 不把 RGB/JET 当独立物理雷达通道，不解释为人体固有 RCS。
- 不创建或移动 SAR 框；不 commit、不 push；不读取或依赖 `old_work`。

## 9. 运行前冻结依赖 SHA256

- `run_p0_common_apparent_motion.py`: `0AB671B6A33A48CA2E3160A201629FA2DD341EF052A29B8D2CCBC2DFB26DCFD8`
- `run_p1e_single_frame_position_specificity.py`: `98468B9DEA391E9FE9A209268CEFE7BE32BE40A7D7742B9DBE7D54C3539B9BB1`
- `run_p1e_candidate_recall_audit.py`: `84CCAEBB9A195D184B6C34393CC71A7699E5F190D4D5FC253C16E337855CF0F8`
- `gt_blind_candidates_all_processed_frames.csv`: `D2F1673A247FDB3AB1DD884F989ADC0ABE4E33A86AEFE45B5DFB4BE286FD6EC0`
- `manual_reference_candidate_interpretation_v2.csv`: `796F20EB3080C5B45CDEBBCC71584CC95C65691F056D46C4A31704A3D86E8EC7`
- `observation_condition_table.csv`: `DE65B9705A353F0DF783E0D4A59D0274FD05547362ABE463C50C9C5469D80C21`
- `frame_display_condition_table.csv`: `8997701F7FC34D1B52502F11B44FCEF64EC700A0FD2D734EA1AB6090A9DBAD8A`
- `explorer_data.js`: `C39E60EB478FF7D815EFE6984D3BCF36600737E2EC3D1FF76D04020DED54EF7D`

