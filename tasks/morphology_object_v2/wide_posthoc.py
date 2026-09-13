"""Read GT only AFTER hashed wide object; never feeds runtime construction."""
import json,hashlib
import numpy as np
import matplotlib.pyplot as plt
from scipy import ndimage as ndi
from common import ROOT,writejson,savefig
from render import panels,base,segments

def main():
    out=ROOT/'output/morphology_object_v2';wide=out/'wide';audit=json.loads((wide/'WIDE_RUNTIME_AUDIT.json').read_text())
    assert hashlib.sha256((wide/'wide_object.json').read_bytes()).hexdigest()==audit['object_sha256']
    wobj=json.loads((wide/'wide_object.json').read_text());wa=dict(np.load(wide/'wide_field.npz'))
    panels(wobj,wa,out/'figures'/'WIDE_RUNTIME_object.png','Frozen 300 x 180 native aperture | STOP_GRAPH_BUDGET')
    sid='GM_RM017_f0344_g151';gobj=json.loads((out/'objects'/(sid+'_object.json')).read_text())
    gd=np.load(ROOT/'output/gm_gt_morphology_20260913/fields'/(sid+'.npz'))
    x0,y0,x1,y1=wobj['aperture']['observation_xyxy']
    def to_wide(xy):
        xy=np.asarray(xy);mx=ndi.map_coordinates(gd['map_x'],[xy[:,1],xy[:,0]],order=1);my=ndi.map_coordinates(gd['map_y'],[xy[:,1],xy[:,0]],order=1)
        return np.c_[mx-x0,my-y0]
    correspondences=[]
    for n in gobj['nuclei']:
        xy=to_wide([n['xy']])[0];pool=[q for q in wobj['nuclei'] if q['scale_px']==n['scale_px']]
        matches=[dict(id=q['id'],distance_px=float(np.linalg.norm(np.array(q['xy'])-xy))) for q in pool if np.linalg.norm(np.array(q['xy'])-xy)<=3]
        correspondences.append(dict(source=n['id'],native_wide_xy=xy.tolist(),all_compatible_nuclei=matches,semantics='posthoc_3px_geometric_compatibility_not_identity'))
    traces=[]
    for s in gobj['segments']:
        xy=to_wide(s['geometry']['polyline_xy']);traces.append(dict(source=s['id'],native_wide_xy=xy.tolist()))
    fig,ax=plt.subplots(1,3,figsize=(17,6),layout='constrained');z=wa['I0']
    base(ax[0],z,'G_WIDE original; no GT runtime input',(0,255));base(ax[1],z,'G_WIDE segment hypotheses',(0,255));segments(ax[1],wobj)
    base(ax[2],z,'POSTHOC ONLY: GT object traces in wide',(0,255));segments(ax[2],wobj,False)
    for t in traces:
        xy=np.array(t['native_wide_xy']);ax[2].plot(xy[:,0],xy[:,1],'--',lw=1.3,label=t['source'])
    ax[2].legend(fontsize=8);fig.suptitle('GT release: structures versus attribution | relation construction stopped, not recovered object',fontsize=13)
    savefig(fig,out/'figures'/'WIDE_POSTHOC.png')
    writejson(wide/'POSTHOC_COMPARISON.json',dict(runtime_object_sha256=audit['object_sha256'],status='MORPHOLOGY_NOT_RECOVERED_AT_OBJECT_LAYER',
        cause='nucleus budget exceeded: retain field/nuclei/segments; no relation graph computed; do not raise budget',
        nuclei=correspondences,gt_segment_traces=traces,relation_recovery='NOT_EVALUABLE_RUNTIME_RELATIONS_NOT_BUILT',
        no_center_error=True,analyst_not_blind=True))
    print('posthoc only',sum(bool(x['all_compatible_nuclei']) for x in correspondences),'/',len(correspondences),'geometric nucleus compatibility; no object recovery claim')

if __name__=='__main__':main()
