"""Build a source-traceable, layer-separated R35 optical/SAR data package."""
from __future__ import annotations

from pathlib import Path
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib
import json
import math
import shutil

import numpy as np
import pandas as pd
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output/car_data_contract_r35_20261030"
TASK = ROOT / "tasks/car_data_contract_r35_20261030"
SCENE = "R35ZF"
MANUAL = ROOT / "output/manual_guided_localization_20261027/CURRENT_USER_BROWSER_ANNOTATIONS.json"
WORKBENCH = ROOT / "output/paired_optical_sar_annotation_workbench_20260828"
CACHE = ROOT / "output/vehicle50_size_trace_20261026/observations_v2/R35ZF"
PREP = ROOT / "output/pseudocolor_labelstudio_prep_20260722/frames"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dump_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def image_info(path: Path):
    with Image.open(path) as im:
        im.load()
        size = list(im.size)
        mode = im.mode
    return size, mode, sha(path)


def rotated_corners(cx, cy, width, height, angle_deg):
    a = math.radians(float(angle_deg))
    c, s = math.cos(a), math.sin(a)
    local = np.array([[-width / 2, -height / 2], [width / 2, -height / 2],
                      [width / 2, height / 2], [-width / 2, height / 2]])
    rot = local @ np.array([[c, s], [-s, c]])
    return (rot + np.array([cx, cy])).round(6).tolist()


