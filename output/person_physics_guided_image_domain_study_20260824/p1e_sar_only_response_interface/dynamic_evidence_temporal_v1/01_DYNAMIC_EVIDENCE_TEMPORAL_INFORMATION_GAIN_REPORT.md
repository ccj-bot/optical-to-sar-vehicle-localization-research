# PERSON P1E 动态证据状态与最小时序信息增益

> 状态：TEMPORAL_STRUCTURE_PRESENT_P0_SPECIFIC_GAIN_NOT_ESTABLISHED  
> 数据角色：R02ZF 为已暴露开发语料；不设单帧资格 gate；不授予 P1_PASS。

## 结论

已经建立透明动态证据图，并证明真实序列有持续响应结构、gross 错误输运会破坏它；但冻结 P0 相对 zero transport 的特异信息增益尚未建立。

- 相对 zero transport 的 incoming-max 中位优势只有 1.5 名，正确更好/平/更差为 53.3% / 16.7% / 30.0%；全部候选 max/sum/mean 排序 Spearman 中位为 0.9756 / 0.9794 / 0.9916。
- P01 相对单帧在 6/8 帧改善，中位改善 3.0 名；P02 在 4/6 帧改善，中位改善 5.0 名。但相对 zero，P01 仅 4/8 更好，P02 仅 2/6 更好。
- P02 F482 在 0.8 m 下缺节点；F490 最近节点为约 0.820 m，是阈值边界病例。时序不能创造节点。
- P03/P04 的八个 manual 间隔在正确 P0 和 zero 下都保持 SHARED。F490/F494 的 max/sum 降级，但 mean rank 仍为 3/2、线程长 23，不能写成所有时序分量共同失败。
- 正确 P0 与 zero 的线程长度统计几乎相同，长线程不能单独归功于 P0。

## R02 分目标

| target | refs | missing | incoming n | image median rank | correct median rank | image→correct median gain | improved vs image | zero-correct median | correct better than zero | worsened ≥50 ranks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P01 | 9 | 0 | 8 | 11.0 | 10.0 | 3.0 | 75.0% | 2.0 | 50.0% | 1 |
| P02 | 9 | 2 | 6 | 18.0 | 15.5 | 5.0 | 66.7% | -3.5 | 33.3% | 2 |
| P03 | 9 | 0 | 8 | 1.0 | 1.0 | 0.0 | 12.5% | 2.5 | 62.5% | 2 |
| P04 | 9 | 0 | 8 | 1.0 | 1.0 | 0.0 | 12.5% | 2.5 | 62.5% | 2 |

![逐帧 rank](lag1_r02/post_analysis_v1/visualizations/manual_reference_rank_dynamics.png)

## 正确 P0 与对照

| component | control | paired n | median control-correct rank | correct better | tie | correct worse |
| --- | --- | --- | --- | --- | --- | --- |
| max | No transport | 30 | 1.5 | 53.3% | 16.7% | 30.0% |
| max | Reverse P0 | 30 | 7.5 | 73.3% | 0.0% | 26.7% |
| max | +0.75 m tangential | 30 | 85.0 | 76.7% | 0.0% | 23.3% |
| max | Shuffled source | 30 | 142.0 | 86.7% | 0.0% | 13.3% |
| sum | No transport | 30 | 1.5 | 53.3% | 13.3% | 33.3% |
| sum | Reverse P0 | 30 | 8.5 | 83.3% | 0.0% | 16.7% |
| sum | +0.75 m tangential | 30 | 103.0 | 76.7% | 0.0% | 23.3% |
| sum | Shuffled source | 30 | 140.0 | 86.7% | 0.0% | 13.3% |
| mean | No transport | 30 | 0.0 | 10.0% | 83.3% | 6.7% |
| mean | Reverse P0 | 30 | 0.0 | 16.7% | 76.7% | 6.7% |
| mean | +0.75 m tangential | 30 | 9.0 | 63.3% | 23.3% | 13.3% |
| mean | Shuffled source | 30 | 41.5 | 73.3% | 0.0% | 26.7% |

### 全部候选的 CORRECT-vs-ZERO 相似度

