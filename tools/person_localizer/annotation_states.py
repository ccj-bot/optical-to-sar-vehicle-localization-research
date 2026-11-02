"""Registration diagnostics and image visibility for annotation outputs.

These fields describe usable image evidence. A current response is not an
automatic human approval, and a review-budget exceedance is not target error.
Coordinates and raw model response flags are preserved.
"""
import math
from pathlib import Path

import numpy as np
import pandas as pd

from .visibility_lifecycle import ImageVisibilityLifecycle, VisibilityPolicy


def registration_quality(models, frames, policy=None, anchor=None):
    policy = policy or {}
    budget = policy.get('max_holdout_p90_work_px')
    step_budget = policy.get('max_step_per_sar_frame_work_px')
    for value in (budget, step_budget):
        if value is not None and (not math.isfinite(value) or value <= 0):
            raise ValueError('Registration review budgets must be finite and positive')
    result = {}; previous = None; reference_broken = False
    for f in sorted(map(int, frames)):
        m = models.get(f, {})
        delta = np.asarray(m.get('delta', [np.nan, np.nan]), dtype=float)
        valid = delta.shape == (2,) and np.isfinite(delta).all()
        p90 = m.get('holdout_p90')
        held = int(m.get('holdout_points', 0))
        step = None
        if valid and previous is not None:
            pf, pd = previous
            step = float(np.linalg.norm(delta-pd)/(f-pf))
        if m.get('reference_revalidated', False):
            reference_broken = False
        if step_budget is not None and step is not None and step > step_budget:
            reference_broken = True
        if m.get('status') != 'FIT' or not valid:
            status, coherent = 'REGISTRATION_UNAVAILABLE', False
        elif reference_broken:
            status, coherent = 'REFERENCE_DISCONTINUITY', False
        elif f == anchor and p90 == 0:
            status, coherent = 'ANCHOR_REFERENCE', True
        elif p90 is None or not math.isfinite(p90) or held == 0:
            status, coherent = 'NO_HELDOUT_VALIDATION', False
        elif budget is None:
            status, coherent = 'REVIEW_BUDGET_UNSPECIFIED', False
        elif p90 > budget:
            status, coherent = 'EXCEEDS_REVIEW_BUDGET', False
        else:
            status, coherent = 'WITHIN_REVIEW_BUDGET', True
        result[f] = dict(registration_fit_status=m.get('status','MISSING'),
            registration_quality_status=status, registration_coherent=coherent,
            registration_holdout_p90_work_px=p90,
            registration_holdout_points=held, registration_fit_points=int(m.get('fit_points',0)),
            registration_step_work_px_per_frame=step,
            registration_reference_break_latched=reference_broken,
            registration_quality_method=m.get('method','ANCHOR_KLT'),
            registration_review_budget_work_px=budget)
        previous = (f,delta) if valid else None
    return result


