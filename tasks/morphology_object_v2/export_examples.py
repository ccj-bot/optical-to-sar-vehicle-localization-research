"""Export a small, lossless teaching subset; no experiment rerun or source edits."""
import argparse
import gzip
import hashlib
import json
import shutil
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SID = 'GM_RM017_f0344_g151'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, default=ROOT / 'output/morphology_object_v2/share_examples')
    args = parser.parse_args()
    source = ROOT / 'output/morphology_object_v2'
    args.out.mkdir(parents=True, exist_ok=True)
    records = []
    for label, sid in [('A059_original', SID), ('A059_shuffled', SID + '__E_layout_shuffled')]:
        original = source / 'objects' / (sid + '_object.json')
        obj = json.loads(original.read_text(encoding='utf8'))
        field = source / 'objects' / obj['full_field']['file']
        target = args.out / (label + '_field.npz')
        shutil.copyfile(field, target)
        obj['full_field']['file'] = target.name
        # Lineage is retained separately; machine paths are not portable inputs.
        old_source = obj['full_field'].pop('source', {})
        obj['full_field']['source_lineage'] = {
            'source_record_sha256': digest(original),
            'source_field_sha256': digest(field),
            'source_archive_sha256': old_source.get('sha256'),
            'scope': 'source paths omitted; all morphology nodes, relations and trees unchanged',
        }
        metadata = obj.get('observation_metadata', {})
        for key in ['original_gray', 'context', 'native']:
            metadata.pop(key, None)
        obj['example_scope'] = 'display-domain teaching subset, not detection or physical target truth'
        raw = json.dumps(obj, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf8')
        compressed = args.out / (label + '_object.json.gz')
        compressed.write_bytes(gzip.compress(raw, mtime=0))
        assert gzip.decompress(compressed.read_bytes()) == raw
        assert digest(target) == digest(field)
        shutil.copyfile(source / 'figures' / (sid + '_object.png'), args.out / (label + '.png'))
        records.append(dict(label=label, original_source_record_sha256=digest(original),
                            record=compressed.name, field=target.name,
                            object_id=obj['id'], I0_shape=list(np.load(target)['I0'].shape)))
    for src, dst in [(SID + '_interventions.png', 'A059_interventions.png'), ('WIDE_POSTHOC.png', 'WIDE_posthoc.png')]:
        shutil.copyfile(source / 'figures' / src, args.out / dst)
    z = np.load(args.out / 'A059_original_field.npz')['I0']
    shuffled = np.load(args.out / 'A059_shuffled_field.npz')
    assert np.array_equal(np.sort(z.ravel()), np.sort(shuffled['I0'].ravel()))
    assert np.array_equal(shuffled['I0'].ravel()[shuffled['original_pixel_to_new_flat']], z.ravel())
    files = {p.name: dict(bytes=p.stat().st_size, sha256=digest(p)) for p in sorted(args.out.iterdir()) if p.name != 'MANIFEST.json'}
    manifest = dict(scope='one GT-conditioned observation, one same-source shuffle; two contextual figures',
                    records=records, files=files, payload_bytes=sum(r['bytes'] for r in files.values()),
                    validation='NPZ bytes unchanged; complete JSON gzip roundtrip; exact histogram and inverse permutation',
                    nonclaims=['not native amplitude', 'no final Mask or detection box', 'wide figure is posthoc; wide runtime data not bundled'])
    (args.out / 'MANIFEST.json').write_text(json.dumps(manifest, indent=2), encoding='utf8')
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
