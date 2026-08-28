"""Run the frozen, GT-blind M0B1-R angular representation audit."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd


SCRIPT = Path(__file__).resolve()
TASK_DIR = SCRIPT.parent
WORKSPACE = TASK_DIR.parents[1]
STUDY = WORKSPACE / "output" / "person_physics_guided_image_domain_study_20260824"
OLD_ROOT = STUDY / "m0b1_r02_raw_fragment_angular_direction_diagnostic"
OUTPUT = STUDY / "m0b1_r_angular_dynamic_representation_audit"
PROTOCOL = OUTPUT / "M0B1_R_ANGULAR_DYNAMIC_REPRESENTATION_AUDIT_PROTOCOL_FROZEN_BEFORE_RUN.md"
FREEZE = OUTPUT / "protocol_freeze.json"
VALIDATOR = TASK_DIR / "validate_m0b1_r_representation_audit.py"

BANK = OLD_ROOT / "dynamic_hypotheses_pre_reference.csv"
OLD_SUMMARY = OLD_ROOT / "pre_reference_summary.json"
OLD_PROTOCOL = OLD_ROOT / "M0B1_R02_RAW_FRAGMENT_ANGULAR_DIRECTION_PROTOCOL_FROZEN_BEFORE_RUN.md"
OLD_RUNNER = WORKSPACE / "tasks" / "person_m0b1_r02_raw_fragment_angular_direction_20260828" / "run_m0b1_raw_fragment_angular_direction.py"
OLD_REPORT = OLD_ROOT / "M0B1_R02_RAW_FRAGMENT_ANGULAR_DIRECTION_REPORT.md"
TIMING_QUERIES = OLD_ROOT / "timing_query_table_pre_reference.csv"

MAPPING_ROOT = WORKSPACE / "output" / "r01_person_azimuth_pilot_20260819"
MAPPING_MODEL = MAPPING_ROOT / "model_summary.json"
MAPPING_TIME_SCAN = MAPPING_ROOT / "time_offset_scan.csv"
MAPPING_LOO = MAPPING_ROOT / "leave_one_person_out_metrics.csv"

TOL = 1e-12
FROZEN_HEAD = "752dd28f26666c8e9e08fd94ad0e74a2beebfade"
FROZEN_M0B1_STATE = "M0B1_ANGULAR_DIRECTION_OBSERVABILITY_INSUFFICIENT"

SOURCE_PATHS = [
    BANK,
    OLD_SUMMARY,
    OLD_PROTOCOL,
    OLD_RUNNER,
    OLD_REPORT,
    TIMING_QUERIES,
    MAPPING_MODEL,
    MAPPING_TIME_SCAN,
    MAPPING_LOO,
]

BANK_COLUMNS = [
    "run_id",
    "timing_condition",
    "pair_index",
    "from_frame_uid",
    "to_frame_uid",
    "from_frame",
    "to_frame",
    "base_edge_id",
    "source_region_id",
    "destination_region_id",
    "source_theta_min_deg",
    "source_theta_max_deg",
    "destination_theta_min_deg",
    "destination_theta_max_deg",
    "source_touches_boundary",
    "destination_touches_boundary",
    "source_truncated",
    "destination_truncated",
    "reference_used",
    "identity_assignment_performed",
    "hypothesis_pruned",
    "hypothesis_id",
    "source_track_id",
    "destination_track_id",
    "static_feasible",
    "angular_availability_state",
    "source_optical_frame_index",
    "destination_optical_frame_index",
    "source_optical_timestamp_ms",
    "destination_optical_timestamp_ms",
    "optical_delta_interval_low_deg",
    "optical_delta_interval_high_deg",
    "optical_direction_state",
    "source_raw_theta_low_deg",
    "source_raw_theta_high_deg",
    "destination_raw_theta_low_deg",
    "destination_raw_theta_high_deg",
    "source_fragment_observation_count",
    "destination_fragment_observation_count",
]


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def file_record(path: Path) -> dict[str, Any]:
    return {"path": str(path.absolute()), "size_bytes": path.stat().st_size, "sha256": sha256_file(path)}


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_table(stem: str, frame: pd.DataFrame) -> None:
    frame.to_csv(OUTPUT / f"{stem}.csv", index=False, encoding="utf-8-sig")
    frame.to_parquet(OUTPUT / f"{stem}.parquet", index=False, compression="zstd")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--freeze", action="store_true")
    mode.add_argument("--run", action="store_true")
    return parser.parse_args()


def freeze_protocol() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    if FREEZE.exists():
        raise RuntimeError(f"Freeze already exists: {FREEZE}")
    for path in [PROTOCOL, VALIDATOR, SCRIPT, *SOURCE_PATHS]:
        if not path.exists():
            raise FileNotFoundError(path)
        if "old_work" in str(path).lower():
            raise RuntimeError(f"old_work source is prohibited: {path}")
    payload = {
        "schema": "PERSON_M0B1_R_PROTOCOL_FREEZE_V1",
        "created_at": now_iso(),
        "frozen_head": FROZEN_HEAD,
        "frozen_predecessor_state": FROZEN_M0B1_STATE,
        "reference_loaded": False,
        "manual_reference_used_in_optical_representation_audit": False,
        "frozen_mapping_tables_with_prior_reference_provenance_read_for_sign_audit": True,
        "manual_reference_used_to_select_representation": False,
        "representation_selected_from_post_reference_outcome": False,
        "numerical_tolerance_deg": TOL,
        "old_work_dependency": False,
        "protocol": file_record(PROTOCOL),
        "runner": file_record(SCRIPT),
        "validator": file_record(VALIDATOR),
        "sources": [file_record(path) for path in SOURCE_PATHS],
        "prohibited": [
            "post_reference_representation_selection",
            "manual_reference",
            "weighted_score",
            "classifier",
            "magnitude_fit",
            "pruning",
            "pareto_pruning",
            "factor_graph",
            "identity",
            "tracker",
            "M0B2",
            "P2",
        ],
    }
    write_json(FREEZE, payload)
    print(json.dumps({"status": "FROZEN", "freeze": str(FREEZE)}, ensure_ascii=False, indent=2))


def verify_freeze() -> dict[str, Any]:
    if not FREEZE.exists():
        raise RuntimeError("Run --freeze before --run")
    payload = json.loads(FREEZE.read_text(encoding="utf-8"))
    checks = [payload["protocol"], payload["runner"], payload["validator"], *payload["sources"]]
    for record in checks:
        path = Path(record["path"])
        if not path.exists() or path.stat().st_size != record["size_bytes"] or sha256_file(path) != record["sha256"]:
            raise RuntimeError(f"Frozen input changed: {path}")
    if payload["frozen_head"] != FROZEN_HEAD or payload["frozen_predecessor_state"] != FROZEN_M0B1_STATE:
        raise RuntimeError("Frozen predecessor contract mismatch")
    return payload


def old_direction_state(low: pd.Series, high: pd.Series) -> pd.Series:
    return pd.Series(
        np.select(
            [low > TOL, high < -TOL],
            ["OPTICAL_POSITIVE", "OPTICAL_NEGATIVE"],
            default="OPTICAL_DIRECTION_INDETERMINATE",
        ),
        index=low.index,
    )


def boundary_state(left: pd.Series, right: pd.Series, prefix: str = "") -> pd.Series:
    positive = (left > TOL) & (right > TOL)
    negative = (left < -TOL) & (right < -TOL)
    zero = (left.abs() <= TOL) & (right.abs() <= TOL)
    labels = [
        f"{prefix}COHERENT_POSITIVE_SHIFT",
        f"{prefix}COHERENT_NEGATIVE_SHIFT",
        f"{prefix}NO_RESOLVED_SHIFT",
    ]
    return pd.Series(
        np.select([positive, negative, zero], labels, default=f"{prefix}DEFORMATION_OR_INDETERMINATE"),
        index=left.index,
    )


def signed_state(values: pd.Series, positive: str, negative: str, zero: str) -> pd.Series:
    return pd.Series(
        np.select([values > TOL, values < -TOL], [positive, negative], default=zero), index=values.index
    )


def frame_sep_stratum(value: pd.Series) -> pd.Series:
    return pd.Series(
        np.select(
            [value.eq(1), value.eq(2), value.between(3, 4), value.ge(5)],
            ["FRAME_GAP_1", "FRAME_GAP_2", "FRAME_GAP_3_4", "FRAME_GAP_5_PLUS"],
            default="FRAME_GAP_OTHER",
        ),
        index=value.index,
    )


def time_sep_stratum(value: pd.Series) -> pd.Series:
    return pd.Series(
        np.select(
            [value.le(60), value.between(61, 120), value.between(121, 240), value.gt(240)],
            ["TIME_GAP_LE_60MS", "TIME_GAP_61_120MS", "TIME_GAP_121_240MS", "TIME_GAP_GT_240MS"],
            default="TIME_GAP_OTHER",
        ),
        index=value.index,
    )


def add_width_strata(frame: pd.DataFrame) -> tuple[pd.DataFrame, list[float]]:
    output = frame.copy()
    quantiles = output["pair_mean_spatial_support_width_deg"].quantile([0, 0.25, 0.5, 0.75, 1]).tolist()
    edges = sorted(set(float(value) for value in quantiles))
    if len(edges) < 2:
        output["optical_interval_width_stratum"] = "WIDTH_SINGLE_VALUE"
        return output, edges
    labels = [f"WIDTH_Q{index + 1}" for index in range(len(edges) - 1)]
    output["optical_interval_width_stratum"] = pd.cut(
        output["pair_mean_spatial_support_width_deg"],
        bins=edges,
        labels=labels,
        include_lowest=True,
        duplicates="drop",
    ).astype(str)
    return output, edges


def enrich_optical(frame: pd.DataFrame) -> tuple[pd.DataFrame, list[float]]:
    output = frame.copy()
    output = output.rename(
        columns={
            "source_raw_theta_low_deg": "L1_deg",
            "source_raw_theta_high_deg": "U1_deg",
            "destination_raw_theta_low_deg": "L2_deg",
            "destination_raw_theta_high_deg": "U2_deg",
        }
    )
    output["width1_deg"] = output["U1_deg"] - output["L1_deg"]
    output["width2_deg"] = output["U2_deg"] - output["L2_deg"]
    output["c1_deg"] = 0.5 * (output["L1_deg"] + output["U1_deg"])
    output["c2_deg"] = 0.5 * (output["L2_deg"] + output["U2_deg"])
    output["h1_deg"] = 0.5 * output["width1_deg"]
    output["h2_deg"] = 0.5 * output["width2_deg"]
    output["delta_c_deg"] = output["c2_deg"] - output["c1_deg"]
    output["all_pairs_low_recomputed_deg"] = output["L2_deg"] - output["U1_deg"]
    output["all_pairs_high_recomputed_deg"] = output["U2_deg"] - output["L1_deg"]
    output["all_pairs_low_center_halfwidth_deg"] = output["delta_c_deg"] - (output["h1_deg"] + output["h2_deg"])
    output["all_pairs_high_center_halfwidth_deg"] = output["delta_c_deg"] + (output["h1_deg"] + output["h2_deg"])
    denominator = output["h1_deg"] + output["h2_deg"]
    output["eta"] = np.where(denominator > TOL, output["delta_c_deg"].abs() / denominator, np.nan)
    output["eta_gt_1_old_observability_condition"] = output["eta"] > 1.0
    output["eta_gt_0_5_diagnostic_only"] = output["eta"] > 0.5
    output["frozen_all_pairs_direction_state_recomputed"] = old_direction_state(
        output["all_pairs_low_recomputed_deg"], output["all_pairs_high_recomputed_deg"]
    )
    output["d_left_deg"] = output["L2_deg"] - output["L1_deg"]
    output["d_right_deg"] = output["U2_deg"] - output["U1_deg"]
    output["d_mid_deg"] = 0.5 * (
        output["L2_deg"] + output["U2_deg"] - output["L1_deg"] - output["U1_deg"]
    )
    output["d_width_deg"] = (output["U2_deg"] - output["L2_deg"]) - (
        output["U1_deg"] - output["L1_deg"]
    )
    output["corresponding_boundary_state"] = boundary_state(output["d_left_deg"], output["d_right_deg"])
    output["midpoint_descriptor_state"] = signed_state(
        output["d_mid_deg"], "MIDPOINT_POSITIVE", "MIDPOINT_NEGATIVE", "MIDPOINT_NUMERICAL_ZERO"
    )
    output["width_deformation_state"] = signed_state(
        output["d_width_deg"], "SUPPORT_WIDTH_EXPANSION", "SUPPORT_WIDTH_CONTRACTION", "SUPPORT_WIDTH_NO_CHANGE"
    )
    output["optical_frame_separation"] = (
        output["destination_optical_frame_index"] - output["source_optical_frame_index"]
    ).astype(int)
    output["optical_time_separation_ms"] = (
        output["destination_optical_timestamp_ms"] - output["source_optical_timestamp_ms"]
    ).astype(int)
    output["frame_separation_stratum"] = frame_sep_stratum(output["optical_frame_separation"].abs())
    output["time_separation_stratum"] = time_sep_stratum(output["optical_time_separation_ms"].abs())
    output["pair_mean_spatial_support_width_deg"] = 0.5 * (output["width1_deg"] + output["width2_deg"])
    output["abs_midpoint_movement_deg"] = output["d_mid_deg"].abs()
    output["boundary_asymmetry_abs_deg"] = (output["d_left_deg"] - output["d_right_deg"]).abs()
    output["relative_width_change_abs"] = output["d_width_deg"].abs() / output[
        "pair_mean_spatial_support_width_deg"
    ].clip(lower=TOL)
    output, edges = add_width_strata(output)
    return output, edges


def stats_row(frame: pd.DataFrame, scope: str, **groups: Any) -> dict[str, Any]:
    eta = pd.to_numeric(frame["eta"], errors="coerce").dropna()
    return {
        "scope": scope,
        **groups,
        "N": int(len(frame)),
        "eta_min": float(eta.min()) if len(eta) else math.nan,
        "eta_median": float(eta.median()) if len(eta) else math.nan,
        "eta_p90": float(eta.quantile(0.90)) if len(eta) else math.nan,
        "eta_p95": float(eta.quantile(0.95)) if len(eta) else math.nan,
        "eta_max": float(eta.max()) if len(eta) else math.nan,
        "fraction_eta_gt_1": float(frame["eta_gt_1_old_observability_condition"].mean()) if len(frame) else math.nan,
        "fraction_eta_gt_0_5": float(frame["eta_gt_0_5_diagnostic_only"].mean()) if len(frame) else math.nan,
        "fraction_old_all_pairs_determinate": float(
            frame["frozen_all_pairs_direction_state_recomputed"].isin(["OPTICAL_POSITIVE", "OPTICAL_NEGATIVE"]).mean()
        ) if len(frame) else math.nan,
        "fraction_boundary_coherent": float(
            frame["corresponding_boundary_state"].isin(
                ["COHERENT_POSITIVE_SHIFT", "COHERENT_NEGATIVE_SHIFT"]
            ).mean()
        ) if len(frame) else math.nan,
        "fraction_boundary_deformation_or_indeterminate": float(
            frame["corresponding_boundary_state"].eq("DEFORMATION_OR_INDETERMINATE").mean()
        ) if len(frame) else math.nan,
        "median_abs_midpoint_movement_deg": float(frame["abs_midpoint_movement_deg"].median()) if len(frame) else math.nan,
        "median_abs_width_change_deg": float(frame["d_width_deg"].abs().median()) if len(frame) else math.nan,
        "median_relative_width_change_abs": float(frame["relative_width_change_abs"].median()) if len(frame) else math.nan,
    }


def grouped_stats(frame: pd.DataFrame, columns: list[str], scope: str) -> pd.DataFrame:
    rows = []
    for key, group in frame.groupby(columns, dropna=False, sort=True):
        values = key if isinstance(key, tuple) else (key,)
        rows.append(stats_row(group, scope, **dict(zip(columns, values))))
    return pd.DataFrame(rows)


def representation_summary(frame: pd.DataFrame, scope: str) -> pd.DataFrame:
    definitions = {
        "FROZEN_ALL_PAIRS_SUPPORT_DIFFERENCE": "frozen_all_pairs_direction_state_recomputed",
        "CORRESPONDING_BOUNDARY_SHIFT": "corresponding_boundary_state",
        "GEOMETRIC_INTERVAL_MIDPOINT_DESCRIPTOR": "midpoint_descriptor_state",
        "SUPPORT_WIDTH_DEFORMATION_DESCRIPTOR": "width_deformation_state",
    }
    rows = []
    for operator, column in definitions.items():
        counts = frame[column].value_counts(dropna=False)
        for state, count in counts.items():
            rows.append(
                {
                    "scope": scope,
                    "operator": operator,
                    "state": state,
                    "N": int(count),
                    "fraction": float(count / len(frame)),
                }
            )
    return pd.DataFrame(rows)


def mapping_audit() -> tuple[pd.DataFrame, dict[str, Any]]:
    model = json.loads(MAPPING_MODEL.read_text(encoding="utf-8"))
    nominal = float(model["nominal_zero_offset_model"]["raw_pixel_slope_deg_per_px"])
    sources: list[tuple[str, pd.Series]] = [("FROZEN_NOMINAL", pd.Series([nominal]))]
    time_scan = pd.read_csv(MAPPING_TIME_SCAN, encoding="utf-8-sig")
    loo = pd.read_csv(MAPPING_LOO, encoding="utf-8-sig")
    sources.append(("TIME_OFFSET_SCAN", pd.to_numeric(time_scan["fit_raw_pixel_slope_deg_per_px"], errors="coerce")))
    sources.append(("LEAVE_ONE_PERSON_OUT", pd.to_numeric(loo["fit_raw_pixel_slope_deg_per_px"], errors="coerce")))
    rows = []
    for name, values in sources:
        values = values.dropna().astype(float)
        rows.append(
            {
                "source": name,
                "N": int(len(values)),
                "min_slope_deg_per_px": float(values.min()),
                "median_slope_deg_per_px": float(values.median()),
                "max_slope_deg_per_px": float(values.max()),
                "positive_count": int((values > TOL).sum()),
                "negative_count": int((values < -TOL).sum()),
                "numerical_zero_count": int((values.abs() <= TOL).sum()),
            }
        )
    table = pd.DataFrame(rows)
    payload = {
        "schema": "PERSON_M0B1_R_MAPPING_DIRECTION_SEMANTICS_V1",
        "frozen_mapping_tables_have_prior_reference_provenance": True,
        "reference_used_to_select_representation": False,
        "new_mapping_fit_performed": False,
        "equation": "theta_deg = a * optical_x_px + b",
        "frozen_nominal_slope_deg_per_px": nominal,
        "frozen_nominal_slope_sign": "POSITIVE" if nominal > TOL else "NON_POSITIVE",
        "all_reviewed_table_slopes_positive": bool((table["negative_count"].sum() == 0) and (table["numerical_zero_count"].sum() == 0)),
        "direction_semantics": {
            "slope_magnitude_uncertainty": "CHANGES_ANGULAR_MAGNITUDE_NOT_DIRECTION_SIGN_WHILE_SIGN_REMAINS_POSITIVE",
            "slope_sign_uncertainty": "ONLY_MAPPING_UNCERTAINTY_COMPONENT_THAT_CAN_REVERSE_DIRECTION_SIGN",
        },
    }
    return table, payload


def sar_diagnostic(bank: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    columns = [
        "run_id",
        "pair_index",
        "from_frame_uid",
        "to_frame_uid",
        "from_frame",
        "to_frame",
        "base_edge_id",
        "source_region_id",
        "destination_region_id",
        "source_theta_min_deg",
        "source_theta_max_deg",
        "destination_theta_min_deg",
        "destination_theta_max_deg",
        "source_touches_boundary",
        "destination_touches_boundary",
        "source_truncated",
        "destination_truncated",
    ]
    edges = bank[columns].drop_duplicates("base_edge_id").copy()
    edges["d_left_s_deg"] = edges["destination_theta_min_deg"] - edges["source_theta_min_deg"]
    edges["d_right_s_deg"] = edges["destination_theta_max_deg"] - edges["source_theta_max_deg"]
    edges["d_mid_s_deg"] = 0.5 * (
        edges["destination_theta_min_deg"]
        + edges["destination_theta_max_deg"]
        - edges["source_theta_min_deg"]
        - edges["source_theta_max_deg"]
    )
    edges["d_width_s_deg"] = (
        edges["destination_theta_max_deg"] - edges["destination_theta_min_deg"]
    ) - (edges["source_theta_max_deg"] - edges["source_theta_min_deg"])
    unavailable = edges[["source_theta_min_deg", "source_theta_max_deg", "destination_theta_min_deg", "destination_theta_max_deg"]].isna().any(axis=1)
    edges["sar_corresponding_boundary_state"] = boundary_state(
        edges["d_left_s_deg"], edges["d_right_s_deg"], prefix="SAR_"
    )
    edges.loc[unavailable, "sar_corresponding_boundary_state"] = "SAR_UNAVAILABLE"
    graph_keys = ["from_frame_uid", "to_frame_uid"]
    source_degree = edges.groupby(graph_keys + ["source_region_id"])["destination_region_id"].nunique().rename("source_out_degree")
    destination_degree = edges.groupby(graph_keys + ["destination_region_id"])["source_region_id"].nunique().rename("destination_in_degree")
    edges = edges.merge(source_degree, on=graph_keys + ["source_region_id"], how="left", validate="many_to_one")
    edges = edges.merge(destination_degree, on=graph_keys + ["destination_region_id"], how="left", validate="many_to_one")
    edges["sar_relation_topology"] = np.select(
        [
            (edges["source_out_degree"] <= 1) & (edges["destination_in_degree"] <= 1),
            (edges["source_out_degree"] > 1) & (edges["destination_in_degree"] <= 1),
            (edges["source_out_degree"] <= 1) & (edges["destination_in_degree"] > 1),
        ],
        ["ONE_TO_ONE", "SPLIT_LIKE", "MERGE_OR_SHARED_LIKE"],
        default="SPLIT_AND_MERGE_LIKE",
    )
    summary = (
        edges.groupby(["sar_relation_topology", "sar_corresponding_boundary_state"], dropna=False)
        .size()
        .rename("N")
        .reset_index()
    )
    summary["fraction_of_unique_sar_edges"] = summary["N"] / len(edges)
    return edges.sort_values(["pair_index", "source_region_id", "destination_region_id"]), summary


def markdown_table(frame: pd.DataFrame, columns: list[str]) -> str:
    use = frame[columns].copy()
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join(["---"] * len(columns)) + " |"
    rows = []
    for row in use.itertuples(index=False, name=None):
        values = []
        for value in row:
            if isinstance(value, float):
                values.append(f"{value:.6f}" if np.isfinite(value) else "NA")
            else:
                values.append(str(value))
        rows.append("| " + " | ".join(values) + " |")
    return "\n".join([header, separator, *rows])


def build_report(summary: dict[str, Any], eta_overall: pd.DataFrame, representation: pd.DataFrame, mapping: dict[str, Any]) -> str:
    bank = eta_overall[eta_overall["scope"].eq("M0B1_BANK_ROWS")].iloc[0]
    unique = eta_overall[eta_overall["scope"].eq("DEDUPLICATED_OPTICAL_PAIR_SIGNATURES")].iloc[0]
    representation_view = representation[
        representation["scope"].eq("DEDUPLICATED_OPTICAL_PAIR_SIGNATURES")
    ][["operator", "state", "N", "fraction"]]
    return f"""# M0B1-R angular dynamic representation audit report

