"""Build seven GT-conditioned records; GT metadata stays outside the core."""
import hashlib
import numpy as np
from common import arguments, load_cases, writejson, git_snapshot, ROOT
from object_core import build_object
from render import panels


def provenance(obj, row, source):
    path = source / row['field']
    obj['full_field']['source'] = {
        'field_archive': path.relative_to(ROOT).as_posix(),
        'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'I0_source_key': 'field_bilinear',
        'native_sample_key': 'raw_nearest',
        'native_coordinate_keys': ['map_x', 'map_y'],
        'validity_key': 'imaging_valid',
        'semantics': 'Unchanged prior rotated bilinear display chart, not native amplitude; native nearest pixels retained in source archive',
    }
    obj['observation_metadata'] = {k: row[k] for k in [
        'scene', 'frame', 'gt_id', 'gt_geometry', 'patch_width', 'patch_height',
        'canonical_vehicle', 'identity_confidence', 'optical_visibility', 'atlas_id',
        'valid_fraction', 'original_gray', 'context', 'native']}
    obj['observation_metadata']['role'] = 'GT-conditioned observation only; never core input'


def main():
    args = arguments()
    rows = load_cases(args)
    manifest = []
    if not (args.out / 'PREEXISTING_GIT.json').exists():
        writejson(args.out / 'PREEXISTING_GIT.json', git_snapshot())
    for r, z, raw, note, anchor in rows:
        sid = r['sample_id']
        obj, arr = build_object(z, sid)
        obj['full_field']['file'] = f'{sid}_field.npz'
        obj['aperture'] = 'previous exact GT rotated chart; observation only'
        obj['case_note'] = note
        provenance(obj, r, args.source)
        np.savez_compressed(args.out / 'objects' / f'{sid}_field.npz', **arr)
        writejson(args.out / 'objects' / f'{sid}_object.json', obj)
        panels(obj, arr, args.out / 'figures' / f'{sid}_object.png', f'{r["atlas_id"]} {sid} | {note}')
        manifest.append(dict(sample_id=sid, atlas_id=r['atlas_id'], nuclei=len(obj['nuclei']),
                             segments=len(obj['segments']), relations=len(obj['relations']),
                             dark_regions=len(obj['dark_open_regions']), uncertainty=';'.join(obj['uncertainty'])))
        print(r['atlas_id'], manifest[-1], flush=True)
    writejson(args.out / 'GT_OBJECT_MANIFEST.json', manifest)


if __name__ == '__main__':
    main()
