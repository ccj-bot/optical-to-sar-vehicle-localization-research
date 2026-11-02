"""Run recovery from source video and optical tracks, without old predictions."""
from pathlib import Path
import copy
import cv2
import numpy as np
import pandas as pd
from scipy.ndimage import maximum_filter
from .pipeline import dump,sha,now
from .recovery import (RecoveryPolicy,fit_proxy,make_prior,bridge_prior,
                       candidate_states,exact_joint_path,refine_missing,predicted_fan_crossing)
from .response_dag import anchored_response_path,ResponseDAGPolicy

def foreground(scene,settings):
    frames=sorted(scene.images);start=settings.get('background_first_frame',frames[0])
    sample_frames=[f for f in frames if f>=start][::5]
    if len(sample_frames)<3:raise ValueError('At least three temporal background samples are required')
    sample=np.stack([scene.images[f] for f in sample_frames]).astype('float32')
    median=np.median(sample,axis=0).astype('float32')
    noise=np.maximum(1.4826*np.median(abs(sample-median),axis=0),1.).astype('float32')
    np.savez_compressed(scene.out/'BACKGROUND.npz',median=median,noise_mad=noise,source_frames=sample_frames)
    domain=cv2.erode(scene.domain.astype('uint8'),np.ones((9,9),np.uint8)).astype(bool)
    observations={}
    for f in frames:
        residual=(scene.images[f].astype('float32')-median)/noise
        image=cv2.GaussianBlur(residual,(0,0),2)-cv2.GaussianBlur(residual,(0,0),10)
        peak=(image==maximum_filter(image,size=9))&domain&(image>0)
        y,x=np.where(peak);observations[f]=(np.c_[x,y].astype(float),image[y,x].astype(float),scene.theta[y,x])
    return observations

def isolated_clear_queries(scene,queries):
    result=[]
    for q in queries:
        o=scene.opt[scene.opt['query'].eq(q)]
        p=o[o.tracking_status.eq('CONFIRMED_OBSERVATION')] if 'tracking_status' in o else o
        if len(p)<7 or 'visibility_status' not in p or 'vehicle_overlap_fraction' not in p:continue
        others=scene.opt[~scene.opt['query'].eq(q)&scene.opt.optical_frame.isin(p.optical_frame)]
        if 'tracking_status' in others:others=others[others.tracking_status.eq('CONFIRMED_OBSERVATION')]
        if p.visibility_status.eq('CLEAR_OPTICAL_OBSERVATION').all() and p.vehicle_overlap_fraction.eq(0).all() and others.empty:
            result.append(q)
    return result

def automatic_core_support(scene,query,observations):
    """Rebuild the automatic core and anchored DAG from current SAR pixels."""
    optical=scene.search_opt[scene.search_opt['query'].eq(query)]
    allframes=[f for f in sorted(observations) if f>=int(optical.sar_frame.min())]
    fitframes=[f for f in allframes if f<=int(optical.sar_frame.max())]
    nodes={};values={};energy={}
    for f in allframes:
        xy,v,theta=observations[f];idx=np.argsort(v)[-192:];nodes[f]=xy[idx];values[f]=v[idx]
        near=optical[(optical.sar_frame-f).abs()<=round(scene.spec['sar_fps']*.25)]
        if len(near):
            gap=np.maximum(np.maximum(float(near.theta_lo.min())-theta[idx],theta[idx]-float(near.theta_hi.max())),0)
        else:gap=np.zeros(len(idx))
        energy[f]=-np.log1p(v[idx])+.5*(gap/3.)**2
    if not fitframes:return pd.DataFrame(),{'query':query,'status':'NO_ELIGIBLE_OPTICAL_FRAMES'}
    cost=np.r_[energy[fitframes[0]],0.];parents=[]
    for a,b in zip(fitframes[:-1],fitframes[1:]):
        d2=np.sum((nodes[a][:,None,:]-nodes[b][None,:,:])**2,axis=2);elapsed=b-a
        transition=np.full((len(nodes[a])+1,len(nodes[b])+1),2.)
        step=.5*d2/(16*elapsed);step[d2>(18*elapsed)**2]=1e8
        transition[:-1,:-1]=step;transition[-1,-1]=0.
        matrix=cost[:,None]+transition;parent=matrix.argmin(0)
        cost=matrix[parent,np.arange(len(energy[b])+1)]+np.r_[energy[b],0.];parents.append(parent)
    path=[int(cost.argmin())]
    for p in reversed(parents):path.append(int(p[path[-1]]))
    path=dict(zip(fitframes,path[::-1]))
    optical_core=int(optical.loc[optical.theta.abs().idxmin(),'sar_frame'])
    choices=[f for f in fitframes if abs(f-optical_core)<=3 and path[f]<len(nodes[f])]
    if not choices:return pd.DataFrame(),{'query':query,'status':'NO_AUTOMATIC_CLEAR_CORE'}
    anchor=min(choices,key=lambda f:abs(f-optical_core));index=path[anchor]
    linked,audit=anchored_response_path(nodes,energy,anchor,index,ResponseDAGPolicy())
    rows=[]
    for f,j in sorted(linked.items()):
        x,y=(nodes[f][j]+.5)*scene.scale-.5
        rows.append(dict(query=query,sar_frame=f,x=x,y=y,response=float(values[f][j])))
    return pd.DataFrame(rows),dict(query=query,status='AUTOMATIC_CORE_AND_DAG',anchor_frame=anchor,
        anchor_native=((nodes[anchor][index]+.5)*scene.scale-.5).tolist(),response_frames=len(rows),edges=audit)

