"""Image visibility, independent of identity existence and localization fitting.

A propagated crossing is an outside-image hypothesis, never a measured exit.
Once latched, unassociated SAR support or a registration change cannot revive
the old episode. A fresh optical observation can start a new episode. Interior
missingness, input HOLD and source termination never imply an exit.
"""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class VisibilityPolicy:
    half_angle_deg: float = 60.0
    edge_band_deg: float = 5.0
    outside_frames: int = 3

    def __post_init__(self):
        if not 0 < self.edge_band_deg < self.half_angle_deg:
            raise ValueError('Invalid image edge band')
        if self.outside_frames < 1:
            raise ValueError('Invalid outside persistence')


class ImageVisibilityLifecycle:
    def __init__(self, policy=None):
        self.policy = policy or VisibilityPolicy()
        self.started = False
        self.outside_latched = False
        self.episode = 0
        self.outside_count = 0
        self.edge_side = 0
        self.edge_response_seen = False
        self.last_angle = None

    def update(self, frame, angle, optical_observed, sar_supported,
               position_valid=True, input_hold=False, transport_coherent=True):
        finite = math.isfinite(angle)
        side = 1 if angle >= 0 else -1
        edge = finite and self.policy.half_angle_deg - self.policy.edge_band_deg <= abs(angle) <= self.policy.half_angle_deg
        outside = finite and abs(angle) > self.policy.half_angle_deg
        birth = bool(optical_observed and not self.started)
        reentry = bool(optical_observed and self.outside_latched)
        if birth or reentry:
            self.episode += 1
            self.started = True
            self.outside_latched = False
            self.outside_count = 0
            self.edge_side = 0
            self.edge_response_seen = False
        if not self.started:
            status = 'NOT_YET_OBSERVED'
        elif self.outside_latched:
            status = 'OUTSIDE_IMAGE_LATCHED'
        elif not transport_coherent:
            self.outside_count = 0
            status = 'ACTIVE_REGISTRATION_UNCERTAIN'
        else:
            if edge and position_valid and not input_hold:
                self.edge_side = side
                self.edge_response_seen |= bool(sar_supported)
            outward = (self.last_angle is not None and finite and
                       side == (1 if self.last_angle >= 0 else -1) and
                       abs(angle) >= abs(self.last_angle) - 1e-6)
            if input_hold:
                self.outside_count = 0
                status = 'ACTIVE_INPUT_HOLD'
            elif not position_valid:
                self.outside_count = 0
                status = 'ACTIVE_POSITION_UNAVAILABLE'
            elif optical_observed:
                self.outside_count = 0
                status = 'REENTERED_OPTICALLY' if reentry else 'ENTERED_OPTICALLY' if birth else 'ACTIVE_OPTICAL'
            elif outside and self.edge_side == side and outward:
                self.outside_count += 1
                self.outside_latched = self.outside_count >= self.policy.outside_frames
                status = 'OUTSIDE_IMAGE_LATCHED' if self.outside_latched else 'EDGE_OUTSIDE_CANDIDATE'
            else:
                self.outside_count = 0
                status = ('ACTIVE_INPUT_HOLD' if input_hold else
                          'ACTIVE_POSITION_UNAVAILABLE' if not position_valid else
                          'ACTIVE_SAR_RESPONSE' if sar_supported else 'ACTIVE_INFERRED')
        visible = bool(self.started and not self.outside_latched and not outside and
                       position_valid and not input_hold and transport_coherent)
        # An invalid registration/held point cannot become the next outward
        # motion observation. Keep the most recent usable image-coordinate state.
        if transport_coherent and position_valid and not input_hold:
            self.last_angle = float(angle) if finite else None
        return dict(frame=int(frame), visibility_status=status,
                    visibility_episode=self.episode, entry_event=birth,
                    reentry_event=reentry, edge_exit_allowed=bool(edge or outside and self.edge_side == side),
                    outside_count=self.outside_count, outside_latched=self.outside_latched,
                    visibility_marker=visible,
                    current_response_visible=bool(visible and sar_supported),
                    identity_state_retained=self.started,
                    last_edge_had_response=self.edge_response_seen,
                    measured_exit_confirmed=False)

    def terminal(self):
        return ('OUTSIDE_IMAGE_HYPOTHESIS_LATCHED' if self.outside_latched else
                'SOURCE_END_CENSORED' if self.started else 'NEVER_OBSERVED')
