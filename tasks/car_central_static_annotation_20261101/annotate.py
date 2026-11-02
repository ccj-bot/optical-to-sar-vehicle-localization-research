"""First central stationary-car sequence: native visual keyframes + interpolation.

Endpoint coordinates below are explicit coarse image readings authored after
viewing CENTRAL_NATIVE_1/2. Endpoints navigate the user-given whole-body extent.
They do not claim that every whole-body edge is radiometrically visible.
"""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import json,sys,hashlib,subprocess,shutil
import numpy as np
import cv2
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'output/car_central_static_annotation_20261101'
PKG=ROOT/'output/car_data_contract_r35_20261030'
sys.path.insert(0,str(PKG/'runtime'))
from car_data_contract import CarDataset
from car_data_contract.geometry import native_corners

TIMES=[358,380,400,420,440,460,480,494]
# Left/upstream and right/downstream endpoints of the short near-end response.
# Native x-right/y-down pixels, not a subpixel fit or image-score optimum.
SEGMENTS={
 '002':[[330,412,382,381],[363,416,410,384],[403,419,449,387],[438,422,481,395],
        [475,421,520,393],[518,421,560,394],[558,421,600,395],[587,417,628,391]],
 '003':[[399,374,446,350],[434,376,480,352],[469,380,515,354],[495,382,544,354],
        [530,383,580,356],[570,383,617,357],[612,387,659,359],[642,384,687,359]],
 '005':[[460,338,507,312],[489,338,538,312],[535,337,579,312],[568,337,613,314],
        [604,337,648,315],[646,337,687,315],[683,339,723,318],[711,339,754,319]],
}
NAMES={'002':'白色SUV','003':'灰色轿车','005':'橙色车'}
COLORS={'002':'#ffff4f','003':'#ef7cfa','005':'#35f7b1'}
FONT_PATH='C:/Windows/Fonts/msyh.ttc'
def font(n=20):return ImageFont.truetype(FONT_PATH,n)
def dump(name,obj):
    (OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def label_sar(im,rows,frame,*,show_segments=False):
    im=im.copy();d=ImageDraw.Draw(im)
    for r in rows:
        s=r['subject_id'];b=r['sar_box'];corn=native_corners(*(b[k] for k in ['cx','cy','width','height','rotation_deg']))
        d.line([tuple(p) for p in np.vstack([corn,corn[:1]])],fill=COLORS[s],width=2)
        x,y=int(b['cx']),int(b['cy'])
        d.text((x-18,y-13),s,font=font(22),fill=COLORS[s],stroke_width=2,stroke_fill='#07182b')
        if show_segments:
            seg=r['sar_end_support_xyxy'];d.line([tuple(seg[:2]),tuple(seg[2:])],fill='white',width=3)
            for p in [seg[:2],seg[2:]]:d.ellipse((p[0]-3,p[1]-3,p[0]+3,p[1]+3),fill='white')
    return im
def main():
    if (OUT/'ANNOTATIONS.json').exists():raise FileExistsError('Annotation version exists; preserve it')
    data=CarDataset(PKG,view='review')
    refs=data.references();anchors={r['manual_target_id'][-3:]:r for r in refs.to_dict('records')}
    source_snapshot=ROOT/'output/manual_guided_localization_20261027/CURRENT_USER_BROWSER_ANNOTATIONS.json'
    original_snapshot_hash=sha(source_snapshot)
    originals={s:{k:float(anchors[s]['sar_raw_'+k]) for k in ['cx','cy','width','height','rotation_deg']} for s in SEGMENTS}
    keyframes=[];dense=[]
    for s,segs in SEGMENTS.items():
        a=originals[s];m0=np.asarray(segs[0],float).reshape(2,2).mean(0)
        for f,seg in zip(TIMES,segs):
            center=np.asarray([a['cx'],a['cy']])+np.asarray(seg,float).reshape(2,2).mean(0)-m0
            box=dict(a);box.update(cx=float(center[0]),cy=float(center[1]))
            if f==358:box=dict(a)
            keyframes.append({'scene':'R35ZF','subject_id':s,'sar_frame':f,'sar_box':box,
                'sar_end_support_xyxy':seg,'support_source':'DIRECT_ASSISTANT_NATIVE_IMAGE_READING',
                'body_source':'USER_NATIVE_BOX_358' if f==358 else 'ANCHOR_BODY_WITH_VISUALLY_READ_LOCAL_DISPLACEMENT',
                'annotation_author':'USER' if f==358 else 'CODEX_ASSISTANT',
                'support_annotation_author':'CODEX_ASSISTANT','source_pointer':anchors[s]['source_json_pointer'],
                'evidence_sheet':'reading/CENTRAL_NATIVE_1.png' if f<=420 else 'reading/CENTRAL_NATIVE_2.png'})
        for f in range(358,495):
            direct=next((r for r in keyframes if r['subject_id']==s and r['sar_frame']==f),None)
            seg=[float(np.interp(f,TIMES,[p[k] for p in segs])) for k in range(4)]
            center=np.asarray([a['cx'],a['cy']])+np.asarray(seg).reshape(2,2).mean(0)-m0
            box=dict(a);box.update(cx=float(center[0]),cy=float(center[1]))
            if f==358:box=dict(a)
            dense.append({'scene':'R35ZF','subject_id':s,'name':NAMES[s],'sar_frame':f,
                'timestamp_ms_nominal':data.frame('SAR',f)['timestamp_ms_nominal'],
                'sar_box':box,'sar_end_support_xyxy':seg,
                'coordinate_space':'SAR_RAW_NATIVE_1024x592','motion_class':'STATIC_PARKED',
                'label_kind':'WHOLE_BODY_APPROXIMATE_TEMPORAL_ANNOTATION',
                'geometry_source':direct['body_source'] if direct else 'INTERPOLATED_BETWEEN_VISUAL_KEYFRAMES',
                'body_size_and_axis_source':'USER_SAR358_REFERENCE',
                'frame_role':'USER_ANCHOR' if f==358 else ('ASSISTANT_KEYFRAME' if direct else 'INTERPOLATED_FRAME'),
                'user_confirmed_this_frame':f==358,'optical_identity':NAMES[s],
                'review_scope':'FIRST_CENTRAL_ANNOTATION_VERSION',
                'visibility_extent':'BODY_ENVELOPE_INSIDE_SAR_DISPLAY',
                'image_path':data.frame('SAR',f)['image_path']})
    dump('KEYFRAME_ANNOTATIONS.json',keyframes)
    dump('ANNOTATIONS.json',{'schema':'CENTRAL_STATIC_CAR_SEQUENCE_V1','scene':'R35ZF',
        'created':datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),
        'subjects':['002','003','005'],'frame_range':[358,494],'fps_source':30,
        'description':'Three parked vehicles, whole native SAR image, approximate whole-body labels across137 frames',
        'method':'Existing manual body358 + per-car direct keyframe endpoint displacement; linear interpolation between keyframes',
        'static_object_semantics':'Vehicles remain parked; changing SAR pixel coordinates are viewpoint/platform image motion',
        'records':dense})
    # Extracted source-frame inventory, including actual nominal optical pairing.
    byframe={f:[r for r in dense if r['sar_frame']==f] for f in range(358,495)}
    manifest={};frame_paths=[];paired_paths=[]
    for n in ['sar_frames','paired_frames','keyframes']:(OUT/n).mkdir(exist_ok=True)
    optical=data.frames('OPTICAL')
    for f in range(358,495):
        sarrow=data.frame('SAR',f);raw=Image.fromarray(data.image('SAR',f));rows=byframe[f]
        manifest[sarrow['image_path']]=sarrow['image_sha256']
        labelled=label_sar(raw,rows,f)
        frame=Image.new('RGB',(1024,656),'#0d2034');frame.paste(labelled,(0,0));d=ImageDraw.Draw(frame)
        d.text((14,597),f'R35  SAR {f:03d}  |  002 白色SUV    003 灰色轿车    005 橙色车',font=font(22),fill='white')
        d.text((14,629),'静止车辆 · 整体范围时序标注初稿',font=font(17),fill='#aebed0')
        path=OUT/'sar_frames'/f'{f:06d}.jpg';frame.save(path,quality=95);frame_paths.append(path)
        t=sarrow['timestamp_ms_nominal'];orow=optical.iloc[(optical.optical_timestamp_ms-t).abs().argsort().iloc[0]].to_dict()
        of=int(orow['optical_frame_index']);opt=Image.fromarray(data.image('OPTICAL',of))
        manifest[orow['optical_image_path']]=orow['image_sha256']
        pair=Image.new('RGB',(1024,1240),'#0d2034')
        pair.paste(opt.resize((1024,576),Image.Resampling.LANCZOS),(0,0));pair.paste(frame,(0,584))
        ppath=OUT/'paired_frames'/f'{f:06d}.jpg';pair.save(ppath,quality=91);paired_paths.append(ppath)
        if f in TIMES:
            frame.save(OUT/'keyframes'/f'SAR_{f}.png')
        if f%30==0:print(f'rendered {f}',flush=True)
    dump('SOURCE_MANIFEST.json',manifest)
    # Simple reference strips identify the three selected cars unambiguously.
    im=Image.new('RGB',(1500,380),'#edf1f6');d=ImageDraw.Draw(im)
    anchor_opt=Image.fromarray(data.image('OPTICAL',215))
    for j,s in enumerate(['002','003','005']):
        r=anchors[s];bb=tuple(int(r['optical_box_'+k]) for k in ['x1','y1','x2','y2'])
        crop=anchor_opt.crop(bb);crop.thumbnail((480,290))
        im.paste(crop,(j*500+(500-crop.width)//2,60))
        d.text((j*500+18,10),s+'  '+NAMES[s],font=font(28),fill='#162c44')
    im.save(OUT/'SELECTED_CARS.png')
    # Four full-frame views with fixed IDs; no anonymous neighborhood questions.
    contact=Image.new('RGB',(2048,1312),'#edf1f6')
    for j,f in enumerate([358,400,440,494]):contact.paste(Image.open(OUT/'sar_frames'/f'{f:06d}.jpg'),((j%2)*1024,(j//2)*656))
    contact.save(OUT/'ANNOTATION_OVERVIEW.png')
    # Evidence panels keep direct response readings separate from whole-body extent.
    detail=Image.new('RGB',(2048,1312),'#edf1f6')
    for j,f in enumerate([358,400,440,494]):
        frame=Image.new('RGB',(1024,656),'#0d2034');frame.paste(label_sar(Image.fromarray(data.image('SAR',f)),byframe[f],f,show_segments=True),(0,0))
        dr=ImageDraw.Draw(frame);dr.text((14,600),f'SAR {f} | 白色短线：逐帧目视读取；彩框：整体范围',font=font(21),fill='white')
        detail.paste(frame,((j%2)*1024,(j//2)*656))
    detail.save(OUT/'KEYFRAME_SUPPORT_AND_BODY.png')
    # Every SAR frame is encoded, playback at half speed for annotation inspection.
    ffmpeg=shutil.which('ffmpeg')
    if not ffmpeg:
        import imageio_ffmpeg
        ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
    for folder,name in [('sar_frames','CENTRAL_STATIC_SAR.mp4'),('paired_frames','CENTRAL_STATIC_PAIRED.mp4')]:
        command=[ffmpeg,'-y','-hide_banner','-loglevel','error','-framerate','15','-start_number','358',
                 '-i',str(OUT/folder/'%06d.jpg'),'-frames:v','137','-c:v','libx264','-preset','fast','-crf','18',
                 '-pix_fmt','yuv420p','-movflags','+faststart',str(OUT/name)]
        subprocess.run(command,check=True)
    # Compact complete-frame GIF to permit inline preview without a local server.
    gif=[Image.open(p).resize((768,492),Image.Resampling.LANCZOS) for p in frame_paths]
    gif[0].save(OUT/'CENTRAL_STATIC_PREVIEW.gif',save_all=True,append_images=gif[1:],duration=70,loop=0,optimize=False)
    checks=[]
    checks.append({'check':'137 consecutive frames per each of3 objects','passed':len(dense)==411 and all([r['sar_frame'] for r in dense if r['subject_id']==s]==list(range(358,495)) for s in SEGMENTS)})
    checks.append({'check':'original user358 boxes retained exactly','passed':all(next(r for r in dense if r['sar_frame']==358 and r['subject_id']==s)['sar_box']==originals[s] for s in SEGMENTS)})
    checks.append({'check':'24 explicit keyframe readings;21 added body placements','passed':len(keyframes)==24 and sum(r['sar_frame']!=358 for r in keyframes)==21})
    checks.append({'check':'source user annotation unchanged','passed':sha(source_snapshot)==original_snapshot_hash})
    # Display completeness checks body perimeter against actual colored SAR fan.
    outside=0
    for f,rows in byframe.items():
        im=np.asarray(Image.open(rows[0]['image_path']).convert('RGB'))
        for r in rows:
            pts=native_corners(*(r['sar_box'][k] for k in ['cx','cy','width','height','rotation_deg']))
            edges=np.concatenate([np.linspace(a,b,100) for a,b in zip(pts,np.roll(pts,-1,axis=0))])
            xy=np.rint(edges).astype(int)
            if np.any(xy<0) or np.any(xy[:,0]>=1024) or np.any(xy[:,1]>=592):outside+=1;continue
            rgb=im[xy[:,1],xy[:,0]].astype(int)
            if np.any((rgb.max(1)-rgb.min(1)<20)&(rgb.min(1)>220)):outside+=1
    checks.append({'check':'all411 body perimeters remain inside colored SAR display','passed':outside==0,'outside_count':outside})
    videos={}
    for name in ['CENTRAL_STATIC_SAR.mp4','CENTRAL_STATIC_PAIRED.mp4']:
        cap=cv2.VideoCapture(str(OUT/name));n=0
        while True:
            ok,fr=cap.read()
            if not ok:break
            n+=1
        cap.release();videos[name]=n
    checks.append({'check':'both videos decode all137 frames','passed':all(n==137 for n in videos.values()),'decoded_frames':videos})
    writeout={'status':'PASS' if all(c['passed'] for c in checks) else 'FAIL','checks':checks,
              'meaning':'Source/geometry/media correctness; annotation precision remains that of this first approximate-body version'}
    dump('CHECKS.json',writeout)
    if writeout['status']!='PASS':raise RuntimeError(writeout)
    print(json.dumps({'subjects':3,'frames':137,'rows':411,'keyframe_rows':24,'checks':writeout['status'],'out':str(OUT)},ensure_ascii=False))

if __name__=='__main__':main()
