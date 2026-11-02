"""Persistent PERSON lifecycle and terminal feedback for offline inference.

Missing observations in the interior are not exits. User-confirmed late
associations constrain the offline graph without inventing earlier detections.
"""
from dataclasses import dataclass,asdict
import numpy as np


@dataclass(frozen=True)
class ExitPolicy:
    half_fov_deg: float = 55.
    edge_band_deg: float = 5.
    absent_edge_frames: int = 3

    def __post_init__(self):
        if not 0<self.edge_band_deg<self.half_fov_deg:raise ValueError('Invalid edge band')
        if self.absent_edge_frames<1:raise ValueError('Invalid absence duration')

    def can_consider_exit(self,angle):
        return bool(np.isfinite(angle) and abs(angle)>=self.half_fov_deg-self.edge_band_deg)

    def to_dict(self):return asdict(self)


class PersistentLifecycle:
    def __init__(self,policy=ExitPolicy()):
        self.policy=policy;self.started=False;self.exited=False;self.edge_missing=0;self.previous_angle=None

    def update(self,frame,angle,optical_observed,sar_supported,exit_evidence=True):
        edge=self.policy.can_consider_exit(angle)
        outward=bool(self.previous_angle is not None and np.isfinite(angle) and np.isfinite(self.previous_angle)
                     and abs(angle)>abs(self.previous_angle)+1e-6)
        if optical_observed:
            self.started=True;self.exited=False;self.edge_missing=0;status='ACTIVE_OBSERVED'
        elif not self.started:
            status='NOT_YET_OBSERVED'
        elif not edge or not exit_evidence:
            # An exit is a revisable boundary hypothesis. A propagated point
            # returning inside, or absence of measured boundary evidence, must
            # never turn a central missing track into a permanent deletion.
            revoked=self.exited;self.exited=False;self.edge_missing=0
            status='ACTIVE_EXIT_REVOKED' if revoked else ('ACTIVE_SAR_UPDATE' if sar_supported else 'ACTIVE_MISSING_INTERIOR')
        elif self.exited:
            status='EXITED_AT_EDGE'
        elif sar_supported:
            self.edge_missing=0;status='ACTIVE_EDGE_RESPONSE'
        elif outward or abs(angle)>self.policy.half_fov_deg:
            self.edge_missing+=1;self.exited=self.edge_missing>=self.policy.absent_edge_frames
            status='EXITED_AT_EDGE' if self.exited else 'EDGE_EXIT_CANDIDATE'
        else:
            self.edge_missing=0;status='ACTIVE_MISSING_EDGE'
        self.previous_angle=float(angle) if np.isfinite(angle) else None
        return dict(frame=int(frame),status=status,object_alive=self.started and not self.exited,
                    edge_exit_allowed=edge,edge_absence_count=self.edge_missing,
                    optical_observed=bool(optical_observed),sar_supported=bool(sar_supported))


def terminal_feedback_energy(centers,accepted_point,sigma_px=3.,supported_probability=.9):
    """Soft position/response factor for one explicitly accepted late instant."""
    if sigma_px<=0 or not 0<supported_probability<1:raise ValueError('Invalid feedback prior')
    position=np.sum((np.asarray(centers)-np.asarray(accepted_point))**2,axis=1)/(2*sigma_px*sigma_px)
    mode=-np.log([supported_probability,1-supported_probability])
    return np.repeat(position,2)+np.tile(mode,len(position))
