"""Frozen single-frame fixtures and exact-native nested-aperture experiment."""
import argparse
import gzip
import hashlib
import json
import subprocess
import os
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from core import build
from frozen_config import CONFIG, FROZEN_TEXT

CODE_ROOT = Path(__file__).resolve().parents[2]
ROOT = Path(os.environ.get('LOCAL_SUPPORT_WORKSPACE', str(CODE_ROOT)))
OUT = ROOT / 'output/local_support_probe'
SID = 'GM_RM017_f0344_g151'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, obj):
    payload = json.dumps(obj, ensure_ascii=False, allow_nan=False, indent=2,
                         default=lambda v: v.item() if isinstance(v,np.generic) else v.tolist()).encode('utf8')
    path.write_bytes(gzip.compress(payload, mtime=0) if path.suffix == '.gz' else payload)


def load(path):
    return json.loads(gzip.decompress(path.read_bytes()) if path.suffix == '.gz' else path.read_bytes())


def snapshot():
    lines = subprocess.check_output(['git','status','--porcelain=v1','-uall'], cwd=ROOT).decode('utf8').splitlines()
    exclusions = ['tasks/local_support_probe/', 'docs/local_support_probe_20260914.md', 'logs/local_support_probe_20260914.md']
    return dict(other_status=[s for s in lines if not any(e in s for e in exclusions)],
                tracked_diff_sha256=hashlib.sha256(subprocess.check_output(['git','diff','--binary'],cwd=ROOT)).hexdigest())


def baseline(z):
    f = ndi.gaussian_filter(z,2,mode='reflect'); out = {}; records=[]
    for q in [65,80]:
        level = float(np.percentile(f,q)); lab,n = ndi.label(f>=level,np.ones((3,3)))
        out[f'baseline_q{q}_levelset'] = f>=level
        out[f'baseline_q{q}_level'] = np.array(level)
        mask = np.zeros(z.shape,bool)
        for k,sl in enumerate(ndi.find_objects(lab),1):
            if sl is None: continue
            yy,xx=np.where(lab[sl]==k); yy+=sl[0].start; xx+=sl[1].start
            if len(xx)<20: continue
            xy=np.c_[xx,yy]; ev,vec=np.linalg.eigh(np.cov(xy.T)); extent=float(np.ptp(xy@vec[:,-1]))
            if extent>=12 and np.sqrt(ev[-1]/max(ev[0],1e-6))>=2:
                mask[yy,xx]=True
                records.append(dict(id=f'S{q}_{k}',support_xy=xy.tolist(),analysis_level=level,quantile=q,
                                    semantics='prior_whole_aperture_connected_support_proposal_not_ridge'))
        out[f'baseline_q{q}']=mask
    return records,out


def picture(ax,z,title):
    ax.imshow(z,cmap='gray',vmin=float(z.min()),vmax=float(z.max()),interpolation='nearest')
    ax.set_title(title,fontsize=9); ax.set_xlabel('aperture x / px');ax.set_ylabel('aperture y / px')


def overlay(ax,shape,xy,color):
    rgba=np.zeros((*shape,4)); pts=np.asarray(xy,int).reshape(-1,2)
    if len(pts):rgba[pts[:,1],pts[:,0]]=color
    ax.imshow(rgba,interpolation='nearest')


