from review import *
from datetime import datetime
from zoneinfo import ZoneInfo
import shutil

TASK=ROOT/'tasks/car_central_static_repair_20261102'
for name in ['RUN.md','VISUAL_REVIEW.md']:shutil.copyfile(TASK/name,OUT/name)
f=494;old=json.loads((OLD/'ANNOTATIONS.json').read_text(encoding='utf-8'))['records'];new=json.loads((OUT/'ANNOTATIONS.json').read_text(encoding='utf-8'))['records']
crop=(460,145,860,465);w,h=400,320
panel=Image.new('RGB',(800,380),'#edf3f7');d=ImageDraw.Draw(panel)
for i,(label,rows,dashed) in enumerate([('旧版 v1',old,False),('修订 v2',new,True)]):
    im=Image.fromarray(source().image('SAR',f));draw=ImageDraw.Draw(im)
    for r in rows:
        if r['sar_frame']!=f:continue
        b=r['sar_box'];c=native_corners(*(b[k] for k in ['cx','cy','width','height','rotation_deg']));s=r['subject_id']
        for a,z in zip(c,np.roll(c,-1,axis=0)):
            if dashed:
                length=np.linalg.norm(z-a)
                for pos in np.arange(0,length,9):draw.line((tuple(a+(z-a)*pos/length),tuple(a+(z-a)*min(pos+5,length)/length)),fill=COLORS[s],width=2)
            else:draw.line((tuple(a),tuple(z)),fill=COLORS[s],width=2)
        draw.text((b['cx']-15,b['cy']-10),s,font=font(16),fill=COLORS[s],stroke_width=1,stroke_fill='#102637')
    panel.paste(im.crop(crop),(i*w,36));d.text((i*w+12,5),'SAR494 | '+label,font=font(18),fill='#152c3b')
d.text((10,359),'同一原图、同一裁剪；修订框长宽仍继承358原人工参考',font=font(13),fill='#314d60');panel.save(OUT/'LAST_FRAME_COMPARE.png')
files=[p for p in OUT.rglob('*') if p.is_file() and p.name!='DELIVERY_MANIFEST.json']
codes=[p for p in TASK.rglob('*') if p.is_file()]
def entry(p):return {'path':str(p),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
dump(OUT/'DELIVERY_MANIFEST.json',{'created':datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'status':'REVIEWABLE_REVISION_COMPLETE_WITH_INHERITED_EXTENT_LIMIT','files':[entry(p) for p in files],'task_sources':[entry(p) for p in codes],
    'entry':str(OUT/'index.html'),'user_confirmed_new_temporal_boxes':0,'independent_accuracy_established':False})
print(json.dumps({'files':len(files),'code_and_notes':len(codes),'entry':str(OUT/'index.html'),'preview':str(OUT/'LAST_FRAME_COMPARE.png')},ensure_ascii=False))
