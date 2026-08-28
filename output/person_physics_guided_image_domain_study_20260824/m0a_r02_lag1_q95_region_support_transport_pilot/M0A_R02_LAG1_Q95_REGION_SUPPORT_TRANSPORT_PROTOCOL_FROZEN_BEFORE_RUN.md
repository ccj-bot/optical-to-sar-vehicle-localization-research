# M0A R02 lag1 q95 region-support transport protocol

- Protocol state: `FROZEN_BEFORE_RUN`
- Freeze revision: `REV4_VALIDATOR_GROUP_INDEX_PERFORMANCE_ONLY`
- Study role: `M0_SAR_TEMPORAL_PREREQUISITE`
- Run: `R02ZF`
- Time status: `TIME_SYNC_NOT_CALIBRATED`
- Baseline commit: `edd7c1ba91577f18fa54877f82ee92eb779aab33`
- Starting HEAD: `edd7c1ba91577f18fa54877f82ee92eb779aab33`
- Active workspace: `D:\profile\research\workspace`
- Interpreter: `D:\MINICONDA\envs\py311\python.exe`
- Output directory: `D:\profile\research\workspace\output\person_physics_guided_image_domain_study_20260824\m0a_r02_lag1_q95_region_support_transport_pilot`

本文必须在任何 synthetic-test 或 M0A 数据结果生成前完成；实现哈希写回并生成独立 freeze record 后才能运行。

## 1. 科学问题与停止点

本轮只回答：

> 冻结 q95 response-region 在相邻 SAR 帧之间是否存在可重复、可解释的图像域 support continuity；这种 continuity 相对结构匹配 alternatives 是否有排序信息；冻结 lag1 P0 相对 zero transport 又提供多少额外贡献。

本轮不是完整 Optical–SAR motion consistency，不使用 raw optical angular dynamics，不回答 `static many-to-many -> dynamic fewer-to-fewer`，不建立 PERSON identity、tracker、path、assignment 或最终 SAR localization。

完成 M0A 后停止；不自动运行 lag3、lag5、two-step、M0B、classifier、score fusion 或 SAR box/localization。

## 2. 冻结范围

- 只使用 R02ZF SAR F472–F494。
- 只使用 22 个 adjacent nominal lag1 pairs。
- pair 必须同时满足 `pair_comparable=True`、frozen M1 selected、M1 model available。
- q95 为主 region layer；q97.5 为 strong core；q90 为 weak envelope。
- 当前 nominal timing 保持不变；不估 offset、不选择 lag、不修改 sync registry。
- response-region 是 `S(x)` 的帧内相对分位超水平区域，不是 PERSON box 或 confidence。
- P0 是 source→destination 图像域公共表观输运，不是平台或目标真实运动。

冻结 pair set：

`472→473, 473→474, 474→475, 475→476, 476→477, 477→478, 478→479, 479→480, 480→481, 481→482, 482→483, 483→484, 484→485, 485→486, 486→487, 487→488, 488→489, 489→490, 490→491, 491→492, 492→493, 493→494`

## 3. 冻结依赖

| dependency | SHA256 |
| --- | --- |
| baseline/current HEAD | `edd7c1ba91577f18fa54877f82ee92eb779aab33` |
| `run_p0_common_apparent_motion.py` | `0AB671B6A33A48CA2E3160A201629FA2DD341EF052A29B8D2CCBC2DFB26DCFD8` |
| `run_p1e_candidate_recall_audit.py` | `84CCAEBB9A195D184B6C34393CC71A7699E5F190D4D5FC253C16E337855CF0F8` |
| B0R R02/R03 model JSONL | `265ADC67D62C466F2D9523FDD06F0503BC9B4AE1343D1A63CCCC3D5FE8FF5E2D` |
| B0R pair metrics | `862BA1FEEE5A4A540DA03230F8A15192DE117BA002AB6FE67C2E8C2EFF0D042C` |
| B0R comparability | `4D0B454A7131212221AD3911B8A9652B93BF0BECDC35F1B9E54B19B4F5735D13` |
| response-region table | `A2BB425C366EA0DE461C427113E8E836A556F65250677146B6F26129E853C339` |
| shell decomposition pre-reference | `2AE24955FD8A4989A04DE38D91F2671BA6D6741DD7F6EE3FB09068BBEA5E3854` |
| region topology nodes pre-reference | `A475A73F20E96F0CA95D4902B8F940E494CB7424EE39B75C18CAEBCC48D46E8D` |
| fan geometry report | `B8A166D2ABCF57B1B3868692651D68610B5FA5B135E6D0BC48DC1D2CDB3F5A93` |
| R02 23 region-mask NPZ aggregate | `0C4D10144D42986382F689BA14DCCC3AFFAD4E5DA0B43F57ED57DCC7CED37863` |
| R02 SAR F472–F494 image aggregate | `1E8ED461192685DC7473D01B08D955B6DCB8FDC8D46DBA46B522ACA3E7F60658` |
| post-reference manual center table | `796F20EB3080C5B45CDEBBCC71584CC95C65691F056D46C4A31704A3D86E8EC7` |

