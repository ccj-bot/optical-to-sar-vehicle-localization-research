# Executive Summary

This document records the first external reconnaissance round for the optical-to-SAR vehicle localization research line. It is not a generic literature review. Each candidate is interpreted against the project spine: frozen SAR candidate-bank selection, hierarchical factor graph reconstruction, Phase4 fixed-prior revalidation, complete-vehicle active factors, diagnostic-only factors, and future partial-visibility or near-field routes.

The strongest Phase4-relevant direction found in this round is:

```text
OBB/geometry representation + track-level candidate path selection + MAP/Viterbi/min-cost-flow/factor graph.
```

The strongest external evidence is not a direct SAR frozen-candidate-bank selector. It is a set of adjacent method families:

- SAR and remote-sensing OBB localization papers, which provide geometry/state schema ideas;
- SAR vehicle and SAR object datasets, which show how SAR object records encode band, polarization, resolution, orientation, and target category;
- tracking-by-detection and network-flow literature, which gives MAP/min-cost-flow path-selection structure over fixed candidate detections;
- optical-SAR matching literature, which supports soft cross-modal priors but is mostly learned and therefore not directly usable as Phase4 scoring;
- amodal and automotive radar work, which is relevant to future partial-visibility and near-field routes only.

Most SAR detector repositories are useful as schema, dataset, and implementation-background references. They must not become Phase4 active scoring methods, detector-confidence factors, learned weights, or candidate-bank expansion mechanisms.

The main literature gap identified in this round is direct SAR frozen-candidate-bank selection. Public work appears much heavier on SAR detection, SAR OBB regression, optical-SAR registration, and generic MOT data association than on selecting among a pre-frozen SAR candidate bank under inference/evaluation separation. This is a search-round finding, not proof that no such literature exists.

# Search Query Plan

Grouped queries for the first reconnaissance round:

| Group | Query patterns |
|---|---|
| SAR vehicle localization/detection | `SAR vehicle detection oriented bounding box`, `SAR vehicle localization dataset`, `MSTAR vehicle detection SAR OBB`, `SIVED SAR vehicle detection`, `Mix MSTAR SAR vehicle detection` |
| optical-to-SAR transfer | `SAR optical image matching deep learning`, `optical SAR image registration`, `SAR optical corresponding patches`, `cross-modal SAR optical localization` |
| SAR candidate/proposal selection | `SAR proposal selection`, `SAR candidate selection object detection`, `rotated SAR benchmark proposals`, `SAR sparse proposal detection` |
| factor graph / CRF / Viterbi tracking | `multi-object tracking min-cost flow`, `MAP data association network flow`, `Viterbi tracking candidate selection`, `factor graph tracking localization`, `CRF tracking-by-detection` |
| SAR scattering/shadow/layover geometry | `SAR scattering vehicle geometry`, `SAR shadow layover object detection`, `scattering point guided SAR detection`, `SAR oriented target geometry` |
| partial visibility / amodal / occlusion | `amodal instance segmentation vehicle occlusion`, `KINS amodal instance segmentation`, `occlusion-aware instance segmentation`, `visible full object center offset` |
| near-field SAR / automotive radar geometry | `automotive radar oriented bounding box`, `range angle Doppler object detection`, `near field radar geometry`, `camera radar cross modal supervision` |
| GitHub repository search | `GitHub SARDet_100K`, `GitHub SIVED SAR vehicle`, `GitHub mmrotate`, `GitHub ByteTrack`, `GitHub TrackEval`, `GitHub OR-Tools min cost flow`, `GitHub RODNet`, `GitHub KINS amodal instance segmentation` |

# Paper Candidate Table

