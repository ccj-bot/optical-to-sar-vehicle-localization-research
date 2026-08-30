from __future__ import annotations

import hashlib
import json
import py_compile
import tempfile
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd


TASK = Path(__file__).resolve().parent
WORKSPACE = TASK.parents[1]
OUT = WORKSPACE / "output" / "person_r02_curb_radial_anchor_pilot_20260831"
PRE = OUT / "pre_reference"
POST = OUT / "post_reference_evaluation_only"
PACK = WORKSPACE / "review_packs" / "PERSON_R02_CURB_RADIAL_ANCHOR_REVIEW_PACK_20260831.zip"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().lower()


class Validator:
    def __init__(self) -> None:
        self.rows: list[dict[str, object]] = []

    def check(self, name: str, condition: bool, detail: str) -> None:
        self.rows.append({"check": name, "passed": bool(condition), "detail": detail})
        print(f"[{'PASS' if condition else 'FAIL'}] {name}: {detail}")

    def finish(self) -> None:
        frame = pd.DataFrame(self.rows)
        frame.to_csv(OUT / "VALIDATION_RESULTS.csv", index=False, encoding="utf-8-sig")
        summary = {
            "checks": len(frame),
            "passed": int(frame.passed.sum()),
            "failed": int((~frame.passed).sum()),
            "status": "PASS" if frame.passed.all() else "FAIL",
        }
        (OUT / "VALIDATION_SUMMARY.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps(summary, ensure_ascii=False))
        if not frame.passed.all():
            raise SystemExit(1)


def main() -> None:
    v = Validator()
    required = [
        OUT / "REPORT.md",
        OUT / "SUMMARY.json",
        OUT / "SAR_CURB_IDENTITY_CONFIRMATION_TEMPLATE.csv",
        PRE / "CURB_VISUAL_HYPOTHESIS_LEDGER.csv",
        PRE / "sar_curb_candidate_frame_bands_pre_reference.parquet",
        PRE / "sar_curb_candidates_and_roles_pre_reference.parquet",
        PRE / "sar_curb_theta_range_bands_pre_reference.parquet",
        PRE / "angular_width_sensitivity_summary_pre_reference.csv",
        PRE / "angle_only_vs_curb_topology_burden_summary_pre_reference.csv",
        PRE / "PRE_REFERENCE_FREEZE_MANIFEST.json",
        POST / "reference_support_retention_summary_post_reference.csv",
        POST / "reference_range_layer_summary_post_reference.csv",
        PACK,
    ]
    for path in required:
        v.check(f"exists::{path.name}", path.exists(), str(path))

    for script in [
        TASK / "prepare_visual_review.py",
        TASK / "freeze_visual_hypotheses.py",
        TASK / "probe_sar_static_bands.py",
        TASK / "run_person_curb0.py",
        TASK / "validate_person_curb0.py",
    ]:
        try:
            with tempfile.TemporaryDirectory() as directory:
                py_compile.compile(str(script), cfile=str(Path(directory) / (script.stem + ".pyc")), doraise=True)
            ok, detail = True, "compiled"
        except Exception as error:
            ok, detail = False, str(error)
        v.check(f"compile::{script.name}", ok, detail)

    visual = pd.read_csv(PRE / "CURB_VISUAL_HYPOTHESIS_LEDGER.csv")
    v.check("visual_rows", len(visual) == 39, f"rows={len(visual)}")
    v.check("visual_before_computed", visual.computed_verdict.eq("NOT_RUN_AT_VISUAL_FREEZE").all(), "computed verdict frozen empty")
    v.check("visual_no_reference", not visual.provenance.astype(str).str.contains("REFERENCE", case=False).any(), "direct visual provenance")

    candidates = pd.read_parquet(PRE / "sar_curb_candidates_and_roles_pre_reference.parquet")
    v.check("candidate_count", len(candidates) == 3, f"count={len(candidates)}")
    v.check("candidate_ranks", set(candidates.score_rank.astype(int)) == {1, 2, 3}, str(candidates.score_rank.tolist()))
    v.check("primary_distance", abs(float(candidates.iloc[0].d_parallel_peak_m) - 7.10) < 0.051, f"d={candidates.iloc[0].d_parallel_peak_m}")
    v.check("alternate_distance", abs(float(candidates.iloc[1].d_parallel_peak_m) - 4.90) < 0.051, f"d={candidates.iloc[1].d_parallel_peak_m}")
    v.check("far_confounder_distance", abs(float(candidates.iloc[2].d_parallel_peak_m) - 12.40) < 0.051, f"d={candidates.iloc[2].d_parallel_peak_m}")
    v.check("candidate_no_reference", (~candidates.manual_sar_reference_used.astype(bool)).all(), "all false")

    bands = pd.read_parquet(PRE / "sar_curb_candidate_frame_bands_pre_reference.parquet")
    primary = bands[bands.score_rank.eq(1) & bands.primary_window]
    available = primary.availability_state.eq("CURB_BAND_AVAILABLE_GT_BLIND")
    v.check("primary_frame_denominator", len(primary) == 54, f"rows={len(primary)}")
    v.check("primary_available_frames", int(available.sum()) == 48, f"available={int(available.sum())}")
    v.check("primary_band_positive", (primary.d_band_high_m > primary.d_band_low_m).all(), "all positive")
    v.check("primary_peak_stable", primary.d_peak_m.between(7.0, 7.2).all(), f"range={primary.d_peak_m.min()}..{primary.d_peak_m.max()}")
    v.check("unavailable_explicit", set(primary.loc[~available, "sar_frame_index"].astype(int)) == {423, 424, 428, 441, 449, 461}, str(primary.loc[~available, "sar_frame_index"].tolist()))

    theta_bands = pd.read_parquet(PRE / "sar_curb_theta_range_bands_pre_reference.parquet")
    v.check("theta_band_available_only", theta_bands.sar_frame_index.nunique() == int(bands[bands.availability_state.eq("CURB_BAND_AVAILABLE_GT_BLIND")].sar_frame_index.nunique()), f"frames={theta_bands.sar_frame_index.nunique()}")
    sample = theta_bands.sample(min(100, len(theta_bands)), random_state=7)
    expected = sample.d_parallel_minus_m / np.cos(np.deg2rad(sample.theta_deg))
    v.check("theta_range_formula", np.allclose(sample.r_curb_minus_m, expected, atol=1e-6), "r=d/cos(theta)")

    widths = pd.read_csv(PRE / "angular_width_sensitivity_summary_pre_reference.csv")
    v.check("six_sensitivities", len(widths) == 6, f"rows={len(widths)}")
    v.check("width_denominator", widths.denominator_shell_rows.eq(157).all(), str(widths.denominator_shell_rows.tolist()))
    v.check("width_available_rows", widths.available_shell_rows.eq(145).all(), str(widths.available_shell_rows.tolist()))
    current = widths[widths.sensitivity.eq("CURRENT_FROZEN")].iloc[0]
    v.check("current_width_numbers", 2.2 < current.curb_range_width_median < 2.4 and 2.7 < current.curb_range_width_p90 < 2.9, f"median={current.curb_range_width_median} p90={current.curb_range_width_p90}")
    ordered = widths.set_index("sensitivity")
    monotonic = (
        ordered.loc["PLUS_MINUS_1_DEG", "curb_range_width_median"]
        < ordered.loc["PLUS_MINUS_2_DEG", "curb_range_width_median"]
        < ordered.loc["PLUS_MINUS_3_DEG", "curb_range_width_median"]
        < ordered.loc["PLUS_MINUS_4_DEG", "curb_range_width_median"]
        < ordered.loc["PLUS_MINUS_6_DEG", "curb_range_width_median"]
    )
    v.check("sensitivity_monotonic", monotonic, "median widths increase with half-width")

    burden = pd.read_parquet(PRE / "angle_only_vs_curb_topology_exact_q95_burden_pre_reference.parquet")
    v.check("burden_rows", len(burden) == 157 * 6 * 2, f"rows={len(burden)}")
    v.check("pixel_intersections", burden.pixel_intersection_used.astype(bool).all(), "all exact pixel intersections")
    v.check("region_nonincrease", (burden.N_region_angle_plus_curb <= burden.N_region_angle_only).all(), "all nonincreasing")
    v.check("family_nonincrease", (burden.N_family_angle_plus_curb <= burden.N_family_angle_only).all(), "all nonincreasing")
    v.check("area_nonincrease", (burden.A_candidate_px_angle_plus_curb <= burden.A_candidate_px_angle_only).all(), "all nonincreasing")
    fallback = burden.topology_state.ne("CURB_TOPOLOGY_APPLIED")
    v.check("fallback_no_deletion", (burden.loc[fallback, "A_candidate_px_angle_plus_curb"] == burden.loc[fallback, "A_candidate_px_angle_only"]).all(), f"fallback_rows={int(fallback.sum())}")
    v.check("families_assigned", burden.unassigned_family_count_before.eq(0).all() and burden.unassigned_family_count_after.eq(0).all(), "zero unassigned")

    burden_summary = pd.read_csv(PRE / "angle_only_vs_curb_topology_burden_summary_pre_reference.csv")
    row = burden_summary[(burden_summary.sensitivity.eq("CURRENT_FROZEN")) & (burden_summary.topology_mode.eq("PRIMARY_SELECTED_CURB"))].iloc[0]
    v.check("current_burden_region", row.N_region_before_median == 8 and row.N_region_after_median == 7, f"{row.N_region_before_median}->{row.N_region_after_median}")
    v.check("current_burden_family", row.N_family_before_median == 8 and row.N_family_after_median == 7, f"{row.N_family_before_median}->{row.N_family_after_median}")
    conservative = burden_summary[(burden_summary.sensitivity.eq("CURRENT_FROZEN")) & (burden_summary.topology_mode.eq("IDENTITY_CONSERVATIVE_TWO_NEAR_BANDS"))].iloc[0]
    v.check("identity_conservative_weaker", conservative.N_family_after_median >= row.N_family_after_median, f"primary={row.N_family_after_median} conservative={conservative.N_family_after_median}")

    freeze = json.loads((PRE / "PRE_REFERENCE_FREEZE_MANIFEST.json").read_text(encoding="utf-8"))
    hash_ok = True
    hash_details = []
    root_lines = []
    for item in freeze["files"]:
        path_value = item["path"]
        path = OUT / path_value if not Path(path_value).is_absolute() else Path(path_value)
        actual = sha256(path)
        ok = actual == item["sha256"] and path.stat().st_size == item["bytes"]
        hash_ok &= ok
        if not ok:
            hash_details.append(path_value)
        root_lines.append(f"{item['path']}|{item['bytes']}|{item['sha256']}")
    root = hashlib.sha256("\n".join(root_lines).encode("utf-8")).hexdigest()
    v.check("freeze_file_hashes", hash_ok, f"bad={hash_details}")
    v.check("freeze_root_hash", root == freeze["pre_reference_root_sha256"], root)
    v.check("freeze_reference_closed", freeze["manual_sar_reference_opened"] is False, "false")
    v.check("freeze_r04_closed", freeze["r04_accessed"] is False, "false")

    retention = pd.read_csv(POST / "reference_support_retention_summary_post_reference.csv")
    v.check("reference_denominator", retention.reference_rows.eq(4).all(), str(retention.reference_rows.unique()))
    current_ret = retention[(retention.sensitivity.eq("CURRENT_FROZEN")) & (retention.topology_mode.eq("PRIMARY_SELECTED_CURB"))].iloc[0]
    v.check("current_reference_retention", current_ret.angular_retention_fraction == 1 and current_ret.radial_retention_fallback_aware_fraction == 1 and current_ret.support_2d_retention_fallback_aware_fraction == 1, current_ret.to_json())
    narrower = retention[(~retention.sensitivity.eq("CURRENT_FROZEN")) & retention.topology_mode.eq("PRIMARY_SELECTED_CURB")]
    v.check("narrower_angular_half", narrower.angular_retention_fraction.eq(0.5).all(), str(narrower.angular_retention_fraction.tolist()))
    layers = pd.read_csv(POST / "reference_range_layer_summary_post_reference.csv")
    v.check("layer_only_12_14", len(layers) == 1 and layers.iloc[0].range_layer == "12_TO_14M" and int(layers.iloc[0].reference_rows) == 4, layers.to_json(orient="records"))

    report = (OUT / "REPORT.md").read_text(encoding="utf-8")
    for phrase in [
        "CURB_RADIAL_TOPOLOGY_ONLY_MODERATELY_USEFUL_IN_STABLE_SEGMENT",
        "F462-F474",
        "48/54",
        "VISUAL_DEVELOPMENT_ONLY_NOT_RUNTIME_CLASSIFIER",
        "6-8 versus 12-14 comparison cannot be completed",
        "R04 was not accessed",
    ]:
        v.check(f"report_phrase::{phrase}", phrase in report, phrase)

    with zipfile.ZipFile(PACK) as archive:
        names = set(archive.namelist())
        required_names = {
            "README.md",
            "PACK_MANIFEST.csv",
            "report/REPORT.md",
            "figures/06_static_band_candidate_overlays.png",
            "figures/09_q95_angle_only_vs_curb_topology_review.png",
            "review_templates/SAR_CURB_IDENTITY_CONFIRMATION_TEMPLATE.csv",
            "q95_masks/R02ZF_SARF000421.npz",
            "raw_sar_keyframes/SAR_F000421.jpg",
        }
        v.check("pack_required_entries", required_names.issubset(names), f"missing={sorted(required_names-names)}")
        v.check("pack_no_r04_paths", not any("R04" in name.upper() for name in names), "no R04 archive paths")
        v.check("pack_has_keyframes", sum(name.startswith("raw_sar_keyframes/") for name in names) >= 8, f"sar={sum(name.startswith('raw_sar_keyframes/') for name in names)}")

    summary = json.loads((OUT / "SUMMARY.json").read_text(encoding="utf-8"))
    v.check("summary_pack_hash", summary["review_pack_sha256"] == sha256(PACK), summary["review_pack_sha256"])
    v.check("summary_pack_size", summary["review_pack_bytes"] == PACK.stat().st_size, str(PACK.stat().st_size))
    v.check("summary_r04_false", summary["r04_accessed"] is False, "false")
    v.finish()


if __name__ == "__main__":
    main()
