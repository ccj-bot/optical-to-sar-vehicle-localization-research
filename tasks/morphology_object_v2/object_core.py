"""Image-only morphology record. No GT, identity, scene or car-score input."""
import sys
from pathlib import Path
from collections import deque
import numpy as np
from scipy import ndimage as ndi
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'sar_vehicle_morphology_object'))
from topology import merge_tree, join

PARAMETERS = dict(scales=[1., 2., 4.], analysis_sigma=2., segment_quantiles=[80, 65],
                  support_min_pixels=20, line_min_extent_px=12., line_min_aspect=2.,
                  parallel_tolerance_deg=25., serial_tolerance_deg=25., opposite_min_deg=60.,
                  pair_radius_px=100., neighbours_per_segment=3,
                  max_nuclei=1500, max_segments=80, max_pair_relations=120)


def clean_tree(t):
    for n in t['nodes']:
        if 'winner' in n: n['elder_representative'] = n.pop('winner')
    return t


def sample(field, xy):
    xy=np.asarray(xy)
    return ndi.map_coordinates(field, [xy[:,1],xy[:,0]], order=1, mode='nearest')


def section(a,b):
    return np.linspace(a,b,max(3,int(np.ceil(np.linalg.norm(np.array(b)-a)))+1))


def axial_angle(a,b):
    return float(np.degrees(np.arccos(np.clip(abs(np.dot(a,b)),0,1))))


def path_above(z, start, target, level):
    h,w=z.shape; sx,sy=start; tx,ty=target
    allowed=z>=level; previous=np.full(z.size,-1,dtype=int); first=sy*w+sx; last=ty*w+tx
    previous[first]=first; queue=deque([first])
    while queue and previous[last]<0:
        cur=queue.popleft(); y,x=divmod(cur,w)
        for dy in (-1,0,1):
            for dx in (-1,0,1):
                yy,xx=y+dy,x+dx
                if (dy or dx) and 0<=yy<h and 0<=xx<w and allowed[yy,xx]:
                    j=yy*w+xx
                    if previous[j]<0: previous[j]=cur;queue.append(j)
    assert previous[last]>=0
    path=[];j=last
    while True:
        y,x=divmod(j,w);path.append([x,y])
        if j==first:break
        j=previous[j]
    return path[::-1]


def merge_witness(z, tree, activation, a, b):
    na=int(activation[a[1],a[0]]);nb=int(activation[b[1],b[0]])
    ancestor=join(tree,na,nb)
    level=float(min(tree['nodes'][ancestor]['level'],z[a[1],a[0]],z[b[1],b[0]]))
    return dict(ancestor_node=ancestor,level=level,path_xy=path_above(z,a,b,level))


def nuclei(z, fields):
    nodes=[]
    for sigma,f in fields.items():
        labels,n=ndi.label((f==ndi.maximum_filter(f,size=3)),structure=np.ones((3,3)))
        for k,sl in enumerate(ndi.find_objects(labels),1):
            if sl is None:continue
            yy,xx=np.where(labels[sl]==k);yy+=sl[0].start;xx+=sl[1].start
            y,x=int(yy[0]),int(xx[0]);r=int(np.ceil(sigma))
            ys=slice(max(0,y-r),min(z.shape[0],y+r+1));xs=slice(max(0,x-r),min(z.shape[1],x+r+1))
            sub=z[ys,xs];iy,ix=np.unravel_index(np.argmax(sub),sub.shape);rawxy=[int(ix+xs.start),int(iy+ys.start)]
            nodes.append(dict(id=f'N{sigma:g}_{k}',type='image_nucleus',xy=[x,y],scale_px=sigma,
                              attributes=dict(analysis_peak=float(f[y,x]),I0_at_proposal=float(z[y,x]),
                                              raw_neighbour_peak_xy=rawxy,raw_neighbour_peak=float(z[rawxy[1],rawxy[0]]),
                                              peak_offset_px=float(np.linalg.norm(np.array(rawxy)-[x,y]))),
                              uncertainty=['not_physical_scatterer']+(['boundary_censored'] if min(x,y,z.shape[1]-1-x,z.shape[0]-1-y)<3*sigma else [])))
    return nodes


