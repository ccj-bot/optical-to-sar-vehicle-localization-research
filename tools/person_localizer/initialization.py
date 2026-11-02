"""Explicit automatic initialization for sequence execution."""
import copy
from pathlib import Path

from .pipeline import Scene, dump, sha, now


def prepare_groups(manifest, spec, config, out):
    groups = copy.deepcopy(manifest['groups'])
    settings = manifest.get('initialization', {})
    mode = settings.get('mode','manifest_seeds')
    if mode not in {'manifest_seeds','rebuild_automatic'}:
        raise ValueError('initialization.mode must be manifest_seeds or rebuild_automatic')
    inherited = manifest.get('inherited_files',{})
    for p, expected in inherited.items():
        if sha(p) != expected: raise ValueError(f'Inherited initialization changed: {p}')
    receipt = dict(created=now(),mode=mode,reference_read=False,
        recomputed_from_current_source=(mode=='rebuild_automatic'),inherited_files=inherited)
    if mode == 'rebuild_automatic':
        cfg = copy.deepcopy(config)
        cfg['initialization_geometry_scope'] = settings.get('geometry_scope','whole_track')
        init = Scene(copy.deepcopy(spec),cfg,Path(out)/'automatic_initialization')
        result = init.run()
        for group in groups:
            selection = group.get('seed_selection','independent')
            if selection not in {'independent','joint_if_available'}:
                raise ValueError('seed_selection must be independent or joint_if_available')
            seeds=[]; frames=set()
            for q in group['queries']:
                r=result[q]; sel=init.selections[q]
                if selection=='joint_if_available' and r.get('joint_stage'):
                    chosen=r['joint_stage']['selected']
                    source_q=r['joint_stage']['group'][0]
                    anchor=init.selections[source_q]['anchor']
                    for member in r['joint_stage']['group']:frames.update(init.selections[member]['A'])
                else:
                    if 'selected' not in r:raise RuntimeError(f'NO_AUTOMATIC_INITIALIZATION:{q}:{r.get("status")}')
                    chosen=r['selected'];anchor=sel['anchor'];frames.update(sel['A'])
                seeds.append({**chosen,'anchor':anchor})
            group.update(seeds=seeds,A=sorted(frames),seeds_at_anchor=True)
        receipt.update(geometry_scope=cfg['initialization_geometry_scope'],
            source_video=spec['sar_video'],source_video_sha256=sha(spec['sar_video']),
            optical_csv=spec['optical_csv'],optical_sha256=sha(spec['optical_csv']),
            outputs={str(init.out/p):sha(init.out/p) for p in ['RESULTS.json','OPTICAL_SELECTION.json','COMPLETION_SEAL.json']})
    receipt['groups_before_transport']=groups
    dump(Path(out)/'INITIALIZATION.json',receipt)
    return groups