| paper_id | title | year | venue_or_source | stable_link_or_doi | task_type | data_type | method_summary | relevant_factor | phase_relevance | candidate_bank_impact | leakage_risk | implementation_available | why_it_matters |
|---|---|---:|---|---|---|---|---|---|---|---|---|---|---|
| P001 | SARDet-100K: Towards Open-Source Benchmark and ToolKit for Large-Scale SAR Object Detection | 2024 | NeurIPS 2024 / arXiv | https://arxiv.org/abs/2403.06534 | raw detection | SAR | Large SAR object detection benchmark and MSFA pretraining framework. | `sar_structure_factor`, `geometry_factor` | diagnostic_only | proposal_generation_required | medium | yes | Useful for SAR detection schema and dataset background, but detector training and confidence must not enter Phase4 scoring. |
| P002 | SIVED: A SAR Image Dataset for Vehicle Detection Based on Rotatable Bounding Box | 2023 | Remote Sensing | https://doi.org/10.3390/rs15112825 | raw detection | SAR vehicle | SAR vehicle dataset with rotatable bounding boxes and metadata including band, resolution, polarization, and target azimuth. | `geometry_factor`, controlled non-visible `source_factor` | Phase4_fixed_prior | none | low | yes | Strong vehicle-specific OBB/schema reference for candidate state fields; Phase4 use is schema/protocol only and does not authorize candidate-bank expansion. |
| P003 | Mix MSTAR: A Synthetic Benchmark Dataset for Multi-Class Rotation Vehicle Detection in Large-Scale SAR Images | 2023 | Remote Sensing | https://doi.org/10.3390/rs15184558 | raw detection | SAR vehicle | Synthetic large-scene SAR vehicle benchmark with OBB labels and rotated-detector baselines. | `geometry_factor`, `sar_structure_factor` | Phase4_fixed_prior | proposal_generation_required | medium | unknown | Phase4 use is schema/protocol only; detector training, proposal generation, and detector confidence are not Phase4-active evidence. Official implementation was not verified in this round. |
| P004 | DRBox-v2: An Improved Detector With Rotatable Boxes for Target Detection in SAR Images | 2019 | IEEE TGRS | https://doi.org/10.1109/TGRS.2019.2920534 | raw detection | SAR | Rotatable-box SAR target detector improving orientation-aware localization. | `geometry_factor`, `sar_structure_factor` | Phase4_fixed_prior | proposal_generation_required | medium | unknown | Phase4 use is schema/protocol only; detector training, proposal generation, and detector confidence are not Phase4-active evidence. Official implementation was not verified in this round. |
| P005 | Learning Polar Encodings for Arbitrary-Oriented Ship Detection in SAR Images | 2021 | IEEE JSTARS / arXiv | https://doi.org/10.1109/JSTARS.2021.3068530 | raw detection | SAR ship | Represents oriented boxes by polar boundary vectors to avoid angle-regression discontinuity. | `geometry_factor` | Phase4_fixed_prior | proposal_generation_required | medium | unknown | Phase4 use is schema/protocol only; detector training, proposal generation, and detector confidence are not Phase4-active evidence. Official implementation was not verified in this round. |
| P006 | DOTA: A Large-scale Dataset for Object Detection in Aerial Images | 2017 | arXiv | https://arxiv.org/abs/1711.10398 | raw detection | optical aerial | Remote-sensing OBB dataset using arbitrary quadrilateral annotations. | `geometry_factor` | background_only | proposal_generation_required | low | yes | Background OBB annotation reference only; optical-only evidence is not SAR physical evidence and is not Phase4-active scoring evidence. |
| P007 | Learning RoI Transformer for Oriented Object Detection in Aerial Images | 2019 | CVPR | https://doi.org/10.1109/CVPR.2019.00296 | raw detection | optical aerial | Learns rotated RoIs to improve oriented object localization. | `geometry_factor` | background_only | proposal_generation_required | medium | yes | Background OBB/RRoI schema and ablation reference only; learned detector internals, proposal generation, and detector confidence are not Phase4-active evidence. |
| P008 | Oriented R-CNN for Object Detection | 2021 | ICCV | https://arxiv.org/abs/2108.05699 | raw detection | aerial / general OBB | Two-stage oriented object detector with oriented proposal and detection heads. | `geometry_factor` | background_only | proposal_generation_required | medium | yes | Background OBB implementation reference only; learned detector internals, proposal generation, and detector confidence are not Phase4-active evidence. |
| P009 | Identifying Corresponding Patches in SAR and Optical Images With a Pseudo-Siamese CNN | 2018 | IEEE GRSL | https://doi.org/10.1109/LGRS.2018.2799232 | cross-modal matching | optical-to-SAR | Learns whether SAR and optical patches correspond. | `optical_temporal_factor` | future_learning_calibration | none | high | unknown | Supports cross-modal prior interpretation, but learned correspondence and alignment labels are not Phase4 fixed-prior scoring. Official implementation availability was not verified in this round. |
| P010 | A Deep Learning Framework for Matching of SAR and Optical Imagery | 2020 | ISPRS Journal of Photogrammetry and Remote Sensing | https://doi.org/10.1016/j.isprsjprs.2020.09.012 | cross-modal matching | optical-to-SAR | Sparse SAR-optical matching framework with learned region selection, correspondence heatmaps, and outlier rejection. | `optical_temporal_factor`, `direction_factor` | future_learning_calibration | none | high | to_verify | Useful for soft prior and alignment-failure reasoning; learned matching cannot enter Phase4 as active weights. Official implementation availability was not verified in this round. |
| P011 | Global Data Association for Multi-Object Tracking Using Network Flows | 2008 | CVPR | https://doi.org/10.1109/CVPR.2008.4587584 | tracking / localization | video detections | Maps MAP data association into a min-cost-flow network. | `transition_factor` | Phase4_fixed_prior | selection_only | low | unknown | Strong algorithm-structure reference for selecting paths through fixed candidate detections. Official implementation availability was not verified in this round. |
| P012 | Globally-Optimal Greedy Algorithms for Tracking a Variable Number of Objects | 2011 | CVPR | https://doi.org/10.1109/CVPR.2011.5995604 | tracking / localization | video detections | Instantiates tracks using shortest paths on a flow network. | `transition_factor` | Phase4_fixed_prior | selection_only | low | unknown | Supports Viterbi/min-cost-flow style candidate path selection without changing the candidate bank. Official implementation availability was not verified in this round. |
| P013 | HOTA: A Higher Order Metric for Evaluating Multi-Object Tracking | 2020 | IJCV | https://doi.org/10.1007/s11263-020-01375-2 | evaluation | tracking outputs | Evaluation metric decomposing detection, localization, and association errors. | `transition_factor` | background_only | none | medium | yes | Useful for post-inference evaluation protocol and grouped analysis; must not leak into inference. |
| P014 | Amodal Instance Segmentation With KINS Dataset | 2019 | CVPR | https://doi.org/10.1109/CVPR.2019.00313 | partial visibility / amodal | optical road scenes | Annotates and predicts invisible object parts under occlusion. | `visibility_factor`, `missing_extent_factor`, `visible_full_center_offset_factor` | Phase7_partial_visibility | candidate_bank_change_required | high | yes | Future route for visible/full-center separation; not active complete-vehicle Phase4 evidence. |
| P015 | CARRADA Dataset: Camera and Automotive Radar with Range-Angle-Doppler Annotations | 2020 | arXiv | https://arxiv.org/abs/2005.01456 | near-field radar dataset | automotive radar / camera | Synchronized camera and radar dataset with range-angle-Doppler annotations. | near-field future route | Phase7B_near_field | unclear | high | yes | Future geometry-regime reference for radar reliability and range-angle state; not SAR remote-sensing Phase4 scoring. |

