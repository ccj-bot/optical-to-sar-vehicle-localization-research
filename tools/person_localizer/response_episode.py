"""Associate measured SAR response episodes without scalar-gap teleportation.

The primary episode is chosen at an optical-only central observation. Other
episodes need a bounded image displacement across a short gap. Unlinked strong
structures remain unresolved, not the same identity merely because they are bright.
"""
from dataclasses import dataclass,asdict
import numpy as np
import pandas as pd

@dataclass(frozen=True)
class EpisodePolicy:
    maximum_step_work_px: float = 18.
    maximum_gap_sar_frames: int = 8
    native_per_work: float = 2.
    anchor_half_window_sar_frames: int = 3
    maximum_observation_step_sar_frames: int = 1

    def __post_init__(self):
        if self.maximum_step_work_px<=0 or self.maximum_gap_sar_frames<1 or self.native_per_work<=0:
            raise ValueError('Invalid episode association scale')

    def to_dict(self):return asdict(self)


def associate_response_episodes(paths,optical,policy=EpisodePolicy()):
    """Keep raw proposals, annotate core association and unresolved locations.

    Geometry uses native image displacement and actual elapsed SAR frames. There
    is no annotation loader and no recovered physical motion claim. A missed
    response retains the object; this function never generates an EXIT label.
    """
    output=[];decisions=[]
    for query,source in paths.groupby('query',sort=False):
        g=source.sort_values('sar_frame').copy();valid=g.candidate_index.ge(0)&np.isfinite(g[['x','y']]).all(axis=1)
        episode=[];number=0;previous_valid=False;previous_frame=None
        for good,f in zip(valid,g.sar_frame):
            if good and (not previous_valid or previous_frame is None or f-previous_frame>policy.maximum_observation_step_sar_frames):number+=1
            episode.append(number if good else -1);previous_valid=bool(good);previous_frame=int(f)
        g['response_episode']=episode;g['primary_episode_associated']=False;g['anchor_selected_by_optical_only']=False
        opt=optical[optical['query'].eq(query)].copy()
        if opt.empty:
            output.append(g);decisions.append(dict(query=query,status='NO_OPTICAL_ANCHOR'));continue
        # Mature actual detections supply the temporal shell; no SAR response
        # score participates in choosing the central optical observation.
        if 'tracking_status' in opt:opt=opt[opt.tracking_status.eq('CONFIRMED_OBSERVATION')]
        if opt.empty:output.append(g);decisions.append(dict(query=query,status='NO_MATURE_OPTICAL_ANCHOR'));continue
        anchor=int(opt.loc[opt.theta.abs().idxmin(),'sar_frame'])
        near=g[valid&(g.sar_frame-anchor).abs().le(policy.anchor_half_window_sar_frames)]
        if near.empty:
            output.append(g);decisions.append(dict(query=query,status='NO_RESPONSE_NEAR_OPTICAL_ANCHOR',anchor=anchor));continue
        selected=near.loc[(near.sar_frame-anchor).abs().idxmin()];core=int(selected.response_episode)
        g.loc[g.index==selected.name,'anchor_selected_by_optical_only']=True
        segments={int(k):p.sort_values('sar_frame') for k,p in g[g.response_episode.ge(0)].groupby('response_episode')}
        accepted={core};links=[]
        # Grow from the core in either temporal direction; rejected episodes
        # never reset the accepted state to a distant structure.
        for direction in [-1,1]:
            current=core
            ordered=sorted((k for k in segments if (k-core)*direction>0),reverse=direction<0)
            for eid in ordered:
                a=segments[current].iloc[-1 if direction>0 else 0];b=segments[eid].iloc[0 if direction>0 else -1]
                elapsed=abs(int(b.sar_frame)-int(a.sar_frame));distance=float(np.linalg.norm([b.x-a.x,b.y-a.y]))/policy.native_per_work
                limit=policy.maximum_step_work_px*elapsed
                passed=bool(elapsed<=policy.maximum_gap_sar_frames and distance<=limit)
                links.append(dict(from_episode=current,to_episode=eid,elapsed_sar_frames=elapsed,distance_work_px=distance,maximum_distance_work_px=limit,linked=passed))
                if passed:accepted.add(eid);current=eid
        g['primary_episode_associated']=g.response_episode.isin(accepted)
        collision=g.get('shared_peak_collision',pd.Series(False,index=g.index)).fillna(False).astype(bool)
        g['current_SAR_update']=g.primary_episode_associated&valid&~collision
        g['object_alive']=True;g['identity_verified']=False
        g['association_state']=np.where(g.current_SAR_update,'CONDITIONAL_SAR_RESPONSE',
            np.where(collision,'SHARED_RESPONSE_UNASSIGNED','LOCATION_UNRESOLVED_ID_RETAINED'))
        output.append(g);decisions.append(dict(query=query,anchor=anchor,core_episode=core,associated_episodes=sorted(accepted),links=links,
            accepted_response_frames=int(g.current_SAR_update.sum()),identity_verified=False))
    return pd.concat(output,ignore_index=True),decisions
