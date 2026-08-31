from __future__ import annotations

import hashlib
import json
import math
import shutil
import zipfile
from pathlib import Path

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


WORKSPACE = Path(r"D:\profile\research\workspace")
TASK = WORKSPACE / "tasks" / "person_r02_static_scene_skeleton_20260831"
OUT = WORKSPACE / "output" / "person_r02_static_scene_skeleton_20260831"
PRE = OUT / "pre_reference"
FIG = OUT / "figures"
PACK = WORKSPACE / "review_packs" / "PERSON_R02_STATIC_SCENE_SKELETON_REVIEW_PACK_20260831.zip"
RAW_OPT = Path(
    r"C:\research_raw\optical_sar_data\20260721data\derived_frames"
    r"\pseudocolor_labelstudio_prep_20260722\frames\optical\R02ZF"
)
RAW_SAR = Path(
    r"C:\research_raw\optical_sar_data\20260721data\derived_frames"
    r"\pseudocolor_labelstudio_prep_20260722\frames\sar_pseudocolor\R02ZF"
)
OPT_F120 = RAW_OPT / "frame_000120_t006667ms.jpg"
SAR_F200 = RAW_SAR / "frame_000200_t006667ms.jpg"

PACK_CODE_NAMES = {
    "analyze_static_boundaries.py",
    "analyze_visual_tree_anchors.py",
    "build_static_scene_skeleton_outputs.py",
    "prepare_synchronized_review.py",
    "validate_static_scene_skeleton.py",
}
EXCLUDED_PRE_REFERENCE_PREFIXES = (
    "static_landmark_",
    "visual_static_landmark_",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_bgr(path: Path) -> np.ndarray:
    image = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(path)
    return image


def annotate_optical() -> np.ndarray:
    image = read_bgr(OPT_F120)
    overlay = image.copy()
    boundary_a = np.array([[0, 1280], [1024, 1270], [2048, 1280], [3072, 1290], [4095, 1300]], np.int32)
    boundary_b = np.array([[0, 1085], [1024, 1075], [2048, 1080], [3072, 1090], [4095, 1105]], np.int32)
    cv2.polylines(overlay, [boundary_a], False, (255, 255, 0), 10, cv2.LINE_AA)
    cv2.polylines(overlay, [boundary_b], False, (0, 165, 255), 10, cv2.LINE_AA)
    cv2.putText(overlay, "OPTICAL EDGE HYPOTHESIS A (road-side curb)", (80, 1240), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (255, 255, 0), 4, cv2.LINE_AA)
    cv2.putText(overlay, "OPTICAL EDGE HYPOTHESIS B (rear sidewalk/planting edge)", (80, 1040), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 165, 255), 4, cv2.LINE_AA)
    tree_x = 1706
    cv2.line(overlay, (tree_x, 140), (tree_x, 970), (0, 255, 0), 10, cv2.LINE_AA)
    cv2.circle(overlay, (tree_x, 660), 55, (0, 255, 0), 10, cv2.LINE_AA)
    cv2.putText(overlay, "TREE A visual axis x=1706 px", (tree_x + 40, 210), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 255, 0), 4, cv2.LINE_AA)
    cv2.rectangle(overlay, (0, 0), (4095, 105), (0, 0, 0), -1)
    cv2.putText(overlay, "OPT F120  t=006667ms  | topology/visual identity only", (40, 72), cv2.FONT_HERSHEY_SIMPLEX, 1.45, (255, 255, 255), 4, cv2.LINE_AA)
    return overlay