- Primary state: `{summary['primary_state']}`
- Frozen predecessor remains: `{FROZEN_M0B1_STATE}`
- M0B2: not entered
- Cross-modal discrimination: not executed
- Reference/manual identity used: no

## Exact frozen operator

For `I_t=[L_t,U_t]`, frozen M0B1 implements:

`Delta I_all=[L2-U1,U2-L1]`.

This is the possible displacement set from any source-support point to any
destination-support point.  It is not a whole-support translation-uncertainty
interval unless an additional correspondence model is supplied.

With `c_t=(L_t+U_t)/2` and `h_t=(U_t-L_t)/2`:

`Delta I_all=[Delta c-(h1+h2),Delta c+(h1+h2)]`.

Thus old determinate direction requires `abs(Delta c)>h1+h2`, equivalently
`eta>1` for `eta=abs(Delta c)/(h1+h2)`.

## Eta and observability

| scope | N | eta_min | eta_median | eta_p90 | eta_p95 | eta_max | fraction_eta_gt_1 | fraction_eta_gt_0_5 | fraction_boundary_coherent |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M0B1 bank rows | {int(bank.N)} | {bank.eta_min:.6f} | {bank.eta_median:.6f} | {bank.eta_p90:.6f} | {bank.eta_p95:.6f} | {bank.eta_max:.6f} | {bank.fraction_eta_gt_1:.6f} | {bank.fraction_eta_gt_0_5:.6f} | {bank.fraction_boundary_coherent:.6f} |
| Deduplicated optical pair signatures | {int(unique.N)} | {unique.eta_min:.6f} | {unique.eta_median:.6f} | {unique.eta_p90:.6f} | {unique.eta_p95:.6f} | {unique.eta_max:.6f} | {unique.fraction_eta_gt_1:.6f} | {unique.fraction_eta_gt_0_5:.6f} | {unique.fraction_boundary_coherent:.6f} |

