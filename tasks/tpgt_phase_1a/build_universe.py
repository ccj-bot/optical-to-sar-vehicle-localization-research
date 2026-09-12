from pathlib import Path
import csv,json,hashlib,re,collections
import pandas as pd
W=Path('D:/profile/research/workspace'); O=W/'output/tpgt/phase_1a'; A=O/'audit'; A.mkdir(parents=True,exist_ok=True)
def dump(p,x): p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def sha(p): return hashlib.file_digest(Path(p).open('rb'),'sha256').hexdigest()
inventory=list(csv.DictReader((W/'output/tpgt/phase_0b/EVENT_SOURCE_CANDIDATES.csv').open(encoding='utf-8-sig')))
S={r['source_id']:r for r in inventory}
manifest={}; cache={}
def read(s):
    if s in cache:return cache[s]
    p=Path(S[s]['source_path']); h=sha(p)
    df=pd.read_parquet(p).fillna('') if p.suffix=='.parquet' else pd.read_csv(p,dtype=str,keep_default_na=False)
    rows=df.to_dict('records'); manifest[s]={'path':str(p),'sha256':h,'rows':len(rows)}
    cache[s]=rows; return rows
def ranges(vals):
    out=[]
    for v in sorted(set(int(float(x)) for x in vals)):
        if out and v==out[-1][1]+1:out[-1][1]=v
        else:out.append([v,v])
    return out
def compact(vals):return ';'.join(str(a) if a==b else f'{a}-{b}' for a,b in ranges(vals))
frozen=list((W/'output/tpgt/phase_0c').glob('*'))+list((W/'research/tpgt').glob('*SCHEMA*'))+list((W/'research/tpgt').glob('*REGISTRY*'))
freeze={str(p):sha(p) for p in frozen if p.is_file()}
dump(A/'frozen_0c_before.json',freeze)
events=[]; details={}
runs={r['run_id']:r for r in read('C_RUNS')}
def add(s,run,ident,domain,layer,ords,frames=None,native_ranges=None,basis='EXACT_OBSERVED_OPTICAL_FRAME_RUNS', extra=None):
    eid='E1A_'+hashlib.sha256(f'{s}|{run}|{ident}'.encode()).hexdigest()[:16]
    rr=ranges(frames) if frames is not None else (native_ranges or [])
    fps=float(runs[run]['optical_fps']) if run in runs else (24.0 if run.startswith('GM_') else None)
    e={'event_hypothesis_id':eid,'domain':domain,'run_id':run,'source_id':s,'source_identity':str(ident),'identity_layer':layer,'source_record_ordinals':compact(ords),'support_ranges_optical_frames':rr,'support_ranges_nominal_ms':[[round(a*1000/fps,3),round(b*1000/fps,3)] for a,b in rr] if fps else [],'interval_basis':basis,'physical_identity_status':'UNKNOWN','canonical_class':'UNKNOWN','distance':'UNKNOWN','pose':'UNKNOWN','completeness':'UNKNOWN','occlusion':'UNKNOWN','truncation':'UNKNOWN','sar_response_presence':'UNKNOWN','sar_localization_validity':'UNKNOWN','event_core_interval':None,'event_context_interval':None}
    events.append(e); details[eid]=extra or {}; return e
cf=read('C_FRAMES'); pf=read('P_DET')
cgroups=collections.defaultdict(list); pgroup=collections.defaultdict(list)
rawcovered=set()
for i,r in enumerate(cf,1):
    cgroups[(r['run_id'],r['object_hypothesis_id'])].append((i,r))
    rawcovered.update(x for x in re.split(r'[;,|]',str(r['source_raw_ids'])) if x)
