"""Build the thin-adapter TPGT Phase 1A blind-first observation workbench.

This consumes the already materialized Phase 1A evidence packs and writes only
the new observation_workbench namespace plus per-pack page/data adapters.
"""
from pathlib import Path
import csv,json,hashlib,shutil,re

W=Path('D:/profile/research/workspace'); O=W/'output/tpgt/phase_1a'; PACKS=O/'evidence_packs'; TASK=W/'tasks/tpgt_phase_1a/observation_workbench'; OUT=O/'observation_workbench'; ASSET=OUT/'assets'
MORPH=['POINT_LIKE','COMPACT_REGION','ELONGATED_REGION','BAND_LIKE','MULTI_COMPONENT','DIFFUSE_REGION','BOUNDARY_ATTACHED','UNCLEAR','OTHER']
TRANS=['APPEAR','DISAPPEAR','SHIFT','ELONGATE','CONTRACT','SPLIT','MERGE','DOMINANT_SWITCH','DISPLAY_BRIGHTNESS_INCREASE','DISPLAY_BRIGHTNESS_DECREASE','INTERMITTENT','NO_CLEAR_CHANGE','UNCERTAIN','OTHER']

def readcsv(p): return list(csv.DictReader(Path(p).open(encoding='utf-8-sig')))
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def dump(p,x): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')

def build_pack(q, manual, seeds, library):
    eid=q['event_hypothesis_id']; p=PACKS/eid; manifest=readcsv(p/'frame_manifest.csv')
    optical=[{'f':int(r['f']),'t':float(r['t']),'path':r['path']} for r in manifest if r['modality']=='optical']
    sar=[{'f':int(r['f']),'t':float(r['t']),'path':r['path'],'gray':r['gray']} for r in manifest if r['modality']=='sar']
    source=json.loads((p/'source_provenance_card.json').read_text(encoding='utf-8')); unknown=json.loads((p/'uncertainty_unknown_card.json').read_text(encoding='utf-8')); controls=json.loads((p/'control_candidates.json').read_text(encoding='utf-8'))
    # Reuse the already generated source optical overlay payload from the old page.
    # This is extracted before the thin adapter replaces that page and never reads SAR reference.
    old=(p/'OBSERVATION_VIEW.html').read_text(encoding='utf-8'); match=re.search(r'const D=(\{.*?\});\s*const \$',old,re.S)
    old_data=json.loads(match.group(1)) if match else {}
    if not old_data and (p/'workbench_data.js').exists():
        cached=(p/'workbench_data.js').read_text(encoding='utf-8'); old_data=json.loads(cached.split('=',1)[1].rstrip(';'))
    boxes=old_data.get('boxes',{})
    universe=readcsv(O/'provisional_event_universe.csv'); rows=[r for r in universe if r['event_hypothesis_id']==eid]
    frame_start=int(sar[0]['f']); frame_end=int(sar[-1]['f']); run=q['run_id']
    data={'schema_version':'TPGT_WORKBENCH_DATA_v0.1','event_hypothesis_id':eid,'domain':q['domain'],'run_id':run,'title':f"{run} · {q['domain']} · {q['source_identity']}",'optical_fps':float(source['source_videos'][0]['native_fps']),'sar_fps':float(source['source_videos'][1]['native_fps']),'sar_width':int(source['source_videos'][1]['native_dimensions'][0]),'sar_height':int(source['source_videos'][1]['native_dimensions'][1]),'optical':optical,'sar':sar,'boxes':boxes,'support_ranges':json.loads(rows[0].get('support_ranges_optical_frames','[]')) if rows else [],'sar_source':'decoded pseudocolor source-video pixels','sync_semantics':'Nominal per-stream FPS only; optical-SAR zero offset/drift are unverified; frame index equality is not assumed.','source_card':source,'unknown_card':unknown,'controls':controls}
    (p/'workbench_data.js').write_text('window.TPGT_WORKBENCH_DATA='+json.dumps(data,ensure_ascii=False,separators=(',',':'))+';',encoding='utf-8')
    man=[dict(x,frame_index=int(x['sar_frame_index'])) for x in manual if x['run_id']==run and frame_start<=int(x['sar_frame_index'])<=frame_end]
    der=[dict(x,frame_index=int(x['sar_frame_index'])) for x in seeds if x['run_id']==run and frame_start<=int(x['sar_frame_index'])<=frame_end]
    lib=[dict(x,frame_index=int(x['sar_frame_index'])) for x in library if x.get('run_id')==run and frame_start<=int(x['sar_frame_index'])<=frame_end]
    registry={'schema_version':'TPGT_OPEN_BOOK_REGISTRY_v0.1','event_hypothesis_id':eid,'layers':{'manual_reference':{'label':'Manual PERSON/CAR SAR reference','provenance_kind':'MANUAL','source':'repaired_manual_anchor_boxes.csv'},'derived_reference':{'label':'Derived/interpolated SAR seed','provenance_kind':'DERIVED','source':'interpolated_seed_boxes.csv'},'historical_library':{'label':'Historical library / proxy metadata','provenance_kind':'PROXY','source':'historical library export'}},'manual_reference':man,'derived_reference':der,'historical_library':lib,'identity_annotations':[],'future_car_annotation_interface':'TPGT_IDENTITY_VISIBILITY_ANNOTATION_v0.1','toggles':{}}
    dump(p/'open_book_registry.json',registry)
    dump(OUT/'records'/f'{eid}.README.json',{'purpose':'Append-only observation revisions created by serve_workbench.py','event_hypothesis_id':eid})

