from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import shutil
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


SCRIPT = Path(__file__).resolve()
TASK = SCRIPT.parent
WORKSPACE = TASK.parents[1]
OUTPUT = WORKSPACE / "output" / "person_u0_r0_sar_response_representation_stress_test_20260904"
PRE = OUTPUT / "pre_reference"
POST = OUTPUT / "post_reference_diagnostic_only"
FIG = PRE / "figures"
MASKS = PRE / "representation_fields"
PACK = WORKSPACE / "review_packs" / "PERSON_U0_R0_SAR_RESPONSE_REPRESENTATION_STRESS_TEST_20260904"
PACK_ZIP = PACK.with_suffix(".zip")

T0_ROOT = WORKSPACE / "output" / "person_t0_temporal_candidate_ambiguity_structure_20260903"
T0_PRE = T0_ROOT / "pre_reference"
R2_PRE = WORKSPACE / "output" / "person_terg_r2_runtime_grounding_and_full_stream_hypothesis_management_20260830" / "pre_reference"
B0_PRE = WORKSPACE / "output" / "person_b0_end_to_end_capability_and_bottleneck_study_20260830" / "pre_reference"
B0_POST = WORKSPACE / "output" / "person_b0_end_to_end_capability_and_bottleneck_study_20260830" / "post_reference_oracle_diagnostic_only"
RANGE_PRE = WORKSPACE / "output" / "person_range_temporal_decision_study_20260830" / "pre_reference"

FRAME_REGISTRY = R2_PRE / "full_stream_frame_registry_pre_reference.parquet"
R2_Q95_REGIONS = R2_PRE / "full_stream_q95_response_regions_pre_reference.parquet"
R2_Q95_MASKS = R2_PRE / "full_stream_q95_masks"
SHELLS = R2_PRE / "full_stream_optical_shells_pre_reference.parquet"
P0_MODELS = B0_PRE / "full_stream_p0_models.jsonl"
STRICT_MEMBERSHIP = RANGE_PRE / "global_mutual_dominant_p0_family_membership.parquet"
REFERENCE = B0_POST / "r01_r02_r03_manual_range_reference_oracle_only.parquet"
FRAGMENT_TARGET_MAP = B0_POST / "raw_fragment_to_offline_target_mapping_oracle_only.csv"

STUDY_TASK = WORKSPACE / "tasks" / "person_physics_guided_image_domain_study_20260824"
P1E_SCRIPT = STUDY_TASK / "run_p1e_single_frame_position_specificity.py"
CANDIDATE_SCRIPT = STUDY_TASK / "run_p1e_candidate_recall_audit.py"
REGION_SCRIPT = STUDY_TASK / "run_p1e_runtime_track_response_region_minimal.py"

LEVELS = (0.90, 0.95, 0.975)
TAGS = {0.90: "Q090", 0.95: "Q095", 0.975: "Q0975"}
SELECTED_WINDOW_IDS = {
    "W1_R01_SINGLE_AZIMUTH_SWEEP_F097_F112",
    "W3_R02_TWO_TARGET_ENTRY_F469_F480",
    "W4_R02_MULTI_TARGET_COMPETITION_F487_F494",
    "W5_R01_HIGH_BACKGROUND_TOPOLOGY_F048_F055",
}
REVIEW_CLASSES = {
    "ALGORITHM_INDUCED_SPLIT",
    "ALGORITHM_INDUCED_MERGE",
    "GENUINE_UNRESOLVED_STRUCTURE",
    "UNCERTAIN",
}
NOT_SELECTED = "NOT_SELECTED_FOR_DIRECT_REVIEW"
W15_REVIEW_CLASSES = {
    "VISIBLE_CROSS_LEVEL_LONG_TERM_STRUCTURE",
    "LOWER_THRESHOLD_OVERMERGE_PRESSURE",
    "UNCERTAIN",
}

KEY_CASE_SELECTION: dict[str, str] = {
    "U0CASE_D7C710E130CD7A3CA037": "W3 F479->F480 clean Q95 split under one Q90 parent",
    "U0CASE_6E10D1D1881E0A528FAE": "W3 F471->F472 first half of broad-ridge split/merge cycle",
    "U0CASE_6048382E9235CB1545A2": "W3 F472->F473 second half of broad-ridge split/merge cycle",
    "U0CASE_242E18D87BA861477E68": "W3 F475->F476 persistent two-core structure inside one Q95/Q90 region",
    "U0CASE_DDBC0423FA50F610B363": "W4 F487->F488 clean threshold-dependent Q95 split",
    "U0CASE_ECF5E7ACB76A2B099E3D": "W4 F489->F490 onset of thin-bridge Q90 over-merge",
    "U0CASE_E42B7C88968837DDE15A": "W4 F490->F491 release of thin-bridge Q90 over-merge",
    "U0CASE_4788D129AFE42D7EC7B0": "W4 F487->F488 topology-label counterexample requiring all branches",
}

INVARIANT_ATLAS_GROUPS: tuple[dict[str, Any], ...] = (
    {
        "atlas_id": "W1_ALL_ENDPOINT_INVARIANTS",
        "window_id": "W1_R01_SINGLE_AZIMUTH_SWEEP_F097_F112",
        "family_ids": (
            "U0F_01EAA250CAC32BDBEAD5",
            "U0F_FA29516582FDE8E3412F",
            "U0F_D969144A1298E2872B02",
            "U0F_A228F8C949AA448A2C59",
            "U0F_3268E49D811B3970B490",
        ),
        "purpose": "all five W1 endpoint-spanning cross-level structures in one fixed coordinate system",
    },
    {
        "atlas_id": "W5_SHARED_COMPACT_RADIAL_LADDER",
        "window_id": "W5_R01_HIGH_BACKGROUND_TOPOLOGY_F048_F055",
        "family_ids": (
            "U0F_0D73CE775203A5D515FA",
            "U0F_73C8020E9D86AED6C806",
            "U0F_DF91BAA50A817596ED2D",
            "U0F_C2DD1B6179E940AEA395",
            "U0F_1EB425AD86DD81E6ECB3",
            "U0F_3D07A6FABCA1F06C13FE",
        ),
        "purpose": "W5 PERSON001/002 shell-intersecting ladder plus the broad persistent structure",
    },
    {
        "atlas_id": "W5_PERSON003_RADIAL_STRUCTURES",
        "window_id": "W5_R01_HIGH_BACKGROUND_TOPOLOGY_F048_F055",
        "family_ids": (
            "U0F_CA737C6FCB4B1ED8AD46",
            "U0F_7C09657CD2D3BC745366",
            "U0F_EFECD5B32C86EA3B7B19",
            "U0F_B32A9DA633F9073ADEF7",
        ),
        "purpose": "W5 PERSON003 near/mid/far structures plus the endpoint-invariant over-merge counterexample",
    },
)

# Filled only after direct inspection of the generated GT-blind targeted
# figures. Keys are stable case_id values from
# semantic_reverse_audit_candidates.csv. Automatic candidates not selected by
# select_case_rows() are explicitly outside the direct-review denominator.
MANUAL_CASE_REVIEWS: dict[str, dict[str, str]] = {
    "U0CASE_D7C710E130CD7A3CA037": {
        "manual_visual_class": "ALGORITHM_INDUCED_SPLIT",
        "what_image_shows": "From F479 to F480, one spatially continuous low-level structure changes from one to two Q95 children while two Q97.5 peak cores remain visible.",
        "what_is_invariant": "The lower-level support and the two high-level cores persist across the event; the Q95 connected-component count is the unstable part.",
        "what_remains_uncertain": "The imagery does not establish that the two persistent cores are one physical response object rather than two unresolved substructures.",
    },
    "U0CASE_6E10D1D1881E0A528FAE": {
        "manual_visual_class": "GENUINE_UNRESOLVED_STRUCTURE",
        "what_image_shows": "F471-F472 contains a broad multi-lobed ridge whose exact Q90 parent changes from seven to four Q95 children; the image does not provide a clean object boundary.",
        "what_is_invariant": "A broad structured response remains present across Q90, Q95, Q97.5, and adjacent frames despite changing component partition.",
        "what_remains_uncertain": "Neither a single physical response nor several independent responses can be justified from this display-domain sequence.",
    },
    "U0CASE_6048382E9235CB1545A2": {
        "manual_visual_class": "GENUINE_UNRESOLVED_STRUCTURE",
        "what_image_shows": "F472-F473 is the reverse half of the same broad-ridge cycle: the exact Q90 parent changes from four to seven Q95 children while its lobed support remains visually continuous but internally complex.",
        "what_is_invariant": "The wide multi-level ridge persists through the split/merge cycle; only its sampled threshold partition and branch graph change.",
        "what_remains_uncertain": "The sequence cannot decide whether the lobes should be grouped into one bounded response hypothesis or retained as a set of separate primitives.",
    },
    "U0CASE_242E18D87BA861477E68": {
        "manual_visual_class": "GENUINE_UNRESOLVED_STRUCTURE",
        "what_image_shows": "A single persistent Q90/Q95 region contains two stable Q97.5 cores connected by a saddle in F475-F476.",
        "what_is_invariant": "Both high-level cores and their shared lower-level support remain visible across the neighboring frames.",
        "what_remains_uncertain": "One connected component is not enough to decide whether this is one response with two cores or two unresolved responses.",
    },
    "U0CASE_DDBC0423FA50F610B363": {
        "manual_visual_class": "ALGORITHM_INDUCED_SPLIT",
        "what_image_shows": "From F487 to F488, a compact continuous structure changes from one to two Q95 children while the Q90 parent and single Q97.5 core remain continuous.",
        "what_is_invariant": "The compact lower-level support and its dominant peak core persist; the Q95 connected-component identity fragments at the threshold.",
        "what_remains_uncertain": "This supports repairing the representation label only; it does not identify the structure as PERSON-specific.",
    },
    "U0CASE_ECF5E7ACB76A2B099E3D": {
        "manual_visual_class": "ALGORITHM_INDUCED_MERGE",
        "what_image_shows": "At F490, a thin low-intensity bridge joins a visibly separated upper arc and lower ridge inside one Q90 parent.",
        "what_is_invariant": "The upper and lower structures remain distinguishable at Q95/Q97.5 and in adjacent frames even when Q90 connects them.",
        "what_remains_uncertain": "The appropriate boundary within either structure is still unresolved; only the unrestricted Q90 merge is rejected.",
    },
    "U0CASE_E42B7C88968837DDE15A": {
        "manual_visual_class": "ALGORITHM_INDUCED_MERGE",
        "what_image_shows": "The split-and-merge label is driven by optional branches released from the F490 over-merged Q90 parent rather than by a visually credible physical split event.",
        "what_is_invariant": "The separated arc and ridge remain distinct at higher thresholds; the temporary lower-threshold bridge is the representation-dependent feature.",
        "what_remains_uncertain": "Optional branch topology is not lower-mutual family authority, so the exact temporal correspondence of every released branch remains unresolved.",
    },
    "U0CASE_4788D129AFE42D7EC7B0": {
        "manual_visual_class": "UNCERTAIN",
        "what_image_shows": "The highlighted branch itself remains a compact two-child/two-core structure; the SPLIT_LIKE label depends on another optional outgoing branch outside that selected correspondence.",
        "what_is_invariant": "The highlighted local structure and its two higher-level cores persist across F487-F488.",
        "what_remains_uncertain": "The additional optional branch may be background or a related fragment; the image and non-mutual topology do not decide between them.",
    },
}

MANUAL_W15_REVIEWS: dict[str, dict[str, str]] = {
    "U0W15INV_04228D38A1AFB61C3371": {
        "manual_visual_class": "VISIBLE_CROSS_LEVEL_LONG_TERM_STRUCTURE",
        "what_image_shows": "W1 contains a broad response near 11.1 m that is visible throughout F097-F112, with internal branching that changes across frames and thresholds.",
        "what_is_invariant": "A spatially coherent image-domain ridge persists at separated range/azimuth support across Q90, Q95, and Q97.5.",
        "what_remains_uncertain": "Persistence does not distinguish a PERSON response from stable scene background, and the changing branches do not define one physical object.",
    },
    "U0W15INV_FB6CF934D553A1133A39": {
        "manual_visual_class": "VISIBLE_CROSS_LEVEL_LONG_TERM_STRUCTURE",
        "what_image_shows": "W1 contains a near-apex response near 2.5 m that remains visible at the sampled endpoints and intermediate frames.",
        "what_is_invariant": "The near-range structure survives the three sampled thresholds and temporal-family construction.",
        "what_remains_uncertain": "Its proximity to the apex and fan boundary makes extent and physical independence especially representation-sensitive.",
    },
    "U0W15OVER_FAF55E86F49103CFFACE": {
        "manual_visual_class": "LOWER_THRESHOLD_OVERMERGE_PRESSURE",
        "what_image_shows": "At W1 F108, one Q90 parent spans several visibly separated structures across a wide range/azimuth extent and contains six Q95 children and eleven Q97.5 cores.",
        "what_is_invariant": "Several distinct higher-level structures remain visible inside the parent rather than collapsing into a single compact response.",
        "what_remains_uncertain": "Their exact physical grouping is unresolved, but treating the whole Q90 parent as one bundle is not image-supported.",
    },
    "U0W15INV_9C68CDE1DB2D9CD2B813": {
        "manual_visual_class": "VISIBLE_CROSS_LEVEL_LONG_TERM_STRUCTURE",
        "what_image_shows": "W5 contains a broad response near 18 m that persists through F048-F055 and remains visible across sampled thresholds.",
        "what_is_invariant": "A long-lived broad image-domain ridge survives threshold and temporal-family changes in the fixed-coordinate atlas.",
        "what_remains_uncertain": "The structure is background-compatible and cannot be counted as PERSON-specific or as one exact physical response hypothesis.",
    },
    "U0W15INV_B3ABF153B88E74060ACD": {
        "manual_visual_class": "VISIBLE_CROSS_LEVEL_LONG_TERM_STRUCTURE",
        "what_image_shows": "W5 contains a compact near-range response near 4.9 m that remains spatially separated from the mid/far structures in the common-coordinate atlas.",
        "what_is_invariant": "The compact structure persists across Q90, Q95, Q97.5 and the window endpoints.",
        "what_remains_uncertain": "The atlas establishes a stable SAR image-domain alternative, not correspondence to PERSON003 or independent target evidence.",
    },
    "U0W15OVER_5B7016A7009D63B42E26": {
        "manual_visual_class": "LOWER_THRESHOLD_OVERMERGE_PRESSURE",
        "what_image_shows": "At W5 F53, one Q90 parent absorbs a broad ridge with five Q95 children and six Q97.5 cores, including support that is visibly wider than a compact response hypothesis.",
        "what_is_invariant": "Multiple higher-level substructures and the broad background-compatible ridge persist even though the Q90 family spans the endpoints.",
        "what_remains_uncertain": "Endpoint invariance alone cannot say which substructures belong together or which, if any, supports PERSON003.",
    },
}


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def stable_id(prefix: str, *parts: Any) -> str:
    payload = "||".join(str(part) for part in parts)
    return f"{prefix}_{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:20].upper()}"


def write_table(frame: pd.DataFrame, stem: Path, parquet: bool = True) -> None:
    stem.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(stem.with_suffix(".csv"), index=False)
    if parquet:
        frame.to_parquet(stem.with_suffix(".parquet"), index=False)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def parse_intervals(value: str) -> list[tuple[float, float]]:
    return [(float(low), float(high)) for low, high in json.loads(value)]


