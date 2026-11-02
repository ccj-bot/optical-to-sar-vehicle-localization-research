"""Optical-only duplicate handling, motion tracking and vehicle occlusion memory.

Measured boxes are never replaced by Kalman predictions. Lost tracks can retain
their identity internally, but produce no synthetic detection or SAR input row.
"""
from dataclasses import dataclass
from types import SimpleNamespace

import numpy as np

from .vehicle_gate import person_vehicle_overlap
from .vehicle_context import VehicleContextTracker, relation, contaminated_extents


@dataclass(frozen=True)
class TrackingPolicy:
    duplicate_cover: float = .90
    duplicate_width_ratio: float = .60
    duplicate_head_distance: float = .25
    duplicate_max_height_ratio: float = 2.2
    overlap_enter: float = .50
    overlap_exit: float = .25
    release_observations: int = 3
    vehicle_clearance_fraction: float = .05
    partial_aspect_ratio: float = .70
    track_buffer: int = 30
    fuse_detection_confidence_in_association: bool = False
    short_step_center_height_fraction: float = .45
    short_step_color_similarity: float = .70
    vehicle_duplicate_iou: float = .65
    vehicle_duplicate_area_ratio: float = 3.5
    vehicle_context_max_gap: int = 3
    vehicle_upper_horizontal_cover: float = .60
    vehicle_upper_max_height_fraction: float = .65
    vehicle_upper_gap_fraction: float = .50
    vehicle_upper_inside_fraction: float = .25
    vehicle_extent_added_fraction: float = .70


