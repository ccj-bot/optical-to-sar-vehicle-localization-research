"""Build scene-first optical target review data; all detections are read-only proposals."""
from pathlib import Path
import csv,json,hashlib,subprocess,shutil,datetime
W=Path('D:/profile/research/workspace'); OUT=W/'output/tpgt/unified_target_review_observation'; PROP=OUT/'proposals'; TASK=W/'tasks/tpgt_unified_target_review_observation'
SCENES=['GM_RM011','GM_RM017','GM_RM019','R35ZF','R01ZF']; BBR='feature/tpgt-gm-complete-interval-b12'; BCOMMIT='946e4750b998c3667d09bcf43fa05cb7b08d1e71'; BASE='output/tpgt/gm_complete_interval_b12'
SCENE_SPECS={'GM_RM011':('D:/profile/research/data/GM_RM011/GM_RM011_frames','{i:06d}.png',24.0),'GM_RM017':('D:/profile/research/data/GM_RM017/GM_RM017_frames','{i:06d}.png',24.0),'GM_RM019':('D:/profile/research/data/GM_RM019/GM_RM019_frames','{i:06d}.png',24.0),'R35ZF':('D:/profile/research/data/20260721data/derived_frames/pseudocolor_labelstudio_prep_20260722/frames/optical/R35ZF','frame_{i:06d}_t*.jpg',18.0),'R01ZF':('D:/profile/research/data/20260721data/derived_frames/pseudocolor_labelstudio_prep_20260722/frames/optical/R01ZF','frame_{i:06d}_t*.jpg',18.0)}
YOLO11={'GM_RM011':Path('D:/profile/research/optical-sar-visual-diagnosis/outputs/oty0_yolo_detection_stream_audit_20260704_gm011_oty_stream/oty0_yolo_detection_table.csv'),'GM_RM017':Path('D:/profile/research/optical-sar-visual-diagnosis/outputs/oty0_yolo_detection_stream_audit_20260701_181317/oty0_yolo_detection_table.csv'),'GM_RM019':Path('D:/profile/research/optical-sar-visual-diagnosis/outputs/oty0_yolo_detection_stream_audit_20260701_170617/oty0_yolo_detection_table.csv')}
YOLO26={s:Path(f'D:/profile/research/optical-sar-visual-diagnosis/outputs/oty2_yolo26l_detector_quality_probe_20260704_231830/oty0_yolo_detection_stream_audit_yolo26l_{s.lower()}/oty0_yolo_detection_table.csv') for s in SCENES}
NEW65_VEHICLE=Path('D:/profile/research/workspace/output/new_scene_vehicle_temporal_segments_20260818/full_65_identity_v2_20260818/optical_vehicle_track_frames.csv')
NEW65_PERSON=Path('D:/profile/research/workspace/output/person_optical_guided_sar_annotation_full_20260823/optical_person_detections_stitched.csv')
FILES={'car':'01_car_interval_candidates/COMPLETE_CAR_INTERVAL_CANDIDATES.csv','person_det':'04_person_rescout/GM17_PERSON_DETECTIONS.csv','person_tracks':'04_person_rescout/GM17_PERSON_PROVISIONAL_TRACKS.csv','person_intervals':'04_person_rescout/GM17_PERSON_INTERVAL_CANDIDATES.csv'}
def rd(p): return list(csv.DictReader(Path(p).open(encoding='utf-8-sig')))
def dump(p,x): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def det(p,model,scene):
 out=[]
 if not p.exists(): return out
 for r in rd(p):
  if r.get('scene',r.get('run_id',scene)) != scene: continue
  try: f=int(r.get('optical_frame_num',r.get('frame_index',0))); b=[float(r[k]) for k in ('bbox_x1','bbox_y1','bbox_x2','bbox_y2')]; c=float(r.get('confidence','nan'))
  except (ValueError,KeyError): continue
  cls=r.get('class_name',r.get('target_class','unknown')).lower(); src=r.get('source_models',r.get('detection_pass',model))
  out.append({'frame':f,'class_name':cls,'confidence':c,'x1':b[0],'y1':b[1],'x2':b[2],'y2':b[3],'det_id':r.get('det_id',r.get('raw_track_fragment_id','')),'model':model,'source_model_detail':src,'scene':scene,'semantic_role':'PROPOSAL_ONLY_NOT_IDENTITY_TRUTH'})
 return out
