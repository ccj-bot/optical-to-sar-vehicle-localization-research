"""Second probe: nuclei-to-segment relations and same-source destructions."""
import numpy as np
import matplotlib.pyplot as plt
from scipy import ndimage as ndi
from common import arguments, load_cases, writejson, smooth, show, savefig
from topology import merge_tree


def ridge_field(z, sigma=2.0):
    f = smooth(z, sigma)
    dxx = ndi.gaussian_filter(z, sigma, order=(0, 2)); dyy = ndi.gaussian_filter(z, sigma, order=(2, 0)); dxy = ndi.gaussian_filter(z, sigma, order=(1, 1))
    lam = np.empty_like(z); direction = np.empty_like(z)
    for y in range(z.shape[0]):
        for x in range(z.shape[1]):
            ev, vec = np.linalg.eigh([[dxx[y,x], dxy[y,x]], [dxy[y,x], dyy[y,x]]])
            lam[y,x] = ev[0]; direction[y,x] = np.arctan2(vec[1,0], vec[0,0])
    # Positive transverse curvature magnitude, normalized only for viewing.
    score = np.maximum(0, -lam)
    score /= max(float(np.percentile(score, 99)), 1e-8)
    return f, np.clip(score, 0, 1), direction


def ridge_segments(score, direction, q=82):
    # A deliberately provisional ridge graph: q is a view control, not a learned threshold.
    mask = score >= np.percentile(score, q)
    lab, n = ndi.label(mask, structure=np.ones((3,3)))
    segments=[]
    for i in range(1,n+1):
        yy,xx=np.where(lab==i)
        if len(xx)<5: continue
        angles=direction[yy,xx]; segments.append({'id':f'R{i}','pixels':int(len(xx)), 'centroid_uv':[float((xx+.5).mean()/score.shape[1]),float((yy+.5).mean()/score.shape[0])], 'axis_deg':float(np.degrees(np.arctan2(np.sin(angles).mean(),np.cos(angles).mean()))), 'view_only_q':q})
    return mask, segments


def destroys(z):
    q90,q65=float(np.percentile(z,90)),float(np.percentile(z,65))
    nuclei=np.where(z>=q90,z,z.min())
    no_weak=np.where(z>=q65,z,q65)
    filled=z.copy(); h,w=z.shape; filled[int(.32*h):int(.68*h), int(.18*w):int(.82*w)] = np.median(z)
    rng=np.random.default_rng(20260913); shuffled=z.ravel().copy(); rng.shuffle(shuffled); shuffled=shuffled.reshape(z.shape)
    return {'original':z,'strong_nuclei_only':nuclei,'weak_support_removed':no_weak,'dark_interval_filled':filled,'spatial_layout_shuffled':shuffled}


def main():
    args=arguments(); rows=load_cases(args); summary=[]
    for r,z,raw,note,anchor in rows:
        sid=r['sample_id']; fig,ax=plt.subplots(2,5,figsize=(19,8),layout='constrained'); f,score,direction=ridge_field(z); mask,segs=ridge_segments(score,direction)
        show(ax[0,0],z,'原始场：核与弱支撑均保留'); show(ax[0,1],score,'临时 ridge 响应：σ2 横向曲率 magnitude', (0,1)); ax[0,1].imshow(mask,alpha=.4,cmap='autumn'); ax[0,1].set_title('临时 ridge 图（q82，仅观察）')
        for seg in segs:
            ax[0,1].text(seg['centroid_uv'][0]*z.shape[1],seg['centroid_uv'][1]*z.shape[0],seg['id'],color='cyan',fontsize=8)
        show(ax[0,2],f,'σ2 中尺度场'); show(ax[0,3],z,'核→段：只显示临时段质心')
        for seg in segs: ax[0,3].plot(seg['centroid_uv'][0]*z.shape[1],seg['centroid_uv'][1]*z.shape[0],'o',mfc='none',mec='orange')
        q40=float(np.percentile(z,40)); low=z<=q40
        show(ax[0,4],z,'低场 q40：暗间隔/开放性观察')
        ax[0,4].imshow(low, cmap='Blues', alpha=.35, interpolation='nearest')
        variations=destroys(z); desc=[]
        for j,(name,field) in enumerate(variations.items()):
            show(ax[1,j],field,name.replace('_','\n'))
            tree,_=merge_tree(field); peaks=sum(n['kind']=='peak' for n in tree['nodes']); merges=sum(n['kind']=='merge' for n in tree['nodes'])
            desc.append({'case':sid,'variant':name,'peaks':peaks,'merges':merges,'min':float(field.min()),'max':float(field.max()),'operation_semantics':'same-source display intervention; not a physical counterfactual'})
        fig.suptitle(f'{r["atlas_id"]} {sid} | {note}\nRidge/segment and destruction probes: no vehicle score or mask',fontsize=13)
        savefig(fig,args.out/'figures'/f'{sid}_relations_destruction.png')
        writejson(args.out/'objects'/f'{sid}_relations.json',{'sample_id':sid,'gt_geometry':r['gt_geometry'],'note':note,'ridge_sigma':2,'ridge_segments':segs,'ridge_semantics':'Provisional curvature ridge; threshold q82 is view control, not acceptance.','destructions':desc,'source_field':r['field']})
        summary.extend(desc)
        print(r['atlas_id'],len(segs),flush=True)
    writejson(args.out/'RELATION_SUMMARY.json',summary)
    writejson(args.out/'RELATION_NOTES.json',{'what_ridge_keeps':'elongated transverse-curvature response and provisional segment centroids','what_it_loses':'weak support below view q and branches crossing at junctions','what_destruction_tests':'whether visible organization survives nuclei-only, weak-support removal, dark-interval fill, or spatial shuffle','not_a_classifier':True})


if __name__=='__main__':main()
