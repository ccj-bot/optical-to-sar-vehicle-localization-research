"""Portable scene execution with frozen parameters and explicit evidence boundaries."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib,json
import cv2,numpy as np,pandas as pd
from scipy.spatial import cKDTree
from .numerics import FFTLineCV,predict,basis,joint_losses,singleton_losses
from .eligibility import assess_inputs
from .vehicle_gate import attach_vehicle_evidence

def now():return datetime.now(ZoneInfo('Asia/Shanghai')).isoformat()
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def dump(path,value):Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf8')

class Scene:
 def __init__(self,spec,config,out):
  self.spec=spec;self.cfg=config;self.out=Path(out);self.out.mkdir(parents=True,exist_ok=False)
  if config.get('initialization_geometry_scope','whole_track') not in {'whole_track','local_A'}:
   raise ValueError('initialization_geometry_scope must be whole_track or local_A')
  self.opt=pd.read_csv(spec['optical_csv']);self.queries=spec['queries']
  self.native_w=spec['native_width'];self.native_h=spec['native_height']
  self.w=config['work_width'];self.scale=self.native_w/self.w;self.h=round(self.native_h/self.scale)
  g=config['geometry_modes'][f'{self.native_w}x{self.native_h}']
  self.origin=(np.array([g['center_x_px'],g['center_y_px']])+.5)/self.scale-.5
  self.radius=g['radius_px']/self.scale
  self.yy,self.xx=np.mgrid[:self.h,:self.w];self.pts=np.c_[self.xx.ravel(),self.yy.ravel()]
  r=np.hypot(self.xx-self.origin[0],self.origin[1]-self.yy)
  self.theta=np.degrees(np.arctan2(self.xx-self.origin[0],self.origin[1]-self.yy))
  self.domain=(r>config['minimum_radius_work_px'])&(r<self.radius)&(abs(self.theta)<config['fan_half_angle_deg'])
  pad=int(np.ceil(4*config['large_sigma']))
  self.context=cv2.erode(self.domain.astype('uint8'),np.ones((2*pad+1,2*pad+1),np.uint8)).astype(bool)&(abs(self.theta)<=config['central_half_angle_deg'])
  self.motion_domain=(r>config['motion']['feature_radius_min'])&(r<self.radius)&(abs(self.theta)<config['motion']['half_angle_deg'])
  self.images={};self.selections={};self.models={};self.inputs=[Path(spec['optical_csv']),Path(spec['sar_video'])]
  self.results={};self.native_predictions=[]
  self.search_opt=self.opt;self.input_filter_applied=False

 def filter_inputs(self):
  if self.input_filter_applied:return
  self.opt=attach_vehicle_evidence(self.opt,self.spec,self.cfg,self.out)
  if self.spec.get('vehicle_evidence_csv'):self.inputs.append(Path(self.spec['vehicle_evidence_csv']))
  frames,queries,mask=assess_inputs(self.opt,self.spec,self.cfg)
  frames.to_csv(self.out/'OPTICAL_FRAME_ELIGIBILITY.csv',index=False)
  queries.to_csv(self.out/'QUERY_ELIGIBILITY.csv',index=False)
  self.search_opt=self.opt.iloc[np.flatnonzero(mask)].copy()
  self.eligibility=queries.astype(object).where(pd.notnull(queries),None).set_index('query').to_dict('index')
  for q in self.queries:
   audit=self.eligibility[q]
   if not audit['input_eligible']:
    self.results[q]=dict(query=q,status=audit['status'],input_eligibility=audit,identity_verified=False)
  dump(self.out/'INPUT_GATE.json',dict(created=now(),policy=self.cfg.get('input_gate',{}),
   input_queries=len(self.queries),eligible_queries=int(queries.input_eligible.sum()),
   decision_uses='optical metadata and optical boxes only; no SAR pixels, labels or predicted points',
   metric_range_verified=bool(queries.metric_range_verified.any()),
   warning='input eligibility is not target identification or localization acceptance'))
  # Preserve all actors in self.opt for background-motion exclusion; only the
  # geometry/anchor/search observations use the eligible subset.
  self.input_filter_applied=True

 def select(self):
  self.filter_inputs()
  if not any(a['input_eligible'] for a in self.eligibility.values()):return
  cap=cv2.VideoCapture(self.spec['sar_video']);total=int(cap.get(cv2.CAP_PROP_FRAME_COUNT));cap.release();frames=set()
  for query in self.queries:
   if not self.eligibility[query]['input_eligible']:continue
   opt=self.search_opt[self.search_opt['query'].eq(query)].copy()
   available=opt[opt.sar_frame.ge(0)&opt.sar_frame.lt(total)]
   if available.empty:
    self.results[query]=dict(query=query,status='ANCHOR_SOURCE_UNAVAILABLE');continue
   anchor=available.loc[available.theta.abs().idxmin()];core=int(anchor.sar_frame)
   half=self.cfg['half_A_window'];A=list(range(max(0,core-half),min(total,core+half+1)))
   mode='raw' if abs(float(anchor.theta))>self.cfg['central_half_angle_deg'] else 'dog'
   # Preserve the development module's optical input domain.  Outside-domain
   # rows stay in the inventory but cannot hard-constrain a central model.
   model_opt=opt[opt.theta.abs()<=self.cfg['central_half_angle_deg']] if mode=='dog' else opt
   other=model_opt[~model_opt.sar_frame.isin(A)]
   sel=dict(query=query,anchor=core,anchor_optical=int(anchor.optical_frame),A=A,
    even=other[other.optical_frame.mod(2).eq(0)].sar_frame.astype(int).tolist(),
    B=(other if self.cfg.get('all_optical_observation_readout',False) else other[other.optical_frame.mod(2).eq(1)]).sar_frame.astype(int).tolist(),
    mode=mode,input_optical_rows=len(opt),model_optical_rows=len(model_opt))
   self.selections[query]=sel;frames.update(A);frames.update(int(f) for f in opt.sar_frame if 0<=f<total)
  if not frames:return
  self.first=min(frames);self.last=max(frames)
  dump(self.out/'OPTICAL_SELECTION.json',dict(created=now(),selections=self.selections,
   source_frame_range=[self.first,self.last],total_frames=total,selection_by_optical_only=True))

 def decode(self):
  cap=cv2.VideoCapture(self.spec['sar_video']);assert cap.isOpened();cap.set(cv2.CAP_PROP_POS_FRAMES,self.first)
  lut=cv2.applyColorMap(np.arange(256,dtype=np.uint8).reshape(-1,1),cv2.COLORMAP_JET).reshape(256,3);tree=cKDTree(lut.astype(float))
  lookup=np.full(1<<24,-1,dtype=np.int16)
  for f in range(self.first,self.last+1):
   ok,im=cap.read()
   if not ok:raise RuntimeError(f'VIDEO_DECODE_FAILED:{f}')
   if im.shape[:2]!=(self.native_h,self.native_w):raise ValueError('native dimensions mismatch')
   keys=(im[:,:,0].astype(np.uint32)<<16)|(im[:,:,1].astype(np.uint32)<<8)|im[:,:,2].astype(np.uint32)
   missing=lookup[keys]<0
   if missing.any():
    u=np.unique(keys[missing]);colors=np.c_[u>>16,(u>>8)&255,u&255]
    _,ix=tree.query(colors.astype(float),workers=2);lookup[u]=ix.astype(np.int16)
   a=lookup[keys].astype('uint8')
   self.images[f]=cv2.resize(a,(self.w,self.h),interpolation=cv2.INTER_AREA) if self.scale!=1 else a
   if (f-self.first)%100==0:print(self.spec['scene_id'],'decode',f,flush=True)
  cap.release()

 def transport(self,query):
  s=self.selections[query];core=s['anchor'];A=s['A'];opt=self.cfg['motion'];mask=self.motion_domain.copy()
  if opt['exclude_optical_anchor_bands']:
   for q,g in self.opt.groupby('query'):
    row=g.loc[(g.sar_frame-core).abs().idxmin()]
    if abs(row.sar_frame-core)<=self.cfg['half_A_window']:
     mask&=~((self.theta>=row.theta_lo)&(self.theta<=row.theta_hi))
  p=cv2.goodFeaturesToTrack(self.images[core],maxCorners=opt['max_corners'],qualityLevel=opt['quality'],
   minDistance=opt['min_distance'],blockSize=opt['block_size'],mask=mask.astype('uint8')*255)
  if p is None:return {}
  xy=p[:,0];tile=(xy//opt['holdout_tile_px']).astype(int);hold=(tile[:,0]+2*tile[:,1])%5==0
  paths={core:xy.copy()};valid={core:np.ones(len(xy),bool)};cycles={core:np.zeros(len(xy))}
  options=dict(winSize=(opt['window'],opt['window']),maxLevel=opt['levels'],
   criteria=(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,50,.01))
  for seq in [range(core-1,self.first-1,-1),range(core+1,self.last+1)]:
   previous=core
   for f in seq:
    before=paths[previous].astype('float32')[:,None,:]
    after,st,_=cv2.calcOpticalFlowPyrLK(self.images[previous],self.images[f],before,None,**options)
    back,rt,_=cv2.calcOpticalFlowPyrLK(self.images[f],self.images[previous],after,None,**options)
    v=valid[previous]&st[:,0].astype(bool)&rt[:,0].astype(bool)&np.isfinite(after[:,0]).all(1)&np.isfinite(back[:,0]).all(1)
    v&=(after[:,0,0]>=0)&(after[:,0,0]<self.w)&(after[:,0,1]>=0)&(after[:,0,1]<self.h)
    paths[f]=after[:,0];valid[f]=v;cycles[f]=np.linalg.norm(back[:,0]-before[:,0],axis=1);previous=f
  order=sorted(paths);disp=np.stack([paths[f]-xy for f in order]);vv=np.stack([valid[f] for f in order]);cy=np.stack([cycles[f] for f in order]);ia=[order.index(f) for f in A]
  if any((vv[k]&~hold).sum()<3 for k in ia):return {}
  prelim=np.stack([np.median(disp[k,vv[k]&~hold],axis=0) for k in ia]);res=np.linalg.norm(disp[ia]-prelim[:,None,:],axis=2);tol=opt['cycle_tolerance_px']
  stable=vv[ia].all(0)&(np.median(res,axis=0)<=tol)&(np.median(cy[ia],axis=0)<=tol)
  survive={core:stable.copy()};models={}
  for seq in [range(core-1,self.first-1,-1),range(core+1,self.last+1)]:
   previous=core
   for f in seq:survive[f]=survive[previous]&valid[f]&(cycles[f]<=tol);previous=f
  for k,f in enumerate(order):
   fit=survive[f]&~hold;test=survive[f]&hold
   if fit.sum()<3:models[f]=dict(status='INSUFFICIENT_PUBLIC_POINTS',fit_points=int(fit.sum()));continue
   d=np.median(disp[k,fit],axis=0);err=np.linalg.norm(disp[k,test]-d,axis=1)
   models[f]=dict(status='FIT',delta=d.tolist(),fit_points=int(fit.sum()),holdout_points=int(test.sum()),
    holdout_p90=float(np.quantile(err,.9)) if len(err) else None)
  self.models[query]=models
  return models

 def observations(self,query,A,models,mode):
  s=self.selections[query];opt=self.search_opt[self.search_opt['query'].eq(query)]
  if s['mode']=='dog':opt=opt[opt.theta.abs()<=self.cfg['central_half_angle_deg']]
  allowed=opt[opt.sar_frame.isin(set(A)|set(s['even']))];rows=[]
  for row in allowed.itertuples():
   lo,hi=float(row.theta_lo),float(row.theta_hi)
   if mode=='raw' or self.cfg.get('bearing_time_envelope_all_modes',False):
    nearby=allowed[(allowed.optical_frame-row.optical_frame).abs()/self.spec['optical_fps']*1000<=self.cfg['timing_uncertainty_ms']]
    lo,hi=float(nearby.theta_lo.min()),float(nearby.theta_hi.max())
   m=models.get(int(row.sar_frame),{})
   if m.get('status')=='FIT':rows.append(dict(frame=int(row.sar_frame),lo=lo,hi=hi,delta=m['delta']))
  # Apply after constructing the original time envelope, matching the isolated
  # local-A experiment exactly. Later observations still enter sequence factors.
  if self.cfg.get('initialization_geometry_scope','whole_track')=='local_A':
   rows=[o for o in rows if o['frame'] in set(A)]
  return rows

 def pool(self,observations):
  p=self.pts[self.domain.ravel()];keep=np.ones(len(p),bool)
  for o in observations:
   dx=p[:,0]+o['delta'][0]-self.origin[0];dy=p[:,1]+o['delta'][1]-self.origin[1]
   lo,hi=np.deg2rad([o['lo'],o['hi']])
   keep&=(dx*np.cos(lo)+dy*np.sin(lo)>=0)&(dx*np.cos(hi)+dy*np.sin(hi)<=0)
  return p[keep]

 def packet(self,A,models,mode,pools):
  s1,s2=self.cfg['small_sigma'],self.cfg['large_sigma'];blur=s1*np.array(self.cfg['blur_multipliers'])
  radius=int(np.ceil(8*np.hypot(s2 if mode=='dog' else s1,max(blur))))
  pts=np.concatenate(pools);l=max(0,int(pts[:,0].min())-radius);r=min(self.w,int(pts[:,0].max())+radius+1)
  t=max(0,int(pts[:,1].min())-radius);b=min(self.h,int(pts[:,1].max())+radius+1);yy,xx=np.mgrid[t:b,l:r]
  source=self.context if mode=='dog' else self.domain
  values=[];masks=[]
  for f in A:
   m=models.get(f,{})
   if f not in self.images or m.get('status')!='FIT':return None
   a=self.images[f].astype('float32')
   field=cv2.GaussianBlur(a,(0,0),s1)-cv2.GaussianBlur(a,(0,0),s2) if mode=='dog' else a
   d=m['delta'];mx=np.float32(xx+d[0]);my=np.float32(yy+d[1])
   values.append(cv2.remap(field,mx,my,cv2.INTER_LINEAR).ravel());masks.append(cv2.remap(source.astype('uint8'),mx,my,cv2.INTER_NEAREST).ravel().astype(bool))
  valid=np.all(masks,axis=0);kept=[]
  for p in pools:
   idx=(p[:,1]-t)*(r-l)+p[:,0]-l;kept.append(p[valid[idx]])
  block=int(np.ceil(4*s2));fold=(xx.ravel()//block+2*(yy.ravel()//block))%5;xy=np.c_[xx.ravel(),yy.ravel()].astype(float);Z=np.c_[np.ones(len(xy)),(xy-xy.mean(0))/max(xx.shape)]
  return dict(xx=xx,yy=yy,xy=xy,Z=Z,values=np.stack(values,axis=1).astype(float),valid=valid,fold=fold,
   pools=kept,radius=radius,roi=[l,t,r,b],source=source,mode=mode,models=models,A=A)

 def response(self,packet,descriptors):
  xy=packet['xy'];s1,s2=self.cfg['small_sigma'],self.cfg['large_sigma']
  if not descriptors:return np.empty((len(xy),0))
  centers=np.array([[d['x'],d['y']] for d in descriptors]);blur=np.array([d['blur'] for d in descriptors])
  if packet['mode']=='dog':return basis(xy,centers,blur,s1,s2)
  r2=np.sum((xy[:,None,:]-centers[None,:,:])**2,axis=2);sig=np.hypot(s1,blur)
  return np.exp(-r2/(2*sig*sig))/(2*np.pi*sig*sig)

 def search_one(self,query):
  sel=self.selections[query];models=self.models.get(query,{})
  obs=self.observations(query,sel['A'],models,sel['mode']);pts=self.pool(obs)
  folder=self.out/query;folder.mkdir()
  dump(folder/'CONTRACT.json',dict(selection=sel,observations=obs,candidate_geometry=len(pts),
   B_registration_images_accessed=True,B_target_pixels_used_in_objective=False))
  if not len(obs):return dict(query=query,status='MISSING_TRANSPORT_CONSTRAINTS')
  if not len(pts):return dict(query=query,status='MODEL_DOMAIN_INCOMPATIBLE',geometry_candidates=0)
  pack=self.packet(sel['A'],models,sel['mode'],[pts])
  if pack is None:return dict(query=query,status='MISSING_A_SOURCE_OR_TRANSPORT')
  if not len(pack['pools'][0]) and sel['mode']=='dog':
   pack=self.packet(sel['A'],models,'raw',[pts]);sel=sel.copy();sel['mode']='raw_context_fallback'
  if pack is None or not len(pack['pools'][0]):return dict(query=query,status='NO_OBSERVABLE_CENTER',geometry_candidates=len(pts))
  if any(np.sum(pack['valid']&(pack['fold']==k))==0 for k in range(5)):return dict(query=query,status='INSUFFICIENT_SPATIAL_FOLDS')
  engine=FFTLineCV(xx=pack['xx'],yy=pack['yy'],values=pack['values'],valid=pack['valid'],fold=pack['fold'],centers=pack['pools'][0],kernel_radius=pack['radius'])
  radius=pack['radius'];ky,kx=np.mgrid[-radius:radius+1,-radius:radius+1];losses=[];best=None
  for blur in self.cfg['small_sigma']*np.array(self.cfg['blur_multipliers']):
   a=np.hypot(self.cfg['small_sigma'],blur);kernel=np.exp(-(kx*kx+ky*ky)/(2*a*a))/(2*np.pi*a*a)
   if pack['mode']=='dog':
    b=np.hypot(self.cfg['large_sigma'],blur);kernel-=np.exp(-(kx*kx+ky*ky)/(2*b*b))/(2*np.pi*b*b)
   values=engine.evaluate_kernel(kernel);losses.append(values);j=int(np.argmin(values));p=pack['pools'][0][j];row=dict(x=float(p[0]),y=float(p[1]),blur=float(blur),A_mse=float(values[j]))
   if best is None or row['A_mse']<best['A_mse']:best=row
  Q=self.response(pack,[best]);direct=float(np.mean([predict(pack['values'][:,i],pack['Z'],Q,pack['valid']&(pack['fold']!=k),pack['valid']&(pack['fold']==k))[0] for k in range(5) for i in range(len(sel['A']))]))
  assert abs(direct-best['A_mse'])<1e-7,(direct,best)
  np.savez_compressed(folder/'A_PROFILES.npz',centers=pack['pools'][0],losses=np.stack(losses))
  dump(folder/'SELECTED.json',dict(created=now(),selected=best,roi=pack['roi'],A=sel['A'],B=sel['B'],mode=pack['mode'],direct_error=abs(direct-best['A_mse'])))
  dump(folder/'A_SELECTION_SEAL.json',dict(created=now(),files={str(folder/f):sha(folder/f) for f in ['SELECTED.json','A_PROFILES.npz','CONTRACT.json']}))
  evaluation=self.evaluate(query,pack,[best],sel['B'],folder)
  return dict(query=query,anchor=sel['anchor'],mode=pack['mode'],selected=best,geometry_candidates=len(pts),
   observed_candidates=len(pack['pools'][0]),A_direct_error=abs(direct-best['A_mse']),**evaluation)

 def evaluate(self,query,pack,descriptors,B,folder,prefix='',component_index=0):
  Q=self.response(pack,descriptors);valid=pack['valid'];Y=pack['values'];Z=pack['Z'];A=pack['A'];fold=pack['fold']
  amp=np.mean([predict(Y[:,i],Z,Q,valid,valid)[1] for i in range(len(A))],axis=0)
  rows=[];preds=[];s1,s2=self.cfg['small_sigma'],self.cfg['large_sigma']
  for f in B:
   m=pack['models'].get(f,{})
   if f not in self.images or m.get('status')!='FIT':
    preds.append(dict(scene_id=self.spec['scene_id'],query=query,frame=f,status='MISSING_SOURCE_OR_TRANSPORT'));continue
   a=self.images[f].astype('float32');field=cv2.GaussianBlur(a,(0,0),s1)-cv2.GaussianBlur(a,(0,0),s2) if pack['mode']=='dog' else a
   d=np.array(m['delta']);mx=np.float32(pack['xx']+d[0]);my=np.float32(pack['yy']+d[1]);y=cv2.remap(field,mx,my,cv2.INTER_LINEAR).ravel().astype(float);mask=cv2.remap(pack['source'].astype('uint8'),mx,my,cv2.INTER_NEAREST).ravel().astype(bool)
   for k in range(5):
    tr=mask&(fold!=k);te=mask&(fold==k)
    if tr.sum()<10 or not te.any():continue
    for name,basis_,target in [('conditional',Q,y),('frozen_A',np.empty((len(y),0)),y-Q@amp),('plane',np.empty((len(y),0)),y)]:
     mse,_=predict(target,Z,basis_,tr,te);rows.append(dict(frame=f,fold=k,model=name,mse=mse,observed_pixels=int(te.sum())))
   wp=np.array([descriptors[component_index]['x'],descriptors[component_index]['y']])+d
   p=(wp+.5)*self.scale-.5;dv=wp-self.origin;angle=float(np.degrees(np.arctan2(dv[0],-dv[1])))
   opt=self.search_opt[self.search_opt['query'].eq(query)];o=opt[opt.sar_frame.eq(f)].iloc[0];lo,hi=float(o.theta_lo),float(o.theta_hi)
   nominal_gap=max(lo-angle,angle-hi,0.)
   if pack['mode']=='raw':
    allowed=opt[opt.sar_frame.isin(set(A)|set(self.selections[query]['even']))]
    near=allowed[(allowed.optical_frame-o.optical_frame).abs()/self.spec['optical_fps']*1000<=self.cfg['timing_uncertainty_ms']]
    if len(near):lo,hi=float(near.theta_lo.min()),float(near.theta_hi.max())
   energy=Q[:,component_index]**2
   preds.append(dict(scene_id=self.spec['scene_id'],query=query,frame=f,status='RESPONSE_PROPOSAL',method=prefix or 'single',
    x=float(p[0]),y=float(p[1]),point_bearing=angle,nominal_optical_gap=nominal_gap,conditioned_optical_gap=max(lo-angle,angle-hi,0.),
    response_energy_observed_fraction=float(energy[mask].sum()/energy.sum()),transport_holdout_p90=m['holdout_p90']))
  self.native_predictions.extend(preds)
  pd.DataFrame(preds).to_csv(folder/f'{prefix}PREDICTIONS.csv',index=False)
  if not rows:return dict(status='NO_B_IMAGE_READOUT')
  df=pd.DataFrame(rows);df.to_csv(folder/f'{prefix}B_READOUT.csv',index=False);summary=df.groupby('model').mse.mean().to_dict()
  gain=100*(1-summary['conditional']/summary['plane']);frozen=100*(1-summary['frozen_A']/summary['plane'])
  mismatch=sum(p.get('conditioned_optical_gap',0)>1e-9 for p in preds)
  return dict(status=('POINT_GEOMETRY_MISMATCH' if mismatch else ('CONDITIONAL_RESPONSE_PROPOSAL' if gain>0 else 'UNSUPPORTED_IMAGE_RESPONSE')),
   B_frames=int(df.frame.nunique()),B_mse=summary,conditional_gain_pct=gain,frozen_gain_pct=frozen,
   B_conditioned_geometry_mismatches=mismatch,identity_verified=False)

 def joint_groups(self):
  pending=set(self.selections);groups=[]
  while pending:
   first=sorted(pending)[0];pending.remove(first);group={first};changed=True
   while changed:
    changed=False
    for q in sorted(pending):
     if any(abs(self.selections[q]['anchor']-self.selections[t]['anchor'])<=2*self.cfg['half_A_window'] for t in group):
      pending.remove(q);group.add(q);changed=True
   if len(group)>1:groups.append(sorted(group))
  for group in groups:
   if len(group)!=2:
    for q in group:self.results[q]['competition_status']='UNRESOLVED_GROUP_LARGER_THAN_TWO'
    continue
   q1,q2=group;s1,s2=self.selections[q1],self.selections[q2]
   if s1['mode']!='dog' or s2['mode']!='dog':
    for q in group:self.results[q]['competition_status']='UNRESOLVED_CROSS_MODE_GROUP'
    continue
   A=sorted(set(s1['A'])|set(s2['A']));mp=self.models.get(q1,{})
   pools=[self.pool(self.observations(q,A,mp,'dog')) for q in group]
   if any(not len(p) for p in pools):
    for q in group:self.results[q]['competition_status']='JOINT_GEOMETRY_EMPTY'
    continue
   packet=self.packet(A,mp,'dog',pools)
   if packet is None or any(not len(p) for p in packet['pools']):
    for q in group:self.results[q]['competition_status']='JOINT_OBSERVABILITY_UNAVAILABLE'
    continue
   counts=[len(p)*len(self.cfg['blur_multipliers']) for p in packet['pools']];npix=int(packet['valid'].sum())
   if np.prod(counts)>self.cfg['maximum_joint_models'] or npix*sum(counts)>self.cfg['maximum_basis_elements']:
    for q in group:self.results[q]['competition_status']='JOINT_BUDGET_EXCEEDED_UNRESOLVED'
    continue
   valid=packet['valid'];Z=packet['Z'][valid];Y=packet['values'][valid];fold=packet['fold'][valid]
   if any(np.sum(fold==k)==0 for k in range(5)):continue
   meta=[];Qs=[];blurs=self.cfg['small_sigma']*np.array(self.cfg['blur_multipliers'])
   for points in packet['pools']:
    cc=np.repeat(points,len(blurs),axis=0);bb=np.tile(blurs,len(points))
    q=basis(packet['xy'][valid],cc,bb,self.cfg['small_sigma'],self.cfg['large_sigma'])
    q/=np.sqrt(np.sum(q*q,axis=0));Qs.append(q);meta.append(pd.DataFrame(dict(x=cc[:,0],y=cc[:,1],blur=bb)))
   losses=joint_losses(Z,Qs[0],Qs[1],Y,fold);i,j=np.unravel_index(np.argmin(losses),losses.shape)
   desc=[meta[0].iloc[int(i)].to_dict(),meta[1].iloc[int(j)].to_dict()]
   ind=[int(np.argmin(singleton_losses(Z,q,Y,fold))) for q in Qs];idesc=[meta[k].iloc[ind[k]].to_dict() for k in range(2)]
   actual=self.response(packet,desc)[valid]
   direct=float(np.mean([predict(Y[:,f],Z,actual,fold!=k,fold==k)[0] for k in range(5) for f in range(len(A))]))
   assert abs(direct-losses[i,j])<1e-7
   folder=self.out/('JOINT_'+q1+'_'+q2);folder.mkdir()
   np.savez_compressed(folder/'FULL_A_LOSSES.npz',loss=losses)
   B=sorted((set(s1['B'])&set(s2['B']))-set(A))
   dump(folder/'SELECTED.json',dict(created=now(),group=group,A=A,B=B,selected=desc,independent_same_domain=idesc,
    models=int(np.prod(counts)),A_NNLS_error=abs(direct-float(losses[i,j]))))
   dump(folder/'A_SELECTION_SEAL.json',dict(created=now(),B_target_fitting_used=False,
    files={str(folder/f):sha(folder/f) for f in ['FULL_A_LOSSES.npz','SELECTED.json']}))
   for k,q in enumerate(group):
    jr=self.evaluate(q,packet,desc,B,folder,prefix=f'joint_{k}_',component_index=k)
    control=self.evaluate(q,packet,idesc,B,folder,prefix=f'independent_same_domain_{k}_',component_index=k)
    self.results[q]['competition_status']='JOINT_PAIR_EVALUATED'
    self.results[q]['joint_stage']=dict(group=group,shared_image_evidence=True,selected=desc[k],readout=jr,independent_same_domain=control)

 def run(self):
  self.select()
  if self.selections:
   self.decode()
   for q in self.selections:
    print(self.spec['scene_id'],'motion',q,flush=True);self.transport(q)
    self.results[q]=self.search_one(q);print(self.spec['scene_id'],q,self.results[q]['status'],flush=True)
   self.joint_groups()
  pd.DataFrame(self.native_predictions,columns=['scene_id','query','frame','status','method','x','y','point_bearing','nominal_optical_gap','conditioned_optical_gap','response_energy_observed_fraction','transport_holdout_p90']).to_csv(self.out/'PREDICTIONS.csv',index=False)
  dump(self.out/'RESULTS.json',dict(created=now(),scene=self.spec['scene_id'],results=list(self.results.values()),
   pixel_transform='native=(work+0.5)*native_width/work_width-0.5',native_per_work=self.scale,
   optical_mapping_status=self.cfg['mapping']['status'],runtime_manual_SAR_initialization=False,
   input_gate_policy=self.cfg.get('input_gate',{}),
   B_readout='target fitting not used in A objective; public registration conditional on B images'))
  dump(self.out/'INPUT_SEAL.json',dict(created=now(),files={str(p):sha(p) for p in self.inputs}))
  dump(self.out/'COMPLETION_SEAL.json',dict(created=now(),files={str(p):sha(p) for p in self.out.rglob('*') if p.is_file() and p.name!='COMPLETION_SEAL.json'}))
  return self.results
