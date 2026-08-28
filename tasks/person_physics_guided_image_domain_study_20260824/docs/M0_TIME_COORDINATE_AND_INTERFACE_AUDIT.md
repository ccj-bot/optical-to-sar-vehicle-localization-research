# M0 时间、坐标与接口前置审计

- 审计日期：2026-08-28
- 性质：代码、配置、schema 与既有物化产物的只读 prerequisite audit
- 当前权威状态：`P0_FROZEN_PASS / P1E_EXPLORATORY_OBSERVATION_INTERFACES_ESTABLISHED / RUNTIME_IDENTITY_NOT_ESTABLISHED / P2_NOT_ESTABLISHED`
- M0 执行状态：`NOT_EXECUTED`
- 活动目录：`D:\profile\research\workspace`
- 默认解释器：`D:\MINICONDA\envs\py311\python.exe`
- 边界：未读取或依赖 `old_work`；未运行新 motion-consistency 实验；未修改 P0、C2/S(x)、manual SAR reference、mapping、guard 或既有报告

## 0. 结论先行

当前仓库已经具备设计 M0 的必要观测接口，但还不具备把 M0 解释为严格物理同步下跨模态运动估计的条件。

可以直接使用的量包括：

1. 名义 index/FPS 时间轴，以及明确的 optical time ↔ SAR time 最近帧查询；
2. 固定 optical-x → SAR azimuth 线性映射和预声明的时间窗、guard、fan/common-FoV clipping；
3. SAR 像素到 range/azimuth 的扇面几何；
4. 冻结 P0 的逐帧对前向公共表观位移模型与 pair/model comparability；
5. 398/398 帧 q90/q95/q97.5 response-region masks/descriptors；
6. 最新真实像素 shell–region topology。

尚未建立的量包括：

- 独立硬件时间戳、原始逐帧 PTS、相机—SAR 固定 offset/drift 标定；
- 可部署的 runtime optical identity；
- 独立校准的 shared optical→SAR mapping uncertainty 与 guard 覆盖率；
- 权威的 region-mask P0 warp 约定与物化产物；
- PERSON-specific SAR region identity 或最终定位。

因此 M0 的第一共同量应是：

`Δtheta_optical ↔ Δtheta_SAR`

而不是：

`SAR pixel speed = k × optical pixel speed`

也不能先用 manual reference 拟合 timing、mapping、guard 或局部尺度。

## 1. 权威顺序与对象边界

发生冲突时，按以下顺序解释：

1. 当前实际代码、物化 schema、execution ledger 和独立验证器；
2. 同实验 pre-run amendment；
3. 最新 `shell_uncertainty_region_topology_v1`；
4. 较早 observation/runtime-track/dynamic 报告；
5. `P1E_EXPLORATORY_CONCLUSION.md` 和旧 temporal gate 只作历史记录。

规范对象：

- `raw_track_fragment_id`：自动 optical fragment hypothesis，不是真实 PERSON identity；
- `optical_person_id`：`GT_BLIND_OFFLINE_CONTINUITY_PROXY`，包含全 run stitching/assignment/短缺口处理，不是 causal runtime identity；
- optical shell：time/azimuth search support，不提供 SAR range、response center、PERSON box 或跨模态 identity；
- response-region：冻结 `S(x)` 的 q90/q95/q97.5 超水平连通区域，不是 PERSON box；centroid 只是 shape descriptor；
- P0：SAR 图像域公共表观输运，不是平台真实轨迹或目标真实运动；
- manual SAR reference / `physical_target_id`：只允许在全部 runtime/pre-reference 产物冻结后离线评价。

上述 supersession 与字段边界由 `docs/current_state_review.md` 和 `00A_PRE_RUN_OPTICAL_IDENTITY_PROVENANCE_AMENDMENT.md` 规定。

## 2. Optical 时间基准

### 2.1 实际来源

