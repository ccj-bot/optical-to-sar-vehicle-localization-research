"""Independent pixel/path invariants and frozen-fixture integrity, not accuracy."""
import hashlib
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
from run_probe import ROOT,CODE_ROOT,OUT,load,write,snapshot,digest
from core import build
from frozen_config import CONFIG,FROZEN_TEXT


def main():
    pre=load(OUT/'PRE_RUN_FREEZE.json')
    assert hashlib.sha256(FROZEN_TEXT.encode('utf8')).hexdigest()==pre['sha256']
    assert pre['configuration']==CONFIG
    assert digest(Path(__file__).with_name('core.py'))==pre['code_sha256']
    counts=dict(records=0,fragments=0,groups=0,gaps=0)
    records={}; fields={}
    for row in load(OUT/'MANIFEST.json'):
        name=row['name'];o=load(OUT/'records'/(name+'.json.gz'));a=dict(np.load(OUT/'records'/(name+'.npz')))
        z=a['I0'];h,w=z.shape;records[name]=o;fields[name]=a
        assert np.isfinite(z).all()
        if name not in CONFIG['native_windows']:
            source=ROOT/row['source']['file']
            if not source.exists(): source=CODE_ROOT/row['source']['file']
            assert digest(source)==row['source']['sha256']
            assert np.array_equal(z,np.load(source)['I0'])
        for s in [1,2,4]:assert np.array_equal(a[f'I{s}'],ndi.gaussian_filter(z,s,radius=3*s,mode='reflect'))
        assert np.array_equal(a['rank_support'],z>ndi.percentile_filter(z,78,size=13,mode='reflect'))
        union=np.zeros(z.shape,bool);index={f['id']:f for f in o['fragments']}
        for f in o['fragments']:
            pts=np.asarray(f['support_xy'],int);d=np.array(CONFIG['oriented']['directions'][f['direction_index']]);normal=np.array([-d[1],d[0]])
            assert len(pts)>=3 and np.all(np.diff(pts,axis=0)==d)
            assert f['endpoints_xy']==[pts[0].tolist(),pts[-1].tolist()]
            assert f['path_xy']==f['support_xy']
            for scale in [0,1,2,4]:
                field=a[f'I{scale}'];audit=f['scale_audit'][f'I{scale}'];center=field[pts[:,1],pts[:,0]]
                assert np.array_equal(center,audit['center'])
                yes=np.ones(len(pts),bool)
                for distance in [-4,-2,2,4]:
                    other=pts+distance*normal;other[:,0]=np.clip(other[:,0],0,w-1);other[:,1]=np.clip(other[:,1],0,h-1)
                    samples=field[other[:,1],other[:,0]];assert np.array_equal(samples,audit['transverse_samples'][str(distance)])
                    yes &= center>samples+1e-9
                assert np.array_equal(yes,audit['crest_at_each_pixel'])
                if scale in [0,1]: assert yes.all()
            union[pts[:,1],pts[:,0]]=True;counts['fragments']+=1
        assert np.array_equal(union,a['oriented_support'])
        group_union=np.zeros(z.shape,bool)
        for g in o['groups']:
            pts=np.unique(np.concatenate([index[mid]['support_xy'] for mid in g['members']]),axis=0)
            assert np.array_equal(pts,np.array(g['support_xy']))
            assert g['attributes']['extent_px']<=48
            assert len({index[mid]['direction_index'] for mid in g['members']})==1
            assert 'not_transitive_closure' in g['uncertainty']
            group_union[pts[:,1],pts[:,0]]=True;counts['groups']+=1
        assert np.array_equal(group_union,a['group_support'])
        for gap in o['gaps']:
            pts=np.array(gap['section_xy']);assert np.array_equal(z[pts[:,1],pts[:,0]],gap['I0_profile'])
            assert gap['closest_endpoints_xy'][0] in index[gap['source']]['endpoints_xy']
            assert gap['closest_endpoints_xy'][1] in index[gap['target']]['endpoints_xy']
            mask=a[f'candidate_d{index[gap["source"]]["direction_index"]}']
            missing=pts[~mask[pts[:,1],pts[:,0]]]
            assert np.array_equal(missing,np.asarray(gap['missing_local_support_xy']).reshape(-1,2));counts['gaps']+=1
        for audit in o['old_chord_audit']:
            for path in audit['raw_supported_paths']:
                pts=np.array(path);assert a['oriented_support'][pts[:,1],pts[:,0]].all()
                assert np.all(np.max(np.abs(np.diff(pts,axis=0)),axis=1)==1)
            assert bool(audit['raw_supported_paths'])==(audit['type']=='CONTINUOUS_RIDGE')
        counts['records']+=1
    # Same native source as the prior frozen wide field, never a rotated chart.
    prior=ROOT/'output/morphology_object_v2/wide'
    assert np.array_equal(fields['W3']['I0'],np.load(prior/'wide_field.npz')['I0'])
    assert records['W3']['lineage']['sha256']==load(prior/'WIDE_RUNTIME_AUDIT.json')['source_sha256']
    for name in ['W1','W2']:
        x,y,x1,y1=CONFIG['native_windows'][name];ox,oy,_,_=CONFIG['native_windows']['W3']
        assert np.array_equal(fields[name]['I0'],fields['W3']['I0'][y-oy:y1-oy,x-ox:x1-ox])
    for record in load(OUT/'APERTURE_COMPARISON.json'):
        for method in ['rank_support','oriented_support']:
            assert record['support_comparisons'][method]['changed_interior_pixels']==0
    # Equality floor must never be promoted to a bright local crest.
    floor=fields['A_cores_only']['I0']==fields['A_cores_only']['I0'].min()
    assert not fields['A_cores_only']['oriented_support'][floor].any()
    c=fields['C_dark_middle_raised']['I0'];level=float(np.percentile(fields['A059_original']['I0'],85))
    flat=ndi.binary_erosion(c==level,structure=np.ones((9,9)),border_value=0)
    assert flat.any() and not fields['C_dark_middle_raised']['oriented_support'][flat].any()
    flatobj,flatarr=build(np.full((40,80),70.),CONFIG)
    assert not flatobj['fragments'] and not flatobj['groups'] and not flatarr['rank_support'].any()
    # A genuine support gap remains absent from the union of a candidate group.
    yy,xx=np.mgrid[:60,:100];z=np.full((60,100),5.)
    stripes=((xx>=20)&(xx<=29))|((xx>=36)&(xx<=45));z+=40*np.exp(-((yy-30)/1.5)**2)*stripes
    test,_=build(z,CONFIG)
    assert test['groups'] and any(g['missing_local_support_xy'] for g in test['gaps'])
    assert np.array_equal(np.sort(fields['A059_original']['I0'].ravel()),np.sort(fields['A059_shuffled']['I0'].ravel()))
    same_worktree=snapshot()==load(OUT/'PREEXISTING_GIT.json')
    report=dict(status='PASS_TECHNICAL_NOT_VEHICLE_OR_SEMANTIC_VALIDATION',counts=counts,
        plateau_fixture=dict(A_floor_pixels=int(floor.sum()),C_constant_interior_pixels=int(flat.sum()),
                              supported_A_floor_pixels=0,supported_C_constant_interior_pixels=0),
        workspace_audit='UNCHANGED' if same_worktree else 'NOT_ASSERTED_EXTERNAL_BRANCH_SWITCH; commits isolated on requested branch',
        tests=['exact sources and native overlap','frozen config/core hash unchanged','actual raw/smoothed transverse samples',
               'actual path endpoints and digital adjacency','groups exact member support union; no gap filling',
               'bounded local supports interior-invariant under native crops','constant field yields no fragments',
               'synthetic separated strips preserve a gap','exact histogram fixture'],
        limitations=['finite-context invariance is a design property, not vehicle evidence',
                     'group membership can remain ambiguous despite stable support',
                     'corridor audit does not disprove a wider curved or fragmented band'])
    write(OUT/'VALIDATION.json',report);print(report)


if __name__=='__main__':main()