Toolchain: Python 3.11.14, OpenCV 4.13.0, NumPy 1.26.4, pandas 2.3.3。

Implementation hashes must be inserted before protocol freeze:

| implementation | SHA256 before run |
| --- | --- |
| `run_m0a_r02_lag1_q95_region_support_transport.py` | `4ABA5781293EAE950DC78D530F33FC5191B81B7163AFCEC0AD38BFC030213FDC` |
| `test_m0a_mask_warp.py` | `AA82E876F4E0D8103EEB25100C966C261A7339B2C23C0EEEF8318D3723297374` |
| `validate_m0a_r02_lag1_q95_region_support_transport.py` | `F2E4297F2EBB6E9AA34FD33C52249F997607E76BA5918651DA0179A45539BDC6` |
| `render_m0a_r02_lag1_q95_region_support_report.py` | `C6AF40E4DDDEE7B06FC97AA0D1584C42FAE0007E260DF108D5C1A79DBC929FEE` |

## 4. Valid-domain contract

Destination valid mask 复用当前 single-frame semantics：

1. geometry center/radius/20 m 来自 frozen fan geometry；
2. inner range exclusion = 0.75 m；
3. theta 在 frozen frame fan bounds 内；
4. SAR rendered pixel 至少一个通道 `<248`；
5. 固定 3×3 morphological open；
6. 每帧 pixel count 必须与冻结 shell-decomposition table 中该帧自己的 `omega_single_pixel_count` 完全一致，否则立即停止。

R02 F472–F494 的冻结 cardinality 实际为逐帧 `364950` 或 `364951`；不能额外假定所有帧都等于同一常数。首次 preflight 在未写出 synthetic JSON 或实验结果前发现并移除了该错误常数断言，保留逐帧 metadata parity 作为唯一 cardinality 审计。

valid mask 只用于 transport denominator 和 destination support clipping；不改变 q90/q95/q97.5 region masks。

## 5. P0 与 soft affine mask-warp contract

Frozen lag1 model 是 pair-specific M1 translation：

`d = [dx, dy] = predict_displacement(point)`

坐标为 image pixels，x 向右、y 向下，方向为 source→destination。

P0 warp 固定为：

```text
M = [[1, 0, dx],
     [0, 1, dy]]
cv2.warpAffine(
    source_binary_float32,
    M,
    dsize=(width, height),
    flags=cv2.INTER_LINEAR,
    borderMode=cv2.BORDER_CONSTANT,
    borderValue=0,
)
```

不设置 `WARP_INVERSE_MAP`。输出 clip 到 `[0,1]`，名称固定为 `soft occupancy support`。不声称严格 conserved mass；不对 out-of-frame 或 invalid loss 重新归一化。

ZERO transport 使用完全相同 source mask、destination frame/pool/valid mask，只将 `M` 固定为 identity。

禁止 dilation、closing、opening、watershed、connected-component repair、reference-conditioned parameter 或任何 PERSON-specific修复。

## 6. Synthetic tests

运行数据前必须 5/5 PASS：

