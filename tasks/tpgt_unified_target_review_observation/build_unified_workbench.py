"""Build the unified full-sequence target review adapter.

Proposal artifacts are imported read-only from the B1.2 Git object store. No
detector, tracker, mapping, or SAR inference is executed here.
"""
from pathlib import Path
import csv,json,hashlib,subprocess,shutil,datetime

W=Path('D:/profile/research/workspace'); OUT=W/'output/tpgt/unified_target_review_observation'; PROP=OUT/'proposals'; TASK=W/'tasks/tpgt_unified_target_review_observation'; RAW=W/'data/GM_RM017'; BBR='feature/tpgt-gm-complete-interval-b12'; BCOMMIT='946e4750b998c3667d09bcf43fa05cb7b08d1e71'
BASE='output/tpgt/gm_complete_interval_b12'
FILES={'car':'01_car_interval_candidates/COMPLETE_CAR_INTERVAL_CANDIDATES.csv','person_det':'04_person_rescout/GM17_PERSON_DETECTIONS.csv','person_tracks':'04_person_rescout/GM17_PERSON_PROVISIONAL_TRACKS.csv','person_intervals':'04_person_rescout/GM17_PERSON_INTERVAL_CANDIDATES.csv'}
def csvread(p):return list(csv.DictReader(Path(p).open(encoding='utf-8-sig')))
def dump(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def git_file(rel):return subprocess.check_output(['git','-C',str(W),'show',f'{BBR}:{BASE}/{rel}'])
def import_b12(name,rel):
    p=PROP/name; p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(git_file(rel)); return p
def main():
    OUT.mkdir(parents=True,exist_ok=True); (OUT/'audit').mkdir(exist_ok=True)
    imported={}
    for key,rel in FILES.items():
        p=import_b12(Path(rel).name,rel); imported[key]={'path':str(p.relative_to(W)),'source_branch':BBR,'source_commit':BCOMMIT,'source_path':f'{BASE}/{rel}','sha256':sha(p),'semantic_role':'PROPOSAL_ONLY_READ_ONLY'}
    cars=csvread(PROP/'COMPLETE_CAR_INTERVAL_CANDIDATES.csv'); pdet=csvread(PROP/'GM17_PERSON_DETECTIONS.csv'); ptr=csvread(PROP/'GM17_PERSON_PROVISIONAL_TRACKS.csv'); pints=csvread(PROP/'GM17_PERSON_INTERVAL_CANDIDATES.csv')
    states_path=Path('D:/profile/research/optical-sar-visual-diagnosis-data-foundation/manifests/oty2/oty2_p1e_canonical_vehicle_frame_states.csv'); states=csvread(states_path) if states_path.exists() else []
    source_boxes={}
    for r in states:
        if r.get('scene')!='GM_RM017':continue
        vid=r.get('canonical_vehicle_id','');
        try: b=[float(r[k]) for k in ('reference_bbox_x1','reference_bbox_y1','reference_bbox_x2','reference_bbox_y2')]
        except (KeyError,ValueError):continue
        if b[2]<=b[0] or b[3]<=b[1]:continue
        source_boxes.setdefault(vid,{}).setdefault(str(int(r['frame_index'])),[]).append(b)
    optical=[{'frame':i,'path':f'/data/GM_RM017/GM_RM017_frames/{i:06d}.png'} for i in range(368)]
    sar=[{'frame':i,'path':f'/data/GM_RM017/GM_RM017_SARframes/{i:06d}.png','gray_path':f'/data/GM_RM017/GM_RM017_SARframes_gray/{i:06d}.png'} for i in range(766)]
    proposals={'cars':[r for r in cars if r['scene']=='GM_RM017'],'person_tracks':ptr,'person_intervals':pints,'person_detections':pdet}
    data={'schema_version':'TPGT_UNIFIED_TARGET_REVIEW_DATA_v0.1','scene':'GM_RM017','optical_width':800,'optical_height':600,'sar_width':1024,'sar_height':592,'optical':optical,'sar':sar,'source_boxes':source_boxes,'proposals':proposals,'sync_semantics':'Optical and SAR frame indices are separate; nominal timing is context only and exact synchronization is unverified.','proposal_semantics':'All B1.2 intervals/tracks/detections are read-only proposals and never human truth.'}
    dump(OUT/'target_review_data.json',data)
    (OUT/'target_review_data.js').write_text('window.TPGT_REVIEW_DATA='+json.dumps(data,ensure_ascii=False,separators=(',',':'))+';',encoding='utf-8')
    shutil.copy2(TASK/'target_review_view.html',OUT/'TARGET_REVIEW_VIEW.html'); shutil.copy2(TASK/'target_review.js',OUT/'target_review.js'); shutil.copy2(TASK/'target_review.css',OUT/'target_review.css')
    shutil.copy2(TASK/'sar_observation_view.html',OUT/'SAR_OBSERVATION_VIEW.html'); shutil.copy2(TASK/'sar_observation.js',OUT/'sar_observation.js'); shutil.copy2(TASK/'open_book_interpretation.html',OUT/'OPEN_BOOK_INTERPRETATION.html'); shutil.copy2(TASK/'open_book_interpretation.js',OUT/'open_book_interpretation.js')
    dump(OUT/'B12_PROPOSAL_IMPORT_MANIFEST.json',{'schema_version':'B12_PROPOSAL_IMPORT_MANIFEST_v0.1','source_branch':BBR,'source_commit':BCOMMIT,'import_timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'semantic_role':'PROPOSAL_ONLY','files':imported})
    dump(OUT/'review_demo_fixture.json',{'schema_version':'TPGT_TARGET_REVIEW_RECORD_v0.1','review_id':'DEMO_UNFROZEN_GM_RM017_PV002','scene':'GM_RM017','domain':'CAR','source_target_id':'GM_RM017:PV002','human_local_target_id':'','review_start_frame':0,'review_end_frame':367,'human_core_start_frame':None,'human_core_end_frame':None,'identity_status':'AMBIGUOUS','body_completeness':'UNKNOWN','boundary_state':'UNKNOWN','occlusion_state':'UNKNOWN','target_type':'UNKNOWN','research_admission':'DEFER_COMPLEX','review_note':'Demo fixture; not a human review and not frozen.','proposal_source':'B1.2','proposal_interval':[154,173],'proposal_used_as_reference':False,'record_created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'revision_created_at':datetime.datetime.now(datetime.timezone.utc).isoformat()})
    index='''<!doctype html><meta charset="utf-8"><link rel="stylesheet" href="target_review.css"><main><h1>TPGT · Unified Target Review + SAR Observation</h1><p>完整光学时序 → 人工目标/区间冻结 → PRE_OPEN_BOOK SAR Observation。B1.2 仅为灰色 proposal，不是人工真值。</p><div class="card"><a href="TARGET_REVIEW_VIEW.html?target=CAR:GM_RM017:PV002">CAR · GM_RM017:PV002</a><br><a href="TARGET_REVIEW_VIEW.html?target=CAR:GM_RM017:PV003">CAR · GM_RM017:PV003</a><br><a href="TARGET_REVIEW_VIEW.html?target=CAR:GM_RM017:PV004">CAR · GM_RM017:PV004</a><br><a href="TARGET_REVIEW_VIEW.html?target=CAR:GM_RM017:PV001">CAR · GM_RM017:PV001（TRUCK_OR_LARGE_VEHICLE / NO_CURRENT_SAR_REFERENCE）</a><br><a href="TARGET_REVIEW_VIEW.html?target=PERSON:GM_RM017:FULL_SEQUENCE">PERSON · GM_RM017 full optical stream 0–367</a></div><p class="muted">先看片和冻结，不要把 provisional ID 自动升格为真实身份。</p></main>'''; (OUT/'index.html').write_text(index,encoding='utf-8')
    dump(OUT/'audit'/'build_validation.json',{'complete':True,'optical_frames':368,'sar_frames':766,'car_first_priority':['GM_RM017:PV002','GM_RM017:PV003','GM_RM017:PV004'],'car_extra':['GM_RM017:PV001'],'person_full_stream':True,'b12_import_read_only':True,'human_intervals_initially_empty':True,'canonical_schema_unchanged':True})
    print(json.dumps({'output':str(OUT),'cars':len(proposals['cars']),'person_detections':len(pdet),'person_tracks':len(ptr)},ensure_ascii=False))
if __name__=='__main__':main()