# GitHub Repository Candidate Table

| repo_id | repo_url | project_name | owner | license | latest_checked_commit_or_release | task_type | method_summary | usable_component | relevant_factor | phase_relevance | clone_location_recommendation | reuse_policy | risks | why_it_matters |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R001 | https://github.com/open-mmlab/mmrotate | MMRotate | open-mmlab | Apache-2.0 | v0.3.4, 2023-02-01 | rotated object detection | PyTorch toolbox for rotated object detection and OBB methods. | schema / implementation reference | `geometry_factor` | Phase4_fixed_prior | `D:\profile\research\external_repos\mmrotate\` | read_only_reference | Learned detector framework; detector confidence and training must not enter Phase4. | Best repo reference for OBB conventions, angle representation, and rotated-detector schemas. |
| R002 | https://github.com/zcablii/SARDet_100K | SARDet_100K | zcablii | Attribution-NonCommercial 4.0 International | to_verify | SAR object detection | Official dataset/toolkit implementation for SARDet-100K and MSFA. | dataset schema / background | `sar_structure_factor`, `geometry_factor` | diagnostic_only | `D:\profile\research\external_repos\SARDet_100K\` | read_only_reference | Noncommercial license; latest commit was not verified in this round; learned detector and dataset aggregation risks; no code reuse without review. | Useful to understand SAR dataset organization and detector-heavy bias. |
| R003 | https://github.com/CAESAR-Radi/SIVED | SIVED | CAESAR-Radi | to_verify | to_verify | SAR vehicle detection dataset | Dataset repository for SIVED with rotatable bounding box annotation references. | dataset schema | `geometry_factor`, controlled non-visible `source_factor` | Phase4_fixed_prior | `D:\profile\research\external_repos\SIVED\` | read_only_reference | Official license and latest commit were not verified in this round; dataset must not alter the candidate bank. | Vehicle-specific SAR OBB dataset reference closest to the project vehicle setting. |
| R004 | https://github.com/FoundationVision/ByteTrack | ByteTrack | FoundationVision | MIT | to_verify | tracking-by-detection | Associates high- and low-score detections for MOT. | algorithm structure / comparison reference | `transition_factor` | Phase4_fixed_prior | `D:\profile\research\external_repos\ByteTrack\` | method_summary_only | Latest commit was not verified in this round; uses detector confidence and learned detections; confidence must not become a Phase4 factor. | Useful contrast for candidate association logic, but Phase4 should prefer fixed candidate costs over detector scores. |
| R005 | https://github.com/JonathonLuiten/TrackEval | TrackEval | JonathonLuiten | MIT | to_verify | tracking evaluation | Evaluation toolkit for HOTA and other MOT metrics. | post-inference evaluation protocol | `transition_factor` | background_only | `D:\profile\research\external_repos\TrackEval\` | read_only_reference | Latest commit was not verified in this round; evaluation labels and metrics must remain post-inference only. | Useful for grouped path/association failure analysis after inference outputs exist. |
| R006 | https://github.com/google/or-tools | OR-Tools | google | Apache-2.0 | v9.15, 2026-01-12 | optimization | Combinatorial optimization library with min-cost-flow and routing tooling. | implementation reference | `transition_factor` | Phase4_fixed_prior | `D:\profile\research\external_repos\or-tools\` | possible_reimplementation_after_review | General optimizer dependency and licensing/provenance review required before any code use. | Candidate path selection can be expressed as a min-cost-flow/MAP problem; this is a reference only. |
| R007 | https://github.com/yizhou-wang/RODNet | RODNet | yizhou-wang | MIT | rodnet v1.3, 2022-03-15 | automotive radar detection | Radar object detection network using range-azimuth data and cross-modal supervision. | future route reference | near-field future route | Phase7B_near_field | `D:\profile\research\external_repos\RODNet\` | read_only_reference | Automotive radar is not SAR remote sensing; learned cross-modal supervision is future-only. | Useful for future near-field geometry-regime and range-angle reliability concepts. |
| R008 | https://github.com/qqlu/Amodal-Instance-Segmentation-through-KINS-Dataset | Amodal-Instance-Segmentation-through-KINS-Dataset | qqlu | to_verify | to_verify | amodal segmentation | Reference code/data for KINS amodal instance segmentation. | future route reference | `visibility_factor`, `missing_extent_factor`, `visible_full_center_offset_factor` | Phase7_partial_visibility | `D:\profile\research\external_repos\KINS_amodal\` | read_only_reference | Official license and latest commit were not verified in this round; active partial visibility is blocked in Phase4. | Useful only after complete-vehicle branch is stable and Phase7 schema work begins. |