1. identity：输出逐像素等于输入；
2. integer translation：方向/位置/边界与预期一致；
3. subpixel translation：验证 bilinear soft occupancy，输出存在 `(0,1)` fractional pixels；
4. boundary loss：移出 raster 的 occupancy 不得被归一回来；
5. point-vs-mask consistency：代表点的 `predict_displacement()` destination 与 warped impulse occupancy center-of-mass 在固定容差内一致。

容差冻结为：identity/integer max error `1e-6`；subpixel soft-occupancy sum/center-of-mass error `1e-5`；P0 point-vs-mask center-of-mass error `0.05 px`，只使用离边界足够远的代表点。

## 7. Region-layer definitions

- q95 region mask：NPZ `Q095 == region_label`。
- q97.5 strong core：`Q0975>0` 与当前 q95 region mask 的像素交集；无 core 时 descriptors 为 `UNAVAILABLE/NaN`。
- q90 weak envelope：所有与当前 q95 region 有像素交叠的 q90 connected-component labels 的并集。
- region descriptors 来自冻结 pre-reference table；centroid 只作 shape descriptor。

## 8. Denominator contract

对每个 source region、condition、pair 先物化：

- `source_support_total = sum(source_binary_mask)`
- `warped_support_before_valid_clip = sum(warped_soft_occupancy)`
- `warped_support_in_destination_valid = sum(warped_soft_occupancy * destination_valid_mask)`
- `transport_out_of_frame_or_invalid = source_support_total - warped_support_in_destination_valid`
- `valid_transport_fraction = warped_support_in_destination_valid / source_support_total`

对每个 destination region：

- `intersection = sum(warped_soft_occupancy * destination_region_mask)`
- `conditional_valid_retention = intersection / warped_support_in_destination_valid`
- `source_total_retention = intersection / source_support_total`
- `destination_explained_fraction = intersection / destination_support_total`
- `soft_iou = intersection / (warped_support_in_destination_valid + destination_support_total - intersection)`

所有 denominator 为零的状态显式标为 unavailable；不删除 boundary/truncated cases。boundary/truncation 必须单独分层。

## 9. 完整 one-step compatibility matrix

每个合法 `t→t+1` pair、每个 source q95 region、每个 destination q95 region均生成 P0 和 ZERO 两行。不得使用 mutual nearest、Hungarian、unique edge、thread、path、forced assignment 或 identity。

独立保存：

1. q95 soft intersection；
2. q95 conditional-valid retention；
3. q95 source-total retention；
4. q95 destination explained fraction；
5. q95 soft IoU；
6. q97.5→q95 source-total core retention；
7. q97.5→q97.5 source-total core retention；
8. q90 weak-envelope source-total retention；
9. source/destination theta span；
10. source/destination range span；
11. theta/range midpoint change；
12. area ratio；
13. boundary/truncation；
14. P0/comparability state。

禁止 max/sum/mean fusion、learned weighting、posterior 或综合 consistency score。

## 10. Matched structural alternatives

Matched sets 在 reference reveal 前为每条 candidate edge冻结。对同一 source region 和 destination frame，排除该 edge 自己后，所有其它 destination q95 regions 按以下 deterministic structural distance 排序，取前 5；不足 5 时保留全部：

```text
distance =
  4 * boundary_state_mismatch
  + 4 * truncation_state_mismatch
  + abs(destination_region_degree_bin_difference)
  + abs(destination_component_shell_count_bin_difference)
  + abs(log(area_alt / area_edge))
  + abs(theta_change_alt - theta_change_edge) / 5 deg
  + abs(range_change_alt - range_change_edge) / 1 m
```

degree bins 固定为 `0,1,2,3+`；component-shell-count bins 固定为 `0,1,2,3+`。tie 依 `destination_region_id` 字典序。

该 set 与 P0/ZERO condition 无关；所有 alternatives 原样保存。reference reveal 后即使 alternative 也被支持，也不得删除，只能分层为 supported/unsupported/unresolved-shared。

本轮不设 primary time-shift null。

## 11. Pre-reference schema prohibition

runtime/pre-reference tables 不得包含：

- `physical_target_id`；
- manual box/center/range/azimuth；
- P01/P02/P03/P04 或 `target_id`；
- offline one-to-one assignment；
- stitched optical identity/provenance；
- reference-conditioned best edge；
- reference-supported/unsupported label。