def annotate_sar() -> np.ndarray:
    image = read_bgr(SAR_F200)
    overlay = image.copy()
    curves = pd.read_parquet(PRE / "static_boundary_theta_time_tracks_pre_reference.parquet")
    curves = curves[curves.sar_frame_index.eq(200)]
    summary = pd.read_parquet(PRE / "static_boundary_frame_summary_pre_reference.parquet")
    summary = summary[summary.sar_frame_index.eq(200)].set_index("boundary_id")
    cx, cy, px_per_m = 511.745326, 590.776351, 591.340317 / 20.0
    colors = {
        "STATIC_BOUNDARY_A": (255, 255, 0),
        "STATIC_BOUNDARY_B": (0, 165, 255),
        "STATIC_BOUNDARY_C": (255, 0, 255),
    }
    for boundary_id, frame in curves.groupby("boundary_id"):
        points = []
        for item in frame.sort_values("theta_deg").itertuples(index=False):
            theta = math.radians(float(item.theta_deg))
            d = float(item.d_peak_smooth_m)
            x = int(round(cx + d * px_per_m * math.tan(theta)))
            y = int(round(cy - d * px_per_m))
            if 0 <= x < overlay.shape[1] and 0 <= y < overlay.shape[0]:
                points.append((x, y))
        cv2.polylines(overlay, [np.asarray(points, np.int32)], False, colors[boundary_id], 3, cv2.LINE_AA)
        center = float(summary.loc[boundary_id, "d_center_m"])
        label_y = int(round(cy - center * px_per_m)) - 7
        cv2.putText(overlay, f"{boundary_id[-1]} {center:.2f}m", (25, max(25, label_y)), cv2.FONT_HERSHEY_SIMPLEX, 0.62, colors[boundary_id], 2, cv2.LINE_AA)

    tree_track = pd.read_parquet(PRE / "tree_visual_yellow_strap_tracks_pre_reference.parquet")
    tree = tree_track[
        tree_track.tree_id.eq("TREE_A_USER_F120") & tree_track.optical_frame_index.eq(120)
    ].iloc[0]
    theta_pred = float(tree.theta_pred_deg)
    theta_rad = math.radians(theta_pred)
    p0 = (int(round(cx + 3.0 * px_per_m * math.sin(theta_rad))), int(round(cy - 3.0 * px_per_m * math.cos(theta_rad))))
    p1 = (int(round(cx + 20.0 * px_per_m * math.sin(theta_rad))), int(round(cy - 20.0 * px_per_m * math.cos(theta_rad))))
    cv2.line(overlay, p0, p1, (0, 255, 0), 3, cv2.LINE_AA)
    cv2.putText(overlay, f"tree theta_pred={theta_pred:+.02f}deg", (540, 570), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (0, 255, 0), 2, cv2.LINE_AA)

    detail = pd.read_csv(PRE / "tree_sar_competitor_trajectories_pre_reference.csv")
    candidates = detail[
        detail.tree_id.eq("TREE_A_USER_F120") & detail.sar_frame_index.eq(200)
    ].sort_values("competition_rank")
    rank_colors = {1: (255, 255, 255), 2: (0, 255, 255), 3: (0, 0, 255)}
    for item in candidates.itertuples(index=False):
        theta = math.radians(float(item.theta_sar_deg))
        r = float(item.range_sar_m)
        x = int(round(cx + r * px_per_m * math.sin(theta)))
        y = int(round(cy - r * px_per_m * math.cos(theta)))
        color = rank_colors[int(item.competition_rank)]
        cv2.circle(overlay, (x, y), 11, color, 3, cv2.LINE_AA)
        cv2.putText(overlay, f"R{int(item.competition_rank)} {r:.1f}m e={item.theta_residual_deg:+.1f}", (x + 12, y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.48, color, 2, cv2.LINE_AA)
    cv2.rectangle(overlay, (0, 0), (1023, 54), (0, 0, 0), -1)
    cv2.putText(overlay, "SAR F200  t=006667ms  | same timestamp", (18, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.78, (255, 255, 255), 2, cv2.LINE_AA)
    return overlay


def build_overview() -> None:
    optical = cv2.cvtColor(annotate_optical(), cv2.COLOR_BGR2RGB)
    sar = cv2.cvtColor(annotate_sar(), cv2.COLOR_BGR2RGB)
    pair = pd.read_parquet(PRE / "parallel_boundary_pair_frame_summary_pre_reference.parquet")
    tree = pd.read_csv(PRE / "tree_sar_competitor_trajectories_pre_reference.csv")
    tree = tree[tree.tree_id.eq("TREE_A_USER_F120")]

    fig = plt.figure(figsize=(20, 14), constrained_layout=True)
    grid = fig.add_gridspec(2, 2, height_ratios=[1.20, 0.80])
    ax_opt = fig.add_subplot(grid[0, 0])
    ax_sar = fig.add_subplot(grid[0, 1])
    ax_pair = fig.add_subplot(grid[1, 0])
    ax_tree = fig.add_subplot(grid[1, 1])
    ax_opt.imshow(optical)
    ax_opt.axis("off")
    ax_opt.set_title("Optical topology hypotheses (not SAR identity)")
    ax_sar.imshow(sar)
    ax_sar.axis("off")
    ax_sar.set_title("SAR neutral boundary curves + competing compact points")

    ax_pair.plot(pair.sar_frame_index, pair.delta_r_median_m, color="tab:green", lw=1.1, label="median B-A separation")
    ax_pair.fill_between(
        pair.sar_frame_index,
        pair.delta_r_median_m - pair.delta_r_p90_absdev_m,
        pair.delta_r_median_m + pair.delta_r_p90_absdev_m,
        color="tab:green",
        alpha=0.18,
        label="within-frame theta P90 absdev",
    )
    ax_pair.axvspan(330, 335, color="gold", alpha=0.35, label="strict stable SAR F330-F335")
    ax_pair.axvline(200, color="black", ls="--", lw=1.0, label="core SAR F200")
    ax_pair.set_xlabel("SAR frame")
    ax_pair.set_ylabel("B-A radial separation [m]")
    ax_pair.set_title("Parallel boundary-pair behavior")
    ax_pair.legend(fontsize=8)

    for rank, frame in tree.groupby("competition_rank"):
        ax_tree.plot(
            frame.sar_frame_index,
            frame.theta_residual_deg,
            marker=".",
            lw=0.9,
            label=f"competitor R{rank} @ {frame.range_hypothesis_center_m.median():.2f}m",
        )
    ax_tree.axhline(0, color="black", lw=0.8)
    ax_tree.axvline(200, color="black", ls="--", lw=1.0)
    ax_tree.set_xlabel("SAR frame")
    ax_tree.set_ylabel("theta_SAR - theta_pred [deg]")
    ax_tree.set_title("User tree: single-frame agreement does not persist")
    ax_tree.legend(fontsize=8)
    fig.suptitle(
        "R02 STATIC SCENE SKELETON OVERVIEW | exact OPT F120 / SAR F200 timestamp match | no PERSON reference",
        fontsize=18,
    )
    fig.savefig(FIG / "R02_STATIC_SCENE_SKELETON_OVERVIEW.png", dpi=180)
    plt.close(fig)


def report_text(boundary: dict, mapping: dict, winners: pd.DataFrame) -> str:
    a = boundary["boundary_stats_full_sequence"]["STATIC_BOUNDARY_A"]
    b = boundary["boundary_stats_full_sequence"]["STATIC_BOUNDARY_B"]
    c = boundary["boundary_stats_full_sequence"]["STATIC_BOUNDARY_C"]
    tree_a = winners[(winners.tree_id.eq("TREE_A_USER_F120")) & winners.competition_rank.eq(1)].iloc[0]
    false_core = winners[(winners.tree_id.eq("TREE_A_USER_F120")) & winners.competition_rank.eq(3)].iloc[0]
    return f"""# PERSON-R02-S0 R02 static radial-azimuth scene skeleton

## Direct answer

**4.9 m 和 7.1 m 更像同一人行道/路缘带的两条平行物理边，但证据只支持“稳定片段中的成对场景骨架”，不能把两条线唯一命名为具体前/后缘；树在 F120/F200 单帧上确有很像的 SAR 亮点，却没有通过完整多帧轨迹竞争，因此暂时不能作为已确认方位静态锚。**

## Radial skeleton verdict

- Verdict: `PARALLEL_BOUNDARY_PAIR_SUPPORTED_IN_STABLE_SUBSEGMENTS_PHYSICAL_STRIP_IDENTITY_PLAUSIBLE_NOT_UNIQUE`.
- Neutral identities remain `STATIC_BOUNDARY_A/B/C`; response strength, persistence, and physical identity are not equated.
- A/B pair is jointly available on `{boundary['pair_available_frames']}/{boundary['pair_total_frames']} = {boundary['pair_availability_fraction']:.1%}` frames under the strict curved-ridge coherence gate.
- Across available pair frames, median separation is `{boundary['pair_delta_r_median_m']:.3f} m`; temporal P90 absolute variation is `{boundary['pair_delta_r_temporal_p90_absdev_m']:.3f} m`; median within-frame theta P90 absolute variation is `{boundary['pair_delta_r_median_theta_p90_absdev_m']:.3f} m`.
- Longest strict stable segment: SAR F{boundary['longest_stable_segment'][0]}-F{boundary['longest_stable_segment'][1]}; median separation `{boundary['stable_segment_pair_delta_r_median_m']:.3f} m`, temporal P90 absolute variation `{boundary['stable_segment_pair_delta_r_p90_temporal_absdev_m']:.3f} m`.
- A full-sequence center `{a['median_d_center_m']:.2f} m` (availability `{a['availability_fraction']:.1%}`), B `{b['median_d_center_m']:.2f} m` (`{b['availability_fraction']:.1%}`), C `{c['median_d_center_m']:.2f} m` (`{c['availability_fraction']:.1%}`).
- P0 common-translation compensation leaves A/B separation invariant by construction. Individual adjacent-frame compensated median absolute residuals are A `{boundary['p0_compensation']['STATIC_BOUNDARY_A']['p0_compensated_abs_residual_median']:.3f} m`, B `{boundary['p0_compensation']['STATIC_BOUNDARY_B']['p0_compensated_abs_residual_median']:.3f} m`, C `{boundary['p0_compensation']['STATIC_BOUNDARY_C']['p0_compensated_abs_residual_median']:.3f} m`. P0 remains SAR image-domain common apparent translation, not recovered platform motion.

## Physical interpretation

- The optical sequence visibly contains a road-side curb/front edge and a farther sidewalk/planting edge. The measured A/B separation and ordering are compatible with one physical strip, so the former `primary/alternate` competition interpretation is rejected for this scene-skeleton analysis.
- Exact edge naming remains set-valued: A/B may correspond to `ROAD-SIDE CURB FRONT EDGE` and `SIDEWALK REAR / PLANTING EDGE`, but this ordering is not promoted to calibrated cross-modal identity.
- C at about `{c['median_d_center_m']:.2f} m` is not well described as pure random clutter. It is a third persistent parking/planting/building-side response layer, likely composite and sometimes vehicle-contaminated: `THIRD_PERSISTENT_SCENE_LAYER_IDENTITY_COMPOSITE`.
- At the exact core time OPT F120 / SAR F200, A and C satisfy the strict single-boundary gate, while B has strong response but excessive theta-shape variation; the core case is illustrative, not the strictest pair segment.

## Tree / static azimuth anchor verdict

- Three visually distinct strapped roadside trees were followed using manual visual knots plus yellow-strap image support. Optical availability: TREE_A 61/66 frames, TREE_B 70/81, TREE_C 67/81.
- Confirmed SAR static anchors: `{mapping['accepted_static_anchor_count']}`. Final mapping verdict: `{mapping['current_azimuth_mapping_verdict']}`.
- Best user-tree range competitor is `{tree_a.range_hypothesis_center_m:.2f} m`: persistence `{tree_a.matched_frames}/{tree_a.available_sar_frames} = {tree_a.persistence_fraction:.1%}`, median absolute theta residual `{tree_a.median_abs_theta_residual_deg:.2f} deg`, P90 `{tree_a.p90_abs_theta_residual_deg:.2f} deg`. It fails the temporal trajectory gate.
- Strongest false single-frame correspondence is the user tree's `{false_core.range_hypothesis_center_m:.2f} m` competitor: at SAR F200 its theta residual is only about `+0.14 deg`, but across the sequence persistence is `{false_core.persistence_fraction:.1%}`, median absolute residual `{false_core.median_abs_theta_residual_deg:.2f} deg`, and P90 `{false_core.p90_abs_theta_residual_deg:.2f} deg`. It disappears/reappears and does not maintain one compact response trajectory.
- Rank-1 signed median residuals for the three visual tree candidates are close to zero (`+0.30`, `+0.14`, `-0.20 deg`) but have broad, discontinuous spreads. This is exactly why no stable offset or slope correction is inferred.
- `CURRENT_AZIMUTH_MAPPING = STATIC_ANCHORS_INSUFFICIENT_TO_JUDGE`; no mapping rewrite and no leave-one-anchor-out calibration claim are authorized.

## Core figure and evidence

- Main overview: `figures/R02_STATIC_SCENE_SKELETON_OVERVIEW.png`.
- Exact timestamp core case uses `OPT F120 t006667ms` and `SAR F200 t006667ms`; SAR F95 is not used as synchronized evidence.
- Continuous review sheets cover optical F80-F200 and SAR F133-F333. The review pack also contains raw optical F110-F135, raw SAR F183-F225, and the strict stable segment.
- The earlier 7-11-frame template landmark experiment and coordinate-grid development diagnostics are excluded from the final evidence chain and review pack; the tree conclusion comes from the longer yellow-strap sequence plus matched SAR-point competition.

## Independent validation

- Machine-readable results: `VALIDATION_RESULTS.csv` and `VALIDATION_SUMMARY.json`.
- The validator independently recomputes the exact F120/F200 timestamp match, complete 495-frame denominators, A/B stable segment, tree counts, zero confirmed anchors, non-claims, and review-pack integrity.

## Decision for future PERSON work

`SCENE_SKELETON_WORTH_RETAINING_AS_CONSERVATIVE_CONTEXT_NOT_YET_PERSON_MECHANISM`.

The radial A/B/C ordering is useful scene context and the A/B pair is physically plausible. However, tree-point identity and the current angular mapping are not confirmed strongly enough to use the scene skeleton for PERSON pruning or grounding yet. A next study should manually label one compact SAR point through an uninterrupted tree passage, or use a designed static reflector/known pole, before revisiting PERSON.

## Non-claims

No PERSON reference, PERSON discrimination, PERSON range, final localization, final center/box, R04, P2, learned model, new tracker, full camera calibration, intrinsic RCS, physical platform-motion recovery, or mapping rewrite is used or claimed. All optical semantics are visual-development only, and all SAR point identities remain set-valued unless explicitly rejected by temporal competition.
"""


def build_review_pack() -> tuple[int, str, int]:
    PACK.parent.mkdir(parents=True, exist_ok=True)
    if PACK.exists():
        PACK.unlink()
    entries: list[dict[str, object]] = []

    def add_file(archive: zipfile.ZipFile, source: Path, arcname: str, category: str) -> None:
        archive.write(source, arcname)
        entries.append(
            {
                "archive_path": arcname,
                "source_path": str(source),
                "category": category,
                "bytes": source.stat().st_size,
                "sha256": sha256_file(source),
            }
        )

    with zipfile.ZipFile(PACK, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        code_sources = [TASK / name for name in sorted(PACK_CODE_NAMES)] + [TASK / "README.md"]
        for source in code_sources:
            add_file(archive, source, f"code/{source.name}", "code")
        for source in sorted(PRE.glob("*")):
            if source.is_file() and not source.name.startswith(EXCLUDED_PRE_REFERENCE_PREFIXES):
                add_file(archive, source, f"pre_reference/{source.name}", "pre_reference_table")
        for source in sorted(FIG.rglob("*.png")):
            if "landmark_review" in source.relative_to(FIG).parts:
                continue
            add_file(archive, source, f"figures/{source.relative_to(FIG).as_posix()}", "figure")
        for source in [OUT / "REPORT.md", OUT / "SUMMARY.json"]:
            add_file(archive, source, f"report/{source.name}", "report")

        for frame_index in range(110, 136):
            source = sorted(RAW_OPT.glob(f"frame_{frame_index:06d}_t*ms.jpg"))[0]
            add_file(archive, source, f"raw_sequences/core_optical_F110_F135/{source.name}", "raw_optical_continuous")
        for frame_index in range(183, 226):
            source = sorted(RAW_SAR.glob(f"frame_{frame_index:06d}_t*ms.jpg"))[0]
            add_file(archive, source, f"raw_sequences/core_sar_F183_F225/{source.name}", "raw_sar_continuous")
        for frame_index in range(330, 336):
            source = sorted(RAW_SAR.glob(f"frame_{frame_index:06d}_t*ms.jpg"))[0]
            add_file(archive, source, f"raw_sequences/stable_sar_F330_F335/{source.name}", "raw_sar_stable_segment")
        for frame_index in range(198, 203):
            source = sorted(RAW_OPT.glob(f"frame_{frame_index:06d}_t*ms.jpg"))[0]
            add_file(archive, source, f"raw_sequences/stable_optical_context_F198_F202/{source.name}", "raw_optical_stable_context")

        pack_readme = """# R02 static scene skeleton review pack

Start with `figures/R02_STATIC_SCENE_SKELETON_OVERVIEW.png` and `report/REPORT.md`.
The core optical/SAR pair uses exactly t=006667ms. Boundary A/B/C are neutral SAR image-domain hypotheses. Tree candidates are visual-development identities; none passed the multi-frame SAR point trajectory gate. The pack contains continuous raw sequences, not only keyframes. No PERSON final location or box is included.
"""
        archive.writestr("README.md", pack_readme)
        entries.append(
            {
                "archive_path": "README.md",
                "source_path": "GENERATED_TEXT",
                "category": "readme",
                "bytes": len(pack_readme.encode("utf-8")),
                "sha256": hashlib.sha256(pack_readme.encode("utf-8")).hexdigest(),
            }
        )
        manifest = {
            "pack_name": PACK.name,
            "created_date": "2026-08-31",
            "entry_count_excluding_manifest": len(entries),
            "person_reference_used": False,
            "r04_accessed": False,
            "entries": entries,
        }
        archive.writestr("MANIFEST.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    return PACK.stat().st_size, sha256_file(PACK), len(entries) + 1


def build_output_manifest() -> None:
    manifest_rows = []
    for path in sorted(item for item in OUT.rglob("*") if item.is_file()):
        if path.name == "OUTPUT_MANIFEST.csv":
            continue
        relative = path.relative_to(OUT)
        if "landmark_review" in relative.parts:
            continue
        if relative.parts and relative.parts[0] == "pre_reference" and relative.name.startswith(
            EXCLUDED_PRE_REFERENCE_PREFIXES
        ):
            continue
        manifest_rows.append(
            {
                "workspace_relative_path": path.relative_to(WORKSPACE).as_posix(),
                "artifact_scope": "output",
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "person_reference_used": False,
                "r04_accessed": False,
            }
        )
    manifest_rows.append(
        {
            "workspace_relative_path": PACK.relative_to(WORKSPACE).as_posix(),
            "artifact_scope": "uncommitted_review_pack",
            "bytes": PACK.stat().st_size,
            "sha256": sha256_file(PACK),
            "person_reference_used": False,
            "r04_accessed": False,
        }
    )
    pd.DataFrame(manifest_rows).to_csv(
        OUT / "OUTPUT_MANIFEST.csv", index=False, encoding="utf-8-sig"
    )


def main() -> None:
    build_overview()
    boundary = json.loads((PRE / "static_boundary_analysis_summary_pre_reference.json").read_text(encoding="utf-8"))
    mapping = json.loads((PRE / "tree_static_anchor_mapping_summary_pre_reference.json").read_text(encoding="utf-8"))
    winners = pd.read_csv(PRE / "tree_sar_competition_winners_pre_reference.csv")
    report = report_text(boundary, mapping, winners)
    (OUT / "REPORT.md").write_text(report, encoding="utf-8")
    summary = {
        "verdict": "PARALLEL_BOUNDARY_PAIR_SUPPORTED_IN_STABLE_SUBSEGMENTS_PHYSICAL_STRIP_IDENTITY_PLAUSIBLE_NOT_UNIQUE",
        "tree_verdict": "VISUAL_TREE_TO_SAR_POINT_NOT_TEMPORALLY_CONFIRMED",
        "current_azimuth_mapping": mapping["current_azimuth_mapping_verdict"],
        "pair_delta_r_median_m": boundary["pair_delta_r_median_m"],
        "pair_delta_r_temporal_p90_absdev_m": boundary["pair_delta_r_temporal_p90_absdev_m"],
        "longest_stable_segment": boundary["longest_stable_segment"],
        "stable_segment_pair_delta_r_median_m": boundary["stable_segment_pair_delta_r_median_m"],
        "visual_tree_count": 3,
        "confirmed_static_anchor_count": mapping["accepted_static_anchor_count"],
        "core_case": {"optical_frame": 120, "sar_frame": 200, "timestamp_ms": 6667},
        "boundary_c_interpretation": "THIRD_PERSISTENT_SCENE_LAYER_IDENTITY_COMPOSITE",
        "person_reference_used": False,
        "r04_accessed": False,
    }
    (OUT / "SUMMARY.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    pack_bytes, pack_sha, pack_entries = build_review_pack()
    summary.update(
        {
            "review_pack_path": str(PACK),
            "review_pack_bytes": pack_bytes,
            "review_pack_sha256": pack_sha,
            "review_pack_entry_count": pack_entries,
        }
    )
    (OUT / "SUMMARY.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    build_output_manifest()
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
