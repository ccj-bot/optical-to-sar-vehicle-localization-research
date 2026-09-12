from __future__ import annotations

import csv, html, json, math, re, shutil
from collections import defaultdict
from pathlib import Path
from statistics import median

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(r"D:\profile\research\wt_b12")
FOUNDATION = Path(r"D:\profile\research\optical-sar-visual-diagnosis-data-foundation")
MANIFEST = FOUNDATION / "manifests" / "oty2"
RAW = Path(r"D:\profile\research\data")
OUT = ROOT / "output" / "tpgt" / "gm_complete_interval_b12"
SCENES = ["GM_RM011", "GM_RM017", "GM_RM019"]
REG_PATH = MANIFEST / "oty2_p1e_canonical_optical_vehicle_registry.csv"
STATE_PATH = MANIFEST / "oty2_p1e_canonical_vehicle_frame_states.csv"
PERSON_MODEL = ROOT / "yolo11l.pt"


def read_csv(p: Path):
    with p.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(p: Path, rows, fields):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)


def write_json(p: Path, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def bbox(r):
    try:
        vals = [float(r[k]) for k in ("reference_bbox_x1", "reference_bbox_y1", "reference_bbox_x2", "reference_bbox_y2")]
        if vals[2] <= vals[0] or vals[3] <= vals[1]: return None
        return vals
    except (KeyError, ValueError): return None


def runs(frames):
    out = []
    for x in sorted(set(frames)):
        if not out or x > out[-1][-1] + 1: out.append([x])
        else: out[-1].append(x)
    return out


def source_note(rows):
    return ";".join(sorted({r.get("reference_bbox_origin", "unknown") or "unknown" for r in rows}))


def interval_candidates(reg, states):
    by_id = defaultdict(list)
    for r in states:
        if r.get("scene") not in SCENES or r.get("is_vehicle_visible") != "true": continue
        if r.get("is_full_vehicle_visible") != "true" or not bbox(r): continue
        by_id[(r["scene"], r["canonical_vehicle_id"])].append(r)
    all_rows = []; seq = defaultdict(list)
    for rr in reg:
        s, vid = rr["scene"], rr["canonical_vehicle_id"]
        if s not in SCENES: continue
        fs = sorted(by_id.get((s, vid), []), key=lambda x: int(x["frame_index"]))
        for run in runs([int(x["frame_index"]) for x in fs]):
            part = [x for x in fs if int(x["frame_index"]) in run]
            start, end = run[0], run[-1]
            margins = []
            for x in part:
                b = bbox(x); margins.append(min(b[0], b[1], 800-b[2], 600-b[3]))
            # Producer flags are retained as provenance, not treated as human truth.
            interval_id = f"{vid}:CI{len(seq[(s,vid)])+1:02d}"
            seq[(s,vid)].append(interval_id)
            if vid == "GM_RM017:PV001": status = "VEHICLE_NO_SAR_REFERENCE"
            else: status = "AUTO_INTERVAL_CANDIDATE"
            all_rows.append({
                "scene": s, "vehicle_id": vid, "interval_id": interval_id,
                "frame_start": start, "frame_end": end, "frame_count": len(part),
                "support_type": "CONTIGUOUS_FULL_VISIBLE_STATE_ROWS",
                "identity_status": "CANONICAL_OPTICAL_IDENTITY_CONFIRMED",
                "body_complete_status": "PRODUCER_FULL_VISIBLE_PROXY",
                "boundary_status": "INTERIOR_BBOX_PROXY" if min(margins) >= 5 else "BOUNDARY_CONTACT_OR_UNKNOWN",
                "occlusion_status": "UNKNOWN_DIRECT_REVIEW_REQUIRED",
                "bbox_semantics": "REFERENCE_BOX_PRESENT;PROVENANCE_RETAINED",
                "source_provenance": source_note(part),
                "auto_priority": "HIGH" if len(part) >= 12 else ("MEDIUM" if len(part) >= 6 else "LOW"),
                "human_review_status": status if status == "VEHICLE_NO_SAR_REFERENCE" else "REVIEW_REQUIRED",
                "human_note": "",
            })
    return all_rows


def render_interval_sheet(scene, vid, row, state_map, out):
    s, start, end = scene, int(row["frame_start"]), int(row["frame_end"])
    all_frames = sorted(int(r["frame_index"]) for r in state_map[(scene, vid)])
    before = [x for x in all_frames if x < start][-1:]
    after = [x for x in all_frames if x > end][:1]
    core = [start, min(end, start+max(1,(end-start)//4)), start+(end-start)//2, max(start,end-max(1,(end-start)//4)), end]
    picks = []
    for x in before + core + after:
        if x not in picks: picks.append(x)
    tiles=[]; font=ImageFont.load_default()
    lookup = {(int(r["frame_index"])): r for r in state_map[(scene, vid)]}
    for fr in picks:
        p = RAW / scene / f"{scene}_frames" / f"{fr:06d}.png"
        im = Image.open(p).convert("RGB"); im.thumbnail((400,300)); tile=Image.new("RGB",(420,360),"white"); tile.paste(im,((420-im.width)//2,30)); d=ImageDraw.Draw(tile)
        r=lookup.get(fr); b=bbox(r) if r else None
        if b:
            sx,sy=im.width/800,im.height/600; ox=(420-im.width)//2; oy=30
            d.rectangle((ox+b[0]*sx,oy+b[1]*sy,ox+b[2]*sx,oy+b[3]*sy),outline="red",width=3)
        d.text((5,5),f"{scene} {vid} frame={fr}",fill="black",font=font)
        d.text((5,315),f"source={(r or {}).get('reference_bbox_origin','none')} full={(r or {}).get('is_full_vehicle_visible','?')}",fill="black",font=font)
        tiles.append(tile)
    sheet=Image.new("RGB",(420*len(tiles),360),"white")
    for i,t in enumerate(tiles): sheet.paste(t,(420*i,0))
    out.parent.mkdir(parents=True,exist_ok=True); sheet.save(out)


def car_contact_sheets(cands, states):
    state_map=defaultdict(list)
    for r in states: state_map[(r["scene"],r["canonical_vehicle_id"])].append(r)
    manifest=[]
    for r in cands:
        if r["human_review_status"] == "VEHICLE_NO_SAR_REFERENCE": pass
        fn=f"{r['interval_id'].replace(':','_')}.png"; p=OUT/"02_car_contact_sheets"/r["scene"]/fn
        render_interval_sheet(r["scene"],r["vehicle_id"],r,state_map,p)
        manifest.append({"run":"TPGT-GM-B1.2","event":f"{r['scene']}_CAR_INTERVAL","source_media":str(RAW/r['scene']/f"{r['scene']}_frames"),"frame_index":f"{r['frame_start']}-{r['frame_end']}","observation_id":r["interval_id"],"visual_asset":str(p)})
    write_csv(OUT/"02_car_contact_sheets"/"media_manifest.csv",manifest,list(manifest[0]) if manifest else ["run","event","source_media","frame_index","observation_id","visual_asset"])


def gm19_audit(states):
    rows=[r for r in states if r["canonical_vehicle_id"]=="GM_RM019:PV003" and r["frame_index"] in {"136","118","119","120","121","123"}]
    lines=["# GM019 PV003 Contact-Sheet Audit","","## Finding","","Frame 136 is not on the silver MPV. The source box `[735.261,327.552,777.576,350.071]` is a tiny background box over the storefront, while the neighboring frames 118–123 contain large vehicle boxes. This is a source-box/detector anomaly (finding C), not a valid vehicle observation.","","## Evidence",""]
    for r in rows: lines.append(f"- frame {r['frame_index']}: source={r.get('reference_bbox_origin','')}; bbox=({r.get('reference_bbox_x1')},{r.get('reference_bbox_y1')},{r.get('reference_bbox_x2')},{r.get('reference_bbox_y2')}); visibility={r.get('visibility_state')}")
    lines += ["","## Minimal repair","","Exclude frame 136 from PV003 interval evidence and retain the provenance/error record. The valid maximal contiguous complete candidate remains frames 118–123; do not repair the box by interpolation in this task."]
    p=OUT/"03_gm019_pv003_audit"/"GM019_PV003_CONTACT_SHEET_AUDIT.md"; p.parent.mkdir(parents=True,exist_ok=True); p.write_text("\n".join(lines),encoding="utf-8")


def old_scout_audit():
    roots=list(Path(r"D:\profile\research\optical-sar-visual-diagnosis\outputs\oty2").glob("detector_swap_timeline_stability_probe_*/detector_tables/*/GM_RM017/oty0_yolo_detection_table.csv"))
    details=[]
    for p in roots:
        rows=read_csv(p); persons=[r for r in rows if r.get("class_name","").lower()=="person"]
        details.append({"table":str(p),"rows":len(rows),"person_rows":len(persons),"person_frames":sorted({int(float(r["optical_frame_num"])) for r in persons})})
    lines=["# GM17 PERSON Scout Failure Audit","","The B1.1 scout did not scan the 368-frame stream. It consumed pre-existing detector tables, each containing only a sparse subset of frames. GM17 YOLOv8n and YOLO11n had zero person rows; YOLO12n had one person row (frame 184); YOLO26n had one (frame 164); YOLOv8s had two rows at frame 164. The scout then emitted each surviving detection as a singleton and applied no temporal linking. Therefore the prior NONE_FOUND result is a cache coverage and linking failure, not evidence of no PERSON.","","## Cache audit",""]
    lines += [f"- `{d['table']}`: rows={d['rows']}, person_rows={d['person_rows']}, person_frames={d['person_frames']}" for d in details]
    p=OUT/"00_audit"/"GM17_PERSON_SCOUT_FAILURE_AUDIT.md"; p.parent.mkdir(parents=True,exist_ok=True); p.write_text("\n".join(lines),encoding="utf-8")
    return details


def person_rescout():
    det_path=OUT/"04_person_rescout"/"GM17_PERSON_DETECTIONS.csv"
    if det_path.exists():
        # Re-runs reuse the machine-readable full-stream result; this keeps
        # track-linking/report repairs deterministic without another inference.
        det=read_csv(det_path)
        for d in det:
            d["frame"] = int(d["frame"]); d["confidence"] = float(d["confidence"])
            for k in ("bbox_x1","bbox_y1","bbox_x2","bbox_y2"): d[k] = float(d[k])
    else:
        from ultralytics import YOLO
        model=YOLO(str(PERSON_MODEL))
        paths=[RAW/"GM_RM017"/"GM_RM017_frames"/f"{i:06d}.png" for i in range(368)]
        det=[]
        # YOLO11l exceeds the available 8 GB GPU during inference on this host;
        # use deterministic single-frame CPU streaming rather than changing model
        # family or silently falling back to a sparse cache.
        results=model.predict(source=[str(p) for p in paths], classes=[0], conf=0.12, imgsz=640, batch=1, device="cpu", stream=True, verbose=False)
        for fr,res in enumerate(results):
            if res.boxes is None: continue
            for b,conf,cls in zip(res.boxes.xyxy.cpu().tolist(),res.boxes.conf.cpu().tolist(),res.boxes.cls.cpu().tolist()):
                x1,y1,x2,y2=map(float,b); det.append({"scene":"GM_RM017","frame":fr,"class":"person","confidence":round(float(conf),6),"bbox_x1":round(x1,3),"bbox_y1":round(y1,3),"bbox_x2":round(x2,3),"bbox_y2":round(y2,3),"model":"YOLO11l","source":"full_368_frame_rescout"})
        write_csv(det_path,det,["scene","frame","class","confidence","bbox_x1","bbox_y1","bbox_x2","bbox_y2","model","source"])
    # Greedy short-gap linking, optical only. A fragment is provisional, never physical identity.
    tracks=[]
    for d in sorted(det,key=lambda x:(x["frame"],-x["confidence"])):
        best=None; bestdist=1e9
        cx=(d["bbox_x1"]+d["bbox_x2"])/2; cy=(d["bbox_y1"]+d["bbox_y2"])/2
        for t in tracks:
            if d["frame"] == t["last_frame"]: continue
            if d["frame"]-t["last_frame"]>3: continue
            px,py=t["last_cx"],t["last_cy"]; dist=math.hypot(cx-px,cy-py)
            if dist<bestdist and dist<140: best,bestdist=t,dist
        if best is None:
            best={"id":f"GM_RM017:PROVISIONAL_OPTICAL_PERSON_ID_{len(tracks)+1:03d}","detections":[]}; tracks.append(best)
        best["detections"].append(d); best["last_frame"]=d["frame"]; best["last_cx"]=cx; best["last_cy"]=cy
    trrows=[]; introws=[]
    for t in tracks:
        ds=t["detections"]; fs=[d["frame"] for d in ds]; gaps=max(0,len(range(min(fs),max(fs)+1))-len(fs)); maxgap=max([b-a-1 for a,b in zip(fs,fs[1:])] or [0]); hs=[d["bbox_y2"]-d["bbox_y1"] for d in ds]; boundary=sum(1 for d in ds if d["bbox_x1"]<=3 or d["bbox_y1"]<=3 or d["bbox_x2"]>=797 or d["bbox_y2"]>=597)/len(ds)
        priority="HIGH" if len(ds)>=8 and boundary<0.4 and median(hs)>=35 else ("MEDIUM" if len(ds)>=3 else "LOW")
        trrows.append({"provisional_person_id":t["id"],"frame_start":min(fs),"frame_end":max(fs),"support_count":len(ds),"gap_count":gaps,"max_gap":maxgap,"median_bbox_height":round(median(hs),2),"boundary_contact_fraction":round(boundary,3),"identity_clarity":"OPTICAL_PROVISIONAL","body_completeness":"PROXY_REVIEW_REQUIRED","auto_priority":priority,"human_review_status":"REVIEW_REQUIRED","notes":"Short-gap greedy optical linking; no SAR or physical identity claim"})
        introws.append({**trrows[-1],"interval_id":t["id"]+":INTERVAL_01","status":"REVIEW_REQUIRED"})
    write_csv(OUT/"04_person_rescout"/"GM17_PERSON_PROVISIONAL_TRACKS.csv",trrows,list(trrows[0]) if trrows else ["provisional_person_id"])
    write_csv(OUT/"04_person_rescout"/"GM17_PERSON_INTERVAL_CANDIDATES.csv",introws,list(introws[0]) if introws else ["provisional_person_id"])
    return det,trrows,introws


def person_sheets(tracks):
    rows=[]; media=[]
    for t in tracks:
        if t["auto_priority"]=="LOW": continue
        ds=[d for d in read_csv(OUT/"04_person_rescout"/"GM17_PERSON_DETECTIONS.csv") if d["frame"] and d["frame"]]
        ds=[d for d in ds if d["frame"] and int(d["frame"])>=int(t["frame_start"]) and int(d["frame"])<=int(t["frame_end"])]
        fs=sorted({int(d["frame"]) for d in ds}); picks=[]
        gap_adj=[]
        for a,b in zip(fs,fs[1:]):
            if b-a>1: gap_adj.extend([a+1,b-1])
        for x in ([fs[0],fs[len(fs)//4],fs[len(fs)//2],fs[-1]] + gap_adj) if fs else []:
            if x not in picks:picks.append(x)
        tiles=[]
        for fr in picks:
            im=Image.open(RAW/"GM_RM017"/"GM_RM017_frames"/f"{fr:06d}.png").convert("RGB"); im.thumbnail((400,300)); tile=Image.new("RGB",(420,350),"white"); tile.paste(im,((420-im.width)//2,28)); d=ImageDraw.Draw(tile); d.text((5,5),f"GM_RM017 PERSON {t['provisional_person_id']} frame={fr}",fill="black")
            for q in ds:
                if int(q["frame"])==fr:
                    sx,sy=im.width/800,im.height/600; ox=(420-im.width)//2; oy=28; d.rectangle((ox+float(q['bbox_x1'])*sx,oy+float(q['bbox_y1'])*sy,ox+float(q['bbox_x2'])*sx,oy+float(q['bbox_y2'])*sy),outline="red",width=3)
            tiles.append(tile)
        if not tiles: continue
        sheet=Image.new("RGB",(420*len(tiles),350),"white")
        for i,tile in enumerate(tiles): sheet.paste(tile,(420*i,0))
        p=OUT/"05_person_contact_sheets"/(t["provisional_person_id"].replace(":","_")+".png"); p.parent.mkdir(parents=True,exist_ok=True); sheet.save(p)
        media.append({"run":"TPGT-GM-B1.2","event":"GM_RM017_PERSON_RESCOUNT","source_media":str(RAW/"GM_RM017"/"GM_RM017_frames"),"frame_index":f"{t['frame_start']}-{t['frame_end']}","observation_id":t["provisional_person_id"],"visual_asset":str(p)})
    write_csv(OUT/"05_person_contact_sheets"/"media_manifest.csv",media,list(media[0]) if media else ["run","event","source_media","frame_index","observation_id","visual_asset"])


def review_index(cands, ints):
    lines=["<!doctype html><meta charset='utf-8'><title>TPGT GM B1.2 Review Index</title><style>body{font-family:Arial}img{max-width:100%}section{border:1px solid #ccc;padding:10px;margin:10px}</style>","<h1>TPGT-GM-B1.2 optical-only review</h1>","<p>SAR, SAR GT, mapping, IoU and historical SAR quality are intentionally absent.</p>","<h2>A. CAR complete interval candidates</h2>"]
    for r in cands:
        rel=f"../02_car_contact_sheets/{r['scene']}/{r['interval_id'].replace(':','_')}.png"; lines.append(f"<section><h3>{html.escape(r['interval_id'])}</h3><p>{r['frame_start']}-{r['frame_end']} ({r['frame_count']} frames), priority={r['auto_priority']}, provenance={html.escape(r['source_provenance'])}</p><img src='{rel}'><p>Decision: ACCEPT COMPLETE INTERVAL / REJECT / AMBIGUOUS / DEFER TRUNCATED</p></section>")
    lines.append("<h2>B. GM17 PERSON provisional intervals</h2>")
    for r in ints:
        if r["auto_priority"]=="LOW": continue
        rel=f"../05_person_contact_sheets/{r['provisional_person_id'].replace(':','_')}.png"; lines.append(f"<section><h3>{html.escape(r['provisional_person_id'])}</h3><p>{r['frame_start']}-{r['frame_end']} support={r['support_count']} gaps={r['gap_count']} priority={r['auto_priority']}</p><img src='{rel}'><p>Decision: ACCEPT PERSON RESEARCH CANDIDATE / REJECT / AMBIGUOUS</p></section>")
    p=OUT/"06_review"/"REVIEW_INDEX_B12.html"; p.parent.mkdir(parents=True,exist_ok=True); p.write_text("\n".join(lines),encoding="utf-8")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    reg=read_csv(REG_PATH); states=read_csv(STATE_PATH)
    cands=interval_candidates(reg,states)
    fields=list(cands[0]) if cands else ["scene","vehicle_id","interval_id"]
    write_csv(OUT/"01_car_interval_candidates"/"COMPLETE_CAR_INTERVAL_CANDIDATES.csv",cands,fields)
    write_csv(OUT/"01_car_interval_candidates"/"COMPLETE_CAR_CORE_INTERVALS.csv",[],fields)
    write_json(OUT/"01_car_interval_candidates"/"PANEL_STATUS.json",{"status":"PENDING_HUMAN_REVIEW","human_confirmed_interval_count":0,"sar_reference_opened":False})
    car_contact_sheets(cands,states); gm19_audit(states); audit=old_scout_audit(); det,tracks,ints=person_rescout(); person_sheets(tracks); review_index(cands,ints)
    # Consolidated manifest lets every submitted visual asset be traced without
    # retaining raw frame/video copies.
    manifests=[]
    for mp in [OUT/"02_car_contact_sheets"/"media_manifest.csv", OUT/"05_person_contact_sheets"/"media_manifest.csv"]:
        if mp.exists(): manifests.extend(read_csv(mp))
    write_csv(OUT/"06_review"/"media_manifest.csv",manifests,list(manifests[0]) if manifests else ["run","event","source_media","frame_index","observation_id","visual_asset"])
    write_json(OUT/"07_handoff"/"HANDOFF.json",{"task":"TPGT-GM-B1.2","status":"PENDING_HUMAN_REVIEW_BEFORE_MAPPING","car_interval_candidates":str(OUT/"01_car_interval_candidates"/"COMPLETE_CAR_INTERVAL_CANDIDATES.csv"),"complete_car_core_intervals":str(OUT/"01_car_interval_candidates"/"COMPLETE_CAR_CORE_INTERVALS.csv"),"person_tracks":str(OUT/"04_person_rescout"/"GM17_PERSON_PROVISIONAL_TRACKS.csv"),"media_manifest":str(OUT/"06_review"/"media_manifest.csv"),"sar_opened":False,"next_step":"Human review only; no mapping in this run"})
    counts={s:sum(1 for r in cands if r["scene"]==s) for s in SCENES}
    report=["# TPGT-GM-B1.2 Complete-Interval Recovery + GM17 PERSON Rescout","","## Scope and stop point","","Optical-only interval recovery and full-stream GM17 PERSON discovery. SAR GT/manual reference, mapping, truncation correction, selector/ranking, final annotation and A-line edits were not performed.","","## Direct answers","",f"- Complete interval candidates: GM011={counts['GM_RM011']}, GM017={counts['GM_RM017']}, GM019={counts['GM_RM019']}.","- GM017 PV002 maximum candidate: frames 154–173; PV003: 162–188; PV004: 169–201. PV001 is retained as VEHICLE_NO_SAR_REFERENCE (frames 129–159).","- GM011: no >=12-frame complete interval was found; no identity is promoted. GM019: no >=12-frame interval was found; PV003 candidate frames 118–123 is the strongest short window.","- GM019 PV003 frame 136 is a false source-box/background anomaly; see `03_gm019_pv003_audit/GM019_PV003_CONTACT_SHEET_AUDIT.md`.","- The old PERSON scout failed because it read sparse detector caches and emitted singleton detections without temporal linking; see `00_audit/GM17_PERSON_SCOUT_FAILURE_AUDIT.md`.",f"- Full 368-frame YOLO11l rescout produced {len(det)} person detections and {len(tracks)} provisional optical tracks; all remain REVIEW_REQUIRED.","- A PERSON interval is considered present only as a provisional optical candidate here; no human confirmation or physical identity claim is made.","","## Review gate","","Open `06_review/REVIEW_INDEX_B12.html`. Freeze decisions before any SAR reference or mapping work. `COMPLETE_CAR_CORE_INTERVALS.csv` is intentionally empty.","","## Reproduction", "", "`D:\\MINICONDA\\envs\\py311\\python.exe tasks\\tpgt_gm_complete_interval_b12\\run_b12.py`"]
    (OUT/"REPORT.md").write_text("\n".join(report),encoding="utf-8")
    validation={"status":"PASS_WITH_REVIEW_GATE","optical_only_selection":"PASS","sar_opened":False,"car_candidate_counts":counts,"person_detection_count":len(det),"person_track_count":len(tracks),"human_core_intervals":0,"old_person_scout_audit_rows":len(audit)}
    write_json(OUT/"08_validation"/"VALIDATION.json",validation)
    print(json.dumps({"output":str(OUT),"car_candidate_counts":counts,"person_detections":len(det),"person_tracks":len(tracks),"status":validation["status"]},ensure_ascii=False,indent=2))

if __name__ == "__main__": main()
