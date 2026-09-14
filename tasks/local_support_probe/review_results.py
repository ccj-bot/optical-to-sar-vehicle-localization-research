"""Readout-only diagnostics; no fragment or group proposal changes."""
import json
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
import matplotlib.pyplot as plt
from run_probe import OUT,load,write,baseline,compare_native,figures,picture,overlay
from frozen_config import CONFIG


def main():
    config=CONFIG;native={};summary=[]
    for rec in load(OUT/'MANIFEST.json'):
        name=rec['name'];obj=load(OUT/'records'/(name+'.json.gz'));arr=dict(np.load(OUT/'records'/(name+'.npz')))
        _,extras=baseline(arr['I0']);arr.update(extras)
        np.savez_compressed(OUT/'records'/(name+'.npz'),**arr)
        if name in config['native_windows']:
            x0,y0,_,_=config['native_windows'][name]
            regions={k:[a-x0,b-y0,c-x0,d-y0] for k,(a,b,c,d) in config['visual_regions_native_only_posthoc'].items()}
            native[name]=(obj,arr)
        else:regions=config['visual_regions_chart_only_posthoc']
        obj['displayed_groups']=figures(name,obj,arr,regions)
        write(OUT/'records'/(name+'.json.gz'),obj)
        # Capture every proposed point's exact support persistence per scale.
        point_audit=[]
        for f in obj['fragments']:
            point_audit.append(dict(fragment=f['id'],scales={k:dict(crest_pixels=sum(v['crest_at_each_pixel']),
                  path_pixels=len(v['center'])) for k,v in f['scale_audit'].items()}))
        summary.append(dict(case=name,fragment_scale_witnesses=point_audit,displayed_groups=obj['displayed_groups']))
    compare_native(native,config)
    write(OUT/'SCALE_READOUT.json',summary)
    # Level-set change and component/PCA rejection must not be conflated.
    base=native['W1'][1];x0,y0,x1,y1=config['native_windows']['W1'];h,w=base['I0'].shape
    fig,axes=plt.subplots(3,4,figsize=(16,9),layout='constrained');levels=[]
    for row,name in enumerate(['W1','W2','W3']):
        obj,arr=native[name];ox,oy,_,_=config['native_windows'][name];dx,dy=x0-ox,y0-oy
        info=dict(window=name,levels={},component_readout=[])
        for col,method in enumerate(['baseline_q65_levelset','baseline_q65','baseline_q80_levelset','baseline_q80']):
            b=arr[method][dy:dy+h,dx:dx+w];yy,xx=np.where(b)
            picture(axes[row,col],base['I0'],name+' / '+method);overlay(axes[row,col],base['I0'].shape,np.c_[xx,yy],[.3,.7,1,.5])
        for q in [65,80]:
            info['levels'][str(q)]=float(arr[f'baseline_q{q}_level'])
            labels,_=ndi.label(arr[f'baseline_q{q}_levelset'],np.ones((3,3)))
            # Readout at a fixed already-reviewed main-band pixel, not runtime input.
            label=labels[1035-oy,1140-ox]
            if label:
                yy,xx=np.where(labels==label);xy=np.c_[xx,yy];ev,vec=np.linalg.eigh(np.cov(xy.T));extent=float(np.ptp(xy@vec[:,-1]))
                aspect=float(np.sqrt(ev[-1]/max(ev[0],1e-6)))
                info['component_readout'].append(dict(q=q,component=int(label),native_readout_pixel=[1140,1035],
                    support_pixels=len(xy),extent_px=extent,aspect=aspect,accepted_as_old_segment=bool(arr[f'baseline_q{q}'][1035-oy,1140-ox])))
        levels.append(info)
    fig.suptitle('Whole-aperture baseline | a stable EMPTY segment output is not recovery',fontsize=13)
    fig.savefig(OUT/'figures/BASELINE_LEVELS_AND_REJECTION.png',dpi=140);plt.close(fig)
    write(OUT/'BASELINE_READOUT.json',levels)
    # Each native readout uses identical I0 and coordinates across windows.
    for region,box in config['visual_regions_native_only_posthoc'].items():
        a,b,c,d=box;fig,axes=plt.subplots(3,3,figsize=(14,7),layout='constrained')
        for row,name in enumerate(['W1','W2','W3']):
            obj,arr=native[name];ox,oy,_,_=config['native_windows'][name];crop=arr['I0'][b-oy:d-oy,a-ox:c-ox]
            for col,title in enumerate(['I0 identical pixels','actual fragment support','group support (not filled gaps)']):
                picture(axes[row,col],crop,name+' '+region+' / '+title)
            for col,method in [(1,'oriented_support'),(2,'group_support')]:
                mask=arr[method][b-oy:d-oy,a-ox:c-ox];yy,xx=np.where(mask);overlay(axes[row,col],crop.shape,np.c_[xx,yy],[.2,.8,1,.6])
        fig.savefig(OUT/'figures'/('NATIVE_'+region.upper()+'.png'),dpi=140);plt.close(fig)
    print('Readout complete: no proposal retuning or window changes.')


if __name__=='__main__':main()