def frame_record(row: pd.Series) -> dict[str, Any]:
    return {
        "run_id": str(row.run_id),
        "sar_frame_uid": str(row.sar_frame_uid),
        "sar_frame_index": int(row.sar_frame_index),
        "sar_timestamp_ms": int(row.sar_timestamp_ms),
        "sar_image_path": str(row.sar_image_path),
        "sar_width_px": int(row.sar_width_px),
        "sar_height_px": int(row.sar_height_px),
        "theta_low_deg": float(row.theta_low_deg),
        "theta_high_deg": float(row.theta_high_deg),
        "nominal_optical_frame_index": int(row.nominal_optical_frame_index),
        "nominal_optical_timestamp_ms": int(row.nominal_optical_timestamp_ms),
        "sync_status": str(row.sync_status),
        "geometry": {
            "center_x_px": float(row.geometry_center_x_px),
            "center_y_px": float(row.geometry_center_y_px),
            "radius_px": float(row.geometry_radius_px),
            "outer_range_m": float(row.geometry_outer_range_m),
        },
    }


def load_contract() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    windows = pd.read_csv(T0_PRE / "window_registry.csv")
    windows = windows[windows["window_id"].isin(SELECTED_WINDOW_IDS)].copy()
    tracks = pd.read_csv(T0_PRE / "window_track_registry.csv")
    tracks = tracks[tracks["window_id"].isin(SELECTED_WINDOW_IDS)].copy()
    if set(windows["window_id"]) != SELECTED_WINDOW_IDS:
        raise RuntimeError("selected T0 windows are incomplete")
    if windows["run_id"].astype(str).str.upper().str.contains("R04").any():
        raise RuntimeError("forbidden confirmation run entered window contract")
    selected = {
        (str(row.run_id), frame)
        for row in windows.itertuples(index=False)
        for frame in range(int(row.start_frame), int(row.end_frame) + 1)
    }
    registry = pd.read_parquet(FRAME_REGISTRY)
    registry = registry[
        registry.apply(lambda row: (str(row.run_id), int(row.sar_frame_index)) in selected, axis=1)
    ].copy()
    if len(registry) != 44:
        raise RuntimeError(f"expected 44 unique selected frames, got {len(registry)}")
    all_shells = pd.read_parquet(SHELLS)
    all_shells = all_shells[all_shells["mode"].eq("CAUSAL_REPLAY")].copy()
    shell_parts = []
    for window in windows.itertuples(index=False):
        selected_tracks = set(tracks.loc[tracks["window_id"].eq(window.window_id), "track_id"].astype(str))
        part = all_shells[
            all_shells["run_id"].eq(window.run_id)
            & all_shells["track_id"].astype(str).isin(selected_tracks)
            & all_shells["frame_index"].between(int(window.start_frame), int(window.end_frame))
        ].copy()
        part["window_id"] = window.window_id
        shell_parts.append(part)
    shells = pd.concat(shell_parts, ignore_index=True)
    if shells["run_id"].astype(str).str.upper().str.contains("R04").any():
        raise RuntimeError("forbidden confirmation run entered shell contract")
    return windows, tracks, registry.sort_values(["run_id", "sar_frame_index"]), shells


def input_manifest(registry: pd.DataFrame) -> pd.DataFrame:
    paths: list[tuple[Path, str]] = [
        (T0_PRE / "window_registry.csv", "frozen T0 window selection"),
        (T0_PRE / "window_track_registry.csv", "frozen T0 track/window selection"),
        (FRAME_REGISTRY, "full-stream frame provenance"),
        (R2_Q95_REGIONS, "existing Q95 descriptor baseline"),
        (STRICT_MEMBERSHIP, "existing strict-family baseline"),
        (SHELLS, "frozen optical azimuth shells"),
        (P0_MODELS, "frozen common-apparent-transport models"),
        (P1E_SCRIPT, "unchanged C2/S(x) observation field"),
        (CANDIDATE_SCRIPT, "unchanged candidate-map construction"),
        (REGION_SCRIPT, "unchanged percentile/component operation"),
        (TASK / "HISTORICAL_OVERLAP.md", "historical duplication gate"),
    ]
    rows = []
    for path, role in paths:
        if not path.exists():
            raise FileNotFoundError(path)
        rows.append({"path": str(path.resolve()), "role": role, "bytes": path.stat().st_size, "sha256": sha256_file(path), "reference_used": False})
    for row in registry.itertuples(index=False):
        path = Path(str(row.sar_image_path))
        if not path.exists():
            raise FileNotFoundError(path)
        rows.append({"path": str(path.resolve()), "role": "unmodified SAR pseudocolor input frame", "bytes": path.stat().st_size, "sha256": sha256_file(path), "reference_used": False})
    frame = pd.DataFrame(rows)
    if frame["path"].str.upper().str.contains("R04ZF").any():
        raise RuntimeError("forbidden confirmation-run path entered input manifest")
    return frame