def source_row(path: Path, role: str, status: str, root: Path | None = None):
    size = path.stat().st_size
    return dict(path=str(path), role=role, status=status, bytes=int(size), sha256=sha(path),
                relative_to_root=str(path.relative_to(root)) if root and path.is_relative_to(root) else None)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    watched = [MANUAL, WORKBENCH / 'paired_frame_manifest.parquet',
               WORKBENCH / 'optical_candidate_manifest.parquet',
               *[CACHE / n for n in ['META.json','OBS.npz','MASKS_PACKED.npy','MOTION.json','COMPLETE.json']]]
    source_start = {str(p): sha(p) for p in watched}
    dump_json(OUT / 'SOURCE_HASHES_BEFORE.json', source_start)
    manual = read_json(MANUAL)
    meta = read_json(CACHE / "META.json")
    complete = read_json(CACHE / "COMPLETE.json")
    for p, h in complete["outputs"].items():
        assert sha(Path(p)) == h, f"cache hash mismatch: {p}"

    frame_path = WORKBENCH / "paired_frame_manifest.parquet"
    candidate_path = WORKBENCH / "optical_candidate_manifest.parquet"
    frames = pd.read_parquet(frame_path)
    frames = frames[frames.run_id == SCENE].sort_values("optical_frame_index").reset_index(drop=True)
    candidates = pd.read_parquet(candidate_path)
    candidates = candidates[candidates.run_id == SCENE].sort_values(["optical_frame_index", "candidate_id"]).reset_index(drop=True)
    assert len(frames) == 298 and len(candidates) == 4212

    manual_records = [x for x in manual["annotations"] if x["run_id"] == SCENE]
    manual_by_opt = {int(x["optical_frame_index"]): x for x in manual_records}
    manual_rows = []
    status_by_sar = defaultdict(lambda: {"confirmed": 0, "draft": 0, "pairs": 0})
    for record in manual_records:
        opt_f = int(record["optical_frame_index"])
        for pair_index, pair in enumerate(record.get("pairs", [])):
            sar = pair.get("sar_box")
            status = str(pair.get("relation_status") or "UNKNOWN").upper()
            source = (sar or {}).get("source")
            if status == "CONFIRMED" and source == "MANUAL_NATIVE_SAR":
                ref_authority = "USER_CONFIRMED_NATIVE_SAR"
            elif status == "DRAFT":
                ref_authority = "USER_DRAFT_REVIEW_ONLY"
            else:
                ref_authority = "UNRESOLVED"
            row = {
                "scene": SCENE,
                "reference_subject_id": f"paired_workbench_20260828::{pair['manual_target_id']}",
                "identity_scope": "USER_PAIR_ID_AT_RECORDED_FRAMES_ONLY",
                "manual_target_id": pair.get("manual_target_id"),
                "pair_id": pair.get("pair_id"),
                "optical_frame_index": opt_f,
                "selected_sar_frame_index": int(record["selected_sar_frame_uid"].split("SAR")[-1]) if record.get("selected_sar_frame_uid") else None,
                "source_candidate_id": pair.get("source_candidate_id"),
                "optical_linkage_hint": pair.get("source_object_hypothesis_id"),
                "identity_suggestion_source": pair.get("identity_suggestion_source"),
                "class_name": pair.get("class_name"),
                "relation_status": status,
                "extent_type": pair.get("extent_type"),
                "reference_authority": ref_authority,
                "annotation_source": source or "NONE",
                "optical_box_x1": (pair.get("optical_box") or {}).get("x1"),
                "optical_box_y1": (pair.get("optical_box") or {}).get("y1"),
                "optical_box_x2": (pair.get("optical_box") or {}).get("x2"),
                "optical_box_y2": (pair.get("optical_box") or {}).get("y2"),
                "sar_raw_cx": (sar or {}).get("cx"),
                "sar_raw_cy": (sar or {}).get("cy"),
                "sar_raw_width": (sar or {}).get("width"),
                "sar_raw_height": (sar or {}).get("height"),
                "sar_raw_rotation_deg": (sar or {}).get("rotation_deg"),
                "sar_raw_coordinate_space": "SAR_RAW_NATIVE_1024x592" if sar else None,
                "target_visibility_status": "UNKNOWN",
                "image_availability_status": "NOT_CHECKED_AT_RECORD_IMPORT",
                "note": pair.get("note") or "",
                "snapshot_updated_at": record.get("updated_at"),
            }
            if sar:
                f = int(sar["sar_frame_index"])
                d = np.asarray(meta["public_delta"][str(f)], dtype=float)
                off = np.asarray(meta["reference_offset"], dtype=float)
                row["sar_reference_cx"] = float(sar["cx"] - d[0] + off[0])
                row["sar_reference_cy"] = float(sar["cy"] - d[1] + off[1])
                row["sar_reference_width"] = float(sar["width"])
                row["sar_reference_height"] = float(sar["height"])
                row["sar_reference_rotation_deg"] = float(sar["rotation_deg"])
                row["sar_reference_coordinate_space"] = "SAR_REFERENCE_GRID_V2_1705x608"
                row["sar_raw_corners"] = json.dumps(rotated_corners(sar["cx"], sar["cy"], sar["width"], sar["height"], sar["rotation_deg"]))
                row["sar_reference_corners"] = json.dumps(rotated_corners(row["sar_reference_cx"], row["sar_reference_cy"], sar["width"], sar["height"], sar["rotation_deg"]))
                status_by_sar[f]["pairs"] += 1
                status_by_sar[f]["confirmed"] += int(ref_authority == "USER_CONFIRMED_NATIVE_SAR")
                status_by_sar[f]["draft"] += int(ref_authority == "USER_DRAFT_REVIEW_ONLY")
            else:
                for key in ["sar_reference_cx", "sar_reference_cy", "sar_reference_width", "sar_reference_height", "sar_reference_rotation_deg", "sar_reference_coordinate_space", "sar_raw_corners", "sar_reference_corners"]:
                    row[key] = None
            op_img = Path(frames.loc[frames.optical_frame_index == opt_f, 'optical_image_path'].iloc[0])
            sar_img = Path(meta['source_image_paths'][str(row['selected_sar_frame_index'])])
            assert op_img.is_file() and sar_img.is_file()
            row['image_availability_status'] = 'AVAILABLE'
            row['sar_axis_deg_undirected'] = ((float(sar['rotation_deg']) + (90 if sar['height'] > sar['width'] else 0)) % 180) if sar else None
            row['sar_extent_semantics'] = 'APPROXIMATE_WHOLE_BODY_REFERENCE_NOT_RESPONSE_MASK' if sar else 'NO_SAR_BOX'
            row['sar_physical_heading_deg'] = None
            row['sar_part_labels'] = None
            row['sar_box_boundary_precision_px'] = None
            manual_rows.append(row)
    manual_df = pd.DataFrame(manual_rows)
    manual_df.to_parquet(OUT / "MANUAL_ANNOTATIONS.parquet", index=False)
    manual_df.to_csv(OUT / "MANUAL_ANNOTATIONS.csv", index=False, encoding="utf-8-sig")

    # Optical frame table: no record, record with only drafts, and confirmed SAR
    # reference are separate states. Visibility remains unknown unless explicitly
    # annotated by the user.
    optical_rows = []
    for row in frames.to_dict("records"):
        f = int(row["optical_frame_index"])
        rec = manual_by_opt.get(f)
        pairs = (rec or {}).get("pairs", [])
        conf = sum(1 for p in pairs if p.get("relation_status") == "CONFIRMED" and (p.get("sar_box") or {}).get("source") == "MANUAL_NATIVE_SAR")
        drafts = sum(1 for p in pairs if p.get("relation_status") == "DRAFT")
        if conf:
            annotation_state = "CONFIRMED_MANUAL_SAR_AND_POSSIBLE_DRAFTS"
        elif drafts:
            annotation_state = "DRAFT_ONLY"
        elif rec:
            annotation_state = "RECORD_WITHOUT_SAR_REFERENCE"
        else:
            annotation_state = "NO_MANUAL_RECORD"
        p = Path(row["optical_image_path"])
        size, mode, digest = image_info(p)
        optical_rows.append({
            **row,
            "scene": SCENE,
            "modality": "OPTICAL",
            "image_available": True,
            "image_width_px": size[0],
            "image_height_px": size[1],
            "image_mode": mode,
            "image_sha256": digest,
            "manual_annotation_state": annotation_state,
            "manual_pair_count": len(pairs),
            "confirmed_manual_sar_pair_count": conf,
            "draft_pair_count": drafts,
            "target_visibility_status": "UNKNOWN",
            "candidate_layer_status": "CANDIDATE_ROWS_AVAILABLE" if row['candidate_count'] else "NO_CANDIDATE_ROWS_NOT_ABSENCE",
            "sync_claim": "NOMINAL_INDEX_FPS_ZERO_OFFSET_UNVERIFIED",
            "sync_uncertainty_ms": 250,
        })
    optical_df = pd.DataFrame(optical_rows)
    optical_df['nominal_grid_sar_index'] = np.rint(optical_df.optical_timestamp_ms.to_numpy() * 30 / 1000).astype(int)
    optical_df['nominal_grid_sar_frame_available'] = optical_df.nominal_grid_sar_index.between(0,494)
    optical_df['pairing_status'] = np.where(optical_df.nominal_grid_sar_frame_available,
        'NEAREST_AVAILABLE_NOMINAL_TIMESTAMP', 'NOMINAL_GRID_TARGET_OUTSIDE_SAR_SOURCE')
    optical_df.to_parquet(OUT / "OPTICAL_FRAMES.parquet", index=False)
    optical_df.to_csv(OUT / "OPTICAL_FRAMES.csv", index=False, encoding="utf-8-sig")

    # SAR frame table and frame-level missingness. All 495 images exist; lack of
    # a manual box is kept separate from visibility and image availability.
    sar_rows = []
    sar_dir = PREP / "sar_pseudocolor" / SCENE
    for f in range(495):
        p = sar_dir / f"frame_{f:06d}_t{int(round(f * 1000 / 30)):06d}ms.jpg"
        if not p.exists():
            matches = sorted(sar_dir.glob(f"frame_{f:06d}_t*.jpg"))
            assert len(matches) == 1, f"missing SAR frame {f}"
            p = matches[0]
        size, mode, digest = image_info(p)
        state = status_by_sar[f]
        sar_rows.append({
            "scene": SCENE,
            "modality": "SAR",
            "sar_frame_index": f,
            "timestamp_ms_nominal": int(round(f * 1000 / 30)),
            "timestamp_source": "FRAME_FILENAME_INDEX_TIME_NOT_HARDWARE_TIMESTAMP",
            "image_path": str(p),
            "image_available": True,
            "image_width_px": size[0],
            "image_height_px": size[1],
            "image_mode": mode,
            "image_sha256": digest,
            "manual_annotation_state": "CONFIRMED_MANUAL_SAR_REFERENCE" if state["confirmed"] else ("DRAFT_ONLY" if state["draft"] else "NO_MANUAL_SAR_REFERENCE"),
            "manual_pair_count": state["pairs"],
            "confirmed_manual_sar_pair_count": state["confirmed"],
            "draft_pair_count": state["draft"],
            "target_visibility_status": "UNKNOWN",
            "response_observation_status": "DERIVED_SAR_FRAGMENTS_AVAILABLE",
            "coordinate_space_raw": "SAR_RAW_NATIVE_1024x592",
            "coordinate_space_reference": "SAR_REFERENCE_GRID_V2_1705x608",
        })
    sar_df = pd.DataFrame(sar_rows)
    sar_df.to_parquet(OUT / "SAR_FRAMES.parquet", index=False)
    sar_df.to_csv(OUT / "SAR_FRAMES.csv", index=False, encoding="utf-8-sig")

    # Preserve candidates as proposal rows with explicit non-truth semantics.
    cand = candidates.copy()
    cand["evidence_layer"] = "OPTICAL_CANDIDATE"
    cand["source_role"] = "SEARCH_SHELL_PRIOR"
    cand["truth_status"] = "PROPOSAL_ONLY"
    cand["target_visibility_status"] = "UNKNOWN"
    cand["image_coordinate_space"] = "OPTICAL_NATIVE_3840x2160"
    cand.to_parquet(OUT / "OPTICAL_CANDIDATES.parquet", index=False)
    cand.to_csv(OUT / "OPTICAL_CANDIDATES.csv", index=False, encoding="utf-8-sig")

    # Normalize the full image-derived fragment table. The original compressed
    # cache remains the computational source; this table is the review/index view.
    arr = dict(np.load(CACHE / "OBS.npz"))
    frame_counts = defaultdict(int)
    obs_rows = []
    source_paths = meta["source_image_paths"]
    source_hashes = meta["image_hashes"]
    for i in range(len(arr["frame"])):
        f = int(arr["frame"][i]); local = frame_counts[f]; frame_counts[f] += 1
        a = arr["a"][i]; b = arr["b"][i]; x = arr["x"][i]
        obs_rows.append({
            "scene": SCENE,
            "obs_id": f"{SCENE}_SAR{f:06d}_OBS{local:05d}",
            "source_array_row": i,
            "sar_frame_index": f,
            "source_sar_image_path": source_paths[str(f)],
            "source_sar_image_sha256": source_hashes.get(source_paths[str(f)]),
            "evidence_layer": "SAR_DERIVED_RESPONSE",
            "source_role": "LOCAL_IMAGE_OPERATOR_OUTPUT",
            "truth_status": "NOT_GROUND_TRUTH",
            "coordinate_space": "SAR_REFERENCE_GRID_V2_1705x608",
            "a_x": float(a[0]), "a_y": float(a[1]),
            "b_x": float(b[0]), "b_y": float(b[1]),
            "mid_x": float(x[0]), "mid_y": float(x[1]),
            "angle_rad": float(arr["angle"][i]),
            "angle_deg": float(np.degrees(arr["angle"][i])),
            "length_px": float(arr["length"][i]),
            "clipped": bool(arr["clipped"][i]),
            "background_density": float(arr["bg"][i]),
            "arc_ratio": float(arr["arc"][i]),
            "mask_source": "MASKS_PACKED.npy",
            "public_delta_transform": "reference = raw - public_delta(frame) + reference_offset",
            "target_visibility_status": "UNKNOWN",
        })
    obs_df = pd.DataFrame(obs_rows)
    shifts = np.asarray([meta['public_delta'][str(f)] for f in arr['frame']]) - np.asarray(meta['reference_offset'])
    for src, dest in [('a','a'),('b','b'),('x','mid')]:
        raw = arr[src] + shifts
        obs_df['raw_'+dest+'_x'] = raw[:,0]
        obs_df['raw_'+dest+'_y'] = raw[:,1]
    obs_df['extraction_transform_id'] = 'native_lsd_v2_20261026'
    obs_df['physical_part_identity'] = 'UNKNOWN'
    obs_df['vehicle_ownership'] = 'UNRESOLVED'
    bg = obs_df[['obs_id','source_array_row','sar_frame_index','background_density','arc_ratio']].copy()
    bg['model_id'] = 'v2_half_radial_arc_half_uniform'
    bg['value_semantics'] = 'ASSUMED_BACKGROUND_MODEL_OUTPUT_NOT_MEASUREMENT'
    bg.to_parquet(OUT / 'SAR_BACKGROUND_MODEL.parquet', index=False)
    obs_df.drop(columns=['background_density','arc_ratio'],inplace=True)
    obs_df.to_parquet(OUT / "SAR_OBSERVATIONS.parquet", index=False)
    # Keep a compact CSV of frame-level counts; the full fragment table is
    # intentionally Parquet to avoid a huge text artifact.
    obs_counts = obs_df.groupby("sar_frame_index", as_index=False).agg(fragment_count=("obs_id", "count"), clipped_count=("clipped", "sum"))
    obs_counts.to_csv(OUT / "SAR_OBSERVATION_FRAME_COUNTS.csv", index=False, encoding="utf-8-sig")

    transform = {
        "scene": SCENE,
        "raw_sar_space": {"name": "SAR_RAW_NATIVE_1024x592", "width_px": 1024, "height_px": 592},
        "reference_sar_space": {"name": "SAR_REFERENCE_GRID_V2_1705x608", "width_px": int(meta["native_shape"][1]), "height_px": int(meta["native_shape"][0])},
        "optical_space": {"name": "OPTICAL_NATIVE_3840x2160", "width_px": 3840, "height_px": 2160},
        "reference_offset_xy": meta["reference_offset"],
        "public_delta_source": str(CACHE / "MOTION.json"),
        "public_delta_sha256": sha(CACHE / "MOTION.json"),
        "formula": "sar_reference_xy = sar_raw_xy - public_delta_xy[sar_frame] + reference_offset_xy",
        "semantics": "offline conditional image-domain translation; not physical motion or metric calibration",
        "manual_boxes": "stored in raw native coordinates and transformed copy; raw values remain authoritative",
    }
    dump_json(OUT / "COORDINATE_TRANSFORMS.json", transform)

    source_files = [
        (MANUAL, "USER_MANUAL_SNAPSHOT", "CURRENT_REFERENCE_SNAPSHOT"),
        (frame_path, "WORKBENCH_FRAME_MANIFEST", "CURRENT_FRAME_MANIFEST"),
        (candidate_path, "WORKBENCH_OPTICAL_CANDIDATES", "PROPOSAL_SOURCE"),
        (CACHE / "META.json", "SAR_CACHE_METADATA", "CURRENT_DERIVED_CACHE"),
        (CACHE / "OBS.npz", "SAR_CACHE_OBSERVATIONS", "CURRENT_DERIVED_CACHE"),
        (CACHE / "MASKS_PACKED.npy", "SAR_CACHE_MASKS", "CURRENT_DERIVED_CACHE"),
        (CACHE / "MOTION.json", "SAR_PUBLIC_TRANSFORM", "CURRENT_DERIVED_TRANSFORM"),
        (CACHE / "COMPLETE.json", "SAR_CACHE_RECEIPT", "CURRENT_RECEIPT"),
        (ROOT / "tasks/paired_optical_sar_annotation_workbench_20260828/web/app.js", "WORKBENCH_RENDERER", "CURRENT_RENDER_RULE"),
        (ROOT / "tasks/vehicle50_size_trace_20261026/prepare_native.py", "SAR_CACHE_BUILDER", "CURRENT_DERIVED_CACHE"),
    ]
    manifest = [source_row(p, role, status, ROOT) for p, role, status in source_files]
    # Include every actual optical/SAR image referenced by the normalized frame
    # tables. This makes frame availability and source integrity auditable.
    for p in sorted(set(Path(x) for x in optical_df["optical_image_path"]) | set(Path(x) for x in sar_df["image_path"])):
        manifest.append(source_row(p, "FRAME_IMAGE", "CURRENT_SOURCE_IMAGE", ROOT))
    dump_json(OUT / "SOURCE_MANIFEST.json", {"created": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(), "files": manifest})

    contract = {
        "schema": "CAR_R35_DATA_CONTRACT_V1",
        "created": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
        "scene": SCENE,
        "status": "NORMALIZED_REVIEW_PACKAGE",
        "source_snapshot": str(MANUAL),
        "counts": {
            "optical_frames": int(len(optical_df)),
            "sar_frames": int(len(sar_df)),
            "optical_candidate_rows": int(len(cand)),
            "sar_response_fragments": int(len(obs_df)),
            "manual_annotation_rows": int(len(manual_df)),
            "confirmed_manual_sar_rows": int((manual_df.reference_authority == "USER_CONFIRMED_NATIVE_SAR").sum()),
            "draft_rows": int((manual_df.reference_authority == "USER_DRAFT_REVIEW_ONLY").sum()),
        },
        "layer_rules": {
            "raw_frames": "available images and nominal time/frame metadata; no target claim",
            "sar_derived_response": "LSD-like image-derived fragments with response fields; not GT, ownership, or full-body edges",
            "optical_candidates": "detector/editable proposals; search shell prior only",
            "manual_confirmed": "user-confirmed native SAR boxes; reference layer, immutable in this package",
            "draft": "preserved for review; cannot evaluate as confirmed reference",
        },
        "missingness_rules": {
            "image_available": "source image exists and hash verified",
            "no_manual_record": "no current user annotation record; target visibility remains UNKNOWN",
            "draft_only": "a user record exists but no confirmed native SAR reference",
            "unknown_visibility": "no direct visibility judgment was recorded",
            "unobserved": "reserved for an explicit review decision; never inferred from no box",
        },
        "time_rules": {
            "optical_sar_binding": "nearest nominal frame with actual delta retained",
            "sync_status": "NOMINAL_INDEX_FPS_ZERO_OFFSET_UNVERIFIED",
            "sync_uncertainty_ms": 250,
            "sar_timestamp": "nominal 30 FPS index time; not hardware synchronization proof",
        },
        "coordinate_rules": transform,
        "claim_boundary": "This package standardizes evidence and provenance. It does not establish automatic car localization, identity accuracy, physical size, or complete-body recovery.",
        "source_manifest": "SOURCE_MANIFEST.json",
    }
    dump_json(OUT / "DATA_CONTRACT.json", contract)

    report = f"""# R35 CAR data normalization report

Created: {contract['created']}

The package separates raw frames, SAR image-derived response fragments, optical
candidate proposals, confirmed manual native-SAR references, and DRAFT records.

## Counts

- optical frames: {len(optical_df)}
- SAR frames: {len(sar_df)}
- optical candidate rows: {len(cand)}
- image-derived SAR fragments: {len(obs_df)}
- manual annotation rows: {len(manual_df)}
- confirmed MANUAL_NATIVE_SAR rows: {(manual_df.reference_authority == 'USER_CONFIRMED_NATIVE_SAR').sum()}
- DRAFT rows: {(manual_df.reference_authority == 'USER_DRAFT_REVIEW_ONLY').sum()}

## Data rules

Every frame image is hash checked. A missing manual box is represented as a
missing annotation state while target visibility stays UNKNOWN. Optical rows are
candidate prior material. SAR fragments are derived response evidence and retain
their source frame, source image hash, reference-grid coordinate system, clipping
flag, background density and transform provenance. User-confirmed boxes retain
raw native coordinates as the authoritative values and also expose a transformed
reference-grid copy for analysis.

The nominal optical-to-SAR pairing retains the actual frame delta and its 250 ms
uncertainty. It is not treated as hardware synchronization. Public translation is
recorded as an offline image-domain transform, not physical motion or metric
calibration.

## Files

- `DATA_CONTRACT.json`: schema, statuses, boundaries and counts
- `SOURCE_MANIFEST.json`: source paths, hashes and roles
- `OPTICAL_FRAMES.parquet`: 298 optical frame rows and annotation state
- `SAR_FRAMES.parquet`: 495 SAR frame rows and annotation state
- `OPTICAL_CANDIDATES.parquet`: 4,212 proposal rows
- `MANUAL_ANNOTATIONS.parquet`: current snapshot records, including DRAFTs
- `SAR_OBSERVATIONS.parquet`: 672,155 derived response fragment rows
- `COORDINATE_TRANSFORMS.json`: raw/reference coordinate contract
- `SAR_OBSERVATION_FRAME_COUNTS.csv`: frame-level response counts

This is a normalized evidence package. It is not a localization result.
"""
    (OUT / "REPORT.md").write_text(report, encoding="utf-8")

    verification = {
        "status": "BUILT_PENDING_INDEPENDENT_VALIDATION",
        "source_hashes_unchanged": {p: sha(Path(p)) == h for p,h in source_start.items()},
        "claim_boundary": contract["claim_boundary"],
        "output_sha256": {p.name: sha(p) for p in OUT.iterdir() if p.is_file() and p.name != "VERIFICATION.json"},
    }
    assert all(verification['source_hashes_unchanged'].values())
    dump_json(OUT / "VERIFICATION.json", verification)
    print(json.dumps({"output": str(OUT), "counts": contract["counts"], "status": verification["status"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
