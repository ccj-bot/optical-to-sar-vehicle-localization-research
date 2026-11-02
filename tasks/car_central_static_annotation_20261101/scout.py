from pathlib import Path
import json,sys,hashlib
from collections import Counter
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'output/car_central_static_annotation_20261101'
FRAMES=ROOT/'output/pseudocolor_labelstudio_prep_20260722/frames'
FONT='C:/Windows/Fonts/msyh.ttc'
def font(n=24):return ImageFont.truetype(FONT,n)
def write(name,obj):
    (OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
def indexed(scene,sensor):
    return {int(p.name.split('_')[1]):p for p in (FRAMES/sensor/scene).glob('frame_*.jpg')}
def main():
    OUT.mkdir(exist_ok=False)
    (OUT/'scout').mkdir()
    cohort_path=ROOT/'output/vehicle50_size_trace_20261026/FINAL_COHORT_50.json'
    cohort=json.loads(cohort_path.read_text(encoding='utf-8-sig'))
    counts=Counter(v['scene'] for v in cohort['vehicles'])
    inventory=[]
    for scene,count in sorted(counts.items()):
        sar=indexed(scene,'sar_pseudocolor');opt=indexed(scene,'optical')
        selected=[sorted(sar)[round((len(sar)-1)*t)] for t in [0.2,0.5,0.8]]
        im=Image.new('RGB',(1536,980),'#f3f5f7');d=ImageDraw.Draw(im)
        d.text((16,10),f'{scene} | 原图序列抽览 | 旧候选{count}条（不按旧框决定新样本）',font=font(25),fill='#132d4a')
        rows=[]
        for j,f in enumerate(selected):
            of=min(opt,key=lambda k:abs(k/18-f/30));x=j*512
            d.text((x+8,55),f'OPT {of} / SAR {f}',font=font(22),fill='#132d4a')
            oi=Image.open(opt[of]).convert('RGB');si=Image.open(sar[f]).convert('RGB')
            im.paste(oi.resize((512,288)),(x,90));im.paste(si.resize((512,296)),(x,410))
            # Native central crop for initial visible structure, not a box.
            im.paste(si.crop((250,120,774,392)).resize((512,266)),(x,714))
            rows.append({'sar_frame':f,'sar_source':str(sar[f]),'optical_frame':of,'optical_source':str(opt[of])})
        im.save(OUT/'scout'/f'{scene}.png')
        inventory.append({'scene':scene,'existing_candidate_count':count,'sar_frame_count':len(sar),
            'optical_frame_count':len(opt),'sar_range':[min(sar),max(sar)],'optical_range':[min(opt),max(opt)],
            'review_frames':rows,'static_and_complete_vehicle_population':'TO_BE_ASSIGNED_FROM_SEQUENCE_REVIEW'})
    write('SCENE_INVENTORY.json',inventory)
    write('USER_CORRECTION.json',{'date':'2026-11-01','confirmed_optical_groups':[
        {'subject':'003','panels':[1,2,3,4],'meaning':'SAME_PHYSICAL_CAR_IN_DISPLAYED_OPTICAL_IMAGES'},
        {'subject':'004','panels':[5,6],'meaning':'ANOTHER_SAME_PHYSICAL_CAR_IN_DISPLAYED_OPTICAL_IMAGES'}],
        'previous_review_queue_priority':'SUPERSEDED',
        'primary_goal':'静止车辆；存在完整入画时段；优先中部车辆连续标注',
        'next_goal':'完整车辆情况下的时序预测','later_mechanisms':['扇面边缘','近场'],
        'user_instruction':'不要过于保守防御，发挥创新性，不要叠加层层保护'})
    sar=indexed('R35ZF','sar_pseudocolor');opt=indexed('R35ZF','optical')
    sf=[0,60,120,180,240,270,300,330,358,390,420,450,480,494]
    for page in range(4):
        times=sf[page*4:page*4+4]
        im=Image.new('RGB',(2048,1300),'#f3f5f7');d=ImageDraw.Draw(im)
        for j,f in enumerate(times):
            x=(j%2)*1024;y=(j//2)*650
            d.text((x+12,y+8),f'R35 SAR {f} | 无框完整原图',font=font(27),fill='#132d4a')
            im.paste(Image.open(sar[f]).convert('RGB'),(x,y+50))
        im.save(OUT/'scout'/f'R35_FULL_{page+1}.png')
    for j,f in enumerate([180,215,250,275,297]):
        im=Image.open(opt[f]).convert('RGB')
        im.save(OUT/'scout'/f'OPT_{f}.png')
    print(json.dumps({'scenes':dict(counts),'out':str(OUT)},ensure_ascii=False))

if __name__=='__main__':main()