| component | frames | median frame Spearman | median exact-rank ties | median |rank delta| |
| --- | --- | --- | --- | --- |
| geometry | 22 | 0.9142 | 1.6% | 21.5 |
| max | 22 | 0.9756 | 3.4% | 11.5 |
| sum | 22 | 0.9794 | 4.0% | 10.0 |
| mean | 22 | 0.9916 | 19.3% | 2.0 |

| control | correct edges | control edges | correct-edge overlap | Jaccard |
| --- | --- | --- | --- | --- |
| No transport | 4654 | 4661 | 96.0% | 0.9210 |
| Reverse P0 | 4654 | 4615 | 91.0% | 0.8413 |
| +0.75 m tangential | 4654 | 3199 | 8.3% | 0.0516 |

正确 P0 与 zero 的互为最近邻边 96.0% 重合，线程长度 73.8% 完全相同，shared state 32/32 一致。+0.75 m 与 shuffle 只是 gross sanity，不是校准 null。

![正确 P0 与对照](lag1_r02/post_analysis_v1/visualizations/correct_p0_control_information_gain.png)

冻结 lag1 位移中位数约 0.103 m，局部区域 σ 中位数约 0.301 m；zero transport 通常仍落在同一可能区域内。

局部误差支持中，22.4% 使用 nearest-8 fallback，39.7% 至少一个距离/方位维度未被锚点双侧包围。

![输运尺度](lag1_r02/post_analysis_v1/visualizations/lag1_transport_vs_uncertainty_scale.png)

## 线程与固定空间控制

| condition | threads | median len | P90 len | max | nodes in len≥10 |
| --- | --- | --- | --- | --- | --- |
| CORRECT_P0 | 1803 | 2.0 | 8.0 | 23 | 31.0% |
| REVERSE_P0 | 1842 | 2.0 | 8.0 | 23 | 29.8% |
| TANGENTIAL_PLUS_0_75M | 3258 | 1.0 | 4.0 | 11 | 1.3% |
| ZERO_TRANSPORT | 1796 | 2.0 | 8.0 | 23 | 31.5% |

| condition | image ref-offset percentile | image positive | temporal ref-offset percentile | temporal positive | thread ref-offset nodes | reference longer |
| --- | --- | --- | --- | --- | --- | --- |
| CORRECT_P0 | 0.223 | 79.6% | 0.128 | 68.2% | 4.0 | 67.3% |
| ZERO_TRANSPORT | 0.223 | 79.6% | 0.109 | 65.9% | 4.5 | 67.3% |
| REVERSE_P0 | 0.223 | 79.6% | 0.121 | 67.1% | 4.0 | 62.2% |
| TANGENTIAL_PLUS_0_75M | 0.223 | 79.6% | -0.065 | 40.0% | -1.0 | 20.4% |

![线程持续性](lag1_r02/post_analysis_v1/visualizations/thread_persistence_reference_vs_offsets.png)

![x-y-t 投影](lag1_r02/post_analysis_v1/visualizations/spacetime_response_tube_projection.png)

`SHARED` 使用 0.8 m 邻域，而 P01/P02 间距仅 0.510–0.656 m、P03/P04 仅 0.695–0.808 m；它只表示邻域重叠/未观察到分离，不证明物理融合。

### 证据分量相互矛盾的病例

| frame | target | image rank | correct max | correct sum | correct mean | thread len | zero max |
| --- | --- | --- | --- | --- | --- | --- | --- |
| F483 | P02 | 9 | 114 | 116 | 15 | 7 | 86 |
| F487 | P02 | 18 | 198 | 203 | 17 | 7 | 134 |
| F490 | P01 | 13 | 255 | 269 | 15 | 2 | 281 |
| F490 | P04 | 12 | 105 | 120 | 3 | 23 | 116 |
| F490 | P03 | 12 | 105 | 120 | 3 | 23 | 116 |
| F494 | P04 | 1 | 206 | 220 | 2 | 23 | 221 |
| F494 | P03 | 1 | 206 | 220 | 2 | 23 | 221 |

## 直接病例

![F472→F473 P01/P02: P01/P02 start with low-ranked, partly shared local responses; temporal support improves some ranks but is not uniquely P0-specific.](lag1_r02/post_analysis_v1/visualizations/case_01_f472_f473_p01_p02_low_rank_shared.png)