for i,r in enumerate(pf,1):pgroup[(r['run_id'],r['optical_person_id'])].append((i,r))
for sid,key,groups,dom in [('C_IDS','object_hypothesis_id',cgroups,'CAR'),('P_TRACKS','optical_person_id',pgroup,'PERSON')]:
    for i,r in enumerate(read(sid),1):
        g=groups.get((r['run_id'],r[key]),[])
        e=add(sid,r['run_id'],r[key],dom,'stitched_offline_identity',[i],frames=[x['frame_index'] for _,x in g],extra={'observation_source':'C_FRAMES' if dom=='CAR' else 'P_DET','observation_ordinals':compact([j for j,_ in g]),'optical_rows':[x for _,x in g]})
        if not g:
            e['interval_basis']='SOURCE_ENDPOINT_OBSERVATIONS_ONLY_INTERIOR_UNKNOWN'
            start=r.get('first_frame',r.get('start_frame')); end=r.get('last_frame',r.get('end_frame'))
            e['support_ranges_optical_frames']=ranges([start,end]); e['support_ranges_nominal_ms']=[[a*1000/float(runs[r['run_id']]['optical_fps']),b*1000/float(runs[r['run_id']]['optical_fps'])] for a,b in e['support_ranges_optical_frames']]
for i,r in enumerate(read('C_LOCAL'),1):
    add('C_LOCAL',r['run_id'],r['object_hypothesis_id'],'CAR','stitched_offline_identity',[i],frames=[r['first_frame'],r['last_frame']],basis='VERSION_LOCAL_ENDPOINT_OBSERVATIONS_ONLY_INTERIOR_UNKNOWN')
# Raw fragment ancestry stays version/source scoped; no new stitching.
for sid,rows,dom,key in [('C_FRAMES',cf,'CAR','raw_track_id')]+[(s,read(s),'PERSON','raw_track_fragment_id' if s.startswith('P_RAW') else 'person_id') for s in S if s.startswith(('P_RAW_','P_REUSED_'))]:
    groups=collections.defaultdict(list)
    for i,r in enumerate(rows,1):groups[(r['run_id'],str(r.get(key,'') or f'row_{i}'))].append((i,r))
    for (run,ident),g in groups.items():add(sid,run,ident,dom,'raw_detection_or_fragment_id',[i for i,_ in g],frames=[r['frame_index'] for _,r in g])
# Every raw CAR row is either linked through exact native raw_det_id ancestry or retained as its own single-observation hypothesis.
raw=read('C_RAW'); linked=0
for i,r in enumerate(raw,1):
    if r['raw_det_id'] in rawcovered:linked+=1;continue
    add('C_RAW',r['run_id'],r['raw_det_id'],'CAR','raw_detection_or_fragment_id',[i],frames=[r['frame_index']])
for sid in ['GM_REG','GM_P1D']:
    for i,r in enumerate(read(sid),1):
        rr=[]
        for token in re.split(r'[;,]',r.get('visible_frame_ranges','')):
            token=token.strip()
            if re.fullmatch(r'\d+\s*-\s*\d+',token):rr.append([int(x) for x in token.split('-')])
            elif re.fullmatch(r'\d+',token):rr.append([int(token),int(token)])
        if not rr:
            for k in ['frame_first_visible','frame_last_visible']:
                if r.get(k,''):rr.append([int(r[k]),int(r[k])])
        add(sid,r['scene'],r['canonical_vehicle_id'],'CAR','manual_local_identity',[i],native_ranges=rr,basis='SOURCE_DECLARED_VISIBLE_RANGES' if r.get('visible_frame_ranges') else 'SOURCE_ENDPOINTS_ONLY_INTERIOR_UNKNOWN')
# Retain selected historical source hypotheses too; selected-source bias is provenance, not a deletion rule. Bounds use only observed optical frames.
for sid in ['LIBRARY','LIBRARY_CONFIRMED']:
    gg=collections.defaultdict(list)
    for i,r in enumerate(read(sid),1):gg[(r['run_id'],r['event_id'])].append((i,r))
    for (run,ident),g in gg.items():
        labels={r.get('coarse_class','') for _,r in g}; domain='PERSON' if labels=={'PERSON'} else 'CAR' if labels<={'CAR','VEHICLE','car','vehicle'} else 'SOURCE_CLASS_UNRESOLVED'
        add(sid,run,ident,domain,'source_identity_hypothesis',[i for i,_ in g],frames=[r['optical_frame_index'] for _,r in g],basis='OBSERVED_OPTICAL_FRAMES_FROM_HISTORICALLY_SELECTED_SOURCE')
