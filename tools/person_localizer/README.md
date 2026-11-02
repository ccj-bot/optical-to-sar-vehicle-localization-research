# PERSON localizer 0.1.0rc9

2026-10-29：统一CLI已支持`legacy/recovery/sequence`。旧scene仍按原路由运行；新scene可声明`person_engine=sequence`和`sequence_manifest`，也可直接传`--manifest`。manifest的config控制采样、持续HOLD、初始化和标注状态；不再需要任务脚本替换生命周期函数。

```powershell
& python -X utf8 -B tools/person_localizer/cli.py --manifest 路径/manifest.json --output 新目录
```

新增显式配置：

- `persistent_proposal_center=true`：光学缺测/HOLD时保持上一搜索网格中心，避免网格跳回初始点造成断链；不补造光学观测、不解除HOLD。默认关闭保持已验证旧分支。R07完整源试验在第345/346/348帧定位到这一断链并单独启用。
- `initialization_geometry_scope=local_A`：自动初始化只取原时间包络构造后的A帧几何交集；默认`whole_track`保持旧行为。sequence manifest中的`initialization.mode=rebuild_automatic`会实际从当前源视频/光学重新求初点，`geometry_scope`指定范围；`manifest_seeds`明确复用已记录的初点。`INITIALIZATION.json`区分两种来源。
- `sequence_exit_policy`：`half_fov_deg/edge_band_deg/absent_edge_frames`替代旧任务里的60°临时替换，默认仍是旧55°政策。搜索域`fan_half_angle_deg`与显示支持/可见状态分开配置。
- `annotation_output.enabled=true`：输出注册质量、可见状态、源首/源尾删失和`ANNOTATIONS.csv`。`visibility`使用`half_angle_deg/edge_band_deg/outside_frames`，`use_rendered_support=true`读取真实显示扇面；`registration`可声明`max_holdout_p90_work_px`和`max_step_per_sar_frame_work_px`复核预算。预算是标注复核政策，不是已经标定的目标误差阈值。
- `current_SAR_update`与原生x/y保持数值求解结果；注册异常、HOLD、图像外等进入独立`annotation_state`。原`definite_point`保存在`model_definite_point`，新值受可见性/质量限制。连续HOLD和不可信注册不能触发出画或复活旧片段。源首已有目标标为删失，短实验片尾为`SEGMENT_END_OPEN`。
- recovery不使用公共锚点运输，质量字段标为`NOT_APPLICABLE_NATIVE_FRAME_ENGINE`；仍执行同样的可见性/输入状态输出。scene可用`person_config`选择自身配置。`--gate-only`仍只做光学资格检查；`--feedback`只能显式用于带终端反馈的sequence manifest。

运行冻结保存原manifest和变换后的`resolved_groups`两份坐标，避免把已减过公共平移的seed当原始seed再次减。`PACKAGE.json`记录实际引擎；原预测CSV和人工标签都不作为新推断的替代输入。

历史阶段（2026-10-28）：`sequence_runner` 增加`raw_support_sampling={"enabled":true,"saturation_min":50}`及`persistent_input_hold=true`。两项默认关闭以保留旧路径；R04真实数据修复与R07前缀检查见`output/person_followthrough_20261028/REPORT.md`。当日生命周期尚未接入CLI；这一入口缺口已由上述rc9整合处理。

条件SAR显示图像响应定位的可复用测试版。输入：场景JSON、光学人物轨迹CSV、SAR伪彩视频。输出：A选择封存、B条件图像预测、原生像素位置、缺测/不相容/多query状态和清单。不使用逐目标人工SAR初框，不输出确认人体轮廓。

## rc8：重叠联合关联、缺测补位与局部回搜

新版已接入同一个CLI。使用`--engine recovery`，或在scene JSON设置`"person_engine": "recovery"`。
默认`--engine auto`遵循scene.person_engine；旧scene未声明引擎时沿用legacy。可用`--engine legacy`明确运行兼容路径。

本机R50的完整输入示例已保存为`output/person_algorithm_rc8_20261027/R50ZF.json`：

```powershell
& python -X utf8 -B tools/person_localizer/cli.py --scene output/person_algorithm_rc8_20261027/R50ZF.json --output output/person_rc8_new_run
```