def figures(name,obj,arr,regions):
    z=arr['I0']; fig,axes=plt.subplots(1,4,figsize=(17,5),layout='constrained')
    for ax,title in zip(axes,['I0 unchanged','Finite local rank: actual support','Raw crest paths: actual pixels','Groups: support union only']):picture(ax,z,title)
    yy,xx=np.where(arr['rank_support']);overlay(axes[1],z.shape,np.c_[xx,yy],[.2,.7,1,.55])
    for f in obj['fragments']:
        overlay(axes[2],z.shape,f['support_xy'],plt.get_cmap('tab10')(f['direction_index']))
    for i,g in enumerate(obj['groups']):
        color=list(plt.get_cmap('tab10')(i%10));color[3]=.45;overlay(axes[3],z.shape,g['support_xy'],color)
    fig.suptitle(name+' | no fitted chords; no all-pairs graph',fontsize=13)
    fig.savefig(OUT/'figures'/(name+'_support.png'),dpi=140);plt.close(fig)
    # Spatially ordered group witnesses. Readout regions NEVER enter core.
    selected=[]
    for g in obj['groups']:
        xy=np.array(g['support_xy']);c=xy.mean(0)
        region=next((key for key,(x0,y0,x1,y1) in regions.items() if x0<=c[0]<x1 and y0<=c[1]<y1),None)
        if region:selected.append((region,float(c[0]),float(c[1]),g))
    selected=sorted(selected,key=lambda s:s[:3]); page_records=[]
    # Four spatially ordered witnesses PER readout region, no strength ranking.
    selected=[entry for region in regions for entry in [s for s in selected if s[0]==region][:4]]
    if selected:
        fig,axes=plt.subplots(len(selected),3,figsize=(12,2.6*len(selected)),squeeze=False,layout='constrained')
        byid={f['id']:f for f in obj['fragments']}; edges={e['id']:e for e in obj['gaps']}
        for row,(region,cx,cy,g) in enumerate(selected):
            xy=np.array(g['support_xy']); lo=np.maximum(xy.min(0)-7,0);hi=np.minimum(xy.max(0)+8,[z.shape[1],z.shape[0]])
            for ax in axes[row,:2]:
                picture(ax,z,region+' / '+g['id']);ax.set_xlim(lo[0],hi[0]);ax.set_ylim(hi[1],lo[1])
            for j,mid in enumerate(g['members']):
                f=byid[mid];overlay(axes[row,1],z.shape,f['support_xy'],plt.get_cmap('tab10')(j%10))
                e=np.array(f['endpoints_xy']);axes[row,1].plot(e[:,0],e[:,1],'o',ms=2,mfc='none',mec='yellow')
                axes[row,1].text(*e[0],mid,fontsize=6,color='white')
            for eid in g['gap_witnesses']:
                gap=edges[eid]; pts=np.array(gap['section_xy']);axes[row,1].plot(pts[:,0],pts[:,1],'--',lw=.7,color='cyan')
                axes[row,2].plot(gap['I0_profile'],lw=.8,label=eid)
            axes[row,2].set_title('I0 gap profiles, not support bridges',fontsize=9)
            axes[row,2].set_xlabel('section sample');axes[row,2].legend(fontsize=6)
            page_records.append(dict(group=g['id'],region=region))
        fig.suptitle(name+' | bounded alternative fragment groups; endpoints are actual pixels',fontsize=12)
        fig.savefig(OUT/'figures'/(name+'_groups.png'),dpi=120);plt.close(fig)
    return page_records


def region_note(obj,arr,regions):
    result={}
    for key,(x0,y0,x1,y1) in regions.items():
        result[key]=dict(readout_xyxy=[x0,y0,x1,y1],
                        fragments=[f['id'] for f in obj['fragments'] if any(x0<=x<x1 and y0<=y<y1 for x,y in f['support_xy'])],
                        groups=[g['id'] for g in obj['groups'] if any(x0<=x<x1 and y0<=y<y1 for x,y in g['support_xy'])])
    return result


def native_signature(rec,origin,clip):
    xy=np.asarray(rec['support_xy'],int)+origin;x0,y0,x1,y1=clip
    xy=xy[(xy[:,0]>=x0)&(xy[:,0]<x1)&(xy[:,1]>=y0)&(xy[:,1]<y1)]
    return tuple(sorted(map(tuple,xy.tolist())))