# Method-To-Factor Mapping

| Project factor or route | Supporting papers/repos | Support type | Can affect Phase4? | Risks |
|---|---|---|---|---|
| `geometry_factor` | P002, P003, P004, P005, P006, P007, P008; R001, R003 | schema, concept, ablation, implementation reference | Yes for P002-P005 and R001/R003 as fixed-prior OBB/fan-polar schema; P006-P008 are background OBB references only. | SAR shell evidence can be double-counted with `sar_structure_factor`; learned detector regression, proposal generation, and detector confidence must not become factor scores. |
| `direction_factor` | P005, P007, P008, P010 | concept, schema | Limited. Direction representation and angle consistency can inform fixed transforms if separated from source trust. | Direction assumptions can be counted again through candidate source or detector heading. |
| controlled non-visible `source_factor` | P001, P002, P003; R002, R003 | schema, source/provenance concept | Yes, only as non-visible source-family provenance after ownership is declared. | Dataset/proposal source and direction/geometry cues can be conflated; visible source remains veto/uncertainty-only. |
| `optical_temporal_factor` | P009, P010 | concept, future learning reference | Limited to soft-prior interpretation and field/schema ideas. | Learned cross-modal matching, correspondence labels, or alignment evaluation must not enter Phase4 scoring. |
| `transition_factor` | P011, P012, P013; R004, R005, R006 | algorithm structure, ablation, post-inference evaluation | Yes, strongest Phase4 structure for MAP/Viterbi/min-cost-flow selection over fixed candidates. | Detector confidence, learned association embeddings, and evaluation metrics must not be used as inference factors. |
| `sar_structure_factor` diagnostic only | P001, P003, P004, P005; R002 | concept, schema, background | No active Phase4 scoring. | Overlaps with geometry and uncertainty; SAR support versus ambiguity is unresolved. |
| `uncertainty_factor` diagnostic only | P001, P013, P015; R005, R007 | concept, evaluation/future route | No active Phase4 scoring. | Confidence calibration and uncertainty routing can copy detector behavior or B patch protection. |
| `visibility/missing_extent/visible_full_center_offset` future route | P014; R008 | future route, schema | No. Phase7 only. | Visible evidence must not generate full center; amodal completion would change the active branch. |
| near-field future route | P015; R007 | future route, geometry-regime concept | No. Phase7B only. | Automotive radar geometry is not SAR remote-sensing geometry; cannot modify candidate bank or replace the selector. |