导帧代码通过 OpenCV 视频 metadata 读取 FPS、帧数和尺寸：

- `tasks/pseudocolor_labelstudio_prep_20260722/export_paired_frames.py:43-56`
- `fps = cv2.CAP_PROP_FPS`
- `frame_count = cv2.CAP_PROP_FRAME_COUNT`

时间戳不是硬件时间戳或容器 PTS，而是：

`timestamp_ms = round(frame_index * 1000 / fps)`

证据：

- 文件名生成：`export_paired_frames.py:59-61`
- catalog 字段：`export_paired_frames.py:90-103`

R01–R04 optical 视频 metadata 证据位于：

- `output/pseudocolor_labelstudio_prep_20260722/video_inventory.csv:1-9`

实际 optical FPS：

| run | FPS | frame count | size |
| --- | ---: | ---: | --- |
| R01ZF | 17.99996969533712 | 297 | 3840×2160 |
| R02ZF | 17.9999664411512 | 298 | 3840×2160 |
| R03ZF | 17.9999664411512 | 298 | 3840×2160 |
| R04ZF | 17.9999664411512 | 298 | 3840×2160 |

因此 nominal optical step 约为 55/56 ms，不能口头简化成一个精确 18 FPS 硬件时钟。

### 2.2 frame index、timestamp 与 dropped-frame 边界

- frame index 从 0 连续递增；导帧 catalog 检查索引必须为 `0..N-1`：`build_annotation_batch.py:45-63`。
- 完整解码时，decoded count 必须等于 metadata frame count：`export_paired_frames.py:101-105`。
- 这只能确认保存的视频可连续解码、导出目录索引连续。
- 仓库没有读取 raw per-frame PTS、采集端 sequence number 或丢帧标志，因此物理 acquisition dropped frames 状态为：`NOT_AUDITED`。

### 2.3 raw fragment 使用的时间字段

当前 shell 代码读取 optical hypothesis 表中的整数 `timestamp_ms`，并以 `raw_track_fragment_id` 分组：

- `run_p1e_runtime_track_response_region_minimal.py:223-245`
- `run_p1e_shell_uncertainty_region_topology.py:236-267`

这个 `timestamp_ms` 沿用上述 nominal index/FPS 时间轴。`GT-blind` 只说明没有 PERSON reference 参与生成，不等于该字段已经具备硬件同步或因果在线保证。

### 2.4 时间策略的实际查询逻辑

冻结策略在 `run_p1e_shell_uncertainty_region_topology.py:62-70`：

| policy | 查询区间，相对 query time | 未来帧 | 准确语义 |
| --- | --- | --- | --- |
| `SAME_FRAME` | `[0, 0] ms` | 否 | timestamp 必须等于 nominal optical query time |
| `PAST_ONLY_250MS` | `[-250, 0] ms` | 否 | 因果过去窗 |
| `BUFFERED_100MS` | `[-250, +100] ms` | 是，最多 100 ms | 固定 100 ms latency 的 buffered diagnostic |
| `CENTERED_100MS` | `[-100, +100] ms` | 是 | centered/offline diagnostic |
| `CENTERED_250MS` | `[-250, +250] ms` | 是 | centered/offline diagnostic |
| `CENTERED_500MS` | `[-500, +500] ms` | 是 | centered/offline diagnostic |

实际选择条件为闭区间：`run_p1e_shell_uncertainty_region_topology.py:260-267`。输出显式记录允许未来延迟、是否实际读到未来 observation：`run_p1e_shell_uncertainty_region_topology.py:329-348`。

`buffered latency` 的定义是预声明窗口上界 `max(0, high_offset_ms)`；它不是测得的网络、传输或处理延迟。

### 2.5 optical unavailable 的表达

若某帧某 policy 没有符合条件的 optical detection：

- 不生成 synthetic detection 或零宽壳；
- 该帧没有对应 shell row；
- frame summary 中 `track_shell_available=False`、active shell count=0：`run_p1e_shell_uncertainty_region_topology.py:449-468`。