def compare_native(native,config):
    baseobj,basearr=native['W1']; box=config['native_windows']['W1'];x0,y0,x1,y1=box;h,w=basearr['I0'].shape
    fig,axes=plt.subplots(3,4,figsize=(16,9),layout='constrained');output=[]
    methods=['baseline_q65','rank_support','oriented_support','group_support']
    for row,name in enumerate(['W1','W2','W3']):
        obj,arr=native[name];ox,oy,_,_=config['native_windows'][name];dy,dx=y0-oy,x0-ox
        assert np.array_equal(arr['I0'][dy:dy+h,dx:dx+w],basearr['I0'])
        entry=dict(window=name,reference_window='W1',exact_native_pixel_overlap=True,support_comparisons={},fragments=[],groups=[])
        for col,method in enumerate(methods):
            a=basearr[method];b=arr[method][dy:dy+h,dx:dx+w];diff=a!=b;halo=9
            picture(axes[row,col],basearr['I0'],name+' -> W1 / '+method)
            yy,xx=np.where(a&b);overlay(axes[row,col],a.shape,np.c_[xx,yy],[.4,1,.5,.45])
            yy,xx=np.where(a&~b);overlay(axes[row,col],a.shape,np.c_[xx,yy],[1,.1,.1,.8])
            yy,xx=np.where(b&~a);overlay(axes[row,col],a.shape,np.c_[xx,yy],[.2,.5,1,.8])
            entry['support_comparisons'][method]=dict(changed_xy=np.c_[np.where(diff)[1],np.where(diff)[0]].tolist(),
                changed_pixels=int(diff.sum()),interior_halo_px=halo,changed_interior_pixels=int(diff[halo:-halo,halo:-halo].sum()))
        for method in ['baseline_q65_levelset','baseline_q80_levelset','baseline_q80']:
            a=basearr[method];b=arr[method][dy:dy+h,dx:dx+w];diff=a!=b
            entry['support_comparisons'][method]=dict(changed_xy=np.c_[np.where(diff)[1],np.where(diff)[0]].tolist(),
                changed_pixels=int(diff.sum()),interior_halo_px=9,changed_interior_pixels=int(diff[9:-9,9:-9].sum()))
        for collection in ['fragments','groups','rank_regions']:
            target_members={f['id']:f for f in obj['fragments']}
            base_members={f['id']:f for f in baseobj['fragments']}
            def signature(rec,origin,members):
                sig=native_signature(rec,origin,box)
                if collection=='groups':
                    parts=[native_signature(members[mid],origin,box) for mid in rec['members']]
                    return (sig,tuple(sorted(part for part in parts if part)))
                return sig
            entry.setdefault(collection,[])
            lookup={}
            for target in obj[collection]:
                sig=signature(target,np.array([ox,oy]),target_members)
                if sig:lookup.setdefault(sig,[]).append(target['id'])
            for source in baseobj[collection]:
                sig=signature(source,np.array([x0,y0]),base_members)
                entry[collection].append(dict(source=source['id'],all_exact_clipped_support_matches=lookup.get(sig,[]),
                    semantics='same_native_support_and_for_groups_same_member_partition; not_identity'))
        output.append(entry)
    fig.suptitle('Same native pixels | green shared; red only W1; blue only larger window\nLocal pixels, maximal fragment extent and group membership are separate stability questions',fontsize=12)
    fig.savefig(OUT/'figures/NATIVE_STABILITY.png',dpi=140);plt.close(fig)
    write(OUT/'APERTURE_COMPARISON.json',output)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--raw-root',type=Path,required=True);args=parser.parse_args()
    OUT.mkdir(exist_ok=True)
    for folder in ['records','figures']: (OUT/folder).mkdir(exist_ok=True)
    config=CONFIG
    if not (OUT/'PREEXISTING_GIT.json').exists():write(OUT/'PREEXISTING_GIT.json',snapshot())
    write(OUT/'PRE_RUN_FREEZE.json',dict(configuration=config,sha256=hashlib.sha256(FROZEN_TEXT.encode('utf8')).hexdigest(),
          code_sha256=digest(Path(__file__).with_name('core.py')),freeze_precedes_source_decode=True))
    cases=[];base=CODE_ROOT/'tasks/morphology_object_v2/examples';prior=ROOT/'output/morphology_object_v2/objects'
    for name in ['original','shuffled']:
        path=base/f'A059_{name}_field.npz';old=load(base/f'A059_{name}_object.json.gz')
        cases.append((f'A059_{name}',np.load(path)['I0'],old,dict(file=path.relative_to(CODE_ROOT).as_posix(),sha256=digest(path)),config['visual_regions_chart_only_posthoc']))
    for name in ['A_cores_only','C_dark_middle_raised']:
        path=prior/(SID+'__'+name+'_field.npz');old=load(prior/(SID+'__'+name+'_object.json'))
        cases.append((name,np.load(path)['I0'],old,dict(file=path.relative_to(ROOT).as_posix(),sha256=digest(path)),config['visual_regions_chart_only_posthoc']))
    source=args.raw_root/config['native_image'];rgb=np.asarray(Image.open(source));assert rgb.ndim==3 and np.array_equal(rgb[:,:,0],rgb[:,:,1]) and np.array_equal(rgb[:,:,1],rgb[:,:,2])
    for name,(x0,y0,x1,y1) in config['native_windows'].items():
        z=rgb[y0:y1,x0:x1,0].astype(float)
        regions={k:[a-x0,b-y0,c-x0,d-y0] for k,(a,b,c,d) in config['visual_regions_native_only_posthoc'].items()}
        cases.append((name,z,None,dict(file=config['native_image'],sha256=digest(source),native_xyxy=[x0,y0,x1,y1],sampling='native_only'),regions))
    manifest=[];native={}
    for name,z,old,lineage,regions in cases:
        obj,arr=build(z,config,old);obj['baseline'],extras=baseline(z);arr.update(extras)
        arr['group_support']=np.zeros(z.shape,bool)
        for g in obj['groups']:
            xy=np.array(g['support_xy']);arr['group_support'][xy[:,1],xy[:,0]]=True
        obj.update(name=name,lineage=lineage,parameters=config,field_file=name+'.npz')
        obj['posthoc_readout']=region_note(obj,arr,regions)
        obj['displayed_groups']=figures(name,obj,arr,regions)
        np.savez_compressed(OUT/'records'/(name+'.npz'),**arr);write(OUT/'records'/(name+'.json.gz'),obj)
        manifest.append(dict(name=name,fragments=len(obj['fragments']),groups=len(obj['groups']),gaps=len(obj['gaps']),
                             source=lineage,old_chords=obj['old_chord_audit'],uncertainty=obj['uncertainty']))
        if name in config['native_windows']:native[name]=(obj,arr)
        print(name,'fragments',len(obj['fragments']),'groups',len(obj['groups']),'gaps',len(obj['gaps']),flush=True)
    compare_native(native,config)
    write(OUT/'MANIFEST.json',manifest)
    print('Done. All data/figures under output/local_support_probe; no target outputs.')


if __name__=='__main__': main()