def reconstruct_representations(registry: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    p1e = load_module("u0_p1e", P1E_SCRIPT)
    candidate = load_module("u0_candidate", CANDIDATE_SCRIPT)
    region = load_module("u0_region", REGION_SCRIPT)
    MASKS.mkdir(parents=True, exist_ok=True)
    region_rows: list[dict[str, Any]] = []
    frame_rows: list[dict[str, Any]] = []
    r2_regions = pd.read_parquet(R2_Q95_REGIONS)
    r2_regions = r2_regions.set_index(["run_id", "frame_index"])
    for number, raw_row in enumerate(registry.itertuples(index=False), start=1):
        row = pd.Series(raw_row._asdict())
        frame = frame_record(row)
        image = cv2.imread(frame["sar_image_path"], cv2.IMREAD_COLOR)
        if image is None:
            raise FileNotFoundError(frame["sar_image_path"])
        mask, radial, theta, px_per_m = candidate.single_frame_observation_mask(frame, image)
        maps, metadata = candidate.compute_existing_candidate_maps_for_mask(p1e, frame, image, mask, radial, theta, px_per_m)
        support_radius_px = max(1, int(round(p1e.PHYSICAL_SUPPORT_RADIUS_M * px_per_m)))
        support_fraction = candidate.support_fraction_map(p1e, mask, support_radius_px)
        evaluation = p1e.build_evaluation_maps(maps, mask, support_radius_px, "fixed_support_mean_v2")
        score = evaluation[region.PRIMARY_CANDIDATE]
        eligible = mask & (support_fraction >= candidate.SUPPORT_TRUNCATED_MIN) & np.isfinite(score)
        percentile = region.percentile_field(score, eligible)
        arrays: dict[str, np.ndarray] = {
            "score_S": score.astype(np.float32),
            "percentile": percentile.astype(np.float32),
            "eligible": eligible.astype(np.uint8),
            "theta_deg": theta.astype(np.float32),
            "jet_proxy": metadata["jet_proxy"].astype(np.float32),
        }
        thresholds: dict[str, float] = {}
        counts: dict[str, int] = {}
        for level in LEVELS:
            labels, rows, threshold = region.component_descriptors(
                frame, score, percentile, eligible, support_fraction, radial, theta, px_per_m, level
            )
            tag = TAGS[level]
            arrays[tag] = labels.astype(np.int32)
            thresholds[tag] = float(threshold)
            counts[tag] = int(len(rows))
            region_rows.extend(rows)
        existing_path = R2_Q95_MASKS / f"{frame['sar_frame_uid']}.npz"
        with np.load(existing_path) as existing:
            parity = bool(np.array_equal(existing["Q095"], arrays["Q095"]))
        if not parity:
            raise RuntimeError(f"Q95 parity failed: {frame['sar_frame_uid']}")
        np.savez_compressed(MASKS / f"{frame['sar_frame_uid']}.npz", **arrays)
        q95_existing = r2_regions.loc[(frame["run_id"], frame["sar_frame_index"])]
        frame_rows.append({
            "run_id": frame["run_id"],
            "frame_uid": frame["sar_frame_uid"],
            "frame_index": frame["sar_frame_index"],
            "sar_image_path": frame["sar_image_path"],
            "sar_input_semantics": "UNMODIFIED_8BIT_PSEUDOCOLOR_DISPLAY_FRAME_NOT_SENSOR_RAW_AMPLITUDE",
            "score_semantics": "DISPLAY_DERIVED_FIXED_DISK_MEAN_OF_C2_COMPACT_GRADIENT_CONSENSUS",
            "q90_region_count": counts["Q090"],
            "q95_region_count": counts["Q095"],
            "q975_region_count": counts["Q0975"],
            "q90_numeric_threshold": thresholds["Q090"],
            "q95_numeric_threshold": thresholds["Q095"],
            "q975_numeric_threshold": thresholds["Q0975"],
            "q95_label_mask_pixel_exact_to_r2": parity,
            "q95_descriptor_row_count_matches_r2": counts["Q095"] == int(len(q95_existing)),
            "reference_used": False,
        })
        print(f"representation {number}/{len(registry)} {frame['sar_frame_uid']}", flush=True)
    return pd.DataFrame(region_rows), pd.DataFrame(frame_rows)


def build_hierarchy(regions: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    lookup = regions.set_index(["run_id", "frame_index", "percentile_tag", "region_label"])
    for (run_id, frame_index), group in regions.groupby(["run_id", "frame_index"], sort=False):
        uid = str(group.iloc[0]["frame_uid"])
        with np.load(MASKS / f"{uid}.npz") as archive:
            q90 = archive["Q090"]
            q95 = archive["Q095"]
            q975 = archive["Q0975"]
        for child_tag, parent_tag, child_labels, parent_labels in (
            ("Q095", "Q090", q95, q90),
            ("Q0975", "Q095", q975, q95),
            ("Q0975", "Q090", q975, q90),
        ):
            for child_label in sorted(set(np.unique(child_labels).tolist()) - {0}):
                pixels = child_labels == child_label
                parent_values, counts = np.unique(parent_labels[pixels], return_counts=True)
                valid = [(int(label), int(count)) for label, count in zip(parent_values, counts) if int(label) != 0]
                child_row = lookup.loc[(run_id, frame_index, child_tag, child_label)]
                if len(valid) != 1:
                    raise RuntimeError(f"non-unique sampled hierarchy parent: {uid} {child_tag} {child_label} -> {parent_tag} {valid}")
                parent_label, overlap = valid[0]
                parent_row = lookup.loc[(run_id, frame_index, parent_tag, parent_label)]
                rows.append({
                    "run_id": run_id,
                    "frame_index": int(frame_index),
                    "frame_uid": uid,
                    "child_tag": child_tag,
                    "child_region_id": str(child_row.region_id),
                    "child_region_label": int(child_label),
                    "parent_tag": parent_tag,
                    "parent_region_id": str(parent_row.region_id),
                    "parent_region_label": int(parent_label),
                    "child_pixel_count": int(child_row.pixel_count),
                    "parent_pixel_count": int(parent_row.pixel_count),
                    "contained_pixel_count": overlap,
                    "child_containment_fraction": overlap / max(int(child_row.pixel_count), 1),
                    "parent_coverage_fraction": overlap / max(int(parent_row.pixel_count), 1),
                    "code_operation": "exact label lookup at child pixels in a nested sampled threshold set",
                    "intended_semantic": "test whether a high-threshold fragment belongs to the same lower-threshold response structure",
                    "verified_semantic": "sampled threshold ancestry only; not physical identity or unrestricted max-tree authority",
                    "reference_used": False,
                })
    hierarchy = pd.DataFrame(rows)
    return hierarchy


def load_available_p0_models() -> tuple[dict[tuple[str, int, int], dict[str, Any]], pd.DataFrame]:
    raw = read_jsonl(P0_MODELS)
    rows = []
    models = {}
    for item in raw:
        run_id = str(item["run_id"])
        source = int(item["from_frame"])
        destination = int(item["to_frame"])
        available = str(item.get("p0_state")) == "P0_AVAILABLE" and bool(item.get("runtime_authority_allowed", False))
        rows.append({"run_id": run_id, "source_frame": source, "destination_frame": destination, "p0_available": available, "p0_state": item.get("p0_state"), "reference_used": False})
        if available:
            models[(run_id, source, destination)] = item
    return models, pd.DataFrame(rows)


def p0_matrix(model: dict[str, Any]) -> np.ndarray:
    dx, dy = model["parameters"]["translation_xy"]
    return np.asarray([[1.0, 0.0, float(dx)], [0.0, 1.0, float(dy)]], dtype=np.float32)


def build_temporal_edges(windows: pd.DataFrame, regions: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    models, availability_all = load_available_p0_models()
    lookup = regions.set_index(["run_id", "frame_index", "percentile_tag", "region_label"])
    rows: list[dict[str, Any]] = []
    availability_rows: list[dict[str, Any]] = []
    for window in windows.itertuples(index=False):
        for source_frame in range(int(window.start_frame), int(window.end_frame)):
            key = (str(window.run_id), source_frame, source_frame + 1)
            available = key in models
            availability_rows.append({"window_id": window.window_id, "run_id": window.run_id, "source_frame": source_frame, "destination_frame": source_frame + 1, "p0_available": available, "reference_used": False})
            if not available:
                continue
            matrix = p0_matrix(models[key])
            source_uid = f"{window.run_id}_SARF{source_frame:06d}"
            destination_uid = f"{window.run_id}_SARF{source_frame + 1:06d}"
            with np.load(MASKS / f"{source_uid}.npz") as source_archive, np.load(MASKS / f"{destination_uid}.npz") as destination_archive:
                for level in LEVELS:
                    tag = TAGS[level]
                    source_labels = source_archive[tag]
                    destination_labels = destination_archive[tag]
                    height, width = source_labels.shape
                    pair_rows: list[dict[str, Any]] = []
                    for source_label in sorted(set(np.unique(source_labels).tolist()) - {0}):
                        source_row = lookup.loc[(window.run_id, source_frame, tag, source_label)]
                        source_mask = source_labels == source_label
                        warped = cv2.warpAffine(source_mask.astype(np.float32), matrix, (width, height), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0.0)
                        warped_support = float(warped.sum())
                        destination_candidates = sorted(set(destination_labels[warped > 0].astype(int).tolist()) - {0})
                        for destination_label in destination_candidates:
                            destination_row = lookup.loc[(window.run_id, source_frame + 1, tag, destination_label)]
                            destination_mask = destination_labels == destination_label
                            intersection = float((warped * destination_mask).sum())
                            if intersection <= 0:
                                continue
                            destination_px = float(destination_row.pixel_count)
                            pair_rows.append({
                                "window_id": window.window_id,
                                "run_id": window.run_id,
                                "percentile_level": level,
                                "percentile_tag": tag,
                                "source_frame": source_frame,
                                "destination_frame": source_frame + 1,
                                "source_region_id": str(source_row.region_id),
                                "destination_region_id": str(destination_row.region_id),
                                "soft_intersection_px": intersection,
                                "source_support_px": float(source_row.pixel_count),
                                "warped_source_support_px": warped_support,
                                "destination_support_px": destination_px,
                                "source_retention": intersection / max(warped_support, 1e-9),
                                "destination_explained": intersection / max(destination_px, 1e-9),
                                "soft_iou": intersection / max(warped_support + destination_px - intersection, 1e-9),
                                "translation_dx_px": float(matrix[0, 2]),
                                "translation_dy_px": float(matrix[1, 2]),
                                "reference_used": False,
                            })
                    if pair_rows:
                        pair = pd.DataFrame(pair_rows)
                        source_max = pair.groupby("source_region_id")["source_retention"].transform("max")
                        destination_max = pair.groupby("destination_region_id")["destination_explained"].transform("max")
                        pair["source_dominant"] = np.isclose(pair["source_retention"], source_max, rtol=1e-9, atol=1e-12)
                        pair["destination_dominant"] = np.isclose(pair["destination_explained"], destination_max, rtol=1e-9, atol=1e-12)
                        pair["optional_compatible"] = pair["source_dominant"] | pair["destination_dominant"]
                        pair["lower_mutual_dominant"] = pair["source_dominant"] & pair["destination_dominant"]
                        optional = pair[pair["optional_compatible"]]
                        out_degree = optional.groupby("source_region_id")["destination_region_id"].nunique()
                        in_degree = optional.groupby("destination_region_id")["source_region_id"].nunique()
                        pair["optional_out_degree"] = pair["source_region_id"].map(out_degree).fillna(0).astype(int)
                        pair["optional_in_degree"] = pair["destination_region_id"].map(in_degree).fillna(0).astype(int)
                        pair["topology_ambiguity"] = np.select(
                            [(pair["optional_out_degree"] > 1) & (pair["optional_in_degree"] > 1), pair["optional_out_degree"] > 1, pair["optional_in_degree"] > 1],
                            ["SPLIT_AND_MERGE_LIKE", "SPLIT_LIKE", "MERGE_LIKE"],
                            default="ONE_TO_ONE_LIKE_OR_NONOPTIONAL",
                        )
                        pair["family_authority_semantics"] = "SAME_FROZEN_P0_WARP_AND_MUTUAL_DOMINANCE_OPERATION_APPLIED_PER_THRESHOLD"
                        rows.extend(pair.to_dict("records"))
    edges = pd.DataFrame(rows)
    return edges, pd.DataFrame(availability_rows)


class UnionFind:
    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def add(self, item: str) -> None:
        self.parent.setdefault(item, item)

    def find(self, item: str) -> str:
        self.add(item)
        if self.parent[item] != item:
            self.parent[item] = self.find(self.parent[item])
        return self.parent[item]

    def union(self, left: str, right: str) -> None:
        a, b = self.find(left), self.find(right)
        if a != b:
            self.parent[max(a, b)] = min(a, b)


def build_window_families(windows: pd.DataFrame, regions: pd.DataFrame, edges: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for window in windows.itertuples(index=False):
        for level in LEVELS:
            tag = TAGS[level]
            subset = regions[
                regions["run_id"].eq(window.run_id)
                & regions["frame_index"].between(int(window.start_frame), int(window.end_frame))
                & regions["percentile_tag"].eq(tag)
            ]
            uf = UnionFind()
            for region_id in subset["region_id"].astype(str):
                uf.add(region_id)
            selected_edges = edges[
                edges["window_id"].eq(window.window_id)
                & edges["percentile_tag"].eq(tag)
                & edges["lower_mutual_dominant"].astype(bool)
            ]
            for edge in selected_edges.itertuples(index=False):
                uf.union(str(edge.source_region_id), str(edge.destination_region_id))
            groups: dict[str, list[str]] = defaultdict(list)
            for region_id in subset["region_id"].astype(str):
                groups[uf.find(region_id)].append(region_id)
            ids = {root: stable_id("U0F", window.window_id, tag, min(members)) for root, members in groups.items()}
            for region in subset.itertuples(index=False):
                root = uf.find(str(region.region_id))
                rows.append({
                    "window_id": window.window_id,
                    "run_id": window.run_id,
                    "frame_index": int(region.frame_index),
                    "percentile_level": level,
                    "percentile_tag": tag,
                    "region_id": str(region.region_id),
                    "window_local_family_id": ids[root],
                    "family_semantics": "WINDOW_LOCAL_MUTUAL_DOMINANT_FROZEN_P0_COMPONENT_NO_OPTIONAL_UNION",
                    "reference_used": False,
                })
    return pd.DataFrame(rows)


def shell_incidence(
    shells: pd.DataFrame,
    regions: pd.DataFrame,
    families: pd.DataFrame,
) -> pd.DataFrame:
    family_map = families.set_index(["window_id", "percentile_tag", "region_id"])["window_local_family_id"].to_dict()
    strict = pd.read_parquet(STRICT_MEMBERSHIP)
    strict_map = strict.set_index(["run_id", "frame_index", "region_id"])["strict_family_id"].to_dict()
    region_lookup = regions.set_index(["run_id", "frame_index", "percentile_tag", "region_label"])
    rows: list[dict[str, Any]] = []
    for shell in shells.itertuples(index=False):
        uid = str(shell.frame_uid)
        intervals = parse_intervals(str(shell.effective_intervals_json))
        with np.load(MASKS / f"{uid}.npz") as archive:
            theta = archive["theta_deg"]
            shell_mask = np.zeros(theta.shape, dtype=bool)
            for low, high in intervals:
                shell_mask |= (theta >= low) & (theta <= high)
            for level in LEVELS:
                tag = TAGS[level]
                labels = archive[tag]
                labels_in = sorted(set(labels[shell_mask].astype(int).tolist()) - {0})
                for label in labels_in:
                    region = region_lookup.loc[(shell.run_id, int(shell.frame_index), tag, label)]
                    intersection = int(np.count_nonzero((labels == label) & shell_mask))
                    region_id = str(region.region_id)
                    rows.append({
                        "window_id": shell.window_id,
                        "run_id": shell.run_id,
                        "frame_index": int(shell.frame_index),
                        "track_id": shell.track_id,
                        "percentile_level": level,
                        "percentile_tag": tag,
                        "region_id": region_id,
                        "region_label": int(label),
                        "window_local_family_id": family_map[(shell.window_id, tag, region_id)],
                        "existing_strict_family_id": strict_map.get((shell.run_id, int(shell.frame_index), region_id)) if tag == "Q095" else None,
                        "shell_intersection_px": intersection,
                        "region_pixel_count": int(region.pixel_count),
                        "shell_fraction_of_region": intersection / max(int(region.pixel_count), 1),
                        "reference_used": False,
                    })
    return pd.DataFrame(rows)


def hierarchy_enrichment(hierarchy: pd.DataFrame, regions: pd.DataFrame) -> pd.DataFrame:
    q95_q90 = hierarchy[(hierarchy.child_tag == "Q095") & (hierarchy.parent_tag == "Q090")].copy()
    q975_q95 = hierarchy[(hierarchy.child_tag == "Q0975") & (hierarchy.parent_tag == "Q095")].copy()
    q975_q90 = hierarchy[(hierarchy.child_tag == "Q0975") & (hierarchy.parent_tag == "Q090")].copy()
    q95_counts = q95_q90.groupby("parent_region_id")["child_region_id"].nunique().rename("q95_child_count")
    q975_counts = q975_q90.groupby("parent_region_id")["child_region_id"].nunique().rename("q975_descendant_count")
    q975_per_q95 = q975_q95.groupby("parent_region_id")["child_region_id"].nunique().rename("q975_child_count")
    q90 = regions[regions.percentile_tag.eq("Q090")][["run_id", "frame_index", "region_id", "pixel_count", "area_m2", "range_min_m", "range_max_m", "theta_min_deg", "theta_max_deg"]].copy()
    q90 = q90.merge(q95_counts, left_on="region_id", right_index=True, how="left").merge(q975_counts, left_on="region_id", right_index=True, how="left")
    q90[["q95_child_count", "q975_descendant_count"]] = q90[["q95_child_count", "q975_descendant_count"]].fillna(0).astype(int)
    q90["hierarchy_risk_state"] = np.select(
        [(q90.q95_child_count > 1) & (q90.q975_descendant_count > 1), q90.q95_child_count > 1, q90.q975_descendant_count > 1],
        ["LOWER_LEVEL_PARENT_MERGES_MULTIPLE_Q95_AND_PEAK_CORES", "LOWER_LEVEL_PARENT_MERGES_Q95_FRAGMENTS", "SINGLE_Q95_WITH_MULTIPLE_PEAK_CORES"],
        default="SINGLE_NESTED_STRUCTURE_OR_NO_HIGH_CORE",
    )
    q95 = regions[regions.percentile_tag.eq("Q095")][["run_id", "frame_index", "region_id", "pixel_count", "area_m2"]].copy()
    q95 = q95.merge(q975_per_q95, left_on="region_id", right_index=True, how="left")
    q95["q975_child_count"] = q95["q975_child_count"].fillna(0).astype(int)
    write_table(q95, PRE / "q95_peak_core_multiplicity")
    return q90


def ambiguity_tables(
    windows: pd.DataFrame,
    tracks: pd.DataFrame,
    incidence: pd.DataFrame,
    q90_enriched: pd.DataFrame,
    hierarchy: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    frame_rows = []
    for keys, group in incidence.groupby(["window_id", "run_id", "track_id", "frame_index"], sort=False):
        window_id, run_id, track_id, frame_index = keys
        row: dict[str, Any] = {"window_id": window_id, "run_id": run_id, "track_id": track_id, "frame_index": int(frame_index), "reference_used": False}
        for tag, prefix in (("Q090", "q90"), ("Q095", "q95"), ("Q0975", "q975")):
            part = group[group.percentile_tag.eq(tag)]
            row[f"{prefix}_component_count"] = int(part.region_id.nunique())
            row[f"{prefix}_window_family_count"] = int(part.window_local_family_id.nunique())
            if tag == "Q095":
                row["existing_strict_family_count"] = int(part.existing_strict_family_id.dropna().nunique())
        frame_rows.append(row)
    frame = pd.DataFrame(frame_rows)

    q90_info = q90_enriched.set_index("region_id")
    endpoint_rows = []
    summary_rows = []
    for track in tracks.itertuples(index=False):
        part = incidence[(incidence.window_id == track.window_id) & (incidence.track_id == track.track_id)]
        first = int(track.first_shell_frame)
        last = int(track.last_shell_frame)
        q90 = part[part.percentile_tag.eq("Q090")].copy()
        q90["has_q95_child"] = q90.region_id.map(q90_info.q95_child_count).fillna(0).gt(0)
        q90["has_q975_descendant"] = q90.region_id.map(q90_info.q975_descendant_count).fillna(0).gt(0)
        first_families = set(q90[(q90.frame_index == first) & q90.has_q95_child & q90.has_q975_descendant].window_local_family_id)
        last_families = set(q90[(q90.frame_index == last) & q90.has_q95_child & q90.has_q975_descendant].window_local_family_id)
        invariant = first_families & last_families
        for family in sorted(first_families | last_families):
            endpoint_rows.append({
                "window_id": track.window_id,
                "run_id": track.run_id,
                "track_id": track.track_id,
                "q90_window_family_id": family,
                "nested_q90_q95_q975_at_first_endpoint": family in first_families,
                "nested_q90_q95_q975_at_last_endpoint": family in last_families,
                "endpoint_spanning_cross_level_invariant": family in invariant,
                "semantic_limit": "endpoint-spanning nested support, not physical identity or PERSON specificity",
                "reference_used": False,
            })
        fg = frame[(frame.window_id == track.window_id) & (frame.track_id == track.track_id)].sort_values("frame_index")
        last_row = fg[fg.frame_index == last].iloc[0]
        summary_rows.append({
            "window_id": track.window_id,
            "run_id": track.run_id,
            "track_id": track.track_id,
            "frame_count": int(len(fg)),
            "strict_family_ambiguity_median": float(fg.existing_strict_family_count.median()),
            "strict_family_ambiguity_last_frame": int(last_row.existing_strict_family_count),
            "q90_family_burden_median": float(fg.q90_window_family_count.median()),
            "q90_family_burden_last_frame": int(last_row.q90_window_family_count),
            "q975_peak_core_family_median": float(fg.q975_window_family_count.median()),
            "q975_peak_core_family_last_frame": int(last_row.q975_window_family_count),
            "endpoint_spanning_cross_level_invariant_ambiguity": int(len(invariant)),
            "invariant_semantics": "Q90 temporal family present at both shell endpoints with nested Q95 and Q97.5 support at both endpoints",
            "reference_used": False,
        })
    return frame, pd.DataFrame(summary_rows), pd.DataFrame(endpoint_rows)


def semantic_reverse_candidates(
    windows: pd.DataFrame,
    edges: pd.DataFrame,
    hierarchy: pd.DataFrame,
    q90_enriched: pd.DataFrame,
    regions: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    parent_q90 = hierarchy[(hierarchy.child_tag == "Q095") & (hierarchy.parent_tag == "Q090")].set_index("child_region_id")["parent_region_id"].to_dict()
    q975_counts = hierarchy[(hierarchy.child_tag == "Q0975") & (hierarchy.parent_tag == "Q095")].groupby("parent_region_id")["child_region_id"].nunique().to_dict()
    q95_children_by_q90 = hierarchy[
        (hierarchy.child_tag == "Q095") & (hierarchy.parent_tag == "Q090")
    ].groupby("parent_region_id")["child_region_id"].apply(lambda values: sorted(set(map(str, values)))).to_dict()
    q975_descendants_by_q90 = hierarchy[
        (hierarchy.child_tag == "Q0975") & (hierarchy.parent_tag == "Q090")
    ].groupby("parent_region_id")["child_region_id"].apply(lambda values: sorted(set(map(str, values)))).to_dict()
    rows = []
    selected_windows = set(windows[windows.window_id.str.startswith(("W3_", "W4_"))].window_id)
    q95 = edges[edges.window_id.isin(selected_windows) & edges.percentile_tag.eq("Q095") & edges.optional_compatible.astype(bool)].copy()
    q90_all = edges[edges.window_id.isin(selected_windows) & edges.percentile_tag.eq("Q090")].copy()
    q90 = q90_all[q90_all.optional_compatible.astype(bool)].copy()
    q90_pair = q90.set_index(["window_id", "source_frame", "source_region_id", "destination_region_id"])
    for keys, group in q95.groupby(["window_id", "run_id", "source_frame"], sort=False):
        window_id, run_id, source_frame = keys
        group = group.copy()
        group["q90_source_parent"] = group.source_region_id.map(parent_q90)
        group["q90_destination_parent"] = group.destination_region_id.map(parent_q90)
        for parent_keys, nested in group.groupby(["q90_source_parent", "q90_destination_parent"], dropna=False):
            q90_source, q90_destination = parent_keys
            source_count = int(nested.source_region_id.nunique())
            destination_count = int(nested.destination_region_id.nunique())
            source_peak_cores = int(sum(q975_counts.get(region_id, 0) for region_id in set(nested.source_region_id)))
            destination_peak_cores = int(sum(q975_counts.get(region_id, 0) for region_id in set(nested.destination_region_id)))
            source_edge_q95_ids = sorted(set(map(str, nested.source_region_id)))
            destination_edge_q95_ids = sorted(set(map(str, nested.destination_region_id)))
            source_parent_q95_ids = [] if pd.isna(q90_source) else q95_children_by_q90.get(str(q90_source), [])
            destination_parent_q95_ids = [] if pd.isna(q90_destination) else q95_children_by_q90.get(str(q90_destination), [])
            source_parent_q975_ids = [] if pd.isna(q90_source) else q975_descendants_by_q90.get(str(q90_source), [])
            destination_parent_q975_ids = [] if pd.isna(q90_destination) else q975_descendants_by_q90.get(str(q90_destination), [])
            selected_q90_edge = q90_all[
                q90_all.window_id.eq(window_id)
                & q90_all.source_frame.eq(int(source_frame))
                & q90_all.source_region_id.astype(str).eq(str(q90_source))
                & q90_all.destination_region_id.astype(str).eq(str(q90_destination))
            ]
            outgoing = q90[
                q90.window_id.eq(window_id)
                & q90.source_frame.eq(int(source_frame))
                & q90.source_region_id.astype(str).eq(str(q90_source))
            ]
            incoming = q90[
                q90.window_id.eq(window_id)
                & q90.source_frame.eq(int(source_frame))
                & q90.destination_region_id.astype(str).eq(str(q90_destination))
            ]
            outgoing_optional_ids = sorted(set(map(str, outgoing.destination_region_id)))
            outgoing_mutual_ids = sorted(set(map(str, outgoing.loc[outgoing.lower_mutual_dominant.astype(bool), "destination_region_id"])))
            incoming_optional_ids = sorted(set(map(str, incoming.source_region_id)))
            incoming_mutual_ids = sorted(set(map(str, incoming.loc[incoming.lower_mutual_dominant.astype(bool), "source_region_id"])))
            q90_state = "NO_Q90_P0_EDGE"
            if pd.notna(q90_source) and pd.notna(q90_destination):
                key = (window_id, int(source_frame), q90_source, q90_destination)
                if key in q90_pair.index:
                    value = q90_pair.loc[key]
                    if isinstance(value, pd.DataFrame):
                        value = value.iloc[0]
                    q90_state = str(value.topology_ambiguity)
            q95_fragmented = source_count > 1 or destination_count > 1
            multiple_peak_cores = source_peak_cores > source_count or destination_peak_cores > destination_count
            if q95_fragmented and q90_state == "ONE_TO_ONE_LIKE_OR_NONOPTIONAL":
                auto = "REPRESENTATION_DEPENDENT_Q95_FRAGMENTATION_CANDIDATE"
            elif q95_fragmented and q90_state in {"SPLIT_LIKE", "MERGE_LIKE", "SPLIT_AND_MERGE_LIKE"}:
                auto = "MULTILEVEL_TOPOLOGY_AMBIGUITY_CANDIDATE"
            elif multiple_peak_cores:
                auto = "Q95_OR_Q90_MERGE_OF_MULTIPLE_PEAK_CORES_CANDIDATE"
            else:
                auto = "ONE_TO_ONE_OR_UNCERTAIN"
            case_id = stable_id("U0CASE", window_id, source_frame, q90_source, q90_destination, auto)
            review = MANUAL_CASE_REVIEWS.get(case_id, {})
            rows.append({
                "case_id": case_id,
                "window_id": window_id,
                "run_id": run_id,
                "source_frame": int(source_frame),
                "destination_frame": int(source_frame) + 1,
                "q90_source_region_id": q90_source,
                "q90_destination_region_id": q90_destination,
                "q95_source_component_count": source_count,
                "q95_destination_component_count": destination_count,
                "q975_source_peak_core_count": source_peak_cores,
                "q975_destination_peak_core_count": destination_peak_cores,
                "q95_source_edge_participating_count": source_count,
                "q95_destination_edge_participating_count": destination_count,
                "q95_source_exact_parent_total_count": len(source_parent_q95_ids),
                "q95_destination_exact_parent_total_count": len(destination_parent_q95_ids),
                "q975_source_exact_parent_total_count": len(source_parent_q975_ids),
                "q975_destination_exact_parent_total_count": len(destination_parent_q975_ids),
                "q95_source_edge_region_ids_json": json.dumps(source_edge_q95_ids),
                "q95_destination_edge_region_ids_json": json.dumps(destination_edge_q95_ids),
                "q95_source_exact_parent_region_ids_json": json.dumps(source_parent_q95_ids),
                "q95_destination_exact_parent_region_ids_json": json.dumps(destination_parent_q95_ids),
                "q975_source_exact_parent_region_ids_json": json.dumps(source_parent_q975_ids),
                "q975_destination_exact_parent_region_ids_json": json.dumps(destination_parent_q975_ids),
                "q90_topology_state": q90_state,
                "q90_selected_edge_optional_compatible": bool(selected_q90_edge.optional_compatible.astype(bool).any()) if len(selected_q90_edge) else False,
                "q90_selected_edge_lower_mutual_dominant": bool(selected_q90_edge.lower_mutual_dominant.astype(bool).any()) if len(selected_q90_edge) else False,
                "q90_selected_edge_soft_iou": float(selected_q90_edge.soft_iou.max()) if len(selected_q90_edge) else math.nan,
                "q90_outgoing_optional_destination_ids_json": json.dumps(outgoing_optional_ids),
                "q90_outgoing_lower_mutual_destination_ids_json": json.dumps(outgoing_mutual_ids),
                "q90_incoming_optional_source_ids_json": json.dumps(incoming_optional_ids),
                "q90_incoming_lower_mutual_source_ids_json": json.dumps(incoming_mutual_ids),
                "q90_optional_out_degree_exact_source": len(outgoing_optional_ids),
                "q90_optional_in_degree_exact_destination": len(incoming_optional_ids),
                "automatic_stress_signal": auto,
                "manual_visual_class": review.get("manual_visual_class", "PENDING_DIRECT_REVIEW"),
                "what_image_shows": review.get("what_image_shows", "PENDING_DIRECT_REVIEW"),
                "what_is_invariant": review.get("what_is_invariant", "PENDING_DIRECT_REVIEW"),
                "what_remains_uncertain": review.get("what_remains_uncertain", "PENDING_DIRECT_REVIEW"),
                "reference_used": False,
            })
    cases = apply_case_review_policy(pd.DataFrame(rows))
    q90 = q90_enriched[q90_enriched.run_id.isin(["R01ZF", "R02ZF"])].copy()
    frame_to_window = {}
    for window in windows.itertuples(index=False):
        for frame in range(int(window.start_frame), int(window.end_frame) + 1):
            frame_to_window[(window.run_id, frame)] = window.window_id
    q90["window_id"] = q90.apply(lambda row: frame_to_window.get((row.run_id, int(row.frame_index))), axis=1)
    q90 = q90[q90.window_id.notna()].copy()
    q90["overmerge_pressure"] = q90.q95_child_count * q90.q975_descendant_count * q90.pixel_count
    counter = q90.sort_values("overmerge_pressure", ascending=False).groupby("window_id", as_index=False).head(3)
    counter = counter[["window_id", "run_id", "frame_index", "region_id", "pixel_count", "area_m2", "q95_child_count", "q975_descendant_count", "hierarchy_risk_state", "overmerge_pressure"]].copy()
    counter["falsification_role"] = "largest lower-threshold parent structures; inspect whether count reduction swallows independent background"
    counter["reference_used"] = False
    return cases.sort_values(["window_id", "source_frame", "case_id"]), counter.sort_values(["window_id", "overmerge_pressure"], ascending=[True, False])


def operation_semantics() -> pd.DataFrame:
    rows = [
        ("reconstruct_S_x", "Recompute unchanged P1E C2 fixed-support-mean field from the 8-bit pseudocolor frame.", "Expose the field whose percentile sets define current response support.", "Display-derived response field only; sensor raw amplitude/complex/IQ is unavailable."),
        ("threshold_components", "Take percentile >= tau inside the frozen eligible fan and run 8-connected components.", "Represent same-frame response support at Q90/Q95/Q97.5.", "Threshold-specific image regions; not physical objects, PERSON masks, or confidence components."),
        ("sampled_component_parent", "Look up each higher-threshold child pixel in the next lower-threshold label image.", "Test whether Q95 fragments reunite in a lower-level structure.", "Exact ancestry for three sampled levels only; not full max-tree truth."),
        ("threshold_specific_p0_family", "Warp each component with frozen P0, compute soft overlap, retain mutual source/destination dominance, and union those edges.", "Compare temporal fragmentation while holding the temporal operation fixed.", "Window-local continuity representation; not tracking, motion recovery, or identity."),
        ("optional_branch_topology_probe", "Count all optional-compatible incoming/outgoing Q90 edges separately from lower-mutual-dominant edges.", "Expose split/merge-like alternatives without promoting them to family identity.", "Optional branch degree is an ambiguity proposal only; it can be driven by weak overlap or an over-merged parent and is not lower-mutual family authority."),
        ("q90_parent_bundle_probe", "Treat Q95 siblings sharing a Q90 parent as a possible frame-local bundle for counting only.", "Stress whether Q95 separation is threshold-induced.", "A falsifiable bundle proposal; large parents may over-merge unrelated background."),
        ("endpoint_cross_level_invariant", "Count Q90 temporal families present at first and last shell frames with nested Q95 and Q97.5 support at both endpoints.", "Identify long-lived structures not erased by sampled threshold changes.", "Endpoint-spanning image-domain ambiguity; not PERSON discrimination or an exact physical-object count."),
    ]
    return pd.DataFrame(rows, columns=["code_operation", "program_computation", "intended_semantic", "verified_semantic"])


def color_for(value: str) -> tuple[float, float, float]:
    digest = hashlib.sha256(value.encode("utf-8")).digest()
    return tuple((64 + int(channel) * 0.70) / 255.0 for channel in digest[:3])


def load_frame_arrays(uid: str) -> dict[str, np.ndarray]:
    with np.load(MASKS / f"{uid}.npz") as archive:
        return {key: archive[key] for key in archive.files}


def robust_display(field: np.ndarray, mask: np.ndarray | None = None) -> np.ndarray:
    finite = np.isfinite(field)
    if mask is not None:
        finite &= mask
    values = field[finite]
    if not len(values):
        return np.zeros(field.shape, dtype=float)
    low, high = np.quantile(values, [0.01, 0.995])
    return np.clip((field - low) / max(high - low, 1e-9), 0.0, 1.0)


def draw_contours(ax: Any, labels: np.ndarray, color: str, linewidth: float = 0.7) -> None:
    for label in sorted(set(np.unique(labels).tolist()) - {0}):
        contours, _ = cv2.findContours((labels == label).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            points = contour[:, 0, :]
            ax.plot(points[:, 0], points[:, 1], color=color, linewidth=linewidth)


def render_window_figures(
    windows: pd.DataFrame,
    registry: pd.DataFrame,
    regions: pd.DataFrame,
    hierarchy: pd.DataFrame,
    families: pd.DataFrame,
) -> list[Path]:
    FIG.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    registry_map = {(str(row.run_id), int(row.sar_frame_index)): row for row in registry.itertuples(index=False)}
    strict = pd.read_parquet(STRICT_MEMBERSHIP)
    strict_map = strict.set_index("region_id")["strict_family_id"].to_dict()
    q95_parent = hierarchy[(hierarchy.child_tag == "Q095") & (hierarchy.parent_tag == "Q090")].set_index("child_region_id")["parent_region_id"].to_dict()
    q90_family = families[families.percentile_tag.eq("Q090")].set_index(["window_id", "region_id"])["window_local_family_id"].to_dict()
    region_lookup = regions.set_index(["run_id", "frame_index", "percentile_tag", "region_label"])
    for window in windows.itertuples(index=False):
        frames = list(range(int(window.start_frame), int(window.end_frame) + 1))
        fig, axes = plt.subplots(len(frames), 4, figsize=(16, max(12, 2.65 * len(frames))), constrained_layout=True)
        if len(frames) == 1:
            axes = axes[None, :]
        for row_index, frame_index in enumerate(frames):
            meta = registry_map[(window.run_id, frame_index)]
            uid = str(meta.sar_frame_uid)
            image_bgr = cv2.imread(str(meta.sar_image_path), cv2.IMREAD_COLOR)
            image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
            arrays = load_frame_arrays(uid)
            ax = axes[row_index, 0]
            ax.imshow(image_rgb)
            ax.set_title(f"{window.run_id} F{frame_index}\nunmodified pseudocolor input", fontsize=8)
            ax.axis("off")
            ax = axes[row_index, 1]
            ax.imshow(robust_display(arrays["score_S"], arrays["eligible"].astype(bool)), cmap="magma", vmin=0, vmax=1)
            ax.set_title("display-derived S(x)\n1–99.5% compression", fontsize=8)
            ax.axis("off")
            ax = axes[row_index, 2]
            ax.imshow(image_rgb)
            draw_contours(ax, arrays["Q090"], "cyan", 0.8)
            draw_contours(ax, arrays["Q095"], "yellow", 0.8)
            draw_contours(ax, arrays["Q0975"], "magenta", 0.8)
            ax.set_title("multi-level: Q90 cyan / Q95 yellow / Q97.5 magenta", fontsize=8)
            ax.axis("off")
            ax = axes[row_index, 3]
            ax.imshow(image_rgb)
            q90_labels = arrays["Q090"]
            q95_labels = arrays["Q095"]
            for label in sorted(set(np.unique(q90_labels).tolist()) - {0}):
                region = region_lookup.loc[(window.run_id, frame_index, "Q090", label)]
                family = q90_family[(window.window_id, str(region.region_id))]
                contours, _ = cv2.findContours((q90_labels == label).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                for contour in contours:
                    pts = contour[:, 0, :]
                    ax.plot(pts[:, 0], pts[:, 1], color=color_for(family), linewidth=1.2)
            draw_contours(ax, q95_labels, "white", 0.45)
            for label in sorted(set(np.unique(q95_labels).tolist()) - {0})[:24]:
                region = region_lookup.loc[(window.run_id, frame_index, "Q095", label)]
                family = str(strict_map.get(str(region.region_id), "NA"))[-5:]
                ax.text(float(region.centroid_x_px_shape_descriptor), float(region.centroid_y_px_shape_descriptor), family, fontsize=4.5, color="white", ha="center", va="center")
            ax.set_title("Q90 family color + white Q95 + strict ID suffix", fontsize=8)
            ax.axis("off")
        fig.suptitle(f"U0-R0 sequence representation atlas — {window.window_id}\nInput is pseudocolor display-domain SAR; no sensor raw amplitude is available", fontsize=13)
        path = FIG / f"{window.window_id}_sequence_representation_atlas.png"
        fig.savefig(path, dpi=130)
        plt.close(fig)
        paths.append(path)

        key_frames = [frames[0], frames[len(frames) // 2], frames[-1]]
        fig, axes = plt.subplots(3, 6, figsize=(24, 11), constrained_layout=True)
        for r, frame_index in enumerate(key_frames):
            meta = registry_map[(window.run_id, frame_index)]
            uid = str(meta.sar_frame_uid)
            image_bgr = cv2.imread(str(meta.sar_image_path), cv2.IMREAD_COLOR)
            image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
            arrays = load_frame_arrays(uid)
            panels = [
                (image_rgb, None, "unmodified pseudocolor input"),
                (robust_display(arrays["jet_proxy"], arrays["eligible"].astype(bool)), "gray", "display-derived jet/intensity proxy"),
                (robust_display(arrays["score_S"], arrays["eligible"].astype(bool)), "magma", "compressed S(x)"),
            ]
            for c, (panel, cmap, title) in enumerate(panels):
                axes[r, c].imshow(panel, cmap=cmap)
                axes[r, c].set_title(f"F{frame_index} {title}", fontsize=8)
                axes[r, c].axis("off")
            axes[r, 3].imshow(image_rgb)
            draw_contours(axes[r, 3], arrays["Q095"], "yellow", 1.0)
            axes[r, 3].set_title("current Q95 connected components", fontsize=8)
            axes[r, 3].axis("off")
            axes[r, 4].imshow(image_rgb)
            draw_contours(axes[r, 4], arrays["Q090"], "cyan", 1.0)
            draw_contours(axes[r, 4], arrays["Q095"], "yellow", 0.8)
            draw_contours(axes[r, 4], arrays["Q0975"], "magenta", 0.8)
            axes[r, 4].set_title("multi-level response sets", fontsize=8)
            axes[r, 4].axis("off")
            axes[r, 5].imshow(image_rgb)
            q90_labels = arrays["Q090"]
            for label in sorted(set(np.unique(q90_labels).tolist()) - {0}):
                region = region_lookup.loc[(window.run_id, frame_index, "Q090", label)]
                family = q90_family[(window.window_id, str(region.region_id))]
                contours, _ = cv2.findContours((q90_labels == label).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                for contour in contours:
                    pts = contour[:, 0, :]
                    axes[r, 5].plot(pts[:, 0], pts[:, 1], color=color_for(family), linewidth=1.2)
            draw_contours(axes[r, 5], arrays["Q095"], "white", 0.5)
            draw_contours(axes[r, 5], arrays["Q0975"], "black", 0.5)
            axes[r, 5].set_title("sampled hierarchy / Q90 temporal family", fontsize=8)
            axes[r, 5].axis("off")
        fig.suptitle(f"U0-R0 compact independent-review sheet — {window.window_id}\nColumns preserve input -> derived field -> current Q95 -> multi-level -> hierarchy order", fontsize=13)
        path = FIG / f"{window.window_id}_compact_review_sheet.png"
        fig.savefig(path, dpi=150)
        plt.close(fig)
        paths.append(path)
    return paths


def select_case_rows(cases: pd.DataFrame) -> pd.DataFrame:
    case_ids = set(cases.case_id.astype(str))
    missing = sorted(set(KEY_CASE_SELECTION) - case_ids)
    if missing:
        raise RuntimeError(f"GT-blind key-case allowlist rows missing: {missing}")
    selected = cases.set_index("case_id", drop=False).loc[list(KEY_CASE_SELECTION)].copy().reset_index(drop=True)
    return selected.sort_values(["window_id", "source_frame", "case_id"])


def apply_case_review_policy(cases: pd.DataFrame) -> pd.DataFrame:
    cases = cases.copy()
    selected_ids = set(select_case_rows(cases).case_id.astype(str))
    cases["selected_for_direct_review"] = cases.case_id.astype(str).isin(selected_ids)
    cases["review_selection_reason"] = np.where(
        cases.selected_for_direct_review,
        cases.case_id.astype(str).map(KEY_CASE_SELECTION),
        "AUTOMATIC_CANDIDATE_NOT_SELECTED_FOR_DIRECT_REVIEW",
    )
    cases["manual_visual_class"] = NOT_SELECTED
    cases["what_image_shows"] = "Not selected for direct review; no manual image-semantic claim is made."
    cases["what_is_invariant"] = "Not assessed outside the selected direct-review denominator."
    cases["what_remains_uncertain"] = "Automatic signal remains an unreviewed proposal."
    for case_id in selected_ids:
        review = MANUAL_CASE_REVIEWS.get(case_id, {})
        mask = cases.case_id.astype(str).eq(case_id)
        cases.loc[mask, "manual_visual_class"] = review.get("manual_visual_class", "PENDING_DIRECT_REVIEW")
        cases.loc[mask, "what_image_shows"] = review.get("what_image_shows", "PENDING_DIRECT_REVIEW")
        cases.loc[mask, "what_is_invariant"] = review.get("what_is_invariant", "PENDING_DIRECT_REVIEW")
        cases.loc[mask, "what_remains_uncertain"] = review.get("what_remains_uncertain", "PENDING_DIRECT_REVIEW")
    return cases


def enrich_case_family_mappings(cases: pd.DataFrame, families: pd.DataFrame) -> pd.DataFrame:
    cases = cases.copy()
    family_map = families.set_index("region_id")["window_local_family_id"].astype(str).to_dict()
    strict = pd.read_parquet(STRICT_MEMBERSHIP)
    strict_map = strict.set_index("region_id")["strict_family_id"].astype(str).to_dict()

    def mapped_ids(payload: str, mapping: dict[str, str]) -> str:
        values = json.loads(str(payload))
        return json.dumps(sorted({mapping.get(str(value), "NA") for value in values}))

    cases["q90_source_window_family_id"] = cases.q90_source_region_id.astype(str).map(family_map)
    cases["q90_destination_window_family_id"] = cases.q90_destination_region_id.astype(str).map(family_map)
    for side in ("source", "destination"):
        q95_field = f"q95_{side}_exact_parent_region_ids_json"
        q975_field = f"q975_{side}_exact_parent_region_ids_json"
        cases[f"q95_{side}_strict_family_ids_json"] = cases[q95_field].map(lambda value: mapped_ids(value, strict_map))
        cases[f"q95_{side}_window_family_ids_json"] = cases[q95_field].map(lambda value: mapped_ids(value, family_map))
        cases[f"q975_{side}_window_family_ids_json"] = cases[q975_field].map(lambda value: mapped_ids(value, family_map))
    return cases


def draw_binary_contours(ax: Any, mask: np.ndarray, color: str, linewidth: float = 1.0) -> None:
    contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for contour in contours:
        points = contour[:, 0, :]
        ax.plot(points[:, 0], points[:, 1], color=color, linewidth=linewidth)


def crop_bounds(masks: Iterable[np.ndarray], width: int, height: int, margin: int = 28) -> tuple[int, int, int, int]:
    xs: list[np.ndarray] = []
    ys: list[np.ndarray] = []
    for mask in masks:
        y, x = np.where(mask)
        if len(x):
            xs.append(x)
            ys.append(y)
    if not xs:
        return 0, 0, width, height
    x = np.concatenate(xs)
    y = np.concatenate(ys)
    x0 = max(0, int(x.min()) - margin)
    y0 = max(0, int(y.min()) - margin)
    x1 = min(width, int(x.max()) + margin + 1)
    y1 = min(height, int(y.max()) + margin + 1)
    return x0, y0, x1, y1


def hierarchy_region_maps(
    regions: pd.DataFrame,
    hierarchy: pd.DataFrame,
) -> tuple[dict[str, tuple[str, int]], dict[str, list[str]], dict[str, list[str]]]:
    region_labels = {
        str(row.region_id): (str(row.percentile_tag), int(row.region_label))
        for row in regions.itertuples(index=False)
    }
    q95_children: dict[str, list[str]] = defaultdict(list)
    q975_descendants: dict[str, list[str]] = defaultdict(list)
    for row in hierarchy.itertuples(index=False):
        if row.child_tag == "Q095" and row.parent_tag == "Q090":
            q95_children[str(row.parent_region_id)].append(str(row.child_region_id))
        if row.child_tag == "Q0975" and row.parent_tag == "Q090":
            q975_descendants[str(row.parent_region_id)].append(str(row.child_region_id))
    return region_labels, q95_children, q975_descendants


def region_ids_mask(
    arrays: dict[str, np.ndarray],
    region_labels: dict[str, tuple[str, int]],
    region_ids: Iterable[str],
) -> np.ndarray:
    mask = np.zeros(arrays["Q090"].shape, dtype=bool)
    for region_id in region_ids:
        tag, label = region_labels[str(region_id)]
        mask |= arrays[tag].eq(label) if hasattr(arrays[tag], "eq") else arrays[tag] == label
    return mask


def targeted_hierarchy_masks(
    arrays: dict[str, np.ndarray],
    q90_region_ids: Iterable[str],
    region_labels: dict[str, tuple[str, int]],
    q95_children: dict[str, list[str]],
    q975_descendants: dict[str, list[str]],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    q90_ids = [str(value) for value in q90_region_ids]
    q95_ids = [child for parent in q90_ids for child in q95_children.get(parent, [])]
    q975_ids = [child for parent in q90_ids for child in q975_descendants.get(parent, [])]
    return (
        region_ids_mask(arrays, region_labels, q90_ids),
        region_ids_mask(arrays, region_labels, q95_ids),
        region_ids_mask(arrays, region_labels, q975_ids),
    )


def shell_interval_map(shells: pd.DataFrame) -> dict[tuple[str, int], list[tuple[float, float]]]:
    result: dict[tuple[str, int], list[tuple[float, float]]] = defaultdict(list)
    for row in shells.itertuples(index=False):
        key = (str(row.window_id), int(row.frame_index))
        result[key].extend(parse_intervals(str(row.effective_intervals_json)))
    return {key: sorted(set(values)) for key, values in result.items()}


def mask_from_intervals(arrays: dict[str, np.ndarray], intervals: Iterable[tuple[float, float]]) -> np.ndarray:
    theta = arrays["theta_deg"]
    mask = np.zeros(theta.shape, dtype=bool)
    for low, high in intervals:
        mask |= (theta >= float(low)) & (theta <= float(high))
    return mask & arrays["eligible"].astype(bool)


def render_targeted_sequence_sheet(
    review_id: str,
    title: str,
    run_id: str,
    frame_targets: dict[int, list[str]],
    exact_frames: set[int],
    registry_map: dict[tuple[str, int], Any],
    region_labels: dict[str, tuple[str, int]],
    q95_children: dict[str, list[str]],
    q975_descendants: dict[str, list[str]],
    path: Path,
    exact_role_label: str = "exact source/destination parent",
    context_role_label: str = "same Q90 temporal-family context",
    shell_intervals_by_frame: dict[int, list[tuple[float, float]]] | None = None,
    branch_targets: dict[int, dict[str, Any]] | None = None,
    event_warp: dict[str, Any] | None = None,
    region_info: dict[str, dict[str, Any]] | None = None,
    strict_map: dict[str, str] | None = None,
) -> Path:
    loaded: dict[int, tuple[np.ndarray, dict[str, np.ndarray], tuple[np.ndarray, np.ndarray, np.ndarray]]] = {}
    target_masks = []
    for frame_index, q90_ids in frame_targets.items():
        meta = registry_map[(run_id, int(frame_index))]
        image_bgr = cv2.imread(str(meta.sar_image_path), cv2.IMREAD_COLOR)
        image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        arrays = load_frame_arrays(str(meta.sar_frame_uid))
        masks = targeted_hierarchy_masks(arrays, q90_ids, region_labels, q95_children, q975_descendants)
        loaded[int(frame_index)] = (image_rgb, arrays, masks)
        target_masks.append(masks[0])
    first_image = next(iter(loaded.values()))[0]
    height, width = first_image.shape[:2]
    x0, y0, x1, y1 = crop_bounds(target_masks, width, height)
    frames = sorted(frame_targets)
    event_mode = event_warp is not None
    column_count = 6 if event_mode else 5
    fig, axes = plt.subplots(len(frames), column_count, figsize=(24 if event_mode else 20, max(4.0, 3.65 * len(frames))), constrained_layout=True)
    if len(frames) == 1:
        axes = axes[None, :]
    for r, frame_index in enumerate(frames):
        image_rgb, arrays, masks = loaded[frame_index]
        q90_mask, q95_mask, q975_mask = masks
        role = exact_role_label if frame_index in exact_frames else context_role_label
        axes[r, 0].imshow(image_rgb)
        if shell_intervals_by_frame:
            shell_mask = mask_from_intervals(arrays, shell_intervals_by_frame.get(frame_index, []))
            draw_binary_contours(axes[r, 0], shell_mask, "white", 0.8)
        draw_binary_contours(axes[r, 0], q90_mask, "red", 1.5)
        axes[r, 0].add_patch(plt.Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, edgecolor="white", linewidth=1.0))
        axes[r, 0].set_title(f"F{frame_index} locator\n{role}", fontsize=8)
        raw_crop = image_rgb[y0:y1, x0:x1]
        score_crop = robust_display(arrays["score_S"], arrays["eligible"].astype(bool))[y0:y1, x0:x1]
        axes[r, 1].imshow(raw_crop)
        axes[r, 1].set_title("unmodified pseudocolor crop", fontsize=8)
        axes[r, 2].imshow(score_crop, cmap="magma", vmin=0, vmax=1)
        axes[r, 2].set_title("display-derived S(x) crop", fontsize=8)
        axes[r, 3].imshow(raw_crop)
        draw_binary_contours(axes[r, 3], q90_mask[y0:y1, x0:x1], "cyan", 1.6)
        draw_binary_contours(axes[r, 3], q95_mask[y0:y1, x0:x1], "yellow", 1.1)
        draw_binary_contours(axes[r, 3], q975_mask[y0:y1, x0:x1], "magenta", 1.0)
        q90_ids = [str(value) for value in frame_targets[frame_index]]
        q95_ids = [child for parent in q90_ids for child in q95_children.get(parent, [])]
        if region_info and strict_map:
            for q95_id in q95_ids:
                info = region_info.get(q95_id)
                if not info:
                    continue
                x = float(info["centroid_x_px_shape_descriptor"]) - x0
                y = float(info["centroid_y_px_shape_descriptor"]) - y0
                suffix = str(strict_map.get(q95_id, "NA"))[-5:]
                axes[r, 3].text(x, y, suffix, fontsize=5, color="white", ha="center", va="center")
        axes[r, 3].set_title("exact Q90/Q95/Q97.5; Q95 strict-ID suffix", fontsize=8)
        axes[r, 4].imshow(raw_crop)
        branch = (branch_targets or {}).get(frame_index, {})
        optional_mask = region_ids_mask(arrays, region_labels, branch.get("optional_ids", []))
        mutual_mask = region_ids_mask(arrays, region_labels, branch.get("mutual_ids", []))
        selected_mask = region_ids_mask(arrays, region_labels, branch.get("selected_ids", q90_ids))
        draw_binary_contours(axes[r, 4], optional_mask[y0:y1, x0:x1], "orange", 1.4)
        draw_binary_contours(axes[r, 4], mutual_mask[y0:y1, x0:x1], "lime", 1.3)
        draw_binary_contours(axes[r, 4], selected_mask[y0:y1, x0:x1], "cyan", 1.8)
        axes[r, 4].set_title(str(branch.get("label", "selected structure: cyan")), fontsize=8)
        if event_mode:
            axes[r, 5].imshow(raw_crop)
            source_frame = int(event_warp["source_frame"])
            destination_frame = int(event_warp["destination_frame"])
            if frame_index == source_frame:
                draw_binary_contours(axes[r, 5], q90_mask[y0:y1, x0:x1], "cyan", 1.8)
                axes[r, 5].set_title(
                    f"P0 source; dx={event_warp['dx_px']:.2f}, dy={event_warp['dy_px']:.2f}", fontsize=8
                )
            elif frame_index == destination_frame:
                source_mask = loaded[source_frame][2][0].astype(np.float32)
                matrix = np.asarray(event_warp["matrix"], dtype=np.float32)
                warped = cv2.warpAffine(source_mask, matrix, (width, height), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0.0)
                warped_binary = warped > 0.1
                overlap = warped_binary & q90_mask
                warped_only = warped_binary & ~q90_mask
                destination_only = q90_mask & ~warped_binary
                overlay = np.zeros((y1 - y0, x1 - x0, 4), dtype=float)
                overlay[warped_only[y0:y1, x0:x1]] = (1.0, 0.45, 0.0, 0.45)
                overlay[destination_only[y0:y1, x0:x1]] = (1.0, 0.0, 1.0, 0.42)
                overlay[overlap[y0:y1, x0:x1]] = (1.0, 1.0, 1.0, 0.65)
                axes[r, 5].imshow(overlay)
                draw_binary_contours(axes[r, 5], warped_binary[y0:y1, x0:x1], "orange", 1.0)
                draw_binary_contours(axes[r, 5], q90_mask[y0:y1, x0:x1], "cyan", 1.0)
                axes[r, 5].set_title("P0 residual: white overlap / orange source-only / magenta dest-only", fontsize=8)
            else:
                axes[r, 5].set_title("P0 residual shown only for exact pair", fontsize=8)
        for c in range(column_count):
            axes[r, c].axis("off")
    fig.suptitle(f"{review_id}\n{title}\nCrop [{x0},{y0},{x1},{y1}]; context family is not physical identity", fontsize=11)
    fig.savefig(path, dpi=170)
    plt.close(fig)
    return path


def q90_family_frame_regions(
    families: pd.DataFrame,
) -> tuple[dict[tuple[str, str], str], dict[tuple[str, str, int], list[str]]]:
    q90 = families[families.percentile_tag.eq("Q090")].copy()
    region_to_family = {
        (str(row.window_id), str(row.region_id)): str(row.window_local_family_id)
        for row in q90.itertuples(index=False)
    }
    frame_regions = q90.groupby(["window_id", "window_local_family_id", "frame_index"])["region_id"].apply(lambda values: sorted(set(map(str, values)))).to_dict()
    return region_to_family, frame_regions


def render_case_figures(
    cases: pd.DataFrame,
    windows: pd.DataFrame,
    registry: pd.DataFrame,
    regions: pd.DataFrame,
    hierarchy: pd.DataFrame,
    families: pd.DataFrame,
    edges: pd.DataFrame,
    shells: pd.DataFrame,
) -> list[Path]:
    selected = cases[cases.selected_for_direct_review.astype(bool)].copy().sort_values(["window_id", "source_frame", "case_id"])
    write_table(selected.drop(columns=["complexity"], errors="ignore"), PRE / "selected_semantic_reverse_audit_cases", parquet=False)
    registry_map = {(str(row.run_id), int(row.sar_frame_index)): row for row in registry.itertuples(index=False)}
    window_bounds = {str(row.window_id): (int(row.start_frame), int(row.end_frame)) for row in windows.itertuples(index=False)}
    region_labels, q95_children, q975_descendants = hierarchy_region_maps(regions, hierarchy)
    region_to_family, frame_regions = q90_family_frame_regions(families)
    region_info = regions.set_index("region_id").to_dict("index")
    strict = pd.read_parquet(STRICT_MEMBERSHIP)
    strict_map = strict.set_index("region_id")["strict_family_id"].astype(str).to_dict()
    shell_map = shell_interval_map(shells)
    p0_models, _ = load_available_p0_models()
    paths: list[Path] = []
    for case in selected.itertuples(index=False):
        start, end = window_bounds[str(case.window_id)]
        source = int(case.source_frame)
        destination = int(case.destination_frame)
        source_family = region_to_family[(str(case.window_id), str(case.q90_source_region_id))]
        destination_family = region_to_family[(str(case.window_id), str(case.q90_destination_region_id))]
        frame_targets: dict[int, list[str]] = {
            source: [str(case.q90_source_region_id)],
            destination: [str(case.q90_destination_region_id)],
        }
        if source - 1 >= start:
            context = frame_regions.get((str(case.window_id), source_family, source - 1), [])
            if context:
                frame_targets[source - 1] = context
        if destination + 1 <= end:
            context = frame_regions.get((str(case.window_id), destination_family, destination + 1), [])
            if context:
                frame_targets[destination + 1] = context
        incoming_optional = json.loads(str(case.q90_incoming_optional_source_ids_json))
        incoming_mutual = json.loads(str(case.q90_incoming_lower_mutual_source_ids_json))
        outgoing_optional = json.loads(str(case.q90_outgoing_optional_destination_ids_json))
        outgoing_mutual = json.loads(str(case.q90_outgoing_lower_mutual_destination_ids_json))
        branch_targets = {
            source: {
                "optional_ids": incoming_optional,
                "mutual_ids": incoming_mutual,
                "selected_ids": [str(case.q90_source_region_id)],
                "label": f"incoming Q90 parents: optional {len(incoming_optional)}, lower-mutual {len(incoming_mutual)}",
            },
            destination: {
                "optional_ids": outgoing_optional,
                "mutual_ids": outgoing_mutual,
                "selected_ids": [str(case.q90_destination_region_id)],
                "label": f"outgoing Q90 branches: optional {len(outgoing_optional)}, lower-mutual {len(outgoing_mutual)}",
            },
        }
        model = p0_models[(str(case.run_id), source, destination)]
        matrix = p0_matrix(model)
        event_warp = {
            "source_frame": source,
            "destination_frame": destination,
            "matrix": matrix.tolist(),
            "dx_px": float(matrix[0, 2]),
            "dy_px": float(matrix[1, 2]),
        }
        title = (
            f"{case.window_id} | {case.automatic_stress_signal} | Q90 {case.q90_topology_state}; "
            f"selected edge optional={case.q90_selected_edge_optional_compatible}, "
            f"lower-mutual={case.q90_selected_edge_lower_mutual_dominant}, IoU={case.q90_selected_edge_soft_iou:.3f}\n"
            f"edge-participating Q95 {case.q95_source_edge_participating_count}->{case.q95_destination_edge_participating_count}; "
            f"exact-parent Q95 {case.q95_source_exact_parent_total_count}->{case.q95_destination_exact_parent_total_count}; "
            f"exact-parent Q97.5 {case.q975_source_exact_parent_total_count}->{case.q975_destination_exact_parent_total_count}; "
            f"manual={case.manual_visual_class}"
        )
        path = FIG / f"case_targeted_{case.case_id}.png"
        paths.append(render_targeted_sequence_sheet(
            str(case.case_id), title, str(case.run_id), frame_targets, {source, destination}, registry_map,
            region_labels, q95_children, q975_descendants, path,
            shell_intervals_by_frame={frame: shell_map.get((str(case.window_id), frame), []) for frame in frame_targets},
            branch_targets=branch_targets,
            event_warp=event_warp,
            region_info=region_info,
            strict_map=strict_map,
        ))
    return paths


def apply_w15_review_notes(rows: pd.DataFrame) -> pd.DataFrame:
    rows = rows.copy()
    rows["manual_visual_class"] = "PENDING_DIRECT_REVIEW"
    rows["what_image_shows"] = "PENDING_DIRECT_REVIEW"
    rows["what_is_invariant"] = "PENDING_DIRECT_REVIEW"
    rows["what_remains_uncertain"] = "PENDING_DIRECT_REVIEW"
    for review_id, review in MANUAL_W15_REVIEWS.items():
        mask = rows.review_id.astype(str).eq(review_id)
        if not mask.any():
            continue
        for field in ("manual_visual_class", "what_image_shows", "what_is_invariant", "what_remains_uncertain"):
            rows.loc[mask, field] = review[field]
    return rows


def build_w15_review_rows(
    invariants: pd.DataFrame,
    counterexamples: pd.DataFrame,
    families: pd.DataFrame,
    regions: pd.DataFrame,
) -> pd.DataFrame:
    q90_families = families[families.percentile_tag.eq("Q090")].copy()
    q90_regions = regions[regions.percentile_tag.eq("Q090")][
        ["region_id", "range_min_m", "range_max_m", "pixel_count", "area_m2"]
    ].copy()
    q90_families = q90_families.merge(q90_regions, on="region_id", how="left")
    inv = invariants[
        invariants.endpoint_spanning_cross_level_invariant.astype(bool)
        & invariants.window_id.astype(str).str.startswith(("W1_", "W5_"))
    ].copy()
    inv_rows: list[dict[str, Any]] = []
    for (window_id, family_id), group in inv.groupby(["window_id", "q90_window_family_id"], sort=False):
        members = q90_families[
            q90_families.window_id.astype(str).eq(str(window_id))
            & q90_families.window_local_family_id.astype(str).eq(str(family_id))
        ].copy()
        range_center = (members.range_min_m + members.range_max_m) / 2.0
        frames = sorted(set(pd.to_numeric(members.frame_index).astype(int)))
        inv_rows.append({
            "review_id": stable_id("U0W15INV", window_id, family_id),
            "review_kind": "LONG_TERM_CROSS_LEVEL_INVARIANT",
            "window_id": str(window_id),
            "run_id": str(group.run_id.iloc[0]),
            "q90_window_family_id": str(family_id),
            "focus_frame": int(frames[len(frames) // 2]),
            "focus_q90_region_id": "",
            "frames_present": int(len(frames)),
            "first_frame": int(frames[0]),
            "last_frame": int(frames[-1]),
            "median_range_center_m_shape_descriptor": float(range_center.median()),
            "median_q90_area_m2": float(members.area_m2.median()),
            "supporting_track_ids_json": json.dumps(sorted(set(map(str, group.track_id))), ensure_ascii=False),
            "selection_role": "endpoint-spanning Q90 family with nested Q95 and Q97.5 support; selected for radial-separation visual audit",
            "reference_used": False,
        })
    inv_candidates = pd.DataFrame(inv_rows)
    selected_inv = []
    for window_id, group in inv_candidates.groupby("window_id", sort=False):
        ranked = group.sort_values(["frames_present", "median_q90_area_m2", "q90_window_family_id"], ascending=[False, False, True])
        first = ranked.iloc[0]
        selected_inv.append(first)
        if len(ranked) > 1:
            remainder = ranked.iloc[1:].copy()
            remainder["range_separation_from_first_m"] = (
                remainder.median_range_center_m_shape_descriptor - float(first.median_range_center_m_shape_descriptor)
            ).abs()
            selected_inv.append(remainder.sort_values(["range_separation_from_first_m", "frames_present"], ascending=[False, False]).iloc[0])
    selected_inv_df = pd.DataFrame(selected_inv).drop(columns=["range_separation_from_first_m"], errors="ignore")

    region_to_family, _ = q90_family_frame_regions(families)
    over_rows = []
    over = counterexamples[counterexamples.window_id.astype(str).str.startswith(("W1_", "W5_"))].copy()
    for window_id, group in over.groupby("window_id", sort=False):
        row = group.sort_values("overmerge_pressure", ascending=False).iloc[0]
        family_id = region_to_family[(str(row.window_id), str(row.region_id))]
        over_rows.append({
            "review_id": stable_id("U0W15OVER", row.window_id, row.frame_index, row.region_id),
            "review_kind": "LOWER_THRESHOLD_OVERMERGE_COUNTEREXAMPLE",
            "window_id": str(row.window_id),
            "run_id": str(row.run_id),
            "q90_window_family_id": family_id,
            "focus_frame": int(row.frame_index),
            "focus_q90_region_id": str(row.region_id),
            "frames_present": math.nan,
            "first_frame": math.nan,
            "last_frame": math.nan,
            "median_range_center_m_shape_descriptor": math.nan,
            "median_q90_area_m2": float(row.area_m2),
            "supporting_track_ids_json": "[]",
            "selection_role": f"largest Q90 over-merge pressure in window; Q95 children={int(row.q95_child_count)}, Q97.5 descendants={int(row.q975_descendant_count)}",
            "reference_used": False,
        })
    combined = pd.concat([selected_inv_df, pd.DataFrame(over_rows)], ignore_index=True)
    return apply_w15_review_notes(combined.sort_values(["window_id", "review_kind", "review_id"]))


def render_w15_review_figures(
    rows: pd.DataFrame,
    windows: pd.DataFrame,
    registry: pd.DataFrame,
    regions: pd.DataFrame,
    hierarchy: pd.DataFrame,
    families: pd.DataFrame,
    shells: pd.DataFrame,
) -> list[Path]:
    write_table(rows, PRE / "selected_w1_w5_representation_reviews", parquet=False)
    write_table(rows[rows.review_kind.eq("LONG_TERM_CROSS_LEVEL_INVARIANT")], PRE / "selected_long_term_invariant_families", parquet=False)
    write_table(rows[rows.review_kind.eq("LOWER_THRESHOLD_OVERMERGE_COUNTEREXAMPLE")], PRE / "selected_overmerge_counterexamples", parquet=False)
    registry_map = {(str(row.run_id), int(row.sar_frame_index)): row for row in registry.itertuples(index=False)}
    window_bounds = {str(row.window_id): (int(row.start_frame), int(row.end_frame)) for row in windows.itertuples(index=False)}
    region_labels, q95_children, q975_descendants = hierarchy_region_maps(regions, hierarchy)
    region_info = regions.set_index("region_id").to_dict("index")
    strict = pd.read_parquet(STRICT_MEMBERSHIP)
    strict_map = strict.set_index("region_id")["strict_family_id"].astype(str).to_dict()
    shell_map = shell_interval_map(shells)
    _, frame_regions = q90_family_frame_regions(families)
    paths: list[Path] = []
    for row in rows.itertuples(index=False):
        window_id = str(row.window_id)
        family_id = str(row.q90_window_family_id)
        start, end = window_bounds[window_id]
        exact_frames: set[int] = set()
        if row.review_kind == "LONG_TERM_CROSS_LEVEL_INVARIANT":
            available = sorted(frame for (window, family, frame) in frame_regions if window == window_id and family == family_id)
            frames = sorted(set([available[0], available[len(available) // 2], available[-1]]))
            frame_targets = {frame: frame_regions[(window_id, family_id, frame)] for frame in frames}
            exact_frames = set(frames)
            exact_label = "selected endpoint-spanning Q90 family support"
            context_label = exact_label
            file_name = f"invariant_targeted_{row.review_id}.png"
        else:
            focus = int(row.focus_frame)
            frame_targets = {focus: [str(row.focus_q90_region_id)]}
            for frame in (focus - 1, focus + 1):
                if start <= frame <= end:
                    context = frame_regions.get((window_id, family_id, frame), [])
                    if context:
                        frame_targets[frame] = context
            exact_frames = {focus}
            exact_label = "exact high-pressure Q90 parent"
            context_label = "same Q90 temporal-family context"
            file_name = f"overmerge_targeted_{row.review_id}.png"
        title = f"{window_id} | {row.review_kind} | manual={row.manual_visual_class} | {row.selection_role}"
        paths.append(render_targeted_sequence_sheet(
            str(row.review_id), title, str(row.run_id), frame_targets, exact_frames, registry_map,
            region_labels, q95_children, q975_descendants, FIG / file_name,
            exact_role_label=exact_label, context_role_label=context_label,
            shell_intervals_by_frame={frame: shell_map.get((window_id, frame), []) for frame in frame_targets},
            region_info=region_info,
            strict_map=strict_map,
        ))
    return paths


def render_fixed_invariant_atlases(
    windows: pd.DataFrame,
    registry: pd.DataFrame,
    regions: pd.DataFrame,
    hierarchy: pd.DataFrame,
    families: pd.DataFrame,
    shells: pd.DataFrame,
) -> list[Path]:
    registry_map = {(str(row.run_id), int(row.sar_frame_index)): row for row in registry.itertuples(index=False)}
    window_map = {str(row.window_id): row for row in windows.itertuples(index=False)}
    region_labels, q95_children, q975_descendants = hierarchy_region_maps(regions, hierarchy)
    _, frame_regions = q90_family_frame_regions(families)
    shell_map = shell_interval_map(shells)
    manifest_rows: list[dict[str, Any]] = []
    paths: list[Path] = []
    for group in INVARIANT_ATLAS_GROUPS:
        window_id = str(group["window_id"])
        window = window_map[window_id]
        start, end = int(window.start_frame), int(window.end_frame)
        frames = sorted({start, (start + end) // 2, end})
        family_ids = [str(value) for value in group["family_ids"]]
        loaded: dict[int, tuple[np.ndarray, dict[str, np.ndarray], dict[str, np.ndarray]]] = {}
        all_masks: list[np.ndarray] = []
        for frame_index in frames:
            meta = registry_map[(str(window.run_id), frame_index)]
            image_bgr = cv2.imread(str(meta.sar_image_path), cv2.IMREAD_COLOR)
            image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
            arrays = load_frame_arrays(str(meta.sar_frame_uid))
            family_masks: dict[str, np.ndarray] = {}
            for family_id in family_ids:
                region_ids = frame_regions.get((window_id, family_id, frame_index), [])
                family_masks[family_id] = region_ids_mask(arrays, region_labels, region_ids)
                all_masks.append(family_masks[family_id])
            loaded[frame_index] = (image_rgb, arrays, family_masks)
        height, width = next(iter(loaded.values()))[0].shape[:2]
        x0, y0, x1, y1 = crop_bounds(all_masks, width, height, margin=42)
        fig, axes = plt.subplots(len(frames), 3, figsize=(15, 4.2 * len(frames)), constrained_layout=True)
        if len(frames) == 1:
            axes = axes[None, :]
        for row_index, frame_index in enumerate(frames):
            image_rgb, arrays, family_masks = loaded[frame_index]
            shell_mask = mask_from_intervals(arrays, shell_map.get((window_id, frame_index), []))
            axes[row_index, 0].imshow(image_rgb)
            draw_binary_contours(axes[row_index, 0], shell_mask, "white", 0.8)
            axes[row_index, 0].add_patch(plt.Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, edgecolor="white", linewidth=1.0))
            for family_id, mask in family_masks.items():
                draw_binary_contours(axes[row_index, 0], mask, color_for(family_id), 1.6)
            axes[row_index, 0].set_title(f"F{frame_index} full-frame locator; white=optical shell union", fontsize=8)
            raw_crop = image_rgb[y0:y1, x0:x1]
            axes[row_index, 1].imshow(raw_crop)
            axes[row_index, 2].imshow(robust_display(arrays["score_S"], arrays["eligible"].astype(bool))[y0:y1, x0:x1], cmap="magma", vmin=0, vmax=1)
            for family_id, mask in family_masks.items():
                color = color_for(family_id)
                draw_binary_contours(axes[row_index, 1], mask[y0:y1, x0:x1], color, 1.8)
                draw_binary_contours(axes[row_index, 2], mask[y0:y1, x0:x1], color, 1.8)
                q90_ids = frame_regions.get((window_id, family_id, frame_index), [])
                _, q95_mask, q975_mask = targeted_hierarchy_masks(arrays, q90_ids, region_labels, q95_children, q975_descendants)
                draw_binary_contours(axes[row_index, 2], q95_mask[y0:y1, x0:x1], "yellow", 0.8)
                draw_binary_contours(axes[row_index, 2], q975_mask[y0:y1, x0:x1], "magenta", 0.7)
                y_pixels, x_pixels = np.where(mask[y0:y1, x0:x1])
                if len(x_pixels):
                    axes[row_index, 1].text(float(np.median(x_pixels)), float(np.median(y_pixels)), family_id[-5:], color="white", fontsize=6, ha="center", va="center")
            axes[row_index, 1].set_title(f"fixed crop [{x0},{y0},{x1},{y1}] with family-ID suffix", fontsize=8)
            axes[row_index, 2].set_title("same fixed crop: Q90 family color / Q95 yellow / Q97.5 magenta", fontsize=8)
            for column in range(3):
                axes[row_index, column].axis("off")
        fig.suptitle(
            f"{group['atlas_id']} — {group['purpose']}\nShared axes preserve radial/azimuth separation; colors are window-local image-domain families, not identities",
            fontsize=11,
        )
        path = FIG / f"invariant_atlas_{group['atlas_id']}.png"
        fig.savefig(path, dpi=170)
        plt.close(fig)
        paths.append(path)
        manifest_rows.append({
            "atlas_id": group["atlas_id"],
            "window_id": window_id,
            "run_id": str(window.run_id),
            "family_ids_json": json.dumps(family_ids),
            "frames_json": json.dumps(frames),
            "fixed_crop_xyxy_json": json.dumps([x0, y0, x1, y1]),
            "purpose": group["purpose"],
            "reference_used": False,
        })
    write_table(pd.DataFrame(manifest_rows), PRE / "fixed_coordinate_invariant_atlas_manifest", parquet=False)
    return paths


def write_pre_report(
    summary: pd.DataFrame,
    cases: pd.DataFrame,
    counterexamples: pd.DataFrame,
    frame_summary: pd.DataFrame,
    w15_reviews: pd.DataFrame,
) -> None:
    lines = [
        "# U0-R0 — SAR Response Representation Stress Test (Pre-reference)",
        "",
        "## Scope and input truth",
        "",
        "The pre-construction runner is reference-isolated: it uses only T0 W1/W3/W4/W5 and never reads R04 or the manual PERSON reference. The available SAR runtime input is an 8-bit pseudocolor display frame, not sensor raw amplitude/complex/IQ. Figures therefore show the unmodified pseudocolor input, a display-derived intensity proxy, and the unchanged P1E C2/S(x) field separately.",
        "Strict analyst-naive reveal ordering cannot be claimed because the reference table schema and sample rows were inspected while implementing the later post-reference loader. No reference value was used to choose thresholds, hierarchy, cases, formulas, or manual pre-reference classifications; the supported claim is code/data isolation, not analyst blindness.",
        "",
        "## Representation burden",
        "",
        "| Window / track | strict Q95 median | sampled Q90 family burden median | Q97.5 family median | strict last | sampled Q90 burden last | cross-level endpoint invariant |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary.itertuples(index=False):
        lines.append(
            f"| {row.window_id} / {row.track_id} | {row.strict_family_ambiguity_median:.1f} | {row.q90_family_burden_median:.1f} | {row.q975_peak_core_family_median:.1f} | {row.strict_family_ambiguity_last_frame} | {row.q90_family_burden_last_frame} | {row.endpoint_spanning_cross_level_invariant_ambiguity} |"
        )
    lines.extend([
        "",
        "These counts are representation burdens, not physical target counts. Q90 can connect some Q95 fragments, while also activating or absorbing additional background structures; its count is not a collapsed object count. Q97.5 may expose peak cores and may also fragment a broad response.",
        "",
        "## Reverse semantic audit status",
        "",
    ])
    status_counts = cases.manual_visual_class.value_counts().to_dict() if len(cases) else {}
    lines.append(f"Manual visual classes: `{json.dumps(status_counts, ensure_ascii=False)}`.")
    lines.append(f"Direct-review denominator: `{int(cases.selected_for_direct_review.astype(bool).sum())}` selected of `{len(cases)}` automatic candidates; all other rows are `{NOT_SELECTED}`.")
    lines.append("")
    for row in select_case_rows(cases).itertuples(index=False):
        lines.extend([
            f"### {row.case_id} — {row.window_id} F{row.source_frame}->F{row.destination_frame}",
            "",
            f"- Code signal: `{row.automatic_stress_signal}`; Q90 topology `{row.q90_topology_state}`.",
            f"- Edge-participating / exact-parent descendants: Q95 `{row.q95_source_edge_participating_count}->{row.q95_destination_edge_participating_count}` / `{row.q95_source_exact_parent_total_count}->{row.q95_destination_exact_parent_total_count}`; Q97.5 exact-parent `{row.q975_source_exact_parent_total_count}->{row.q975_destination_exact_parent_total_count}`.",
            f"- Selected Q90 edge: optional-compatible `{row.q90_selected_edge_optional_compatible}`, lower-mutual-dominant `{row.q90_selected_edge_lower_mutual_dominant}`, soft IoU `{row.q90_selected_edge_soft_iou:.3f}`. Optional topology is not family authority.",
            f"- Manual visual class: `{row.manual_visual_class}`.",
            f"- What image shows: {row.what_image_shows}",
            f"- What is invariant: {row.what_is_invariant}",
            f"- What remains uncertain: {row.what_remains_uncertain}",
            "",
        ])
    lines.extend([
        "## W1/W5 targeted invariant and over-merge review",
        "",
    ])
    for row in w15_reviews.itertuples(index=False):
        lines.extend([
            f"### {row.review_id} — {row.window_id}",
            "",
            f"- Review kind: `{row.review_kind}`; manual visual class: `{row.manual_visual_class}`.",
            f"- What image shows: {row.what_image_shows}",
            f"- What is invariant: {row.what_is_invariant}",
            f"- What remains uncertain: {row.what_remains_uncertain}",
            "",
        ])
    lines.extend([
        "## Falsification attempts",
        "",
        f"The lower-threshold over-merge ledger contains {len(counterexamples)} deliberately selected large Q90 parents. They are not success examples: each asks whether a lower threshold reduces count by swallowing independent ridge/background support.",
        "The fixed-coordinate atlases show five long-lived, radially/azimuthally separated W1 structures and multiple W5 near/mid/far or broad-ridge structures. This supports persistent SAR image-domain multiplicity only. Several W5 structures are visibly background-compatible, and the endpoint-invariant W5 broad ridge is also a lower-threshold over-merge counterexample.",
        "",
        f"Q95 pixel-exact parity: {int(frame_summary.q95_label_mask_pixel_exact_to_r2.sum())}/{len(frame_summary)} frames. Q95 descriptor row-count parity: {int(frame_summary.q95_descriptor_row_count_matches_r2.sum())}/{len(frame_summary)} frames.",
        "",
        "## Current stopping boundary",
        "",
        "No representation is selected as a winner in the pre-reference phase. If any selected W3/W4 or W1/W5 direct visual review remains pending, the representation is not frozen for reference reveal.",
    ])
    text = "\n".join(lines) + "\n"
    (OUTPUT / "REPORT_PRE_REFERENCE.md").write_text(text, encoding="utf-8")
    (PRE / "REPORT_PRE_REFERENCE.md").write_text(text, encoding="utf-8")


def freeze_pre_reference() -> dict[str, Any]:
    cases = pd.read_csv(PRE / "semantic_reverse_audit_candidates.csv")
    selected = cases[cases.selected_for_direct_review.astype(bool)]
    if selected.manual_visual_class.eq("PENDING_DIRECT_REVIEW").any():
        raise RuntimeError("selected W3/W4 direct visual review is still pending; refusing final pre-reference freeze")
    if not set(selected.manual_visual_class).issubset(REVIEW_CLASSES):
        raise RuntimeError("selected W3/W4 review contains an invalid manual class")
    w15 = pd.read_csv(PRE / "selected_w1_w5_representation_reviews.csv")
    if w15.manual_visual_class.eq("PENDING_DIRECT_REVIEW").any():
        raise RuntimeError("selected W1/W5 direct visual review is still pending; refusing final pre-reference freeze")
    if not set(w15.manual_visual_class).issubset(W15_REVIEW_CLASSES):
        raise RuntimeError("selected W1/W5 review contains an invalid manual class")
    targets = [path for path in PRE.rglob("*") if path.is_file() and path.name not in {"pre_reference_freeze_manifest.csv", "pre_reference_freeze_summary.json"}]
    rows = []
    for path in sorted(targets):
        relative = path.relative_to(PRE).as_posix()
        rows.append({"relative_path": relative, "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = pd.DataFrame(rows)
    manifest.to_csv(PRE / "pre_reference_freeze_manifest.csv", index=False)
    digest = hashlib.sha256()
    for row in manifest.itertuples(index=False):
        digest.update(f"{row.relative_path}|{row.bytes}|{row.sha256}\n".encode("utf-8"))
    summary = {
        "schema": "PERSON_U0_R0_PRE_REFERENCE_FREEZE_V2",
        "file_count": int(len(manifest)),
        "tree_sha256": digest.hexdigest().upper(),
        "windows": sorted(SELECTED_WINDOW_IDS),
        "selected_frame_count": 44,
        "levels": list(LEVELS),
        "reference_used": False,
        "r04_used": False,
        "preconstruction_reference_codepath_used": False,
        "analyst_naive_reveal_order_preserved": False,
        "phase_isolation_claim": "reference schema/sample inspection occurred during post-loader implementation; no reference value entered construction, selection, formulas, or manual pre-reference classification",
        "sensor_raw_amplitude_available": False,
    }
    (PRE / "pre_reference_freeze_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def verify_freeze() -> dict[str, Any]:
    manifest = pd.read_csv(PRE / "pre_reference_freeze_manifest.csv")
    expected = set(manifest.relative_path.astype(str))
    actual = {
        path.relative_to(PRE).as_posix()
        for path in PRE.rglob("*")
        if path.is_file() and path.name not in {"pre_reference_freeze_manifest.csv", "pre_reference_freeze_summary.json"}
    }
    if actual != expected:
        raise RuntimeError(f"pre-reference file-set mismatch: missing={sorted(expected - actual)} unexpected={sorted(actual - expected)}")
    for row in manifest.itertuples(index=False):
        path = PRE / row.relative_path
        if not path.exists() or path.stat().st_size != int(row.bytes) or sha256_file(path) != str(row.sha256):
            raise RuntimeError(f"pre-reference freeze mismatch: {row.relative_path}")
    digest = hashlib.sha256()
    for row in manifest.itertuples(index=False):
        digest.update(f"{row.relative_path}|{row.bytes}|{row.sha256}\n".encode("utf-8"))
    summary = json.loads((PRE / "pre_reference_freeze_summary.json").read_text(encoding="utf-8"))
    if digest.hexdigest().upper() != summary["tree_sha256"]:
        raise RuntimeError("pre-reference tree digest mismatch")
    return summary


def run_pre() -> None:
    if WORKSPACE.resolve() != Path(r"D:\profile\research\workspace").resolve():
        raise RuntimeError(f"workspace mismatch: {WORKSPACE}")
    if "old_work" in str(SCRIPT).lower() or "old_work" in str(OUTPUT).lower():
        raise RuntimeError("archive-only path entered runtime")
    if PRE.exists():
        shutil.rmtree(PRE)
    if POST.exists():
        shutil.rmtree(POST)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    shutil.copy2(TASK / "HISTORICAL_OVERLAP.md", OUTPUT / "HISTORICAL_OVERLAP.md")
    windows, tracks, registry, shells = load_contract()
    write_table(windows, PRE / "window_registry", parquet=False)
    write_table(tracks, PRE / "window_track_registry", parquet=False)
    write_table(input_manifest(registry), PRE / "input_manifest", parquet=False)
    regions, frame_summary = reconstruct_representations(registry)
    write_table(regions, PRE / "threshold_component_regions")
    write_table(frame_summary, PRE / "frame_representation_summary")
    hierarchy = build_hierarchy(regions)
    write_table(hierarchy, PRE / "sampled_component_hierarchy")
    q90_enriched = hierarchy_enrichment(hierarchy, regions)
    write_table(q90_enriched, PRE / "q90_parent_structure_audit")
    edges, availability = build_temporal_edges(windows, regions)
    write_table(edges, PRE / "threshold_specific_p0_edges")
    write_table(availability, PRE / "selected_window_p0_availability", parquet=False)
    families = build_window_families(windows, regions, edges)
    write_table(families, PRE / "threshold_specific_window_family_membership")
    incidence = shell_incidence(shells, regions, families)
    write_table(incidence, PRE / "track_threshold_region_incidence")
    frame_ambiguity, ambiguity_summary, invariants = ambiguity_tables(windows, tracks, incidence, q90_enriched, hierarchy)
    write_table(frame_ambiguity, PRE / "track_frame_ambiguity_by_representation")
    write_table(ambiguity_summary, PRE / "track_window_ambiguity_summary")
    write_table(invariants, PRE / "cross_level_endpoint_invariant_families")
    cases, counterexamples = semantic_reverse_candidates(windows, edges, hierarchy, q90_enriched, regions)
    cases = enrich_case_family_mappings(cases, families)
    write_table(cases, PRE / "semantic_reverse_audit_candidates", parquet=False)
    write_table(counterexamples, PRE / "lower_threshold_overmerge_counterexamples", parquet=False)
    write_table(operation_semantics(), PRE / "operation_semantics", parquet=False)
    render_window_figures(windows, registry, regions, hierarchy, families)
    render_case_figures(cases, windows, registry, regions, hierarchy, families, edges, shells)
    w15_reviews = build_w15_review_rows(invariants, counterexamples, families, regions)
    render_w15_review_figures(w15_reviews, windows, registry, regions, hierarchy, families, shells)
    render_fixed_invariant_atlases(windows, registry, regions, hierarchy, families, shells)
    shutil.copy2(TASK / "HISTORICAL_OVERLAP.md", PRE / "HISTORICAL_OVERLAP.md")
    write_pre_report(ambiguity_summary, cases, counterexamples, frame_summary, w15_reviews)
    selected_pending = cases.selected_for_direct_review.astype(bool) & cases.manual_visual_class.eq("PENDING_DIRECT_REVIEW")
    if not selected_pending.any() and not w15_reviews.manual_visual_class.eq("PENDING_DIRECT_REVIEW").any():
        summary = freeze_pre_reference()
        print(f"pre-reference frozen {summary['tree_sha256']}", flush=True)
    else:
        print("draft pre-reference products complete; selected direct visual reviews required before freeze", flush=True)


def run_finalize_pre() -> None:
    if (PRE / "pre_reference_freeze_manifest.csv").exists() or (PRE / "pre_reference_freeze_summary.json").exists():
        raise RuntimeError("pre-reference tree is already frozen; refusing to mutate it")
    required = [
        PRE / "window_registry.csv",
        PRE / "window_track_registry.csv",
        PRE / "frame_representation_summary.parquet",
        PRE / "threshold_component_regions.parquet",
        PRE / "sampled_component_hierarchy.parquet",
        PRE / "q90_parent_structure_audit.parquet",
        PRE / "threshold_specific_p0_edges.parquet",
        PRE / "threshold_specific_window_family_membership.parquet",
        PRE / "track_window_ambiguity_summary.parquet",
        PRE / "cross_level_endpoint_invariant_families.csv",
        PRE / "semantic_reverse_audit_candidates.csv",
        PRE / "lower_threshold_overmerge_counterexamples.csv",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise RuntimeError(f"draft pre-reference inputs missing: {missing}")
    windows, _, registry, shells = load_contract()
    frame_summary = pd.read_parquet(PRE / "frame_representation_summary.parquet")
    regions = pd.read_parquet(PRE / "threshold_component_regions.parquet")
    hierarchy = pd.read_parquet(PRE / "sampled_component_hierarchy.parquet")
    q90_enriched = pd.read_parquet(PRE / "q90_parent_structure_audit.parquet")
    edges = pd.read_parquet(PRE / "threshold_specific_p0_edges.parquet")
    families = pd.read_parquet(PRE / "threshold_specific_window_family_membership.parquet")
    ambiguity_summary = pd.read_parquet(PRE / "track_window_ambiguity_summary.parquet")
    legacy_rename = {
        "representation_collapsed_q90_family_median": "q90_family_burden_median",
        "representation_collapsed_q90_family_last_frame": "q90_family_burden_last_frame",
    }
    ambiguity_summary = ambiguity_summary.rename(columns=legacy_rename)
    write_table(ambiguity_summary, PRE / "track_window_ambiguity_summary")
    invariants = pd.read_csv(PRE / "cross_level_endpoint_invariant_families.csv")
    cases, counterexamples = semantic_reverse_candidates(windows, edges, hierarchy, q90_enriched, regions)
    cases = enrich_case_family_mappings(cases, families)
    write_table(cases, PRE / "semantic_reverse_audit_candidates", parquet=False)
    write_table(counterexamples, PRE / "lower_threshold_overmerge_counterexamples", parquet=False)
    write_table(operation_semantics(), PRE / "operation_semantics", parquet=False)
    for pattern in ("case_*.png", "case_targeted_*.png", "invariant_targeted_*.png", "overmerge_targeted_*.png", "invariant_atlas_*.png"):
        for path in FIG.glob(pattern):
            path.unlink()
    render_case_figures(cases, windows, registry, regions, hierarchy, families, edges, shells)
    w15_reviews = build_w15_review_rows(invariants, counterexamples, families, regions)
    render_w15_review_figures(w15_reviews, windows, registry, regions, hierarchy, families, shells)
    render_fixed_invariant_atlases(windows, registry, regions, hierarchy, families, shells)
    shutil.copy2(TASK / "HISTORICAL_OVERLAP.md", PRE / "HISTORICAL_OVERLAP.md")
    write_pre_report(ambiguity_summary, cases, counterexamples, frame_summary, w15_reviews)
    selected_pending = cases.selected_for_direct_review.astype(bool) & cases.manual_visual_class.eq("PENDING_DIRECT_REVIEW")
    if selected_pending.any() or w15_reviews.manual_visual_class.eq("PENDING_DIRECT_REVIEW").any():
        print("targeted pre-reference review sheets refreshed; selected direct reviews remain pending", flush=True)
        return
    summary = freeze_pre_reference()
    print(f"pre-reference frozen {summary['tree_sha256']}", flush=True)


def reference_diagnostic() -> tuple[pd.DataFrame, pd.DataFrame]:
    p1e = load_module("u0_post_p1e", P1E_SCRIPT)
    windows = pd.read_csv(PRE / "window_registry.csv")
    tracks = pd.read_csv(PRE / "window_track_registry.csv")
    regions = pd.read_parquet(PRE / "threshold_component_regions.parquet")
    families = pd.read_parquet(PRE / "threshold_specific_window_family_membership.parquet")
    reference = pd.read_parquet(REFERENCE)
    mapping = pd.read_csv(FRAGMENT_TARGET_MAP)
    mapping = mapping.set_index(["run_id", "entity_id"])["target_id"].to_dict()
    registry = pd.read_parquet(FRAME_REGISTRY)
    registry_map = {(str(row.run_id), int(row.sar_frame_index)): pd.Series(row._asdict()) for row in registry.itertuples(index=False)}
    region_label_lookup = regions.set_index(["run_id", "frame_index", "percentile_tag", "region_label"])
    family_lookup = families.set_index(["window_id", "percentile_tag", "region_id"])["window_local_family_id"].to_dict()
    rows = []
    for track in tracks.itertuples(index=False):
        target_id = mapping.get((track.run_id, track.track_id))
        if target_id is None:
            continue
        refs = reference[
            reference.run_id.eq(track.run_id)
            & reference.target_id.eq(target_id)
            & reference.frame_index.between(int(track.first_shell_frame), int(track.last_shell_frame))
        ]
        for ref in refs.itertuples(index=False):
            meta = frame_record(registry_map[(track.run_id, int(ref.frame_index))])
            px_per_m = meta["geometry"]["radius_px"] / meta["geometry"]["outer_range_m"]
            point = p1e.point_from_polar(float(ref.reference_range_m) * px_per_m, float(ref.reference_theta_deg), meta["geometry"])
            x, y = int(round(float(point[0]))), int(round(float(point[1])))
            uid = meta["sar_frame_uid"]
            arrays = load_frame_arrays(uid)
            for level in LEVELS:
                tag = TAGS[level]
                label = int(arrays[tag][y, x]) if 0 <= y < arrays[tag].shape[0] and 0 <= x < arrays[tag].shape[1] else 0
                region_id = None
                family_id = None
                pixel_count = math.nan
                if label:
                    region = region_label_lookup.loc[(track.run_id, int(ref.frame_index), tag, label)]
                    region_id = str(region.region_id)
                    family_id = family_lookup[(track.window_id, tag, region_id)]
                    pixel_count = int(region.pixel_count)
                rows.append({
                    "window_id": track.window_id,
                    "run_id": track.run_id,
                    "track_id": track.track_id,
                    "target_id_post_reference": target_id,
                    "frame_index": int(ref.frame_index),
                    "percentile_level": level,
                    "percentile_tag": tag,
                    "reference_x_px": float(point[0]),
                    "reference_y_px": float(point[1]),
                    "reference_in_component": bool(label),
                    "reference_region_id": region_id,
                    "reference_window_family_id": family_id,
                    "reference_region_pixel_count": pixel_count,
                    "construction_unchanged_after_reference": True,
                })
    diagnostic = pd.DataFrame(rows)
    summary_rows = []
    for keys, group in diagnostic.groupby(["window_id", "run_id", "track_id", "percentile_tag"], sort=False):
        window_id, run_id, track_id, tag = keys
        ordered = group.sort_values("frame_index")
        supported = ordered[ordered.reference_in_component]
        family_sequence = supported.reference_window_family_id.dropna().astype(str).tolist()
        switches = sum(left != right for left, right in zip(family_sequence, family_sequence[1:]))
        summary_rows.append({
            "window_id": window_id,
            "run_id": run_id,
            "track_id": track_id,
            "percentile_tag": tag,
            "reference_sample_count": int(len(ordered)),
            "reference_supported_count": int(ordered.reference_in_component.sum()),
            "reference_support_fraction": float(ordered.reference_in_component.mean()) if len(ordered) else math.nan,
            "reference_unique_window_family_count": int(supported.reference_window_family_id.nunique()),
            "reference_family_switch_count": int(switches),
            "reference_region_pixel_count_median": float(pd.to_numeric(supported.reference_region_pixel_count, errors="coerce").median()) if len(supported) else math.nan,
            "diagnostic_semantics": "post-reference consistency only; not construction, threshold tuning, or localization performance",
        })
    return diagnostic, pd.DataFrame(summary_rows)


def write_final_report(post_summary: pd.DataFrame) -> None:
    pre_summary = pd.read_csv(PRE / "track_window_ambiguity_summary.csv")
    cases = pd.read_csv(PRE / "semantic_reverse_audit_candidates.csv")
    w15 = pd.read_csv(PRE / "selected_w1_w5_representation_reviews.csv")
    reviewed = cases[
        cases.selected_for_direct_review.astype(bool)
        & cases.manual_visual_class.isin(REVIEW_CLASSES)
    ]
    induced = reviewed[reviewed.manual_visual_class.isin(["ALGORITHM_INDUCED_SPLIT", "ALGORITHM_INDUCED_MERGE"])]
    invariant = reviewed[reviewed.manual_visual_class.eq("GENUINE_UNRESOLVED_STRUCTURE")]
    uncertain = reviewed[reviewed.manual_visual_class.eq("UNCERTAIN")]
    w15_invariant = w15[w15.manual_visual_class.eq("VISIBLE_CROSS_LEVEL_LONG_TERM_STRUCTURE")]
    w15_overmerge = w15[w15.manual_visual_class.eq("LOWER_THRESHOLD_OVERMERGE_PRESSURE")]
    support_totals = []
    for tag, group in post_summary.groupby("percentile_tag", sort=False):
        support_totals.append(
            f"{tag} {int(group.reference_supported_count.sum())}/{int(group.reference_sample_count.sum())} supported, "
            f"{int(group.reference_family_switch_count.sum())} family switches"
        )
    lines = [
        "# U0-R0 — SAR Response Representation Stress Test",
        "",
        "## Outcome first",
        "",
        "U0-R0 changes the abstraction audit, not PERSON localization. Q90/Q95/Q97.5 and a sampled hierarchy were compared with the temporal operation held fixed. Any count contraction is reported separately from image-supported structure and from post-reference consistency.",
        "",
        "The input limitation is material: the current pipeline exposes 8-bit pseudocolor display frames, not sensor raw amplitude/complex/IQ. All conclusions are therefore conditional SAR image-domain response conclusions.",
        "",
        "## A. Which T0 ambiguities are representation-induced?",
        "",
    ]
    if len(induced):
        for row in induced.itertuples(index=False):
            lines.append(f"- `{row.case_id}` ({row.window_id} F{row.source_frame}->F{row.destination_frame}): `{row.manual_visual_class}`. {row.what_image_shows}")
    else:
        lines.append("- No reviewed case was strong enough to label algorithm-induced split/merge.")
    for row in w15_overmerge.itertuples(index=False):
        lines.append(f"- `{row.review_id}` ({row.window_id}): `{row.manual_visual_class}`. {row.what_image_shows}")
    lines.extend(["", "## B. Which ambiguities remain under multiple reasonable representations?", ""])
    if len(invariant):
        for row in invariant.itertuples(index=False):
            lines.append(f"- `{row.case_id}` ({row.window_id}): {row.what_is_invariant}")
    else:
        lines.append("- No case was promoted beyond uncertainty solely from the automated hierarchy.")
    for row in w15_invariant.itertuples(index=False):
        lines.append(f"- `{row.review_id}` ({row.window_id}): {row.what_is_invariant} {row.what_remains_uncertain}")
    lines.append("- Global representation-collapsed ambiguity: not established. Sampled Q90 family burden is usually higher than strict Q95 burden, so Q90 is reported as a stress-test burden rather than a collapsed physical-object count.")
    for row in pre_summary.itertuples(index=False):
        lines.append(
            f"- `{row.window_id}` / `{row.track_id}`: strict-Q95 median `{row.strict_family_ambiguity_median:.1f}`, sampled-Q90-family burden median `{row.q90_family_burden_median:.1f}`, endpoint cross-level invariant burden `{row.endpoint_spanning_cross_level_invariant_ambiguity}`. These are image-domain hypotheses, not target counts."
        )
    lines.extend([
        "",
        "## C. Minimum reasonable SAR response abstraction",
        "",
        "For these four windows, the minimum adequate audit abstraction is a **multi-level response structure record with explicit parent/child evidence and set-valued temporal continuity**. This is not yet a confirmed physical response-object definition. A lone Q95 component is too brittle in reviewed fragmentation cases, while an unrestricted Q90 bundle is too permissive in the deliberate over-merge counterexamples. Q97.5 peak cores help expose internal multiplicity but are not sufficient objects by themselves.",
        "",
        "The abstraction is therefore not 'Q90 wins'. It is: retain the unmodified field, the three sampled level sets, exact ancestry, and optional split/merge semantics. Do not force one threshold or one family ID to carry physical identity.",
        "",
        "## D. Meaning for PERSON localization",
        "",
        "- Representation improvement: supported only where the same visible structure stops changing ID after explicit hierarchy is retained.",
        "- Ambiguity reduction: count contraction is conditional and must exclude Q90 over-merge cases.",
        "- Actual PERSON discrimination: not established. Post-reference checks only measure whether sparse references remain inside frozen structures and whether family switching changes.",
        f"- Frozen post-reference containment totals: {'; '.join(support_totals)}. Higher Q90 containment is confounded by visibly over-merged parents and is not localization improvement.",
        "",
        "## Post-reference consistency diagnostic",
        "",
        "| Window / track | level | samples | supported | family switches | median component px |",
        "|---|---|---:|---:|---:|---:|",
    ])
    for row in post_summary.itertuples(index=False):
        median_px = "NA" if pd.isna(row.reference_region_pixel_count_median) else f"{row.reference_region_pixel_count_median:.0f}"
        lines.append(f"| {row.window_id} / {row.track_id} | {row.percentile_tag} | {row.reference_sample_count} | {row.reference_supported_count} | {row.reference_family_switch_count} | {median_px} |")
    lines.extend([
        "",
        f"Reviewed semantic cases: {len(reviewed)}; algorithm-induced: {len(induced)}; genuine unresolved: {len(invariant)}; uncertain: {len(uncertain)}.",
        "",
        "Validator PASS, hashes, and reproducible figures establish artifact integrity and phase isolation only. They do not establish physical truth or localization improvement.",
    ])
    (OUTPUT / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_post() -> None:
    freeze = verify_freeze()
    POST.mkdir(parents=True, exist_ok=True)
    diagnostic, summary = reference_diagnostic()
    write_table(diagnostic, POST / "reference_representation_diagnostic")
    write_table(summary, POST / "reference_representation_summary", parquet=False)
    state = {
        "schema": "PERSON_U0_R0_POST_REFERENCE_STATE_V1",
        "pre_reference_tree_sha256": freeze["tree_sha256"],
        "reference_rows": int(len(diagnostic)),
        "summary_rows": int(len(summary)),
        "construction_changed_after_reference": False,
        "reference_used_for_parameter_choice": False,
        "r04_used": False,
    }
    (POST / "post_reference_state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
    write_final_report(summary)
    print(f"post-reference diagnostic complete rows={len(diagnostic)}", flush=True)


def run_pack() -> None:
    verify_freeze()
    if not (OUTPUT / "REPORT.md").exists():
        raise RuntimeError("final report missing; run post first")
    if PACK.exists():
        shutil.rmtree(PACK)
    PACK.mkdir(parents=True)
    records = []
    files = [
        OUTPUT / "HISTORICAL_OVERLAP.md",
        OUTPUT / "REPORT_PRE_REFERENCE.md",
        OUTPUT / "REPORT.md",
        PRE / "operation_semantics.csv",
        PRE / "track_window_ambiguity_summary.csv",
        PRE / "semantic_reverse_audit_candidates.csv",
        PRE / "lower_threshold_overmerge_counterexamples.csv",
        PRE / "selected_semantic_reverse_audit_cases.csv",
        PRE / "selected_w1_w5_representation_reviews.csv",
        PRE / "selected_long_term_invariant_families.csv",
        PRE / "selected_overmerge_counterexamples.csv",
        PRE / "fixed_coordinate_invariant_atlas_manifest.csv",
        PRE / "pre_reference_freeze_manifest.csv",
        PRE / "pre_reference_freeze_summary.json",
        POST / "reference_representation_diagnostic.csv",
        POST / "reference_representation_summary.csv",
        POST / "post_reference_state.json",
    ] + sorted(FIG.glob("*.png"))
    for source in files:
        destination = PACK / ("figures" if source.suffix.lower() == ".png" else "tables_and_reports") / source.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        records.append({"relative_path": destination.relative_to(PACK).as_posix(), "bytes": destination.stat().st_size, "sha256": sha256_file(destination), "source_path": str(source.resolve())})
    manifest = pd.DataFrame(records)
    manifest.to_csv(PACK / "REVIEW_PACK_MANIFEST.csv", index=False)
    if PACK_ZIP.exists():
        PACK_ZIP.unlink()
    with zipfile.ZipFile(PACK_ZIP, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(PACK.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(PACK.parent))
    print(f"review pack: {PACK_ZIP}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("pre", "finalize-pre", "post", "pack"), required=True)
    args = parser.parse_args()
    if args.phase == "pre":
        run_pre()
    elif args.phase == "finalize-pre":
        run_finalize_pre()
    elif args.phase == "post":
        run_post()
    else:
        run_pack()


if __name__ == "__main__":
    main()
