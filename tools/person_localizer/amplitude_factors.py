"""Shared image likelihood with a positive response-strength prior.

The half-normal prior integrates response amplitude instead of fitting an
arbitrarily large amplitude from a partly measured tail. Background is projected
out once for the shared scene. A spatial correlation temperature is explicit.
"""
from dataclasses import dataclass,asdict
import numpy as np
from scipy.special import ndtr,log_ndtr
from numpy.polynomial.legendre import leggauss
from .temporal_factors import _nnls2


@dataclass(frozen=True)
class ResponsePrior:
    noise_variance: float
    amplitude_scales: tuple
    spatial_correlation_area: float

    def to_dict(self):return asdict(self)


def positive_quadrant_probability(h,k,rho):
    """Bivariate normal CDF using the angular Plackett integral (64 nodes)."""
    h,k,rho=np.broadcast_arrays(h,k,rho)
    angle=np.arcsin(np.clip(rho,-1+1e-12,1-1e-12))
    nodes,weights=leggauss(64);integral=np.zeros_like(angle)
    for x,w in zip(nodes,weights):
        theta=.5*(x+1)*angle;s=np.sin(theta);c2=np.cos(theta)**2
        integral+=w*np.exp(-(h*h-2*h*k*s+k*k)/(2*c2))
    result=ndtr(h)*ndtr(k)+angle*integral/(4*np.pi)
    return np.clip(result,1e-300,1.)


def statistics(y,Z,Q1,Q2,valid):
    z=Z[valid];v=y[valid];q1=Q1[valid];q2=Q2[valid]
    inv=np.linalg.pinv(z.T@z);b0=inv@z.T@v;u1=inv@z.T@q1;u2=inv@z.T@q2
    r0=v-z@b0
    p=np.maximum(np.sum(q1*q1,axis=0)-np.sum((z.T@q1)*u1,axis=0),0.)
    s=np.maximum(np.sum(q2*q2,axis=0)-np.sum((z.T@q2)*u2,axis=0),0.)
    c=q1.T@q2-(z.T@q1).T@u2
    r=q1.T@r0;t=q2.T@r0
    return dict(p=p,s=s,c=c,r=r,t=t,b0=b0,u1=u1,u2=u2,n=int(valid.sum()),sse=float(r0@r0))


def joint_response_factors(y,Z,Q1,Q2,valid,prior):
    """Log Bayes factors relative to background on a single shared pixel set.

    The likelihood uses the declared effective noise variance. These factors
    define a working image model, not calibrated identity probabilities.
    """
    n1,n2=Q1.shape[1],Q2.shape[1]
    if valid.sum()<4:
        return dict(first=np.zeros(n1),second=np.zeros(n2),both=np.zeros((n1,n2)),observed=False)
    st=statistics(y,Z,Q1,Q2,valid)
    variance=prior.noise_variance*prior.spatial_correlation_area
    tau1,tau2=prior.amplitude_scales
    p=st['p']*tau1*tau1/variance;s=st['s']*tau2*tau2/variance
    c=st['c']*tau1*tau2/variance;r=st['r']*tau1/variance;t=st['t']*tau2/variance
    k1=1+p;k2=1+s
    first=.5*r*r/k1-.5*np.log(k1)+np.log(2.)+log_ndtr(r/np.sqrt(k1))
    second=.5*t*t/k2-.5*np.log(k2)+np.log(2.)+log_ndtr(t/np.sqrt(k2))
    det=k1[:,None]*k2[None,:]-c*c
    mu1=(r[:,None]*k2[None,:]-t[None,:]*c)/det
    mu2=(t[None,:]*k1[:,None]-r[:,None]*c)/det
    h=mu1/np.sqrt(k2[None,:]/det);k=mu2/np.sqrt(k1[:,None]/det)
    rho=-c/np.sqrt(k1[:,None]*k2[None,:])
    both=.5*(r[:,None]*mu1+t[None,:]*mu2)-.5*np.log(det)+np.log(4.)+np.log(positive_quadrant_probability(h,k,rho))
    return dict(first=first,second=second,both=both,observed=True,
                posterior_amplitude_correlation=rho)


def response_state_energy(factors):
    n1,n2=factors['both'].shape;e=np.zeros((2*n1,2*n2))
    e[0::2,0::2]=-factors['both']
    e[0::2,1::2]=-factors['first'][:,None]
    e[1::2,0::2]=-factors['second'][None,:]
    return e


def ridge_readout(y,Z,Q,train,test,prior,active=(True,True)):
    """Posterior-mode positive amplitudes, fit using training pixels only."""
    st=statistics(y,Z,Q[:,:1],Q[:,1:2],train)
    variance=prior.noise_variance*prior.spatial_correlation_area
    tau1,tau2=prior.amplitude_scales
    p=st['p'][0]*tau1*tau1/variance+1;s=st['s'][0]*tau2*tau2/variance+1
    c=st['c'][0,0]*tau1*tau2/variance;r=st['r'][0]*tau1/variance;t=st['t'][0]*tau2/variance
    mode='both' if all(active) else 'first' if active[0] else 'second' if active[1] else 'none'
    a,b=_nnls2(p,s,c,r,t,mode);amps=np.array([float(a)*tau1,float(b)*tau2])
    background=st['b0']-st['u1'][:,0]*amps[0]-st['u2'][:,0]*amps[1]
    residual=y[test]-Z[test]@background-Q[test]@amps
    return float(np.mean(residual*residual)),amps,background


def transition_potential(offsets,elapsed_sar_frames,policy):
    """Gaussian displacement factor with equal self-potential at every position.

    Row normalization on a truncated grid rewards a boundary stay in path MAP.
    These are pairwise factor potentials; inference normalizes the whole chain.
    """
    variance=policy.motion_sigma_per_sar_frame**2*max(1.,elapsed_sar_frames)
    d2=np.sum((offsets[:,None,:]-offsets[None,:,:])**2,axis=2)
    position=np.exp(-.5*d2/variance)
    modes=np.array([[1-policy.supported_to_weak,policy.supported_to_weak],
                    [policy.weak_to_supported,1-policy.weak_to_supported]])
    modes=np.linalg.matrix_power(modes,max(1,int(round(elapsed_sar_frames))))
    return np.kron(position,modes)