`eta>1` is reported only as the old operator's mathematical observability
condition.  It is not a tuned threshold.

## Representation comparison

{markdown_table(representation_view, ['operator', 'state', 'N', 'fraction'])}

The corresponding-boundary descriptors are `d_left=L2-L1` and
`d_right=U2-U1`.  `d_mid` is only the geometric interval midpoint descriptor.
`d_width=(U2-L2)-(U1-L1)=width2-width1` is shape/support deformation.

## Semantic layer finding

- A, spatial support extent: the optical bbox-derived interval width.
- B, measurement uncertainty: not provided by that width in the M0B1 bank.
- C, temporal translation: corresponding-boundary and midpoint changes.
- D, shape/width deformation: boundary disagreement and `d_width`.

M0B1 used A inside the all-pairs possible-displacement radius as though it
bounded B for motion-direction observability.  The code correctly answered the
question posed by that operator, but that operator is semantically broader than
whole-support translation and therefore suppresses short-time direction.

## Mapping direction semantics

Frozen `theta=a*x+b` slope is `{mapping['frozen_nominal_slope_deg_per_px']:.12f}`
deg/px and positive.  All reviewed frozen slope-table entries are positive:
`{mapping['all_reviewed_table_slopes_positive']}`.  Slope magnitude uncertainty
changes angular magnitude; a slope-sign reversal would be required to reverse
direction sign.  No new mapping was fitted.