# Phase4-Usable Evidence

Only the following evidence may affect Phase4 fixed-prior design:

- OBB and oriented-geometry representation from P002-P005 and R001/R003, as field/schema guidance for complete-vehicle candidate state; P006-P008 remain background OBB references only.
- MAP/min-cost-flow/path-selection structure from P011, P012, and R006, as a way to select paths through fixed candidates.
- Tracking evaluation organization from P013 and R005, only after inference outputs already exist.
- Optical-SAR matching papers P009 and P010, only as soft-prior interpretation and failure-mode background.
- SAR detection benchmark records P001-P005, only as SAR schema/background and diagnostic grouping references.

Allowed influence:

- fixed-prior factor interpretation;
- field/schema design;
- ablation organization;
- MAP/Viterbi/min-cost-flow path-selection structure;
- post-inference evaluation protocol.

Disallowed in Phase4:

- learned weights;
- candidate-bank expansion;
- detector confidence as factor score;
- B patch action copying;
- eval-only fields in inference;
- active SAR structure, uncertainty, final arbitration, or visibility scoring.

# Future-Only Evidence

The following evidence is useful but not active in Phase4:

- Learned domain adaptation and cross-modal matching from P009 and P010. These may inform future learned priors but cannot supply Phase4 weights.
- Learned detectors and candidate generation from P001-P008. These may explain SAR OBB conventions but must not expand or replace the frozen candidate bank.
- SAR structure and uncertainty modeling from P001, P003, P004, and P005. These remain diagnostic-only until SAR support, ambiguity, and B patch dependency are separated.
- Amodal and partial-visibility evidence from P014 and R008. This belongs to Phase7 partial-visibility schema work.
- Near-field and automotive radar geometry from P015 and R007. This belongs to the Phase7B near-field geometry-regime route.
- General tracking-by-detection systems such as R004. These are useful as association references but cannot import detector confidence, appearance embeddings, or learned association weights into Phase4.