def overlap_metrics(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    intersection = np.prod(np.maximum(0., np.minimum(a[2:], b[2:])-np.maximum(a[:2], b[:2])))
    area_a = np.prod(a[2:]-a[:2])
    area_b = np.prod(b[2:]-b[:2])
    return float(intersection/min(area_a, area_b)), float(intersection/(area_a+area_b-intersection))


def reconcile_duplicates(detections, policy=TrackingPolicy(), vehicles=None):
    """Return source indices and suppressions, requiring common head/top support.

    Containment alone is insufficient: adjacent people and a wide crowd box must
    survive. This is conservative duplicate-observation handling, not identity GT.
    """
    order = sorted(range(len(detections)), key=lambda i: (
        -detections[i]['confidence'],
        -np.prod(np.asarray(detections[i]['bbox'])[2:]-np.asarray(detections[i]['bbox'])[:2]), i))
    kept, suppressed = [], []
    for i in order:
        small = np.asarray(detections[i]['bbox'], float)
        sw, sh = small[2:]-small[:2]
        duplicate = None
        for j in kept:
            large = np.asarray(detections[j]['bbox'], float)
            lw, lh = large[2:]-large[:2]
            cover, iou = overlap_metrics(small, large)
            center_gap = abs((small[0]+small[2]-large[0]-large[2])/2)
            if (cover >= policy.duplicate_cover
                    and min(sw, lw)/max(sw, lw) >= policy.duplicate_width_ratio
                    and center_gap <= policy.duplicate_head_distance*min(sw, lw)
                    and abs(small[1]-large[1]) <= policy.duplicate_head_distance*min(sh, lh)
                    and max(sh, lh)/min(sh, lh) <= policy.duplicate_max_height_ratio):
                duplicate = dict(suppressed_index=i, retained_index=j, smaller_coverage=cover, iou=iou,
                                 reason='DUPLICATE_LOCAL_PERSON_OBSERVATION')
                break
        if duplicate is None:
            kept.append(i)
        else:
            suppressed.append(duplicate)
    if vehicles:
        extended=contaminated_extents(detections,kept,vehicles,policy)
        removed={r['suppressed_index'] for r in extended}
        kept=[i for i in kept if i not in removed]
        suppressed.extend(extended)
        redirects={r['suppressed_index']:r['retained_index'] for r in suppressed}
        for record in suppressed:
            target=record['retained_index'];seen=set()
            while target in redirects:
                assert target not in seen,'Cyclic duplicate identity evidence'
                seen.add(target);target=redirects[target]
            record['retained_index']=target
    return sorted(kept), suppressed


class VehicleVisibilityMemory:
    """Prevent a briefly shortened upper-body box from clearing an overlap hold."""
    def __init__(self, policy=TrackingPolicy()):
        self.policy = policy
        self.states = {}

    def update(self, track_id, frame, box, vehicles, contexts=None):
        p = self.policy
        x1, y1, x2, y2 = map(float, box)
        width, height = x2-x1, y2-y1
        aspect = height/width
        overlap = person_vehicle_overlap(box, vehicles)
        state = self.states.setdefault(track_id, dict(held=False, clear=0, last=frame-1, aspects=[], owner=None))
        if frame != state['last']+1:
            state['clear'] = 0
        if contexts is None:
            contexts=[dict(vehicle_context_id=i+1,bbox=list(v),observed=True) for i,v in enumerate(vehicles)]
        relations=[relation(box,c,p) for c in contexts]
        lower_body_contact=any(r['lower_contact'] for r in relations)
        upper_body_contact=any(r['upper_contact'] for r in relations)
        clear_of_vehicles=not lower_body_contact and not upper_body_contact
        owners={alias for c in contexts if c['observed']
                for alias in c.get('observed_alias_ids',[c['vehicle_context_id']])}
        # Keep the binding on a currently measured representative when an
        # overlapping proposal disappears. Otherwise an old alias expires even
        # while the same occlusion region is still observed in every frame.
        direct={c['vehicle_context_id'] for c in contexts if c['observed']}
        if state['owner'] in owners and state['owner'] not in direct:
            owner=next(c for c in contexts if state['owner'] in c.get('observed_alias_ids',[]))
            state['owner']=owner['vehicle_context_id']
        previous_aspect = float(np.quantile(state['aspects'][-15:], .8)) if state['aspects'] else aspect
        shape_shortened = aspect < p.partial_aspect_ratio*previous_aspect
        reason = 'CLEAR_OPTICAL_OBSERVATION'
        if overlap > p.overlap_enter:
            state['held'], state['clear'] = True, 0
            state['owner']=max(relations,key=lambda r:r['overlap'])['vehicle_context_id']
            reason = 'VEHICLE_OVERLAP'
        elif upper_body_contact:
            state['held'],state['clear']=True,0
            state['owner']=max((r for r in relations if r['upper_contact']),key=lambda r:r['horizontal_cover'])['vehicle_context_id']
            reason='VEHICLE_UPPER_BODY_OCCLUSION'
        elif lower_body_contact and shape_shortened:
            state['held'], state['clear'] = True, 0
            state['owner']=max((r for r in relations if r['lower_contact']),key=lambda r:r['horizontal_cover'])['vehicle_context_id']
            reason = 'VEHICLE_OCCLUSION_MEMORY'
        elif state['held']:
            owner_observed=state['owner'] in owners
            if overlap <= p.overlap_exit and clear_of_vehicles and owner_observed:
                state['clear'] += 1
            else:
                state['clear'] = 0
            if state['clear'] >= p.release_observations:
                state['held'] = False
            else:
                reason = 'VEHICLE_OCCLUSION_MEMORY' if owner_observed else 'VEHICLE_CONTEXT_UNAVAILABLE'
        state['aspects'].append(aspect)
        state['last'] = frame
        return dict(vehicle_overlap_fraction=overlap, visibility_status=reason,
                    visibility_hold=state['held'], visibility_clear_streak=state['clear'],
                    lower_body_vehicle_contact=lower_body_contact, shortened_box=shape_shortened,
                    upper_body_vehicle_contact=upper_body_contact,vehicle_context_id=state['owner'],
                    vehicle_context_observed=state['owner'] in owners)


class OpticalPersonTracker:
    """BoT-SORT motion association with shared policy, without a new ReID model."""
    def __init__(self, fps, policy=TrackingPolicy()):
        from ultralytics.trackers.bot_sort import BOTSORT
        import cv2

        class AppearanceBOTSORT(BOTSORT):
            def init_track(inner, results, img=None):
                tracks = super().init_track(results, img)
                if img is None:
                    return tracks
                for track, box in zip(tracks, results.xyxy):
                    x1, y1, x2, y2 = box.astype(float)
                    w, h = x2-x1, y2-y1
                    x1, x2 = max(0, int(x1+.15*w)), min(img.shape[1], int(x2-.15*w))
                    y1, y2 = max(0, int(y1+.05*h)), min(img.shape[0], int(y2-.05*h))
                    if x2 <= x1 or y2 <= y1:
                        continue
                    patch = cv2.cvtColor(img[y1:y2, x1:x2], cv2.COLOR_BGR2HSV)
                    hist = []
                    for band in np.array_split(patch, 2):
                        hh = (cv2.calcHist([band], [0,1,2], None, [8,4,4], [0,180,0,256,0,256]).ravel()
                              if band.size else np.zeros(128, dtype=np.float32))
                        hist.extend(np.sqrt(hh/max(float(hh.sum()), 1.)))
                    track.update_features(np.asarray(hist, dtype=np.float32))
                return tracks

            def get_dists(inner, tracks, detections):
                distances = super().get_dists(tracks, detections)
                # IoU-only confirmation breaks a fast, narrow new box before its
                # velocity can be estimated. Adjacent measured observations can
                # use a bounded, appearance-checked center association instead.
                # No such fallback is allowed across an occlusion gap.
                for i, track in enumerate(tracks):
                    if inner.frame_id-track.end_frame != 1 or track.smooth_feat is None:
                        continue
                    a = track.xyxy; aw, ah = a[2:]-a[:2]
                    for j, detection in enumerate(detections):
                        if detection.curr_feat is None:
                            continue
                        b = detection.xyxy; bw, bh = b[2:]-b[:2]
                        height = max(ah, bh)
                        gap = np.linalg.norm((a[:2]+a[2:]-b[:2]-b[2:])/2)/height
                        similarity = float(np.dot(track.smooth_feat, detection.curr_feat))
                        if (gap <= policy.short_step_center_height_fraction
                                and min(ah,bh)/height >= .65
                                and min(aw,bw)/max(aw,bw) >= .4
                                and abs(a[1]-b[1])/height <= .3
                                and similarity >= policy.short_step_color_similarity):
                            distances[i,j] = min(distances[i,j], .45+.35*gap+.2*(1-similarity))
                return distances
        self.policy = policy
        self.visibility = VehicleVisibilityMemory(policy)
        self.vehicle_tracker = VehicleContextTracker(policy)
        self.vehicle_contexts = []
        args = SimpleNamespace(track_high_thresh=.25, track_low_thresh=.10, new_track_thresh=.25,
                               track_buffer=policy.track_buffer, match_thresh=.8,
                               fuse_score=policy.fuse_detection_confidence_in_association,
                               gmc_method='sparseOptFlow', proximity_thresh=.5, appearance_thresh=.8,
                               with_reid=False, model='auto')
        self.tracker = AppearanceBOTSORT(args, frame_rate=int(round(fps)))

    def update(self, frame, image, detections, vehicles):
        from ultralytics.engine.results import Boxes
        if any(d['confidence'] < .25 for d in detections):
            raise ValueError('This source-index adapter expects the declared confidence >= 0.25 detection cache')
        self.vehicle_contexts=self.vehicle_tracker.update(frame,vehicles)
        current_vehicles=[c['bbox'] for c in self.vehicle_contexts]
        kept, suppression = reconcile_duplicates(detections, self.policy, current_vehicles)
        array = np.asarray([[*detections[i]['bbox'], detections[i]['confidence'], 0] for i in kept], dtype=np.float32).reshape(-1, 6)
        boxes = Boxes(array, image.shape[:2])
        self.tracker.update(boxes, image)
        observations = []
        used = set()
        for track in self.tracker.tracked_stracks:
            if track.frame_id != self.tracker.frame_id:
                continue
            idx = int(track.idx)
            assert 0 <= idx < len(kept)
            original = kept[idx]
            assert original not in used
            used.add(original)
            det = detections[original]
            visibility = self.visibility.update(int(track.track_id), frame, det['bbox'], current_vehicles, self.vehicle_contexts)
            observations.append(dict(source_index=original, track_id=int(track.track_id),
                                     tracking_status='CONFIRMED_OBSERVATION' if track.is_activated else 'TENTATIVE_OBSERVATION',
                                     bbox=list(map(float, det['bbox'])), confidence=det['confidence'], **visibility))
        return observations, suppression, [i for i in kept if i not in used]
