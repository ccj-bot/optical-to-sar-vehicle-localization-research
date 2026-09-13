"""Two clear cases, five frozen interventions, rebuilt field-backed objects."""
import numpy as np
import matplotlib.pyplot as plt
from common import arguments, load_cases, writejson, savefig
from object_core import build_object
from render import base,segments,relations,panels,dark

SELECTED={'GM_RM017_f0344_g151','GM_RM019_f0350_g332'}

def variants(z):
    h,w=z.shape;low=float(z.min());yy,xx=np.mgrid[:h,:w]
    result=[('original',z.copy(),None,{'operation':'none'})]
    high=float(np.percentile(z,97));result.append(('A_cores_only',np.where(z>=high,z,low),None,{'operation':'below_q97_to_source_min','level':high}))
    strip=(xx>=.32*w)&(xx<.70*w)&(yy<.30*h);q85=float(np.percentile(z,85));weak=strip&(z<q85);f=z.copy();f[weak]=low
    result.append(('B_weak_strip_removed',f,None,{'operation':'frozen_top_strip_below_q85_to_min','edited_xy':np.c_[xx[weak],yy[weak]].tolist(),'level':q85}))
    middle=(xx>=.18*w)&(xx<.82*w)&(yy>=.30*h)&(yy<.70*h);f=z.copy();f[middle]=np.maximum(f[middle],q85)
    result.append(('C_dark_middle_raised',f,None,{'operation':'raise_frozen_middle_to_at_least_q85','edited_xy':np.c_[xx[middle],yy[middle]].tolist(),'level':q85,'region_is_manual_intervention_not_inferred_interior':True}))
    x0,x1=int(.18*w),int(.70*w);length=max(2,int(.18*h));y0,y1=int(.72*h),int(.34*h)
    mapping=np.arange(z.size).reshape(z.shape);mapping[y0:y0+length,x0:x1],mapping[y1:y1+length,x0:x1]=mapping[y1:y1+length,x0:x1].copy(),mapping[y0:y0+length,x0:x1].copy()
    f=z.ravel()[mapping];inverse=np.argsort(mapping.ravel())
    result.append(('D_units_relocated',f,inverse,{'operation':'swap_equal_opposite_band_and_middle_blocks','blocks_xywh':[[x0,y0,x1-x0,length],[x0,y1,x1-x0,length]],'histogram_exact':True,'seam_confounds':True}))
    rng=np.random.default_rng(20260914);mapping=rng.permutation(z.size);f=z.ravel()[mapping].reshape(z.shape)
    result.append(('E_layout_shuffled',f,np.argsort(mapping),{'operation':'exact_permutation','seed':20260914,'histogram_exact':True}))
    return result

def compare(original,new,inverse,shape):
    h,w=shape;nn=[];ss=[]
    for n in original['nuclei']:
        x,y=n['xy'];j=y*w+x if inverse is None else int(inverse[y*w+x]);ny,nx=divmod(j,w)
        matches=[q['id'] for q in new['nuclei'] if q['scale_px']==n['scale_px'] and np.linalg.norm(np.array(q['xy'])-[nx,ny])<=2]
        nn.append(dict(source=n['id'],mapped_xy=[nx,ny],compatible_proposals=matches,semantics='all_within_2px_same_scale_not_identity'))
    for s in original['segments']:
        xy=np.array(s['geometry']['support_xy']);pixels=xy[:,1]*w+xy[:,0]
        if inverse is not None:pixels=inverse[pixels]
        pool=set(pixels.tolist());matches=[]
        for t in new['segments']:
            if t['attributes']['quantile']!=s['attributes']['quantile']:continue
            xy=np.array(t['geometry']['support_xy']);other=set((xy[:,1]*w+xy[:,0]).tolist());overlap=len(pool&other)
            if overlap:matches.append(dict(target=t['id'],shared_pixels=overlap,source_support_pixels=len(pool),target_support_pixels=len(other)))
        ss.append(dict(source=s['id'],all_overlapping_candidates=matches,semantics='support_overlap_not_segment_identity'))
    return dict(nuclei=nn,segments=ss,original_relations=[{'id':r['id'],'type':r['type']} for r in original['relations']],rebuilt_relations=[{'id':r['id'],'type':r['type']} for r in new['relations']],relation_identity='NOT_ASSIGNED')

def main():
    args=arguments();records=[]
    for r,z,raw,note,anchor in load_cases(args):
        if r['sample_id'] not in SELECTED:continue
        sid=r['sample_id'];fig,ax=plt.subplots(3,6,figsize=(21,10),layout='constrained');orig=None;desc=[]
        for j,(name,f,inverse,operation) in enumerate(variants(z)):
            obj,arr=build_object(f,sid+'__'+name)
            if orig is None:orig=obj
            prefix=f'{sid}__{name}';obj['full_field']['file']=prefix+'_field.npz';obj['intervention']=operation;obj['intervention']['same_source_not_physical_counterfactual']=True
            arr['original_pixel_to_new_flat']=np.arange(z.size) if inverse is None else inverse
            np.savez_compressed(args.out/'objects'/(prefix+'_field.npz'),**arr);writejson(args.out/'objects'/(prefix+'_object.json'),obj)
            writejson(args.out/'objects'/(prefix+'_comparison.json'),compare(orig,obj,inverse,z.shape))
            for k in range(3):base(ax[k,j],f,name if k==0 else ('Segments / typed edges' if k==1 else 'Dark/open witnesses'),(z.min(),z.max()))
            segments(ax[1,j],obj,labels=False);relations(ax[1,j],obj);dark(ax[2,j],obj,z.shape)
            panels(obj,arr,args.out/'figures'/(prefix+'_object.png'),r['atlas_id']+' '+name)
            desc.append(dict(variant=name,object=prefix+'_object.json',comparison=prefix+'_comparison.json',operation=operation,uncertainty=obj['uncertainty'],relations=[e['type'] for e in obj['relations']]))
            print(r['atlas_id'],name,len(obj['segments']),len(obj['relations']),flush=True)
        fig.suptitle(r['atlas_id']+' | Original and five interventions; fixed display range; no score',fontsize=13)
        savefig(fig,args.out/'figures'/f'{sid}_interventions.png');records.append(dict(sample_id=sid,variants=desc))
    writejson(args.out/'INTERVENTION_SUMMARY.json',records)

if __name__=='__main__':main()
