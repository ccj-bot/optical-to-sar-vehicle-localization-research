"""Finite-neighbourhood support hypotheses. No GT, scene, or vehicle score."""
from collections import deque
import numpy as np
from scipy import ndimage as ndi


def shifted(z, dx, dy):
    y = np.clip(np.arange(z.shape[0]) + dy, 0, z.shape[0]-1)
    x = np.clip(np.arange(z.shape[1]) + dx, 0, z.shape[1]-1)
    return z[np.ix_(y, x)]


def crest(z, direction, offsets, epsilon):
    dx, dy = direction; nx, ny = -dy, dx
    yes = np.ones(z.shape, bool)
    for distance in offsets:
        yes &= z > shifted(z, distance*nx, distance*ny) + epsilon
        yes &= z > shifted(z, -distance*nx, -distance*ny) + epsilon
    return yes


def values(z, xy):
    xy = np.asarray(xy, int)
    return z[xy[:, 1], xy[:, 0]].tolist()


def boundary_distance(xy, shape):
    xy = np.asarray(xy)
    return float(min(xy[:, 0].min(), xy[:, 1].min(), shape[1]-1-xy[:, 0].max(), shape[0]-1-xy[:, 1].max()))


def path_in(mask, start, end):
    start = tuple(start); end = tuple(end)
    if not mask[start[1], start[0]] or not mask[end[1], end[0]]:
        return None
    queue = deque([start]); prev = {start: None}; h, w = mask.shape
    while queue:
        x, y = queue.popleft()
        if (x, y) == end:
            result = []; cur = end
            while cur is not None:
                result.append(list(cur)); cur = prev[cur]
            return result[::-1]
        for dx, dy in [(-1,-1), (0,-1), (1,-1), (-1,0), (1,0), (-1,1), (0,1), (1,1)]:
            p = (x+dx, y+dy)
            if 0 <= p[0] < w and 0 <= p[1] < h and mask[p[1], p[0]] and p not in prev:
                prev[p] = (x, y); queue.append(p)
    return None


def local_rank(z, spec):
    q = ndi.percentile_filter(z, spec['percentile'], size=spec['window'], mode='reflect')
    support = z > q  # strict comparison; ties on constant interiors are not support
    labels, _ = ndi.label(support, np.ones((3,3)))
    records = []
    for k, sl in enumerate(ndi.find_objects(labels), 1):
        if sl is None:
            continue
        yy, xx = np.where(labels[sl] == k); yy += sl[0].start; xx += sl[1].start
        xy = np.c_[xx, yy]
        records.append(dict(id=f'Q{k}', type='UNRESOLVED_SUPPORT_REGION', support_xy=xy.tolist(),
                            attributes=dict(local_rank_window=spec['window'], percentile=spec['percentile'],
                                            I0_values=values(z, xy), local_levels=values(q, xy)),
                            uncertainty=['connected_local_rank_support_is_not_ridge', 'component_extent_may_depend_on_outside_links']))
    return records, support, q


def runs(mask, direction):
    dx, dy = direction; h, w = mask.shape; result = []
    for y, x in np.argwhere(mask):
        px, py = x-dx, y-dy
        if 0 <= px < w and 0 <= py < h and mask[py, px]:
            continue
        path = []; xx, yy = int(x), int(y)
        while 0 <= xx < w and 0 <= yy < h and mask[yy, xx]:
            path.append([xx, yy]); xx += dx; yy += dy
        result.append(path)
    return result