def segment_hypotheses(z,f,ns,p):
    segments=[]; supports={}; ledger=[]
    for q in p['segment_quantiles']:
        level=float(np.percentile(f,q)); lab,n=ndi.label(f>=level,structure=np.ones((3,3)))
        for k,sl in enumerate(ndi.find_objects(lab),1):
            if sl is None:continue
            yy,xx=np.where(lab[sl]==k);yy+=sl[0].start;xx+=sl[1].start
            sid=f'S{q}_{k}'; count=len(xx)
            if count<p['support_min_pixels']:
                ledger.append(dict(component=sid,status='below_analysis_support_size',pixels=count));continue
            xy=np.c_[xx,yy].astype(float); center=xy.mean(0);cov=np.cov(xy.T);ev,vec=np.linalg.eigh(cov)
            axis=vec[:,-1];axis*=1 if axis[0]>=0 else -1
            along=(xy-center)@axis;extent=float(np.ptp(along));aspect=float(np.sqrt(ev[-1]/max(ev[0],1e-6)))
            if extent<p['line_min_extent_px'] or aspect<p['line_min_aspect']:
                ledger.append(dict(component=sid,status='compact_or_nonelongated_group_unresolved',pixels=count));continue
            endpoints=[(center+axis*np.percentile(along,a)).tolist() for a in [5,95]]
            centerline=section(*endpoints);normal=np.array([-axis[1],axis[0]]);offset=max(3.,2*np.sqrt(max(ev[0],0)))
            left=centerline+offset*normal;right=centerline-offset*normal
            left[:,0]=np.clip(left[:,0],0,z.shape[1]-1);left[:,1]=np.clip(left[:,1],0,z.shape[0]-1)
            right[:,0]=np.clip(right[:,0],0,z.shape[1]-1);right[:,1]=np.clip(right[:,1],0,z.shape[0]-1)
            fullsupport=np.zeros(z.shape,bool);fullsupport[yy,xx]=True
            raw_labels,nraw=ndi.label(fullsupport&(z>=level),structure=np.ones((3,3)))
            peak=int(np.argmax(f[yy,xx]));anchor=[int(xx[peak]),int(yy[peak])]
            memberships=[n['id'] for n in ns if fullsupport[n['xy'][1],n['xy'][0]]]
            statuses=['uncertain_segment','support_is_level_set_not_target_mask']
            if nraw>1:statuses.append('raw_level_fragmented')
            if np.any((xx==0)|(yy==0)|(xx==z.shape[1]-1)|(yy==z.shape[0]-1)):statuses.append('boundary_censored')
            segments.append(dict(id=sid,type='candidate_ridge_or_band',proposed_from='I_sigma',nuclei=memberships,
                                 geometry=dict(center_xy=center.tolist(),axis_xy=axis.tolist(),polyline_xy=centerline.tolist(),
                                               support_xy=xy.astype(int).tolist()),
                                 attributes=dict(quantile=q,analysis_level=level,extent_px=extent,aspect=aspect,anchor_xy=anchor),
                                 raw_check=dict(type='paired_field_trace',center_xy=centerline.tolist(),I0=sample(z,centerline).tolist(),
                                                I_sigma=sample(f,centerline).tolist(),flank_left_xy=left.tolist(),flank_right_xy=right.tolist(),
                                                I0_left=sample(z,left).tolist(),I0_right=sample(z,right).tolist(),
                                                raw_components_at_same_level=int(nraw)),uncertainty=statuses))
            supports[sid]=fullsupport
    return segments,supports,ledger


def dark_region(z,f,a,b,rid):
    xy=section(a,b);r0=sample(z,xy);r2=sample(f,xy);n=len(xy)
    interval=range(max(1,int(.2*n)),min(n-1,max(2,int(.8*n))))
    valley=min(interval,key=lambda i:r0[i]);x,y=np.rint(xy[valley]).astype(int)
    endpoint_low=min(float(r0[0]),float(r0[-1]));v=float(z[y,x])
    # No universal dark cutoff: levels are conditional on this cross-section.
    level=v+.5*max(0,endpoint_low-v)
    records=[]
    for fraction in [.2,.5]:
        level=v+fraction*max(0,endpoint_low-v)
        for name,field in [('I0',z),('I_sigma',f)]:
            lab,_=ndi.label(field<=level,structure=np.ones((3,3)));label=int(lab[y,x])
            if not label:records.append(dict(field=name,level=level,fraction=fraction,pixels_xy=[],boundary_sides=[]));continue
            yy,xx=np.where(lab==label);sides=[]
            for side,present in [('left',np.any(xx==0)),('right',np.any(xx==z.shape[1]-1)),('top',np.any(yy==0)),('bottom',np.any(yy==z.shape[0]-1))]:
                if present:sides.append(side)
            records.append(dict(field=name,level=level,fraction=fraction,pixels_xy=np.c_[xx,yy].tolist(),boundary_sides=sides))
    return dict(id='D_'+rid,type='cross_section_valley_and_open_region',witness_relation=rid,
                seed_xy=[int(x),int(y)],cross_section_xy=xy.tolist(),I0_profile=r0.tolist(),I_sigma_profile=r2.tolist(),
                regions=records,attributes=dict(valley_gray=v,endpoint_low=endpoint_low),
                uncertainty=['case_local_level','not_vehicle_interior_mask','openness_is_to_aperture_boundary'])


