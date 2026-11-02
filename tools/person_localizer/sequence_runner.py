"""Scene-parameterized PERSON sequence experiment; no reference loader in inference.

Initialization is explicitly inherited automatic A selection. Groups contain at
most two people; a fixed Voronoi partition allocates each registered observation
sample to one group. This is an approximation to an unrestricted multi-person
model. Response/association weights are not identity probabilities.
"""
from pathlib import Path
import argparse, json, time, copy
import shutil
import cv2
import numpy as np
import pandas as pd
from scipy.signal import fftconvolve
from threadpoolctl import threadpool_limits
from .pipeline import Scene, dump, sha, now
from .numerics import predict
from .temporal_factors import (TemporalFactorPolicy, residual_grid,
    initial_distribution, forward_backward, viterbi)
from .amplitude_factors import (ResponsePrior, joint_response_factors,
    response_state_energy, ridge_readout)
from .sequence_lifecycle import PersistentLifecycle, ExitPolicy, terminal_feedback_energy
from .image_support import read_rendered_support, sample_observed
from .initialization import prepare_groups
from .annotation_states import registration_quality, annotate_predictions, write_annotation_export


def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))


def sequence_exit_policy(scene):
    """Legacy55 by default; explicit policy replaces task monkeypatches."""
    settings=getattr(scene,'cfg',{}).get('sequence_exit_policy')
    return ExitPolicy(**settings) if settings is not None else ExitPolicy()


def proposal_center(scene, seed, delta, optical, transport_fit, previous=None):
    """Retain the proposal coordinate frame across missing/held optical input.

    This carries a search frame, not a measured person location or a bearing
    observation. The optical factor remains missing and HOLD still forbids an
    image-response update. The compatibility default retains the original reset.
    """
    base=np.asarray(seed,dtype=float).copy()
    if optical['lo'] is not None and transport_fit:
        d=base+delta-scene.origin;radius=np.linalg.norm(d)
        angle=np.degrees(np.arctan2(d[0],-d[1]))
        theta=np.deg2rad(np.clip(angle,optical['lo'],optical['hi']))
        return scene.origin+radius*np.array([np.sin(theta),-np.cos(theta)])-delta
    if scene.cfg.get('persistent_proposal_center',False) and previous is not None:
        return np.asarray(previous,dtype=float).copy()
    return base


def gaussian(xy, centers, blur, cfg, mode):
    d2=np.sum((xy[:,None,:]-np.asarray(centers)[None,:,:])**2,axis=2)
    s=np.hypot(cfg['small_sigma'],blur)
    q=np.exp(-d2/(2*s*s))/(2*np.pi*s*s)
    if mode=='dog':
        s=np.hypot(cfg['large_sigma'],blur)
        q-=np.exp(-d2/(2*s*s))/(2*np.pi*s*s)
    return q


def bearing_metadata(scene,q,f):
    """Never bridge an ineligible measured observation with a geometry factor."""
    of=round(f/scene.spec['sar_fps']*scene.spec['optical_fps'])
    allrows=scene.opt[scene.opt['query'].eq(q)]
    actual=allrows[allrows.optical_frame.eq(of)]
    good=scene.search_opt[scene.search_opt['query'].eq(q)]
    observed=good[good.optical_frame.eq(of)]
    result=dict(query=q,sar_frame=int(f),optical_frame=of,lo=None,hi=None,
        source='MISSING',measured=not actual.empty,eligible=not observed.empty,
        source_observation_id=None,hold=False)
    if not actual.empty and observed.empty:
        return {**result,'source':'HOLD_MEASURED_INPUT','hold':True}
    if not observed.empty:
        row=observed.iloc[0]
        return {**result,'source':'MEASURED','lo':float(row.theta_lo),'hi':float(row.theta_hi),
            'source_observation_id':str(row.get('source_observation_id',f'{q}:OPT:{of}'))}
    if getattr(scene,'cfg',{}).get('persistent_input_hold',False):
        previous=allrows[allrows.optical_frame.lt(of)].sort_values('optical_frame')
        if len(previous) and previous.index[-1] not in good.index:
            # A missing detector row does not establish that an occlusion or
            # input-quality HOLD ended. Only an actual eligible observation can.
            return {**result,'source':'HOLD_UNRESOLVED_MISSING_INPUT','hold':True}
    left=good[good.sar_frame.lt(f)].sort_values('sar_frame')
    right=good[good.sar_frame.gt(f)].sort_values('sar_frame')
    if len(left) and len(right):
        a,b=left.iloc[-1],right.iloc[0]
        middle=allrows[allrows.sar_frame.gt(a.sar_frame)&allrows.sar_frame.lt(b.sar_frame)]
        if b.sar_frame-a.sar_frame<=5 and set(middle.index)<=set(good.index):
            w=(f-a.sar_frame)/(b.sar_frame-a.sar_frame)
            return {**result,'source':'INTERPOLATED_BEARING',
                'lo':float((1-w)*a.theta_lo+w*b.theta_lo),
                'hi':float((1-w)*a.theta_hi+w*b.theta_hi)}
    return result