这与“检测存在但角度为 0”或“PERSON 不存在”严格不同。

## 3. SAR 时间基准与 optical↔SAR nominal mapping

### 3.1 SAR FPS 与 timestamp

SAR 伪彩视频同样使用 OpenCV metadata 与 index/FPS 合成时间戳。R01–R04 均为：

- `30.0 FPS`
- `495 frames`
- `1024×592`
- nominal step 33/34 ms

证据：`video_inventory.csv:1-9` 与 `export_paired_frames.py:43-61,90-103`。

### 3.2 当前 sync registry

R01–R04 的当前 registry 都是：

- `time_scale = 1.0`
- `offset_ms = 0.0`
- `drift_ppm = 0.0`
- `sync_uncertainty_ms = 250`
- `sync_status = NOMINAL_INDEX_FPS_ZERO_OFFSET_UNVERIFIED`
- `sync_semantics = PLACEHOLDER_FOR_PER_RUN_VALIDATED_OFFSET_SCALE_AND_UNCERTAINTY`

证据：

`output/new_scene_vehicle_temporal_segments_20260818/full_65_identity_v2_20260818/sync_registry.csv:1-5`

严格同步结论：`NOT_CALIBRATED`。

### 3.3 实际时间变换和最近帧选择

Optical→SAR nominal time：

`t_sar_target = time_scale * t_optical + offset_ms`

SAR→optical query：

`t_optical_query = (t_sar - offset_ms) / time_scale`

证据：`build_annotation_batch.py:615-663`。

最近帧选择使用绝对 timestamp residual；等距时取较小 frame index：`build_annotation_batch.py:65-72`。当前没有 interpolation 到中间图像，也不是 frame-number equality。

### 3.4 SAME_FRAME 的准确含义与 nominal residual

`SAME_FRAME` 表示：针对每个 SAR frame，使用 registry 变换后 nearest optical frame 的 nominal timestamp，并要求 optical observation timestamp 等于该 query timestamp。它不表示两个传感器已经通过独立物理事件验证为同一曝光时刻。

对现有 explorer 中 R01–R04 共 398 个 SAR frame 的已物化 nominal pairs，只读计算：

- residual 定义：`sar_timestamp_ms - nominal_optical_timestamp_ms`
- min = `-23 ms`
- median = `0 ms`
- max = `+23 ms`
- absolute P95 = `23 ms`

该 residual 可计算，但只反映 18 FPS 与 30 FPS nominal grids 的最近帧量化差，不能当作同步误差上界或校准结果。

## 4. Optical→SAR azimuth mapping

### 4.1 固定公式、输入输出和方向

当前固定 mapping：

`theta_deg = 0.02666536443690682 * optical_x_px - 45.502258572693094`

- 输入：optical 图像横坐标 `x_px`，原点在图像左侧，向右增加；当前宽度 3840 px；
- 输出：SAR fan azimuth，单位 degree；
- slope：`0.02666536443690682 deg/px`；
- intercept：`-45.502258572693094 deg`；
- 正方向：SAR image-right 为正 azimuth；
- 当前 mapping 只依赖 optical x，不使用 optical y、box height、depth、SAR range 或 PERSON reference at runtime。

运行常量：`run_p1e_runtime_track_response_region_minimal.py:69-80`。

### 4.2 detection box → interval → guard → clipping

无 guard detection interval：

- lower = `f(bbox_x1)`
- upper = `f(bbox_x2)`

当前主实现随后在两侧加入固定 ±6°：

- `theta_shell_low = f(bbox_x1) - 6°`
- `theta_shell_high = f(bbox_x2) + 6°`

证据：`run_p1e_runtime_track_response_region_minimal.py:223-239`。

最新分解实现先保留无 guard box intervals，再分开计算：

