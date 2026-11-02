"""Scene-independent shared-response association and explicit missing positions.

Optical scale/angle are soft image-domain priors. A measured response and a
position inferred without a current response always retain different states.
This module has no filesystem, scene-name, query-ID or historical-result input.
"""
from dataclasses import dataclass, asdict
import numpy as np
from scipy.ndimage import median_filter

@dataclass(frozen=True)
class RecoveryPolicy:
    peak_budget: int = 12
    weak_offset_work_px: float = 10.
    weak_sigma_work_px: float = 12.
    bearing_sigma_deg: float = 4.
    log_depth_sigma: float = .25
    response_cap: float = 8.
    motion_sigma_work_px: float = 3.5
    switch_cost: float = .25
    exclusion_work_px: float = 6.
    maximum_joint_states: int = 2000000
    gap_radius_work_px: float = 45.
    gap_sigma_work_px: float = 25.
    gap_min_response: float = 1.
    gap_motion_sigma_work_px: float = 6.
    gap_reconfiguration_cost: float = 3.

    def __post_init__(self):
        if self.peak_budget < 1 or self.maximum_joint_states < 1:
            raise ValueError('Candidate and joint-state budgets must be positive')
        if any(v <= 0 for k,v in asdict(self).items() if k.endswith(('_px','_deg','_sigma'))):
            raise ValueError('Recovery scales must be positive')

    def to_dict(self): return asdict(self)

def interpolate(frames, values, requested):
    frames=np.asarray(frames); values=np.asarray(values); requested=np.asarray(requested)
    if not len(frames) or len(frames)!=len(values) or np.any(np.diff(frames)<=0):
        raise ValueError('Interpolation requires unique increasing frame indices')
    if not np.isfinite(values).all(): raise ValueError('Nonfinite optical/support input')
    result=np.interp(requested,frames,values)
    if len(frames)==1:return result
    for left in [True,False]:
        ids=slice(0,min(8,len(frames))) if left else slice(max(0,len(frames)-8),None)
        slope=float(np.clip(np.polyfit(frames[ids]-frames[ids][0],values[ids],1)[0],-2.,2.))
        mask=requested<frames[0] if left else requested>frames[-1];k=0 if left else -1
        result[mask]=values[k]+slope*(requested[mask]-frames[k])
    return result

def fit_proxy(optical, supports, origin):
    products=[]; offsets=[]
    for query,a in supports.groupby('query',sort=False):
        o=optical[optical['query'].eq(query)].sort_values('sar_frame').drop_duplicates('sar_frame')
        h=interpolate(o.sar_frame,o.bbox_y2-o.bbox_y1,a.sar_frame)
        theta=interpolate(o.sar_frame,o.theta,a.sar_frame)
        products.extend((origin[1]-a.y.to_numpy())*h)
        offsets.extend(np.degrees(np.arctan2(a.x-origin[0],origin[1]-a.y))-theta)
    products=np.asarray(products);offsets=np.asarray(offsets)
    if len(products)<3 or not np.isfinite(products).all() or np.any(products<=0):
        raise ValueError('Positive forward-depth support is needed to fit a scene proxy')
    return dict(product=float(np.median(products)),angle_offset_deg=float(np.median(offsets)),
                product_std=float(products.std()),support_frames=len(products),metric_calibration=False)

def make_prior(optical, frames, origin, scale, proxy, clear=False):
    o=optical.sort_values('sar_frame').drop_duplicates('sar_frame')
    theta=interpolate(o.sar_frame,o.theta,frames)+proxy['angle_offset_deg']
    heights=o.bbox_y2-o.bbox_y1;full=float(heights.quantile(.9))
    if not np.isfinite(full) or full<=0:raise ValueError('Missing positive optical height')
    if clear:
        height=interpolate(o.sar_frame,median_filter(heights.to_numpy(),size=5,mode='nearest'),frames)
        height=np.maximum(height,.85*full)
    else:height=np.full(len(frames),full)
    depth=proxy['product']/height
    native=np.c_[origin[0]+depth*np.tan(np.deg2rad(theta)),origin[1]-depth]
    return (native+.5)/scale-.5,theta,depth,full

