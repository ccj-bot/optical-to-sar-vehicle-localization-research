"""Independent source-value, coordinate, timing, missingness and reader checks."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import sys,json,hashlib
import numpy as np
import pandas as pd
import cv2
from PIL import Image
from normalize import ROOT,OUT,CACHE,MANUAL,WORKBENCH,sha,read_json,dump_json
sys.path.insert(0,str(ROOT/'tools'))
from car_data_contract import CarDataset,native_corners,raw_to_reference,reference_to_raw

def main(out=OUT):
    out=Path(out);checks=[]
    def check(name,ok,detail=None):
        checks.append({'check':name,'passed':bool(ok),'detail':detail})
        if not ok:raise AssertionError(f'{name}: {detail}')
    op=pd.read_parquet(out/'OPTICAL_FRAMES.parquet');sar=pd.read_parquet(out/'SAR_FRAMES.parquet');manual=pd.read_parquet(out/'MANUAL_ANNOTATIONS.parquet')
    cand=pd.read_parquet(out/'OPTICAL_CANDIDATES.parquet');timeline=pd.read_parquet(out/'SUBJECT_TIMELINE.parquet')
    check('full_available_optical_sequence',op.optical_frame_index.tolist()==list(range(298)))
    check('full_available_sar_sequence',sar.sar_frame_index.tolist()==list(range(495)))
    check('frame_tables_contain_no_manual_coverage',not any(k.startswith(('manual_','confirmed_manual_','draft_')) for d in [op,sar] for k in d))
    check('all_records_have_source_images',all(Path(p).is_file() for p in [*op.optical_image_path,*sar.image_path]))
    manifest=read_json(out/'SOURCE_MANIFEST.json');hash_checks=[{'path':x['path'],'matches':sha(Path(x['path']))==x['sha256']} for x in manifest['files']]
    check('all_bound_sources_unchanged',all(x['matches'] for x in hash_checks),{'files':len(hash_checks)})
    initial=read_json(out/'SOURCE_HASHES_BEFORE.json')
    check('build_inputs_preserved',all(sha(Path(p))==h for p,h in initial.items()))
    receipt=read_json(CACHE/'COMPLETE.json');historical=[{'path':p,'matches_recorded_receipt':sha(Path(p))==h} for p,h in receipt['source_hashes'].items()]
    check('old_extraction_source_receipt_matches',all(x['matches_recorded_receipt'] for x in historical),{'files':len(historical)})
    meta=read_json(CACHE/'META.json')
    check('all_sar_hashes_match_frozen_cache',all(row.image_sha256==meta['image_hashes'][row.image_path] for row in sar.itertuples()))

    original=read_json(MANUAL);ref_record=next(x for x in original['annotations'] if x['frame_uid']=='R35ZF_OPT000215')
    check('all_nine_pairs_preserved',set(manual.pair_id)=={x['pair_id'] for x in ref_record['pairs']})
    def pointer(doc,ptr):
        for part in ptr.strip('/').split('/'):
            doc=doc[int(part)] if isinstance(doc,list) else doc[part]
        return doc
    check('manual_json_pointers_resolve',all(pointer(original,r.source_json_pointer)['pair_id']==r.pair_id for r in manual.itertuples()))
    check('manual_candidate_links_resolve',set(manual.source_candidate_id).issubset(set(cand.candidate_id)))
    v5=read_json(ROOT/'output/vehicle50_reference_annotation_20261027/REFERENCE_DRAFT_V5.json')
    legacy=pd.read_parquet(out/'LEGACY_AGENT_DRAFTS.parquet')
    check('historical_draft_payloads_and_pointers_exact',all(pointer(v5,r.source_pointer)==json.loads(r.native_payload_json) for r in legacy.itertuples()))
    corner_err=0.;negative_rejected=0;roundtrip=0.
    for p in ref_record['pairs']:
        r=manual[manual.pair_id==p['pair_id']].iloc[0]
        check('pair_status_'+p['manual_target_id'],r.relation_status==p['relation_status'])
        b=p['sar_box']
        if b is None:
            check('draft_has_no_fabricated_box_'+p['manual_target_id'],pd.isna(r.sar_raw_cx) and r.reference_authority=='USER_DRAFT_REVIEW_ONLY');continue
        vals=np.array([b[k] for k in ['cx','cy','width','height','rotation_deg']])
        norm=np.array([r[k] for k in ['sar_raw_cx','sar_raw_cy','sar_raw_width','sar_raw_height','sar_raw_rotation_deg']])
        check('manual_native_values_exact_'+p['manual_target_id'],np.array_equal(vals,norm))
        a=native_corners(*vals);cv=cv2.boxPoints(((vals[0],vals[1]),(vals[2],vals[3]),vals[4]))
        corner_err=max(corner_err,max(np.linalg.norm(cv-x,axis=1).min() for x in a))
        bad=cv2.boxPoints(((vals[0],vals[1]),(vals[2],vals[3]),-vals[4]))
        negative_rejected+=int(max(np.linalg.norm(bad-x,axis=1).min() for x in a)>.01)
        delta=meta['public_delta'][str(int(r.selected_sar_frame_index))];off=meta['reference_offset'];c=raw_to_reference(a,delta,off)
        roundtrip=max(roundtrip,float(np.abs(reference_to_raw(c,delta,off)-a).max()))
        check('saved_corners_match_svg_'+p['manual_target_id'],np.allclose(np.array(json.loads(r.sar_raw_corners)),a,atol=1e-6))
    check('svg_cv2_agree',corner_err<1e-3,{'max_error_px':float(corner_err)})
    check('wrong_sign_regression_rejected',negative_rejected==6,{'caught_cases':negative_rejected})
    check('manual_transform_roundtrip',roundtrip<1e-9,{'max_error_px':roundtrip})
    check('one_confirmed_sar_frame',manual.loc[manual.reference_authority=='USER_CONFIRMED_NATIVE_SAR','selected_sar_frame_index'].unique().tolist()==[358])
    confirmed=(timeline.sensor=='SAR')&(timeline.annotation_state=='CONFIRMED_FRAME_REFERENCE')
    check('timeline_has_exactly_six_sar_references',int(confirmed.sum())==6)
    check('unknown_not_negative',((timeline.loc[timeline.annotation_state=='UNANNOTATED','presence_judgment']=='UNKNOWN').all()))
    check('no_propagated_manual_labels',not timeline.generated_geometry.any())
    coverage=pd.read_parquet(out/'FRAME_REVIEW_STATE.parquet')
    check('review_coverage_preserved_outside_default_frames',int(coverage.loc[coverage.sensor=='SAR','confirmed_manual_sar_pair_count'].sum())==6)
    check('complete_subject_frame_coverage',len(timeline)==9*(298+495) and not timeline.duplicated(['reference_subject_id','sensor','frame_index']).any())
    last=op.loc[op.optical_frame_index==297].iloc[0]
    check('missing_495_preserved',last.nominal_grid_sar_index==495 and not last.nominal_grid_sar_frame_available and last.nearest_sar_frame_index==494)

    source_cand=pd.read_parquet(WORKBENCH/'optical_candidate_manifest.parquet');source_cand=source_cand[source_cand.run_id=='R35ZF'].sort_values('candidate_id').reset_index(drop=True)
    cc=cand.sort_values('candidate_id').reset_index(drop=True)
    cols=['candidate_id','optical_frame_index','class_name','confidence','x1','y1','x2','y2','object_hypothesis_id']
    check('all_candidate_rows_and_values_preserved',source_cand[cols].equals(cc[cols]),{'rows':len(cc)})
    check('hypothesis_not_physical_identity',(cand.physical_identity_status=='UNRESOLVED').all())

    fragments=pd.read_parquet(out/'SAR_OBSERVATIONS.parquet');arr=dict(np.load(CACHE/'OBS.npz'));bg=pd.read_parquet(out/'SAR_BACKGROUND_MODEL.parquet')
    check('full_fragment_set_retained',len(fragments)==len(arr['frame']) and fragments.source_array_row.tolist()==list(range(len(arr['frame']))) and fragments.obs_id.is_unique)
    check('fragments_do_not_embed_background_model','background_density' not in fragments and 'arc_ratio' not in fragments)
    check('optional_model_values_preserved',np.array_equal(bg.background_density,arr['bg']) and np.array_equal(bg.arc_ratio,arr['arc']))
    maxerr=0.
    for src,dst in [('a','a'),('b','b'),('x','mid')]:
        ref=fragments[[dst+'_x',dst+'_y']].to_numpy();raw=fragments[['raw_'+dst+'_x','raw_'+dst+'_y']].to_numpy()
        check('reference_fragment_values_exact_'+src,np.array_equal(ref,arr[src]))
        shift=np.array([meta['public_delta'][str(f)] for f in arr['frame']])-np.array(meta['reference_offset'])
        maxerr=max(maxerr,float(np.max(np.abs(raw-shift-ref))))
    check('all_fragment_native_reference_roundtrip',maxerr<1e-9,{'max_error_px':maxerr,'fragments':len(fragments)})
    check('fragment_ownership_not_imputed',(fragments.vehicle_ownership=='UNRESOLVED').all())

    d=CarDataset(out)
    for name,call in [('manual_reference_denied',lambda:d.references()),('manual_timeline_denied',lambda:d.review_timeline()),('history_denied',lambda:d.history_index())]:
        caught=False
        try:call()
        except PermissionError:caught=True
        check(name,caught)
    for name,call in [('missing_sar_frame_not_clamped',lambda:d.frame('SAR',495)),('unknown_representation_rejected',lambda:d.fragments(358,representation='any'))]:
        caught=False
        try:call()
        except (ValueError,KeyError):caught=True
        check(name,caught)
    check('default_frames_no_reference_leak',not any(k.startswith(('manual','confirmed','draft','reference_subject')) for k in d.frame('OPTICAL',215)))
    check('real_image_loader_sar',d.image('SAR',358).shape==(592,1024,3))
    check('real_image_loader_optical',d.image('OPTICAL',215).shape==(2160,3840,3))
    check('explicit_fragment_loader',len(d.fragments(358,representation='native_lsd_v2_20261026'))==1402)
    check('review_mode_six_confirmed',len(CarDataset(out,view='review').references())==6)
    mask=d.reference_mask(358,mask_id='lsd_v2_operator_valid_reference')
    check('explicit_mask_loader',mask.shape==(608,1705) and mask.dtype==np.bool_)
    check('context_retains_uncertainty',len(d.paired_context(215)['sar_context'])>1)
    result={'status':'PASS_DATA_INTEGRITY_AND_SEMANTIC_GUARDS','checks':checks,'passed_count':len(checks),'scientific_localization_acceptance':False,
            'coverage_limit':'only6 user-confirmed SAR boxes, all at358; all other current subject frames unannotated',
            'sources_checked':hash_checks,'old_cache_sources_checked':historical,
            'completed':datetime.now(ZoneInfo('Asia/Shanghai')).isoformat()}
    dump_json(out/'VERIFICATION.json',result)
    print(json.dumps({'status':result['status'],'checks':len(checks),'all_sources':len(hash_checks),'old_cache_sources':len(historical)},ensure_ascii=False),flush=True)
    return result
if __name__=='__main__':main()