# Recommended Reading Order

Papers:

1. P002, SIVED: read first for SAR vehicle OBB dataset structure, annotation schema, and metadata fields relevant to complete-vehicle state.
2. P003, Mix MSTAR: read for SAR vehicle OBB benchmark design, synthetic-data limitations, and rotated-detector failure context.
3. P011, Global Data Association for Multi-Object Tracking Using Network Flows: inspect MAP and min-cost-flow formulation for fixed candidate path selection.
4. P012, Globally-Optimal Greedy Algorithms for Tracking a Variable Number of Objects: inspect shortest-path/flow-network structure for scalable path construction.
5. P007, RoI Transformer: inspect rotated RoI/OBB schema and ablation organization, not detector training.
6. P010, A Deep Learning Framework for Matching of SAR and Optical Imagery: inspect cross-modal matching failure modes and soft-prior interpretation.
7. P013, HOTA: inspect evaluation decomposition only for post-inference grouped failure analysis.
8. P014, KINS amodal instance segmentation: read later for Phase7 visible/full-center separation concepts.

Repositories:

1. R001, MMRotate: inspect angle representations, OBB schemas, and evaluation conventions as read-only reference.
2. R006, OR-Tools: inspect min-cost-flow API and formulation examples only after a Phase4 scaffold design is approved.
3. R005, TrackEval: inspect post-inference tracking metric organization and grouped evaluation outputs.

# Gaps And Risks

Observed gaps and risks from this reconnaissance:

- SAR frozen candidate-bank selection literature gap: this round found SAR detection, OBB regression, tracking-by-detection, and optical-SAR matching, but no verified direct method for selecting among a pre-frozen SAR candidate bank under this project's inference/evaluation separation.
- Detector-heavy bias in SAR repositories: most repos train detectors or generate proposals; they are background/schema references, not Phase4 scoring methods.
- Transfer-method bias toward learned domain adaptation: optical-SAR matching work commonly uses learned correspondence, pseudo-labels, or registration supervision; this is future learning/calibration material.
- Factor graph sources mostly from generic MOT: MAP/min-cost-flow structure is strong, but the physical SAR factors must be supplied by this project.
- Near-field sources mostly automotive radar rather than SAR remote sensing: useful for range-angle reliability ideas, but not a direct SAR geometry substitute.
- Double-counting risk: OBB geometry, SAR structure, source provenance, and direction can encode overlapping evidence.
- Leakage risk: tracking metrics, detector labels, GT boxes, correspondence labels, occlusion labels, and amodal masks must stay post-inference or future-only.
- License/provenance risk: repositories marked `to_verify` or noncommercial must not be copied or reused without explicit review.
- B patch risk: no external method may be used to justify copying B patch action behavior into active scoring.

# Next Action

Recommended next actions:

- Read P002, P003, P011, P012, P007, P010, and P013 first.
- Clone, only if separately authorized, R001, R006, and R005 outside the main repo under `D:\profile\research\external_repos\` for read-only inspection.
- Keep R002, R003, R007, and R008 as read-only candidates until license/data-use conditions and provenance are checked.
- Create a factor-specific literature map after human review, starting with `geometry_factor` and `transition_factor`.
- A Phase4 execution scaffold design can start only after this document is reviewed and the existing Phase4 GO/NO-GO gates remain satisfied. Actual Phase4 execution, training, calibration, candidate-bank changes, GM17 replacement, and partial-visibility or near-field activation remain blocked unless separately authorized.

Items still marked for verification:

- implementation availability for P003, P004, P005, P010, P011, and P012;
- license and latest checked commit/release for R003 and R008;
- latest checked commit for R002, R004, and R005;
- whether any paper in this set has an official implementation beyond the repository candidates listed here.
