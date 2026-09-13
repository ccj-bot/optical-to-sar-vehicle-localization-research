"""Portable I/O for seven image-conditioned morphology probes."""
import argparse
import csv
import hashlib
import json
import subprocess
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
from scipy import ndimage as ndi
font_manager.fontManager.addfont('C:/Windows/Fonts/msyh.ttc')
plt.rcParams['font.family'] = 'Microsoft YaHei'
plt.rcParams['axes.unicode_minus'] = False

ROOT = Path(__file__).resolve().parents[2]
CASES = [
    ('GM_RM017_f0344_g151', 'strong band / weak opposite segments', (.5, .48)),
    ('GM_RM017_f0330_g115', 'side band / end imbalance', (.5, .45)),
    ('GM_RM017_f0353_g177', 'endpoint groups / fragmented side', (.5, .48)),
    ('GM_RM017_f0378_g254', 'fragmented organization', (.5, .45)),
    ('GM_RM011_f0256_g77', 'layered short bars', (.5, .70)),
    ('GM_RM019_f0350_g332', 'opposite groups / dark interval', (.5, .48)),
    ('GM_RM017_f0344_g152', 'weak morphology / no forced whole', (.5, .48)),
]


def arguments():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, default=ROOT/'output/gm_gt_morphology_20260913')
    p.add_argument('--out', type=Path, default=ROOT/'output/sar_vehicle_morphology_object')
    return p.parse_args()


def readcsv(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def writejson(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_snapshot():
    status = subprocess.check_output(['git', 'status', '--porcelain=v1', '-uall'], cwd=ROOT).decode('utf-8')
    exclude = ['tasks/sar_vehicle_morphology_object/', 'logs/sar_vehicle_morphology_object.md',
               'docs/sar_vehicle_morphology_object_exploration.md']
    lines = [line for line in status.splitlines() if not any(p in line for p in exclude)]
    diff = subprocess.check_output(['git', 'diff', '--binary'], cwd=ROOT)
    return {'other_status': lines, 'unstaged_tracked_diff_sha256': hashlib.sha256(diff).hexdigest()}


def load_cases(args):
    args.out.mkdir(parents=True, exist_ok=True)
    for folder in ['figures', 'objects', 'fields']:
        (args.out/folder).mkdir(exist_ok=True)
    index = {r['sample_id']: r for r in readcsv(args.source/'SAMPLE_INDEX.csv')}
    result = []
    for sid, note, anchor in CASES:
        r = index[sid]
        with np.load(args.source/r['field']) as d:
            z = d['field_bilinear'].astype(float)
            valid = d['imaging_valid'].copy()
            raw = d['raw_nearest'].copy()
        # The selected previous crops are fully geometrically valid. Do not
        # silently inpaint if future inputs violate that experimental condition.
        assert valid.all() and np.isfinite(z).all()
        result.append((r, z, raw, note, anchor))
    return result


def smooth(z, sigma):
    return z.copy() if sigma == 0 else ndi.gaussian_filter(z, sigma, mode='reflect')


def show(ax, z, title, limits=None):
    lo, hi = (float(z.min()), float(z.max())) if limits is None else limits
    ax.imshow(z, cmap='gray', vmin=lo, vmax=hi, interpolation='nearest')
    ax.set_title(title, fontsize=10)
    ax.set_xlabel('x / GT chart px'); ax.set_ylabel('y / GT chart px')


def savefig(fig, path):
    fig.savefig(path, dpi=140, bbox_inches='tight')
    plt.close(fig)
