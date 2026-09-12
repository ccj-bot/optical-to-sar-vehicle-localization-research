from pathlib import Path
import json,csv,cv2,numpy as np
from PIL import Image,ImageDraw
W=Path('D:/profile/research/workspace');O=W/'output/tpgt/phase_1a'
D=json.loads((O/'audit/study_source_details.json').read_text(encoding='utf-8'))
choices=[('E1A_899fea6cb26d4a25','clean_complete_anchor_candidate','R35 continuous large optical CAR; visible front/body at opening followed by boundary exit. Optical-only anchor; physical completeness remains UNKNOWN.'),('E1A_fb9b2b8ac5504522','ordinary','R02 CAR with ordinary small optical scale and several explicit observation gaps.'),('E1A_d0a799aebda9689f','weak_stress','R01 large optical bbox contacting image boundary during much of its short observed interval.'),('E1A_3520f2a29d6f636f','clean_complete_anchor_candidate','R01 sustained large optical PERSON observations; inspect interior full-body views and boundary exit; completeness UNKNOWN.'),('E1A_c994e59a370a09b4','ordinary','R03 moderate optical PERSON scale and continuous short observation range near recording end.'),('E1A_79b0263a150b69e3','weak_stress','R02 small optical PERSON hypothesis with 11 observed frames across five disjoint support ranges.')]
queue=[]; canvas=Image.new('RGB',(1440,len(choices)*300),'#101820');dr=ImageDraw.Draw(canvas)
for n,(eid,role,reason) in enumerate(choices):
    d=D[eid]; e=d['event']; rr=sorted(d['optical_rows'],key=lambda r:int(r['frame_index']))
    queue.append({'study_order':n+1,'event_hypothesis_id':eid,'domain':e['domain'],'run_id':e['run_id'],'source_identity':e['source_identity'],'study_role':role,'selection_basis':reason,'completeness_status':'UNKNOWN_PENDING_FULL_FRAME_REVIEW','evidence_pack':f'evidence_packs/{eid}/OBSERVATION_VIEW.html'})
    for j,idx in enumerate([0,len(rr)//2,len(rr)-1]):
        r=rr[idx];im=cv2.imdecode(np.fromfile(r['optical_image_path'],dtype=np.uint8),cv2.IMREAD_COLOR)
        if im is None:raise RuntimeError(r['optical_image_path'])
        b=[int(float(r[k])) for k in ['bbox_x1','bbox_y1','bbox_x2','bbox_y2']];cv2.rectangle(im,tuple(b[:2]),tuple(b[2:]),(0,220,255),6)
        im=cv2.resize(im,(480,270));canvas.paste(Image.fromarray(cv2.cvtColor(im,cv2.COLOR_BGR2RGB)),(j*480,n*300+30))
        dr.text((j*480+6,n*300+6),f'{e["source_identity"]} F{r["frame_index"]} / {role}',fill='white')
canvas.save(O/'audit/queue_optical_preselection.jpg',quality=92)
with (O/'study_queue.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(queue[0]));w.writeheader();w.writerows(queue)
(O/'audit/queue_selection_basis.json').write_text(json.dumps({'inputs':['C_IDS source identity','P_TRACKS source identity','C_FRAMES optical bbox/frame','P_DET optical bbox/frame','C_RUNS acquisition metadata'],'queue':queue,'sar_quality_used':False,'manual_sar_reference_used':False,'accepted_tier_used':False,'status':'OPTICAL_ONLY_PRESELECTION_FOR_VISUAL_CHECK'},ensure_ascii=False,indent=2),encoding='utf-8')
print('Queue written; optical-only visual preview ready.')
