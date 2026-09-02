from __future__ import annotations

import hashlib
import json
import math
import shutil
import zipfile
from pathlib import Path

import cv2
import numpy as np
import pandas as pd


TASK = Path(__file__).resolve().parent
WORKSPACE = TASK.parents[1]
OUT = WORKSPACE / "output" / "person_r02_scene_depth_value_test_20260902"
PRE = OUT / "pre_reference"
POST = OUT / "post_reference_evaluation_only"
FIG = OUT / "figures" / "final_review"
PACK_STAGE = OUT / "review_pack_content"
PACK = WORKSPACE / "review_packs" / "PERSON_R02_SCENE_DEPTH_VALUE_TEST_20260903.zip"
R2_PRE = WORKSPACE / "output" / "person_terg_r2_runtime_grounding_and_full_stream_hypothesis_management_20260830" / "pre_reference"
REGISTRY = R2_PRE / "full_stream_frame_registry_pre_reference.parquet"
Q95_MASKS = R2_PRE / "full_stream_q95_masks"
CONDITIONS = ["ANGLE_ONLY", "ANGLE_PLUS_ONE_CURB_HALFSPACE", "ANGLE_PLUS_TWO_BOUNDARY_SCENE_LAYER"]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().lower()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def read_bgr(path: Path) -> np.ndarray:
    image = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(path)
    return image


