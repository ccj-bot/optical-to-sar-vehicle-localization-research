"""Post-hoc C5-vs-v1 rank1 equivalence audit.

This script reads evaluation outputs only. It does not read A001/A005/A019/A021,
does not generate a ranking, and does not modify candidate data.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


WORKSPACE = Path(__file__).resolve().parents[1]
V1_EVAL = WORKSPACE / "output/gm17_phase4_minimal_factor_pilot_20260628_110447/evaluation_per_target.csv"
COMBINED_EVAL = (
    WORKSPACE
    / "output/gm17_phase4_combined_structure_temporal_fixed_pilot_20260628_224407/evaluation_combined_per_target_by_variant.csv"
)
SUMMARY_DIR = WORKSPACE / "docs"
KEYS = ["target_identity", "scene", "sar_frame_num", "gm17_track_id"]
GEOM = ["cx", "cy", "w", "h"]
GEOMETRY_ATOL = 1e-9


def read_v1() -> pd.DataFrame:
    cols = KEYS + [
        "candidate_id",
        "cx",
        "cy",
        "w",
        "h",
        "center_error",
        "axis_aligned_proxy_iou",
        "best_proxy_candidate_id",
        "best_proxy_pilot_rank",
    ]
    out = pd.read_csv(V1_EVAL, usecols=cols)
    out["v1_rank1_is_best_proxy"] = out["candidate_id"].astype(str) == out["best_proxy_candidate_id"].astype(str)
    return out.rename(
        columns={
            "candidate_id": "v1_candidate_id",
            "cx": "v1_cx",
            "cy": "v1_cy",
            "w": "v1_w",
            "h": "v1_h",
            "center_error": "v1_center_error",
            "axis_aligned_proxy_iou": "v1_axis_aligned_proxy_iou",
            "best_proxy_candidate_id": "v1_best_proxy_candidate_id",
            "best_proxy_pilot_rank": "v1_best_proxy_rank",
        }
    )


def read_c5() -> pd.DataFrame:
    cols = KEYS + [
        "variant",
        "candidate_id",
        "cx",
        "cy",
        "w",
        "h",
        "center_error",
        "axis_aligned_proxy_iou",
        "best_proxy_candidate_id",
        "best_proxy_rank",
        "rank1_is_best_proxy",
    ]
    all_rows = pd.read_csv(COMBINED_EVAL, usecols=cols)
    out = all_rows.loc[all_rows["variant"].astype(str).str.lower() == "c5"].copy()
    out["c5_rank1_is_best_proxy"] = out["rank1_is_best_proxy"].astype(bool)
    return out.drop(columns=["variant", "rank1_is_best_proxy"]).rename(
        columns={
            "candidate_id": "c5_candidate_id",
            "cx": "c5_cx",
            "cy": "c5_cy",
            "w": "c5_w",
            "h": "c5_h",
            "center_error": "c5_center_error",
            "axis_aligned_proxy_iou": "c5_axis_aligned_proxy_iou",
            "best_proxy_candidate_id": "c5_best_proxy_candidate_id",
            "best_proxy_rank": "c5_best_proxy_rank",
        }
    )


def fmt_rate(value: float) -> str:
    return f"{value:.4f}"


def markdown_bool(value: bool) -> str:
    return "yes" if bool(value) else "no"


def frame_to_markdown(df: pd.DataFrame) -> str:
    columns = list(df.columns)
    rows = []
    rows.append("| " + " | ".join(columns) + " |")
    rows.append("| " + " | ".join(["---"] * len(columns)) + " |")
    for _, row in df.iterrows():
        values = []
        for col in columns:
            value = row[col]
            if isinstance(value, (bool, np.bool_)):
                values.append(markdown_bool(bool(value)))
            else:
                values.append(str(value))
        rows.append("| " + " | ".join(values) + " |")
    return "\n".join(rows)


def main() -> None:
    if not V1_EVAL.exists():
        raise FileNotFoundError(V1_EVAL)
    if not COMBINED_EVAL.exists():
        raise FileNotFoundError(COMBINED_EVAL)

    v1 = read_v1()
    c5 = read_c5()
    if v1.duplicated(KEYS).any():
        raise ValueError("v1 evaluation has duplicate target keys")
    if c5.duplicated(KEYS).any():
        raise ValueError("combined C5 evaluation has duplicate target keys")

    joined = v1.merge(c5, on=KEYS, how="outer", indicator=True)
    matched = joined.loc[joined["_merge"] == "both"].copy()
    if len(matched) != len(v1) or len(matched) != len(c5):
        raise ValueError(
            f"target key mismatch: v1={len(v1)}, c5={len(c5)}, matched={len(matched)}, "
            f"merge_counts={joined['_merge'].value_counts().to_dict()}"
        )

    matched["same_candidate_id"] = matched["v1_candidate_id"].astype(str) == matched["c5_candidate_id"].astype(str)
    geom_checks = []
    for col in GEOM:
        geom_checks.append(
            np.isclose(
                matched[f"v1_{col}"].astype(float),
                matched[f"c5_{col}"].astype(float),
                rtol=0.0,
                atol=GEOMETRY_ATOL,
                equal_nan=False,
            )
        )
    matched["same_geometry"] = np.logical_and.reduce(geom_checks)
    matched["same_center_error"] = np.isclose(
        matched["v1_center_error"].astype(float),
        matched["c5_center_error"].astype(float),
        rtol=0.0,
        atol=GEOMETRY_ATOL,
        equal_nan=False,
    )
    matched["same_axis_aligned_proxy_iou"] = np.isclose(
        matched["v1_axis_aligned_proxy_iou"].astype(float),
        matched["c5_axis_aligned_proxy_iou"].astype(float),
        rtol=0.0,
        atol=GEOMETRY_ATOL,
        equal_nan=False,
    )
    matched["different_id_same_geometry"] = (~matched["same_candidate_id"]) & matched["same_geometry"]
    matched["same_best_proxy_candidate_id"] = (
        matched["v1_best_proxy_candidate_id"].astype(str) == matched["c5_best_proxy_candidate_id"].astype(str)
    )
    matched["rank1_best_proxy_changed"] = (
        matched["v1_rank1_is_best_proxy"].astype(bool) != matched["c5_rank1_is_best_proxy"].astype(bool)
    )

    n = len(matched)
    same_candidate_id_count = int(matched["same_candidate_id"].sum())
    same_geometry_count = int(matched["same_geometry"].sum())
    different_id_same_geometry_count = int(matched["different_id_same_geometry"].sum())
    same_best_proxy_candidate_id_count = int(matched["same_best_proxy_candidate_id"].sum())
    rank1_best_proxy_changed_count = int(matched["rank1_best_proxy_changed"].sum())

    v1_rank1_best_proxy_rate = float(matched["v1_rank1_is_best_proxy"].mean())
    c5_rank1_best_proxy_rate = float(matched["c5_rank1_is_best_proxy"].mean())

    diff_examples = matched.loc[
        ~matched["same_candidate_id"],
        KEYS
        + [
            "v1_candidate_id",
            "c5_candidate_id",
            "same_geometry",
            "v1_rank1_is_best_proxy",
            "c5_rank1_is_best_proxy",
            "v1_best_proxy_rank",
            "c5_best_proxy_rank",
        ],
    ].head(10)
    best_proxy_changed_examples = matched.loc[
        matched["rank1_best_proxy_changed"],
        KEYS
        + [
            "v1_candidate_id",
            "c5_candidate_id",
            "v1_best_proxy_candidate_id",
            "c5_best_proxy_candidate_id",
            "v1_best_proxy_rank",
            "c5_best_proxy_rank",
            "v1_rank1_is_best_proxy",
            "c5_rank1_is_best_proxy",
        ],
    ].head(10)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary_path = SUMMARY_DIR / f"gm17_phase4_c5_v1_temporal_baseline_equivalence_audit_summary_{timestamp}.md"
    lines = [
        f"# GM17 Phase4 C5-vs-v1 Temporal Baseline Equivalence Audit {timestamp}",
        "",
        "## Current Position",
        "",
        "This is a post-hoc sanity check explaining why C5 and v1 can have identical rank1 center/IoU metrics while `rank1_is_best_proxy` differs.",
        "",
        "It does not generate a new ranking, tune a threshold, train a model, calibrate weights, or modify A001/A005/A019/A021.",
        "",
        "## Inputs",
        "",
        f"- v1 evaluation: `{V1_EVAL.relative_to(WORKSPACE)}`",
        f"- combined evaluation: `{COMBINED_EVAL.relative_to(WORKSPACE)}`",
        "- combined variant audited: `c5`",
        "",
        "## Method",
        "",
        "- Join v1 rank1 rows and combined C5 rank1 rows by `target_identity + scene + sar_frame_num + gm17_track_id`.",
        "- Compare rank1 `candidate_id`.",
        "- When IDs differ, compare selected box geometry using `cx/cy/w/h` with a numeric serialization tolerance of `1e-9`.",
        "- Compare post-hoc `rank1_is_best_proxy` identity status only for explanation.",
        "",
        "## Results",
        "",
        f"- matched target groups: `{n}`",
        f"- same candidate_id count: `{same_candidate_id_count}`",
        f"- same_candidate_id_rate: `{fmt_rate(same_candidate_id_count / n)}`",
        f"- same geometry count: `{same_geometry_count}`",
        f"- same_geometry_rate: `{fmt_rate(same_geometry_count / n)}`",
        f"- different_id_same_geometry_count: `{different_id_same_geometry_count}`",
        f"- same center_error count: `{int(matched['same_center_error'].sum())}`",
        f"- same axis_aligned_proxy_iou count: `{int(matched['same_axis_aligned_proxy_iou'].sum())}`",
        f"- same best_proxy_candidate_id count: `{same_best_proxy_candidate_id_count}`",
        f"- same best_proxy_candidate_id rate: `{fmt_rate(same_best_proxy_candidate_id_count / n)}`",
        f"- v1 rank1_is_best_proxy rate: `{fmt_rate(v1_rank1_best_proxy_rate)}`",
        f"- C5 rank1_is_best_proxy rate: `{fmt_rate(c5_rank1_best_proxy_rate)}`",
        f"- rank1_is_best_proxy changed count: `{rank1_best_proxy_changed_count}`",
        "",
        "## Interpretation",
        "",
    ]
    if same_candidate_id_count == n and same_geometry_count == n and rank1_best_proxy_changed_count > 0:
        lines.extend(
            [
                "C5 and v1 select the same rank1 `candidate_id` and the same `cx/cy/w/h` geometry for every target.",
                "",
                "Therefore the identical center error and axis-aligned proxy IoU are expected: the selected rank1 box is the same. The `rank1_is_best_proxy` difference is not caused by a different C5 selected candidate. It comes from post-hoc best-proxy identity accounting in the evaluation outputs: for the changed rows, the C5 evaluation marks the same rank1 candidate as the best-proxy identity while the v1 evaluation records a different best-proxy candidate ID.",
            ]
        )
    elif same_geometry_count == n and same_candidate_id_count < n:
        lines.extend(
            [
                "C5 and v1 select the same `cx/cy/w/h` geometry for every target, but not always the same `candidate_id`.",
                "",
                "Therefore center error and axis-aligned proxy IoU can be identical, because those metrics depend on the selected box geometry. `rank1_is_best_proxy` can differ because it is candidate-ID based: two candidate IDs can carry the same selected geometry while only one ID matches the post-hoc best-proxy identity.",
            ]
        )
    elif same_geometry_count == n:
        lines.extend(
            [
                "C5 and v1 select the same rank1 geometry for every target. Any identity metric difference should be interpreted as candidate-ID accounting rather than geometric localization change.",
            ]
        )
    else:
        lines.extend(
            [
                "C5 and v1 do not select identical geometry for every target. The rank1 center/IoU equivalence should be reviewed target-by-target before interpreting the identity metric gap.",
            ]
        )
    lines.extend(
        [
            "",
            "## Different-ID Examples",
            "",
        ]
    )
    if diff_examples.empty:
        lines.append("No different-ID examples were found.")
    else:
        lines.append(frame_to_markdown(diff_examples))
    lines.extend(
        [
            "",
            "## Rank1 Best-Proxy Changed Examples",
            "",
        ]
    )
    if best_proxy_changed_examples.empty:
        lines.append("No rank1 best-proxy status changes were found.")
    else:
        lines.append(frame_to_markdown(best_proxy_changed_examples))
    lines.extend(
        [
            "",
            "## Boundary Statement",
            "",
            "- This audit reads only completed evaluation outputs.",
            "- It does not read A001, A005, A019, or A021 directly.",
            "- It does not create, filter, move, or re-rank candidates.",
            "- It does not change any Phase4C rule.",
        ]
    )
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(summary_path)


if __name__ == "__main__":
    main()
