"""Optical vehicle overlap evidence, independent of SAR and target references."""
from pathlib import Path
import cv2,pandas as pd

def person_vehicle_overlap(person,vehicles):
    x1,y1,x2,y2=map(float,person);area=(x2-x1)*(y2-y1)
    if area<=0:return 0.
    overlaps=[]
    for vehicle in vehicles:
        a,b,c,d=map(float,vehicle)
        overlaps.append(max(0.,min(x2,c)-max(x1,a))*max(0.,min(y2,d)-max(y1,b))/area)
    return max(overlaps,default=0.)

def attach_vehicle_evidence(optical,spec,config,out):
    gate=config.get('input_gate',{}).get('vehicle_overlap',{})
    if not gate.get('enabled',False):return optical
    path=spec.get('vehicle_evidence_csv')
    if path:
        evidence=pd.read_csv(path)
    else:
        from ultralytics import YOLO
        model=YOLO(gate['weights']);video=spec.get('optical_video')
        if not video:video=str(spec['sar_video']).replace('_C_R.MP4','_C.MP4')
        cap=cv2.VideoCapture(video);records=[]
        wanted=optical[optical['query'].isin(spec['queries'])]
        for frame,g in wanted.groupby('optical_frame',sort=True):
            cap.set(cv2.CAP_PROP_POS_FRAMES,int(frame));ok,image=cap.read()
            if not ok:
                boxes=[];status='SOURCE_UNAVAILABLE'
            else:
                pred=model.predict(image,classes=gate['class_ids'],conf=gate['confidence'],imgsz=gate['image_size'],device=gate.get('device',0),verbose=False)[0]
                boxes=pred.boxes.xyxy.cpu().numpy().tolist();status='DETECTOR_COMPLETED'
            for row in g.itertuples():
                records.append(dict(query=row.query,optical_frame=int(frame),vehicle_check_status=status,
                    vehicle_overlap_fraction=person_vehicle_overlap([row.bbox_x1,row.bbox_y1,row.bbox_x2,row.bbox_y2],boxes)))
        cap.release();evidence=pd.DataFrame(records)
    keys=['query','optical_frame']
    assert not evidence.duplicated(keys).any(),'Ambiguous vehicle evidence keys'
    cols=keys+['vehicle_check_status','vehicle_overlap_fraction']
    result=optical.drop(columns=['vehicle_check_status','vehicle_overlap_fraction'],errors='ignore').merge(evidence[cols],on=keys,how='left',validate='many_to_one',sort=False)
    evidence[cols].to_csv(Path(out)/'VEHICLE_EVIDENCE_USED.csv',index=False)
    return result