def write_png(path: Path, image: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ok, encoded = cv2.imencode(".png", image)
    if not ok:
        raise RuntimeError(path)
    encoded.tofile(path)


def fit(image: np.ndarray, width: int, height: int) -> np.ndarray:
    scale = min(width / image.shape[1], height / image.shape[0])
    resized = cv2.resize(image, (int(image.shape[1] * scale), int(image.shape[0] * scale)))
    canvas = np.full((height, width, 3), 245, dtype=np.uint8)
    x, y = (width - resized.shape[1]) // 2, (height - resized.shape[0]) // 2
    canvas[y : y + resized.shape[0], x : x + resized.shape[1]] = resized
    return canvas


def add_header(image: np.ndarray, lines: list[str]) -> np.ndarray:
    top = np.full((82, image.shape[1], 3), (22, 22, 22), dtype=np.uint8)
    for index, line in enumerate(lines):
        cv2.putText(top, line, (12, 28 + index * 27), cv2.FONT_HERSHEY_SIMPLEX, 0.56, (245, 245, 245), 1, cv2.LINE_AA)
    return np.vstack([top, image])


def unpack_mask(path: Path, condition: str) -> np.ndarray:
    key = {CONDITIONS[0]: "angle_only_packbits", CONDITIONS[1]: "one_curb_packbits", CONDITIONS[2]: "two_boundary_packbits"}[condition]
    with np.load(path, allow_pickle=False) as archive:
        shape = tuple(int(value) for value in archive["shape"])
        bits = np.unpackbits(archive[key])[: int(np.prod(shape))]
    return bits.reshape(shape).astype(bool)


def draw_boundaries(image: np.ndarray, frame: int, boundary_index: dict[tuple[int, str], pd.Series]) -> np.ndarray:
    result = image.copy()
    for object_type, color in (("SAR_BOUNDARY_NEAR", (255, 255, 0)), ("SAR_BOUNDARY_FAR", (0, 165, 255))):
        points = np.rint(np.asarray(json.loads(str(boundary_index[(frame, object_type)].points_json)), dtype=float)).astype(np.int32)
        cv2.polylines(result, [points], False, color, 3, cv2.LINE_AA)
    return result


def render_triptych(label: str, row: pd.Series, burden: pd.DataFrame, registry: pd.DataFrame, boundary_index: dict[tuple[int, str], pd.Series]) -> Path:
    frame = int(row.sar_frame)
    raw = read_bgr(Path(registry.loc[frame].sar_image_path))
    with np.load(Q95_MASKS / f"R02ZF_SARF{frame:06d}.npz", allow_pickle=False) as archive:
        q95 = archive["Q095"]
    shell_id = str(row.name)
    shell = burden[burden.shell_id.eq(shell_id)].set_index("condition")
    names = ["A ANGLE ONLY", "B ONE CURB", "C TWO BOUNDARIES"]
    panels = []
    for condition, name in zip(CONDITIONS, names):
        item = shell.loc[condition]
        support = unpack_mask(OUT / str(item.support_mask_file), condition)
        selected = (q95 > 0) & support
        overlay = raw.copy()
        color = np.zeros_like(overlay)
        color[selected] = (40, 40, 255)
        overlay = cv2.addWeighted(overlay, 1.0, color, 0.45, 0.0)
        contours, _ = cv2.findContours(selected.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(overlay, contours, -1, (0, 255, 255), 1, cv2.LINE_AA)
        overlay = draw_boundaries(overlay, frame, boundary_index)
        state = "APPLIED" if bool(item.condition_applied) else "FALLBACK"
        panels.append(add_header(fit(overlay, 750, 490), [f"{name} [{state}]", f"regions/families={int(item.N_region)}/{int(item.N_family)} area={int(item.A_candidate_px)} px"]))
    body = np.hstack(panels)
    title = np.full((78, body.shape[1], 3), (8, 8, 8), dtype=np.uint8)
    cv2.putText(title, f"{label}: SAR F{frame:03d} / OPT F{int(row.optical_frame):03d} / {row.person_hypothesis_id}", (14, 31), cv2.FONT_HERSHEY_SIMPLEX, 0.68, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(title, "near=cyan, far=orange, retained Q95 support=red; no final PERSON localization", (14, 61), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (220, 220, 220), 1, cv2.LINE_AA)
    path = FIG / f"{label.lower().replace(' ', '_')}.png"
    write_png(path, np.vstack([title, body]))
    return path


def render_reference_gap(queue: pd.DataFrame, retention: pd.DataFrame, registry: pd.DataFrame, boundary_index: dict[tuple[int, str], pd.Series]) -> Path:
    rows = retention[retention.condition.eq(CONDITIONS[2])]
    frame = int(rows.iloc[0].sar_frame)
    frame_row = registry.loc[frame]
    sar = draw_boundaries(read_bgr(Path(frame_row.sar_image_path)), frame, boundary_index)
    px_per_m = float(frame_row.geometry_radius_px) / float(frame_row.geometry_outer_range_m)
    for item in rows.itertuples(index=False):
        angle = math.radians(float(item.reference_theta_deg))
        radius = float(item.reference_range_m) * px_per_m
        point = (int(round(frame_row.geometry_center_x_px + radius * math.sin(angle))), int(round(frame_row.geometry_center_y_px - radius * math.cos(angle))))
        color = (0, 0, 255) if bool(item.operator_contaminated_known_case) else (255, 0, 255)
        cv2.drawMarker(sar, point, color, cv2.MARKER_CROSS, 18, 3, cv2.LINE_AA)
    sar = add_header(fit(sar, 1020, 590), ["SAR F472: red=known exposed reference, magenta=clean reference", "Both frozen shells exceed boundary theta coverage; two-boundary operator falls back"])
    selected = queue[queue.optical_review_id.isin(set(rows.optical_review_id))].drop_duplicates("optical_review_id")
    optical = read_bgr(Path(selected.iloc[0].optical_image_path))
    for item in selected.itertuples(index=False):
        color = (0, 0, 255) if str(item.person_hypothesis_id).endswith("PERSON017") else (255, 0, 255)
        cv2.rectangle(optical, (round(item.bbox_x1), round(item.bbox_y1)), (round(item.bbox_x2), round(item.bbox_y2)), color, 5)
    optical = add_header(fit(optical, 1020, 590), ["OPT F283: both hypotheses are visually clear L2 / parking-side", "Clean retention remains untestable because the pre-frozen full-theta gate is false"])
    path = FIG / "reference_overlap_and_boundary_theta_gap.png"
    write_png(path, np.hstack([optical, sar]))
    return path


def paired_metrics(burden: pd.DataFrame, condition: str) -> tuple[dict[str, float | int], pd.DataFrame]:
    base = burden[burden.condition.eq(CONDITIONS[0])].set_index("shell_id")
    current = burden[burden.condition.eq(condition) & burden.condition_applied].set_index("shell_id")
    joined = current.join(base[["N_region", "N_family", "A_candidate_px", "A_candidate_m2"]], rsuffix="_baseline")
    joined["area_reduction_fraction"] = np.where(joined.A_candidate_px_baseline > 0, 1 - joined.A_candidate_px / joined.A_candidate_px_baseline, 0)
    metrics: dict[str, float | int] = {"rows": len(joined), "frames": int(joined.sar_frame.nunique())}
    for name in ["N_region", "N_family", "A_candidate_px", "A_candidate_m2"]:
        metrics[f"{name}_before_median"] = float(joined[f"{name}_baseline"].median())
        metrics[f"{name}_after_median"] = float(joined[name].median())
    reduction = joined.area_reduction_fraction
    metrics.update({
        "area_reduction_fraction_median": float(reduction.median()),
        "area_reduction_fraction_p75": float(reduction.quantile(0.75)),
        "area_reduction_fraction_p90": float(reduction.quantile(0.90)),
        "positive_family_contraction_fraction": float((joined.N_family < joined.N_family_baseline).mean()),
        "positive_area_contraction_fraction": float((reduction > 0).mean()),
        "N_family_after_p75": float(joined.N_family.quantile(0.75)),
        "N_family_after_p90": float(joined.N_family.quantile(0.90)),
        "N_family_after_max": float(joined.N_family.max()),
        "N_family_singleton_fraction": float((joined.N_family == 1).mean()),
        "N_family_le2_fraction": float((joined.N_family <= 2).mean()),
    })
    return metrics, joined


def common_metrics(burden: pd.DataFrame) -> dict[str, float | int]:
    one = burden[burden.condition.eq(CONDITIONS[1]) & burden.condition_applied].set_index("shell_id")
    two = burden[burden.condition.eq(CONDITIONS[2]) & burden.condition_applied].set_index("shell_id")
    common = one.index.intersection(two.index)
    base = burden[burden.condition.eq(CONDITIONS[0])].set_index("shell_id").loc[common]
    one, two = one.loc[common], two.loc[common]
    incremental = np.where(one.A_candidate_px > 0, 1 - two.A_candidate_px / one.A_candidate_px, 0)
    return {
        "rows": len(common), "angle_N_family_median": float(base.N_family.median()), "one_N_family_median": float(one.N_family.median()), "two_N_family_median": float(two.N_family.median()),
        "angle_area_median": float(base.A_candidate_px.median()), "one_area_median": float(one.A_candidate_px.median()), "two_area_median": float(two.A_candidate_px.median()),
        "family_change_rows_two_vs_one": int((two.N_family != one.N_family).sum()), "incremental_area_median": float(np.median(incremental)), "incremental_area_max": float(np.max(incremental)),
    }


def build_pack(paths: list[Path]) -> tuple[int, str]:
    if PACK_STAGE.exists():
        shutil.rmtree(PACK_STAGE)
    PACK_STAGE.mkdir(parents=True)
    records = []
    for source in paths:
        relative = Path("code") / source.name if source.parent == TASK else Path("artifacts") / source.relative_to(OUT)
        target = PACK_STAGE / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        records.append({"relative_path": str(relative).replace("\\", "/"), "bytes": target.stat().st_size, "sha256": sha256(target), "source_path": str(source)})
    pd.DataFrame(records).sort_values("relative_path").to_csv(PACK_STAGE / "PACK_MANIFEST.csv", index=False, encoding="utf-8-sig")
    (PACK_STAGE / "README.md").write_text("Start with artifacts/REPORT.md and artifacts/figures/final_review. This pack contains candidate-support evidence only, not final PERSON localization.\n", encoding="utf-8")
    PACK.parent.mkdir(parents=True, exist_ok=True)
    if PACK.exists():
        PACK.unlink()
    with zipfile.ZipFile(PACK, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(PACK_STAGE.rglob("*")):
            if path.is_file():
                archive.write(path, str(path.relative_to(PACK_STAGE)).replace("\\", "/"))
    return PACK.stat().st_size, sha256(PACK)


def main() -> None:
    if WORKSPACE.resolve() != Path(r"D:\profile\research\workspace").resolve():
        raise RuntimeError(WORKSPACE)
    freeze = json.loads((PRE / "PRE_REFERENCE_FREEZE_MANIFEST.json").read_text(encoding="utf-8"))
    denominators = json.loads((PRE / "denominators_pre_reference.json").read_text(encoding="utf-8"))
    burden = pd.read_parquet(PRE / "runtime_support_burden_pre_reference.parquet")
    queue = pd.read_parquet(PRE / "optical_person_scene_layer_pre_reference.parquet")
    retention = pd.read_parquet(POST / "reference_support_retention_post_reference.parquet")
    retention_summary = pd.read_parquet(POST / "reference_support_retention_summary_post_reference.parquet")
    layers = pd.read_parquet(POST / "scene_layer_vs_reference_range_strata_post_reference.parquet")
    boundaries = pd.read_parquet(PRE / "BOUNDARY_VALUE_ELIGIBLE_GEOMETRY_PRE_REFERENCE.parquet")
    registry = pd.read_parquet(REGISTRY); registry = registry[registry.run_id.eq("R02ZF")].set_index("sar_frame_index")
    boundary_index = {(int(row.sar_frame_index), str(row.object_type)): pd.Series(row._asdict()) for row in boundaries.itertuples(index=False)}
    one, _ = paired_metrics(burden, CONDITIONS[1])
    two, paired = paired_metrics(burden, CONDITIONS[2])
    common = common_metrics(burden)
    success = paired.sort_values(["area_reduction_fraction", "N_family"], ascending=[False, True]).iloc[0]
    residual = paired.sort_values(["N_family", "A_candidate_px"], ascending=[False, False]).iloc[0]
    weak = paired.sort_values(["area_reduction_fraction", "N_family"], ascending=[True, False]).iloc[0]
    success_fig = render_triptych("strongest success", success, burden, registry, boundary_index)
    residual_fig = render_triptych("strongest residual clutter", residual, burden, registry, boundary_index)
    gap_fig = render_reference_gap(queue, retention, registry, boundary_index)
    clean_all = retention_summary[(retention_summary.condition.eq(CONDITIONS[2])) & retention_summary.population.eq("CONFIRMATORY_UNCONTAMINATED")].iloc[0]
    clean_applied = retention_summary[(retention_summary.condition.eq(CONDITIONS[2])) & retention_summary.population.eq("CONFIRMATORY_UNCONTAMINATED_APPLIED_ONLY")].iloc[0]
    layer_text = ", ".join(f"{r.scene_layer}/{r.reference_range_stratum}: {int(r.reference_rows)}" for r in layers.itertuples(index=False)) or "none"
    report = f"""# R02 PERSON scene-depth boundary value test

## Direct answer

If the near/far boundaries are correct and fully cover the frozen optical corridor, they reduce median R02 PERSON Q95 support from **{two['N_family_before_median']:.0f} to {two['N_family_after_median']:.0f} regions/families** and from **{two['A_candidate_px_before_median']:.0f} to {two['A_candidate_px_after_median']:.0f} px** ({two['A_candidate_m2_before_median']:.3f} to {two['A_candidate_m2_after_median']:.3f} m2 proxy), a **{two['area_reduction_fraction_median']:.1%} median area contraction** across {two['rows']} fully covered shell rows. P90/max family burden remains {two['N_family_after_p90']:.0f}/{two['N_family_after_max']:.0f}; singleton and <=2-family fractions are both 0%.

The final decision is **INSUFFICIENT_PERSON_OVERLAP**. Only {int(clean_all.reference_rows)} uncontaminated reference row overlaps the selected cases, and **{int(clean_applied.reference_rows)} uncontaminated reference rows** satisfy the pre-frozen full-boundary-theta application rule. Contraction is measured, but reference retention and `FALSE_SCENE_LAYER_PRUNE` risk are not scientifically estimable.

## Frozen denominator

- Trusted boundary frames: {denominators['eligible_boundary_frames']}; causal shell rows: {denominators['causal_shell_rows']}; unique optical visual cases: {denominators['unique_optical_visual_cases']}.
- Optical visual layers: {denominators['scene_layer_distribution_visual_cases'].get('L2', 0)} `L2`, {denominators['scene_layer_distribution_visual_cases'].get('UNCERTAIN', 0)} `UNCERTAIN`, no observed `L0/L1` cases.
- Exact two-boundary application: {denominators['two_boundary_applied_rows']}/{denominators['causal_shell_rows']}; {denominators['two_boundary_fallback_rows']} rows fall back because both curves do not fully cover the optical corridor.
- Pre-reference root SHA256: `{freeze['pre_reference_root_sha256']}`.

## Candidate contraction

| Condition | Applied rows | Median region/family | Median area px | Median area reduction | P75 / P90 reduction |
|---|---:|---:|---:|---:|---:|
| One-curb halfspace | {one['rows']} | {one['N_family_before_median']:.0f}->{one['N_family_after_median']:.0f} | {one['A_candidate_px_before_median']:.0f}->{one['A_candidate_px_after_median']:.0f} | {one['area_reduction_fraction_median']:.1%} | {one['area_reduction_fraction_p75']:.1%} / {one['area_reduction_fraction_p90']:.1%} |
| Two-boundary L2 layer | {two['rows']} | {two['N_family_before_median']:.0f}->{two['N_family_after_median']:.0f} | {two['A_candidate_px_before_median']:.0f}->{two['A_candidate_px_after_median']:.0f} | {two['area_reduction_fraction_median']:.1%} | {two['area_reduction_fraction_p75']:.1%} / {two['area_reduction_fraction_p90']:.1%} |

On the {common['rows']} rows where both radial conditions are available, family burden is **{common['angle_N_family_median']:.1f}->{common['one_N_family_median']:.1f}->{common['two_N_family_median']:.1f}** and median area is **{common['angle_area_median']:.0f}->{common['one_area_median']:.0f}->{common['two_area_median']:.0f} px** for angle-only, one-curb, and two-boundary. Two boundaries change family count relative to one curb on **{common['family_change_rows_two_vs_one']}/{common['rows']} rows** and add only **{common['incremental_area_median']:.1%} median** incremental area contraction (maximum {common['incremental_area_max']:.1%}). The far halfspace therefore captures nearly all observed L2 discrimination.

## Reference safety and range strata

- Two matched references exist; F472/PERSON017 is the previously exposed operator-contaminated case.
- The single clean reference is L2 at 13.885 m, but the two-boundary condition is fallback, not applied.
- Fallback-aware 100% retention is not safety evidence. Applied clean retention denominator is zero, so the false-prune rate is unavailable.
- Layer/range summary: {layer_text}. There are no 6-8 m rows and no L0/L1 contrast, so radial-stratum correspondence cannot be tested.

## Strongest cases and failures

- Strongest contraction: SAR F{int(success.sar_frame)}, optical F{int(success.optical_frame)}, `{success.person_hypothesis_id}`: family {int(success.N_family_baseline)}->{int(success.N_family)}, area {int(success.A_candidate_px_baseline)}->{int(success.A_candidate_px)} px ({success.area_reduction_fraction:.1%}).
- Strongest residual clutter: SAR F{int(residual.sar_frame)}, optical F{int(residual.optical_frame)}, `{residual.person_hypothesis_id}`: {int(residual.N_family)} families and {int(residual.A_candidate_px)} px remain in the valid L2 layer.
- Representation warning: SAR F{int(weak.sar_frame)} reduces families {int(weak.N_family_baseline)}->{int(weak.N_family)} but removes only {weak.area_reduction_fraction:.1%} of Q95 area.
- F472 is the key availability counterexample: the PERSON layer is visually clear, but the optical corridor exceeds the trusted boundary-theta span, so the rule withdraws instead of extrapolating.

## Decision and only next step

Decision: **INSUFFICIENT_PERSON_OVERLAP**. The measured contraction is modest, leaves about ten families, and provides no family-level gain over one curb on the common denominator. With zero uncontaminated applied reference rows, this run does not justify repairing F66 or engineering full-stream curve propagation.

The only next step is a **small reference-blind overlap collection**: select a few already trusted, full-theta boundary frames containing PERSON hypotheses in at least L1 and L2; freeze optical layers and supports; then evaluate retention. Do not repair F66, expand coverage, recalibrate azimuth, use R04, or enter final localization first.

## Scope and non-claims

This is `VISUAL_DEVELOPMENT_ONLY` and `VALUE IF CORRECT`. Optical supplies angle and scene-layer support; SAR Q95 remains candidate authority. No identity, center, box, intrinsic RCS, physical motion, tracker, weighted fusion, learned depth, R04, or final localization is claimed.
"""
    (OUT / "REPORT.md").write_text(report, encoding="utf-8")
    summary = {"schema": "PERSON_R02_SCENE_DEPTH_VALUE_TEST_SUMMARY_V1", "decision": "INSUFFICIENT_PERSON_OVERLAP", "two_boundary_contraction": two, "one_curb_contraction": one, "common_comparison": common, "pre_reference_root_sha256": freeze["pre_reference_root_sha256"], "uncontaminated_two_boundary_applied_reference_rows": int(clean_applied.reference_rows), "false_scene_layer_prune_rate_estimable": False, "worth_repairing_f66_now": False, "next_step": "SMALL_REFERENCE_BLIND_FULL_THETA_PERSON_OVERLAP_COLLECTION_ONLY", "r04_accessed": False, "final_localization_run": False}
    write_json(OUT / "SUMMARY.json", summary)
    pack_files = [TASK / name for name in ["README.md", "scene_layer_visual_labels_v1.csv", "prepare_pre_reference_review.py", "freeze_pre_reference.py", "evaluate_post_reference.py", "build_report.py"]] + [OUT / "REPORT.md", OUT / "SUMMARY.json", PRE / "PRE_REFERENCE_FREEZE_MANIFEST.json", PRE / "denominators_pre_reference.json", PRE / "optical_person_scene_layer_pre_reference.csv", PRE / "runtime_support_burden_summary_pre_reference.csv", PRE / "case_selection_pre_reference.csv", POST / "reference_support_retention_summary_post_reference.csv", POST / "scene_layer_vs_reference_range_strata_post_reference.csv", POST / "post_reference_gate_audit.json", success_fig, residual_fig, gap_fig]
    size, digest = build_pack(pack_files)
    summary.update({"review_pack_path": str(PACK), "review_pack_bytes": size, "review_pack_sha256": digest})
    write_json(OUT / "SUMMARY.json", summary)
    files = [path for path in OUT.rglob("*") if path.is_file() and not path.is_relative_to(PACK_STAGE)]
    pd.DataFrame([{"relative_path": str(path.relative_to(OUT)).replace("\\", "/"), "bytes": path.stat().st_size, "sha256": sha256(path)} for path in files]).sort_values("relative_path").to_csv(OUT / "OUTPUT_MANIFEST.csv", index=False, encoding="utf-8-sig")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
