"""Small reproducibility and non-regression checks for this exploratory branch."""
import json, hashlib, subprocess
from pathlib import Path
from common import ROOT, CASES, digest


def main():
    out=ROOT/'output/sar_vehicle_morphology_object'; src=ROOT/'output/gm_gt_morphology_20260913'
    for p in [out/'CASE_LINEAGE.json',out/'MERGE_SUMMARY.json',out/'RELATION_SUMMARY.json',out/'RELATION_NOTES.json']:
        assert p.is_file(),p
    lineage=json.loads((out/'CASE_LINEAGE.json').read_text(encoding='utf8')); assert len(lineage)==len(CASES)
    for row in lineage:
        assert digest(src/row['field'])==row['sha256']
        for s in [0,2]:
            assert (out/'objects'/f'{row["sample_id"]}_tree_s{s}.json').is_file()
            assert (out/'fields'/f'{row["sample_id"]}_tree_s{s}.npz').is_file()
            assert (out/'figures'/f'{row["sample_id"]}_merge.png').is_file()
        assert (out/'figures'/f'{row["sample_id"]}_relations_destruction.png').is_file()
        obj=json.loads((out/'objects'/f'{row["sample_id"]}_relations.json').read_text(encoding='utf8'))
        assert obj['ridge_semantics'].startswith('Provisional') and all(x['operation_semantics'].startswith('same-source') for x in obj['destructions'])
    snapshot=json.loads((out/'PREEXISTING_GIT.json').read_text(encoding='utf8'))
    status=subprocess.check_output(['git','status','--porcelain=v1','-uall'],cwd=ROOT).decode('utf8').splitlines()
    other=[x for x in status if not any(p in x for p in ['tasks/sar_vehicle_morphology_object/','logs/sar_vehicle_morphology_object.md','docs/sar_vehicle_morphology_object_exploration.md'])]
    assert other==snapshot['other_status'], 'pre-existing worktree changed outside task'
    print('PASS',len(lineage),'cases; pre-existing worktree unchanged outside task')


if __name__=='__main__':main()