def main():
    OUT.mkdir(parents=True,exist_ok=True); ASSET.mkdir(parents=True,exist_ok=True)
    for name in ('workbench.css','workbench.js'): shutil.copy2(TASK/name,ASSET/name)
    schema={'$schema':'https://json-schema.org/draft/2020-12/schema','$id':'TPGT_OBSERVATION_RECORD_v0.1','type':'object','additionalProperties':True,'required':['schema_version','observation_id','event_hypothesis_id','domain','run_id','revision','observation_phase','sar_frame_start','sar_frame_end','spatial_marks','morphology','transitions','continuity','human_certainty','bookmarks','observation_text','display_semantics','sync_semantics','created_at','updated_at','provenance'],'properties':{'schema_version':{'const':'TPGT_OBSERVATION_RECORD_v0.1'},'domain':{'enum':['CAR','PERSON','UNKNOWN']},'observation_phase':{'enum':['PRE_OPEN_BOOK','POST_OPEN_BOOK']},'spatial_marks':{'type':'array'},'morphology':{'type':'array','items':{'enum':MORPH}},'transitions':{'type':'array','items':{'enum':TRANS}},'continuity':{'enum':['CONTINUOUS','INTERMITTENT','SINGLE_FRAME','UNCERTAIN']},'human_certainty':{'enum':['CLEAR','LIKELY','AMBIGUOUS']},'display_semantics':{'type':'object','properties':{'gray_is_bgr2gray_derived':{'const':True}}}}}
    dump(OUT/'schema'/'TPGT_OBSERVATION_RECORD_v0.1.json',schema)
    dump(OUT/'schema'/'TPGT_INTERPRETATION_CANDIDATE_v0.1.json',{'type':'object','required':['schema_version','event_hypothesis_id','interpretation_text'],'properties':{'schema_version':{'const':'TPGT_INTERPRETATION_CANDIDATE_v0.1'},'possible_hypotheses':{'type':['string','array']}}})
    dump(OUT/'schema'/'TPGT_IDENTITY_VISIBILITY_ANNOTATION_v0.1.json',{'type':'object','required':['target_annotation_id','run_id','domain','identity_semantics','frame_start','frame_end','source','provenance'],'properties':{'domain':{'const':'CAR'},'visibility_state':{'type':'string'},'truncation_state':{'type':'string'},'occlusion_state':{'type':'string'}}})
    dump(OUT/'registered_target_annotations.json',{'schema_version':'TPGT_IDENTITY_VISIBILITY_ANNOTATION_v0.1','annotations':[],'semantics':'Read-only/importable Open-book condition information; never auto-mapped to SAR response.'})
    manual=readcsv(W/'output/person_sar_fullframe_interpolation_review_20260823/repaired_manual_anchor_boxes.csv'); seeds=readcsv(W/'output/person_sar_fullframe_interpolation_review_20260823/interpolated_seed_boxes.csv'); library=readcsv(W/'output/tpgt/phase_1a/evidence_packs/E1A_3520f2a29d6f636f/open_book_historical_library.csv') if False else []
    # The canonical historical library source is recorded in each old open-book card; reuse per-pack CSV where present.
    for q in readcsv(O/'study_queue.csv'):
        p=PACKS/q['event_hypothesis_id']; libs=readcsv(p/'open_book_historical_library.csv') if (p/'open_book_historical_library.csv').exists() else []
        build_pack(q,manual,seeds,libs)
    # Copy adapters into each evidence pack; relative links are stable for standalone file review.
    for q in readcsv(O/'study_queue.csv'):
        p=PACKS/q['event_hypothesis_id']; shutil.copy2(TASK/'OBSERVATION_VIEW.html',p/'OBSERVATION_VIEW.html'); shutil.copy2(TASK/'OPEN_BOOK_VIEW.html',p/'OPEN_BOOK_VIEW.html')
    dump(OUT/'build_manifest.json',{'schema_version':'TPGT_OBSERVATION_WORKBENCH_BUILD_v0.1','events':[q['event_hypothesis_id'] for q in readcsv(O/'study_queue.csv')],'asset_sha256':{n:sha(ASSET/n) for n in ('workbench.css','workbench.js')},'blind_page_does_not_load_open_book_registry':True,'queue_sha256':sha(O/'study_queue.csv')})
    print(json.dumps({'output':str(OUT),'events':6,'schema':str(OUT/'schema/TPGT_OBSERVATION_RECORD_v0.1.json')},ensure_ascii=False))
if __name__=='__main__': main()
