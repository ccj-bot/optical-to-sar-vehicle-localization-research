# PERSON P1E 候选存在性—唯一定位性语义拆分

> 状态：`SEMANTIC_SPLIT_COMPLETE_TEMPORAL_GATE_NOT_OPEN`  
> 数据角色：R01/R02/R03/R04 均为已暴露开发语料；不授予 P1_PASS；本轮未运行时序。

## 结论

R02 不是单一的“PERSON 响应不存在”，也不是整体的“Top-5 候选召回已经成立”。

- P01：9/9 帧在 0.8 m 内存在 C2 局部峰，但最近 rank 中位数 14.0，Top-5 为 0/9。
- P02：7/9 帧在 0.8 m 内存在峰，Top-5 为 0/9；另 2/9 为半径级候选缺失/当前表示未捕捉。
- P03/P04：各 8/9 进入 Top-5、5/9 为 Top-1，但九帧均出现同一 GT-blind 候选落入多个 reference 的 0.8 m 邻域。
- R02 总体 Recall@1/3/5(0.8 m) = 27.8% / 44.4% / 44.4%；Top-5 相对 Top-1 仅恢复 16.7%。

因此，P01/P02 多数属于“参考附近有低 rank 原始峰，但没有进入高响应 Top-5 短名单”，P02 还混有 2 个候选缺失；P03/P04 属于“候选召回成立，但共享响应与唯一性不足”。`response_merging_suspected` 仅为图像域诊断，不是物理融合证明。

## 三层评价

1. 原始峰存在：任意 GT-blind 局部峰是否在 reference 的固定半径内。
2. 候选短名单召回：固定 K=1/2/3/5 的 Recall@K(r)。
3. 单帧唯一定位：reference 能否击败局部强竞争响应、是否 Top-1、是否与其他 reference 共享候选。

原 hard-background 应改释为 `local competing-response pool`。`peak_to_reference_center_offset` 只表示算子高分位置相对人工框几何中心的偏移，不直接等于物理分辨率或真实散射中心误差。

## R02 分目标

| R02 target | n | R@1 | R@3 | R@5 | any-rank peak <=0.8m | median rank | radius misses | any shared peak | best peak shared |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P01 | 9 | 0.0% | 0.0% | 0.0% | 100.0% | 14.0 | 0 | 77.8% | 33.3% |
| P02 | 9 | 0.0% | 0.0% | 0.0% | 77.8% | 14.0 | 2 | 77.8% | 77.8% |
| P03 | 9 | 55.6% | 88.9% | 88.9% | 100.0% | 1.0 | 0 | 100.0% | 100.0% |
| P04 | 9 | 55.6% | 88.9% | 88.9% | 100.0% | 1.0 | 0 | 100.0% | 100.0% |

## 跨 run

| run | references | R@1 0.8m | R@3 0.8m | R@5 0.8m | any-rank peak <=0.8m | median nearest rank | merging suspected |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R01ZF | 99 | 49.5% | 86.9% | 90.9% | 100.0% | 2.0 | 60.6% |
| R02ZF | 36 | 27.8% | 44.4% | 44.4% | 94.4% | 8.0 | 88.9% |
| R03ZF | 4 | 0.0% | 0.0% | 25.0% | 100.0% | 9.5 | 0.0% |
| R04ZF | 112 | 17.0% | 51.8% | 67.0% | 100.0% | 3.0 | 0.0% |

## 候选池规模

| run | operator | frames | candidate count min/median/max | spacing min/median (m) |
| --- | --- | --- | --- | --- |
| R01ZF | C2 | 39 | 251 / 285 / 312 | 0.451 / 0.460 |
| R01ZF | C3 | 39 | 375 / 397 / 426 | 0.451 / 0.451 |
| R02ZF | C2 | 23 | 219 / 294 / 327 | 0.451 / 0.471 |
| R02ZF | C3 | 23 | 334 / 399 / 422 | 0.451 / 0.451 |
| R03ZF | C2 | 4 | 331 / 338 / 346 | 0.451 / 0.452 |
| R03ZF | C3 | 4 | 413 / 431 / 444 | 0.451 / 0.452 |
| R04ZF | C2 | 60 | 244 / 305 / 334 | 0.451 / 0.460 |
| R04ZF | C3 | 60 | 381 / 418 / 445 | 0.451 / 0.451 |

## C3 诊断

| R02 target | R@1 | R@5 | any-rank peak <=0.8m | median rank |
| --- | --- | --- | --- | --- |
| P01 | 0.0% | 0.0% | 100.0% | 121.0 |
| P02 | 0.0% | 0.0% | 100.0% | 99.0 |
| P03 | 77.8% | 88.9% | 100.0% | 1.0 |
| P04 | 77.8% | 88.9% | 100.0% | 46.0 |

C3 对 P01/P02 的 Recall@5 仍为 0，最近 rank 中位数约 121/99，没有形成修复。

## 单帧域与时序域

| frame | old frozen-P0 P1E status | Omega_single_v1 | nearest d (m) | rank | Top5 |
| --- | --- | --- | --- | --- | --- |
| 458 | ABSTAIN_LOW_VALID_SUPPORT | FULL | 0.021 | 18 | no |
| 462 | ABSTAIN_LOW_VALID_SUPPORT | FULL | 0.102 | 13 | no |
| 488 | EVALUABLE | FULL | 0.086 | 5 | yes |
| 494 | EVALUABLE | FULL | 0.111 | 6 | no |

F458 在 `Omega_single_v1` 中为 FULL，且约 0.02 m 处有 C2 峰，但 rank=18。它证明“P0 不可比较不等于单帧不可观察”，不证明 Top-5 召回足够。

## 时序入口