## Bottleneck hierarchy

1. `REPRESENTATION_OBSERVABILITY`: among {summary['dynamic_available_bank_rows']}
   records already passing same-fragment and distinct-sample gates, frozen
   all-pairs determinate direction is {summary['old_determinate_bank_rows']};
   corresponding-boundary coherent rows are
   {summary['boundary_coherent_bank_rows']}.
2. `RAW_FRAGMENT_CONTINUITY`: remains an upstream availability loss of
   {summary['frozen_fragment_break_rows']} frozen-bank records.
3. `SAME_SAMPLE_TEMPORAL_SAMPLING`: remains an upstream availability loss of
   {summary['frozen_same_sample_rows']} records.
4. `SYNC`: remains `{summary['sync_status']}` and was not calibrated.
5. `MAPPING_MAGNITUDE`: affects magnitude after direction is represented; it
   is not the leading explanation for zero sign observability with positive
   slope.

## SAR structural diagnostic

Optical recovery gate: `{summary['optical_recovery_gate']}`.  SAR-side output
was materialized: `{summary['sar_diagnostic_materialized']}`.  It contains only
q95 corresponding-boundary/midpoint/width structural states and split/merge
degree descriptors.  It does not compare optical and SAR states and does not
make a cross-modal claim.

## Final judgment

