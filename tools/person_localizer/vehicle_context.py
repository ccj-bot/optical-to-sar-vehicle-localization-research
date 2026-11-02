"""Class-agnostic measured vehicle contexts for optical PERSON occlusion gates."""
import numpy as np
from scipy.optimize import linear_sum_assignment


def area(box):
    return max(0., float(box[2]-box[0]))*max(0., float(box[3]-box[1]))


def intersection(a, b):
    return max(0., min(a[2],b[2])-max(a[0],b[0]))*max(0., min(a[3],b[3])-max(a[1],b[1]))


def iou(a, b):
    inter=intersection(a,b)
    return inter/max(1e-9,area(a)+area(b)-inter)


class VehicleContextTracker:
    """Track measured rectangles across COCO class switches; no ghost vehicle boxes.

    A context ID is an association hypothesis, not a confirmed physical identity.
    The largest measured box represents near-duplicate class proposals; geometry
    is never expanded to include people or extrapolated into a missing frame.
    """
    def __init__(self, policy):
        self.policy=policy
        self.tracks={}
        self.next_id=1

    def update(self, frame, boxes):
        p=self.policy;groups=[]
        for i in sorted(range(len(boxes)),key=lambda k:(-area(boxes[k]),k)):
            if area(boxes[i])<=0:raise ValueError('Invalid vehicle rectangle')
            group=None
            for g in groups:
                a,b=boxes[i],g['bbox'];cover=intersection(a,b)/min(area(a),area(b))
                ratio=max(area(a),area(b))/min(area(a),area(b))
                if iou(a,b)>=p.vehicle_duplicate_iou or (cover>=.9 and ratio<=p.vehicle_duplicate_area_ratio):
                    group=g;break
            if group is None:groups.append(dict(bbox=list(map(float,boxes[i])),source_indices=[i],representative_index=i))
            else:group['source_indices'].append(i)
        active=[(tid,t) for tid,t in sorted(self.tracks.items()) if 0<frame-t['last']<=p.vehicle_context_max_gap]
        assignment={}
        if active and groups:
            costs=np.full((len(active),len(groups)),1e6)
            for ti,(tid,t) in enumerate(active):
                previous=np.asarray(t['bbox']);predicted=previous+np.asarray(t['velocity'])*(frame-t['last'])
                for gi,g in enumerate(groups):
                    bb=np.asarray(g['bbox']);ov=iou(predicted,bb)
                    distance=np.linalg.norm((predicted[:2]+predicted[2:]-bb[:2]-bb[2:])/2)
                    scale=max(1.,np.linalg.norm(predicted[2:]-predicted[:2]))
                    size_ratio=min(area(predicted),area(bb))/max(1.,area(predicted),area(bb))
                    if ov>=.15 or (distance/scale<=.25 and size_ratio>=.25):costs[ti,gi]=1-ov+.2*distance/scale
            ii,jj=linear_sum_assignment(costs)
            assignment={j:active[i][0] for i,j in zip(ii,jj) if costs[i,j]<1e5}
        contexts=[]
        for gi,g in enumerate(groups):
            tid=assignment.get(gi)
            if tid is None:
                tid=self.next_id;self.next_id+=1;velocity=np.zeros(4)
            else:
                old=self.tracks[tid]
                velocity=(np.asarray(g['bbox'])-old['bbox'])/(frame-old['last'])
            self.tracks[tid]=dict(bbox=g['bbox'],velocity=velocity.tolist(),last=frame)
            # Two overlapping proposals may alternate as the representative.
            # Preserve their shared observed support for occlusion memory without
            # asserting that the IDs are independently confirmed vehicle objects.
            aliases={tid}
            for previous_id,previous in active:
                predicted=np.asarray(previous['bbox'])+np.asarray(previous['velocity'])*(frame-previous['last'])
                if iou(g['bbox'],previous['bbox'])>=.5 or iou(g['bbox'],predicted)>=.5:
                    aliases.add(previous_id)
            contexts.append(dict(vehicle_context_id=tid,observed_alias_ids=sorted(aliases),observed=True,**g))
        return contexts


def relation(person, context, policy):
    x1,y1,x2,y2=map(float,person);a,b,c,d=context['bbox']
    width,height=x2-x1,y2-y1;vh=d-b
    overlap=intersection(person,context['bbox'])/max(1e-9,area(person))
    horizontal=max(0.,min(x2,c)-max(x1,a))/max(1e-9,width)
    lower_contact=horizontal>=.5 and b-.15*height<=y2<d+policy.vehicle_clearance_fraction*height
    # An upper body just above a car can have IoP=0. This is only a HOLD
    # hypothesis; it does not assert that the person is sitting inside the car.
    upper_contact=(horizontal>=policy.vehicle_upper_horizontal_cover
                   and height<=policy.vehicle_upper_max_height_fraction*vh
                   and b-policy.vehicle_upper_gap_fraction*height<=y2<=b+policy.vehicle_upper_inside_fraction*vh)
    return dict(vehicle_context_id=context['vehicle_context_id'],overlap=float(overlap),
                horizontal_cover=float(horizontal),lower_contact=bool(lower_contact),upper_contact=bool(upper_contact))


def contaminated_extents(detections, kept, vehicles, policy):
    """Identify a wide PERSON box whose extra area is mostly vehicle support.

    Require exactly one enclosed, top-aligned person proposal. Multiple contained
    heads remain ambiguous and are not collapsed into a single person instance.
    """
    removed=[]
    for outer_index in kept:
        outer=detections[outer_index]['bbox'];members=[]
        for inner_index in kept:
            if inner_index==outer_index:continue
            inner=detections[inner_index]['bbox']
            if (area(outer)>=1.5*area(inner)
                    and intersection(outer,inner)/max(1e-9,area(inner))>=policy.duplicate_cover
                    and abs(outer[1]-inner[1])<=policy.duplicate_head_distance*(inner[3]-inner[1])):
                members.append(inner_index)
        if len(members)!=1:continue
        inner_index=members[0];inner=detections[inner_index]['bbox']
        for vehicle in vehicles:
            overlap=intersection(outer,vehicle)/max(1e-9,area(outer))
            extra=(intersection(outer,vehicle)-intersection(inner,vehicle))/max(1e-9,area(outer)-area(inner))
            if overlap>policy.overlap_enter and extra>=policy.vehicle_extent_added_fraction:
                removed.append(dict(suppressed_index=outer_index,retained_index=inner_index,
                    smaller_coverage=intersection(outer,inner)/area(inner),iou=iou(outer,inner),
                    extra_vehicle_fraction=float(extra),reason='VEHICLE_CONTAMINATED_PERSON_EXTENT'))
                break
    return removed