def annotate_predictions(scene, predictions, quality, source_last_frame, metadata=None):
    """Add visibility/review fields without changing x/y or current_SAR_update.

    `metadata` is only needed by an engine without measured optical columns.
    The caller may export these results separately for legacy engine compatibility.
    """
    options = scene.cfg.get('annotation_output', {})
    if not options.get('enabled', False):
        return predictions
    policy = VisibilityPolicy(**options.get('visibility', {}))
    out = predictions.copy()
    group_keys = ['variant','query'] if 'variant' in out else ['query']
    updates = {}
    for _, rows in out.groupby(group_keys, sort=False):
        rows = rows.sort_values('sar_frame')
        query = rows.iloc[0]['query']
        optical = scene.opt[scene.opt['query'].eq(query)]
        first_opt = int(optical.optical_frame.min()) if len(optical) else None
        first_frame, last_frame = int(rows.sar_frame.min()), int(rows.sar_frame.max())
        life = ImageVisibilityLifecycle(policy)
        earlier_observed = bool(len(optical) and (optical.sar_frame < first_frame).any())
        if earlier_observed:
            life.started = True; life.episode = 1
        seen_observations = set()
        for ix, row in rows.iterrows():
            f = int(row.sar_frame)
            meta = metadata(scene, query, f) if metadata else {}
            observed = bool(row.get('optical_measured',meta.get('measured',False)))
            hold = bool(row.get('input_hold',meta.get('hold',False)))
            eligible = bool(row.get('optical_eligible',meta.get('eligible',False)))
            of = int(row.get('optical_frame',round(f/scene.spec['sar_fps']*scene.spec['optical_fps'])))
            observation = f'{query}:OPT:{of}'
            fresh = observed and observation not in seen_observations
            if observed: seen_observations.add(observation)
            xy = np.array([row.x,row.y],dtype=float)
            work = (xy+.5)/scene.scale-.5
            d = work-scene.origin
            finite = bool(np.isfinite(d).all())
            radius = float(np.linalg.norm(d)) if finite else float('nan')
            angle = float(np.degrees(np.arctan2(d[0],-d[1]))) if finite else float('nan')
            coordinate_valid = finite and scene.cfg['minimum_radius_work_px'] < radius < scene.radius
            inside = coordinate_valid and abs(angle) <= policy.half_angle_deg
            if options.get('use_rendered_support', False):
                masks = getattr(scene,'rendered_support',{})
                if f not in masks: raise RuntimeError(f'ANNOTATION_RENDERED_SUPPORT_MISSING:{f}')
                px,py = np.rint(work).astype(int) if finite else (-1,-1)
                inside = bool(inside and 0<=px<scene.w and 0<=py<scene.h and masks[f][py,px])
            registration = quality.get(f, dict(registration_fit_status='MISSING',
                registration_quality_status='REGISTRATION_UNAVAILABLE',registration_coherent=False))
            current = bool(row.current_SAR_update)
            state = life.update(f,angle,fresh,current,position_valid=coordinate_valid,
                input_hold=hold,transport_coherent=registration['registration_coherent'])
            source_start = bool(first_opt==0)
            started_event = state['entry_event']
            if source_start: state['entry_event']=False
            marker = bool(state['visibility_marker'] and inside)
            visible_current = bool(marker and current and not hold)
            if not life.started: label='NOT_YET_OBSERVED'
            elif life.outside_latched: label='OUTSIDE_IMAGE_HYPOTHESIS'
            elif hold: label='INPUT_HOLD'
            elif not registration['registration_coherent']: label='REGISTRATION_REVIEW'
            elif not inside: label='POSITION_OUTSIDE_SUPPORT'
            elif visible_current: label='CURRENT_SAR_RESPONSE'
            else: label='TEMPORAL_INFERRED'
            updates[ix] = {**registration, **state,
                'optical_measured':observed, 'optical_eligible':eligible, 'input_hold':hold,
                'optical_observation_fresh':fresh,'episode_started':started_event,
                'source_start_censored':source_start,
                'run_start_left_censored':earlier_observed,
                'in_image_support':inside,'annotation_state':label,
                'annotation_marker':marker,'annotation_current_response':visible_current,
                'annotation_review_required':label in {'INPUT_HOLD','REGISTRATION_REVIEW','POSITION_OUTSIDE_SUPPORT','TEMPORAL_INFERRED'},
                'candidate_marker':bool(life.started and not life.outside_latched and inside),
                'human_review_status':'UNREVIEWED',
                'current_response_visible':visible_current,
                'source_end_censored':bool(f==source_last_frame and life.started and not life.outside_latched),
                'segment_end_open':bool(f==last_frame and last_frame<source_last_frame and life.started and not life.outside_latched)}
        updates[rows.index[-1]]['terminal_state']=(life.terminal() if last_frame==source_last_frame else
            'SEGMENT_END_OPEN' if life.started and not life.outside_latched else life.terminal())
    derived = pd.DataFrame.from_dict(updates,orient='index')
    for col in derived: out[col] = derived[col]
    # Preserve the older output decision for transparent state-only comparison.
    if 'definite_point' in out:
        out['model_definite_point'] = out.definite_point
        out['definite_point'] = out.annotation_current_response & out.optical_eligible
    return out


def write_annotation_export(predictions, output):
    """One point/state table for the annotation UI; no invented body envelope."""
    if 'annotation_state' not in predictions:
        return
    selected=predictions[predictions.variant.eq('temporal_map')].copy() if 'variant' in predictions else predictions.copy()
    if 'scene' not in selected and 'scene_id' in selected:selected['scene']=selected.scene_id
    columns=['scene','query','sar_frame','optical_frame','x','y','current_SAR_update',
        'annotation_state','annotation_marker','candidate_marker','annotation_current_response',
        'annotation_review_required','human_review_status','input_hold','optical_measured',
        'registration_quality_status','registration_holdout_p90_work_px','visibility_status',
        'visibility_episode','source_start_censored','source_end_censored','segment_end_open',
        'terminal_state','identity_verified']
    selected.reindex(columns=columns).to_csv(Path(output)/'ANNOTATIONS.csv',index=False)
