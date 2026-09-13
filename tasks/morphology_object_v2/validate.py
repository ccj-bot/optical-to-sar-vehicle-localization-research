"""Technical witness/integrity tests, NOT scientific morphology acceptance."""
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
from PIL import Image
from common import ROOT, CASES, git_snapshot, writejson
from object_core import sample, build_object, merge_tree, merge_witness
from intervene import SELECTED, variants

OUT = ROOT / 'output/morphology_object_v2'
COUNTS = dict(objects=0, segments=0, pair_relations=0, exact_paths=0, dark_level_regions=0)


def read(path):
    return json.loads(path.read_text(encoding='utf8'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def raster(xy, shape):
    result = np.zeros(shape, dtype=bool)
    xy = np.asarray(xy, dtype=int).reshape(-1, 2)
    if len(xy):
        assert np.all(xy >= 0) and np.all(xy[:, 0] < shape[1]) and np.all(xy[:, 1] < shape[0])
        result[xy[:, 1], xy[:, 0]] = True
        assert result.sum() == len(xy)
    return result


def check_object(path):
    obj = read(path)
    arr = dict(np.load(path.parent / obj['full_field']['file']))
    z = arr['I0']; f = arr['I2']; h, w = z.shape
    assert obj['kind'] == 'MorphologyObject' and z.ndim == 2 and np.isfinite(z).all()
    for sigma in [1, 2, 4]:
        assert np.array_equal(arr[f'I{sigma}'], ndi.gaussian_filter(z, sigma, mode='reflect'))
    ns = {n['id']: n for n in obj['nuclei']}
    segs = {s['id']: s for s in obj['segments']}
    assert len(ns) == len(obj['nuclei']) and len(segs) == len(obj['segments'])
    assert 'not_a_physical_object_assignment' in obj['uncertainty']
    if len(ns) > obj['parameters']['max_nuclei'] or len(segs) > obj['parameters']['max_segments']:
        assert 'STOP_GRAPH_BUDGET' in obj['uncertainty'] and not obj['relations']
    for n in ns.values():
        x, y = n['xy']; field = arr[f'I{int(n["scale_px"])}']
        assert 0 <= x < w and 0 <= y < h
        assert field[y, x] == n['attributes']['analysis_peak']
        assert z[y, x] == n['attributes']['I0_at_proposal']
        assert 'not_physical_scatterer' in n['uncertainty']
        assert field[y, x] == field[max(0, y-1):y+2, max(0, x-1):x+2].max()
    supports = {}
    for s in segs.values():
        COUNTS['segments'] += 1
        support = raster(s['geometry']['support_xy'], z.shape); supports[s['id']] = support
        level = s['attributes']['analysis_level']; assert np.all(f[support] >= level)
        assert np.isclose(level, np.percentile(f, s['attributes']['quantile']))
        assert set(s['nuclei']) <= ns.keys()
        for nid in s['nuclei']:
            x, y = ns[nid]['xy']; assert support[y, x]
        trace = s['raw_check']
        for field, xy, key in [(z, 'center_xy', 'I0'), (f, 'center_xy', 'I_sigma'),
                               (z, 'flank_left_xy', 'I0_left'), (z, 'flank_right_xy', 'I0_right')]:
            assert np.array_equal(sample(field, trace[xy]), trace[key])
        assert ndi.label(support & (z >= level), np.ones((3, 3)))[1] == trace['raw_components_at_same_level']
        assert 'uncertain_segment' in s['uncertainty']
    for r in obj['relations']:
        assert r['source'] in segs and r['target'] in segs
        if r['type'] == ['nested_analysis_support']:
            assert np.all(supports[r['target']][supports[r['source']]])
            continue
        COUNTS['pair_relations'] += 1
        assert r['semantics_status'] == 'computational_relation_hypothesis'
        a = segs[r['source']]['attributes']['anchor_xy']; b = segs[r['target']]['attributes']['anchor_xy']
        for key, field in [('I0_merge', z), ('I_sigma_merge', f)]:
            witness = r['witness'][key]; xy = np.array(witness['path_xy'], dtype=int); level = witness['level']
            assert np.array_equal(xy[0], a) and np.array_equal(xy[-1], b)
            assert np.all(xy >= 0) and np.all(xy[:, 0] < w) and np.all(xy[:, 1] < h)
            assert np.all(np.max(np.abs(np.diff(xy, axis=0)), axis=1) == 1)
            assert np.isclose(field[xy[:, 1], xy[:, 0]].min(), level, rtol=0, atol=1e-10)
            labels, _ = ndi.label(field >= level, np.ones((3, 3)))
            assert labels[a[1], a[0]] > 0 and labels[a[1], a[0]] == labels[b[1], b[0]]
            labels, _ = ndi.label(field >= np.nextafter(level, np.inf), np.ones((3, 3)))
            assert labels[a[1], a[0]] == 0 or labels[b[1], b[0]] == 0 or labels[a[1], a[0]] != labels[b[1], b[0]]
            COUNTS['exact_paths'] += 1
        xy = np.array(r['witness']['I_sigma_merge']['path_xy'])
        assert z[xy[:, 1], xy[:, 0]].min() == r['attributes']['I0_min_on_smoothed_path']
    for d in obj['dark_open_regions']:
        assert np.array_equal(sample(z, d['cross_section_xy']), d['I0_profile'])
        assert np.array_equal(sample(f, d['cross_section_xy']), d['I_sigma_profile'])
        x, y = d['seed_xy']
        for record in d['regions']:
            field = z if record['field'] == 'I0' else f
            labels, _ = ndi.label(field <= record['level'], np.ones((3, 3)))
            expected = labels == labels[y, x] if labels[y, x] else np.zeros(z.shape, bool)
            observed = raster(record['pixels_xy'], z.shape)
            assert np.array_equal(expected, observed)
            sides = [s for s, yes in [('left', observed[:, 0].any()), ('right', observed[:, -1].any()),
                                      ('top', observed[0].any()), ('bottom', observed[-1].any())] if yes]
            assert sides == record['boundary_sides']
            COUNTS['dark_level_regions'] += 1
    for tree in obj['merge_topology'].values():
        for n in tree['nodes']:
            assert 'winner' not in n and 'elder_representative' in n
            for child in n['children']:
                assert tree['nodes'][child]['parent'] == n['id'] and tree['nodes'][child]['level'] >= n['level']
    COUNTS['objects'] += 1
    return obj, arr


def main():
    manifest = read(OUT / 'GT_OBJECT_MANIFEST.json')
    assert {r['sample_id'] for r in manifest} == {r[0] for r in CASES}
    historical = read(ROOT / 'output/sar_vehicle_morphology_object/CASE_LINEAGE.json')
    for r in historical:
        source = ROOT / 'output/gm_gt_morphology_20260913' / r['field']
        assert digest(source) == r['sha256']
        objpath = OUT / 'objects' / (r['sample_id'] + '_object.json')
        obj = read(objpath)
        assert obj['full_field']['source']['sha256'] == r['sha256']
        assert np.array_equal(np.load(source)['field_bilinear'], np.load(objpath.parent / obj['full_field']['file'])['I0'])
        assert np.load(source)['imaging_valid'].all()
    for path in sorted((OUT / 'objects').glob('*_object.json')):
        check_object(path)
        assert (OUT / 'figures' / (path.stem + '.png')).is_file()
        assert (OUT / 'inspect' / (path.stem.removesuffix('_object') + '.html')).is_file()
    for sid in SELECTED:
        z = np.load(OUT / 'objects' / (sid + '_field.npz'))['I0']
        for name, expected, inverse, operation in variants(z):
            prefix = sid + '__' + name; arr = np.load(OUT / 'objects' / (prefix + '_field.npz'))
            assert np.array_equal(expected, arr['I0'])
            comparison = read(OUT / 'objects' / (prefix + '_comparison.json'))
            assert comparison['relation_identity'] == 'NOT_ASSIGNED'
            if inverse is not None:
                assert np.array_equal(np.sort(z.ravel()), np.sort(arr['I0'].ravel()))
                assert np.array_equal(arr['I0'].ravel()[arr['original_pixel_to_new_flat']], z.ravel())
            if name.startswith('C_'):
                xy = np.array(operation['edited_xy'])
                assert np.all(arr['I0'][xy[:, 1], xy[:, 0]] >= np.percentile(z, 85))
                assert np.any(arr['I0'] > z)
    wide = OUT / 'wide'; audit = read(wide / 'WIDE_RUNTIME_AUDIT.json')
    assert digest(Path(__file__).with_name('wide_freeze.json')) == audit['freeze_sha256']
    assert digest(wide / 'wide_object.json') == audit['object_sha256']
    assert read(wide / 'POSTHOC_COMPARISON.json')['runtime_object_sha256'] == audit['object_sha256']
    wobj, wa = check_object(wide / 'wide_object.json')
    assert len(wobj['nuclei']) == 2137 and len(wobj['segments']) == 10 and not wobj['relations']
    assert wa['I0'].shape == (180, 300) and 'STOP_GRAPH_BUDGET' in wobj['uncertainty']
    opens = audit['runtime_file_opens']
    assert not any(s.lower() in p.lower() for p in opens for s in ['SAMPLE_INDEX', 'gm_gt_morphology', 'g151', 'labels', 'gt_geometry'])
    source = Path(opens[0]); assert digest(source) == audit['source_sha256']
    native = np.asarray(Image.open(source)); x0, y0, x1, y1 = wobj['aperture']['observation_xyxy']
    assert np.array_equal(native[y0:y1, x0:x1, 0], wa['I0'])
    # Behavioral failure fixtures: do not silently turn a plateau into success.
    flat, _ = build_object(np.ones((10, 40)))
    assert flat['segments'] and 'uncertain_segment' in flat['segments'][0]['uncertainty']
    # Same connected hierarchy can have different coordinate layout.
    fixture = np.array([[0., 0., 0., 0., 0.], [0., 9., 3., 8., 0.], [0., 0., 0., 0., 0.]])
    t, a = merge_tree(fixture); tt, aa = merge_tree(fixture.T)
    m = merge_witness(fixture, t, a, [1, 1], [3, 1]); mm = merge_witness(fixture.T, tt, aa, [1, 1], [1, 3])
    assert m['level'] == mm['level'] == 3 and m['path_xy'] != mm['path_xy']
    assert COUNTS['objects'] == 20
    assert git_snapshot() == read(OUT / 'PREEXISTING_GIT.json')
    record = dict(status='PASS_TECHNICAL_WITNESSES_NOT_SCIENTIFIC_ACCEPTANCE', counts=COUNTS,
                  source_arrays='7 unchanged prior fields; historical SHA256 verified', interventions='12 replayed incl 2 originals; D/E exact histograms',
                  wide='freeze/object/source hashes unchanged; no GT opens in recorded interval; budget stop enforced',
                  workspace='preexisting status and unstaged tracked diff hash unchanged',
                  known_failure_fixture='constant plateau still proposes a segment; preserved and reported, not fixed',
                  hierarchy_geometry_fixture='transpose preserves merge level while changing image path',
                  limitations=['file audit begins after imports; not an OS sandbox proof', 'raw witnesses verified, not semantic acceptance',
                               'intervention operation replay shares generator; explicit histogram and fill checks are additional invariants'])
    writejson(OUT / 'QA_VALIDATION.json', record)
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