1. representative single detection-box angular width；
2. temporal/view union increment；
3. guard union increment；
4. fan clipping loss；
5. common-FoV overlap；
6. fragment availability/provenance。

证据：`run_p1e_shell_uncertainty_region_topology.py:270-389`。

common-FoV 由 SAR fan 与整个 optical 横向映射范围相交得到；fan/common-FoV clipping 在 shell geometry 阶段加入：`run_p1e_shell_uncertainty_region_topology.py:289-320`。

因此禁止把以下量合并成一个“mapping error”：

- detection-box angular span；
- temporal/view union；
- ±6° guard；
- fan clipping；
- common-FoV overlap；
- fragment missing/fragmentation；
- 尚未独立校准的 mapping/timing uncertainty。

### 4.3 参数来源与限制

参数来自：

`output/r01_person_azimuth_pilot_20260819/model_summary.json`

关键字段：

- `fixed_correspondence`：line 70 起；
- `designation = PILOT_REFERENCE_ONLY`：line 100；
- raw-pixel equation/slope/intercept：lines 104-106；
- 单 run timing 诊断为 `NOT_IDENTIFIABLE_FROM_THIS_STATIC_SINGLE_RUN_PILOT`：line 172。

它由 R01 锁定的 manual PERSON optical/SAR correspondences 拟合，因此可作为当前冻结配置复用，但不能称为独立 shared runtime calibration。R04 报告状态是 `PASS_PROVISIONAL_R04_FIXED_R01_CROSSRUN_CONDITIONAL_ON_SYNC`，`model_refit=false`；其支持仍以未验证同步为条件。

M0 禁止用 manual reference 重新拟合 slope/intercept、offset 或 guard。

## 5. SAR pixel → range/azimuth 几何

### 5.1 1024×592 固定扇面参数

权威文件：

`output/pseudocolor_azimuth_calibration_20260803/geometry/fan_geometry_report.json:1-20`

参数：

- image size：1024×592 px；
- fan center：`(cx, cy) = (511.74532586922845, 590.7763512520755)` px；
- radius：`591.3403167097985 px`；
- outer range：`20.0 m`；
- `29.567015835489922 px/m`；
- `0.0338214720607576 m/px`。

### 5.2 坐标定义

图像坐标：

- origin：top-left；
- x：向右增加；
- y：向下增加。

range：

`r_m = hypot(x - cx, y - cy) / px_per_m`

azimuth：

`theta_deg = degrees(atan2(x - cx, cy - y))`

正 azimuth 指向 image-right。实际 grid 实现：`run_p1e_shell_uncertainty_region_topology.py:224-233`。

### 5.3 valid mask、fan 与 common-FoV

单帧有效区同时要求：

- range ≥ 0.75 m；
- range ≤ fan radius；
- theta 在当前 frame fan bounds 内；
- rendered fan 非白；
- 之后做固定 3×3 morphological open。

证据：`run_p1e_candidate_recall_audit.py:122-145`。

P0 transport reliable domain 与该单帧 valid mask 不是同一个对象；单帧 observable 不自动意味着某个 lag 的 P0 pair/model 可用。

### 5.4 response-region 已有字段

`response_region_table_pre_reference.csv` 共 69,201 rows，已有：

- `range_min_m`, `range_max_m`；
- `theta_min_deg`, `theta_max_deg`；
- `centroid_x_px_shape_descriptor`, `centroid_y_px_shape_descriptor`；
- `area_m2`, `major_extent_m`, `minor_extent_m`, `elongation`；
- `touches_observable_boundary`, `has_truncated_support`；
- percentile layer、region label/id、score descriptors。

所以 optical 与 SAR motion 可先在角度单位比较；SAR range change 只能作为 SAR-side auxiliary evidence。

## 6. P0 坐标、方向和数学语义

### 6.1 P0 实际是什么