def bridge_prior(frames,prior,supports,scale):
    a=supports.sort_values('sar_frame');index=np.searchsorted(frames,a.sar_frame.to_numpy())
    if not len(a) or np.any(index>=len(frames)) or np.any(np.asarray(frames)[index]!=a.sar_frame):
        raise ValueError('Support frames must be inside the requested sequence')
    residual=(a[['x','y']].to_numpy()+.5)/scale-.5-prior[index]
    return prior+np.column_stack([interpolate(a.sar_frame,residual[:,d],frames) for d in [0,1]])

def weak_offsets(policy):
    d=policy.weak_offset_work_px
    return np.array([(x,y) for x in [-d,0.,d] for y in [-d,0.,d]])

def predicted_fan_crossing(frames,angles,last_optical_frame,half_angle_deg):
    """Bounded-search endpoint only: this is not measured exit evidence."""
    frames=np.asarray(frames);angles=np.asarray(angles)
    crossings=np.flatnonzero((frames>last_optical_frame)&(np.abs(angles)>=half_angle_deg))
    return int(frames[crossings[0]]) if len(crossings) else None

def candidate_states(frames,priors,angles,depths,active,observations,origin,scale,policy):
    offsets=weak_offsets(policy);n=policy.peak_budget+len(offsets);inf=1e8
    nodes=[];energies=[];ids=[];responses=[]
    for t,f in enumerate(frames):
        xy,v,theta=observations[int(f)];native=(xy+.5)*scale-.5;d=origin[1]-native[:,1]
        fn=[];fe=[];fi=[];fr=[]
        for q,prior in enumerate(priors):
            p=prior[t]
            if not active[t,q]:
                fn.append(np.tile(p,(n,1)));fe.append(np.r_[0.,np.full(n-1,inf)]);fi.append(np.full(n,-1));fr.append(np.zeros(n));continue
            e=.5*((theta-angles[q][t])/policy.bearing_sigma_deg)**2
            e+=.5*(np.log(np.maximum(d,1)/depths[q][t])/policy.log_depth_sigma)**2
            e-=np.log1p(np.minimum(v,policy.response_cap))
            chosen=np.argsort(e)[:policy.peak_budget];pad=policy.peak_budget-len(chosen)
            fn.append(np.vstack([xy[chosen],np.tile(p,(pad,1)),p+offsets]))
            fe.append(np.r_[e[chosen],np.full(pad,inf),.5*np.sum(offsets**2,axis=1)/policy.weak_sigma_work_px**2])
            fi.append(np.r_[chosen,np.full(pad+len(offsets),-1)]);fr.append(np.r_[v[chosen],np.zeros(pad+len(offsets))])
        nodes.append(fn);energies.append(fe);ids.append(fi);responses.append(fr)
    return np.array(nodes),np.array(energies),np.array(ids),np.array(responses)

def exact_joint_path(nodes,energies,observation_ids,priors,active,policy=RecoveryPolicy()):
    """Exact separable min-plus Viterbi with same-frame shared-peak exclusion."""
    count,k,n,_=nodes.shape;shape=(n,)*k;inf=1e8
    if n**k>policy.maximum_joint_states:
        raise ValueError(f'{n**k} joint states exceed the declared budget; no query was silently dropped')
    if not np.isfinite(nodes).all():raise ValueError('Nonfinite candidate coordinates')
    def emission(t):
        e=np.zeros(shape,dtype=np.float64)
        for q in range(k):
            s=[1]*k;s[q]=n;e+=energies[t,q].reshape(s)
        for a in range(k):
            for b in range(a+1,k):
                if not(active[t,a] and active[t,b]):continue
                d2=np.sum((nodes[t,a,:,None]-nodes[t,b,None,:])**2,axis=2)
                shared=(observation_ids[t,a,:,None]>=0)&(observation_ids[t,b,None,:]>=0)
                collision=shared&((d2<policy.exclusion_work_px**2)|(observation_ids[t,a,:,None]==observation_ids[t,b,None,:]))
                s=[1]*k;s[a]=s[b]=n;e+=collision.reshape(s)*inf
        return e
    cost=emission(0);parents=[]
    for t in range(1,count):
        step=[]
        for q in range(k):
            if active[t-1,q] and active[t,q]:
                delta=nodes[t,q,None,:,:]-nodes[t-1,q,:,None,:]-(priors[q][t]-priors[q][t-1])
                transition=.5*np.sum(delta**2,axis=2)/policy.motion_sigma_work_px**2
                transition+=policy.switch_cost*((observation_ids[t-1,q,:,None]<0)!=(observation_ids[t,q,None,:]<0))
            else:transition=np.zeros((n,n))
            moved=np.moveaxis(cost,q,-1);matrix=moved[..., :,None]+transition
            arg=matrix.argmin(axis=-2);cost=np.moveaxis(matrix.min(axis=-2),-1,q)
            step.append(np.moveaxis(arg,-1,q).astype(np.uint16))
        cost+=emission(t);parents.append(step)
    if cost.min()>=inf:raise ValueError('No feasible joint assignment; competing evidence was not duplicated')
    path=[tuple(np.unravel_index(cost.argmin(),shape))]
    for step in reversed(parents):
        state=list(path[-1])
        for q in range(k-1,-1,-1):state[q]=int(step[q][tuple(state)])
        path.append(tuple(state))
    return list(reversed(path))

