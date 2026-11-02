"""Build separately versioned, assistant-reviewable R35 continuous annotations."""
from review import *
from datetime import datetime
from zoneinfo import ZoneInfo
import cv2

KEYS=[358,370,380,390,400,410,420,430,440,450,460,470,480,486,490,494]
data=source();old=json.loads((OLD/'ANNOTATIONS.json').read_text(encoding='utf-8'))['records']
old_by={(r['subject_id'],r['sar_frame']):r for r in old}
nav=json.loads((OUT/'diagnostics'/'local_rigid_navigation.json').read_text(encoding='utf-8'))['variants']
primary={s:{r['frame']:r for r in rs} for s,rs in nav['100'].items()}
sensitivity={s:{r['frame']:r for r in rs} for s,rs in nav['160'].items()}
rows=[];deltas=[]
for f in range(358,495):
    for s in ['002','003','005']:
        b=dict(primary[s][f]['box']);prior=old_by[s,f]['sar_box'];alt=sensitivity[s][f]['box']
        rows.append({'scene':'R35ZF','subject_id':s,'name':NAMES[s],'sar_frame':f,
            'timestamp_ms_nominal':data.frame('SAR',f)['timestamp_ms_nominal'],
            'coordinate_space':'SAR_RAW_NATIVE_1024x592','sar_box':b,
            'annotation_author':'USER' if f==358 else 'CODEX_ASSISTANT',
            'user_confirmed_this_frame':f==358,
            'frame_role':'USER_ANCHOR' if f==358 else ('ASSISTANT_REVIEW_KEYFRAME' if f in KEYS else 'PROPAGATED_FRAME_FOR_SEQUENCE_REVIEW'),
            'position_and_axis_source':'USER_SAR358_REFERENCE' if f==358 else 'ADJACENT_MULTI_STRUCTURE_LOCAL_RIGID_NAVIGATION_WITH_ASSISTANT_VISUAL_REVIEW',
            'extent_source':'USER_SAR358_DIMENSIONS_RETAINED_NOT_REMEASURED',
            'boundary_visibility':'COMPLETE_SOURCE_REFERENCE' if f==358 else 'NEAR_END_RESPONSE_OBSERVED_FAR_EXTENT_INHERITED',
            'review_state':'SOURCE_USER_REFERENCE' if f==358 else 'PENDING_ASSISTANT_SEQUENCE_REVIEW',
            'motion_class':'STATIC_PARKED','physical_identity_claim':'SOURCE_ID_CONTINUITY_REVIEW_NOT_NEW_INDEPENDENT_PROOF',
            'image_path':data.frame('SAR',f)['image_path'],
            'navigation_correspondences':primary[s][f]['correspondences'],
            'neighborhood_sensitivity_px':float(np.hypot(b['cx']-alt['cx'],b['cy']-alt['cy'])),
            'source_annotation_pointer':old_by[s,358].get('source_pointer'),
            'source_reference_record':f'{OLD.as_posix()}/ANNOTATIONS.json#subject={s},frame=358'})
        deltas.append({'subject':s,'frame':f,'center_change_xy':[b['cx']-prior['cx'],b['cy']-prior['cy']],
                       'angle_change_deg':b['rotation_deg']-prior['rotation_deg'],
                       'interpretation':'REVISION_DIFFERENCE_NOT_MEASURED_ERROR'})
byframe={f:[r for r in rows if r['sar_frame']==f] for f in range(358,495)}

def draw_box(d,b,color,width=2,dashed=False,label=None):
    c=native_corners(*(b[k] for k in ['cx','cy','width','height','rotation_deg']))
    for i,(a,z) in enumerate(zip(c,np.roll(c,-1,axis=0))):
        if dashed:
            length=np.linalg.norm(z-a)
            for pos in np.arange(0,length,9):
                p=a+(z-a)*pos/length;q=a+(z-a)*min(pos+5,length)/length
                d.line((tuple(p),tuple(q)),fill=color,width=width)
        else:d.line((tuple(a),tuple(z)),fill=color,width=width)
    if label:d.text((b['cx']-14,b['cy']-12),label,font=font(18),fill=color,stroke_width=2,stroke_fill='#0a1925')

