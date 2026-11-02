"""Audited FFT and nonnegative response solvers; no dataset paths."""

import numpy as np

from scipy.optimize import nnls

from scipy.fft import rfft2,irfft2,next_fast_len

class FFTLineCV:
 def __init__(self,xx,yy,values,valid,fold,centers,kernel_radius):
  self.xx=xx;self.yy=yy;self.h,self.w=xx.shape;self.xy=np.c_[xx.ravel(),yy.ravel()].astype(float);self.Z=np.c_[np.ones(len(self.xy)),(self.xy-self.xy.mean(0))/max(self.h,self.w)];self.Y=values;self.valid=valid;self.fold=fold;self.centers=np.asarray(centers,int);self.radius=kernel_radius;self.shape=(next_fast_len(self.h+2*kernel_radius),next_fast_len(self.w+2*kernel_radius));self.iy=self.centers[:,1]-int(yy.min())+kernel_radius;self.ix=self.centers[:,0]-int(xx.min())+kernel_radius;self.groups=[];channels=np.concatenate([self.Z.T,values.T],axis=0).reshape(-1,self.h,self.w)
  for k in [-1,0,1,2,3,4]:
   mask=valid if k==-1 else valid&(fold==k);z=self.Z[mask];y=values[mask];self.groups.append(dict(fft=rfft2(channels*mask.reshape(self.h,self.w),s=self.shape,axes=(-2,-1),workers=2),zz=z.T@z,zy=z.T@y,yy=np.sum(y*y,axis=0),n=int(mask.sum())))
  self.plane=self.evaluate_kernel(np.zeros((2*kernel_radius+1,2*kernel_radius+1)),plane_only=True)[0]

 def correlations(self,kernel):
  kfft=rfft2(kernel[::-1,::-1],s=self.shape,workers=2);sqfft=rfft2((kernel*kernel)[::-1,::-1],s=self.shape,workers=2);result=[]
  for g in self.groups:
   corr=irfft2(g['fft']*kfft[None,:,:],s=self.shape,axes=(-2,-1),workers=2);qq=irfft2(g['fft'][0]*sqfft,s=self.shape,workers=2)[self.iy,self.ix];result.append(dict(zq=corr[:3,self.iy,self.ix].T,qy=corr[3:,self.iy,self.ix].T,qq=qq))
  return result

 def evaluate_kernel(self,kernel,plane_only=False,details=False):
  corr=None if plane_only else self.correlations(kernel);total=self.groups[0];losses=[];saved=[]
  for f in range(5):
   te=self.groups[f+1];tr={key:total[key]-te[key] for key in ['zz','zy','yy','n']};inv=np.linalg.pinv(tr['zz']);n=len(self.centers);nf=self.Y.shape[1]
   if plane_only:a=np.zeros((n,nf));b=np.broadcast_to(inv@tr['zy'],(n,3,nf));zq=np.zeros((n,3));testzq=zq;testqy=np.zeros((n,nf));testqq=np.zeros(n)
   else:
    test=corr[f+1];train={key:corr[0][key]-test[key] for key in ['zq','qy','qq']};zq=train['zq'];rhs=train['qy']-zq@inv@tr['zy'];projected=train['qq']-np.einsum('ni,ij,nj->n',zq,inv,zq);threshold=np.finfo(float).eps*64*np.maximum(1.,np.abs(train['qq']));a=np.divide(rhs,projected[:,None],out=np.zeros_like(rhs),where=projected[:,None]>threshold[:,None]);a=np.maximum(a,0.);b=np.einsum('ij,njf->nif',inv,tr['zy'][None,:,:]-zq[:,:,None]*a[:,None,:]);testzq=test['zq'];testqy=test['qy'];testqq=test['qq']
   loss=(te['yy'][None,:]-2*np.einsum('nif,if->nf',b,te['zy'])-2*a*testqy+np.einsum('nif,ij,njf->nf',b,te['zz'],b)+2*a*np.einsum('nif,ni->nf',b,testzq)+a*a*testqq[:,None])/te['n'];losses.append(loss)
   if details:saved.append(dict(fold=f,test_mse=loss,amplitudes=a,background=b))
  result=np.mean(np.stack(losses),axis=(0,2));return (result,saved) if details or plane_only else result

def basis(xy,centers,blurs,s1,s2):
 r2=np.sum((xy[:,None,:]-centers[None,:,:])**2,axis=2)
 a=np.hypot(s1,blurs);b=np.hypot(s2,blurs)
 return np.exp(-r2/(2*a*a))/(2*np.pi*a*a)-np.exp(-r2/(2*b*b))/(2*np.pi*b*b)

def predict(y,Z,Q,tr,te):
 z=Z[tr];q=Q[tr];v=y[tr]
 if Q.shape[1]:
  pr=q-z@np.linalg.lstsq(z,q,rcond=None)[0]
  a,_=nnls(pr,v-z@np.linalg.lstsq(z,v,rcond=None)[0],maxiter=1000)
 else:a=np.empty(0)
 b=np.linalg.lstsq(z,v-q@a,rcond=None)[0]
 return float(np.mean((y[te]-Z[te]@b-Q[te]@a)**2)),a