P0 是 pair-specific、source frame `t` → destination frame `t+lag` 的公共表观输运模型。LK 在代码中明确先 source→destination，再 destination→source 做 forward-backward check：`run_p0_common_apparent_motion.py:396-415`。

基础拟合量：

`fit_disp = fit_tracked - fit_points`

证据：`run_p0_common_apparent_motion.py:529-544`。

单位和坐标：

- 单位：image pixel；
- vector：`[dx, dy]`；
- x 正方向：right；
- y 正方向：down；
- 方向：source → destination；
- 它不是平台 trajectory、世界坐标 motion 或 PERSON physical motion。

### 6.2 模型族与冻结选择

- M0：zero displacement；
- M1：robust global translation；
- M2：global affine transform；
- M3：spatial polar-basis displacement field。

代码：`run_p0_common_apparent_motion.py:529-610`。

冻结选择：

- lag1 = M1；
- lag3 = M2；
- lag5 = M2。

来源：`p0_common_apparent_motion/model_selection_R01.json`。

预测函数接受任意点集：`run_p0_common_apparent_motion.py:613-630`。M2 的准确形式为：

`destination = point @ A.T + b`

并返回：

`destination - point`

### 6.3 reliable domain 与 unavailable

P0 可用性是 pair/model/comparability 问题。现有 `comparability_registry.csv` 明确保存：

- `scheduled`, `comparable`, `comparability_reason`；
- valid fraction；
- tracked/fit/holdout anchor count；
- spatial coverage；
- display condition；
- PERSON/boundary mask violation checks。

后续 observation/topology schema 把位置状态区分为 `P0_TRANSPORT_CORE`、`P0_TRANSPORT_EXTENDED`、`P0_TRANSPORT_UNAVAILABLE`。`UNAVAILABLE` 不是有效 zero vector；M0 不得将不可用 pair 默认为 M0 或无运动。

### 6.4 是否可作用到 region mask

数学上：可以。`predict_displacement()` 可以对 mask 内任意 pixel centers 求前向位移，不需要读取 PERSON reference。

工程上：尚未建立权威实现。当前 task scripts 中没有 `warpAffine`、`warpPerspective`、full-mask `remap` 或统一 region-mask warp API；已有代码只对 points/candidate nodes 做预测和 destination-valid sampling。

因此当前状态是：

`MASK_WARP_MATHEMATICALLY_FEASIBLE / NOT_IMPLEMENTED / NOT_MATERIALIZED`

执行 M0 前必须冻结：

- forward support rasterization 或 inverse remap；
- binary/soft occupancy 语义；
- interpolation；
- destination validity mask；
- out-of-frame、hole、collision 处理；
- retained-source denominator；
- split/merge edge如何共享 warped support。

在此之前，不应以 `region centroid displacement - P0 vector` 作为主定义。

## 7. 当前已有 SAR temporal information 与可复用代码

历史 `dynamic_evidence_temporal_v1` 实际做过：

- run：R02ZF；
- lag：1；
- node：离散 C2 peak/candidate，不是 field/region；
- P0：冻结 lag1 M1，对 source node points 前向预测；
- distance：预测点到 destination nodes 的像素距离，以 local design uncertainty 归一化；
- controls：correct P0、zero、reverse、+0.75 m tangential、固定 shift7 shuffled source；
- graph：mutual-nearest edges 与 forced threads；
- score：geometry support 与 C2 max/sum/mean 派生量。

代码证据：

- pair/model/comparability 加载：`run_p1e_dynamic_evidence_temporal.py:323-377`；
- point polar/local uncertainty：`:380-440`；
- point prediction与 controls：`:491-567`。

现有审阅结论是 temporal persistence 存在，但 P0-specific lag1 gain 未建立；correct P0 与 zero 的 edges 高度重合。旧 temporal gate 已 superseded。

### 7.1 可复用