def temporal_groups(optical,queries,padding):
    groups=[]
    for q in sorted(queries,key=lambda q:optical[optical['query'].eq(q)].sar_frame.min()):
        o=optical[optical['query'].eq(q)];lo=int(o.sar_frame.min());hi=int(o.sar_frame.max())+padding
        if groups and lo<=groups[-1]['last']:
            groups[-1]['queries'].append(q);groups[-1]['last']=max(hi,groups[-1]['last'])
        else:groups.append(dict(queries=[q],first=lo,last=hi))
    return groups

def run(scene,settings=None):
    settings=copy.deepcopy(settings or {})
    unknown=set(settings)-{'policy','background_first_frame','tail_search_sar_frames','last_sar_frame'}
    if unknown:raise ValueError(f'Unknown response_recovery settings: {sorted(unknown)}')
    policy=RecoveryPolicy(**settings.get('policy',{}));padding=int(settings.get('tail_search_sar_frames',15))
    if padding<0:raise ValueError('tail_search_sar_frames must be nonnegative')
    # Enabling this engine explicitly enables measured partial-bearing searches;
    # the quality audit remains on disk and no identity is upgraded by the gate.
    original_config=copy.deepcopy(scene.cfg)
    scene.cfg=copy.deepcopy(scene.cfg)
    scene.cfg['input_gate']['occluded_bearing_search']={'enabled':True}
    scene.filter_inputs();queries=[q for q in scene.queries if scene.eligibility[q]['input_eligible']]
    input_files=list(scene.inputs);code_files=list(Path(__file__).parent.glob('*.py'))
    input_hashes={str(p):sha(p) for p in input_files+code_files}
    clear=isolated_clear_queries(scene,queries)
    dump(scene.out/'RECOVERY_POLICY.json',dict(created=now(),settings=settings,policy=policy.to_dict(),
        clear_queries=clear,source='current optical tracks and SAR video only',old_predictions_loaded=False,
        proxy_scope=scene.spec['scene_id'],identity_accuracy=None))
    if not clear:
        dump(scene.out/'RECOVERY_ROUTE.json',dict(engine='legacy',reason='NO_ISOLATED_CLEAR_SCENE_SCALE_DONOR',
            no_cross_scene_scale_imported=True))
        # Restore the original gate before the compatibility fallback.
        scene.cfg=original_config
        scene.input_filter_applied=False;scene.opt=pd.read_csv(scene.spec['optical_csv']);scene.results={}
        scene.run();return
    origin=(scene.origin+.5)*scene.scale-.5;half_angle=float(scene.cfg['fan_half_angle_deg'])
    scene.first=max(0,int(scene.opt[scene.opt['query'].isin(queries)].sar_frame.min()))
    cap=cv2.VideoCapture(scene.spec['sar_video']);scene.last=int(cap.get(cv2.CAP_PROP_FRAME_COUNT))-1;cap.release()
    scene.source_last_frame=scene.last
    stop=settings.get('last_sar_frame')
    if stop is not None:scene.last=min(scene.last,int(stop))
    if scene.last<scene.first:raise ValueError('No source frames overlap the query interval')
    print('RECOVERY decode',scene.first,scene.last,flush=True);scene.decode()
    observations=foreground(scene,settings);core_parts=[];audit=[]
    for q in clear:
        support,receipt=automatic_core_support(scene,q,observations);audit.append(receipt)
        if not support.empty:core_parts.append(support)
    dump(scene.out/'AUTOMATIC_CORES.json',dict(created=now(),queries=audit,source_manual_SAR=False))
    if not core_parts:raise ValueError('No automatic clear response available for scene-scale estimation')
    core=pd.concat(core_parts,ignore_index=True);core.to_csv(scene.out/'CORE_RESPONSES.csv',index=False)
    proxy=fit_proxy(scene.opt,core,origin);dump(scene.out/'SCENE_PROXY.json',dict(created=now(),scene=scene.spec['scene_id'],**proxy))
    result=[];lifetimes=[]
    def append(query,frames,xy,response,supported,prior,core_frames=()):
        o=scene.opt[scene.opt['query'].eq(query)];last=int(o.sar_frame.max())
        for t,f in enumerate(frames):
            x,y=(xy[t]+.5)*scene.scale-.5;p=(prior[t]+.5)*scene.scale-.5
            retained=int(f) in core_frames;theta=float(np.degrees(np.arctan2(x-origin[0],origin[1]-y)))
            result.append(dict(scene_id=scene.spec['scene_id'],query=query,sar_frame=int(f),frame=int(f),
                optical_frame=round(f/scene.spec['sar_fps']*scene.spec['optical_fps']),x=float(x),y=float(y),theta=theta,
                prior_x=float(p[0]),prior_y=float(p[1]),response=float(response[t]),current_SAR_update=bool(supported[t]),
                inferred=not bool(supported[t]),core_support_retained=retained,
                state='AUTOMATIC_CORE_RESPONSE' if retained else 'CURRENT_IMAGE_RESPONSE' if supported[t] else 'INFERRED_POSITION',
                object_alive=True,optical_after_last=bool(f>last),exit_eligible=bool(half_angle-5<=abs(theta)<=half_angle),
                identity_verified=False))
    for q in sorted(core['query'].unique()):
        o=scene.opt[scene.opt['query'].eq(q)];frames=np.arange(max(scene.first,int(o.sar_frame.min())),scene.last+1)
        prior,theta,depth,height=make_prior(o,frames,origin,scene.scale,proxy,clear=True)
        support=core[core['query'].eq(q)];prior=bridge_prior(frames,prior,support,scene.scale)
        xy,value,observed=refine_missing(frames,prior,support,observations,origin,scene.scale,policy)
        append(q,frames,xy,value,observed,prior,set(support.sar_frame.astype(int)))
        lifetimes.append(dict(query=q,first=int(frames[0]),last=int(frames[-1]),source_end_is_exit=False))
    other=[q for q in queries if q not in set(core['query'])]
    for group in temporal_groups(scene.opt,other,padding):
        qs=group['queries'];frames=np.arange(max(scene.first,group['first']),min(scene.last,group['last'])+1)
        priors=[];angles=[];depths=[];active=np.zeros((len(frames),len(qs)),bool)
        for qi,q in enumerate(qs):
            o=scene.opt[scene.opt['query'].eq(q)]
            p,t,d,h=make_prior(o,frames,origin,scene.scale,proxy)
            crossing=predicted_fan_crossing(frames,t,int(o.sar_frame.max()),half_angle)
            # A predicted boundary crossing ends this bounded position search;
            # it is recorded as a hypothesis, never a measured exit decision.
            stop=crossing if crossing is not None else int(frames[-1])+1
            active[:,qi]=(frames>=int(o.sar_frame.min()))&(frames<stop)
            priors.append(p);angles.append(t);depths.append(d)
            lifetimes.append(dict(query=q,first=int(o.sar_frame.min()),last=stop-1,
                predicted_beyond_fan_frame=crossing,measured_exit_confirmed=False,full_height_proxy_px=h))
        nodes,e,ids,values=candidate_states(frames,priors,angles,depths,active,observations,origin,scene.scale,policy)
        print('RECOVERY joint',len(qs),'queries',len(frames),'frames',flush=True)
        path=exact_joint_path(nodes,e,ids,priors,active,policy)
        for qi,q in enumerate(qs):
            ts=np.flatnonzero(active[:,qi]);indices=np.array([path[t][qi] for t in ts])
            append(q,frames[ts],nodes[ts,qi,indices],values[ts,qi,indices],ids[ts,qi,indices]>=0,priors[qi][ts])
    df=pd.DataFrame(result).sort_values(['query','sar_frame'])
    if scene.cfg.get('annotation_output',{}).get('enabled',False):
        from .annotation_states import annotate_predictions, write_annotation_export
        from .sequence_runner import bearing_metadata
        from .image_support import read_rendered_support
        options=scene.cfg['annotation_output']
        if options.get('use_rendered_support',False):
            scene.rendered_support=read_rendered_support(scene.spec['sar_video'],scene.images,
                (scene.h,scene.w),options.get('saturation_min',50))
        # This engine searches native current-frame peaks; it does not transport
        # an anchor point through the sequence's background-registration model.
        quality={f:dict(registration_fit_status='NOT_APPLICABLE_NATIVE_FRAME_ENGINE',
            registration_quality_status='NOT_APPLICABLE_NATIVE_FRAME_ENGINE',
            registration_coherent=True) for f in scene.images}
        df=annotate_predictions(scene,df,quality,scene.source_last_frame,metadata=bearing_metadata)
        dump(scene.out/'ANNOTATION_POLICY.json',dict(created=now(),policy=options,
            coordinate_and_model_response_unchanged=True,public_registration_required=False,
            source_last_frame=scene.source_last_frame))
        df[df.terminal_state.notna()].to_csv(scene.out/'QUERY_TERMINALS.csv',index=False)
        write_annotation_export(df,scene.out)
    df.to_csv(scene.out/'PREDICTIONS.csv',index=False)
    dump(scene.out/'LIFETIMES.json',lifetimes)
    inventory=[]
    for q in scene.queries:
        g=df[df['query'].eq(q)];inventory.append(dict(query=q,positions=len(g),current_responses=int(g.current_SAR_update.sum()),
            inferred_positions=int(g.inferred.sum()),input_status=scene.eligibility[q]['status'],identity_verified=False))
    dump(scene.out/'RESULTS.json',dict(created=now(),scene=scene.spec['scene_id'],engine='recovery',queries=inventory,
        source_only_runtime=True,old_predictions_loaded=False,scene_proxy_not_global=True,identity_accuracy=None))
    summary=df.groupby('query').agg(frames=('sar_frame','size'),image_response_frames=('current_SAR_update','sum'),
        inferred_frames=('inferred','sum'),core_support_frames=('core_support_retained','sum'),first=('sar_frame','min'),last=('sar_frame','max'))
    summary.to_csv(scene.out/'SUMMARY.csv')
    np.savez_compressed(scene.out/'WORK_FRAMES.npz',frames=np.array(sorted(scene.images),dtype=np.int32),images=np.stack([scene.images[f] for f in sorted(scene.images)]))
    for p,h in input_hashes.items():
        if sha(p)!=h:raise RuntimeError(f'Input or implementation changed during inference: {p}')
    dump(scene.out/'SOURCE_SEAL.json',dict(created=now(),files=input_hashes,verified_unchanged_during_run=True))
    dump(scene.out/'RECOVERY_ROUTE.json',dict(engine='recovery',old_predictions_loaded=False))
    print(summary.to_string(),flush=True)