def singleton_losses(Z,Q,Y,fold):
 result=np.zeros(Q.shape[1])
 for k in range(5):
  tr=fold!=k;te=~tr;z=Z[tr];q=Q[tr];y=Y[tr];zt=Z[te];qt=Q[te];yt=Y[te]
  inv=np.linalg.pinv(z.T@z);b=inv@z.T@y;u=inv@z.T@q
  p=np.sum(q*q,axis=0)-np.sum((z.T@q)*u,axis=0)
  rhs=q.T@y-(z.T@q).T@b
  a=np.maximum(np.divide(rhs,p[:,None],out=np.zeros_like(rhs),where=p[:,None]>1e-12),0)
  residual=yt-zt@b;rt=qt-zt@u
  values=np.sum(residual**2,axis=0)[None,:]-2*a*(rt.T@residual)+a*a*np.sum(rt*rt,axis=0)[:,None]
  result+=values.mean(1)/len(yt)/5
 return result

def joint_losses(Z,Q1,Q2,Y,fold):
 """Every pair, all four nonnegative active sets, no top-N pruning."""
 c1,c2=Q1.shape[1],Q2.shape[1];groups=[]
 for k in range(5):
  mask=fold==k;z=Z[mask];y=Y[mask];a=Q1[mask];b=Q2[mask]
  groups.append(dict(zz=z.T@z,zy=z.T@y,yy=np.sum(y*y,axis=0),z1=z.T@a,z2=z.T@b,
   y1=a.T@y,y2=b.T@y,d1=np.sum(a*a,axis=0),d2=np.sum(b*b,axis=0),cross=a.T@b,n=int(mask.sum())))
 total={key:sum(g[key] for g in groups) for key in groups[0]}
 scores=np.zeros((c1,c2))
 for fold_id,te in enumerate(groups):
  tr={key:total[key]-te[key] for key in total};inv=np.linalg.pinv(tr['zz']);b0=inv@tr['zy'];u1=inv@tr['z1'];u2=inv@tr['z2']
  p1=tr['d1']-np.sum(tr['z1']*u1,axis=0);p2=tr['d2']-np.sum(tr['z2']*u2,axis=0)
  p12=tr['cross']-tr['z1'].T@u2
  r1=tr['y1']-tr['z1'].T@b0;r2=tr['y2']-tr['z2'].T@b0
  base=te['yy']-2*np.sum(b0*te['zy'],axis=0)+np.sum(b0*(te['zz']@b0),axis=0)
  # The fitted plane also changes with each nonnegative component.
  # Test residual cross terms must include its train-estimated projection.
  t1=te['y1']-te['z1'].T@b0-u1.T@te['zy']+u1.T@te['zz']@b0
  t2=te['y2']-te['z2'].T@b0-u2.T@te['zy']+u2.T@te['zz']@b0
  g1=te['d1']-2*np.sum(te['z1']*u1,axis=0)+np.sum(u1*(te['zz']@u1),axis=0)
  g2=te['d2']-2*np.sum(te['z2']*u2,axis=0)+np.sum(u2*(te['zz']@u2),axis=0)
  g12=te['cross']-te['z1'].T@u2-u1.T@te['z2']+u1.T@te['zz']@u2
  for start in range(0,c1,16):
   end=min(c1,start+16);P=p1[start:end,None,None];S=p2[None,:,None];C=p12[start:end,:,None];R=r1[start:end,None,:];T=r2[None,:,:]
   shape=(end-start,c2,Y.shape[1]);a=np.zeros(shape);b=np.zeros(shape);loss=np.zeros(shape)
   aa=np.maximum(np.divide(R,P,out=np.zeros_like(R),where=P>1e-12),0);aa=np.broadcast_to(aa,shape)
   trial=-2*aa*R+aa*aa*P;keep=trial<loss;loss=np.where(keep,trial,loss);a=np.where(keep,aa,a)
   bb=np.maximum(np.divide(T,S,out=np.zeros_like(T),where=S>1e-12),0);bb=np.broadcast_to(bb,shape)
   trial=-2*bb*T+bb*bb*S;keep=trial<loss;loss=np.where(keep,trial,loss);a=np.where(keep,0,a);b=np.where(keep,bb,b)
   determinant=P*S-C*C;good=determinant>1e-12*np.maximum(P*S,1)
   aa=np.divide(R*S-T*C,determinant,out=np.zeros(shape),where=good);bb=np.divide(T*P-R*C,determinant,out=np.zeros(shape),where=good)
   trial=-2*(aa*R+bb*T)+aa*aa*P+bb*bb*S+2*aa*bb*C
   keep=good&(aa>=0)&(bb>=0)&(trial<loss);a=np.where(keep,aa,a);b=np.where(keep,bb,b)
   value=base[None,None,:]-2*a*t1[start:end,None,:]-2*b*t2[None,:,:]+a*a*g1[start:end,None,None]+b*b*g2[None,:,None]+2*a*b*g12[start:end,:,None]
   scores[start:end]+=value.mean(2)/te['n']/5
  print('joint fold',fold_id,'all pairs',c1*c2,'running minimum',scores.min(),flush=True)
 return scores
