"""Attach observation-only provenance, rerender and build local witness inspector.

No object rebuilding or wide-runtime mutation. Run after interventions/posthoc.
"""
import argparse
import csv
import html
import json
from pathlib import Path
import numpy as np
from common import ROOT, writejson
from run_gt import provenance
from render import panels


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--rerender', action='store_true')
    args = parser.parse_args()
    out = ROOT / 'output/morphology_object_v2'
    source = ROOT / 'output/gm_gt_morphology_20260913'
    notes = json.loads(Path(__file__).with_name('review_notes.json').read_text(encoding='utf8'))
    manifest = json.loads((out / 'GT_OBJECT_MANIFEST.json').read_text())
    with (source / 'SAMPLE_INDEX.csv').open(encoding='utf-8-sig', newline='') as stream:
        rows = {r['sample_id']: r for r in csv.DictReader(stream)}
    template = Path(__file__).with_name('inspect_template.html').read_text(encoding='utf8')
    (out / 'inspect').mkdir(exist_ok=True)
    links = []
    paths = [out / 'objects' / (r['sample_id'] + '_object.json') for r in manifest]
    paths += sorted((out / 'objects').glob('*__*_object.json'))
    paths += [out / 'wide/wide_object.json']
    for path in paths:
        obj = json.loads(path.read_text(encoding='utf8'))
        sid = path.stem.removesuffix('_object')
        baseid = sid.split('__')[0]
        if sid in rows:
            provenance(obj, rows[sid], source)
            writejson(path, obj)
        elif '__' in sid:
            obj['full_field']['source'] = {'original_field': baseid + '_field.npz',
                                         'operation': 'object.intervention', 'role': 'same-source display intervention'}
            writejson(path, obj)
        arr = dict(np.load(path.parent / obj['full_field']['file']))
        wide = sid == 'wide'
        prefix = 'WIDE_RUNTIME' if wide else sid
        panel = out / 'figures' / (prefix + '_object.png')
        title = obj.get('observation_metadata', {}).get('atlas_id', '') + ' ' + obj['id']
        note = notes['wide'] if wide else notes['cases'][baseid]
        if '__' in sid:
            note += ' INTERVENTION: ' + notes['interventions']
        if args.rerender:
            panels(obj, arr, panel, title)
        reduced = {k: v for k, v in obj.items() if k not in ['merge_topology', 'proposal_ledger']}
        data = dict(object=reduced, arrays={k: arr[k].tolist() for k in ['I0', 'I2']},
                    title=title, note=note, panel='../figures/' + panel.name,
                    witness='../figures/' + panel.stem + '_witness.png',
                    links={'Complete object JSON': '../' + path.relative_to(out).as_posix(),
                           'Full field NPZ': '../' + (path.parent / obj['full_field']['file']).relative_to(out).as_posix()})
        if sid in rows:
            data['links']['Native SAR context'] = '../../gm_gt_morphology_20260913/' + rows[sid]['context']
            data['links']['Native nearest sampling'] = '../../gm_gt_morphology_20260913/' + rows[sid]['native']
        content = template.replace('__DATA__', json.dumps(data, ensure_ascii=False, allow_nan=False).replace('</', '<\\/'))
        (out / 'inspect' / (sid + '.html')).write_text(content, encoding='utf8')
        links.append(f'<li><a href="inspect/{sid}.html">{html.escape(title)}</a> — {html.escape(note)}</li>')
    overview = ['GM_RM017_f0344_g151_interventions.png', 'GM_RM019_f0350_g332_interventions.png', 'WIDE_POSTHOC.png']
    page = '<!doctype html><meta charset="utf-8"><title>MorphologyObject v2</title><style>body{font:17px system-ui;max-width:1200px;margin:30px auto;line-height:1.7}li{margin:14px 0}img{width:100%}</style>'
    page += '<h1>可回指原场的 MorphologyObject：7 个 GT 案例 + 10 项干预 + 1 个冻结宽窗口</h1><p>先看原图，再选择结构层/单元。每条候选关系均可单独回看二维位置和鞍路径。蓝色是带边界开放状态的暗区见证，不是车辆 Mask。漂亮的图不代表解析成功。</p>'
    page += '<p><a href="../../docs/morphology_object_v2_exploration.md">研究报告</a> · <a href="QA_VALIDATION.json">技术验证</a></p><ol>' + ''.join(links) + '</ol>'
    for name in overview:
        page += f'<h2>{name}</h2><a href="figures/{name}"><img src="figures/{name}" alt="{name}"></a>'
    (out / 'INDEX.html').write_text(page, encoding='utf8')
    print('Inspector pages:', len(paths), '| No science recomputation; wide runtime unchanged')


if __name__ == '__main__':
    main()