`recovery.py`提供无文件系统依赖的数值接口；`recovery_runner.py`负责实际输入、自动核心、联合恢复及封存。
运行时从当前视频和光学轨迹重新建立孤立清晰人物的自动响应DAG，再估计本场景的弱尺度乘积与方位偏差。
没有导入实验tasks代码、旧预测CSV或人工SAR坐标。光学小框/遮挡仍留质量审计，成熟轨迹允许进行实测方位搜索。

重叠轨迹在同一张共享响应图中做精确联合最短路径，同一观测不能被多人重复占用；具体弱位置状态贯穿缺帧。
之后以双向位置模型、有界当前SAR回搜补齐清晰人物的内部及首尾缺测。`current_SAR_update`与`inferred`逐帧区分。
`core_support_retained`表示从当前输入自动重新得到的DAG支撑，不表示加载了历史坐标或人工确认。

scene可选`response_recovery`设置：`background_first_frame`、`tail_search_sar_frames`、`last_sar_frame`和`policy`。
其中`policy`字段见`RecoveryPolicy`，包括峰预算、空间软约束、联合状态预算及缺测回搜半径。
R50示例仅指定背景起始帧150，以维持本轮对照同口径；没有把R50的尺度或角差写入全局配置。
没有孤立清晰尺度参考时，保留路由回执并运行legacy，避免借用另一场景尺度。

新增输出：`AUTOMATIC_CORES.json`、`CORE_RESPONSES.csv`、`SCENE_PROXY.json`、`RECOVERY_POLICY.json`、
`RECOVERY_ROUTE.json`、`LIFETIMES.json`、逐帧`PREDICTIONS.csv`、查询清单`RESULTS.json`和`SOURCE_SEAL.json`。
预测超出扇形只结束这段有界位置搜索，记为未确认的边界假设；中部无峰不记作出画，源结束不记作出画。

本轮源输入回归：R50共421条人物帧记录，与前一版视频坐标及响应状态一致；后段97帧含80帧响应、17帧补位。
R01/R04 legacy合计285条输出与旧版一致。这些是实现一致性与兼容性检查，不是六场景身份准确率提升结论。
实验结果与运行命令见`output/person_algorithm_rc8_20261027`。

运行：python -m person_localizer.cli --scene scene.json --output 新目录，需将workspace/tools加入PYTHONPATH；也可直接运行tools/person_localizer/cli.py。

scene.json需要scene_id、sar_video、optical_csv、native_width、native_height、sar_fps、queries。光学CSV需要query、optical_frame、sar_frame、theta、theta_lo、theta_hi，可另含image_path和光学框字段。queries为本次处理的光学ID列表；全部输入query均在inventory留状态。

rc4默认开启光学输入筛选，启用时CSV必须含原生bbox_x1/y1/x2/y2，并通过scene的optical_width/optical_height、光学视频或光学图像解析尺寸；缺失时HOLD，不默认为通过。默认框高/图高>=5%、框高/宽>=1.2、无贴边截断、方位区间与既有±55°工作扇形有交集，至少7个唯一光学可用帧。它们是可调整的输入质量规则，不代表量程标定或完整人物识别；局部/非站立嫌疑、小目标、缺测均保留HOLD原因，不宣称物理超量程。

查询和逐帧审计写入QUERY_ELIGIBILITY.csv、OPTICAL_FRAME_ELIGIBILITY.csv和INPUT_GATE.json；被暂缓/排除query仍在RESULTS.json中，且不搜索、不输出坐标。全部人物光学观测仍保留用于背景运动的排除掩码，避免把被暂缓人物当作静态背景。锚点、几何约束和B读出只使用通过筛选的帧。

仅做筛选：python tools/person_localizer/cli.py --scene scene.json --output 新目录 --gate-only。自定义配置用--config；禁用input_gate.enabled可保留rc3输入行为作诊断对照。旧rc3冻结目录和压缩包保持不变。

米制量程门控仅在scene.range_gate.status为INDEPENDENTLY_VERIFIED、provenance非空且sar_min_m/sar_max_m有效时启用；CSV需提供具有相同距离口径的range_lower_m/range_upper_m。仅区间完全无交集才标EXCLUDE_OUTSIDE_CONFIRMED_RANGE。缺少独立量程来源时不做米制排除。