def render(f,mode='new',footer=True):
    im=Image.fromarray(data.image('SAR',f));d=ImageDraw.Draw(im)
    for r in byframe[f]:
        s=r['subject_id'];b=r['sar_box'] if mode=='new' else old_by[s,f]['sar_box']
        draw_box(d,b,COLORS[s],width=2,label=s,dashed=(mode=='new' and f!=358))
    if footer:
        canvas=Image.new('RGB',(1024,664),'#102637');canvas.paste(im,(0,0));d=ImageDraw.Draw(canvas)
        heading='修订 v2' if mode=='new' else '旧版 v1：后段偏移对照'
        d.text((16,601),f'SAR {f}  |  {heading}  |  002 白色SUV   003 灰色轿车   005 橙色车',font=font(18),fill='white')
        d.text((16,633),'虚线：助手修订的整体参考范围；长宽沿用358，弱远端未独立重测' if mode=='new' else '原有短亮带中点平移＋固定姿态；保留旧结果用于对照',font=font(16),fill='#cbdce7')
        return canvas
    return im

def main():
    if (OUT/'ANNOTATIONS.json').exists():raise FileExistsError('Preserve existing revision; create a new version instead')
    for directory in ['sar_frames','compare_frames','keyframes','sequence_review']:(OUT/directory).mkdir(parents=True,exist_ok=True)
    for f in range(358,495):
        new=render(f);new.save(OUT/'sar_frames'/f'{f:06d}.jpg',quality=93)
        compare=Image.new('RGB',(2048,664));compare.paste(render(f,'old'),(0,0));compare.paste(new,(1024,0));compare.save(OUT/'compare_frames'/f'{f:06d}.jpg',quality=93)
        if f in KEYS:compare.save(OUT/'keyframes'/f'COMPARE_{f}.png')
    review_pages=[]
    fs=list(range(358,495))
    for page,start in enumerate(range(0,len(fs),12)):
        group=fs[start:start+12];w,h=400,320
        sheet=Image.new('RGB',(3*w,4*(h+25)),'#eff3f6');d=ImageDraw.Draw(sheet)
        for i,f in enumerate(group):
            centers=np.array([[r['sar_box']['cx'],r['sar_box']['cy']] for r in byframe[f]])
            left=round(centers[:,0].mean())-200;top=145
            im=render(f,footer=False).crop((left,top,left+w,top+h));x,y=(i%3)*w,(i//3)*(h+25);sheet.paste(im,(x,y+25));d.text((x+6,y+2),f'SAR {f} | x{left}:{left+w} y145:465',font=font(15),fill='#182e3d')
        p=OUT/'sequence_review'/f'PAGE_{page+1:02d}_{group[0]}_{group[-1]}.png';sheet.save(p);review_pages.append({'page':page+1,'frames':group,'path':str(p),'inspection_status':'PENDING'})
    dump(OUT/'ANNOTATIONS.json',{'schema':'CENTRAL_STATIC_CAR_REPAIR_V2','created':datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'scene':'R35ZF','subjects':['002','003','005'],'frames':[358,494],
        'status':'PENDING_ASSISTANT_SEQUENCE_REVIEW','method':'Source-reference initialization; per-frame local rigid image navigation; visual review; no body shrinkage from fading response.',
        'extent_limit':'Original358 width/height are retained. Full-body far edges are not independently observed in all frames. This is a repaired approximate annotation, not newly user-confirmed truth.',
        'records':rows})
    dump(OUT/'KEYFRAME_REVISIONS.json',[r for r in rows if r['sar_frame'] in KEYS])
    dump(OUT/'REVISION_DIFFERENCES.json',deltas)
    dump(OUT/'SEQUENCE_REVIEW.json',{'status':'PENDING','pages':review_pages,'source_frame_count':137,'object_frame_count':411})
    print(json.dumps({'frames':137,'rows':411,'keyframes':len(KEYS),'review_pages':len(review_pages),'output':str(OUT)},ensure_ascii=False))

if __name__=='__main__':main()