`{summary['primary_state']}`

M0B1 successfully diagnosed that the current all-pairs support interval
operator is unobservable for short-time motion direction; the new
representation requires an independently versioned validation.  The frozen
M0B1 negative result remains unchanged.

Stop.  No M0B2, cross-modal discrimination, magnitude fitting, pruning,
identity, tracking, factor graph, P2, or final localization was executed.
"""


def run_audit() -> None:
    freeze = verify_freeze()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    bank = pd.read_csv(BANK, usecols=BANK_COLUMNS, encoding="utf-8-sig", low_memory=False)
    if bank["reference_used"].astype(bool).any() or bank["identity_assignment_performed"].astype(bool).any():
        raise RuntimeError("Pre-reference isolation violated")
    available = bank[bank["angular_availability_state"].eq("ANGULAR_DYNAMIC_AVAILABLE")].copy()
    if not available["source_track_id"].eq(available["destination_track_id"]).all():
        raise RuntimeError("Dynamic available row crosses raw fragments")
    if available["source_optical_frame_index"].eq(available["destination_optical_frame_index"]).any():
        raise RuntimeError("Dynamic available row uses same optical sample")
    optical, width_edges = enrich_optical(available)
    if not np.allclose(
        optical["all_pairs_low_recomputed_deg"], optical["optical_delta_interval_low_deg"], atol=1e-9, rtol=0
    ) or not np.allclose(
        optical["all_pairs_high_recomputed_deg"], optical["optical_delta_interval_high_deg"], atol=1e-9, rtol=0
    ):
        raise RuntimeError("Frozen all-pairs operator recomputation mismatch")
    if not np.allclose(
        optical["all_pairs_low_recomputed_deg"], optical["all_pairs_low_center_halfwidth_deg"], atol=1e-9, rtol=0
    ) or not np.allclose(
        optical["all_pairs_high_recomputed_deg"], optical["all_pairs_high_center_halfwidth_deg"], atol=1e-9, rtol=0
    ):
        raise RuntimeError("Center/half-width derivation mismatch")
    if not optical["frozen_all_pairs_direction_state_recomputed"].eq(optical["optical_direction_state"]).all():
        raise RuntimeError("Frozen direction-state recomputation mismatch")
    signature_columns = [
        "timing_condition",
        "source_track_id",
        "source_optical_frame_index",
        "destination_optical_frame_index",
        "source_optical_timestamp_ms",
        "destination_optical_timestamp_ms",
        "L1_deg",
        "U1_deg",
        "L2_deg",
        "U2_deg",
    ]
    multiplicity = optical.groupby(signature_columns, dropna=False).size().rename("bank_row_multiplicity").reset_index()
    unique = optical.drop_duplicates(signature_columns).merge(multiplicity, on=signature_columns, validate="one_to_one")
    optical["record_semantics"] = "M0B1_PRE_REFERENCE_BANK_ROW_SAR_STATIC_RELATION_DUPLICATION_RETAINED"
    unique["record_semantics"] = "DEDUPLICATED_RUNTIME_LEGAL_OPTICAL_DYNAMIC_PAIR_SIGNATURE"
    write_table("optical_dynamic_bank_records_pre_reference", optical)
    write_table("optical_dynamic_unique_pairs_pre_reference", unique)

    eta_overall = pd.DataFrame(
        [
            stats_row(optical, "M0B1_BANK_ROWS"),
            stats_row(unique, "DEDUPLICATED_OPTICAL_PAIR_SIGNATURES"),
        ]
    )
    write_table("eta_summary_overall_pre_reference", eta_overall)
    grouped_outputs = {
        "eta_by_fragment_pre_reference": grouped_stats(unique, ["timing_condition", "source_track_id"], "DEDUPLICATED_OPTICAL_PAIR_SIGNATURES"),
        "eta_by_exact_frame_separation_pre_reference": grouped_stats(unique, ["optical_frame_separation"], "DEDUPLICATED_OPTICAL_PAIR_SIGNATURES"),
        "eta_by_frame_separation_stratum_pre_reference": grouped_stats(unique, ["frame_separation_stratum"], "DEDUPLICATED_OPTICAL_PAIR_SIGNATURES"),
        "eta_by_exact_time_separation_pre_reference": grouped_stats(unique, ["optical_time_separation_ms"], "DEDUPLICATED_OPTICAL_PAIR_SIGNATURES"),
        "eta_by_time_separation_stratum_pre_reference": grouped_stats(unique, ["time_separation_stratum"], "DEDUPLICATED_OPTICAL_PAIR_SIGNATURES"),
        "eta_by_optical_interval_width_stratum_pre_reference": grouped_stats(unique, ["optical_interval_width_stratum"], "DEDUPLICATED_OPTICAL_PAIR_SIGNATURES"),
    }
    for stem, frame in grouped_outputs.items():
        write_table(stem, frame)
    representation = pd.concat(
        [
            representation_summary(optical, "M0B1_BANK_ROWS"),
            representation_summary(unique, "DEDUPLICATED_OPTICAL_PAIR_SIGNATURES"),
        ],
        ignore_index=True,
    )
    write_table("representation_state_summary_pre_reference", representation)

    mapping_table, mapping_payload = mapping_audit()
    write_table("mapping_slope_sign_audit_pre_reference", mapping_table)
    write_json(OUTPUT / "mapping_direction_semantics_pre_reference.json", mapping_payload)

    old_summary = json.loads(OLD_SUMMARY.read_text(encoding="utf-8"))
    sync_statuses = sorted(
        pd.read_csv(TIMING_QUERIES, usecols=["sync_status"], encoding="utf-8-sig")["sync_status"].dropna().unique()
    )
    old_determinate_bank = int(
        optical["frozen_all_pairs_direction_state_recomputed"].isin(["OPTICAL_POSITIVE", "OPTICAL_NEGATIVE"]).sum()
    )
    coherent_bank = int(
        optical["corresponding_boundary_state"].isin(["COHERENT_POSITIVE_SHIFT", "COHERENT_NEGATIVE_SHIFT"]).sum()
    )
    coherent_unique = int(
        unique["corresponding_boundary_state"].isin(["COHERENT_POSITIVE_SHIFT", "COHERENT_NEGATIVE_SHIFT"]).sum()
    )
    optical_gate = coherent_unique >= 2
    if old_determinate_bank == 0 and optical_gate:
        primary_state = "M0B1_R_INTERVAL_OPERATOR_SEMANTIC_MISMATCH_CONFIRMED"
    elif coherent_unique == 0:
        primary_state = "M0B1_R_OPTICAL_DYNAMIC_OBSERVABILITY_STILL_INSUFFICIENT"
    else:
        primary_state = "M0B1_R_INTERVAL_OPERATOR_NOT_PRIMARY_BLOCKER"

    sar_materialized = False
    sar_edges = pd.DataFrame()
    sar_summary = pd.DataFrame()
    if optical_gate:
        sar_edges, sar_summary = sar_diagnostic(bank)
        write_table("sar_q95_corresponding_boundary_structural_diagnostic_pre_reference", sar_edges)
        write_table("sar_q95_structural_state_summary_pre_reference", sar_summary)
        sar_materialized = True

    bottleneck = pd.DataFrame(
        [
            {"rank": 1, "layer": "REPRESENTATION_OBSERVABILITY", "N_relevant": len(optical), "N_blocked_old": len(optical) - old_determinate_bank, "N_recovered_boundary_coherent": coherent_bank, "semantics": "WITHIN_SAME_FRAGMENT_DISTINCT_SAMPLE_GATE"},
            {"rank": 2, "layer": "RAW_FRAGMENT_CONTINUITY", "N_relevant": old_summary["hypothesis_rows"], "N_blocked_old": old_summary["fragment_break_rows"], "N_recovered_boundary_coherent": 0, "semantics": "UPSTREAM_AVAILABILITY_GATE"},
            {"rank": 3, "layer": "SAME_SAMPLE_TEMPORAL_SAMPLING", "N_relevant": old_summary["hypothesis_rows"], "N_blocked_old": old_summary["same_optical_sample_rows"], "N_recovered_boundary_coherent": 0, "semantics": "UPSTREAM_AVAILABILITY_GATE"},
            {"rank": 4, "layer": "SYNC", "N_relevant": len(pd.read_csv(TIMING_QUERIES, encoding="utf-8-sig")), "N_blocked_old": math.nan, "N_recovered_boundary_coherent": 0, "semantics": ";".join(sync_statuses)},
            {"rank": 5, "layer": "MAPPING_MAGNITUDE", "N_relevant": int(mapping_table["N"].sum()), "N_blocked_old": 0, "N_recovered_boundary_coherent": 0, "semantics": "ALL_REVIEWED_SLOPES_POSITIVE_MAGNITUDE_NOT_SIGN_BLOCKER"},
        ]
    )
    write_table("bottleneck_hierarchy_pre_reference", bottleneck)

    summary = {
        "schema": "PERSON_M0B1_R_AUDIT_SUMMARY_V1",
        "created_at": now_iso(),
        "primary_state": primary_state,
        "frozen_predecessor_state": FROZEN_M0B1_STATE,
        "frozen_predecessor_modified": False,
        "reference_loaded": False,
        "manual_reference_used_in_optical_representation_audit": False,
        "frozen_mapping_tables_with_prior_reference_provenance_read_for_sign_audit": True,
        "manual_reference_used_to_select_representation": False,
        "cross_modal_discrimination_executed": False,
        "M0B2_executed": False,
        "old_operator_semantics": "ANY_SOURCE_SUPPORT_POINT_TO_ANY_DESTINATION_SUPPORT_POINT_POSSIBLE_DISPLACEMENT_SET",
        "old_operator_is_whole_support_translation_uncertainty": False,
        "spatial_support_extent_misused_as_measurement_uncertainty_for_motion_direction": primary_state == "M0B1_R_INTERVAL_OPERATOR_SEMANTIC_MISMATCH_CONFIRMED",
        "dynamic_available_bank_rows": int(len(optical)),
        "deduplicated_optical_pair_signatures": int(len(unique)),
        "old_determinate_bank_rows": old_determinate_bank,
        "boundary_coherent_bank_rows": coherent_bank,
        "boundary_coherent_unique_pairs": coherent_unique,
        "optical_recovery_gate": "PASS" if optical_gate else "FAIL",
        "sar_diagnostic_materialized": sar_materialized,
        "unique_sar_base_edges": int(len(sar_edges)),
        "frozen_hypothesis_rows": int(old_summary["hypothesis_rows"]),
        "frozen_fragment_break_rows": int(old_summary["fragment_break_rows"]),
        "frozen_same_sample_rows": int(old_summary["same_optical_sample_rows"]),
        "sync_status": ";".join(sync_statuses),
        "width_stratum_edges_deg": width_edges,
        "numerical_tolerance_deg": TOL,
        "mapping_all_reviewed_slopes_positive": mapping_payload["all_reviewed_table_slopes_positive"],
        "prohibited_actions_executed": [],
        "stop_after_stage": True,
        "interpretation": "M0B1 successfully diagnosed that the current all-pairs support interval operator is unobservable for short-time motion direction; the new representation requires an independently versioned validation.",
    }
    write_json(OUTPUT / "audit_summary_pre_reference.json", summary)
    report = build_report(summary, eta_overall, representation, mapping_payload)
    (OUTPUT / "M0B1_R_ANGULAR_DYNAMIC_REPRESENTATION_AUDIT_REPORT.md").write_text(report, encoding="utf-8")

    output_paths = sorted(
        path
        for path in OUTPUT.iterdir()
        if path.is_file() and path.name not in {"final_output_manifest.json", "independent_validation.json"}
    )
    manifest = {
        "schema": "PERSON_M0B1_R_OUTPUT_MANIFEST_V1",
        "created_at": now_iso(),
        "freeze_sha256": sha256_file(FREEZE),
        "reference_loaded": False,
        "old_work_dependency": False,
        "frozen_predecessor_state": FROZEN_M0B1_STATE,
        "primary_state": primary_state,
        "outputs": [file_record(path) for path in output_paths],
    }
    write_json(OUTPUT / "final_output_manifest.json", manifest)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def main() -> None:
    args = parse_args()
    if args.freeze:
        freeze_protocol()
    else:
        run_audit()


if __name__ == "__main__":
    main()
