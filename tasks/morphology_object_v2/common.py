"""Read-only adapter for the seven previously reviewed GM morphology cases."""
import importlib.util
import argparse
import json
import subprocess
import hashlib
import numpy as np
from pathlib import Path
_path=Path(__file__).resolve().parents[1]/'sar_vehicle_morphology_object'/'common.py'
_spec=importlib.util.spec_from_file_location('_prior_morph_common',_path); _mod=importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_mod)
arguments,load_cases,writejson,savefig,git_snapshot = (_mod.arguments,_mod.load_cases,_mod.writejson,_mod.savefig,_mod.git_snapshot)
ROOT=_mod.ROOT; CASES=_mod.CASES

def arguments():
    p=argparse.ArgumentParser()
    p.add_argument('--source',type=Path,default=ROOT/'output/gm_gt_morphology_20260913')
    p.add_argument('--out',type=Path,default=ROOT/'output/morphology_object_v2')
    return p.parse_args()

def writejson(path,obj):
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False,
                    default=lambda v:v.item() if isinstance(v,np.generic) else v.tolist()),encoding='utf-8')

def git_snapshot():
    status=subprocess.check_output(['git','status','--porcelain=v1','-uall'],cwd=ROOT).decode('utf-8')
    excluded=['tasks/morphology_object_v2/','logs/morphology_object_v2.md','docs/morphology_object_v2_exploration.md']
    diff=subprocess.check_output(['git','diff','--binary'],cwd=ROOT)
    return dict(other_status=[x for x in status.splitlines() if not any(p in x for p in excluded)],
                unstaged_tracked_diff_sha256=hashlib.sha256(diff).hexdigest())
