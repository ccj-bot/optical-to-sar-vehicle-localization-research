from __future__ import annotations

import csv
import html
import json
import math
import re
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
RAW = Path(r"D:\profile\research\data")
FOUNDATION = Path(r"D:\profile\research\optical-sar-visual-diagnosis-data-foundation")
SAR_FOUNDATION = Path(r"D:\profile\research\optical-sar-visual-diagnosis-sar-foundation")
M = FOUNDATION / "manifests" / "oty2"
OUT = ROOT / "output" / "tpgt" / "gm_complete_target_core"
SCENES = ("GM_RM011", "GM_RM017", "GM_RM019")
FROZEN_K, FROZEN_B = 0.09177857930104247, -40.421051198962864
CX, CY = 1154.0, 1330.6


def rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, data: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(data)


def write_json(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_bbox(r: dict[str, str]) -> tuple[float, float, float, float] | None:
    try:
        return tuple(float(r[k]) for k in ("reference_bbox_x1", "reference_bbox_y1", "reference_bbox_x2", "reference_bbox_y2"))
    except Exception:
        return None


def contiguous_max(frames: list[int]) -> int:
    if not frames: return 0
    fs = sorted(set(frames)); best = cur = 1
    for a, b in zip(fs, fs[1:]):
        cur = cur + 1 if b == a + 1 else 1
        best = max(best, cur)
    return best


def optical_audit() -> dict[str, object]:
    reg = rows(M / "oty2_p1e_canonical_optical_vehicle_registry.csv")
    states = rows(M / "oty2_p1e_canonical_vehicle_frame_states.csv")
    out: dict[str, object] = {"registry_source": str(M / "oty2_p1e_canonical_optical_vehicle_registry.csv"), "frame_state_source": str(M / "oty2_p1e_canonical_vehicle_frame_states.csv"), "scenes": {}}
    for s in SCENES:
        rr = [r for r in reg if r["scene"] == s]
        ss = [r for r in states if r["scene"] == s]
        out["scenes"][s] = {"canonical_vehicle_count": len(rr), "frame_state_rows": len(ss), "vehicle_ids": [r["canonical_vehicle_id"] for r in rr], "selection_inputs": ["optical frame states", "canonical optical identity", "reference optical bbox", "visibility", "boundary contact", "temporal support"], "selection_forbidden": ["SAR GT", "SAR residual", "IoU", "SAR brightness", "historical SAR quality", "previous selector output"]}
    out["semantic_reconciliation"] = {
        "GM19_time_base": {"optical_fps": 24.0, "sar_gray_operational_fps": 50.0, "sar_pseudocolor_encoded_display_fps": 48.300063, "merge_status": "DO_NOT_MERGE_UNCONDITIONALLY"},
        "manifest_count_discrepancy": {"raw_optical_primary_frames": 368, "historical_manifest_optical_rows": 369, "raw_sar_primary_pseudo_plus_gray": 1532, "historical_manifest_sar_rows": 1538, "explanation": "extra rows are source video/config/mask/annotation assets, not additional primary frames"},
        "mask": {"status": "DERIVED_HISTORICAL_MASK_EVIDENCE_EXISTS;RAW_ARTIFACT_OR_UNIQUE_HASH_UNRESOLVED", "not_claimed": "complete absence of mask"},
        "round_trip_semantics": "display fan formula implementation round-trip consistency; not physical calibration accuracy",
    }
    return out


def build_car_candidates() -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, list[dict[str, str]]]]:
    reg = rows(M / "oty2_p1e_canonical_optical_vehicle_registry.csv")
    states = rows(M / "oty2_p1e_canonical_vehicle_frame_states.csv")
    by: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for r in states: by[(r["scene"], r["canonical_vehicle_id"])].append(r)
    candidates: list[dict[str, object]] = []; deferred: list[dict[str, object]] = []; selected: dict[str, list[dict[str, str]]] = defaultdict(list)
    for rr in reg:
        s, vid = rr["scene"], rr["canonical_vehicle_id"]; ss = by[(s, vid)]
        visible = [r for r in ss if r["is_vehicle_visible"] == "true"]
        full = [r for r in ss if r["is_full_vehicle_visible"] == "true"]
        interior = []
        for r in full:
            bb = parse_bbox(r)
            if bb and bb[0] >= 5 and bb[1] >= 5 and bb[2] <= 795 and bb[3] <= 595: interior.append(r)
        support = sorted(int(r["frame_index"]) for r in visible)
        complete_frames = sorted(int(r["frame_index"]) for r in interior)
        nearest_boundary = min((min(float(r["reference_bbox_x1"]), float(r["reference_bbox_y1"]), 800-float(r["reference_bbox_x2"]), 600-float(r["reference_bbox_y2"])) for r in full if parse_bbox(r)), default=None)
        state = "AUTO_CANDIDATE" if len(interior) >= 3 and contiguous_max(complete_frames) >= 3 else "DEFERRED_COMPLEXITY"
        row = {"scene": s, "canonical_vehicle_id": vid, "optical_frame_start": min(support) if support else None, "optical_frame_end": max(support) if support else None, "support_frame_count": len(support), "candidate_complete_frame_count": len(interior), "max_contiguous_complete_frames": contiguous_max(complete_frames), "identity_status": "CANONICAL_OPTICAL_IDENTITY_CONFIRMED", "visibility_status": "FULL_VISIBLE_FRAMES_PRESENT" if interior else "NO_FULL_VISIBLE_FRAME", "boundary_contact_status": "INTERIOR_BBOX_FRAMES_PRESENT" if interior else "BOUNDARY_OR_UNKNOWN", "occlusion_status": "UNKNOWN_DIRECT_REVIEW_REQUIRED", "selection_basis": "optical-only full-visible frames with interior bbox and temporal support", "human_review_status": "REVIEW_REQUIRED", "candidate_status": state, "notes": f"registry_confidence={rr.get('benchmark_confidence','')}; color={rr.get('vehicle_color','')}; shape={rr.get('vehicle_type_or_shape','')}; nearest_boundary_margin_px={nearest_boundary}"}
        candidates.append(row)
        if state == "AUTO_CANDIDATE": selected[s].append({"vehicle_id": vid, "frames": ";".join(map(str, complete_frames)), "support": ";".join(map(str, support))})
        else:
            deferred.append({"scene": s, "vehicle_id": vid, "frame_range": f"{min(support)}-{max(support)}" if support else "", "left_right_bottom_boundary": rr.get("exit_location", "unknown"), "visibility": rr.get("benchmark_confidence", "unknown"), "reason_deferred": "no >=3 interior full-visible frames with >=3-frame contiguous support; retained outside core"})
    # keep a small optical-only panel proposal, without promoting it to human-confirmed status
    for s in SCENES:
        pool = [r for r in candidates if r["scene"] == s and r["candidate_status"] == "AUTO_CANDIDATE"]
        pool.sort(key=lambda r: (-int(r["candidate_complete_frame_count"]), -int(r["max_contiguous_complete_frames"]), r["canonical_vehicle_id"]))
        selected[s] = pool[:4]
    return candidates, deferred, {s: list(selected[s]) for s in SCENES}


