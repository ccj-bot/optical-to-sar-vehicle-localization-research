"""Witness-oriented visualizations, never an abstract force-directed graph."""
import numpy as np
import matplotlib.pyplot as plt
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]/'sar_vehicle_morphology_object'))
from common import savefig
from topology import draw_tree,focus_leaves


def base(ax,z,title,limits=None):
    lo,hi=(float(z.min()),float(z.max())) if limits is None else limits
    ax.imshow(z,cmap='gray',vmin=lo,vmax=hi,interpolation='nearest');ax.set_title(title,fontsize=10)
    ax.set_xlabel('x / aperture px');ax.set_ylabel('y / aperture px')


def segments(ax,obj,labels=True):
    for i,s in enumerate(obj['segments']):
        xy=np.array(s['geometry']['polyline_xy']);color=plt.get_cmap('tab10')(i%10)
        ax.plot(xy[:,0],xy[:,1],color=color,lw=1.1)
        if labels:ax.text(*s['geometry']['center_xy'],s['id'],color=color,fontsize=8)


def relations(ax,obj):
    index={s['id']:s for s in obj['segments']}
    for r in obj['relations']:
        if not r['id'].startswith('R'):continue
        a=index[r['source']]['geometry']['center_xy'];b=index[r['target']]['geometry']['center_xy']
        color='cyan' if 'opposite' in r['type'] else ('orange' if 'serial' in r['type'] else '#c8a1d4')
        ax.plot([a[0],b[0]],[a[1],b[1]],color=color,lw=.8,ls='--')
        ax.text((a[0]+b[0])/2,(a[1]+b[1])/2,r['id'],color=color,fontsize=8)


def dark(ax,obj,shape):
    overlay=np.zeros((*shape,4))
    for d in obj['dark_open_regions']:
        record=d['regions'][0];xy=np.asarray(record['pixels_xy'])
        if len(xy):overlay[xy[:,1],xy[:,0]]=[.15,.6,1,.22]
        ax.plot(*d['seed_xy'],'o',mfc='none',mec='yellow',ms=4)
    ax.imshow(overlay)


def panels(obj,arr,path,title):
    z=arr['I0'];limits=(float(z.min()),float(z.max()));fig,ax=plt.subplots(2,4,figsize=(17,9),layout='constrained')
    base(ax[0,0],z,'I0: unchanged field',limits);base(ax[0,1],arr['I2'],'I_sigma: proposals only',limits)
    base(ax[0,2],z,'Nuclei: sigma 2 view; all scales saved',limits)
    for n in obj['nuclei']:
        if n['scale_px']==2:ax[0,2].plot(*n['xy'],'.',ms=2,color='cyan')
    base(ax[0,3],z,'Candidate segment geometry',limits);segments(ax[0,3],obj)
    tree=obj['merge_topology']['I_sigma'];labels=draw_tree(ax[1,0],tree,focus_leaves(tree,8));ax[1,0].set_title('I_sigma merge tree (8 view leaves)')
    for nid,label in labels.items():
        x,y=tree['nodes'][nid]['xy'];ax[0,2].text(x,y,str(label),color='yellow',fontsize=7)
    base(ax[1,1],z,'2D relation graph: cyan=opposite',limits);segments(ax[1,1],obj);relations(ax[1,1],obj)
    base(ax[1,2],z,'Dark/open witnesses (not interior mask)',limits);dark(ax[1,2],obj,z.shape)
    base(ax[1,3],z,'Combined object: no forced assignment',limits);dark(ax[1,3],obj,z.shape);segments(ax[1,3],obj);relations(ax[1,3],obj)
    fig.suptitle(title+'\nGT/aperture is not response mask; semantic edges are hypotheses',fontsize=13)
    savefig(fig,path)
    # A separate witness page shows exact paths and original intensity profiles.
    rels=[r for r in obj['relations'] if r['id'].startswith('R')]
    fig,ax=plt.subplots(2,3,figsize=(14,8),layout='constrained');base(ax[0,0],z,'I0 + proposed segment traces',limits);segments(ax[0,0],obj)
    for s in obj['segments']:
        check=s['raw_check'];ax[0,1].plot(check['I0'],lw=.7,label=s['id']);ax[0,2].plot(np.array(check['I0'])-.5*(np.array(check['I0_left'])+check['I0_right']),lw=.7,label=s['id'])
    ax[0,1].set_title('Original centerline profiles');ax[0,2].set_title('I0 center minus two flanks (not a score)');ax[0,2].axhline(0,color='gray',lw=.5)
    for a in ax[0,1:]:
        a.set_xlabel('sample along proposed line');a.set_ylabel('display gray')
        if obj['segments']:a.legend(fontsize=6)
    base(ax[1,0],z,'First typed edge: exact paths',limits)
    if rels:
        r=rels[0]
        for key,color in [('I0_merge','orange'),('I_sigma_merge','cyan')]:
            xy=np.array(r['witness'][key]['path_xy']);ax[1,0].plot(xy[:,0],xy[:,1],color=color,lw=.8,label=key)
        ax[1,0].legend(fontsize=7)
    for d in obj['dark_open_regions']:
        ax[1,1].plot(d['I0_profile'],lw=.8,label=d['id']+' I0');ax[1,1].plot(d['I_sigma_profile'],ls='--',lw=.8)
    ax[1,1].set_title('Cross-group gap: I0 solid / sigma dashed');ax[1,1].set_xlabel('cross-section sample')
    if obj['dark_open_regions']:ax[1,1].legend(fontsize=6)
    ax[1,2].axis('off');lines=[]
    for r in rels[:7]:
        types=[v for v in r['type'] if v in ['opposite','serial','separated_by_dark_gap','open_configuration']]
        lines.append(r['id']+': '+', '.join(types)+'\n'+f"raw saddle {r['witness']['I0_merge']['level']:.1f}; sigma {r['witness']['I_sigma_merge']['level']:.1f}")
    ax[1,2].text(0,1,'\n'.join(lines) or 'No segment-level relation formed.',va='top',fontsize=8)
    fig.suptitle(title+' | original-field witnesses',fontsize=12);savefig(fig,path.with_name(path.stem+'_witness.png'))