def raw_paths(z, fields, spec):
    records = []; arrays = {}; maps = []
    for di, direction in enumerate(spec['directions']):
        scale_masks = {s: crest(f, direction, spec['transverse_offsets'], spec['numeric_epsilon']) for s, f in fields.items()}
        raw = scale_masks[0]; candidate = raw & scale_masks[spec['proposal_sigma']]
        arrays[f'raw_crest_d{di}'] = raw
        arrays[f'candidate_d{di}'] = candidate
        accepted = np.zeros(z.shape, bool)
        for path in runs(candidate, direction):
            if len(path) < spec['minimum_run_pixels']:
                continue
            xy = np.asarray(path); accepted[xy[:,1], xy[:,0]] = True
            dx, dy = direction; nx, ny = -dy, dx
            audit = {}
            for s, field in fields.items():
                flanks = {}
                for d in spec['transverse_offsets']:
                    for sign in [-1, 1]:
                        flanks[f'{sign*d}'] = values(shifted(field, sign*d*nx, sign*d*ny), xy)
                audit[f'I{s}'] = dict(center=values(field, xy), transverse_samples=flanks,
                                     crest_at_each_pixel=values(scale_masks[s], xy))
            records.append(dict(id=f'F{di}_{len(records)}', type='CONTINUOUS_RIDGE',
                semantics_status='local_raw_crest_path_candidate_not_physical_ridge', direction_index=di,
                support_xy=path, path_xy=path, endpoints_xy=[path[0], path[-1]],
                local_shape='digital_straight_run_of_actual_support_pixels', scale_audit=audit,
                attributes=dict(axis_xy=(np.array(direction)/np.linalg.norm(direction)).tolist(),
                                scale_px=1, length_px=(len(path)-1)*float(np.linalg.norm(direction)),
                                I0_min=float(z[xy[:,1],xy[:,0]].min()), neighborhood_halfwidth=4),
                uncertainty=['four_direction_discretization', 'not_vehicle_part', 'no_claim_of_physical_continuity'] +
                            (['boundary_context_incomplete'] if boundary_distance(xy, z.shape) < 9 else [])))
        maps.append(accepted); arrays[f'support_d{di}'] = accepted
    arrays['oriented_support'] = np.any(maps, axis=0)
    return records, arrays


def gap_record(a, b, z, maps):
    endpoints = [(float(np.linalg.norm(np.array(p)-q)), p, q) for p in a['endpoints_xy'] for q in b['endpoints_xy']]
    distance, p, q = min(endpoints, key=lambda item: (item[0], item[1], item[2]))
    steps = int(max(abs(p[0]-q[0]), abs(p[1]-q[1])))
    xy = np.rint(np.linspace(p, q, max(2, steps+1))).astype(int)
    xy = np.unique(xy, axis=0) if distance == 0 else xy
    support = maps[f'candidate_d{a["direction_index"]}']
    missing = xy[~support[xy[:,1], xy[:,0]]]
    profile = values(z, xy)
    valley = int(np.argmin(profile))
    return dict(source=a['id'], target=b['id'], closest_endpoints_xy=[p,q],
                section_xy=xy.tolist(), I0_profile=profile, missing_local_support_xy=missing.tolist(),
                valley_xy=xy[valley].tolist(),
                attributes=dict(endpoint_distance_px=distance, valley_I0=profile[valley]),
                semantics='gap_witness_not_a_bright_bridge; missing_predicate_does_not_alone_mean_darkness')


def support_groups(frags, z, arrays, params, budget):
    if len(frags) > budget['fragments']:
        return [], [], ['STOP_FRAGMENT_BUDGET']
    pairs = []; neighbours = {f['id']: [] for f in frags}; index = {f['id']: f for f in frags}
    for i, a in enumerate(frags):
        axis = np.array(a['attributes']['axis_xy']); normal = np.array([-axis[1], axis[0]])
        ca = np.mean(a['support_xy'], axis=0)
        for b in frags[i+1:]:
            if b['direction_index'] != a['direction_index']:
                continue
            delta = np.mean(b['support_xy'], axis=0)-ca
            if np.linalg.norm(delta) > params['anchor_center_radius_px'] or abs(delta@normal) > params['lateral_tolerance_px']:
                continue
            gap = gap_record(a, b, z, arrays)
            if gap['attributes']['endpoint_distance_px'] > params['endpoint_gap_px']:
                continue
            gap['id'] = f'E{len(pairs)}'; pairs.append(gap)
            neighbours[a['id']].append(b['id']); neighbours[b['id']].append(a['id'])
            if len(pairs) > budget['pair_hypotheses']:
                return [], pairs, ['STOP_PAIR_BUDGET_NO_OBJECT_ASSEMBLY']
    groups = []; seen = set()
    for a in frags:
        ids = tuple(sorted([a['id']] + neighbours[a['id']]))
        if len(ids) < 2 or ids in seen:
            continue
        seen.add(ids)
        xy = np.concatenate([index[i]['support_xy'] for i in ids]); axis = np.array(a['attributes']['axis_xy'])
        extent = float(np.ptp(xy@axis))
        if extent > params['union_extent_px']:
            continue  # limited observation hypothesis, not iterative group trimming
        edges = [p['id'] for p in pairs if p['source'] in ids and p['target'] in ids]
        groups.append(dict(id=f'G{len(groups)}', type='FRAGMENT_GROUP', members=list(ids), gap_witnesses=edges,
                           support_xy=np.unique(xy, axis=0).tolist(),
                           properties=['shared_local_orientation', 'limited_spatial_extent', 'possible_serial_arrangement'],
                           attributes=dict(axis_xy=axis.tolist(), extent_px=extent),
                           uncertainty=['overlapping_alternative_grouping', 'not_transitive_closure',
                                        'dark_gaps_are_not_filled', 'no_vehicle_or_part_semantics']))
    return groups, pairs, []


