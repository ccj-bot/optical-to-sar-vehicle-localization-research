"""Verify frozen profiles and execute every scene's real optical-input route."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'output/person_multiscene_baseline_v1_20261029'
QA=ROOT/'output/person_multiscene_baseline_v1_20261029_verification'
PARENT=ROOT/'output/person_runtime_integration_20261029'


def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))


def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()


def main():
    global QA
    parser=argparse.ArgumentParser();parser.add_argument('--verification-output',type=Path,default=QA)
    QA=parser.parse_args().verification_output.resolve()
    QA.mkdir(exist_ok=False)
    selected=read(OUT/'BASELINE.json')['profiles']
    cases=read(PARENT/'CASES.json')+read(PARENT/'EXTRA_CASES.json')
    for p in selected:
        c=next(c for c in cases if c['id']==p['source_case'])
        assert read(OUT/p['config'])==read(c['config'])
        for name in ['PREDICTIONS.csv','ANNOTATIONS.csv']:
            assert sha(OUT/p['results']/name)==sha(Path(c['output'])/name)
    for entry in read(OUT/'SOURCE_COPIES.json'):
        assert sha(entry['source'])==entry['sha256']==sha(OUT/entry['bundled'])
    spec=importlib.util.spec_from_file_location('person_frozen_launcher',OUT/'run.py')
    launcher=importlib.util.module_from_spec(spec);spec.loader.exec_module(launcher)
    seal=launcher.verify_package()
    launcher.verify_environment()
    external=launcher.verify_external(None,'run')
    command=[sys.executable,'-X','utf8','-B',str(OUT/'run.py')]
    completed=subprocess.run(command+['--list'],cwd=QA,capture_output=True,text=True,check=True)
    assert len(completed.stdout.strip().splitlines())==6
    (QA/'LIST.txt').write_text(completed.stdout,encoding='utf-8')
    def run(p):
        target=QA/p['scene']
        result=subprocess.run(command+['--scene',p['scene'],'--output',str(target),'--gate-only'],
            cwd=QA,capture_output=True,text=True)
        (QA/f"{p['scene']}.log").write_text(result.stdout+result.stderr,encoding='utf-8')
        assert result.returncode==0,(p['scene'],result.stderr)
        receipt=read(target/'BASELINE_RUN.json');gate=read(target/'result/GATE_ONLY.json');pkg=read(target/'result/PACKAGE.json')
        assert pkg['engine']==p['engine']==receipt['actual_engine']
        assert receipt['frozen_runtime']==str(OUT/'runtime/person_localizer')
        assert not gate['SAR_pixels_decoded'] and not gate['candidate_fitting_executed']
        old=next(c for c in cases if c['id']==p['source_case'])
        before=read(old['config']);after=read(target/'resolved_inputs/CONFIG.json');assert before==after
        decoded=read(target/'resolved_inputs/SCENE.json')
        assert Path(decoded['optical_csv']).is_relative_to(OUT)
        if p['engine']=='sequence':
            original_manifest=read(old['manifest']);resolved=read(target/'resolved_inputs/MANIFEST.json')
            path_keys={'scene','config','work_frames_cache','transport_cache','inherited_files','terminal_feedback'}
            assert {k:v for k,v in original_manifest.items() if k not in path_keys}=={k:v for k,v in resolved.items() if k not in path_keys}
            assert sorted(original_manifest.get('inherited_files',{}).values())==sorted(resolved.get('inherited_files',{}).values())
        return dict(scene=p['scene'],engine=p['engine'],gate_only_pass=True,config_identical=True,
            using_bundled_optical=True,receipt=str(target/'BASELINE_RUN.json'))
    checks=[]
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures=[pool.submit(run,p) for p in selected]
        for future in as_completed(futures):checks.append(future.result())
    # Verify the actual integrity guard with a changed manifest in a tiny fixture.
    fixture=QA/'integrity_guard_fixture';fixture.mkdir()
    (fixture/'payload.json').write_text('{"version":1}',encoding='utf-8')
    (fixture/'RELEASE_SEAL.json').write_text(json.dumps({'files':{'payload.json':sha(fixture/'payload.json')}}),encoding='utf-8')
    original_base=launcher.BASE;launcher.BASE=fixture
    launcher.verify_package()
    (fixture/'payload.json').write_text('{"version":2}',encoding='utf-8')
    rejected=False
    try:launcher.verify_package()
    except RuntimeError:rejected=True
    finally:launcher.BASE=original_base
    assert rejected
    launcher.BASE=fixture
    (fixture/'payload.json').write_text('{"version":1}',encoding='utf-8')
    (fixture/'unexpected.json').write_text('{}',encoding='utf-8')
    inventory_rejected=False
    try:launcher.verify_package()
    except RuntimeError:inventory_rejected=True
    finally:launcher.BASE=original_base
    assert inventory_rejected
    launcher.verify_package()
    receipt=dict(status='PASS_FROZEN_MULTISCENE_BASELINE_V1',profiles=len(selected),
        frozen_package_files=len(seal['files']),external_hashes_checked=len(external),exact_source_copies=len(read(OUT/'SOURCE_COPIES.json')),
        all_six_real_gate_routes_pass=True,prediction_tables_identical=True,configuration_values_identical=True,
        integrity_guard_rejects_changed_file=True,gate_checks=sorted(checks,key=lambda x:x['scene']),
        inventory_guard_rejects_unsealed_addition=True,environment_matches_frozen_versions=True,
        resolved_sequence_parameters_and_seed_provenance_identical=True,
        numerical_reexecution=False,numerical_evidence=str(PARENT/'RUNTIME_VERIFICATION.json'),
        R07_full_sequence_evidence=str(PARENT/'R07_COMPLETE_VERIFICATION.json'),
        frozen_package_unchanged_by_smoke_checks=True)
    (QA/'VERIFICATION.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in receipt.items() if k!='gate_checks'},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
