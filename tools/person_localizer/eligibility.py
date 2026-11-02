"""Optical-only input eligibility; no SAR pixels, predictions or references."""
from pathlib import Path
import math
import cv2
import numpy as np
import pandas as pd


def optical_size(spec, optical):
    """Resolve native dimensions from explicit metadata or optical media only."""
    w, h = spec.get('optical_width'), spec.get('optical_height')
    if w is not None and h is not None:
        if not (math.isfinite(float(w)) and math.isfinite(float(h)) and float(w) > 0 and float(h) > 0):
            return None, None, 'INVALID_DECLARED_OPTICAL_DIMENSIONS'
        return float(w), float(h), 'SCENE_OPTICAL_DIMENSIONS'
    video = spec.get('optical_video')
    if not video:
        candidate = str(spec.get('sar_video', '')).replace('_C_R.MP4', '_C.MP4')
        if candidate != str(spec.get('sar_video', '')):
            video = candidate
    if video and Path(video).is_file():
        cap = cv2.VideoCapture(str(video))
        w, h = cap.get(cv2.CAP_PROP_FRAME_WIDTH), cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        cap.release()
        if w > 0 and h > 0:
            return float(w), float(h), 'OPTICAL_VIDEO_METADATA'
    if 'image_path' in optical:
        from PIL import Image
        for p in optical.image_path.dropna().unique():
            if Path(str(p)).is_file():
                with Image.open(p) as im:
                    return float(im.width), float(im.height), 'OPTICAL_IMAGE_METADATA'
    return None, None, 'MISSING_OPTICAL_DIMENSIONS'


def finite(value):
    try:
        return math.isfinite(float(value))
    except (ValueError, TypeError):
        return False


