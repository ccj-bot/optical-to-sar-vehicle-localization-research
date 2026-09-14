"""REJECTED PILOT: not native-aperture or primitive-semantics evidence.

Image-only and deliberately small.  Local ranks propose fragments; they do not
define vehicles or produce a score.  Every accepted primitive is an I0 pixel
component.  A fitted line is retained only as an UNSUPPORTED_CHORD witness.
"""
import json, gzip
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'output/morphology_object_v2/local_fragments'
EX = ROOT / 'output/morphology_object_v2/share_examples'

def local_fragments(z, window=21, min_pixels=5):
    smooth = ndi.gaussian_filter(z, 2, mode='reflect')
    residual = z - ndi.gaussian_filter(z, 5, mode='reflect')
    # Local rank map: threshold is recomputed inside a fixed neighbourhood.
    local_q = ndi.percentile_filter(residual, 78, size=window, mode='reflect')
    support = residual >= local_q
    labels, n = ndi.label(support, np.ones((3,3)))
    fragments=[]
    for k in range(1,n+1):
        yy,xx=np.where(labels==k)
        if len(xx)<min_pixels: continue
        xy=np.c_[xx,yy].astype(float); c=xy.mean(0)
        cov=np.cov(xy.T) if len(xy)>2 else np.eye(2)
        ev,vec=np.linalg.eigh(cov); axis=vec[:,-1]; axis*=1 if axis[0]>=0 else -1
        along=(xy-c)@axis
        fragments.append(dict(id=f'F{k}', type='local_I0_fragment', support_xy=np.c_[xx,yy].tolist(),
            endpoints_xy=[(c+axis*np.percentile(along,p)).tolist() for p in [5,95]],
            attributes=dict(pixels=len(xx), peak=float(z[yy,xx].max()), mean_residual=float(residual[yy,xx].mean()),
                            scale='I0 pixel support; sigma2/5 only proposal context', axis_xy=axis.tolist(),
                            extent_px=float(np.ptp(along))), uncertainty=['proposal_from_local_rank','not_vehicle_part']))
    return fragments, residual, support

def groups(frags, max_gap=24):
    out=[]
    for i,a in enumerate(frags):
        aa=np.array(a['attributes']['axis_xy']); ca=np.mean(np.array(a['support_xy']),0)
        for j in range(i+1,len(frags)):
            b=frags[j]; bb=np.array(b['attributes']['axis_xy']); cb=np.mean(np.array(b['support_xy']),0)
            angle=np.degrees(np.arccos(np.clip(abs(aa@bb),0,1)))
            if np.linalg.norm(ca-cb)<=max_gap and angle<=30:
                out.append(dict(id=f'G{i}_{j}',type='candidate_support_group',members=[a['id'],b['id']],
                    relation_semantics=['shared_local_orientation','serial_or_dark_gap_unresolved'],
                    attributes=dict(distance_px=float(np.linalg.norm(ca-cb)),relative_angle_deg=float(angle)),
                    uncertainty=['candidate_group','dark_gap_not_filled','no_vehicle_membership']))
    return out

def classify_old_segments(z, old):
    result=[]
    for s in old.get('segments',[]):
        line=np.rint(np.array(s['geometry']['polyline_xy'])).astype(int)
        inside=(line[:,0]>=0)&(line[:,0]<z.shape[1])&(line[:,1]>=0)&(line[:,1]<z.shape[0])
        vals=z[line[inside,1],line[inside,0]]
        # A chord is unsupported when a substantial interior run is below its
        # own local support envelope. This is descriptive, not a threshold rule.
        gaps=np.where(vals < np.percentile(vals,40))[0]
        typ='CONTINUOUS_RIDGE' if len(gaps)==0 else ('FRAGMENT_GROUP' if len(gaps)<len(vals)*.35 else 'UNSUPPORTED_CHORD')
        result.append(dict(id=s['id'],proposed_type=typ,trace_pixels=int(len(vals)),low_run_count=int(len(gaps)),
                           note='classification is a raw-trace audit of prior chord, not vehicle semantics'))
    return result

def run_case(label,z,old=None):
    fr,res,support=local_fragments(z); gs=groups(fr)
    record=dict(label=label,shape=list(z.shape),parameters=dict(window=21,local_percentile=78,
        residual='I0 - gaussian_sigma5',component_connectivity=8,min_pixels=5,group_gap_px=24,orientation_deg=30),
        fragments=fr,groups=gs,old_segment_audit=classify_old_segments(z,old) if old else [],
        uncertainty=['local_proposal_only','groups_are_not_vehicle_objects'])
    fig,ax=plt.subplots(1,3,figsize=(15,4),layout='constrained')
    for a,title,img in zip(ax,['I0 original','local residual','I0 fragments / groups'],[z,res,z]):
        a.imshow(img,cmap='gray',interpolation='nearest');a.set_title(title);a.set_axis_off()
    for f in fr:
        xy=np.array(f['endpoints_xy']);ax[2].plot(xy[:,0],xy[:,1],lw=1)
    for g in gs:
        pts=[]
        for mid in g['members']:
            f=next(f for f in fr if f['id']==mid);pts.append(np.mean(np.array(f['support_xy']),0))
        p=np.array(pts);ax[2].plot(p[:,0],p[:,1],'y--',lw=.6)
    fig.suptitle(label+' | local I0 fragments; no score');fig.savefig(OUT/(label+'.png'),dpi=140);plt.close(fig)
    return record

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    with np.load(EX/'A059_original_field.npz') as d: orig=d['I0']
    with np.load(EX/'A059_shuffled_field.npz') as d: shuf=d['I0']
    old=json.loads(gzip.decompress((EX/'A059_original_object.json.gz').read_bytes()))
    rec=[]
    rec.append(run_case('A059_original',orig,old))
    rec.append(run_case('A059_shuffled',shuf,None))
    # Fixed same native pixels, nested windows; center is frozen by coordinates,
    # not inferred from output. The original patch occupies this common crop.
    windows={'W1':orig[10:64,20:140],'W2':orig[4:70,12:148],'W3':orig[0:74,0:160]}
    nested=[]
    for name,z in windows.items():
        r=run_case('A059_'+name,z,old if name=='W3' else None);nested.append(r)
    plateau=np.load(EX/'A059_original_field.npz')['I0'].copy(); plateau[22:52,30:112]=np.percentile(plateau,85)
    rec.append(run_case('A059_plateau_C',plateau,old));
    payload = dict(cases=rec,nested=nested,conclusion={
        'scope':'representation probe only','no_vehicle_score':True,
        'notes':['local rank avoids direct whole-aperture q65/q80 but remains a proposal convention',
                 'fragment support is always actual I0 pixels; fitted endpoints are descriptive',
                 'group geometry is not a relation type added to MorphologyObject',
                 'plateau and shuffle are fixed failure fixtures']})
    (OUT/'RESULTS.json').write_text(json.dumps(payload, indent=2),encoding='utf8')
    print('local fragment probe complete',[(r['label'],len(r['fragments']),len(r['groups'])) for r in rec])

if __name__=='__main__':
    raise SystemExit('Rejected design; see README and report. Outputs from initial run retained only for audit.')