def refine_missing(frames,prior,supports,observations,origin,scale,policy=RecoveryPolicy()):
    """Retain actual supports; recover gaps within a bounded local image region."""
    offsets=weak_offsets(policy);n=policy.peak_budget+len(offsets);inf=1e8
    fixed={int(r.sar_frame):r for r in supports.itertuples()};nodes=[];energies=[];values=[];observed=[]
    work_origin=(origin+.5)/scale-.5
    for t,f in enumerate(frames):
        p=prior[t]
        if int(f) in fixed:
            r=fixed[int(f)];nodes.append(np.tile((np.array([r.x,r.y])+.5)/scale-.5,(n,1)))
            energies.append(np.r_[0.,np.full(n-1,inf)]);values.append(np.r_[r.response,np.zeros(n-1)]);observed.append(np.r_[True,np.zeros(n-1,dtype=bool)]);continue
        xy,v,theta=observations[int(f)];d2=np.sum((xy-p)**2,axis=1);valid=(d2<policy.gap_radius_work_px**2)&(v>=policy.gap_min_response)
        ids=np.flatnonzero(valid);loc=xy[ids];value=v[ids]
        angle=np.degrees(np.arctan2(p[0]-work_origin[0],work_origin[1]-p[1]));depth=work_origin[1]-p[1]
        e=-np.log1p(np.minimum(value,policy.response_cap))+.5*d2[ids]/policy.gap_sigma_work_px**2
        e+=.5*((theta[ids]-angle)/8.)**2+.5*(np.log(np.maximum(work_origin[1]-loc[:,1],1)/depth)/.35)**2
        chosen=np.argsort(e)[:policy.peak_budget];nn=len(chosen);pad=policy.peak_budget-nn
        nodes.append(np.vstack([loc[chosen],np.tile(p,(pad,1)),p+offsets]));energies.append(np.r_[e[chosen],np.full(pad,inf),.5*np.sum(offsets**2,axis=1)/policy.weak_sigma_work_px**2])
        values.append(np.r_[value[chosen],np.zeros(pad+len(offsets))]);observed.append(np.r_[np.ones(nn,dtype=bool),np.zeros(pad+len(offsets),dtype=bool)])
    nodes=np.array(nodes);energies=np.array(energies);values=np.array(values);observed=np.array(observed)
    cost=energies[0].copy();parents=[]
    for t in range(1,len(frames)):
        delta=nodes[t][None,:,:]-nodes[t-1][:,None,:]-(prior[t]-prior[t-1]);d2=np.sum(delta**2,axis=2)
        transition=.5*d2/policy.gap_motion_sigma_work_px**2;both=observed[t-1][:,None]&observed[t][None,:]
        transition[both]=np.minimum(transition[both],policy.gap_reconfiguration_cost);transition[d2>policy.gap_radius_work_px**2]=inf
        transition+=.35*(observed[t-1][:,None]!=observed[t][None,:]);matrix=cost[:,None]+transition
        parents.append(matrix.argmin(0));cost=matrix.min(0)+energies[t]
    if cost.min()>=inf:raise ValueError('No feasible bounded gap path')
    path=[int(cost.argmin())]
    for p in reversed(parents):path.append(int(p[path[-1]]))
    path=np.array(path[::-1]);index=np.arange(len(frames))
    return nodes[index,path],values[index,path],observed[index,path]