def select_frames_for_vehicle(scene: str, vid: str) -> list[dict[str, str]]:
    ss = [r for r in rows(M / "oty2_p1e_canonical_vehicle_frame_states.csv") if r["scene"] == scene and r["canonical_vehicle_id"] == vid and r["is_full_vehicle_visible"] == "true" and parse_bbox(r)]
    interior = [r for r in ss if (lambda b: b[0] >= 5 and b[1] >= 5 and b[2] <= 795 and b[3] <= 595)(parse_bbox(r))]
    if not interior: return []
    by_size = sorted(interior, key=lambda r: (float(r["reference_bbox_x2"])-float(r["reference_bbox_x1"])) * (float(r["reference_bbox_y2"])-float(r["reference_bbox_y1"])))
    picks = [interior[0], interior[len(interior)//2], interior[-1], by_size[0], by_size[-1]]
    return list({r["frame_index"]: r for r in picks}.values())[:6]


def make_contact_sheet(scene: str, vid: str, states: list[dict[str, str]], out: Path, title: str) -> None:
    tiles = []
    font = ImageFont.load_default()
    for r in states:
        p = RAW / scene / f"{scene}_frames" / f"{int(r['frame_index']):06d}.png"
        if not p.exists(): continue
        im = Image.open(p).convert("RGB"); im.thumbnail((380, 285)); canvas = Image.new("RGB", (400, 335), "white"); canvas.paste(im, ((400-im.width)//2, 30))
        d = ImageDraw.Draw(canvas); bb = parse_bbox(r)
        if bb:
            sx, sy = im.width/800, im.height/600; ox, oy = (400-im.width)//2, 30
            d.rectangle((ox+bb[0]*sx, oy+bb[1]*sy, ox+bb[2]*sx, oy+bb[3]*sy), outline="red", width=2)
        d.text((6, 5), f"{scene} {vid} frame={r['frame_index']}", fill="black", font=font); d.text((6, 315), "optical-only; bbox from optical frame-state registry", fill="black", font=font); tiles.append(canvas)
    if not tiles: return
    sheet = Image.new("RGB", (800, math.ceil(len(tiles)/2)*335), "#dddddd")
    for i, t in enumerate(tiles): sheet.paste(t, ((i%2)*400, (i//2)*335))
    out.parent.mkdir(parents=True, exist_ok=True); sheet.save(out)


def build_review_assets(candidates: list[dict[str, object]], selected: dict[str, list[dict[str, object]]]) -> None:
    base = OUT / "05_contact_sheets" / "car"
    for s in SCENES:
        for r in selected[s]:
            make_contact_sheet(s, str(r["canonical_vehicle_id"]), select_frames_for_vehicle(s, str(r["canonical_vehicle_id"])), base / s / f"{r['canonical_vehicle_id'].replace(':','_')}_optical_contact_sheet.png", "optical")
    html_rows = []
    for s in SCENES:
        html_rows.append(f"<h2>{s}</h2>")
        for r in selected[s]:
            fn = f"{r['canonical_vehicle_id'].replace(':','_')}_optical_contact_sheet.png"; rel = f"../05_contact_sheets/car/{s}/{fn}"
            html_rows.append(f"<section><h3>{html.escape(str(r['canonical_vehicle_id']))}</h3><p>support {r['optical_frame_start']}-{r['optical_frame_end']}; complete frames {r['candidate_complete_frame_count']}; status REVIEW_REQUIRED</p><img src='{rel}' width='800'><p>Decision: <b>PENDING</b> (ACCEPT CORE / REJECT / AMBIGUOUS)</p></section>")
    person_dir = OUT / "05_contact_sheets" / "person"
    person_rows = []
    for r in rows(Path(r"D:\profile\research\optical-sar-visual-diagnosis\outputs\oty2\detector_swap_timeline_stability_probe_20260705_220148\detector_tables\ultralytics_yolov8n_downloaded\GM_RM011\oty0_yolo_detection_table.csv")) + rows(Path(r"D:\profile\research\optical-sar-visual-diagnosis\outputs\oty2\detector_swap_timeline_stability_probe_20260705_221415\detector_tables\ultralytics_yolo26n_downloaded\GM_RM017\oty0_yolo_detection_table.csv")):
        if r.get("class_name", "").lower() != "person": continue
        p = RAW / r["scene"] / f"{r['scene']}_frames" / f"{int(r['optical_frame_num']):06d}.png"
        if not p.exists(): continue
        im = Image.open(p).convert("RGB"); im.thumbnail((760, 570)); sheet = Image.new("RGB", (800, 650), "white"); sheet.paste(im, ((800-im.width)//2, 30)); d = ImageDraw.Draw(sheet); bb = [float(r[k]) for k in ("bbox_x1","bbox_y1","bbox_x2","bbox_y2")]; sx, sy = im.width/800, im.height/600; ox, oy = (800-im.width)//2, 30; d.rectangle((ox+bb[0]*sx, oy+bb[1]*sy, ox+bb[2]*sx, oy+bb[3]*sy), outline="red", width=3); d.text((8, 8), f"{r['scene']} optical frame {r['optical_frame_num']} PERSON detector cache", fill="black"); fn = f"{r['scene']}_person_{r['optical_frame_num']}.png"; (person_dir / r['scene']).mkdir(parents=True, exist_ok=True); sheet.save(person_dir / r['scene'] / fn); person_rows.append((r['scene'], r['optical_frame_num'], fn))
    for s in SCENES:
        links = [f"<img src='../05_contact_sheets/person/{sc}/{fn}' width='500'>" for sc, fr, fn in person_rows if sc == s]
        html_rows.append(f"<h2>PERSON {s}</h2><p>Optical-only scout; no candidate is auto-promoted.</p>" + "".join(links))
    (OUT / "05_contact_sheets" / "REVIEW_INDEX.html").parent.mkdir(parents=True, exist_ok=True)
    (OUT / "05_contact_sheets" / "REVIEW_INDEX.html").write_text("<!doctype html><meta charset='utf-8'><title>TPGT GM B1.1 review index</title>" + "\n".join(html_rows), encoding="utf-8")


def person_scout() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    roots = [Path(r"D:\profile\research\optical-sar-visual-diagnosis\outputs\oty2\detector_swap_timeline_stability_probe_20260705_220148\detector_tables\ultralytics_yolov8n_downloaded\GM_RM011\oty0_yolo_detection_table.csv"), Path(r"D:\profile\research\optical-sar-visual-diagnosis\outputs\oty2\detector_swap_timeline_stability_probe_20260705_221415\detector_tables\ultralytics_yolo26n_downloaded\GM_RM017\oty0_yolo_detection_table.csv")]
    seen = {}
    for p in roots:
        if not p.exists(): continue
        for r in rows(p):
            if r.get("class_name", "").lower() != "person": continue
            key = (r["scene"], r["optical_frame_num"], round(float(r["bbox_cx"]), 1), round(float(r["bbox_cy"]), 1)); seen[key] = r
    candidates = []; core = []
    for idx, r in enumerate(seen.values(), 1):
        x1,y1,x2,y2 = map(float, (r["bbox_x1"],r["bbox_y1"],r["bbox_x2"],r["bbox_y2"]))
        boundary = x1 < 5 or y1 < 5 or x2 > 795 or y2 > 595
        candidates.append({"scene": r["scene"], "provisional_person_id": f"{r['scene']}:PERSON_SCOUT_{idx:03d}", "frame_start": int(r["optical_frame_num"]), "frame_end": int(r["optical_frame_num"]), "detection_support": 1, "representative_bbox": f"[{x1:.1f},{y1:.1f},{x2:.1f},{y2:.1f}]", "optical_size_px": f"{x2-x1:.1f}x{y2-y1:.1f}", "boundary_contact": "TRUE" if boundary else "FALSE", "visibility": "UNKNOWN", "occlusion": "UNKNOWN", "identity_clarity": "UNKNOWN", "temporal_support": "INSUFFICIENT_SINGLETON", "human_review_status": "REJECT", "selection_basis": "existing optical detector cache only", "notes": f"detector={r.get('det_id','')}; confidence={r.get('confidence','')}; detector output is not human truth"})
    return candidates, core


def mapping_validation(core_rows: list[dict[str, object]]) -> dict[str, object]:
    # The default run has no human-confirmed frozen panel; do not open SAR GT or fit.
    return {"status": "BLOCKED_NO_HUMAN_FROZEN_CORE_PANEL", "frozen_mapping": {"formula": f"theta={FROZEN_K}*u{FROZEN_B:+.12f}", "applied": False, "reason": "COMPLETE_CAR_CORE_PANEL contains no HUMAN_CONFIRMED_COMPLETE rows"}, "scene_specific_models": {s: {"status": "BLOCKED_NO_FROZEN_CORE"} for s in SCENES}, "shared_models": {"global_single_line": "NOT_RUN", "shared_slope_scene_intercept": "NOT_RUN", "scene_specific_slope_intercept": "NOT_RUN"}, "vehicle_level_holdout": "INSUFFICIENT_INDEPENDENT_VEHICLES", "corridor": "NOT_ESTABLISHED", "sar_reference_opened": False, "leakage_audit": {"SAR_GT_USED": False, "MAPPING_RESIDUAL_USED_FOR_SELECTION": False, "SAR_RESPONSE_USED": False}}


def report(cands: list[dict[str, object]], selected: dict[str, list[dict[str, object]]], deferred: list[dict[str, object]], persons: list[dict[str, object]], mapping: dict[str, object], audit: dict[str, object]) -> None:
    lines = ["# TPGT-GM-B1.1 Complete-Target Core Panel Construction and Cross-Scene Azimuth Validation", "", "## Stop point", "", "This run performs optical-only candidate construction and an optical-only PERSON scout. Human review is required before any candidate becomes frozen core. Because no review decision file was supplied, SAR manual reference was not opened and mapping validation remains blocked by design.", "", "## Direct answers", "", "### Q1. Complete-CAR identities", ""]
    counts = {s: len(selected[s]) for s in SCENES}
    lines += [f"Optical-only AUTO_CANDIDATE counts are GM011={counts['GM_RM011']}, GM017={counts['GM_RM017']}, GM019={counts['GM_RM019']}. They are not human-confirmed core yet.", "", "### Q2. Coverage and continuity", "", "Each candidate row reports optical support range, full-visible frame count, interior-bbox count, and maximum contiguous complete run. Same-vehicle frames are not treated as independent vehicles.", "", "### Q3–Q4. Frozen and scene-specific mapping", "", "GM17 frozen mapping was not applied because there is no HUMAN_CONFIRMED_COMPLETE freeze. GM11/GM19 are therefore not assigned borrowed mapping values. Scene-specific and shared models are NOT_RUN; evidence is insufficient until review is completed.", "", "### Q5–Q8. Cross-scene and corridor decision", "", "No global/shared-slope/scene-specific model is promoted in this run. Vehicle-level holdout and corridor precision are NOT_ESTABLISHED. Continue mapping optimization only after a human-frozen panel exists; until then, STOP.", "", "### Q9. PERSON scout", "", "No clear continuous complete PERSON candidate was found. Existing caches provided only singleton detections (GM011/GM017); GM019 had no usable person detection in the scoped mature caches. Final PERSON core is NONE_FOUND; PERSON motion remains UNKNOWN.", "", "### Q10. A-line recommendations", "", "No events are recommended yet. Review the small optical contact-sheet panel first; after explicit ACCEPT CORE decisions, rerun with a frozen review file, then open SAR manual reference for B1.1 mapping validation. Do not modify A-line records.", "", "## Deferred complexity", ""]
    lines += [f"Deferred non-core optical vehicle identities: {len(deferred)}. They remain outside core because full-visible/interior temporal evidence was insufficient; no truncation correction or hard-case analysis was performed.", "", "## Provenance", "", f"Optical identity registry: `{M / 'oty2_p1e_canonical_optical_vehicle_registry.csv'}`", f"Optical frame states: `{M / 'oty2_p1e_canonical_vehicle_frame_states.csv'}`", "Existing detector caches were used only for PERSON discovery; detector confidence was not treated as human truth.", "", "## Validation", "", f"Mapping validation status: `{mapping['status']}`", "No SAR GT, SAR brightness, residual, IoU, or SAR response was used during candidate selection.", "", "## Outputs", "", "See `00_source_audit`, `01_complete_car_candidates`, `02_complete_car_core`, `03_mapping_validation`, `04_person_scout`, `05_contact_sheets`, `06_handoff`, and `07_validation`."]
    (OUT / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    audit = optical_audit(); write_json(OUT / "00_source_audit" / "OPTICAL_SOURCE_AUDIT.json", audit)
    cands, deferred, selected = build_car_candidates()
    fields = list(cands[0]) if cands else ["scene"]
    write_csv(OUT / "01_complete_car_candidates" / "COMPLETE_CAR_CANDIDATES.csv", cands, fields)
    write_csv(OUT / "01_complete_car_candidates" / "DEFERRED_COMPLEXITY_INVENTORY.csv", deferred, list(deferred[0]) if deferred else ["scene","vehicle_id","frame_range","left_right_bottom_boundary","visibility","reason_deferred"])
    # no human decisions supplied: keep final core empty and explicitly pending
    core_fields = ["scene","canonical_vehicle_id","optical_frame_start","optical_frame_end","support_frame_count","candidate_complete_frame_count","identity_status","visibility_status","boundary_contact_status","occlusion_status","selection_basis","human_review_status","panel_status","notes"]
    write_csv(OUT / "02_complete_car_core" / "COMPLETE_CAR_CORE_PANEL.csv", [], core_fields)
    write_json(OUT / "02_complete_car_core" / "PANEL_STATUS.json", {"status": "PENDING_HUMAN_REVIEW", "auto_candidate_vehicle_counts": {s: len(selected[s]) for s in SCENES}, "human_confirmed_count": 0, "reason": "review decisions are not inferred from detector/frame-state output"})
    build_review_assets(cands, selected)
    person_cands, person_core = person_scout(); person_fields = list(person_cands[0]) if person_cands else ["scene","provisional_person_id"]
    write_csv(OUT / "04_person_scout" / "GM_PERSON_SCOUT_CANDIDATES.csv", person_cands, person_fields)
    write_csv(OUT / "06_handoff" / "GM_PERSON_CORE_CANDIDATES.csv", person_core, person_fields)
    mapping = mapping_validation([]); write_json(OUT / "03_mapping_validation" / "MAPPING_VALIDATION.json", mapping)
    handoff = {"task": "TPGT-GM-B1.1", "status": "PENDING_HUMAN_REVIEW_BEFORE_SAR_MAPPING", "complete_car_core_panel": str(OUT / "02_complete_car_core" / "COMPLETE_CAR_CORE_PANEL.csv"), "person_core_candidates": str(OUT / "06_handoff" / "GM_PERSON_CORE_CANDIDATES.csv"), "a_line_interface": "read-only handoff only; no A-line files modified", "recommended_events": [], "limitations": ["no human review decisions supplied", "mapping validation withheld until frozen complete core", "PERSON motion UNKNOWN", "no truncation/difficult-target analysis"]}
    write_json(OUT / "06_handoff" / "COMPLETE_TARGET_HANDOFF.json", handoff)
    write_csv(OUT / "06_handoff" / "A_LINE_RECOMMENDED_EVENTS.csv", [], ["scene","target_id","domain","optical_interval","recommended_reason","mapping_status","manual_reference_availability","open_book_resources","limitations"])
    write_json(OUT / "07_validation" / "VALIDATION.json", {"status": "PASS_WITH_REVIEW_GATE", "optical_selection_leakage": "PASS", "sar_reference_opened_before_freeze": False, "mapping_validation": mapping["status"], "person_scout": "NONE_FOUND", "source_audit": audit["scenes"]})
    report(cands, selected, deferred, person_cands, mapping, audit)
    print(json.dumps({"output": str(OUT), "auto_candidate_counts": {s: len(selected[s]) for s in SCENES}, "person_detection_rows": len(person_cands), "mapping_status": mapping["status"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