def old_chord_audit(old, z, arrays, frags):
    """Existence of a raw-supported corridor path, NOT own-quantile labeling."""
    results = []; h,w = z.shape
    for seg in old.get('segments', []):
        xy = np.rint(seg['geometry']['polyline_xy']).astype(int)
        xy[:,0] = np.clip(xy[:,0], 0, w-1); xy[:,1] = np.clip(xy[:,1], 0, h-1)
        line = np.zeros(z.shape, bool); line[xy[:,1], xy[:,0]] = True
        corridor = ndi.binary_dilation(line, iterations=2)
        support = corridor & arrays['oriented_support']; labels, _ = ndi.label(support, np.ones((3,3)))
        yy,xx = np.mgrid[:h,:w]
        zones = [(xx-p[0])**2+(yy-p[1])**2 <= 3**2 for p in [xy[0],xy[-1]]]
        common = (set(labels[zones[0]].tolist()) & set(labels[zones[1]].tolist())) - {0}
        paths = []
        for lab in sorted(common):
            ya,xa = np.argwhere(zones[0] & (labels==lab))[0]; yb,xb = np.argwhere(zones[1] & (labels==lab))[0]
            paths.append(path_in(support, [int(xa),int(ya)], [int(xb),int(yb)]))
        members = []
        for f in frags:
            pts = np.array(f['support_xy'])
            if corridor[pts[:,1],pts[:,0]].any(): members.append(f['id'])
        results.append(dict(old_segment=seg['id'], type='CONTINUOUS_RIDGE' if paths else 'UNSUPPORTED_CHORD',
                            scope='fixed_2px_corridor_3px_endpoint_neighbourhood; not universal truth about the band',
                            chord_xy=xy.tolist(), corridor_support_xy=np.c_[xx[support],yy[support]].tolist(),
                            raw_supported_paths=paths, intersecting_actual_fragments=members,
                            alternative='FRAGMENT_GROUP may express separated fragments; inspect gaps, not forced classification'))
    return results


def build(z, config, old=None):
    z = np.asarray(z, dtype=float); assert z.ndim == 2 and np.isfinite(z).all()
    fields = {0:z}
    for sigma in [1,2,4]:
        fields[sigma] = ndi.gaussian_filter(z, sigma, radius=3*sigma, mode='reflect')
    rank, mask, levels = local_rank(z, config['local_rank'])
    frags, arrays = raw_paths(z, fields, config['oriented'])
    groups, pairs, stops = support_groups(frags, z, arrays, config['group'], config['budgets'])
    obj = dict(rank_regions=rank, fragments=frags, groups=groups, gaps=pairs,
               old_chord_audit=old_chord_audit(old,z,arrays,frags) if old else [],
               uncertainty=['local_support_representation_only']+stops)
    arrays.update({f'I{k}':v for k,v in fields.items()}); arrays['rank_support']=mask; arrays['rank_levels']=levels
    return obj, arrays
