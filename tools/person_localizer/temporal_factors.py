"""Masked joint image energies and exact two-query temporal message passing.

The normalized beliefs belong to the declared working energy model. They are
not calibrated physical identity probabilities. Each scene pixel is scored once.
"""
from dataclasses import dataclass, asdict
import numpy as np


@dataclass(frozen=True)
class TemporalFactorPolicy:
    residual_radius_px: int = 8
    residual_step_px: int = 2
    motion_sigma_per_sar_frame: float = .9
    initial_residual_sigma_px: float = 4.
    supported_to_weak: float = .08
    weak_to_supported: float = .12
    initial_supported_probability: float = .6
    active_component_penalty: float = .25
    optical_scale_floor_deg: float = .5
    optical_support_sigmas: float = 3.
    energy_floor_fraction_of_plane: float = .005
    heldout_spatial_fold: int = 4

    def to_dict(self):
        return asdict(self)


def _nnls2(p, s, c, r, t, mode):
    """Vectorized exact two-column nonnegative least squares active sets."""
    shape=np.broadcast_shapes(np.shape(p),np.shape(s),np.shape(c),np.shape(r),np.shape(t))
    p,s,c,r,t=np.broadcast_arrays(p,s,c,r,t)
    a=np.zeros(shape);b=np.zeros(shape);loss=np.zeros(shape)
    if mode in {'first','both'}:
        aa=np.maximum(np.divide(r,p,out=np.zeros(shape),where=p>1e-12),0.)
        value=p*aa*aa-2*r*aa;better=value<loss
        loss=np.where(better,value,loss);a=np.where(better,aa,a)
    if mode in {'second','both'}:
        bb=np.maximum(np.divide(t,s,out=np.zeros(shape),where=s>1e-12),0.)
        value=s*bb*bb-2*t*bb;better=value<loss
        loss=np.where(better,value,loss);a=np.where(better,0.,a);b=np.where(better,bb,b)
    if mode=='both':
        determinant=p*s-c*c;good=determinant>1e-12*np.maximum(p*s,1.)
        aa=np.divide(r*s-t*c,determinant,out=np.zeros(shape),where=good)
        bb=np.divide(t*p-r*c,determinant,out=np.zeros(shape),where=good)
        value=p*aa*aa+s*bb*bb+2*c*aa*bb-2*r*aa-2*t*bb
        better=good&(aa>=0)&(bb>=0)&(value<loss)
        a=np.where(better,aa,a);b=np.where(better,bb,b)
    return a,b


def joint_cv_costs(y,Z,Q1,Q2,valid,fold,fold_ids):
    """Shared-domain CV costs for background, either query, and their joint model.

    valid is specific to this time. Missing data never becomes a zero-valued
    observation. Every candidate is evaluated on the same measured pixels.
    """
    n1,n2=Q1.shape[1],Q2.shape[1]
    result=dict(plane=0.,first=np.zeros(n1),second=np.zeros(n2),both=np.zeros((n1,n2)))
    groups=[]
    for k in fold_ids:
        m=valid&(fold==k);z=Z[m];v=y[m];q1=Q1[m];q2=Q2[m]
        groups.append(dict(n=int(m.sum()),zz=z.T@z,zy=z.T@v,yy=float(v@v),
            z1=z.T@q1,z2=z.T@q2,y1=q1.T@v,y2=q2.T@v,
            d1=np.sum(q1*q1,axis=0),d2=np.sum(q2*q2,axis=0),cross=q1.T@q2))
    total={key:sum(g[key] for g in groups) for key in groups[0]}
    used=0
    for te in groups:
        tr={key:total[key]-te[key] for key in total}
        if te['n']==0 or tr['n']<4:continue
        inv=np.linalg.pinv(tr['zz']);b0=inv@tr['zy'];u1=inv@tr['z1'];u2=inv@tr['z2']
        p=tr['d1']-np.sum(tr['z1']*u1,axis=0);s=tr['d2']-np.sum(tr['z2']*u2,axis=0)
        c=tr['cross']-tr['z1'].T@u2;r=tr['y1']-tr['z1'].T@b0;t=tr['y2']-tr['z2'].T@b0
        base=te['yy']-2*b0@te['zy']+b0@te['zz']@b0
        v1=te['y1']-te['z1'].T@b0-u1.T@te['zy']+u1.T@te['zz']@b0
        v2=te['y2']-te['z2'].T@b0-u2.T@te['zy']+u2.T@te['zz']@b0
        g1=te['d1']-2*np.sum(te['z1']*u1,axis=0)+np.sum(u1*(te['zz']@u1),axis=0)
        g2=te['d2']-2*np.sum(te['z2']*u2,axis=0)+np.sum(u2*(te['zz']@u2),axis=0)
        g12=te['cross']-te['z1'].T@u2-u1.T@te['z2']+u1.T@te['zz']@u2
        a=np.maximum(np.divide(r,p,out=np.zeros_like(r),where=p>1e-12),0.)
        b=np.maximum(np.divide(t,s,out=np.zeros_like(t),where=s>1e-12),0.)
        result['plane']+=base/te['n']
        result['first']+=(base-2*a*v1+a*a*g1)/te['n']
        result['second']+=(base-2*b*v2+b*b*g2)/te['n']
        aa,bb=_nnls2(p[:,None],s[None,:],c,r[:,None],t[None,:],'both')
        result['both']+=(base-2*aa*v1[:,None]-2*bb*v2[None,:]+aa*aa*g1[:,None]+bb*bb*g2[None,:]+2*aa*bb*g12)/te['n']
        used+=1
    if not used:
        return dict(plane=np.nan,first=np.full(n1,np.nan),second=np.full(n2,np.nan),both=np.full((n1,n2),np.nan),folds=0)
    return {**{k:v/used for k,v in result.items()},'folds':used}