- P0 pair/model parameter loading；
- `predict_displacement()`；
- pair comparability 与 local anchor/domain audit；
- pixel↔polar conversion；
- destination valid-mask sampling；
- deterministic matched-condition accounting；
- pre-reference manifest / execution ledger / freeze-before-reference 模式；
- 当前 q90/q95/q97.5 masks、region descriptors；
- 最新真实像素 shell–region topology 的 node/edge/component schema。

### 7.2 只能作历史参考，不得复用为 M0 语义

- peak-node representation 作为主对象；
- mutual-nearest threading；
- forced one-to-one path；
- max/sum score fusion；
- 固定 1σ/2σ thread threshold；
- 旧 temporal qualification gate；
- reference-conditioned branch/path selection；
- fixed shift7 作为唯一 calibrated null。

## 8. M0 runtime/pre-reference 字段白名单草案

### 8.1 允许进入 consistency calculation

- raw optical detections；
- `raw_track_fragment_id`；
- optical `timestamp_ms`；
- fixed optical→SAR azimuth mapping；
- predeclared guard/time policy；
- SAR C2/S(x)；
- q90/q95/q97.5 response-region masks/descriptors；
- SAR fan geometry、single-frame valid mask、common-FoV；
- frozen P0 model/pair comparability/domain；
- latest pixel shell–region topology；
- runtime-legal boundary/truncation/display conditions。

### 8.2 禁止进入 consistency calculation

- `physical_target_id`；
- manual SAR box、center、range、azimuth；
- offline one-to-one assignment；
- best track/branch selected using reference；
- stitched `optical_person_id` 的 continuity/assignment 信息；
- `source_parent_stitched_ids`、accepted-parent provenance 作为动态特征；
- manual-selected region/path；
- `PEAK_MISSING_REGION_PRESENT`、PERSON `SHARED_REGION` 或 P01–P04 labels；
- reference-tuned timing、mapping、guard、lag、threshold 或 warp convention。

这些离线字段只能在全部 M0 hypotheses 和 descriptors 物化并冻结后用于评价。

## 9. 当前缺失或未校准项

1. `TIME_SYNC_NOT_CALIBRATED`：没有硬件 PTS/event-based offset/drift 独立标定；当前 ±23 ms 只是 nominal-grid residual。
2. `DROPPED_FRAME_NOT_AUDITED`：只验证 decode/index 连续，不验证采集端 drop。
3. `RUNTIME_OPTICAL_IDENTITY_NOT_ESTABLISHED`：raw fragments 合法但碎片化；stitched proxy 不是 causal runtime。
4. `AZIMUTH_MAPPING_NOT_INDEPENDENTLY_SHARED_CALIBRATED`：当前 slope/intercept 来自 R01 manual PERSON pilot，R04 仅 conditional-on-sync 验证。
5. `GUARD_COVERAGE_NOT_CALIBRATED`：±6° 是冻结设计 guard，不是统计置信界。
6. `MASK_WARP_CONVENTION_NOT_FROZEN`：点预测可用，region-mask warp 未实现/物化。
7. `PERSON_REGION_IDENTITY_NOT_ESTABLISHED`：response-region 是相对响应支持，不是 PERSON box/identity。
8. `SEALED_PROCESS_ISOLATION_NOT_ESTABLISHED`：当前依赖靠字段净化和先物化顺序守边界，不等于 reference 文件从未加载。

## 10. 对 M0 的直接准入判断

允许进入 docs-defined minimal pilot，但仅限以下口径：

> 在 nominal time、冻结 mapping、runtime-legal raw fragment 与 GT-blind response-region/P0 条件下，测试正确短时动态解释是否相对 matched wrong explanations 更能保留 region support，并减少 static shell–region many-to-many ambiguity。

不允许声称：

- 严格同步下的真实跨模态速度一致性；
- PERSON physical motion recovery；
- runtime identity assignment；
- SAR final localization；
- q95 region 是 PERSON confidence/box；
- P0 是平台真实运动。

本审计没有运行新的 motion-consistency 实验。