## 12. Reference reveal 与评价

严格顺序：protocol/code freeze → inputs → nodes → P0 matrix → ZERO matrix → matched sets → runtime tables → manifest/ledger → independent validation → output hashes → `reference_loaded=false` stage closed → 才读取 reference。

Post-reference 使用冻结 `offline_reference_response_region_evaluation.csv` 的 q95 rows：

- 只有 `region_near_reference_0p30m=True` 且 `nearest_region_id` 有效时建立 target→region mapping；
- 同一 `target_id` 在 source 与 destination frame 均有 q95 mapping时，其 region pair标为 `REFERENCE_SUPPORTED_DYNAMIC_EXPLANATION`；
- 一个 edge 可支持多个 targets；shared 状态保留，不解释为 PERSON region identity。

评价：

- supported explanation 在同 source region全部 destination regions中的 rank/rank percentile；
- frozen matched alternatives pairwise win/tie/loss；
- alternatives reveal 后分层为 unsupported、also-supported/shared；
- P0 vs ZERO descriptor delta；
- q97.5/q90 对 q95 continuity 的附加解释。

本轮不报告 dynamic ambiguity reduction ratio，不声称 ambiguity solved 或 fewer-to-fewer established。

## 13. Outcome-state rules

这些只是 M0A 解释状态，不是 P1/P2 PASS：

- `M0A_MASK_WARP_OR_TRANSPORT_SEMANTICS_BLOCKED`：synthetic/validator/denominator/reference-order 任一关键完整性失败。
- `M0A_REGION_SUPPORT_TRANSPORT_WITH_P0_GAIN`：supported P0 对 reference-unsupported matched alternatives 的 win rate >0.5，supported rank percentile median >0.5，且 supported edges 中 P0 source-total retention 比 ZERO 高的比例 >0.60、median delta >0.01。
- `M0A_REGION_SUPPORT_TEMPORAL_PERSISTENCE_WITHOUT_CLEAR_P0_SPECIFIC_GAIN`：前两项 discrimination 条件成立，但 P0-specific 条件不成立。
- `M0A_REGION_SUPPORT_TEMPORAL_DISCRIMINATION_WEAK`：supported-vs-unsupported win rate ≤0.5 或 supported rank percentile median ≤0.5。

Outcome B（P0≈ZERO>alternatives）属于第二类，不是整个路线失败。

## 14. Deterministic case selection

Pre-reference 自动选择：

1. same edge 最大 P0−ZERO q95 source-total delta；
2. strong-continuation 集合内最小绝对 P0−ZERO delta；
3. same edge 最小 P0−ZERO delta；
4. 最大 P0 q95 source-total retention；
5. 最大 `q90 retention - q95 retention`；
6. q95 上四分位中最大 `q95 retention - q97.5→q97.5 retention`；
7. 每个 source 的第二高 P0 retention 最大者作为 split-like；
8. 每个 destination 的第二高 destination-explained fraction 最大者作为 merge-like；
9. boundary/truncated edges 中 P0 retention 最大者。

Post-reference 自动选择：

10. supported rank percentile 最大；
11. supported rank percentile 最小；
12. frozen matched alternative 超过 supported edge的 margin 最大；若没有 alternative 超过 supported edge，则保存 `NO_DECEPTIVE_ALTERNATIVE_FOUND_STRONGEST_AVAILABLE`，明确呈现最强但仍未超过的 frozen alternative，不伪造 deceptive case。

每类保存 pre-reference 图；post-reference 版本才允许以明显不同 overlay 添加 manual centers。病例选择 registry 必须记录 rule 和完整分母。

## 15. Freeze artifacts required before run

- 本协议最终 SHA256；
- `protocol_freeze.json`，含协议、实现、依赖、pair set、环境哈希；
- pre-run log entry；
- implementation source files；
- 9 张 deterministic pre-reference case PNG 必须在 independent validation 前生成，并与表、manifest、ledger、validation 一起进入 pre-reference output hash freeze；
- 所有 `PENDING_BEFORE_RUN` 替换为实际哈希；
- protocol state 改为 `FROZEN_BEFORE_RUN`。

在上述条件满足前，不运行 synthetic tests 或 M0A 数据。