def build_object(z, object_id='anonymous'):
    z=np.asarray(z,dtype=float);assert z.ndim==2 and np.isfinite(z).all()
    p=PARAMETERS;fields={s:ndi.gaussian_filter(z,s,mode='reflect') for s in p['scales']};f=fields[p['analysis_sigma']]
    ns=nuclei(z,fields);t0,p0=merge_tree(z);t2,p2=merge_tree(f)
    segs,supports,ledger=segment_hypotheses(z,f,ns,p)
    obj=dict(id=object_id,kind='MorphologyObject',full_field={'file':'field.npz','I0':'I0','I_sigma':'I2','semantics':'same_source_display; I0 retained'},
             nuclei=ns,segments=segs,relations=[],dark_open_regions=[],uncertainty=['unresolved_grouping','not_a_physical_object_assignment'],
             proposal_ledger=ledger,merge_topology=dict(I0=t0,I_sigma=t2),parameters=p)
    arrays=dict(I0=z,I1=fields[1.],I2=f,I4=fields[4.],activation_I0=p0,activation_I2=p2)
    if not segs:obj['uncertainty'].append('MORPHOLOGY_NOT_RECOVERED_AT_SEGMENT_LAYER')
    if len(ns)>p['max_nuclei'] or len(segs)>p['max_segments']:
        obj['uncertainty'].append('STOP_GRAPH_BUDGET');clean_tree(t0);clean_tree(t2);return obj,arrays
    pairs=set()
    for i,a in enumerate(segs):
        candidates=[]
        for j,b in enumerate(segs):
            if i==j or a['attributes']['quantile']!=b['attributes']['quantile']:continue
            dist=np.linalg.norm(np.array(a['geometry']['center_xy'])-b['geometry']['center_xy'])
            if dist<=p['pair_radius_px']:candidates.append((float(dist),j))
        for _,j in sorted(candidates)[:p['neighbours_per_segment']]:pairs.add(tuple(sorted([i,j])))
    if len(pairs)>p['max_pair_relations']:
        obj['uncertainty'].append('STOP_RELATION_BUDGET');clean_tree(t0);clean_tree(t2);return obj,arrays
    for i,j in sorted(pairs):
        a,b=segs[i],segs[j];ca=np.array(a['geometry']['center_xy']);cb=np.array(b['geometry']['center_xy']);delta=cb-ca
        direction=delta/max(np.linalg.norm(delta),1e-8);ax=np.array(a['geometry']['axis_xy']);bx=np.array(b['geometry']['axis_xy'])
        angle=axial_angle(ax,bx);da=axial_angle(ax,direction);db=axial_angle(bx,direction)
        types=['neighbouring_structures'];rid=f'R{i}_{j}'
        if angle<=p['parallel_tolerance_deg']:
            types.append('roughly_parallel')
            if max(da,db)<=p['serial_tolerance_deg']:types+=['along_axis','serial']
            if min(da,db)>=p['opposite_min_deg']:types.append('opposite')
        aa=a['attributes']['anchor_xy'];bb=b['attributes']['anchor_xy']
        m0=merge_witness(z,t0,p0,aa,bb);m2=merge_witness(f,t2,p2,aa,bb)
        types.append('joins_at_lower_level')
        if any(s['attributes']['analysis_level']>m0['level'] for s in [a,b]):types.append('weakly_connected_at_lower_level')
        if 'opposite' in types or 'serial' in types:
            dr=dark_region(z,f,aa,bb,rid);obj['dark_open_regions'].append(dr)
            if dr['attributes']['valley_gray']<dr['attributes']['endpoint_low']:
                types+=['separated','separated_by_dark_gap']
                if dr['regions'][0]['boundary_sides']:types.append('open_configuration')
        smoothpath=np.array(m2['path_xy']);raw_on_smooth=float(z[smoothpath[:,1],smoothpath[:,0]].min())
        uncertainty=['hypothesis_not_vehicle_membership','ambiguous_bridge']
        if raw_on_smooth<m2['level']:uncertainty.append('smoothed_path_not_connected_in_I0_at_same_level')
        obj['relations'].append(dict(id=rid,type=types,source=a['id'],target=b['id'],semantics_status='computational_relation_hypothesis',
             witness=dict(I0_merge=m0,I_sigma_merge=m2),attributes=dict(distance_px=float(np.linalg.norm(delta)),relative_axis_deg=angle,
             I0_min_on_smoothed_path=raw_on_smooth,saddle_shift=m2['level']-m0['level']),uncertainty=uncertainty))
    # Exact nesting, without declaring one representation level the correct one.
    for i,a in enumerate(segs):
        for j,b in enumerate(segs):
            if a['attributes']['quantile']<=b['attributes']['quantile']:continue
            if np.all(supports[b['id']][supports[a['id']]]):
                obj['relations'].append(dict(id=f'P{i}_{j}',type=['nested_analysis_support'],source=a['id'],target=b['id'],
                    semantics_status='exact_same_field_containment',witness={'field':'I_sigma','child_support':a['id'],'parent_support':b['id']},
                    attributes={},uncertainty=['not_identity','unresolved_grouping']))
    clean_tree(t0);clean_tree(t2)
    return obj,arrays