def measured_exit_evidence(scene,q,f):
    """Only actual optical boundary observations can license an exit decision.

    Two latest measured centers must be in the outer five degrees on the same
    side, with outward progression. Missing source/cache is never exit evidence.
    Ineligible vehicle/size observations are retained for presence, but cannot
    provide the outward boundary license.
    """
    rows=scene.search_opt[scene.search_opt['query'].eq(q)&scene.search_opt.sar_frame.le(f)]
    rows=rows.sort_values('optical_frame').drop_duplicates('optical_frame').tail(2)
    if len(rows)<2:return False
    angle=rows.theta.to_numpy(float)
    policy=sequence_exit_policy(scene)
    return bool(np.all(np.abs(angle)>=policy.half_fov_deg-policy.edge_band_deg) and np.all(np.abs(angle)<=policy.half_fov_deg)
        and np.sign(angle[0])==np.sign(angle[1]) and abs(angle[1])>abs(angle[0])+1e-6)


def refresh_transport(scene, models):
    """Refresh only depleted shared background KLT; missing stays explicitly missing."""
    cfg=scene.cfg['motion'];options=dict(winSize=(cfg['window'],cfg['window']),
        maxLevel=cfg['levels'],criteria=(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,50,.01))
    missing=[f for f in sorted(scene.images) if models.get(f,{}).get('status')!='FIT']
    for f in sorted(missing,key=lambda x:abs(x-scene.common_anchor)):
        neighbors=[g for g in [f-1,f+1] if models.get(g,{}).get('status')=='FIT']
        if not neighbors:continue
        g=neighbors[0];mask=scene.motion_domain.copy()
        for q in scene.queries:
            meta=bearing_metadata(scene,q,g)
            if meta['lo'] is not None:mask&=~((scene.theta>=meta['lo'])&(scene.theta<=meta['hi']))
        pts=cv2.goodFeaturesToTrack(scene.images[g],maxCorners=cfg['max_corners'],qualityLevel=cfg['quality'],
            minDistance=cfg['min_distance'],blockSize=cfg['block_size'],mask=mask.astype('uint8')*255)
        if pts is None:continue
        after,st,_=cv2.calcOpticalFlowPyrLK(scene.images[g],scene.images[f],pts,None,**options)
        if after is None:continue
        back,rt,_=cv2.calcOpticalFlowPyrLK(scene.images[f],scene.images[g],after,None,**options)
        if back is None:continue
        xy=pts[:,0];disp=after[:,0]-xy;cycle=np.linalg.norm(back[:,0]-xy,axis=1)
        good=st[:,0].astype(bool)&rt[:,0].astype(bool)&(cycle<=cfg['cycle_tolerance_px'])&np.isfinite(disp).all(1)
        hold=((xy[:,0]//64+2*(xy[:,1]//64)).astype(int)%5)==0
        if (good&~hold).sum()<3:continue
        median=np.median(disp[good&~hold],axis=0)
        good&=np.linalg.norm(disp-median,axis=1)<=cfg['cycle_tolerance_px']
        fit=good&~hold;test=good&hold
        if fit.sum()<3:continue
        shift=np.median(disp[fit],axis=0);err=np.linalg.norm(disp[test]-shift,axis=1)
        models[f]=dict(status='FIT',delta=(np.asarray(models[g]['delta'])+shift).tolist(),
            fit_points=int(fit.sum()),holdout_points=int(test.sum()),
            holdout_p90=float(models[g].get('holdout_p90') or 0)+float(np.quantile(err,.9) if len(err) else 1),
            method='ADJACENT_PUBLIC_FEATURE_REFRESH',source_frames=[g,f])
    return models


def observed_dog(field,domain,small_sigma,large_sigma):
    """Difference of Gaussians normalized by actual observed kernel support.

    The exterior is excluded from both convolution numerators. It is never
    interpreted as a zero measurement, white signal, or an absent target.
    """
    support=domain.astype('float32');observed=field.astype('float32')*support
    filtered=[]
    for sigma in [small_sigma,large_sigma]:
        den=cv2.GaussianBlur(support,(0,0),sigma)
        num=cv2.GaussianBlur(observed,(0,0),sigma)
        filtered.append(np.divide(num,den,out=np.zeros_like(num),where=den>1e-6))
    return filtered[0]-filtered[1]


def packet(scene,models,xx,yy,f,mode,ownership):
    m=models.get(f,{})
    if m.get('status')!='FIT':return np.zeros(xx.size),np.zeros(xx.size,bool)
    field=scene.images[f].astype('float32');domain=scene.domain
    if mode=='dog':
        if scene.cfg.get('boundary_normalized_dog',False):
            # White exterior and missing kernel context are not measurements.
            # Normalize each Gaussian by its actually observed support instead
            # of eroding away real, visible near-range/fan-edge target pixels.
            field=observed_dog(field,domain,scene.cfg['small_sigma'],scene.cfg['large_sigma'])
        else:
            field=cv2.GaussianBlur(field,(0,0),scene.cfg['small_sigma'])-cv2.GaussianBlur(field,(0,0),scene.cfg['large_sigma'])
            pad=int(np.ceil(4*scene.cfg['large_sigma']))
            domain=cv2.erode(domain.astype('uint8'),np.ones((2*pad+1,2*pad+1),np.uint8)).astype(bool)
    d=m['delta'];mx=np.float32(xx+d[0]);my=np.float32(yy+d[1])
    if mode=='raw' and scene.cfg.get('raw_support_sampling',{}).get('enabled',False):
        if not hasattr(scene,'rendered_support') or f not in scene.rendered_support:
            raise RuntimeError('RAW_RENDERED_SUPPORT_MISSING')
        observed=domain & scene.rendered_support[f]
        value,valid,_=sample_observed(field,observed,mx,my)
        return value.ravel().astype(float),valid.ravel() & ownership
    y=cv2.remap(field,mx,my,cv2.INTER_LINEAR).ravel().astype(float)
    mask=cv2.remap(domain.astype('uint8'),mx,my,cv2.INTER_NEAREST).ravel().astype(bool)
    return y,mask&ownership


def calibration(scene,models,group,xx,yy,xy,Z,fold,owner):
    seed=np.array([[s['x'],s['y']] for s in group['seeds']]);n=len(seed)
    Q=np.column_stack([gaussian(xy,[p],group['seeds'][i]['blur'],scene.cfg,group['mode'])[:,0] for i,p in enumerate(seed)])
    if n==1:Q=np.c_[Q,np.zeros(len(xy))]
    amps=[];variances=[];areas=[];audit=[]
    for f in group['A']:
        y,mask=packet(scene,models,xx,yy,f,group['mode'],owner);train=mask&(fold!=4)
        if train.sum()<10:continue
        mse,a=predict(y,Z,Q,train,train)
        b=np.linalg.lstsq(Z[train],y[train]-Q[train]@a,rcond=None)[0]
        residual=np.where(train,y-Z@b-Q@a,0).reshape(xx.shape);mm=train.reshape(xx.shape).astype(float)
        cov=fftconvolve(residual,residual[::-1,::-1],mode='full');cnt=fftconvolve(mm,mm[::-1,::-1],mode='full')
        cy,cx=np.array(xx.shape)-1;radius=min(12,cy,cx)
        cov=cov[cy-radius:cy+radius+1,cx-radius:cx+radius+1]
        cnt=cnt[cy-radius:cy+radius+1,cx-radius:cx+radius+1]
        cov=np.divide(cov,cnt,out=np.zeros_like(cov),where=cnt>=10)
        area=max(1.,float(np.sum(np.clip(cov/max(cov[radius,radius],1e-10),-1,1)**2)))
        amps.append(a);variances.append(mse);areas.append(area)
        audit.append(dict(frame=int(f),train_pixels=int(train.sum()),noise_variance=float(mse),area=area,amplitudes=a.tolist()))
    if not amps:raise RuntimeError('NO_A_CALIBRATION_OBSERVATIONS')
    scales=np.maximum(np.sqrt(np.mean(np.square(amps),axis=0)),1.)
    return ResponsePrior(max(1e-6,float(np.median(variances))),tuple(scales),float(np.median(areas))),audit


def group_inference(scene,models,group,allgroups,index,out,policy,feedback=None,optimization=None):
    folder=out/group['name'];folder.mkdir(exist_ok=False)
    offsets=residual_grid(policy);n=len(offsets);zero=int(np.where((offsets==0).all(1))[0][0])
    seeds=np.array([[s['x'],s['y']] for s in group['seeds']]);queries=group['queries'];count=len(queries)
    l,t=np.floor(seeds.min(0)-45).astype(int);r,b=np.ceil(seeds.max(0)+46).astype(int)
    yy,xx=np.mgrid[t:b,l:r];xy=np.c_[xx.ravel(),yy.ravel()].astype(float)
    distances=np.column_stack([np.min(np.sum((xy[:,None,:]-np.array([[s['x'],s['y']] for s in g['seeds']])[None,:,:])**2,axis=2),axis=1) for g in allgroups])
    owner=distances.argmin(1)==index
    Z=np.c_[np.ones(len(xy)),(xy-xy.mean(0))/max(xx.shape)];fold=(xx.ravel()//8+2*(yy.ravel()//8))%5
    prior,cal=calibration(scene,models,group,xx,yy,xy,Z,fold,owner)
    dump(folder/'PRIOR_FROZEN.json',dict(created=now(),prior=prior.to_dict(),A_calibration=cal,group=group,
        spatial_fold4_used=False,ownership='nearest frozen group seed; registered sample belongs to one group',
        approximation='independent groups of <=2; not full multi-person posterior',optimization=optimization))
    frames=sorted(scene.images);energies=[];centers=[];packets=[];metadata=[];factors=[];grids=[]
    previous_proposals=[None]*count
    for f in frames:
        delta=np.array(models.get(f,{}).get('delta',[0.,0.]));current=[];meta=[];geom=[];goodgrid=[]
        for i,q in enumerate(queries):
            o=bearing_metadata(scene,q,f);meta.append(o)
            base=proposal_center(scene,seeds[i],delta,o,models.get(f,{}).get('status')=='FIT',previous_proposals[i])
            previous_proposals[i]=base.copy()
            c=base+offsets;current.append(c)
            if o['lo'] is None:geom.append(np.zeros(2*n));goodgrid.append(True);continue
            d=c+delta-scene.origin;angle=np.degrees(np.arctan2(d[:,0],-d[:,1]))
            gap=np.maximum(np.maximum(o['lo']-angle,angle-o['hi']),0)
            width=.5+np.degrees(np.arctan2(float(models.get(f,{}).get('holdout_p90') or 0),np.maximum(np.linalg.norm(d,axis=1),1)))
            ge=.5*(gap/width)**2;ge[gap>3*width]=np.inf
            finite=bool(np.isfinite(ge).any());goodgrid.append(finite)
            geom.append(np.repeat(ge if finite else np.zeros(n),2))
        centers.append(current);metadata.append(meta);grids.append(goodgrid)
        y,mask=packet(scene,models,xx,yy,f,group['mode'],owner);packets.append((y,mask))
        Q=[gaussian(xy,c,group['seeds'][i]['blur'],scene.cfg,group['mode']) for i,c in enumerate(current)]
        second=Q[1] if count==2 else np.zeros((len(xy),1))
        bf=joint_response_factors(y,Z,Q[0],second,mask&(fold!=4),prior);factors.append(bf)
        e=response_state_energy(bf)
        if count==1:e=e[:,1:2]
        e+=geom[0][:,None]
        if count==2:
            e+=geom[1][None,:]
            duplicate=np.linalg.norm(current[0][:,None,:]-current[1][None,:,:],axis=2)<3
            e[0::2,0::2]=np.where(duplicate,np.inf,e[0::2,0::2])
        energies.append(e)
        if (f-frames[0])%50==0:print('FACTOR',scene.spec['scene_id'],group['name'],f,int(mask.sum()),flush=True)
    e=np.stack(energies);mode=np.array([[1-policy.supported_to_weak,policy.supported_to_weak],[policy.weak_to_supported,1-policy.weak_to_supported]])
    edges=[]
    for i in range(count):
        transitions=[]
        for ti in range(1,len(frames)):
            # Actual compensated positions, not changing optical-proposal indices.
            distance=np.sum((centers[ti-1][i][:,None,:]-centers[ti][i][None,:,:])**2,axis=2)
            variance=policy.motion_sigma_per_sar_frame**2*(frames[ti]-frames[ti-1])
            transitions.append(np.kron(np.exp(-.5*distance/variance),mode))
        edges.append(transitions)
    if count==1:edges.append([np.ones((1,1)) for _ in frames[1:]])
    initial=initial_distribution(offsets,policy);initial2=initial if count==2 else np.ones(1)
    if feedback:
        accepts={a['query']:a for a in feedback['accepted']};fi=frames.index(feedback['sar_frame'])
        for i,q in enumerate(queries):
            a=accepts[q];delta=np.asarray(models[frames[fi]]['delta'])
            target=(np.array([a['x'],a['y']])+.5)/scene.scale-.5-delta
            te=terminal_feedback_energy(centers[fi][i],target,feedback['position_sigma_work_px'],feedback['supported_probability'])
            e[fi]+=te[:,None] if i==0 else te[None,:]
    filtered,smooth=forward_backward(e,*edges,initial,initial2)
    baseprior=initial[:,None]*initial2[None,:]
    paths=dict(fixed_A_public=np.tile([2*zero,2*zero if count==2 else 0],(len(frames),1)),
        independent_frame=np.array([np.unravel_index((ef-np.log(baseprior)).argmin(),ef.shape) for ef in e]),
        forward_filter=np.array([np.unravel_index(p.argmax(),p.shape) for p in filtered]),
        smoothed_marginal=np.array([np.unravel_index(p.argmax(),p.shape) for p in smooth]),
        temporal_map=viterbi(e,*edges,initial,initial2))
    np.savez_compressed(folder/'BELIEFS.npz',frames=frames,energies=e,offsets=offsets,filtered=filtered,smoothed=smooth,centers=np.array(centers),**paths)
    pd.DataFrame([o for mm in metadata for o in mm]).to_csv(folder/'OPTICAL_FACTORS.csv',index=False)
    dump(folder/'INFERENCE_SEAL.json',dict(created=now(),files={str(folder/f):sha(folder/f) for f in ['BELIEFS.npz','OPTICAL_FACTORS.csv','PRIOR_FROZEN.json']},
        reference_read=False,feedback_conditioned=bool(feedback),heldout_fold4_used=False))
    predictions=[];readouts=[]
    for variant,path in paths.items():
        lives=[PersistentLifecycle(sequence_exit_policy(scene)) if 'sequence_exit_policy' in scene.cfg else PersistentLifecycle() for _ in queries]
        for ti,f in enumerate(frames):
            states=path[ti];loc=states[:count]//2;active=list(states[:count]%2==0)
            pos=seeds.copy() if variant=='fixed_A_public' else np.stack([centers[ti][i][loc[i]] for i in range(count)])
            Q=np.column_stack([gaussian(xy,[p],group['seeds'][i]['blur'],scene.cfg,group['mode'])[:,0] for i,p in enumerate(pos)])
            if count==1:Q=np.c_[Q,np.zeros(len(xy))];active.append(False)
            y,mask=packets[ti];train=mask&(fold!=4);test=mask&(fold==4)
            if train.sum()>=4 and test.any():
                mse,amp,_=ridge_readout(y,Z,Q,train,test,prior,active)
                deleted=[ridge_readout(y,Z,Q,train,test,prior,[False,active[1]])[0],
                         ridge_readout(y,Z,Q,train,test,prior,[active[0],False])[0]]
                plane=predict(y,Z,np.empty((len(y),0)),train,test)[0]
                readouts.append(dict(variant=variant,group=group['name'],sar_frame=f,mse=mse,plane_mse=plane,
                    first_deleted_mse=deleted[0],second_deleted_mse=deleted[1],test_pixels=int(test.sum()),A_exposed=f in group['A'],
                    both_optically_eligible=all(o['eligible'] for o in metadata[ti]),
                    optical_available=any(o['lo'] is not None for o in metadata[ti]),feedback_conditioned=bool(feedback)))
            else:amp=np.zeros(2)
            bf=joint_response_factors(y,Z,Q[:,:1],Q[:,1:],train,prior)
            increments=[float(bf['both'][0,0]-bf['second'][0]) if active[1] else float(bf['first'][0]),
                        float(bf['both'][0,0]-bf['first'][0]) if active[0] else float(bf['second'][0])]
            for i,q in enumerate(queries):
                delta=np.asarray(models.get(f,{}).get('delta',[0.,0.]));p=pos[i]+delta;d=p-scene.origin
                angle=float(np.degrees(np.arctan2(d[0],-d[1])));o=metadata[ti][i]
                update=bool(active[i] and amp[i]>0 and increments[i]>0 and grids[ti][i] and mask.any() and not o['hold'])
                exit_evidence=measured_exit_evidence(scene,q,f)
                life=lives[i].update(f,angle,o['measured'],update,exit_evidence=exit_evidence)
                native=(p+.5)*scene.scale-.5
                gap=max(o['lo']-angle,angle-o['hi'],0) if o['lo'] is not None else None
                definite=bool(update and o['eligible'] and not o['hold'] and models.get(f,{}).get('status')=='FIT')
                weight=smooth[ti].sum(axis=1-i).reshape(n,2)[:,0].sum() if count==2 else smooth[ti,:,0].reshape(n,2)[:,0].sum()
                predictions.append(dict(scene=scene.spec['scene_id'],variant=variant,group=group['name'],query=q,sar_frame=f,
                    optical_frame=o['optical_frame'],source_observation_id=o['source_observation_id'],x=float(native[0]),y=float(native[1]),
                    reference_x=float(pos[i,0]),reference_y=float(pos[i,1]),residual_x=float(pos[i,0]-seeds[i,0]),residual_y=float(pos[i,1]-seeds[i,1]),
                    nominal_gap_deg=gap,optical_eligible=o['eligible'],optical_measured=o['measured'],input_hold=o['hold'],
                    response_supported=bool(active[i]),conditional_log_BF=increments[i],amplitude=float(amp[i]),
                    current_SAR_update=update,definite_point=definite,display_marker=bool(life['object_alive'] and not o['hold']),
                    lifecycle=life['status'],edge_exit_allowed=life['edge_exit_allowed'],exit_measured_evidence=exit_evidence,supported_model_weight=float(weight),
                    transport_status=models.get(f,{}).get('status','MISSING'),
                    source_sar_observation=f'{scene.spec["scene_id"]}:SAR:{f}:group:{group["name"]}:one_shared_factor',
                    phase='A_EXPOSED' if f in group['A'] else 'B',feedback_conditioned=bool(feedback),identity_verified=False))
    result=pd.DataFrame(predictions);ev=pd.DataFrame(readouts)
    result.to_csv(folder/'PREDICTIONS.csv',index=False);ev.to_csv(folder/'READOUT.csv',index=False)
    assert not ((result.lifecycle=='EXITED_AT_EDGE')&~result.edge_exit_allowed).any()
    assert not (result.input_hold&result.definite_point).any()
    return result,ev


def execute(manifest,output,feedback=False,optimization=None):
    out=Path(output);out.mkdir(parents=True,exist_ok=False);m=read(manifest)
    scene=Scene(read(m['scene']),read(m['config']),out/'runtime');scene.select()
    cap=cv2.VideoCapture(scene.spec['sar_video']);total=int(cap.get(cv2.CAP_PROP_FRAME_COUNT));cap.release()
    scene.first=int(m['first']);scene.last=total-1 if m.get('to_source_end',True) else int(m['last'])
    scene.common_anchor=int(m['common_anchor'])
    if not 0<=scene.first<=scene.last<total:raise ValueError('Sequence frame range is outside source video')
    scene.source_last_frame=total-1
    if m.get('work_frames_cache'):
        z=np.load(m['work_frames_cache']);scene.images={int(f):im for f,im in zip(z['frames'],z['images'])}
        if set(scene.images)!=set(range(scene.first,scene.last+1)):
            raise ValueError('Frame cache must cover every requested frame exactly')
        if any(im.shape!=(scene.h,scene.w) for im in scene.images.values()):
            raise ValueError('Frame cache dimensions do not match scene/config')
    else:scene.decode()
    support_policy=scene.cfg.get('raw_support_sampling',{})
    annotation_policy=scene.cfg.get('annotation_output',{})
    annotation_enabled=annotation_policy.get('enabled',False)
    if support_policy.get('enabled',False) or (annotation_enabled and annotation_policy.get('use_rendered_support',False)):
        scene.rendered_support=read_rendered_support(scene.spec['sar_video'],scene.images,
            (scene.h,scene.w),saturation_min=int(support_policy.get('saturation_min',annotation_policy.get('saturation_min',50))))
        dump(out/'RENDERED_SUPPORT_POLICY.json',dict(created=now(),policy=support_policy,
            source=scene.spec['sar_video'],frames=len(scene.rendered_support),
            mask='filled largest colored outer contour; dark interior retained',
            interpolation='bilinear observed numerator divided by observed weight',
            raw_only=True,also_used_for_annotation=annotation_enabled,source_sha256=sha(scene.spec['sar_video'])))
    cache=m.get('transport_cache')
    if cache:
        data=read(cache)
        if 'cache_query' in m:data=data[m['cache_query']]
        models={int(f):v for f,v in data.items()}
        if not set(scene.images)<=set(models):
            scene.selections['_shared_public_']=dict(anchor=scene.common_anchor,A=m['transport_A'])
            fresh=scene.transport('_shared_public_');fresh.update(models);models=fresh
    else:
        scene.selections['_shared_public_']=dict(anchor=scene.common_anchor,A=m['transport_A'])
        models=scene.transport('_shared_public_')
    refresh_transport(scene,models);dump(out/'PUBLIC_TRANSPORT.json',models)
    np.savez_compressed(out/'WORK_FRAMES.npz',frames=sorted(scene.images),images=np.stack([scene.images[f] for f in sorted(scene.images)]))
    groups=prepare_groups(m,scene.spec,scene.cfg,out)
    for group in groups:
        if group.get('seeds_at_anchor'):
            for s in group['seeds']:
                delta=models.get(int(s['anchor']),{}).get('delta')
                if delta is None:raise RuntimeError('INITIAL_ANCHOR_TRANSPORT_MISSING')
                s['x']-=delta[0];s['y']-=delta[1]
    policy_cfg=m.get('temporal_policy',{})
    policy=TemporalFactorPolicy(**policy_cfg);terminal=read(m['terminal_feedback']) if feedback else None
    dump(out/'POLICY_FROZEN.json',dict(created=now(),manifest=copy.deepcopy(m),resolved_groups=groups,
        resolved_seed_coordinates='common-reference work pixels',temporal_policy=policy.to_dict(),exit_policy=sequence_exit_policy(scene).to_dict(),
        annotation_policy=annotation_policy,
        feedback_conditioned=feedback,initialization_receipt='INITIALIZATION.json',
        known_limits=['optical cache covers selected segments; source tail without observations retains hypotheses',
          'nominal FPS synchronization unverified','fixed A response scale; fixed approximate public image transport',
          'groups <=2; frozen sample partition approximates cross-group competition'],optimization=optimization))
    inputs=[Path(manifest),Path(m['scene']),Path(m['config']),Path(scene.spec['optical_csv'])]
    inputs.extend(sorted(Path(__file__).parent.glob('*.py')))
    if support_policy.get('enabled',False) or annotation_enabled:
        inputs.extend([Path(scene.spec['sar_video']),Path(__file__).with_name('image_support.py')])
    inputs.extend(Path(m[k]) for k in ['work_frames_cache','transport_cache'] if m.get(k))
    dump(out/'INPUT_SEAL.json',dict(created=now(),files={str(p):sha(p) for p in inputs}))
    allpred=[];allev=[]
    for gi,group in enumerate(groups):
        p,ev=group_inference(scene,models,group,groups,gi,out,policy,terminal,optimization);allpred.append(p);allev.append(ev)
    pred=pd.concat(allpred,ignore_index=True);ev=pd.concat(allev,ignore_index=True)
    if annotation_enabled:
        quality=registration_quality(models,scene.images,annotation_policy.get('registration',{}),scene.common_anchor)
        pd.DataFrame([dict(sar_frame=f,**v) for f,v in quality.items()]).to_csv(out/'REGISTRATION_QUALITY.csv',index=False)
        pred=annotate_predictions(scene,pred,quality,scene.source_last_frame)
        events=pred[pred.episode_started|pred.reentry_event|pred.source_end_censored|pred.segment_end_open]
        events.to_csv(out/'ANNOTATION_EVENTS.csv',index=False)
        pred[pred.terminal_state.notna()].to_csv(out/'QUERY_TERMINALS.csv',index=False)
        dump(out/'ANNOTATION_POLICY.json',dict(created=now(),policy=annotation_policy,
            coordinate_and_model_response_unchanged=True,source_last_frame=scene.source_last_frame,
            review_budget_is_not_target_error=True,identity_verified=False))
    pred.to_csv(out/'PREDICTIONS.csv',index=False);ev.to_csv(out/'READOUT.csv',index=False)
    write_annotation_export(pred,out)
    dump(out/'PREDICTION_SEAL.json',dict(created=now(),files={str(out/f):sha(out/f) for f in ['PREDICTIONS.csv','READOUT.csv','POLICY_FROZEN.json']},reference_read=False))
    dump(out/'RESULTS.json',dict(created=now(),scene=scene.spec['scene_id'],frames=[scene.first,scene.last],queries=sum((g['queries'] for g in groups),[]),
        inference_rows=len(pred),transport_missing=sum(models.get(f,{}).get('status')!='FIT' for f in scene.images),
        source_end_is_exit=False,feedback_conditioned=feedback,identity_accuracy=None))
    print('SCENE_COMPLETE',scene.spec['scene_id'],str(out),flush=True)
    return pred


def replay_lifecycle(manifest,source,output):
    """Replay actual sealed positions through the corrected lifecycle only."""
    out=Path(output);out.mkdir(parents=True,exist_ok=False);source=Path(source);m=read(manifest)
    for p,h in read(source/'PREDICTION_SEAL.json')['files'].items():
        if sha(p)!=h:raise RuntimeError(f'Parent prediction changed: {p}')
    scene=Scene(read(m['scene']),read(m['config']),out/'runtime');scene.select()
    old=pd.read_csv(source/'PREDICTIONS.csv');pred=old.copy()
    for (variant,q),g in pred.groupby(['variant','query']):
        life=PersistentLifecycle(sequence_exit_policy(scene)) if 'sequence_exit_policy' in scene.cfg else PersistentLifecycle()
        for idx,row in g.sort_values('sar_frame').iterrows():
            p=(np.array([row.x,row.y])+.5)/scene.scale-.5;d=p-scene.origin
            angle=float(np.degrees(np.arctan2(d[0],-d[1])))
            evidence=measured_exit_evidence(scene,q,int(row.sar_frame))
            result=life.update(int(row.sar_frame),angle,bool(row.optical_measured),bool(row.current_SAR_update),exit_evidence=evidence)
            pred.loc[idx,'lifecycle']=result['status'];pred.loc[idx,'edge_exit_allowed']=result['edge_exit_allowed']
            pred.loc[idx,'display_marker']=bool(result['object_alive'] and not row.input_hold)
            pred.loc[idx,'exit_measured_evidence']=evidence
    np.testing.assert_array_equal(old[['x','y','reference_x','reference_y']].to_numpy(),pred[['x','y','reference_x','reference_y']].to_numpy())
    assert not ((pred.lifecycle=='EXITED_AT_EDGE')&~pred.edge_exit_allowed).any()
    assert not (pred.input_hold&pred.definite_point).any()
    pred.to_csv(out/'PREDICTIONS.csv',index=False)
    shutil.copyfile(source/'READOUT.csv',out/'READOUT.csv')
    result=read(source/'RESULTS.json');result.update(created=now(),execution='real-state lifecycle replay, inference unchanged')
    dump(out/'RESULTS.json',result)
    dump(out/'PARENT_INFERENCE.json',dict(source=str(source.resolve()),inference_unchanged=True,
        files={str(source/f):sha(source/f) for f in ['PREDICTION_SEAL.json','PREDICTIONS.csv','READOUT.csv','POLICY_FROZEN.json']}))
    dump(out/'POLICY_FROZEN.json',dict(created=now(),manifest=m,parent=str(source.resolve()),
        lifecycle='reversible exit with measured outward optical edge evidence',exit_policy=ExitPolicy().to_dict(),
        feedback_conditioned=result['feedback_conditioned']))
    dump(out/'PREDICTION_SEAL.json',dict(created=now(),files={str(out/f):sha(out/f) for f in ['PREDICTIONS.csv','READOUT.csv','POLICY_FROZEN.json','PARENT_INFERENCE.json']},reference_read=False))
    print('LIFECYCLE_REPLAY_COMPLETE',scene.spec['scene_id'],flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--feedback',action='store_true')
    parser.add_argument('--replay-from',type=Path)
    args=parser.parse_args();cv2.setNumThreads(4);threadpool_limits(4);cv2.setRNGSeed(20261027)
    start=time.time()
    if args.replay_from:replay_lifecycle(args.manifest,args.replay_from,args.output)
    else:execute(args.manifest,args.output,args.feedback)
    print('ELAPSED',time.time()-start,flush=True)


if __name__=='__main__':main()