def assess_inputs(optical, spec, config):
    """Return frame/query audits and a positional mask for usable search rows."""
    cfg = config.get('input_gate', {})
    enabled = bool(cfg.get('enabled', False))
    minimum = int(cfg.get('min_usable_observations', config['min_optical_observations']))
    height_limit = float(cfg.get('min_height_fraction', .05))
    aspect_limit = float(cfg.get('min_bbox_aspect_ratio', 1.2))
    margin = float(cfg.get('border_margin_native_px', .5))
    vehicle_gate = cfg.get('vehicle_overlap', {})
    # Optical occlusion is not evidence of SAR invisibility. This opt-in mode
    # retains measured horizontal bearing for mature partial-person tracks,
    # without claiming visible feet, metric range, or person/vehicle separation.
    bearing_only = bool(cfg.get('occluded_bearing_search', {}).get('enabled', False))
    if minimum < 1 or not 0 < height_limit <= 1 or aspect_limit <= 0 or margin < 0:
        raise ValueError('Invalid optical eligibility policy')
    width, height, dimensions_source = optical_size(spec, optical) if enabled else (None, None, 'GATE_DISABLED')
    rg = spec.get('range_gate', {})
    verified_range = enabled and rg.get('status') == 'INDEPENDENTLY_VERIFIED'
    if verified_range:
        if (not str(rg.get('provenance', '')).strip()
                or not finite(rg.get('sar_min_m')) or not finite(rg.get('sar_max_m'))
                or not 0 <= float(rg['sar_min_m']) < float(rg['sar_max_m'])):
            raise ValueError('Verified range gate requires provenance and a valid metric SAR interval')
    frames = []
    for i, row in enumerate(optical.to_dict('records')):
        reasons = []
        hf = aspect = None
        range_state = 'UNVERIFIED_NO_METRIC_RANGE'
        if enabled:
            keys = ['bbox_x1', 'bbox_y1', 'bbox_x2', 'bbox_y2', 'optical_frame', 'sar_frame', 'theta_lo', 'theta_hi']
            if width is None or height is None:
                reasons.append('MISSING_OPTICAL_DIMENSIONS')
            elif not all(finite(row.get(k)) for k in keys):
                reasons.append('MISSING_OR_INVALID_OPTICAL_GEOMETRY')
            else:
                x1, y1, x2, y2 = [float(row[k]) for k in keys[:4]]
                if not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height
                        and float(row['theta_lo']) <= float(row['theta_hi'])):
                    reasons.append('INVALID_OPTICAL_GEOMETRY')
                else:
                    hf, aspect = (y2-y1)/height, (y2-y1)/(x2-x1)
                    if spec.get('optical_tracking_version') == 'refined':
                        if row.get('tracking_status') not in {'TENTATIVE_OBSERVATION', 'CONFIRMED_OBSERVATION'}:
                            reasons.append('TRACKING_EVIDENCE_UNAVAILABLE')
                        if row.get('visibility_status') not in {'CLEAR_OPTICAL_OBSERVATION', 'VEHICLE_OVERLAP', 'VEHICLE_OCCLUSION_MEMORY',
                                                             'VEHICLE_UPPER_BODY_OCCLUSION', 'VEHICLE_CONTEXT_UNAVAILABLE'}:
                            reasons.append('VISIBILITY_EVIDENCE_UNAVAILABLE')
                    if row.get('tracking_status') == 'TENTATIVE_OBSERVATION':
                        reasons.append('TENTATIVE_TRACK_OBSERVATION')
                    if row.get('visibility_status') in {'VEHICLE_OCCLUSION_MEMORY','VEHICLE_UPPER_BODY_OCCLUSION','VEHICLE_CONTEXT_UNAVAILABLE'}:
                        reasons.append(row['visibility_status'])
                    if vehicle_gate.get('enabled',False):
                        overlap=row.get('vehicle_overlap_fraction')
                        if row.get('vehicle_check_status')!='DETECTOR_COMPLETED' or not finite(overlap) or not 0<=float(overlap)<=1:
                            reasons.append('VEHICLE_CHECK_UNAVAILABLE')
                        elif float(overlap)>float(vehicle_gate['max_person_covered_fraction']):
                            reasons.append('VEHICLE_OVERLAP')
                    if aspect < aspect_limit:
                        reasons.append('PARTIAL_OR_NONSTANDING_SUSPECTED')
                    if hf < height_limit:
                        reasons.append('SMALL_OPTICAL_TARGET')
                    if x1 <= margin or y1 <= margin or x2 >= width-margin or y2 >= height-margin:
                        reasons.append('BORDER_CENSORED')
                    if float(row['theta_hi']) < -config['fan_half_angle_deg'] or float(row['theta_lo']) > config['fan_half_angle_deg']:
                        reasons.append('OUTSIDE_INHERITED_BEARING_DOMAIN')
                if verified_range:
                    lo, hi = row.get('range_lower_m'), row.get('range_upper_m')
                    if not finite(lo) or not finite(hi) or not 0 <= float(lo) <= float(hi):
                        range_state = 'MISSING_OR_INVALID_OPTICAL_RANGE_INTERVAL'
                        reasons.append('RANGE_INTERVAL_UNAVAILABLE')
                    else:
                        outside = float(hi) < float(rg['sar_min_m']) or float(lo) > float(rg['sar_max_m'])
                        range_state = 'OUTSIDE_CONFIRMED_RANGE' if outside else 'OVERLAPS_CONFIRMED_RANGE'
                        if outside:
                            reasons.insert(0, 'OUTSIDE_CONFIRMED_RANGE')
        warnings = []
        if bearing_only and row.get('tracking_status') == 'CONFIRMED_OBSERVATION':
            recoverable = {'VEHICLE_OVERLAP', 'VEHICLE_OCCLUSION_MEMORY',
                           'VEHICLE_UPPER_BODY_OCCLUSION', 'PARTIAL_OR_NONSTANDING_SUSPECTED'}
            warnings = [r for r in reasons if r in recoverable]
            reasons = [r for r in reasons if r not in recoverable]
        status = ('EXCLUDE_OUTSIDE_CONFIRMED_RANGE' if 'OUTSIDE_CONFIRMED_RANGE' in reasons
                  else ('HOLD_' + reasons[0] if reasons else 'ELIGIBLE_OPTICAL_FRAME'))
        frames.append(dict(input_row=i, query=row.get('query'), optical_frame=row.get('optical_frame'),
                           sar_frame=row.get('sar_frame'), frame_eligible=not reasons,
                           status=status, reasons=';'.join(reasons), height_fraction=hf, bbox_aspect_ratio=aspect,
                           range_status=range_state, optical_width=width, optical_height=height,
                           dimensions_source=dimensions_source))
        frames[-1]['vehicle_overlap_fraction']=row.get('vehicle_overlap_fraction')
        frames[-1]['vehicle_check_status']=row.get('vehicle_check_status')
        frames[-1]['tracking_status']=row.get('tracking_status')
        frames[-1]['visibility_status']=row.get('visibility_status')
        frames[-1]['bearing_only_search'] = bool(warnings)
        frames[-1]['optical_quality_warnings'] = ';'.join(warnings)
    columns = ['input_row', 'query', 'optical_frame', 'sar_frame', 'frame_eligible', 'status', 'reasons',
               'height_fraction', 'bbox_aspect_ratio', 'range_status', 'optical_width', 'optical_height', 'dimensions_source',
               'vehicle_overlap_fraction','vehicle_check_status','tracking_status','visibility_status',
               'bearing_only_search','optical_quality_warnings']
    frame_audit = pd.DataFrame(frames, columns=columns)
    queries = []
    for q in spec['queries']:
        f = frame_audit[frame_audit['query'].eq(q)]
        usable = f[f.frame_eligible]
        count = int(usable.optical_frame.nunique())
        reasons = sorted({r for codes in f.reasons for r in codes.split(';') if r})
        if not enabled:
            status = 'ELIGIBLE_GATE_DISABLED'
        elif f.empty:
            status = 'HOLD_NO_OPTICAL_OBSERVATIONS'
        elif (f.status == 'EXCLUDE_OUTSIDE_CONFIRMED_RANGE').all():
            status = 'EXCLUDE_OUTSIDE_CONFIRMED_RANGE'
        elif count >= minimum:
            status = 'ELIGIBLE_FOR_SAR_SEARCH'
        elif count:
            status = 'HOLD_INSUFFICIENT_USABLE_OBSERVATIONS'
        else:
            status = str(f.status.value_counts().index[0])
        eligible = status.startswith('ELIGIBLE_')
        fractions = f.height_fraction.dropna()
        queries.append(dict(query=q, input_eligible=eligible, status=status,
                            input_observations=int(f.optical_frame.nunique()), usable_observations=count,
                            required_usable_observations=minimum, reasons=';'.join(reasons),
                            median_height_fraction=float(fractions.median()) if len(fractions) else None,
                            metric_range_verified=bool(verified_range), identity_verified=False))
    query_audit = pd.DataFrame(queries)
    eligible_queries = set(query_audit.loc[query_audit.input_eligible, 'query'])
    mask = frame_audit.frame_eligible.to_numpy(dtype=bool) & frame_audit['query'].isin(eligible_queries).to_numpy()
    return frame_audit, query_audit, mask