rc5增加光学车辆重合门控：任意车辆检测框覆盖人物框面积超过50%即HOLD_VEHICLE_OVERLAP。使用人物面积为分母的IoP，不用IoU，避免小人物处在大车内时重合被稀释。该状态只表示2D重合/遮挡嫌疑，不能确认人在车内；车辆漏检、仅检测到露出的头部、框不相交的真实遮挡仍可能漏过。

可提供scene.vehicle_evidence_csv（query,optical_frame,vehicle_overlap_fraction,vehicle_check_status）；状态须为DETECTOR_COMPLETED，缺记录不当作无车。缺少缓存时使用配置指定冻结YOLO权重，对光学视频自动检测car/motorcycle/bus/truck。运行回执VEHICLE_EVIDENCE_USED.csv保留全部检查。光学检测可用GPU，SAR数值路径仍为CPU；不使用SAR车框或GT触发该门控。

可选all_optical_observation_readout=true对A外所有可用光学观测执行B图像读出；部分帧的光学角带已参与几何约束，不将其称为盲几何测试。默认关闭以保留原稀疏读出口径。

固定配置在config.json。方位映射来自R01开发拟合，不是新场景独立标定。中央DoG与边缘有效像素正响应依据光学锚点方位选择；边缘使用已声明±250ms光学时间并集。工作宽度固定1024，原生像素中心变换有显式记录。背景运输是图像域公共平移假设，不是物理运动；B注册使用B图像，目标位置选择的评分仅使用A。

本版只自动穷举双query组。更大相互竞争组、预算不足、源缺测均留为未决，不裁top-k制造确定答案。所有帧/候选/像素数是相关图像观测，不作为独立样本数。

无任务目录或历史预测导入。numPy/SciPy/OpenCV/pandas/Pillow为运行依赖。版本与冻结SHA由交付包记录；不把工程可运行称为跨场景识别已验证。

rc6增加可选光学前端`optical_tracking.OpticalPersonTracker`：同顶部/横向对齐的包含框消歧，BoT-SORT卡尔曼关联、相机公共运动补偿；相邻实测帧的快速入画可用颜色直方图和有界中心位移建立关联，无新增ReID模型。失踪轨迹不输出补帧框。输入是冻结检测框、置信度>=0.25、实际光学图像和同帧车框，返回实测框对应ID、确认状态、车辆遮挡记忆；被消歧观测另列审计。前端另需已安装的Ultralytics，SAR CLI仍接受光学轨迹CSV，不隐式重跑检测。

车辆重合触发暂缓后，半身框缩小不立即解除；要求连续3个低重合且下端/横向摆脱车框的实测观测后恢复。它是保守输入状态，不能证明是否坐在车内。CSV可携带tracking_status和visibility_status，待确认或VEHICLE_OCCLUSION_MEMORY帧不进入SAR。scene声明optical_tracking_version=refined时，缺跟踪/可见性证据按HOLD处理；旧CSV行为保持兼容。五场景同检测输入对照及无字媒体见output/person_tracking_refinement_20261026；仍为开发版本。

rc7进一步加入车辆上下文：车辆候选不按car/truck/motorcycle类别硬分身份，近重复框合并、重叠候选共享当前观测别名；人物绑定随当前代表框迁移，避免车辆框切换造成永久HOLD。车辆上缘局部人体可在零IoP、无旧轨迹历史时进入VEHICLE_UPPER_BODY_OCCLUSION；已绑定车辆真正缺测时为VEHICLE_CONTEXT_UNAVAILABLE，不能把缺测当作已离车。仅连续实际分离观测解除状态。

额外人体区域主要位于车体、且只包住一个同顶部人体观测的宽框，作为VEHICLE_CONTAMINATED_PERSON_EXTENT消歧；多个头部、无车辆证据时不作该合并。所有框仍是原始实测框，没有扩张车框来吞并人，也没有改SAR定位核心。此为2D遮挡/归属嫌疑，不确认车内乘员、物理遮挡或目标身份。新门控状态由eligibility消费，细节与五场景回归见output/person_vehicle_context_20261026。
