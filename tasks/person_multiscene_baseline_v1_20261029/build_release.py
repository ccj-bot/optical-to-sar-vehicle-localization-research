"""Package six verified PERSON profiles without changing research algorithms."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import csv
import hashlib
import importlib.metadata
import json
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
PARENT=ROOT/'output/person_runtime_integration_20261029'
OUT=ROOT/'output/person_multiscene_baseline_v1_20261029'
TASK=Path(__file__).parent


def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))


def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()


def write(p,v):
    Path(p).parent.mkdir(parents=True,exist_ok=True)
    Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')


def main():
    OUT.mkdir(exist_ok=False)
    prior=read(PARENT/'DELIVERY_SEAL.json')
    for p,h in prior['files'].items():
        if sha(p)!=h:raise RuntimeError(f'Parent delivery changed:{p}')
    runtime=OUT/'runtime/person_localizer';runtime.mkdir(parents=True)
    sources=[]
    for p in sorted((PARENT/'source_final').iterdir()):
        if p.is_file() and p.suffix in {'.py','.md','.json'}:
            dst=runtime/p.name;shutil.copy2(p,dst)
            if p.suffix=='.py' and sha(ROOT/'tools/person_localizer'/p.name)!=sha(p):
                raise RuntimeError(f'Live runtime differs from verified snapshot:{p.name}')
            sources.append(dict(source=str(p),bundled=str(dst.relative_to(OUT)).replace('\\','/'),sha256=sha(dst)))
    shutil.copy2(TASK/'baseline_launcher.py',OUT/'run.py')
    cases=read(PARENT/'CASES.json')+read(PARENT/'EXTRA_CASES.json')
    chosen=[('R01ZF_visible16_development','FIXED_REFERENCE_BASELINE','近邻双人/清晰片段'),
        ('R04ZF_support_sampling_repair','FIXED_REFERENCE_BASELINE','边界/部分可见响应'),
        ('GM_RM017_historical_parent','TEMPORAL_REVIEW_BASELINE','平台运动与边界响应'),
        ('R02ZF_historical_parent','TEMPORAL_REVIEW_BASELINE','多人重叠/弱响应'),
        ('R07ZF_complete_source','FULL_SEQUENCE_REVIEW_BASELINE','楼梯高度差/车辆遮挡'),
        ('R50ZF_historical_parent','RECOVERY_BASELINE','遮挡恢复/共享峰竞争')]
    external={};profiles=[];copies=[]
    def copy(source,relative):
        source=Path(source);dst=OUT/relative;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dst)
        digest=sha(dst);assert digest==sha(source)
        copies.append(dict(source=str(source),bundled=relative,sha256=digest))
        return 'bundle://'+relative
    def ext(path,scene,role):
        path=str(Path(path).resolve())
        item=external.get(path)
        if item is None:
            item=dict(path=path,role=role,bytes=Path(path).stat().st_size,sha256=sha(path),scenes=[]);external[path]=item
        if scene not in item['scenes']:item['scenes'].append(scene)
    for case_id,status,condition in chosen:
        c=next(x for x in cases if x['id']==case_id);scene=c['scene'];base=f'profiles/{scene}'
        m=read(c['manifest']) if c['manifest'] else None
        spec=read(m['scene']) if m else read(c['scene_pointer']);cfg=read(c['config'])
        spec.pop('person_config',None);spec['person_engine']=c['engine']
        spec['optical_csv']=copy(spec['optical_csv'],base+'/optical.csv')
        if spec.get('vehicle_evidence_csv'):
            spec['vehicle_evidence_csv']=copy(spec['vehicle_evidence_csv'],base+'/vehicle_evidence.csv')
        for key in ['sar_video','optical_video']:
            if spec.get(key):ext(spec[key],scene,'source_video')
        write(OUT/base/'spec.json',spec);write(OUT/base/'config.json',cfg)
        if m is not None:
            m['scene']='bundle://'+base+'/spec.json';m['config']='bundle://'+base+'/config.json'
            if m.get('transport_cache'):
                m['transport_cache']=copy(m['transport_cache'],base+'/public_transport.json')
            if m.get('work_frames_cache'):ext(m['work_frames_cache'],scene,'work_frame_cache')
            inherited={}
            for i,(p,h) in enumerate(m.get('inherited_files',{}).items()):
                if sha(p)!=h:raise RuntimeError(f'Initialization provenance changed:{p}')
                uri=copy(p,base+f'/provenance/{i:02d}_{Path(p).name}');inherited[uri]=h
            if inherited:m['inherited_files']=inherited
            if m.get('terminal_feedback'):
                m['terminal_feedback']=copy(m['terminal_feedback'],base+'/terminal_feedback.json')
            write(OUT/base/'manifest.json',m)
        result=Path(c['output']);result_files=[]
        for name in ['PREDICTIONS.csv','ANNOTATIONS.csv','READOUT.csv','PACKAGE.json','POLICY_FROZEN.json',
            'INITIALIZATION.json','PREDICTION_SEAL.json','SOURCE_SEAL.json','ANNOTATION_POLICY.json',
            'REGISTRATION_QUALITY.csv','QUERY_TERMINALS.csv','INTEGRATION_PARITY.json','RESULTS.json']:
            if (result/name).is_file():
                copy(result/name,f'results/{scene}/{name}');result_files.append(name)
        profiles.append(dict(scene=scene,source_case=case_id,engine=c['engine'],status=status,condition=condition,
            frames=c['old_frames'],config=base+'/config.json',spec=base+'/spec.json',
            manifest=base+'/manifest.json' if m else None,
            cached_initialization=(c['engine']=='sequence'),
            results=f'results/{scene}',result_files=result_files,
            raw_support_sampling=cfg.get('raw_support_sampling',{}).get('enabled',False),
            boundary_normalized_dog=cfg.get('boundary_normalized_dog',False),
            persistent_input_hold=cfg.get('persistent_input_hold',False),
            persistent_proposal_center=cfg.get('persistent_proposal_center',False),
            search_half_angle_deg=cfg['fan_half_angle_deg'],
            display_half_angle_deg=cfg['annotation_output']['visibility']['half_angle_deg'],
            residual_radius_px=(m or {}).get('temporal_policy',{}).get('residual_radius_px',8) if m else None,
            unresolved='001/007关联与007响应归属留待复核' if scene=='R07ZF' else
                '第二人的响应归属仍按状态复核' if scene=='GM_RM017' else
                '纯自动与用户反馈分开；本入口仅纯自动' if scene=='R02ZF' else
                '沿用该范围内已核对的点位与状态'))
    evidence=['FINAL_VERIFICATION.json','RUNTIME_VERIFICATION.json','RUNTIME_VERIFICATION_BEFORE_CONTINUITY.json',
        'CONTINUITY_CODE_REVISION.json','FINAL_DEFAULT_PROPOSAL_VERIFICATION.json','PARITY_SUMMARY.csv',
        'REFERENCE_SUMMARY.csv','REFERENCE_VERIFICATION.json','R07_COMPLETE_VERIFICATION.json',
        'R07_OBSERVED_EPISODE_SUMMARY.csv','R07_COMPLETE_STATES.csv','DISPLAY_SUPPORT_AUDIT.csv',
        'review_qa/VERIFICATION.json','r07_transport_probe/RESULT.json','r07_structure_probe/RESULT.json']
    for p in evidence:copy(PARENT/p,'evidence/'+p.replace('/','__'))
    versions={}
    for p in ['numpy','scipy','pandas','opencv-python','Pillow','threadpoolctl','ultralytics']:
        try:versions[p]=importlib.metadata.version(p)
        except importlib.metadata.PackageNotFoundError:versions[p]=None
    write(OUT/'ENVIRONMENT.json',dict(python=sys.executable,python_version=sys.version,packages=versions,
        hardware_benchmark_performed=False,new_detector_execution=False))
    write(OUT/'SOURCE_COPIES.json',sources+copies)
    write(OUT/'EXTERNAL_DEPENDENCIES.json',list(external.values()))
    registry=dict(release_id='PERSON_MULTISCENE_BASELINE_V1_20261029',runtime_version='0.1.0rc9',
        created=datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),scope='verified six-scene baseline',
        one_shared_runtime=True,per_scene_profiles=True,profiles=profiles,
        parent_delivery_seal_sha256=sha(PARENT/'DELIVERY_SEAL.json'),review_page=str(PARENT/'review/index.html'),
        changed_algorithms=False,new_scene_initialization='New videos must generate their own optical tracks and automatic A seeds; never reuse these source-specific coordinates.',
        baseline_change_rule='Create a new version and pass existing per-scene regression before replacing this baseline.')
    write(OUT/'BASELINE.json',registry)
    keys=['scene','engine','frames','status','condition','search_half_angle_deg','display_half_angle_deg',
        'residual_radius_px','raw_support_sampling','boundary_normalized_dog','persistent_input_hold','persistent_proposal_center','unresolved']
    with (OUT/'SCENE_MATRIX.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=keys);writer.writeheader()
        for p in profiles:writer.writerow({k:p[k] for k in keys})
    write(OUT/'BUILD_RECEIPT.json',dict(created=registry['created'],parent_seal_files_verified=len(prior['files']),
        frozen_python_files=len(list(runtime.glob('*.py'))),profiles=len(profiles),exact_source_copies=len(sources+copies),
        external_dependencies=len(external),algorithm_changes=False))
    print(json.dumps(read(OUT/'BUILD_RECEIPT.json'),ensure_ascii=False,indent=2))


if __name__=='__main__':main()