| frozen check | observed | result |
| --- | --- | --- |
| R02 C2 Recall@5(0.8m) >= 60% | 44.4% | fail |
| Top5 - Top1 >= 20 percentage points | 16.7% | fail |
| reference - fixed-offset median >= 10 points | 44.4% | pass |
| P01 or P02 Recall@5 >= 50% | P01=0.0%, P02=0.0% | fail |

预注册门槛三项失败，因此本轮不运行 lag1/lag3。P0 输运能否改善候选 rank、是否提供新增信息，当前仍是未检验问题，不是阴性结论。

## 病例图

![R02ZF_SARF000472 / P01: C2 nearest rank 7, d=0.659 m, Top5=no, shared=yes. P01/P02 share a low-ranked C2 peak while P03/P04 share a Top-2 peak in the same frame.](single_frame_candidate_recall/visualizations_v2/case_v2_01_r02_f472_p01_shared_low_rank.png)

R02ZF_SARF000472 / P01: C2 nearest rank 7, d=0.659 m, Top5=no, shared=yes. P01/P02 share a low-ranked C2 peak while P03/P04 share a Top-2 peak in the same frame.

![R02ZF_SARF000482 / P02: C2 nearest rank 14, d=1.159 m, Top5=no, shared=no. P02 has no C2 candidate within 0.8 m; P03/P04 still share the Top-1 response.](single_frame_candidate_recall/visualizations_v2/case_v2_02_r02_f482_p02_missing.png)

R02ZF_SARF000482 / P02: C2 nearest rank 14, d=1.159 m, Top5=no, shared=no. P02 has no C2 candidate within 0.8 m; P03/P04 still share the Top-1 response.

![R02ZF_SARF000494 / P01: C2 nearest rank 24, d=0.698 m, Top5=no, shared=yes. P01/P02 share rank 24 on the long response chain; P03/P04 share rank 1.](single_frame_candidate_recall/visualizations_v2/case_v2_03_r02_f494_p01_long_chain.png)

R02ZF_SARF000494 / P01: C2 nearest rank 24, d=0.698 m, Top5=no, shared=yes. P01/P02 share rank 24 on the long response chain; P03/P04 share rank 1.

![R02ZF_SARF000483 / P03: C2 nearest rank 1, d=0.186 m, Top5=yes, shared=yes. P03/P04 are both covered by the same Top-1 C2 peak: candidate existence is strong, uniqueness is not.](single_frame_candidate_recall/visualizations_v2/case_v2_04_r02_f483_p03_top1_shared.png)

R02ZF_SARF000483 / P03: C2 nearest rank 1, d=0.186 m, Top5=yes, shared=yes. P03/P04 are both covered by the same Top-1 C2 peak: candidate existence is strong, uniqueness is not.

![R02ZF_SARF000490 / P03: C2 nearest rank 12, d=0.759 m, Top5=no, shared=yes. The shared P03/P04 response falls to rank 12, showing frame-dependent shortlist instability.](single_frame_candidate_recall/visualizations_v2/case_v2_05_r02_f490_p03_shared_rank12.png)

R02ZF_SARF000490 / P03: C2 nearest rank 12, d=0.759 m, Top5=no, shared=yes. The shared P03/P04 response falls to rank 12, showing frame-dependent shortlist instability.

![R03ZF_SARF000458 / P01: C2 nearest rank 18, d=0.021 m, Top5=no, shared=no. Omega_single_v1 is FULL and a C2 peak lies about 0.02 m from reference, but only at rank 18.](single_frame_candidate_recall/visualizations_v2/case_v2_06_r03_f458_single_frame_full.png)

R03ZF_SARF000458 / P01: C2 nearest rank 18, d=0.021 m, Top5=no, shared=no. Omega_single_v1 is FULL and a C2 peak lies about 0.02 m from reference, but only at rank 18.

![R03ZF_SARF000488 / P01: C2 nearest rank 5, d=0.086 m, Top5=yes, shared=no. Boundary-scene single-frame observation is FULL and the nearby C2 peak reaches rank 5.](single_frame_candidate_recall/visualizations_v2/case_v2_07_r03_f488_top5_boundary.png)

R03ZF_SARF000488 / P01: C2 nearest rank 5, d=0.086 m, Top5=yes, shared=no. Boundary-scene single-frame observation is FULL and the nearby C2 peak reaches rank 5.

![R04ZF_SARF000000 / P01: C2 nearest rank 1, d=0.097 m, Top5=yes, shared=no. An isolated response case where both C2 and C3 place rank 1 near the reference.](single_frame_candidate_recall/visualizations_v2/case_v2_08_r04_f000_isolated_top1.png)

R04ZF_SARF000000 / P01: C2 nearest rank 1, d=0.097 m, Top5=yes, shared=no. An isolated response case where both C2 and C3 place rank 1 near the reference.

## 文件

- [HTML 报告](P1E_CANDIDATE_RECALL_SEMANTIC_SPLIT_REPORT.html)
- [运行前冻结协议](00_CANDIDATE_RECALL_PROTOCOL_FROZEN_BEFORE_RUN.md)
- [原始 Recall@K CSV](single_frame_candidate_recall/manual_reference_candidate_recall.csv)
- [语义解释 v2 CSV](single_frame_candidate_recall/manual_reference_candidate_interpretation_v2.csv)
- [全部 GT-blind 候选](single_frame_candidate_recall/gt_blind_candidates_all_processed_frames.csv)
- [机器可读总结](single_frame_candidate_recall/candidate_semantic_interpretation_v2.json)
- [报告校验](single_frame_candidate_recall/report_validation.json)

冻结 P0、B0R、C0-C3 与旧 P1E 结果均未修改；本轮不授予 P1_PASS，不声称盲验证。
