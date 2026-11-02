"""Separate review leakage, model assumptions, missingness and historical claims."""
from pathlib import Path
import json, shutil, hashlib
import numpy as np
import pandas as pd
from normalize import ROOT,OUT,CACHE,MANUAL,WORKBENCH,sha,read_json,dump_json,source_row

def main(out=OUT):
    out=Path(out);contract=read_json(out/'DATA_CONTRACT.json');manifest=read_json(out/'SOURCE_MANIFEST.json');original=read_json(MANUAL)
    manual=pd.read_parquet(out/'MANUAL_ANNOTATIONS.parquet');op=pd.read_parquet(out/'OPTICAL_FRAMES.parquet');sar=pd.read_parquet(out/'SAR_FRAMES.parquet')
    coverage=[]
    old_coverage=pd.read_parquet(out/'FRAME_REVIEW_STATE.parquet') if (out/'FRAME_REVIEW_STATE.parquet').exists() else None
    for sensor,data,key in [('OPTICAL',op,'optical_frame_index'),('SAR',sar,'sar_frame_index')]:
        private=[c for c in data if c.startswith(('manual_','confirmed_manual_','draft_','target_visibility_'))]
        if private:
            for r in data.to_dict('records'):
                coverage.append({'scene':'R35ZF','sensor':sensor,'frame_index':r[key],
                                 **{k:r[k] for k in private}})
        else:
            assert old_coverage is not None
            coverage.extend(old_coverage[old_coverage.sensor==sensor].to_dict('records'))
        data.drop(columns=private,inplace=True)
        # Keyframe selection reflects historical review choices, not sensor evidence.
        if sensor=='OPTICAL':data.drop(columns=['is_keyframe'],inplace=True,errors='ignore')
        data.to_parquet(out/(sensor+'_FRAMES.parquet'),index=False)
        data.to_csv(out/(sensor+'_FRAMES.csv'),index=False,encoding='utf-8-sig')
    pd.DataFrame(coverage).to_parquet(out/'FRAME_REVIEW_STATE.parquet',index=False)

    # No physical identity is manufactured from an upstream track or candidate ID.
    candidates=pd.read_parquet(out/'OPTICAL_CANDIDATES.parquet')
    names=['identity_hint','identity_tier','identity_status','association_status','association_margin','object_frame_role']
    candidates.rename(columns={k:'source_'+k for k in names},inplace=True)
    candidates['track_scope']='SOURCE_PIPELINE_R35_RECORDING_HYPOTHESIS'
    candidates['physical_identity_status']='UNRESOLVED'
    candidates['physical_truncation_status']='UNKNOWN'
    candidates.to_parquet(out/'OPTICAL_CANDIDATES.parquet',index=False)
    candidates.to_csv(out/'OPTICAL_CANDIDATES.csv',index=False,encoding='utf-8-sig')
    pointers={p['pair_id']:f'/annotations/{i}/pairs/{k}' for i,a in enumerate(original['annotations']) for k,p in enumerate(a.get('pairs',[]))}
    manual['source_json_pointer']=manual.pair_id.map(pointers)
    manual['source_snapshot_sha256']=sha(MANUAL)
    manual.to_parquet(out/'MANUAL_ANNOTATIONS.parquet',index=False)
    manual.to_csv(out/'MANUAL_ANNOTATIONS.csv',index=False,encoding='utf-8-sig')
    links=[];timeline=[]
    for row in manual.to_dict('records'):
        subject=row['reference_subject_id'];of=int(row['optical_frame_index']);sf=int(row['selected_sar_frame_index'])
        has_sar=pd.notna(row['sar_raw_cx']);confirmed=row['reference_authority']=='USER_CONFIRMED_NATIVE_SAR'
        links.append({'reference_subject_id':subject,'optical_frame_index':of,'source_candidate_id':row['source_candidate_id'],
                      'source_track_hint':row['optical_linkage_hint'],'pair_status':row['relation_status'],
                      'track_identity_across_time_confirmed':False,'relation_scope':'THIS_STORED_FRAME_PAIR_ONLY',
                      'source_snapshot':str(MANUAL),'source_pair_id':row['pair_id']})
        for sensor,fs,anchor in [('OPTICAL',op.optical_frame_index.tolist(),of),('SAR',sar.sar_frame_index.tolist(),sf)]:
            for f in fs:
                direct=f==anchor and (sensor=='OPTICAL' or has_sar)
                state=('CONFIRMED_FRAME_REFERENCE' if confirmed else 'DRAFT_FRAME_RECORD') if direct else 'UNANNOTATED'
                timeline.append({'scene':'R35ZF','reference_subject_id':subject,'manual_target_id':row['manual_target_id'],
                                 'sensor':sensor,'frame_index':f,'image_available':True,'annotation_state':state,
                                 'visibility_judgment':'NOT_RECORDED','presence_judgment':'USER_PAIR_REFERENCE' if direct and confirmed else 'UNKNOWN',
                                 'generated_geometry':False,'reference_row_id':row['pair_id'] if direct else None})
    td=pd.DataFrame(timeline);td.to_parquet(out/'SUBJECT_TIMELINE.parquet',index=False)
    td.to_csv(out/'SUBJECT_TIMELINE.csv',index=False,encoding='utf-8-sig')
    pd.DataFrame(links).to_parquet(out/'REFERENCE_ASSOCIATIONS.parquet',index=False)

    provenance=out/'provenance';provenance.mkdir(exist_ok=True)
    copies=[]
    for src in [CACHE/'MOTION.json',CACHE/'MASKS_PACKED.npy',CACHE/'META.json',CACHE/'COMPLETE.json',MANUAL]:
        dest=provenance/src.name;shutil.copyfile(src,dest);assert sha(dest)==sha(src)
        copies.append({'source':str(src),'copy':str(dest.relative_to(out)),'sha256':sha(src)})
    dump_json(out/'SOURCE_COPIES.json',copies)
    meta=read_json(CACHE/'META.json');motion=read_json(CACHE/'MOTION.json')
    transforms=[]
    for f in meta['frames']:
        d=meta['public_delta'][str(f)]
        transforms.append({'scene':'R35ZF','sar_frame_index':f,'transform_id':'offline_public_translation_v2',
                           'delta_x_px':d[0],'delta_y_px':d[1],'offset_x_px':meta['reference_offset'][0],'offset_y_px':meta['reference_offset'][1],
                           'input_time_scope':'FULL_SEQUENCE_OFFLINE','physical_motion_established':False})
    pd.DataFrame(transforms).to_parquet(out/'FRAME_TRANSFORMS.parquet',index=False)
    for name,key in [('PUBLIC_MOTION_EDGES','edges'),('PUBLIC_MOTION_CHECKS','background_holdout_checks')]:
        pd.DataFrame(motion[key]).to_parquet(out/(name+'.parquet'),index=False)
    pd.DataFrame(meta['visibility_coverage']).to_parquet(out/'OPERATOR_MASK_COVERAGE.parquet',index=False)

    # One SAR image can be adjacent to several optical times; retain the full
    # nominal context instead of turning nearest-time lookup into a true pair.
    context=[]
    for r in op.to_dict('records'):
        for s in sar.to_dict('records'):
            delta=s['timestamp_ms_nominal']-r['optical_timestamp_ms']
            if abs(delta)<=r['sync_uncertainty_ms']:
                context.append({'optical_frame_index':r['optical_frame_index'],'sar_frame_index':s['sar_frame_index'],
                                'delta_ms':delta,'declared_uncertainty_ms':r['sync_uncertainty_ms'],
                                'is_nearest_available':s['sar_frame_index']==r['nearest_sar_frame_index'],
                                'pair_status':'NOMINAL_TIME_CONTEXT_NOT_TARGET_ASSOCIATION'})
    pd.DataFrame(context).to_parquet(out/'NOMINAL_PAIR_CONTEXT.parquet',index=False)

    cache_digest=sha(CACHE/'OBS.npz')
    operator={'id':'native_lsd_v2_20261026','status':'OPTIONAL_DERIVED_REPRESENTATION_WITH_HEURISTIC_CHOICES',
      'source_digest':cache_digest,'source_array_row_is_stable_within_this_digest_only':True,
      'pixel_primary_source':'unaltered JPEG frames decoded from pseudocolor video; not complex SAR/IQ/RCS',
      'pipeline':['nearest OpenCV JET LUT color index (display approximation)','mask-normalized DoG, sigma radius/1332.7*2 and12x',
                  'background median/MAD using upper65% fan interior','positive-part and arcsinh transform','0.995 quantile to8bit for LSD',
                  'OpenCV LSD_REFINE_STD','minimum line length6px; samples every0.5px; eroded validity context7x7',
                  'native points translated into expanded reference canvas'],
      'defaults_are_source_settings_not_newly_validated_optima':True,
      'lost_information':['negative DoG response','subthreshold/nonlinear intensity information','structures not represented as a6px line'],
      'background_model':'optional, separate SAR_BACKGROUND_MODEL.parquet; half radial-arc density plus half uniform',
      'operator_source':str(ROOT/'tasks/vehicle50_size_trace_20261026/prepare_native.py'),
      'mask_semantics':'reference-grid operator-valid region; excludes an eroded boundary, not the full displayed fan',
      'temporal_transform_semantics':motion['semantics']}
    dump_json(out/'DERIVED_OPERATOR.json',operator)

    # Keep historical agent annotations and model candidates available for review,
    # without importing any of them into the six current confirmed user boxes.
    v5path=ROOT/'output/vehicle50_reference_annotation_20261027/REFERENCE_DRAFT_V5.json';v5=read_json(v5path);v5rows=[]
    for vi,v in enumerate(v5['vehicles']):
        for sensor,key,indexkey in [('SAR','frames','sar_frame'),('OPTICAL','optical_frames','optical_frame')]:
            for i,r in enumerate(v[key]):
                v5rows.append({'legacy_subject_id':v['vehicle_id'],'scene':v['scene'],'sensor':sensor,'frame_index':r[indexkey],
                               'entry_type':r.get('entry_type','UNKNOWN'),'truth_status':'AGENT_DRAFT_NOT_ACCEPTED_BODY_REFERENCE',
                               'source_version':'V5','source_pointer':f"/vehicles/{vi}/{key}/{i}",
                               'native_payload_json':json.dumps(r,ensure_ascii=False)})
    pd.DataFrame(v5rows).to_parquet(out/'LEGACY_AGENT_DRAFTS.parquet',index=False)
    recent=ROOT/'output/manual_guided_localization_20261029/BOX_CANDIDATES.csv'
    proposals=pd.read_csv(recent,encoding='utf-8-sig');proposals['evidence_layer']='MANUAL_CONDITIONED_MODEL_OR_TRANSPORT'
    proposals['source_path']=str(recent);proposals['accepted_as_new_reference']=False
    proposals.to_parquet(out/'RECENT_CONDITIONED_PROPOSALS.parquet',index=False)
    artifacts=[(v5path,'HISTORICAL','AGENT_REFERENCE_DRAFT','not user-confirmed; includes interpolation and coarse body construction'),
      (ROOT/'output/vehicle50_self_annotation_20261027/DRAFT_INVALIDATION.json','CURRENT_CORRECTION','INVALIDATION','invalidated agent draft'),
      (ROOT/'output/manual_guided_localization_20261027/manual_anchor_F358.png','SUPERSEDED','WRONG_PREVIEW','six rotations had opposite sign'),
      (ROOT/'output/manual_guided_localization_20261029/MANUAL_SAR358_SVG_EXACT.png','CURRENT','REFERENCE_RENDER','exact rendering of source user coordinates'),
      (recent,'HISTORICAL_DIAGNOSTIC','A_LINE_PROPOSAL','unaccepted conditioned coordinates'),
      (ROOT/'output/vehicle50_size_trace_20261026/batch50/global_scene/R35ZF/RESULT.json','HISTORICAL_DIAGNOSTIC','B_LINE_SCENE_CANDIDATES','11 source-scoped candidates; body unverified'),
      (ROOT/'output/research_strategy_review_20261027/START_HERE.md','HISTORICAL_CONTEXT','STRATEGY_AUDIT','not a source of confirmed labels')]
    history=[]
    for p,status,role,note in artifacts:
        history.append({'path':str(p),'sha256':sha(p),'status':status,'role':role,'note':note,'allowed_as_current_confirmed_label':False})
        manifest['files'].append(source_row(p,role,status,ROOT))
    dump_json(out/'HISTORY_INDEX.json',history)
    exposure=[]
    for f in range(495):
        roles=[]
        if f in [338,348,358,368,378]:roles.append('20261029_A_LINE_FIT')
        if f in [343,353,363,373]:roles.append('20261029_A_LINE_READOUT')
        if f==358:roles.append('MANUAL_REFERENCE_SEEN_DURING_DEVELOPMENT')
        roles.append('FULL_SEQUENCE_USED_FOR_PUBLIC_TRANSFORM')
        exposure.append({'sar_frame_index':f,'known_uses':';'.join(roles),'all_prior_experiments_audited':False,'independent_unseen_test':False})
    pd.DataFrame(exposure).to_parquet(out/'KNOWN_DATA_EXPOSURE.parquet',index=False)

    syncpath=ROOT/'output/new_scene_vehicle_temporal_segments_20260818/full_65_identity_v2_20260818/sync_registry.csv'
    sync=pd.read_csv(syncpath);sync=sync[sync.run_id=='R35ZF'];dump_json(out/'SYNC_SOURCE_RECORD.json',sync.to_dict('records'))
    invpath=ROOT/'output/pseudocolor_labelstudio_prep_20260722/video_inventory.csv'
    videos=pd.read_csv(invpath);videos=videos[videos.run_id=='R35ZF'];videos.to_csv(out/'VIDEO_SOURCE_RECORDS.csv',index=False,encoding='utf-8-sig')
    for p,role in [(syncpath,'NOMINAL_SYNC_REGISTRY'),(invpath,'VIDEO_INVENTORY')]:manifest['files'].append(source_row(p,role,'SOURCE_METADATA',ROOT))
    for r in videos.to_dict('records'):
        p=Path(r['path']);assert p.is_file();manifest['files'].append(source_row(p,'RECORDED_VIDEO','CONTENT_VERIFIED_METADATA_INHERITED'))
    cache_receipt=read_json(CACHE/'COMPLETE.json')
    for p,expected in cache_receipt['source_hashes'].items():
        if Path(p).suffix.lower()!='.jpg':
            entry=source_row(Path(p),'EXTRACTOR_DEPENDENCY_OR_CONFIG','INHERITED_DERIVATION',ROOT);entry['cache_recorded_sha256']=expected
            manifest['files'].append(entry)
    manifest['files']=list({r['path']:r for r in manifest['files']}.values())
    dump_json(out/'SOURCE_MANIFEST.json',manifest)

    # Frames are data, models are opt-in, human references require review access.
    views={'observation':{'default':['OPTICAL_FRAMES','SAR_FRAMES'],
                         'opt_in':['OPTICAL_CANDIDATES','SAR_OBSERVATIONS','SAR_BACKGROUND_MODEL','FRAME_TRANSFORMS'],
                         'references_available':False,'object_labels_or_manual_coverage_available':False},
           'review':{'references_available':True,'historical_outputs_available':True},
           'manual_initialized':{'references_available':True,'reporting_protocol':'A_LINE'}}
    dump_json(out/'INPUT_VIEWS.json',views)
    contract['counts'].update(subject_timeline_rows=len(td),confirmed_sar_reference_frames=1,
                             unannotated_sar_subject_states=int(((td.sensor=='SAR')&(td.annotation_state=='UNANNOTATED')).sum()),
                             legacy_agent_draft_rows=len(v5rows),nominal_pair_context_rows=len(context))
    contract['snapshot_extracted_at']=original['extracted_at'];contract['snapshot_refreshed_this_run']=False
    contract['current_scope']='R35 full source sequence; existing confirmed labels normalized, other frames remain unannotated'
    contract['sar_observation_primary_coordinates']='raw_* native pixels; reference columns retain exact inherited transformed measurements'
    contract['operator_registry']='DERIVED_OPERATOR.json';contract['input_views']='INPUT_VIEWS.json'
    contract['layer_rules']['sar_background_model']='assumed model density, not image measurement or true background classification'
    contract['time_rules']['missing_nominal_grid_frame']='retain requested index and availability=false; nearest available context is not substituted for it'
    contract['status']='BUILT_PENDING_INDEPENDENT_VALIDATION';dump_json(out/'DATA_CONTRACT.json',contract)
    coords=read_json(out/'COORDINATE_TRANSFORMS.json')
    coords.update(axis_convention='native x right and y down; positive rotation clockwise on display',
                  rotation_definition='rotation of the width axis, degrees, not necessarily the long axis',
                  long_axis_definition='(rotation_deg +90 if height>width else rotation_deg) modulo180',
                  signed_physical_heading='UNKNOWN; undirected box axis does not establish front/rear',
                  clipping='retain original corners even outside observed fan; do not clamp full-body boxes',
                  pixel_units='native display pixel coordinates; not uniform scene metres')
    dump_json(out/'COORDINATE_TRANSFORMS.json',coords)
    print(json.dumps({'stage':'enriched','timeline_rows':len(td),'sar_unannotated':contract['counts']['unannotated_sar_subject_states'],'nominal_grid_missing':op.loc[~op.nominal_grid_sar_frame_available,['optical_frame_index','nominal_grid_sar_index','nearest_sar_frame_index']].to_dict('records')},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