F472→F473 P01/P02: P01/P02 start with low-ranked, partly shared local responses; temporal support improves some ranks but is not uniquely P0-specific.
![F472→F473 P03/P04: P03/P04 share a high response from the first pair; the legal state is shared rather than two resolved identities.](lag1_r02/post_analysis_v1/visualizations/case_02_f472_f473_p03_p04_high_rank_shared.png)

F472→F473 P03/P04: P03/P04 share a high response from the first pair; the legal state is shared rather than two resolved identities.
![F482→F483 P02: P02 has no C2 node within 0.8 m at F482; the F483 nearby node exists but receives poor incoming rank, so lag1 cannot recover a missing predecessor.](lag1_r02/post_analysis_v1/visualizations/case_03_f482_f483_p02_missing_then_competed.png)

F482→F483 P02: P02 has no C2 node within 0.8 m at F482; the F483 nearby node exists but receives poor incoming rank, so lag1 cannot recover a missing predecessor.
![F487→F488 P01/P02: A positive case: both low-rank P01/P02 responses improve under correct P0, although the advantage over zero transport remains modest.](lag1_r02/post_analysis_v1/visualizations/case_04_f487_f488_low_rank_partial_recovery.png)

F487→F488 P01/P02: A positive case: both low-rank P01/P02 responses improve under correct P0, although the advantage over zero transport remains modest.
![F489→F490 P01: A decisive counterexample: P01 image rank 13 collapses to incoming-max rank 255 under correct P0.](lag1_r02/post_analysis_v1/visualizations/case_05_f489_f490_p01_temporal_collapse.png)

F489→F490 P01: A decisive counterexample: P01 image rank 13 collapses to incoming-max rank 255 under correct P0.
![F489→F490 P03/P04: The shared P03/P04 response remains unresolved: max/sum ranks collapse to 105/120, while mean rank 3 and a 23-node thread remain supportive.](lag1_r02/post_analysis_v1/visualizations/case_06_f489_f490_p03_p04_shared_rank_collapse.png)

F489→F490 P03/P04: The shared P03/P04 response remains unresolved: max/sum ranks collapse to 105/120, while mean rank 3 and a 23-node thread remain supportive.
![F493→F494 P03/P04: A mixed-state counterexample: shared image Top-1 is demoted to max/sum ranks 206/220, while mean rank 2 and a 23-node thread remain supportive.](lag1_r02/post_analysis_v1/visualizations/case_07_f493_f494_top1_shared_temporal_collapse.png)

F493→F494 P03/P04: A mixed-state counterexample: shared image Top-1 is demoted to max/sum ranks 206/220, while mean rank 2 and a 23-node thread remain supportive.

## 当前边界

能确认的是：真实序列存在持续 SAR 响应，明显错误方向、gross 偏移和错误帧序会破坏它，部分低 rank 候选在某些时刻能得到支持。

仍不能确认的是：P0-specific lag1 信息增益、缺失节点恢复、P03/P04 身份分离，或可冻结的 SAR-only 定位接口。

建议的最小后续是预先固定 lag3/两步接续和 missing-state bridge，继续比较 correct、zero、错误输运与打乱帧；不新增硬 gate，也不重调 P0。

## 文件

- [HTML 报告](P1E_DYNAMIC_EVIDENCE_TEMPORAL_REPORT.html)
- [运行前冻结协议](00_DYNAMIC_EVIDENCE_MINIMAL_TEMPORAL_PROTOCOL_FROZEN_BEFORE_RUN.md)
- [runtime graph manifest](lag1_r02/runtime_graph_manifest.json)
- [逐 reference 配对表](lag1_r02/post_analysis_v1/manual_reference_correct_vs_controls.csv)
- [固定空间控制比较](lag1_r02/post_analysis_v1/reference_vs_fixed_offset_temporal_comparison.csv)
- [显示分层比较](lag1_r02/post_analysis_v1/display_stratum_temporal_comparison.csv)
- [机器可读解释](lag1_r02/post_analysis_v1/dynamic_evidence_interpretation_v1.json)
- [独立方法审阅与复现缺口](02_DYNAMIC_EVIDENCE_METHOD_AUDIT.md)
- [报告校验](lag1_r02/post_analysis_v1/report_validation.json)

冻结 P0、B0R、C0-C3 与旧 P1E 结果均未修改；不授予 P1_PASS，不声称盲验证。
    