"""Core-conditioned response paths with explicit displacement across gaps.

A missing observation is a skip edge from a concrete previous position, never
an unlocated scalar state that can restart at any bright structure. This is
apparent image support association, not physical motion or identity recovery.
"""
from dataclasses import dataclass,asdict
import numpy as np

@dataclass(frozen=True)
class ResponseDAGPolicy:
    motion_sigma_work_px: float = 4.
    maximum_step_work_px: float = 18.
    maximum_gap_sar_frames: int = 8
    missing_frame_cost: float = 2.

    def to_dict(self):return asdict(self)

def anchored_response_path(nodes,energies,anchor_frame,anchor_index,policy=ResponseDAGPolicy()):
    """Exact shortest path in each temporal DAG direction from an automatic core.

    Ending a measured path has zero additional observation cost, so the graph
    need not invent support through source/cache ends. Object presence is kept
    separately by the caller. Coordinates and elapsed-frame units are explicit.
    """
    frames=sorted(nodes)
    if anchor_frame not in nodes or not 0<=anchor_index<len(nodes[anchor_frame]):raise ValueError('Unavailable automatic core')
    results={anchor_frame:int(anchor_index)};audit=[]
    for direction in [-1,1]:
        ordered=[anchor_frame]+sorted([f for f in frames if (f-anchor_frame)*direction>0],reverse=direction<0)
        scores={anchor_frame:np.full(len(nodes[anchor_frame]),np.inf)};scores[anchor_frame][anchor_index]=float(energies[anchor_frame][anchor_index])
        parents={};best=(float(scores[anchor_frame][anchor_index]),anchor_frame,anchor_index)
        for i,f in enumerate(ordered[1:],1):
            current=np.full(len(nodes[f]),np.inf);pf=np.full(len(nodes[f]),-1,int);pi=np.full(len(nodes[f]),-1,int)
            for previous in reversed(ordered[:i]):
                elapsed=abs(f-previous)
                if elapsed>policy.maximum_gap_sar_frames:break
                if previous not in scores or not np.isfinite(scores[previous]).any():continue
                distance=np.sum((nodes[previous][:,None,:]-nodes[f][None,:,:])**2,axis=2)
                transition=.5*distance/(policy.motion_sigma_work_px**2*elapsed)+policy.missing_frame_cost*(elapsed-1)
                transition[distance>(policy.maximum_step_work_px*elapsed)**2]=np.inf
                value=scores[previous][:,None]+transition;index=value.argmin(0);minimum=value[index,np.arange(len(nodes[f]))]
                use=minimum<current;current[use]=minimum[use];pf[use]=previous;pi[use]=index[use]
            current+=energies[f];scores[f]=current;parents[f]=(pf,pi)
            if np.isfinite(current).any():
                j=int(current.argmin())
                if float(current[j])<best[0]:best=(float(current[j]),f,j)
        _,f,j=best;endpoint=f;used=[]
        while f!=anchor_frame:
            results[f]=int(j);pf,pi=parents[f];previous,index=int(pf[j]),int(pi[j])
            if previous<0:raise RuntimeError('Broken response DAG predecessor')
            used.append(dict(first_frame=min(f,previous),last_frame=max(f,previous),elapsed_sar_frames=abs(f-previous),
                displacement_work_px=float(np.linalg.norm(nodes[f][j]-nodes[previous][index]))))
            f,j=previous,index
        audit.append(dict(direction=direction,endpoint_frame=endpoint,path_cost=best[0],edges=used))
    return results,audit