def residual_grid(policy):
    values=np.arange(-policy.residual_radius_px,policy.residual_radius_px+1,policy.residual_step_px,dtype=float)
    x,y=np.meshgrid(values,values)
    return np.c_[x.ravel(),y.ravel()]


def transition_matrix(offsets,elapsed_sar_frames,policy):
    """Position random walk plus persistent supported/weak response state."""
    variance=policy.motion_sigma_per_sar_frame**2*max(1.,elapsed_sar_frames)
    d2=np.sum((offsets[:,None,:]-offsets[None,:,:])**2,axis=2)
    position=np.exp(-.5*d2/variance);position/=position.sum(1,keepdims=True)
    modes=np.array([[1-policy.supported_to_weak,policy.supported_to_weak],
                    [policy.weak_to_supported,1-policy.weak_to_supported]])
    # Policy transition probabilities are per SAR frame, including skipped times.
    modes=np.linalg.matrix_power(modes,max(1,int(round(elapsed_sar_frames))))
    return np.kron(position,modes)


def initial_distribution(offsets,policy):
    position=np.exp(-.5*np.sum(offsets*offsets,axis=1)/policy.initial_residual_sigma_px**2)
    position/=position.sum()
    return np.kron(position,[policy.initial_supported_probability,1-policy.initial_supported_probability])


def state_energy(costs,scale,policy):
    """Supported=0 uses a fitted nonnegative component; weak=1 uses background."""
    n1,n2=costs['both'].shape;e=np.zeros((2*n1,2*n2))
    if not costs['folds']:return e
    p=policy.active_component_penalty
    e[0::2,0::2]=(costs['both']-costs['plane'])/scale+2*p
    e[0::2,1::2]=(costs['first'][:,None]-costs['plane'])/scale+p
    e[1::2,0::2]=(costs['second'][None,:]-costs['plane'])/scale+p
    return e


def forward_backward(energies,transitions1,transitions2,prior1,prior2):
    """Exact sum-product on a coupled two-query chain with separable transitions."""
    energies=np.asarray(energies,float)
    minima=energies.min(axis=(1,2),keepdims=True)
    if not np.isfinite(minima).all():raise ValueError('A frame has no finite state')
    emissions=np.where(np.isfinite(energies),np.exp(-np.minimum(energies-minima,700)),0.)
    filtered=[];normalizers=[];a=prior1[:,None]*prior2[None,:]
    for t,e in enumerate(emissions):
        if t:a=transitions1[t-1].T@a@transitions2[t-1]
        a=a*e;z=a.sum()
        if not np.isfinite(z) or z<=0:raise ValueError('No finite supported state path')
        a/=z;filtered.append(a.copy());normalizers.append(z)
    smoothed=np.empty_like(energies);b=np.ones_like(a)
    for t in range(len(energies)-1,-1,-1):
        post=filtered[t]*b;smoothed[t]=post/post.sum()
        if t:
            b=transitions1[t-1]@(emissions[t]*b)@transitions2[t-1].T
            b/=max(float(b.max()),1e-300)
    return np.stack(filtered),smoothed


def viterbi(energies,transitions1,transitions2,prior1,prior2):
    """Exact joint MAP path; retains both back pointers for each coupled state."""
    def negative_log(p):
        result=np.full_like(p,np.inf,dtype=float)
        np.log(p,out=result,where=p>0)
        result[p>0]*=-1
        return result
    score=energies[0]+negative_log(prior1[:,None]*prior2[None,:]);back=[]
    if not np.isfinite(score).any():raise ValueError('No finite initial state')
    for t in range(1,len(energies)):
        c1=negative_log(transitions1[t-1]);c2=negative_log(transitions2[t-1])
        first=score[:,None,:]+c1[:,:,None]
        best_i=first.argmin(0);temp=first.min(0)
        second=temp[:,:,None]+c2[None,:,:]
        best_j=second.argmin(1)
        pred_i=np.take_along_axis(best_i,best_j,axis=1)
        back.append((pred_i,best_j));score=energies[t]+second.min(1)
        if not np.isfinite(score).any():raise ValueError('No finite state path')
        score-=score.min()
    pair=np.unravel_index(np.argmin(score),score.shape);path=[pair]
    for a,b in reversed(back):pair=(int(a[pair]),int(b[pair]));path.append(pair)
    return np.array(path[::-1],int)