# Legacy records are attached as evidence, never reused as event core or context.
legacy={s:read(s) for s in ['C_SEG','P_SEG']}
legacy_lookup=collections.defaultdict(list)
for sid,rows in legacy.items():
    for i,r in enumerate(rows,1):legacy_lookup[(sid,r['run_id'],r.get('object_hypothesis_id',r.get('optical_person_id','')))].append(i)
for e in events:
    sid=e['source_id'];d=details[e['event_hypothesis_id']]
    e['source_path']=manifest[sid]['path'];e['source_sha256']=manifest[sid]['sha256']
    e['observation_source_reference']={'source_id':d['observation_source'],'path':manifest[d['observation_source']]['path'],'sha256':manifest[d['observation_source']]['sha256'],'data_row_ordinals':d['observation_ordinals']} if d.get('observation_source') else None
    ls='C_SEG' if sid=='C_IDS' else 'P_SEG' if sid=='P_TRACKS' else None
    e['legacy_segment_interval_refs']=[{'source_id':ls,'path':manifest[ls]['path'],'sha256':manifest[ls]['sha256'],'data_row_ordinals':compact(legacy_lookup[(ls,e['run_id'],e['source_identity'])]),'semantics':'Historical source only; legacy core/padded fields do not define provisional support or event core/context'}] if ls and legacy_lookup[(ls,e['run_id'],e['source_identity'])] else []
dump(A/'source_manifest.json',manifest)
dump(A/'source_accounting.json',{'raw_car_rows':len(raw),'raw_car_exact_ancestry_linked_rows':linked,'raw_car_retained_singletons':len(raw)-linked,'source_event_counts':dict(collections.Counter(e['source_id'] for e in events)),'scope':'Phase 0B registered target-bearing optical sources; not a physical target census. Same measurement/identity may recur across source/version layers. No global identity reconciliation.','legacy_sources_preserved_by_hash_and_record_locator':{s:len(v) for s,v in legacy.items()}})
def writecsv(p,rows):
    with p.open('w',newline='',encoding='utf-8-sig') as f:
        wr=csv.DictWriter(f,fieldnames=list(rows[0]));wr.writeheader()
        for r in rows:wr.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else v for k,v in r.items()})
writecsv(O/'provisional_event_universe.csv',events)
# Small review convenience JSON for source identities with per-frame optical evidence; no scores or old tiers in selection table.
pool=[]
for e in events:
    d=details[e['event_hypothesis_id']]; rr=d.get('optical_rows',[])
    if not rr:continue
    frames=sorted(set(int(r['frame_index']) for r in rr)); duration=(frames[-1]-frames[0]+1)/float(runs[e['run_id']]['optical_fps'])
    boxes=[[float(r[k]) for k in ['bbox_x1','bbox_y1','bbox_x2','bbox_y2']] for r in rr]
    edge=sum(b[0]<=5 or b[1]<=5 or b[2]>=3835 or b[3]>=2155 for b in boxes)/len(boxes)
    pool.append({'event_hypothesis_id':e['event_hypothesis_id'],'domain':e['domain'],'run_id':e['run_id'],'source_identity':e['source_identity'],'first_frame':frames[0],'last_frame':frames[-1],'observed_frames':len(frames),'duration_s':round(duration,3),'support_range_count':len(e['support_ranges_optical_frames']),'bbox_edge_fraction':round(edge,3),'median_bbox_height':round(float(pd.Series([b[3]-b[1] for b in boxes]).median()),1)})
writecsv(A/'optical_review_pool.csv',pool)
dump(A/'study_source_details.json',{e['event_hypothesis_id']:{'event':e,**details[e['event_hypothesis_id']]} for e in events if details[e['event_hypothesis_id']].get('optical_rows')})
dump(A/'build_result.json',{'events':len(events),'domains':dict(collections.Counter(e['domain'] for e in events)),'frozen_unchanged':all(sha(p)==h for p,h in freeze.items())})
print(json.dumps({'events':len(events),'raw_unlinked':len(raw)-linked,'pool':len(pool),'by_source':dict(collections.Counter(e['source_id'] for e in events))}))