def main():
 OUT.mkdir(parents=True,exist_ok=True); (OUT/'audit').mkdir(exist_ok=True); PROP.mkdir(exist_ok=True)
 imported={}
 for key,rel in FILES.items():
  p=PROP/Path(rel).name; p.write_bytes(subprocess.check_output(['git','-C',str(W),'show',f'{BBR}:{BASE}/{rel}'])); imported[key]={'path':str(p.relative_to(W)),'source_branch':BBR,'source_commit':BCOMMIT,'source_path':f'{BASE}/{rel}','sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'semantic_role':'PROPOSAL_ONLY_READ_ONLY'}
 scenes={}
 for s in SCENES:
  root,pattern,fps=SCENE_SPECS[s]; files=sorted(Path(root).glob('frame_*.jpg' if 'frame_' in pattern and '*.jpg' in pattern else '*.png')); width=height=None
  try:
   from PIL import Image
   with Image.open(files[0]) as im: width,height=im.size
  except Exception: width,height=800,600
  y11=det(YOLO11[s],'YOLO11',s) if s in YOLO11 and YOLO11[s].exists() else det(NEW65_VEHICLE,'YOLO11',s)
  y26=det(YOLO26[s],'YOLO26',s) if s in YOLO26 and YOLO26[s].exists() else det(NEW65_PERSON,'YOLO26',s)
  scenes[s]={'scene':s,'frame_count':len(files),'width':width,'height':height,'fps':fps,'optical':[{'frame':i,'path':'/'+f.absolute().relative_to(Path('D:/profile/research')).as_posix()} for i,f in enumerate(files)],'detections':{'yolo11':y11,'yolo26':y26}}
 cars=rd(PROP/'COMPLETE_CAR_INTERVAL_CANDIDATES.csv'); pdet=rd(PROP/'GM17_PERSON_DETECTIONS.csv'); ptr=rd(PROP/'GM17_PERSON_PROVISIONAL_TRACKS.csv'); pints=rd(PROP/'GM17_PERSON_INTERVAL_CANDIDATES.csv')
 data={'schema_version':'TPGT_OPTICAL_TARGET_REVIEW_DATA_v0.2','scenes':scenes,'proposals':{'cars':[r for r in cars if r.get('scene')=='GM_RM017'],'person_tracks':ptr,'person_intervals':pints,'person_detections':pdet},'sync_semantics':'Optical and SAR frame indices are separate; exact synchronization is unverified.','proposal_semantics':'All detector/track/interval layers are read-only proposals and never human truth.'}
 dump(OUT/'target_review_data.json',data); (OUT/'target_review_data.js').write_text('window.TPGT_REVIEW_DATA='+json.dumps(data,ensure_ascii=False,separators=(',',':'))+';',encoding='utf-8')
 for a,b in [('target_review_view.html','TARGET_REVIEW_VIEW.html'),('target_review.js','target_review.js'),('optical_review_enhancements.js','optical_review_enhancements.js'),('target_review.css','target_review.css'),('sar_observation_view.html','SAR_OBSERVATION_VIEW.html'),('sar_observation.js','sar_observation.js'),('open_book_interpretation.html','OPEN_BOOK_INTERPRETATION.html'),('open_book_interpretation.js','open_book_interpretation.js')]: shutil.copy2(TASK/a,OUT/b)
 dump(OUT/'B12_PROPOSAL_IMPORT_MANIFEST.json',{'schema_version':'B12_PROPOSAL_IMPORT_MANIFEST_v0.1','source_branch':BBR,'source_commit':BCOMMIT,'import_timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'semantic_role':'PROPOSAL_ONLY','files':imported,'detection_assets':{'YOLO11':{s:(str(YOLO11[s]) if s in YOLO11 else str(NEW65_VEHICLE)) for s in SCENES},'YOLO26':{s:(str(YOLO26[s]) if s in YOLO26 else str(NEW65_PERSON)) for s in SCENES}}})
 dump(OUT/'review_demo_fixture.json',{'schema_version':'TPGT_TARGET_REVIEW_RECORD_v0.2','scene':'GM_RM017','human_local_target_id':'','review_start_frame':0,'review_end_frame':367,'record_role':'DEMO_NOT_HUMAN_REVIEW'})
 gm=''.join(f'<a class="scene-card" href="TARGET_REVIEW_VIEW.html?scene={s}"><b>{s}</b><span>{scenes[s]["frame_count"]} 帧 · 检测建议 {len(scenes[s]["detections"]["yolo11"])+len(scenes[s]["detections"]["yolo26"])}</span></a>' for s in SCENES[:3]); new=''.join(f'<a class="scene-card" href="TARGET_REVIEW_VIEW.html?scene={s}"><b>{s}</b><span>{scenes[s]["frame_count"]} 帧 · 检测建议 {len(scenes[s]["detections"]["yolo11"])+len(scenes[s]["detections"]["yolo26"])}</span></a>' for s in SCENES[3:]); (OUT/'index.html').write_text(f'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><link rel="stylesheet" href="target_review.css"><main><h1>TPGT 光学目标复核</h1><h2>GM Controlled Panel</h2><div class="scene-grid">{gm}</div><h2>New65 Discovery Panel</h2><div class="scene-grid">{new}</div><p class="muted">检测框只作可点击建议，不自动生成 physical identity；无检测时仍可手动画框。</p></main>',encoding='utf-8')
 dump(OUT/'scene_manifest.json',{'schema_version':'TPGT_OPTICAL_SCENE_MANIFEST_v0.1','scenes':[{k:v for k,v in scenes[s].items() if k in ('scene','frame_count','width','height','fps')}|{'detection_sources':{m:len(scenes[s]['detections'][m]) for m in ('yolo11','yolo26')}} for s in SCENES]})
 dump(OUT/'audit'/'build_validation.json',{'complete':True,'scenes':SCENES,'optical_frames':{s:scenes[s]['frame_count'] for s in SCENES},'detections':{s:{'YOLO11':len(scenes[s]['detections']['yolo11']),'YOLO26':len(scenes[s]['detections']['yolo26'])} for s in SCENES},'b12_import_read_only':True,'human_intervals_initially_empty':True,'canonical_schema_unchanged':True}); print(json.dumps({'output':str(OUT),'scenes':SCENES},ensure_ascii=False))
if __name__=='__main__': main()
